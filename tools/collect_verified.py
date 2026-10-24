"""Normal collection adapter: adaptive discovery, Agent verification, schema3 only."""
from __future__ import annotations

import argparse
import copy
import hashlib
import html
import io
import json
import os
from pathlib import Path
import re
import subprocess
import sys
import time
from urllib.parse import parse_qs,quote,urlsplit
from uuid import uuid4
import zipfile
from contextlib import contextmanager, nullcontext

ROOT=Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:sys.path.insert(0,str(ROOT))

import httpx
from PIL import Image

from ref_lab.models import CandidatePackage
from ref_lab.verified_collection import AntigravityCollectionAgent,AgentUnavailable,AgentCallFailed,CollectionVision,accepted,query_steps,reference_supported,scope_sha,_plan_name_records
from ref_lab.storage import atomic_write
from ref_lab.collection_history import (HistoryIntegrityBlocked,ImageHistory,collect_history_scope)
from ref_lab import collection_queue
from ref_lab.collection_pipeline import OrderedReviews
from ref_lab.collection_timing import CollectionTiming
from ref_lab.collection_checkpoint import load_checkpoint,original_bytes,coverage,read_json,rule_contract,job_binding
from ref_lab.search_relevance import (classify_card, confirmed_count, exploration_count,
                                      exploration_image_count, exploration_limit, is_confirmed,
                                      relevance_counts, source_warnings)
from tools.collect_adapter import load_job_info,select_browserskill,fetch_pinterest_detail_metadata,NEGATIVE_TYPE_MARKERS
from tools.exact_recall import assess_search,capture_note,normalize_image_url,save
from ref_lab.browser_recovery import (
    BrowserError, BrowserInfrastructureError, PlatformRestrictionError,
    DetailItemError, sanitize_diagnostics, classify_bsk_error, is_infrastructure_error
)

MAX_QUERIES=8
MAX_GOAL_QUERIES=24
MAX_GOAL_NOTE_IMAGES=12
MAX_IMAGES=200
SAMPLE_PER_QUERY=8
MAX_WINDOWS=3
MAX_DETAIL_PAGES=144


def _post_key(url):
    try:parsed=urlsplit(str(url or ''))
    except ValueError:return ''
    if parsed.scheme!='https' or not parsed.hostname or parsed.username or parsed.password:return ''
    path=parsed.path.rstrip('/')
    if parsed.hostname.endswith('.xiaohongshu.com') or parsed.hostname=='xiaohongshu.com':
        path=re.sub(r'^/(?:explore|search_result)/([a-f0-9]{24})$',r'/explore/\1',path)
    return parsed.hostname.lower()+path


def _rank_discovery_cards(cards,seen_posts,attempts,*,names,work_terms,other_terms):
    return sorted(cards,key=lambda card:(bool(_post_key(card.get('page')) in seen_posts
        or attempts.get(_post_key(card.get('page')),0)),classify_card(
            card,names=names,work_terms=work_terms,other_terms=other_terms)['rank']))


def _qualified_feedback(*,before,after,duplicates,received,cards,pending,detail_failures,blocked):
    gain=max(0,after-before)
    if blocked:reason,action='platform_blocked','stop_source'
    elif detail_failures:reason,action='detail_failure','bounded_retry'
    elif pending:reason,action='qualification_pending','continue'
    elif gain:reason,action='qualified_candidates_received','continue'
    elif duplicates:reason,action='history_duplicate_high','change_photography_intent'
    elif cards:reason,action='no_qualified_yield','next_query'
    else:reason,action='visible_candidates_exhausted','next_query'
    return {'reason':reason,'action':action,'qualified_gain':gain,'pending':int(pending),
            'new_originals':received,'duplicates':duplicates,
            'duplicate_fraction':duplicates/max(1,duplicates+received),
            'low_yield':not blocked and not detail_failures and not pending and not gain}


class SourceBlocked(ValueError):
    pass


def discovery_rank(card,aliases=(),work_terms=(),other_terms=()):
    """Order discovery only; absent/negative metadata never becomes a visual verdict.

    The classifier in ``search_relevance`` decides whether a card may count as a
    confirmed target. This rank is retained as a cheap ordering hint and keeps
    the historical 0..4 scale for callers/tests.
    """
    text=str(card.get('text') or '').casefold()
    positive=bool(re.search(r'cosplay|coser|コスプレ|摄影|写真|正片|场照|返图|photoshoot|photograph',text))
    negative=any(term in text for term in (*NEGATIVE_TYPE_MARKERS,'イラスト'))
    target=any(str(name).strip().casefold() in text for name in aliases if str(name).strip())
    if aliases:
        if target:
            return 0 if positive else 1
        if any(str(term).strip().casefold() in text for term in other_terms if str(term).strip()):
            return 4
        return 4 if negative else (2 if positive else 3)
    return 0 if positive and not negative else (2 if negative and not positive else 1)


def fatal_visual_error(exc):
    return getattr(exc,'fatal',False) or getattr(exc,'code','') in ('unexpected_tool','unexpected_read')


def verified_candidate(row,result,project,references,query='',discovery_url=''):
    sha=result.asset_sha
    return {'id':'verified-'+sha[:20],'file':'images/'+Path(row['original_path']).name,
            'title':project['character']+' · '+(result.observed_costume[:70] or '已逐图核验'),
            'source':{'page_url':row['page_url'],'image_url':row['image_url'],'author':row.get('author',''),'search_query':query,
                      'rights':'unknown','source_confirmed':False,'obtained_as':'platform_variant'},
            'discovery_intent':'exact_character','discovery_url':discovery_url,
            'discovery_reason':'多语言发现后独立看图核验；不是搜索词或标题推断。','notes':result.reason,
            'preflight':{'content_type':'real_person_cosplay','identity_prediction':'match','confidence':result.confidence,
                         'visual_evidence':result.kind_evidence+result.identity_evidence+result.costume_evidence+['识别参照：'+r['page_url'] for r in references],
                         'reason':result.reason}}


@contextmanager
def resume_lock(folder,name='resume.lock'):
    folder.mkdir(parents=True,exist_ok=True)
    with (folder/name).open('a+b') as handle:
        handle.seek(0,2)
        if not handle.tell():handle.write(b'0');handle.flush()
        handle.seek(0)
        try:
            if os.name=='nt':
                import msvcrt
                msvcrt.locking(handle.fileno(),msvcrt.LK_NBLCK,1)
            else:
                import fcntl
                fcntl.flock(handle,fcntl.LOCK_EX|fcntl.LOCK_NB)
        except OSError as exc:raise AgentUnavailable('该续核状态已有执行者；未重复启动AGY。') from exc
        try:yield
        finally:
            handle.seek(0)
            if os.name=='nt':msvcrt.locking(handle.fileno(),msvcrt.LK_UNLCK,1)
            else:fcntl.flock(handle,fcntl.LOCK_UN)


def resume_collection(job,source,folder):
    source=source.resolve();folder=folder.resolve()
    if not source.is_relative_to((ROOT/'.local/collection-runs').resolve()) or not folder.is_relative_to((ROOT/'.local/collection-resumes').resolve()):
        raise AgentUnavailable('续核输入/输出必须在本仓库指定隔离目录。')
    with resume_lock(folder):return _resume_collection(job,source,folder)


def _resume_collection(job,source,folder):
    load=lambda p:json.loads(p.read_text('utf8'))
    sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
    project={**job['project_snapshot'],'notes':job.get('notes','')};context=scope_sha(project)
    info=load(source/'run-info.json');received=load(source/'received.json')
    if info.get('binding') is not None and info['binding']!=job_binding(job,info['model']):
        raise AgentUnavailable('原轮缺少当前任务/模型/规则的完整绑定；保留原判断，但不能将其作为可验证断点复用。')
    original=load(source/'visual-audit.json') if (source/'visual-audit.json').exists() else []
    recorded={r['asset_sha'] for r in original}
    if recorded-{r['asset_sha'] for r in received}:raise AgentUnavailable('审计包含未收到原图的记录。')
    original=[*original,*[{'asset_sha':r['asset_sha'],'source_page':r['page_url'],'review':None,'accepted':False,
                         'decision':'NEEDS_EVIDENCE','execution_error':'Received before interrupted audit write'}
                        for r in received if r['asset_sha'] not in recorded]]
    if info['job_id']!=job['id']:raise AgentUnavailable('续核任务ID不一致。')
    references=load(source/'reference-research/report.json')['references']
    if not references:raise AgentUnavailable('续核缺少原轮可信参照；不搜索、不放宽门槛。')
    for row in received:
        path=Path(row['original_path']).resolve()
        if not path.is_relative_to(source/'images') or sha(path)!=row['asset_sha']:raise AgentUnavailable('原候选路径或SHA已改变，拒绝续用旧结果。')
    for ref in references:
        path=Path(ref['path']).resolve()
        if (not path.is_relative_to(source/'reference-research') or sha(path)!=ref['asset_sha'] or
                ref['authority'] not in ('official_publisher','official_licensed_manufacturer','official_licensed_distributor')):
            raise AgentUnavailable('原参照字节或来源边界变化。')
        with Image.open(path) as image:
            if min(image.size)<240:raise AgentUnavailable('原参照清晰度不足。')
            image.verify()
    if len({r['asset_sha'] for r in received})!=len(received):raise AgentUnavailable('原候选SHA重复。')
    for record in original:
        if record.get('review'):
            value=CollectionVision.model_validate(record['review'])
            if value.context_sha!=context or value.asset_sha!=record['asset_sha']:raise AgentUnavailable('原已完成判断不属于当前图片/要求。')
    if info.get('binding') is None:
        # Old checkpoints predate job_binding; replay their exact prompt through read-only receipts.
        from ref_lab.verified_collection import AntigravityCollectionAgent as ReceiptReader
        probe=ReceiptReader(folder,model=info['model'])
        probe.folder=source;probe.candidate_limit=probe.vision_cli_limit=0;probe.deadline=0
        receipts=[load(p) for p in source.glob('agent-*.json')]
        for record in original:
            if not record.get('review'):continue
            valid=False
            for receipt in receipts:
                if receipt.get('result')!=record['review']:continue
                supplied=[ref for ref in references if str(Path(ref['path']).resolve()) in receipt.get('binding',{}).get('inputs',{})]
                path=next(Path(row['original_path']) for row in received if row['asset_sha']==record['asset_sha'])
                try:valid=probe._review_once(path,project,references=supplied).model_dump()==record['review']
                except AgentUnavailable:continue
                if valid:break
            if not valid:raise AgentUnavailable('旧断点缺少与当前原图、条件、参照、模型及提示词一致的成功回执。')
    names=['run-info.json','received.json','visual-audit.json','reference-research/report.json','manifest.json','counts.json','runtime-budget.json']
    names.extend(str(p.relative_to(source)) for p in (source/'reference-research').glob('source-*.*'))
    binding={'job_id':job['id'],'job_binding':job_binding(job,info['model']),'context_sha':context,'source':str(source),'files':{n:sha(source/n) for n in names if (source/n).exists()},
             'image_shas':[r['asset_sha'] for r in received],'reference_shas':[r['asset_sha'] for r in references],'model':info['model']}
    state=folder/'resume-inputs.json'
    if state.exists() and load(state)!=binding:raise AgentUnavailable('续核输入/要求变化；未继承旧断点。')
    if not state.exists():
        if (source/'runtime-budget.json').exists():save(folder/'runtime-budget.json',load(source/'runtime-budget.json'))
        # Every launch is charged, including SUCCESS with denied/invalid evidence.
        for f in source.glob('attempt-*.json'):
            old=load(f)
            save(folder/(f.stem+'-1.json'),{**old,'result_type':'historic_attempt','historic':True})
        pending_before={r['asset_sha'] for r in original if not r.get('review')}
        for f in source.glob('agent-*.json'):
            receipt=load(f)
            if receipt.get('binding') and receipt.get('result',{}).get('asset_sha') in pending_before:save(folder/f.name,receipt)
        save(state,binding)
    audit_path=folder/'visual-audit.json';audit=load(audit_path) if audit_path.exists() else json.loads(json.dumps(original))
    by_sha={r['asset_sha']:r for r in audit}
    if set(by_sha)!={r['asset_sha'] for r in received}:raise AgentUnavailable('续核断点图片集合不一致。')
    for record in audit:
        if record.get('review'):
            value=CollectionVision.model_validate(record['review'])
            if value.asset_sha!=record['asset_sha'] or value.context_sha!=context:raise AgentUnavailable('续核断点判断绑定错误。')
    for record in original:
        if record.get('review') and by_sha[record['asset_sha']]!=record:raise AgentUnavailable('原已完成记录被改写。')
    save(audit_path,audit)
    counts=load(source/'counts.json') if (source/'counts.json').exists() else {}
    spent=counts.get('vision_cli_calls',counts.get('attempted_visual_calls',0))
    if not spent:spent=sum(load(f).get('result_type')=='CollectionVision' for f in source.glob('attempt-*.json'))
    agent=AntigravityCollectionAgent(folder,model=info['model'],target_count=int(job.get('target_count') or 30))
    agent.references=references;agent.candidate_limit=len(received)*3
    agent.vision_cli_limit=max(0,info.get('visual_call_budget',60)-spent)
    failures=[]
    for row in received:
        record=by_sha[row['asset_sha']]
        if record.get('review'):continue
        try:
            value=agent.review(Path(row['original_path']),project);valid=accepted(value,project,references=references)
            if value.asset_sha!=row['asset_sha'] or value.context_sha!=context:raise AgentUnavailable('续核图片/要求绑定不一致。')
            record.clear();record.update(asset_sha=row['asset_sha'],source_page=row['page_url'],review=value.model_dump(),accepted=valid,
                decision='CONFIRMED' if valid else ('MISMATCH' if value.kind not in ('cosplay_photo','portrait_photo','unknown') or (value.identity=='match' and value.costume=='mismatch' and reference_supported(value,references)) else 'NEEDS_EVIDENCE'))
        except AgentUnavailable as exc:
            record['execution_error']=str(exc);failures.append(str(exc))
            save(audit_path,audit)
            if fatal_visual_error(exc):break
        save(audit_path,audit)
    manifest=load(source/'manifest.json') if (source/'manifest.json').exists() else {'candidates':[]}
    old_candidates={c['id']:c for c in manifest['candidates']};candidates=[];images={}
    for row in received:
        record=by_sha[row['asset_sha']]
        if not record['accepted']:continue
        value=CollectionVision.model_validate(record['review'])
        if not accepted(value,project,references=references):raise AgentUnavailable('已有通过记录不满足严格准入。')
        candidate=old_candidates.get('verified-'+row['asset_sha'][:20])
        if candidate is None:
            candidate=verified_candidate(row,value,project,references,row.get('search_query',''),row.get('discovery_url',''))
            candidate['discovery_reason']='续核原轮已保存候选；未重新搜索，原帖子和检索轮次保留，未记录的精确查询不编造。'
        candidates.append(candidate);images[Path(candidate['file']).name]=Path(row['original_path']).read_bytes()
    pending=sum(not r.get('review') for r in audit)
    progress={'total':len(received),'previously_completed':sum(bool(r.get('review')) for r in original),
              'completed':len(received)-pending,'pending':pending,'accepted':len(candidates),'vision_cli_calls':agent.vision_cli_calls,
              'vision_cli_limit':agent.vision_cli_limit,'new_search_queries':0,'Root_selection_overrides':0}
    save(folder/'resume-progress.json',progress)
    previous_report=manifest.get('execution_report',{});checks=previous_report.get('source_checks',[]);queries=previous_report.get('query_log',[])
    source_state=read_json(source/'collector-state.json',{})
    sources=job.get('preferred_sources',['xiaohongshu','pinterest'])
    if source_state.get('steps'):
        coverage_result=coverage(source_state['steps'],source_state['searches'],sources)
    else:
        from ref_lab.verified_collection import NamePlan
        planning=read_json(source/'name-plan.json',{})
        steps=query_steps(project,NamePlan.model_validate(planning['plan']),sources) if planning.get('plan') else []
        attempts={str(i):{**step,'observed':True,'usable':any(s['source']==step['source'] and s['status']=='usable' for s in checks)}
                  for i,step in enumerate(steps) if any(q['source']==step['source'] and q['query']==step['query'] for q in queries)}
        coverage_result=coverage(steps,attempts,sources)
        if not steps:coverage_result['gaps'].append('旧轮缺少可核实的语言检索计划，未宣称覆盖达标。')
    coverage_gaps=list(dict.fromkeys([*coverage_result['gaps'],*[g for g in previous_report.get('gaps',[]) if g.startswith(('来源覆盖未满足：','检索语言覆盖未满足：'))]]))
    complete=not pending and len(candidates)>=int(job.get('target_count') or 12) and not coverage_gaps
    saved_output=load(folder/'manifest.json') if (folder/'manifest.json').exists() else {}
    output={'schema_version':3,'job_id':job['id'],'batch_id':saved_output.get('batch_id') or uuid4().hex,'candidates':candidates,'execution_report':{
        'producer':agent.producer,'status':'completed' if complete else 'blocked',
        'summary':f'{"达标完成" if complete else "部分完成" if candidates else "执行受阻"}：仅续核已保存候选，完成{len(received)-pending}/{len(received)}，AGY通过{len(candidates)}；本次新搜索0。',
        'source_checks':checks,'query_log':queries,'gaps':list(dict.fromkeys(failures))[:20]+coverage_gaps+([f'{pending}张仍未完成视觉执行。'] if pending else [])}}
    CandidatePackage.model_validate(output);save(folder/'manifest.json',output)
    return output,images

XHS_SORT_JS=r"""(() => {
 const real=x=>!x.closest('[aria-hidden="true"]');
 const visible=x=>real(x)&&x.getBoundingClientRect().width>0&&x.getBoundingClientRect().height>0
   &&Number(getComputedStyle(x).opacity)>=.1&&(!x.checkVisibility||x.checkVisibility({checkOpacity:true,checkVisibilityCSS:true}));
 const selector=x=>{if(!x)return null;const chain=[];while(x&&x!==document.body){
   chain.unshift(x.tagName.toLowerCase()+':nth-child('+(Array.from(x.parentElement.children).indexOf(x)+1)+')');x=x.parentElement;}
   return 'body>'+chain.join('>');};
 const tags=Array.from(document.querySelectorAll('.tags')).filter(real);
 const active=tags.filter(x=>x.classList.contains('active')).map(x=>x.textContent.trim());
 const find=t=>tags.find(x=>x.textContent.trim()===t&&visible(x));
 return {trigger:selector(Array.from(document.querySelectorAll('span')).find(x=>['筛选','已筛选'].includes(x.textContent.trim())&&visible(x))),
   dismiss:selector(Array.from(document.querySelectorAll('input[placeholder]')).find(visible)),
   comprehensive:selector(find('综合')),
   latest:selector(find('最新')),
   active:active,
   selected:active.includes('最新'),
   selected_comprehensive:active.includes('综合')};
})()"""

SEARCH_JS=r"""(() => {
 const visible=x=>{const r=x.getBoundingClientRect();return r.width>0&&r.height>0&&r.bottom>0&&r.right>0&&r.top<innerHeight&&r.left<innerWidth
   &&(!x.checkVisibility||x.checkVisibility({checkOpacity:true,checkVisibilityCSS:true}))};
 const text=(document.body&&document.body.innerText)||'';
 const login=Array.from(document.querySelectorAll('[role="dialog"],.login-container,.login-box'))
   .some(x=>visible(x)&&/登录|登入|扫码|Log in|Sign up/.test(x.innerText));
 const challenge=Array.from(document.querySelectorAll('iframe[src*="captcha"]')).some(visible)||/访问过于频繁|验证后继续|Verify you are human/.test(text);
 const source=location.hostname.includes('xiaohongshu')?'xiaohongshu':'pinterest';
 let cards=[];
 if(source==='xiaohongshu'){
  cards=Array.from(document.querySelectorAll('section')).filter(x=>x.querySelector('img'))
    .map(x=>{const link=x.querySelector('a[href*="/explore/"],a[href*="/search_result/"]');
     const href=link?link.href:'';
     const id=(href.match(/\/(?:explore|search_result)\/([a-f0-9]{24})/)||[])[1]||'';
     // The card keeps the URL the search page exposed, including the query
     // parameters that page carried; nothing is composed or guessed here.
     let observed=href;
     if(id&&!href.includes('?')){
      const rich=Array.from(x.querySelectorAll('a[href]')).find(a=>{
       try{const u=new URL(a.href,location.href),original=new URL(href,location.href);
        return u.origin===original.origin&&!u.username&&!u.password&&!!u.search
         &&(u.pathname.match(/^\/(?:explore|search_result)\/([a-f0-9]{24})\/?$/)||[])[1]===id;
       }catch{return false;}});
      if(rich)observed=rich.href;
     }
     return {text:x.innerText,page:observed};});
 }else{
  cards=Array.from(document.images).filter(x=>x.naturalWidth>=200&&x.naturalHeight>=200)
   .map(x=>({text:[x.alt,x.getAttribute('aria-label'),x.closest('[data-test-id="pin"], [data-grid-item], [role="listitem"]')?.innerText].filter(Boolean).join('\n'),
             page:x.closest('a')?.href,cover_url:x.currentSrc||x.src,cover_width:x.naturalWidth,cover_height:x.naturalHeight}))
   .filter(x=>x.page&&/\/pin\/\d+\//.test(x.page));
 }
 const seen=new Set();cards=cards.filter(x=>x.page&&!seen.has(x.page)&&seen.add(x.page)).slice(0,60);
 return {url:location.href,search:document.querySelector('input[placeholder],textarea[placeholder]')?.value,
         visibleMain:text.slice(0,8000),cards,login_required:login,challenge,body_ready:!!document.body,
         sort_latest:source==='xiaohongshu'&&Array.from(document.querySelectorAll('.tags.active'))
           .some(x=>!x.closest('[aria-hidden="true"]')&&x.textContent.trim()==='最新')};
})()"""


DETAIL_PROBE_JS=r"""(() => {
 const visible=x=>{const r=x.getBoundingClientRect();return r.width>0&&r.height>0
   &&(!x.checkVisibility||x.checkVisibility({checkOpacity:true,checkVisibilityCSS:true}));};
 const text=((document.body&&document.body.innerText)||'').slice(0,4000);
 const login=Array.from(document.querySelectorAll('[role="dialog"],.login-container,.login-box'))
   .some(x=>visible(x)&&/登录|登入|扫码|Log in|Sign up/.test(x.innerText));
 const challenge=Array.from(document.querySelectorAll('iframe[src*="captcha"]')).some(visible)
   ||/访问过于频繁|验证后继续|Verify you are human/.test(text);
 const notFound=/当前笔记暂时无法浏览|内容不存在|页面不见了|Note not found/i.test(text);
 return {url:location.href,login_required:login,challenge,not_found:notFound,body_ready:!!document.body};
})()"""


class Browser:
    supports_sort=True
    def __init__(self,folder:Path):
        self.folder=folder;self.session=None;self.start_request=None;self.bsk=None;self.browser_id=None
        self.env={**os.environ,'BSK_AUTO_START':'0'}
        self.timing=None;self.preview=None;self.preview_reused=0
        self.preview_payloads={'created':0,'removed':0,'bytes':0}
        self._preview_root=None
        self._preview_owned=None
        self.cover_cache_path=None;self._cover_entries=None
        self.preview_payloads['metadata_hits']=0
        self.recovery_attempts=0;self.max_recovery_attempts=2
        self.recovery_budget_seconds=60.0;self.recovery_seconds_used=0.0
        self.recovery_start_time=None;self.recovery_active=False
        self.last_successful_page=None;self.last_successful_at=None
        self.return_issue_category=None
        self.known_shas=None;self.known_sources=None;self.incoming_dir=None

    def _span(self,name,**fields):
        timing=getattr(self,'timing',None)
        return timing.span(name,**fields) if timing is not None else nullcontext()

    def _probe_detail(self):
        """Cheap binding/login/404 check for a just-opened detail page.

        A page whose body is not built yet is read again a bounded number of
        times.  An unfinished DOM is not a connection fault, and the wait stays
        inside the deadline that already governs this Job.
        """
        value={}
        for attempt in range(3):
            data=json.loads(self.command('evaluate','--session',self.session,'--json',DETAIL_PROBE_JS))
            if data.get('ok') is not True or not isinstance(data.get('value'),dict):
                raise DetailItemError('Detail page read failed',code='detail_read_failed')
            value=data['value']
            if value.get('body_ready') is not False or attempt>=2:break
            remaining=getattr(self,'deadline',float('inf'))-time.monotonic()
            if remaining<=0:break
            time.sleep(min(0.6,remaining))
        return value

    def _observed_note_url(self,url,note):
        """The observed URL of this note, or nothing at all.

        Nothing is composed here.  The URL is the one the search page exposed;
        it must be HTTPS, carry no credentials, belong to the same source and
        point at the very note the card referred to.  Anything else is refused
        instead of guessed.
        """
        raw=url if isinstance(url,str) else ''
        raw=raw.strip()
        if not raw:return ''
        try:parsed=urlsplit(raw)
        except ValueError:return ''
        if parsed.scheme!='https' or not parsed.hostname:return ''
        if parsed.username or parsed.password:return ''
        host=(parsed.hostname or '').lower()
        if host!='xiaohongshu.com' and not host.endswith('.xiaohongshu.com'):return ''
        match=re.fullmatch(r'/(?:explore|search_result)/([a-f0-9]{24})',parsed.path.rstrip('/'))
        if not match or match.group(1)!=note:return ''
        return raw

    def _search_page_confirmed(self,source,query):
        """Is the live page still the original search result page?

        The source, the query, this session and visible cards must all still
        match.  Only then has the browser not left the page, and stepping
        back would move into an unrelated page.
        """
        try:
            snapshot=self.snapshot()
        except (ValueError,OSError,subprocess.SubprocessError,KeyError):
            return False
        evidence=self._return_state(snapshot,source,query)
        evidence['stage']='after_unconfirmed_navigation'
        self._record_return_check(evidence)
        return bool(evidence.get('confirmed'))

    def can_recover(self)->bool:
        """Recovery keeps the total-Job deadline and a bounded attempt/time cap.

        Only time actually spent inside a recovery counts against the budget;
        normal collection work never consumes it.
        """
        return (self.recovery_attempts<self.max_recovery_attempts
                and time.monotonic()<getattr(self,'deadline',float('inf'))
                and self.recovery_seconds_used<self.recovery_budget_seconds
                and not self.recovery_active)

    def search_url(self,step):
        q=quote(step['query'])
        return ('https://www.pinterest.com/search/pins/?q='+q if step['source']=='pinterest'
                else 'https://www.xiaohongshu.com/search_result?keyword='+q)

    def _return_state(self,snapshot,source,query):
        """Describe whether the live page really is the original search page.

        Source host, path, the original query (URL parameter or visible search
        box), visible result content and this session id are all required; an
        address that merely looks like a search page is not enough.
        """
        parsed=urlsplit(snapshot.get('url','') or '')
        params=parse_qs(parsed.query or '')
        expected_path='/search/pins' if source=='pinterest' else '/search_result'
        host=(parsed.hostname or '').lower()
        domain='pinterest.com' if source=='pinterest' else 'xiaohongshu.com'
        source_ok=host==domain or host.endswith('.'+domain)
        url_query=(params.get('q') or params.get('keyword') or [''])[0]
        box=str(snapshot.get('search') or '')
        cards=snapshot.get('cards') or []
        blocked=bool(snapshot.get('login_required') or snapshot.get('challenge'))
        query_ok=bool(query) and (url_query==query or box==query)
        confirmed=bool(source_ok and parsed.path.rstrip('/')==expected_path and query_ok
                       and cards and not blocked and self.session)
        return {'confirmed':confirmed,'source':source,'host':host,'path':parsed.path.rstrip('/'),
                'expected_path':expected_path,'query':query,'url_query':url_query,'search_box':box,
                'cards':len(cards),'login_required':bool(snapshot.get('login_required')),
                'challenge':bool(snapshot.get('challenge')),'session_id':self.session}

    def _record_return_check(self,evidence):
        checks=collection_queue.read_json(self.folder/'return-checks.json',[])
        checks.append({'at':time.time(),**sanitize_diagnostics(evidence)})
        save(self.folder/'return-checks.json',checks[-20:])

    def _verify_return(self,step,stage):
        try:
            snapshot=self.snapshot()
        except (ValueError,OSError,subprocess.SubprocessError,KeyError) as exc:
            self._record_return_check({'confirmed':False,'stage':stage,'error':type(exc).__name__,
                                       'source':step.get('source'),'query':step.get('query')})
            return False
        evidence=self._return_state(snapshot,step['source'],
                                    str(step.get('query') or getattr(self,'active_query','') or ''))
        evidence['stage']=stage
        self._record_return_check(evidence)
        if evidence['confirmed'] and time.monotonic()<getattr(self,'deadline',float('inf')):
            self.return_failed=False;self.return_error=None;self.return_issue_category=None
            return True
        return False

    def _go_back(self):
        """Step back through browser history without waiting for the SPA.

        The observed SPA return can succeed while a load/commit wait times out.
        ``history.back()`` avoids that wait; the live source/query/content check
        afterwards determines whether the return actually succeeded.
        """
        self.command('evaluate','--session',self.session,'--json',
                     '(()=>{history.back();return true})()',timeout=10)

    def recover(self,step=None,reason='connection')->bool:
        """Recover only this task's browser, within one monotonic deadline.

        A page-return failure is repaired in place first: verify the live page,
        then revisit the original query in the same session. Rebuilding the
        session is the last resort, and the whole attempt stays bounded.
        """
        if not self.can_recover() or not self.bsk or not self.browser_id:
            return False
        self.recovery_attempts+=1
        started=time.monotonic()
        self.recovery_active=True
        if self.recovery_start_time is None:self.recovery_start_time=started
        old_deadline=getattr(self,'deadline',float('inf'))
        # The recovery allowance is what is left of the cumulative budget, not
        # a fresh window: 40 s already spent leaves 20 s, never a new 60 s.
        # Normal collection time between two recoveries is not charged here.
        remaining_budget=max(0.0,self.recovery_budget_seconds-self.recovery_seconds_used)
        self.deadline=min(old_deadline,started+remaining_budget)
        try:
            if reason=='return' and step:
                if self._verify_return(step,'before_repair'):
                    return True
                try:
                    self.command('navigate',self.search_url(step),'--session',self.session,
                                 '--wait-until','domcontentloaded','--timeout','15s',timeout=25)
                except (BrowserError,OSError,subprocess.SubprocessError) as exc:
                    if not is_infrastructure_error(exc):raise
                # A command timeout does not mean the page is wrong: the page is
                # read and judged, and a correct page ends the recovery here.
                if self._verify_return(step,'after_original_query'):
                    return True
            if not self._rebuild_session():
                return False
            if step:
                # A rebuilt session sits on a blank page. Return to the original
                # query and prove source, query, content and session before the
                # run is declared recovered.
                try:
                    self.command('navigate',self.search_url(step),'--session',self.session,
                                 '--wait-until','domcontentloaded','--timeout','15s',timeout=25)
                except (BrowserError,OSError,subprocess.SubprocessError) as exc:
                    if not is_infrastructure_error(exc):raise
                if not self._verify_return(step,'after_rebuild'):
                    return False
            if time.monotonic() >= self.deadline:return False
            self.return_failed=False;self.return_error=None;self.return_issue_category=None
            return True
        except (AgentUnavailable,BrowserError,ValueError,OSError,subprocess.SubprocessError):
            return False
        finally:
            self.deadline=old_deadline
            self.recovery_seconds_used+=time.monotonic()-started
            self.recovery_active=False

    def _rebuild_session(self)->bool:
        browsers=json.loads(self.command('browsers','--json',timeout=10))
        if not isinstance(browsers,list) or not any(
                b.get('instance_id')==self.browser_id and not b.get('unresponsive')
                and not b.get('version_skew') for b in browsers if isinstance(b,dict)):
            self._record_error(BrowserInfrastructureError('原浏览器尚未连接',code='browser_unavailable'))
            return False
        if self.start_request:
            cancelled=json.loads(self.command('session','request',self.start_request,'--cancel','--json',timeout=5))
            if cancelled.get('state')!='closed' or cancelled.get('cleanup_error'):return False
            self.start_request=None
        if self.session:
            try:self.command('session','stop',self.session,'--json',timeout=6)
            except BrowserInfrastructureError as exc:
                if exc.code not in ('session_not_found', 'not_found') and not getattr(exc, 'is_session_dead', False):
                    return False
            self.session=None
        self._start_session(timeout=12)
        # Session creation alone does not prove that the extension can read a page.
        self.snapshot()
        return True

    def _record_error(self,err):
        errors=collection_queue.read_json(self.folder/'browser-errors.json',[])
        errors.append(sanitize_diagnostics({
            'action':err.action,'category':err.category,'code':err.code,
            'details':str(err.details)[:400],'attempt':self.recovery_attempts,
            'result':'failed','at':time.time()
        }))
        save(self.folder/'browser-errors.json',errors)

    def command(self,*args,timeout=35):
        if getattr(self,'_cleanup_active',False):
            cancelling=(args[:2]==('session','request') and len(args)>2
                        and args[2]==self.start_request and '--cancel' in args)
            stopping=(args[:2]==('session','stop') and len(args)>2 and args[2]==self.session)
            if not (cancelling or stopping):
                raise AgentCallFailed('cleanup_operation_not_allowed',fatal=True)
        # Recovery belongs to the controller; replaying a dead session only wastes time.
        remaining=getattr(self,'deadline',float('inf'))-time.monotonic()
        if remaining<=0:
            raise AgentCallFailed('time_budget_exhausted',fatal=True)
        timeout=min(timeout,remaining)
        try:
            result=subprocess.run([self.bsk,*args],capture_output=True,text=True,encoding='utf8',
                                  errors='replace',env=self.env,timeout=timeout)
            if result.returncode:
                raise classify_bsk_error(args[0],result.returncode,result.stdout,result.stderr)
            if '--json' in args:
                try:payload=json.loads(result.stdout)
                except ValueError:
                    raise BrowserInfrastructureError('BrowserSkill 返回无效 JSON',action=args[0],code='invalid_response')
                if isinstance(payload,dict) and payload.get('ok') is False:
                    raise classify_bsk_error(args[0],1,result.stdout,result.stderr)
            return result.stdout
        except subprocess.TimeoutExpired:
            if time.monotonic()>=getattr(self,'deadline',float('inf')):
                raise AgentCallFailed('time_budget_exhausted',fatal=True)
            err=BrowserInfrastructureError('BrowserSkill command timed out',action=args[0],
                                           code='command_timeout',details=f'timeout after {timeout:.3f}s',is_timeout=True)
        except OSError as exc:
            err=BrowserInfrastructureError('BrowserSkill process unavailable',action=args[0],
                                           code='process_unavailable',details=str(exc))
        except BrowserError as exc:
            err=exc
        self._record_error(err)
        raise err

    def _start_session(self,timeout=35):
        self.start_request=f'{int((time.time()+600)*1000)}:{uuid4()}'
        save(self.folder/'browser-session.json',{'browser_id':self.browser_id,'request_id':self.start_request,'state':'pending'})
        self.command('session','request',self.start_request,'--prepare','--json',timeout=5)
        data=json.loads(self.command('session','start','--browser',self.browser_id,'--request-id',
                                     self.start_request,'--no-focus','--json',timeout=timeout))
        self.session=data.get('session_id')
        if not self.session:raise BrowserInfrastructureError('未返回浏览器会话',action='session',code='session_start_failed')
        self.command('session','request',self.start_request,'--claim','--json',timeout=5)
        self.start_request=None
        save(self.folder/'browser-session.json',{'browser_id':self.browser_id,'session_id':self.session,'state':'active'})

    def start(self):
        self.bsk,browser=select_browserskill(self.env)
        if not self.bsk or not browser:raise BrowserInfrastructureError('没有可用的已连接BrowserSkill浏览器',action='session',code='browser_unavailable')
        self.browser_id=browser
        self._start_session()

    def snapshot(self):
        data=json.loads(self.command('evaluate','--session',self.session,'--json',SEARCH_JS))
        if data.get('ok') is not True or not isinstance(data.get('value'),dict):
            raise BrowserInfrastructureError('Visible page read failed',action='evaluate',code='evaluate_failed')
        return data['value']

    def search(self,step,sort='relevance'):
        self.scroll_windows=0
        self.active_query=str(step.get('query') or '')
        q=quote(step['query'])
        url=('https://www.pinterest.com/search/pins/?q='+q if step['source']=='pinterest'
             else 'https://www.xiaohongshu.com/search_result?keyword='+q)
        with self._span('search_navigate',source=step['source']):
            self.command('navigate',url,'--session',self.session,'--wait-until','domcontentloaded','--timeout','25s')
        snapshot={}
        for attempt in range(3):
            with self._span('search_dom',source=step['source']):
                snapshot=self.snapshot()
            if snapshot.get('cards') or snapshot.get('login_required') or snapshot.get('challenge'):break
            if '找不到與這個搜尋條件相符的 Pin' in snapshot.get('visibleMain',''):break
            if attempt<2:time.sleep(1)
        if step['source']=='xiaohongshu' and snapshot.get('cards') and not snapshot.get('login_required') and not snapshot.get('challenge'):
            with self._span('search_sort',source=step['source']):
                state=self._apply_sort(sort)
            snapshot.update(state)
            with self._span('search_dom',source=step['source']):
                snapshot={**self.snapshot(),**state}
        if step['source']=='xiaohongshu' and 'sort_state' not in snapshot:
            snapshot['sort_state']='default_control_unavailable'
        if snapshot.get('cards') and not snapshot.get('login_required') and not snapshot.get('challenge'):
            self.return_failed=False
        self.last_successful_page=url
        self.last_successful_at=time.time()
        return snapshot

    def _apply_sort(self,sort):
        """Pick 综合/最新 through the visible control and report what is active.

        The previous version took a full-page snapshot after every interaction.
        Sort state is readable from the small tag strip, so only one full search
        snapshot is needed afterwards.
        """
        def read():
            payload=json.loads(self.command('evaluate','--session',self.session,'--json',XHS_SORT_JS))
            return (payload.get('value') or {}) if payload.get('ok') is True else {}

        value=read()
        trigger=value.get('trigger')
        if trigger:
            self.command('hover','--selector',trigger,'--session',self.session)
            value={**value,**read()}
        desired='latest' if sort=='latest' else 'comprehensive'
        label='最新' if desired=='latest' else '综合'
        if value.get(desired) and label not in (value.get('active') or []):
            self.command('click','--selector',value[desired],'--session',self.session)
            time.sleep(1)
            value={**value,**read()}
        dismiss=value.get('dismiss')
        if dismiss:
            self.command('hover','--selector',dismiss,'--session',self.session)
            value={**value,**read()}
        active=value.get('active') or []
        return {'sort_state':('comprehensive' if '综合' in active else
                              ('latest' if '最新' in active else 'default')),
                'sort_evidence':{'available': active, 'requested': desired}}

    def more(self,step):
        self.scroll_windows+=1
        self.command('wheel','--delta-y',str(1800*self.scroll_windows),'--session',self.session,'--timeout','10s',timeout=15)
        time.sleep(1)
        return self.snapshot()

    def _cover_metadata(self):
        from ref_lab.collection_history import FINGERPRINT_ALGORITHM_VERSION,_cache_checksum
        from ref_lab.collage import ALGORITHM_VERSION
        if self._cover_entries is None:
            self._cover_entries={}
            path=self.cover_cache_path
            try:
                if path is None or path.is_symlink() or path.stat().st_size>8*1024*1024:return self._cover_entries
                payload=read_json(path,{})
                entries=payload.get('entries')
                if (payload.get('algorithm_version')==FINGERPRINT_ALGORITHM_VERSION
                        and payload.get('collage_version')==ALGORITHM_VERSION
                        and isinstance(entries,dict) and len(entries)<=64
                        and payload.get('checksum')==_cache_checksum(entries)):
                    self._cover_entries=entries
            except (OSError,ValueError,TypeError,AttributeError):pass
        return self._cover_entries

    def _cached_cover_match(self,card,history):
        from ref_lab.collection_history import _photo_relation,_valid_cache_value
        entry=self._cover_metadata().get(card['cover_url'])
        try:
            if (not isinstance(entry,dict) or entry.get('intrinsic')!=[card['cover_width'],card['cover_height']]):return None
            fp=entry['fingerprint'];sha=entry['duplicate_of']
            if not _valid_cache_value(fp) or fp.get('asset_sha')!=entry['preview_sha256']:return None
            original=history.records.get(sha)
            if original is None:return None
            current=history._fingerprint(Path(original['path']))
            if current['asset_sha']!=sha:return None
            relation=({'reason':'same_bytes'} if fp['asset_sha']==sha else _photo_relation(fp,current))
            if not relation or relation.get('state')=='needs_review':return None
            self.preview_payloads['metadata_hits']+=1
            return {**relation,'duplicate_of':sha,'reason':'visible_cover_matches_history',
                    'preview_match':relation['reason'],'asset_role':'discovery_preview',
                    'preview_sha256':fp['asset_sha'],'observed_cover_url':card['cover_url'],
                    'observed_intrinsic_size':entry['intrinsic'],'preview_pixel_size':entry['pixels'],
                    'preview_payload':'metadata_revalidated'}
        except (OSError,ValueError,KeyError,TypeError,AttributeError):return None

    def _remember_cover_match(self,card,history,path,match,pixels):
        from ref_lab.collection_history import FINGERPRINT_ALGORITHM_VERSION,_cache_checksum
        from ref_lab.collage import ALGORITHM_VERSION
        # Cache only content-addressed CDN URLs; every reuse rechecks the pixel relation.
        if (self.cover_cache_path is None or self.cover_cache_path.is_symlink()
                or not re.search(r'/[0-9a-f]{32,64}\.[a-z]+$',urlsplit(card['cover_url']).path)
                or match.get('reason') not in ('same_bytes','near_duplicate','crop_duplicate')
                or match.get('state')=='needs_review' or match.get('duplicate_of') not in history.records):return
        entries=self._cover_metadata()
        fp={key:value for key,value in history._fingerprint(path).items() if key!='path'}
        entries.pop(card['cover_url'],None)
        entries[card['cover_url']]={'fingerprint':fp,'preview_sha256':fp['asset_sha'],
            'duplicate_of':match['duplicate_of'],'intrinsic':[card['cover_width'],card['cover_height']],
            'pixels':list(pixels)}
        self._cover_entries=entries=dict(list(entries.items())[-64:])
        try:save(self.cover_cache_path,{'algorithm_version':FINGERPRINT_ALGORITHM_VERSION,
            'collage_version':ALGORITHM_VERSION,'entries':entries,'checksum':_cache_checksum(entries)})
        except OSError:pass

    def check_duplicate(self,card,history):
        # shortcut: single primary-image Pins only; revisit when Pin galleries are collected.
        # The previous card's payload never outlives its own decision.
        self._discard_preview()
        page=urlsplit(card.get('page',''));url=card.get('cover_url','');parsed=urlsplit(url)
        if (page.scheme!='https' or page.username or page.password or page.hostname not in ('pinterest.com','www.pinterest.com')
                or not re.fullmatch(r'/pin/\d+/?',page.path) or parsed.scheme!='https' or parsed.username or parsed.password
                or not (parsed.hostname=='pinimg.com' or (parsed.hostname or '').endswith('.pinimg.com'))
                or min(card.get('cover_width',0),card.get('cover_height',0))<200):return None
        # A cover address that the library already received, with a verified
        # SHA behind it, is a known repeat: no bytes have to be transferred to
        # say so. It says nothing about the other images of that post.
        known=getattr(self,'known_sources',None) or {}
        key=normalize_image_url(url)
        if key and key in known and known[key] in getattr(history,'records',{}):
            return {'duplicate_of':known[key],'reason':'known_source_url','source_address_precheck':True,
                    'observed_cover_url':url,'preview_payload':'not_downloaded'}
        cached=self._cached_cover_match(card,history)
        if cached:return cached
        try:
            with httpx.stream('GET',url,timeout=5,follow_redirects=False) as response:
                response.raise_for_status();content=bytearray()
                for chunk in response.iter_bytes():
                    content.extend(chunk)
                    if len(content)>2*1024*1024:raise ValueError('Discovery preview exceeds limit')
            raw=bytes(content);sha=hashlib.sha256(raw).hexdigest()
            with Image.open(io.BytesIO(raw)) as image:
                # naturalWidth/Height are density-corrected CSS pixels, not received pixel counts.
                if (abs((image.width/image.height)/(card['cover_width']/card['cover_height'])-1)>.01 or image.width*image.height>40_000_000
                        or getattr(image,'n_frames',1)!=1):return None
                pixels=image.size
                ext={'JPEG':'jpg','PNG':'png','WEBP':'webp','AVIF':'avif'}.get(image.format)
                if ext is None:return None
                image.verify()
            # The payload is temporary: it lives in the run's own staging area
            # and is removed as soon as its decision was made.
            incoming=Path(self.incoming_dir) if self.incoming_dir is not None else self.folder/'incoming'
            previews=incoming/'previews'
            if (incoming.is_symlink() or getattr(incoming,'is_junction',lambda:False)()
                    or incoming.resolve()!=self.folder.resolve()/'incoming'):return None
            if previews.is_symlink() or getattr(previews,'is_junction',lambda:False)():return None
            previews.mkdir(parents=True,exist_ok=True)
            if previews.is_symlink() or not previews.resolve().is_relative_to(self.folder.resolve()):return None
            self._preview_root=previews.resolve()
            path=previews/(uuid4().hex+'.'+ext)
            with path.open('xb') as stream:stream.write(raw)
            self.preview_payloads['created']+=1
            self._preview_owned=path.resolve()
            self.preview={'url':url,'sha':sha,'path':str(path.resolve())}
            match=history.match(path)
            if match:
                self._remember_cover_match(card,history,path,match,pixels)
                # The verdict is recorded; the payload is not kept for later.
                self._discard_preview()
                return {**match,'reason':'visible_cover_matches_history','preview_match':match['reason'],
                             'asset_role':'discovery_preview','preview_sha256':sha,
                             'preview_payload':'temporary_removed',
                             'observed_cover_url':url,'preview_pixel_size':list(pixels),
                             'observed_intrinsic_size':[card['cover_width'],card['cover_height']]}
        except (OSError,ValueError,httpx.HTTPError,Image.DecompressionBombError):
            self._discard_preview()
            return None
        return None

    def _discard_preview(self):
        """Remove the temporary preview payload; the evidence keeps its SHA."""
        preview=self.preview
        self.preview=None
        if not preview:return
        try:
            path=Path(preview.get('path') or '')
            if path!=self._preview_owned:return
            # Only this run's own staging payload is removed; an unrelated or
            # externally owned path is never touched.
            if (not self._preview_root or self._preview_root.is_symlink()
                    or getattr(self._preview_root,'is_junction',lambda:False)()
                    or self._preview_root.resolve()!=(self.folder/'incoming/previews').resolve()
                    or path.parent!=self._preview_root):return
            if path.is_file() and not path.is_symlink() and path.stat().st_nlink==1:
                if hashlib.sha256(path.read_bytes()).hexdigest()!=preview.get('sha'):return
                size=path.stat().st_size
                path.unlink()
                self.preview_payloads['removed']+=1
                self.preview_payloads['bytes']+=size
                self._preview_owned=None
        except (OSError,ValueError):
            pass

    def receive(self,card,step):
        page=card['page'];source=step['source']
        query=str(step.get('query') or getattr(self,'active_query','') or '')
        self.return_failed=False;self.return_error=None;self.return_issue_category=None
        entered_detail=source!='xiaohongshu'
        left_search_page=False
        try:
            if source=='xiaohongshu':
                match=re.search(r'/(?:explore|search_result)/([a-f0-9]{24})',urlsplit(page).path)
                if not match:return []
                note=match.group(1)
                opened=False
                with self._span('detail_click',source=source):
                    try:
                        self.command('click','--selector',f'a.cover[href*="{note}"]','--session',self.session)
                        opened=True
                    except DetailItemError:
                        try:
                            self.command('click','--selector',f'a[href*="{note}"]','--session',self.session)
                            opened=True
                        except DetailItemError:
                            opened=False
                used_fallback=False
                if not opened:
                    # The card left the live grid. Open the URL the search page
                    # itself exposed, once, inside this same detail attempt.
                    target=self._observed_note_url(page,note)
                    if not target:return []
                    used_fallback=True
                    try:
                        with self._span('detail_navigate',source=source):
                            self.command('navigate',target,'--session',self.session,
                                         '--wait-until','domcontentloaded','--timeout','25s')
                    except BrowserInfrastructureError:
                        # The page may or may not have moved. Nothing is assumed
                        # here: the live page below decides what happens next.
                        pass
                try:
                    with self._span('detail_dom_wait',source=source):
                        probe=self._probe_detail()
                except (ValueError,OSError,subprocess.SubprocessError):
                    # A failed read does not prove navigation stayed on the search page.
                    left_search_page=not self._search_page_confirmed(source,query)
                    raise
                probe_url=str(probe.get('url') or '')
                parsed=urlsplit(probe_url)
                host=(parsed.hostname or '').lower()
                host_ok=host=='xiaohongshu.com' or host.endswith('.xiaohongshu.com')
                landed=re.search(r'/(?:explore|search_result)/([a-f0-9]{24})',parsed.path)
                if probe.get('login_required') or probe.get('challenge'):
                    raise SourceBlocked('登录或验证门槛')
                if used_fallback:
                    if parsed.path.rstrip('/')=='/search_result':
                        # The navigation may have timed out without moving.
                        if self._search_page_confirmed(source,query):
                            # Still the same source, query and session with
                            # visible cards: keep the failure, capture nothing
                            # and do not step back into an unrelated page.
                            left_search_page=False
                            return []
                        left_search_page=True
                        return []
                    left_search_page=True
                    if probe.get('not_found') or '/404' in probe_url:
                        self.return_failed=True
                        return []
                    if not host_ok or not landed or landed.group(1)!=note:
                        # A foreign page or another note is never captured.
                        return []
                    if probe.get('body_ready') is not True:
                        # The page never became readable: it proves nothing.
                        raise DetailItemError('Detail page read failed',code='detail_read_failed')
                    entered_detail=True
                else:
                    if probe.get('not_found') or '/404' in probe_url:
                        self.return_failed=True
                        return []
                    if probe.get('body_ready') is False:
                        raise DetailItemError('Detail page read failed',code='detail_read_failed')
                    entered_detail=bool(re.fullmatch(r'/(?:explore|search_result)/[a-f0-9]{24}',parsed.path))
                    if not entered_detail:raise ValueError('Note did not open; search page preserved')
                canonical='https://www.xiaohongshu.com/explore/'+note
                errors=[]
                rows=capture_note(self.bsk,self.session,self.folder,canonical,
                                  limit=getattr(self,'note_image_limit',3),errors=errors,
                                  timing=getattr(self,'timing',None),command=self.command,
                                  deadline=getattr(self,'deadline',float('inf')),
                                  known_shas=getattr(self,'known_shas',None),
                                  known_sources=getattr(self,'known_sources',None),
                                  incoming=getattr(self,'incoming_dir',None))
                self.download_errors=getattr(self,'download_errors',[])+errors
                return rows
            # Navigation and DOM are timed inside the adapter; an outer span here
            # duplicated the same stage name and made a naive sum double count it.
            detail=fetch_pinterest_detail_metadata(self.bsk,self.session,page,self.env,
                                                   timing=getattr(self,'timing',None),command=self.command)
            if detail.get('is_login_wall'):raise SourceBlocked('登录门槛')
            url=detail.get('image_url')
            if not url:return []
            author_detail={'title':detail.get('title',''),'description':detail.get('desc','')}
            source_key=normalize_image_url(url)
            known_sources=getattr(self,'known_sources',None)
            if known_sources and source_key and source_key in known_sources:
                return [{'asset_sha':known_sources[source_key],'page_url':page,'image_url':url,
                         'duplicate':True,'reason':'known_source_url',
                         'author_detail':author_detail,
                         'source_text':detail.get('title','')+'\n'+detail.get('desc','')}]
            with self._span('detail_download',source=source):
                raw,width,height,fmt,reused=self._pinterest_bytes(url)
            ext={'JPEG':'jpg','PNG':'png','WEBP':'webp','AVIF':'avif'}.get(fmt)
            if ext is None:return []
            sha=hashlib.sha256(raw).hexdigest()
            known_shas=getattr(self,'known_shas',None)
            if known_shas is not None and sha in known_shas:
                return [{'asset_sha':sha,'page_url':page,'image_url':url,'duplicate':True,
                         'reason':'same_bytes_known','bytes_received':len(raw),
                         'width':width,'height':height,
                         'author_detail':author_detail,
                         'source_text':detail.get('title','')+'\n'+detail.get('desc','')}]
            incoming=getattr(self,'incoming_dir',None)
            temp_dir=Path(incoming) if incoming is not None else self.folder/'incoming'
            temp_dir.mkdir(parents=True,exist_ok=True)
            temporary=temp_dir/(uuid4().hex+'.part')
            with temporary.open('xb') as stream:stream.write(raw)
            return [{'asset_sha':sha,'original_path':str(temporary.resolve()),'page_url':page,'image_url':url,
                     'source_text':detail.get('title','')+'\n'+detail.get('desc',''),'width':width,'height':height,
                     'author_detail':author_detail,
                     'ext':ext,'temporary':True,'bytes_received':len(raw),'preview_bytes_reused':reused}]
        finally:
            self._discard_preview()
            # Restore the same search page; do not start another query or inspect a related feed.
            navigate_error=None
            if entered_detail or left_search_page:
                try:
                    with self._span('detail_return',source=source):
                        self._go_back()
                except (ValueError,OSError,subprocess.SubprocessError) as exc:
                    navigate_error=exc
                    self.return_failed=True
                    # Separate a slow/SPA page return from a real connection fault.
                    self.return_issue_category=('page_return'
                        if getattr(exc,'is_timeout',False) else 'connection')
                    if is_infrastructure_error(exc):self.return_error=exc
            if entered_detail or left_search_page:
                evidence=None
                for attempt in range(3):
                    try:
                        restored=self.snapshot()
                        evidence=self._return_state(restored,source,query)
                    except (ValueError,OSError,subprocess.SubprocessError,KeyError) as exc:
                        evidence={'confirmed':False,'stage':'after_history_back','error':type(exc).__name__,
                                  'source':source,'query':query,'session_id':self.session}
                        self.return_failed=True
                        self.return_issue_category=self.return_issue_category or 'connection'
                        if is_infrastructure_error(exc) and self.return_error is None:self.return_error=exc
                    if evidence.get('confirmed'):break
                    if attempt<2:
                        remaining=getattr(self,'deadline',float('inf'))-time.monotonic()
                        if remaining<=0:break
                        time.sleep(min(0.7,remaining))
                evidence['stage']='after_history_back'
                evidence['return_attempts']=attempt+1
                evidence['navigate_back_error']=(type(navigate_error).__name__ if navigate_error is not None else None)
                self._record_return_check(evidence)
                if evidence.get('confirmed'):
                    # The original operation did succeed: the page is the same
                    # source, the same query, with visible results, in this
                    # session. A stale timeout error must not stop the Job later.
                    self.return_failed=False
                    self.return_issue_category=None
                    if self.return_error is not None:
                        recovered=getattr(self,'return_recovered',[])
                        recovered.append({'action':'navigate-back','code':getattr(self.return_error,'code',''),
                                          'stage':'verified_live_page','at':time.time()})
                        self.return_recovered=recovered
                        self.return_error=None
                else:
                    self.return_failed=True
                    if self.return_error is None:
                        self.return_error=BrowserInfrastructureError(
                            '返回搜索页未确认',action='navigate-back',code='return_unconfirmed',
                            details=f'source={source} cards={evidence.get("cards")} query_ok={evidence.get("url_query") or evidence.get("search_box")}')
                        self.return_issue_category=self.return_issue_category or 'page_return'

    def _pinterest_bytes(self,url):
        """Download the Pin's primary image, reusing the preview we already fetched.

        ``check_duplicate`` streams the visible cover before history comparison.
        When the detail page reports the very same URL, re-downloading identical
        bytes is pure duplication; the stored preview is verified by SHA instead.
        """
        preview=self.preview
        if preview and preview.get('url')==url:
            try:
                raw=Path(preview['path']).read_bytes()
                if hashlib.sha256(raw).hexdigest()==preview['sha']:
                    with Image.open(io.BytesIO(raw)) as image:
                        image.load();width,height=image.size;fmt=image.format
                    self.preview_reused+=1
                    # The bytes are in memory now; the temporary payload is not
                    # kept for the rest of the Job.
                    self._discard_preview()
                    return raw,width,height,fmt,True
            except (OSError,ValueError,Image.DecompressionBombError):
                pass
        with httpx.stream('GET',url,timeout=15,follow_redirects=False) as response:
            response.raise_for_status();content=bytearray()
            for chunk in response.iter_bytes():
                content.extend(chunk)
                if len(content)>20*1024*1024:raise ValueError('Image exceeds size limit')
        raw=bytes(content)
        with Image.open(io.BytesIO(raw)) as image:
            image.load();width,height=image.size;fmt=image.format
        return raw,width,height,fmt,False

    def close(self):
        started=time.monotonic()
        old_deadline=getattr(self,'deadline',float('inf'))
        self.deadline=(min(old_deadline,started+10) if self.recovery_active else started+10)
        self._cleanup_active=True
        state='cleanup_pending'
        try:
            # A temporary preview payload never outlives the browser.
            self._discard_preview()
            if self.start_request:
                cancelled=json.loads(self.command('session','request',self.start_request,'--cancel','--json',timeout=10))
                if cancelled.get('state')!='closed' or cancelled.get('cleanup_error'):
                    raise BrowserInfrastructureError('会话请求清理尚未确认',action='session',code='cleanup_pending')
                self.start_request=None
            if self.session:
                try:
                    self.command('session','stop',self.session,timeout=10)
                except BrowserInfrastructureError as exc:
                    if exc.code not in ('session_not_found', 'not_found') and not getattr(exc, 'is_session_dead', False):
                        raise
                self.session=None
            state='closed'
        except AgentUnavailable as exc:
            raise BrowserInfrastructureError('会话清理时间预算已用尽',action='session',code='cleanup_pending') from exc
        finally:
            finished=time.monotonic()
            self.deadline=old_deadline
            self._cleanup_active=False
            save(self.folder/'browser-session.json',{'browser_id':self.browser_id,'state':state,
                 'session_id':self.session,'start_request':self.start_request,
                 'cleanup':{'elapsed_seconds':max(0.,finished-started),
                            'grace_allowed':not self.recovery_active,
                            'grace_seconds':max(0.,finished-max(started,old_deadline))}})


def restore_history_index(history, folder, received) -> dict:
    """Restore this Job's verified originals *and* valid tiles into the index.

    Called before any download decision, including on a resumed run. Reusing an
    already-processed record is fine; skipping the index restore is not, because
    then a repeat could be admitted as a new independent photo.
    """
    result = {'originals': 0, 'children': 0, 'errors': []}
    if history is None:
        return result
    from ref_lab.collage import DerivedStore, VALID, record_is_current
    from ref_lab.collection_counts import _child_ok
    records = DerivedStore(folder).items()
    for row in received:
        try:
            history.consider(Path(row['original_path'])); result['originals'] += 1
        except (OSError, ValueError) as exc:
            result['errors'].append({'asset_sha': row['asset_sha'], 'stage': 'original',
                                     'error': type(exc).__name__})
        record = records.get(row['asset_sha'])
        if not record_is_current(record):
            continue
        for child in record.get('children') or []:
            if not isinstance(child, dict) or child.get('status') != VALID:
                continue
            if not _child_ok(folder, child, row['asset_sha']):
                continue
            try:
                history.consider(Path(child['path'])); result['children'] += 1
            except (OSError, ValueError) as exc:
                result['errors'].append({'asset_sha': child.get('child_sha', ''),
                                         'stage': 'child', 'error': type(exc).__name__})
    return result


def _merge_repeat_evidence(by_sha,card,row,*,names,work_terms,other_terms):
    """Fold the evidence of a repeat into the photo this Job already holds.

    A repeat is not a new photo, so its bytes are not downloaded again and it
    is not counted twice. But the new source can name the character or warn
    about the picture, and that evidence belongs to the photo: it is merged
    into the received row, whose own evidence stays in the trail. A photo the
    library already owned is never turned into a new one here.
    """
    sha=row.get('asset_sha')
    if not sha or sha not in by_sha:return False
    from ref_lab.search_relevance import associate_detail
    updated=associate_detail(card,row,names=names,work_terms=work_terms,other_terms=other_terms)
    existing=by_sha[sha]
    trail=existing.setdefault('discovery_evidence_history',[])
    if not trail:trail.append(existing.get('relevance',{}))
    trail.append(updated)
    if is_confirmed({'relevance':updated}) and not is_confirmed(existing):existing['relevance']=updated
    return True


def collect(job:dict,agent,browser,folder:Path,*,history=None,workers=1,finalize_only=False,
            search_only=False)->tuple[dict,dict[str,bytes]]:
    project={**job['project_snapshot'],'notes':job.get('notes','')}
    requested=int(job.get('target_count') or 12)
    extra_target=int(job.get('search_extra_target') or 0)
    requested_total=requested+max(0,extra_target)
    target=min(requested_total,100)
    agent.candidate_limit=min(MAX_IMAGES,max(24,target*3) if search_only else max(20,target*2))
    query_budget=MAX_GOAL_QUERIES if search_only and job.get('goal_id') else MAX_QUERIES
    sources=job.get('preferred_sources',['xiaohongshu','pinterest'])
    try:state=load_checkpoint(folder,job,getattr(agent,'model',agent.producer))
    except (OSError,ValueError,KeyError,TypeError) as exc:raise AgentUnavailable('恢复绑定或原图完整性检查失败：'+str(exc)) from exc
    if finalize_only and not state.get('final_manifest'):
        raise AgentUnavailable('本地收尾缺少已封存的最终判断；不启动新的外部调用。')
    received=state['received'];audit=state['audit'];queries=state['queries'];checks=state['checks']
    pages=set(state['pages']);page_attempts=state['page_attempts'];searches=state['searches']
    duplicates=state['duplicates'];collisions=state['collisions'];gaps=state['gaps']
    pages={_post_key('https://'+key) for key in pages}
    normalized_attempts={}
    for key,value in page_attempts.items():
        normalized=_post_key('https://'+key)
        normalized_attempts[normalized]=normalized_attempts.get(normalized,0)+value
    page_attempts=normalized_attempts
    details=state['details'];windows=state['windows'];steps=state.get('steps',[])
    previous_elapsed=max(float(state.get('elapsed_seconds_total') or 0.0),
                         float(job.get('search_elapsed_seconds') or 0.0))
    continue_info=None
    candidates=[];images={};seen={r['asset_sha'] for r in received};blocked=False;stop_reason='';interrupted=False;kept=0
    reviewed=sum(bool(r.get('review')) for r in audit);attempted=len(received)
    by_sha={r['asset_sha']:r for r in received}
    # Restore the whole known set before any download decision: originals and
    # already-verified tiles of this Job, so a resumed run cannot re-admit a
    # repeat as a new independent photo.
    history_restore=restore_history_index(history,folder,received)
    for record in audit:
        if not record.get('review'):continue
        value=CollectionVision.model_validate(record['review']);row=by_sha[record['asset_sha']]
        refs=record.get('references',state.get('references',[]))
        if value.asset_sha!=row['asset_sha'] or value.context_sha!=scope_sha(project):raise AgentUnavailable('已完成判断的图像/条件绑定改变。')
        if record['accepted']:
            if not accepted(value,project,references=refs):raise AgentUnavailable('旧准入不再满足原规则。')
            candidate=record.get('candidate') or verified_candidate(row,value,project,refs,row.get('search_query',''),row.get('discovery_url',''))
            candidates.append(candidate);images[Path(candidate['file']).name]=original_bytes(row,folder)
    if search_only:
        if state.get('final_manifest'):
            # A historical full-review run is not a quick-search checkpoint; refuse to mix modes.
            raise AgentUnavailable('该 Job 已有正式审核交付；快速搜图不覆盖旧结果，请新建任务。')
        saved_summary=read_json(folder/'search-summary.json',{})
        summary_exists=isinstance(saved_summary,dict) and bool(saved_summary)
        resume_generation=int(job.get('search_resume_generation',0))
        replenishing=resume_generation>int(state.get('search_resume_generation',0))
        if state.get('search_complete') and summary_exists and not extra_target and not replenishing:
            if saved_summary.get('stop_reason') in ('browser_unavailable','sources_blocked') and len(received)<target:
                state['search_complete']=False
            else:
                return saved_summary,{}
        if extra_target or replenishing:
            # Same job, additional target. The local dicts are the objects that
            # ``checkpoint`` persists, so every reset must mutate them in place:
            # rebinding ``state['searches']`` alone silently restored the old
            # ``done=True`` flags on the next save. Originals, human decisions,
            # duplicate/error logs and cumulative budget counters stay untouched.
            previous_target=(int(saved_summary.get('effective_target') or saved_summary.get('target') or 0)
                             if summary_exists else 0)
            if summary_exists and previous_target>=target and not replenishing:
                return saved_summary,{}
            state['search_complete']=False;state['search_summary']={}
            state['search_attempts']=int(state.get('search_attempts',0))+1
            state.setdefault('search_attempt_history',[]).append({'searches':json.loads(json.dumps(searches)),
                'pages':sorted(pages),'queries':list(queries),'at':time.time(),
                'resume_generation':int(state.get('search_resume_generation',0))})
            searches.clear();pages.clear()
            state['search_resume_generation']=resume_generation
            blocked_by=''
            if time.monotonic()>=getattr(agent,'deadline',float('inf'))-30:
                blocked_by='time_budget_exhausted'
            elif details>=MAX_DETAIL_PAGES:
                blocked_by='detail_budget_exhausted'
            elif len(received)>=agent.candidate_limit:
                blocked_by='candidate_budget_exhausted'
            continue_info={'attempt_index':state['search_attempts'],'extra_target':extra_target,
                           'previous_target':previous_target,'target':target,
                           'confirmed_at_start':confirmed_count(received),
                           'queries_before':len(queries),'blocked_by':blocked_by}
            gaps.append('继续补足/加搜：目标 %s 张；本次显式预算与累计消耗分别保留。' % target)
    if state.get('final_manifest') and (finalize_only or state.get('terminal',state.get('outcome')=='complete')):
        manifest=state['final_manifest'];CandidatePackage.model_validate(manifest)
        if manifest['candidates']!=candidates:raise AgentUnavailable('封存交付与原准入记录不一致。')
        save(folder/'manifest.json',manifest);render_result(folder,manifest,images)
        return manifest,images
    if state.get('final_manifest'):
        previous=state.pop('final_manifest')
        key=hashlib.sha256(json.dumps(previous,sort_keys=True,ensure_ascii=False).encode()).hexdigest()
        save(folder/f'manifest-{key}.json',previous)
        state['outcome']='running';gaps.clear()
        for key,search in searches.items():
            if checks.get(search['source'],{}).get('status') in ('blocked','login_required'):
                search.update(done=False,usable=False,observed=False)
        checks={k:v for k,v in checks.items() if v.get('status') not in ('blocked','login_required')}
    if hasattr(agent,'candidate_calls'):agent.candidate_calls=max(agent.candidate_calls,state.get('candidate_calls',0))
    started=time.monotonic()
    timing=getattr(agent,'timing',None) or CollectionTiming(folder)
    if hasattr(browser,'timing'):browser.timing=timing
    collage_worker=None
    type_worker=None
    collage_closed=False
    if search_only:
        from ref_lab.collage import CollageWorker
        if (folder/'goal.json').exists():
            from ref_lab.photo_types import PhotoTypeWorker
            type_worker=PhotoTypeWorker(folder,limit=min(MAX_IMAGES,max(20,target*2)),model=agent.model,history=history,deadline=getattr(agent,'deadline',float('inf'))-5)
        collage_worker=CollageWorker(folder,history=history,known_shas=seen,
                                     on_record=type_worker.enqueue if type_worker else None)
        # A resumed run must finish local processing for originals received before
        # the interruption; already-completed records are reused, not reprocessed.
        for existing in list(received):
            collage_worker.enqueue(existing)
    pending=OrderedReviews(agent,project,workers=workers) if not search_only else None
    first_usable=state.get('first_usable');displayed=-1;displayed_received=-1
    received_errors=state.get('search_errors',[]) if search_only else []
    calls=lambda:getattr(agent,'candidate_calls',attempted)
    name_records=[{"name":str(project.get('character') or '').strip(),
                   "language":'',"source":"project_character"}]
    work_terms=[str(project.get('work') or '').strip()]
    other_terms=[]
    skipped={'other_character':0,'non_photo':0,'exploration_budget':0}
    canonical_cache={'key':None,'value':None}
    qualified_initial=True
    qualified_resumed=bool(received) or 'qualified_timeline' in state
    def canonical_counts(force=False):
        """The one count used by the stop condition, summary and counts.json."""
        from ref_lab.collage import DerivedStore
        from ref_lab.collection_counts import compute
        stamps=[]
        for filename in ('derived.json','photo-types.json','photo-audit.json'):
            try:
                stat=(folder/filename).stat();stamps.append((stat.st_size,stat.st_mtime_ns))
            except OSError:stamps.append((0,0))
        key=(len(received),tuple(stamps),tuple((is_confirmed(r),bool(source_warnings(r))) for r in received))
        if force or canonical_cache['key']!=key or canonical_cache['value'] is None:
            canonical_cache['value']=compute(folder,received,DerivedStore(folder).items())
            canonical_cache['key']=key
        return canonical_cache['value']
    def confirmed():
        return canonical_counts()['target_progress'] if search_only else len(candidates)
    def exploration():
        return exploration_count(received) if search_only else 0
    def pending_qualifications(counts):
        pending=int(getattr(getattr(collage_worker,'_queue',None),'unfinished_tasks',0))
        if type_worker is not None:
            pending+=int(getattr(type_worker.pending,'unfinished_tasks',0))
            pending=max(pending,int(counts.get('type_pending',0))+int(counts.get('history_pending',0)))
        return pending
    def limit_reason():
        if search_only:
            if confirmed()>=target:return 'target_reached'
            if type_worker is not None and type_worker.blocked:return getattr(type_worker,'block_reason','') or 'model_unavailable'
            if time.monotonic()>=getattr(agent,'deadline',float('inf'))-30:return 'time_budget_exhausted'
            if len(received)>=agent.candidate_limit:return 'candidate_budget_exhausted'
            if details>=MAX_DETAIL_PAGES:return 'detail_budget_exhausted'
            return ''
        if len(candidates)>=target and coverage(steps,searches,sources)['explored']:return 'soft_target_reached'
        if time.monotonic()>=getattr(agent,'deadline',float('inf'))-30:return 'time_budget_exhausted'
        if len(candidates)<target and (len(received)>=agent.candidate_limit or calls()>=agent.candidate_limit):return 'visual_budget_exhausted'
        if len(candidates)<target and details>=MAX_DETAIL_PAGES:return 'detail_budget_exhausted'
        return ''
    def checkpoint(phase='collecting'):
        nonlocal displayed,displayed_received,qualified_initial
        if not search_only:
            warned={'verified-'+row['asset_sha'][:20] for row in received if source_warnings(row)}
            for candidate in list(candidates):
                if candidate['id'] in warned:
                    candidates.remove(candidate)
                    images.pop(Path(candidate['file']).name,None)
                    gap='来源含AI生成内容提示；该图保留原件与视觉回执，待人工确认：'+candidate['id']
                    if gap not in gaps:gaps.append(gap)
        state.update(received=received,audit=audit,queries=queries,checks=checks,pages=sorted(pages),page_attempts=page_attempts,
                     searches=searches,duplicates=duplicates,collisions=collisions,gaps=gaps,details=details,windows=windows,
                     first_usable=first_usable,candidate_calls=calls(),references=getattr(agent,'references',None) or [],steps=steps,phase=phase)
        if search_only:state['search_errors']=received_errors
        if search_only:
            attempt=(os.environ.get('LAB_COLLECTION_ATTEMPT_ID') if os.environ.get('LAB_COLLECTION_JOB_ID')==job['id']
                     else job.get('search_attempt_id') or job.get('active_attempt_id'))
            collector_elapsed=time.monotonic()-started
            cumulative=previous_elapsed+max(collector_elapsed,
                time.time()-job['search_attempt_started_at'] if isinstance(job.get('search_attempt_started_at'),(int,float)) else 0.)
            timing.qualified_checkpoint(state,canonical_counts(),job_id=job['id'],attempt_id=attempt,
                collector_elapsed=collector_elapsed,cumulative_elapsed=cumulative,
                initial=qualified_initial,resumed=qualified_resumed)
            qualified_initial=False
        reference_files=state.setdefault('reference_files',{})
        for path in (folder/'reference-research').glob('source-*.*'):
            if path.suffix in ('.html','.json'):reference_files[str(path.relative_to(folder))]=hashlib.sha256(path.read_bytes()).hexdigest()
        save(folder/'collector-state.json',state)
        save(folder/'visual-audit.json',audit)
        model_calls,reported_tokens,reported_calls=_attempt_usage(folder)
        from ref_lab.agent_collection import _owner_record
        save(folder/'progress.json',{'phase':phase,'stop_reason':stop_reason,'soft_target':target,
             'job_id':job['id'],'attempt_id':(os.environ.get('LAB_COLLECTION_ATTEMPT_ID')
                 if os.environ.get('LAB_COLLECTION_JOB_ID')==job['id'] else
                 job.get('search_attempt_id') or job.get('active_attempt_id')),
             'owner':(_owner_record(os.getpid(),phase='recovering') if phase=='browser_recovering' else None),
             'accepted':len(candidates),'received':len(received),'reviewed':reviewed,'duplicates':len(duplicates),
             'queries':len(queries),'visible_windows':windows,'detail_pages':details,
             'vision_cli_calls':model_calls if search_only else getattr(agent,'vision_cli_calls',calls()),
             'model_calls':model_calls,'tokens':reported_tokens,'usage_complete':reported_calls==model_calls,
             'wall_seconds':round(time.monotonic()-started,3),
             'first_usable_seconds':first_usable,'pending_reviews':len(pending) if pending is not None else 0,'vision_workers':workers,
             'browser_errors':collection_queue.read_json(folder/'browser-errors.json',[])[-20:],
             'search_only':bool(search_only),'outcome':state.get('outcome','running'),'coverage':coverage(steps,searches,sources)})
        if search_only:
            if displayed_received!=len(received) or phase=='finished':
                render_search_gallery(folder,received,running=phase!='finished')
                displayed_received=len(received)
        elif displayed!=len(candidates) or phase=='finished':
            render_result(folder,{'candidates':candidates,'execution_report':{'summary':'任务'+('已停止：'+stop_reason if phase=='finished' else '仍在运行'),
                          'gaps':gaps}},images,running=phase!='finished')
            displayed=len(candidates)

    def record_review(entry):
        for i,old in enumerate(audit):
            if old['asset_sha']==entry['asset_sha']:
                if old.get('review'):raise AgentUnavailable('已完成判断不可重复提交。')
                entry['previous_execution_errors']=[*old.get('previous_execution_errors',[]),old.get('execution_error','')]
                audit[i]=entry;return
        audit.append(entry)

    def finish_one():
        nonlocal reviewed,blocked,kept,first_usable
        row=pending.pending[0][0];sha=row['asset_sha']
        try:
            _,result,references=pending.take()
            if result.asset_sha!=sha or result.context_sha!=scope_sha(project):
                raise AgentCallFailed('input_binding_changed',fatal=True)
            raw=Path(row['original_path']).read_bytes()
            if hashlib.sha256(raw).hexdigest()!=result.asset_sha:
                raise AgentCallFailed('input_binding_changed',fatal=True)
        except (AgentUnavailable,OSError,ValueError) as exc:
            if not isinstance(exc,AgentUnavailable):exc=AgentCallFailed('local_input_invalid',fatal=True)
            gap='视觉执行：'+str(exc)
            if gap not in gaps:gaps.append(gap)
            blocked=True
            record_review({'asset_sha':sha,'source_page':row['page_url'],'review':None,'accepted':False,
                          'decision':'NEEDS_EVIDENCE','execution_error':str(exc)})
            checkpoint()
            if fatal_visual_error(exc):raise exc
            return
        reviewed+=1
        valid=accepted(result,project,references=references)
        verdict='CONFIRMED' if valid else ('MISMATCH' if result.kind not in ('cosplay_photo','portrait_photo','unknown') or (result.identity=='match' and result.costume=='mismatch' and reference_supported(result,references)) else 'NEEDS_EVIDENCE')
        record={'asset_sha':sha,'source_page':row['page_url'],'review':result.model_dump(),'accepted':valid,'decision':verdict,
                'reference_shas':[r['asset_sha'] for r in references],'references':references}
        timing.event('review_committed',asset_sha=sha,accepted=valid)
        if valid:
            filename=Path(row['original_path']).name
            candidate=verified_candidate(row,result,project,references,row.get('search_query',''),row.get('discovery_url',''))
            candidates.append(candidate);record['candidate']=candidate
            images[filename]=raw;kept+=1
            if first_usable is None:
                first_usable=time.monotonic()-timing.started
                timing.event('first_usable',asset_sha=sha)
        record_review(record);checkpoint()

    def drain():
        while pending:finish_one()
    known_sources={}
    try:
        checkpoint('planning')
        from ref_lab.verified_collection import NamePlan,deterministic_plan
        if search_only:
            current_plan=deterministic_plan(project, identity_context=job.get('identity_context'),
                                            user_aliases=job.get('search_aliases') or ())
            if state.get('plan'):
                plan=NamePlan.model_validate(state['plan'])
                origin='saved_search_plan'
                if plan != current_plan:
                    state.setdefault('name_plan_history',[]).append({'plan':state['plan'],
                        'steps':list(steps),'searches':dict(searches),'reason':'trusted_name_evidence_updated','at':time.time()})
                    previous=list(searches.values());searches.clear()
                    steps=query_steps(project,current_plan,sources)
                    for index,step in enumerate(steps):
                        old=next((s for s in previous if s['source']==step['source'] and s['query']==step['query']),None)
                        if old is not None:searches[str(index)]=old
                    plan=current_plan
                    origin='trusted_name_evidence_updated'
            else:
                plan=current_plan
                origin='trusted_project_names'
        else:
            with timing.span('name_plan'):
                plan=NamePlan.model_validate(state['plan']) if state.get('plan') else agent.plan(project)
            origin='agent_discovery_hypothesis'
        steps=steps or query_steps(project,plan,sources)
        if search_only and replenishing and state.get('search_attempt_history'):
            prior_searches=state['search_attempt_history'][-1]['searches'].values()
            reasons={s.get('feedback',{}).get('reason') for s in prior_searches}
            if reasons & {'history_duplicate_high','name_coverage_insufficient','non_photographic_high','no_new_results'}:
                seen_queries={(q['source'],q['query']) for q in queries}
                refined=[s for s in query_steps(project,plan,sources,intent_offset=resume_generation%4)
                         if (s['source'],s['query']) not in seen_queries]
                if refined:
                    state.setdefault('query_plan_history',[]).append({'steps':list(steps),
                        'reason':'content_feedback_refinement','feedback':sorted(r for r in reasons if r),'at':time.time()})
                    steps=refined;searches.clear();origin='content_feedback_refinement'
        state['plan']=plan.model_dump()
        if search_only:
            name_records[:] = _plan_name_records(project, plan)
            work_terms[:] = [str(project.get('work') or '').strip()]
            from ref_lab.identity import preset_for_character
            preset=preset_for_character(str(project.get('character') or ''))
            other_terms[:] = [str(item.get('name') or '') for item in (preset or {}).get('common_confusions', []) if isinstance(item, dict)]
            for row in received:
                if 'relevance' not in row:
                    row['relevance']=classify_card(row, names=name_records, work_terms=work_terms,
                                                   other_terms=other_terms)
        for source in sources:
            if source not in {s['source'] for s in steps}:checks[source]={'source':source,'status':'unavailable','detail':'本轮没有该来源的正式适配器；要求保持未满足。'}
        save(folder/'name-plan.json',{'plan':plan.model_dump(),'steps':steps,'origin':origin})
        checkpoint('searching' if search_only else 'reference_prepare')
        if not steps:raise AgentUnavailable('当前所选来源没有正式适配器；未静默改用其他来源。')
        if not search_only:
            try:
                with timing.span('reference_prepare'):agent.prepare(project,plan)
            except AgentUnavailable as exc:
                gaps.append('参照阶段：'+str(exc))
                if fatal_visual_error(exc):raise
            agent.references=agent.references or []
        checkpoint()
        if not search_only:
            completed={r['asset_sha'] for r in audit if r.get('review')}
            for row in received:
                if row['asset_sha'] in completed:continue
                while len(pending)>=workers:finish_one()
                pending.submit(row)
                if workers==1:finish_one()
            drain();checkpoint()
        browser.deadline=getattr(agent,'deadline',float('inf'))-30
        try:
            with timing.span('browser_start'):browser.start()
        except BrowserInfrastructureError:
            checkpoint('browser_recovering')
            try:
                if not (hasattr(browser,'recover') and browser.recover()):raise
            finally:checkpoint()
        known_sources=_known_image_sources(history,folder)
        seen_posts=set(getattr(history,'seen_posts',set()))
        for row in received:
            seen_posts.add(_post_key(row.get('page_url')))
        for name,value in (('known_shas',getattr(history,'known_shas',None) if history is not None else None),
                           ('known_sources',known_sources),('incoming_dir',folder/'incoming')):
            if hasattr(browser,name):setattr(browser,name,value)
        if known_sources:state['known_source_images']=len(known_sources)
        latest_fallback_sources=set()
        total_steps=min(len(steps),query_budget)
        max_passes=2*total_steps
        pass_index=0
        poor_streak=0
        while True:
            refine_due=pass_index>=max_passes
            if (not refine_due and search_only and job.get('goal_id') and total_steps<query_budget
                    and poor_streak>=2 and coverage(steps,searches,sources)['explored'] and not limit_reason()):
                # Two low-yield queries in a row are enough evidence to change
                # direction; waiting for every planned query to repeat first only
                # re-downloads known duplicates.
                refine_due=True
            if refine_due:
                if not (search_only and job.get('goal_id') and total_steps<query_budget and not limit_reason()):
                    break
                known={(step['source'],step['query']) for step in steps}
                fresh=[]
                for offset in range(1,4):
                    fresh=[step for step in query_steps(project,plan,sources,intent_offset=offset)
                           if (step['source'],step['query']) not in known
                           and checks.get(step['source'],{}).get('status') not in ('login_required','blocked')]
                    if fresh:break
                if not fresh:break
                productive={entry['source'] for entry in searches.values()
                            if entry.get('feedback',{}).get('qualified_gain',0)>0}
                fresh.sort(key=lambda step:step['source'] not in productive)
                fresh=fresh[:query_budget-total_steps]
                state.setdefault('query_plan_history',[]).append({'reason':'automatic_goal_refinement',
                    'steps':list(steps),'added_steps':fresh,'at':time.time(),
                    'attempt_id':job.get('active_attempt_id')})
                pass_index=total_steps
                steps.extend(fresh);total_steps=len(steps);max_passes=2*total_steps
                save(folder/'name-plan.json',{'plan':plan.model_dump(),'steps':steps,'origin':'automatic_goal_refinement'})
                checkpoint()
            step_index=pass_index%total_steps;step=steps[step_index]
            source=step['source'];query=step['query']
            search=searches.setdefault(str(step_index),{'source':source,'query':query,'language':step.get('language','unknown'),
                                                      'observed':False,'usable':False,'window':0,'done':False,
                                                      'sort_mode':'relevance'})
            if search.get('done'):
                pass_index+=1;continue
            if checks.get(source,{}).get('status') in ('login_required','blocked'):
                pass_index+=1;continue
            if source=='xiaohongshu' and source in latest_fallback_sources and not search.get('latest_fallback_used'):
                search['sort_mode']='latest';search['latest_fallback_used']=True
            sort_mode=search.get('sort_mode','relevance')
            stop_reason=limit_reason()
            if stop_reason:break
            kept=0;reason='';before=len(candidates)
            feedback_before={'duplicates':len(duplicates),'received':len(received),
                             'qualified':confirmed(),
                             'rejected':canonical_counts().get('type_rejected',0),'details':len(state.get('operation_errors',[]))}
            should_advance=True
            snapshot={}
            try:
                restored_window=search.get('window',0)
                for window in range(restored_window,MAX_WINDOWS):
                    stop_reason=limit_reason()
                    if stop_reason:break
                    if window and not hasattr(browser,'more'):break
                    restored=window==restored_window and search.get('snapshot') is not None
                    with timing.span('browser_resume_navigation' if restored else ('browser_search' if window==0 else 'browser_more')):
                        if window==restored_window:
                            snapshot=(browser.search(step,sort=sort_mode)
                                      if getattr(browser,'supports_sort',False) else browser.search(step))
                            for _ in range(window):
                                if snapshot.get('login_required') or snapshot.get('challenge'):break
                                snapshot=browser.more(step)
                            search['resume_navigations']=search.get('resume_navigations',0)+1
                        else:snapshot=browser.more(step)
                    if not restored:windows+=1
                    search.update(window=window,snapshot=snapshot,observed=True)
                    save(folder/f'search-{step_index+1}-window-{window+1}.json',snapshot)
                    checkpoint()
                    assessment=assess_search(snapshot,query,{'character':project['character'],
                        'costume':project.get('costume',''),
                        'character_aliases':[record['name'] for record in name_records],
                        'costume_aliases':[project.get('costume','')] if project.get('costume') else []})
                    search['assessment']={key:value for key,value in assessment.items() if key!='action'}
                    search['scope_text_hits']=int(assessment.get('scope_text_hits',0) or 0)
                    if snapshot.get('login_required') or snapshot.get('challenge'):
                        checks[source]={'source':source,'status':'blocked','detail':'正常页面出现登录或验证门槛，已停止此来源。'}
                        reason='login_or_challenge';break
                    if assessment['action'] in ('STOP_STALE_QUERY','REVIEW_QUERY_REWRITE','CHANGE_QUERY_OR_SOURCE'):
                        reason=assessment['action'];break
                    checks[source]={'source':source,'status':'usable','detail':'实际查询正常页面；交付数量只计角色文字命中或明确标记的探索候选。'}
                    search['usable']=True;checkpoint()
                    if ((confirmed() if search_only else len(candidates)))>=target:
                        reason='target_reached' if search_only else 'coverage_checked_after_target';break
                    inspected=0;new_cards=0;window_before=len(received);kept_before=len(candidates)
                    confirmed_before=confirmed()
                    ranked=_rank_discovery_cards(snapshot.get('cards',[]),seen_posts,page_attempts,
                        names=name_records,work_terms=work_terms,other_terms=other_terms)
                    window_posts=set()
                    for card in ranked:
                        if not search_only:
                            while pending and pending.pending[0][1] is not None and pending.pending[0][1].done():finish_one()
                            while pending and len(candidates)+len(pending)>=target:finish_one()
                        stop_reason=limit_reason()
                        if inspected>=SAMPLE_PER_QUERY or stop_reason:break
                        parsed=urlsplit(card['page'])
                        if parsed.scheme!='https' or not parsed.hostname:continue
                        page_key=_post_key(card['page'])
                        if not page_key or page_key in window_posts:continue
                        window_posts.add(page_key)
                        if page_key in pages and (not search_only or page_attempts.get(page_key,0)>=3):continue
                        new_cards+=1
                        relevance=classify_card(card,names=name_records,work_terms=work_terms,
                                                other_terms=other_terms)
                        if (search_only and relevance['tier'] in ('other_character','non_photo')
                                and history is not None and hasattr(browser,'check_duplicate')):
                            known_sha=known_sources.get(normalize_image_url(card.get('cover_url')))
                            if known_sha in by_sha and known_sha in getattr(history,'records',{}):
                                duplicate=browser.check_duplicate(card,history)
                                if duplicate and duplicate.get('duplicate_of')==known_sha and duplicate.get('state')!='needs_review':
                                    _merge_repeat_evidence(by_sha,card,{'asset_sha':known_sha,'source_text':card.get('text','')},names=name_records,
                                                          work_terms=work_terms,other_terms=other_terms)
                                    save(folder/'received.json',received)
                                    duplicates.append({'page_url':card['page'],**duplicate})
                                    pages.add(page_key);checkpoint();continue
                        if search_only and relevance['tier']=='other_character':
                            skipped['other_character']+=1;pages.add(page_key);continue
                        if search_only and relevance['tier']=='non_photo' and not is_confirmed({'relevance':relevance}):
                            skipped['non_photo']+=1;pages.add(page_key);continue
                        if search_only and relevance['tier'] in ('target_context','unconfirmed'):
                            source_rows=[r for r in received if urlsplit(r.get('page_url','')).hostname==parsed.hostname]
                            query_rows=[r for r in source_rows if r.get('search_query')==query]
                            if (exploration()>=exploration_limit(target)
                                    or exploration_count(source_rows)>=max(1,(exploration_limit(target)+len(sources)-1)//len(sources))
                                    or exploration_count(query_rows)>=1):
                                skipped['exploration_budget']+=1
                                state.setdefault('deferred_cards',{})[page_key]={'reason':'exploration_budget','source':source,'query':query,'card':card}
                                continue
                        if history is not None and hasattr(browser,'check_duplicate'):
                            with timing.span('discovery_preview'):duplicate=browser.check_duplicate(card,history)
                            if duplicate:
                                current=by_sha.get(duplicate.get('duplicate_of'))
                                if current is not None and duplicate.get('state')!='needs_review':
                                    _merge_repeat_evidence(by_sha,card,{'asset_sha':current['asset_sha'],'source_text':card.get('text','')},
                                        names=name_records,work_terms=work_terms,other_terms=other_terms)
                                    current['discovery_evidence_history'][-1]['image_match']=duplicate
                                    save(folder/'received.json',received)
                                duplicates.append({'page_url':card['page'],**duplicate})
                                pages.add(page_key);save(folder/'duplicates.json',duplicates);checkpoint();continue
                        if page_attempts.get(page_key,0)>=3:
                            pages.add(page_key);gaps.append('本轮该帖详情尝试已达上限；未声称帖内图片已全部处理：'+page_key);continue
                        inspected+=1
                        state.setdefault('deferred_cards',{}).pop(page_key,None)
                        details+=1
                        page_attempts[page_key]=page_attempts.get(page_key,0)+1;per_note=0
                        state.setdefault('detail_schedule',[]).append({'page':page_key,'query':query,
                            'source':source,'window':window+1,'previously_seen':page_key in seen_posts,
                            'attempt':page_attempts[page_key],'detail_index':details})
                        seen_posts.add(page_key)
                        checkpoint()
                        try:
                            browser.note_image_limit=(min(MAX_GOAL_NOTE_IMAGES,agent.candidate_limit-len(received))
                                                      if search_only and job.get('goal_id') else 3)
                            with timing.span('browser_receive'):rows=browser.receive(card,step)
                            observation=state.setdefault('post_observations',{}).setdefault(page_key,{'images':[]})
                            observed={item['image_url']:item for item in observation['images']}
                            for row in rows:
                                if re.fullmatch(r'[0-9a-f]{64}',str(row.get('asset_sha',''))):
                                    image_url=str(row.get('image_url') or '')
                                    observed[image_url]={'image_url':image_url,'asset_sha':row['asset_sha']}
                            observation.update(images=list(observed.values()),last_observed_at=time.time(),
                                attempts=page_attempts[page_key],coverage='partial_or_unknown')
                        except SourceBlocked:
                            checks[source]={'source':source,'status':'blocked','detail':'已停止受登录/验证限制的来源，尝试其他授权来源。'}
                            reason='login_or_challenge';break
                        except PlatformRestrictionError:
                            checks[source]={'source':source,'status':'blocked','detail':'来源需要登录或验证'}
                            reason='login_or_challenge';break
                        except DetailItemError as exc:
                            state.setdefault('operation_errors',[]).append({'action':'detail','page':page_key,
                                'code':exc.code,'attempt':page_attempts[page_key],'result':'skip_card'})
                            if getattr(browser,'return_failed',False):
                                raise getattr(browser,'return_error',None) or BrowserInfrastructureError(
                                    '详情失败后返回搜索页未确认',action='navigate-back',code='return_unconfirmed') from exc
                            continue
                        except ValueError as exc:
                            if is_infrastructure_error(exc):
                                page_attempts[page_key]-=1
                                raise
                            state.setdefault('operation_errors',[]).append({'action':'detail','page':page_key,
                                'code':type(exc).__name__,'attempt':page_attempts[page_key],'result':'retry_pending'})
                            reason='detail_unavailable';checkpoint();break
                        new_download_errors=getattr(browser,'download_errors',[])
                        if new_download_errors:
                            received_errors.extend(new_download_errors)
                            browser.download_errors=[]
                            save(folder/'download-errors.json',received_errors)
                        # A page-return fault is handled before any heavy image
                        # comparison, so the bounded recovery window is not spent
                        # on local history matching.
                        return_issue=getattr(browser,'return_error',None)
                        if return_issue is not None or getattr(browser,'return_failed',False):
                            category=getattr(browser,'return_issue_category','page_return')
                            state.setdefault('return_pending_rows',{})[page_key]={
                                'source':source,'query':query,'category':category,'at':time.time(),
                                'rows':[{k:row.get(k) for k in ('asset_sha','original_path','page_url','image_url','bytes_received','duplicate','reason')} for row in rows]}
                            checkpoint('return_pending')
                            recovered=False
                            if hasattr(browser,'can_recover') and browser.can_recover():
                                # The progress file states that a recovery attempt
                                # is running: the owner and the page can tell a
                                # recovering Job from a searching one.
                                checkpoint('browser_recovering')
                                try:recovered=browser.recover(step,reason='return')
                                except Exception:recovered=False
                                checkpoint()
                            if recovered:
                                code=(getattr(return_issue,'code','') if return_issue is not None else '')
                                errors=collection_queue.read_json(folder/'browser-errors.json',[])
                                errors.append({'action':'browser_recovery','category':category,
                                               'code':code or 'return_unconfirmed','result':'recovered',
                                               'recovered':True,'stage':'before_history_compare','at':time.time()})
                                save(folder/'browser-errors.json',errors)
                                state.setdefault('operation_errors',[]).append({'action':'browser_recovery',
                                    'source':source,'query':query,'code':category,'result':'recovered','at':time.time()})
                                state.setdefault('return_pending_rows',{}).pop(page_key,None)
                                browser.return_failed=False;browser.return_error=None
                                checkpoint()
                            else:
                                if return_issue is not None:raise return_issue
                                raise BrowserInfrastructureError('返回搜索页未确认',action='navigate-back',
                                    code='return_unconfirmed',details=f'category={category}')
                        for row in rows:
                            if not search_only:
                                while pending and (len(pending)>=workers or len(candidates)+len(pending)>=target):finish_one()
                            sha=row['asset_sha']
                            if row.get('duplicate'):
                                reason=row.get('reason') or 'same_bytes_known'
                                entry={'asset_sha':sha,'page_url':row.get('page_url'),'duplicate_of':sha,
                                       'reason':reason,
                                       **({'source_address_precheck':True} if reason=='known_source_url' else {'temporary_copy_removed':True})}
                                if row.get('bytes_received'):
                                    entry['bytes_received']=row['bytes_received']
                                # The bytes are known, so no download happens, but
                                # the sighting may still carry the name or the
                                # warning the first one did not have. The merge
                                # only folds discovery evidence into the received
                                # row: it grants no Review acceptance and never
                                # touches the visual evidence.
                                if _merge_repeat_evidence(
                                        by_sha,card,row,names=name_records,
                                        work_terms=work_terms,other_terms=other_terms):
                                    save(folder/'received.json',received)
                                duplicates.append(entry)
                                save(folder/'duplicates.json',duplicates);checkpoint();continue
                            if sha in seen:
                                _discard_temporary(row)
                                if sha in by_sha:
                                    if _merge_repeat_evidence(
                                            by_sha,card,row,names=name_records,
                                            work_terms=work_terms,other_terms=other_terms):
                                        save(folder/'received.json',received)
                                duplicates.append({'asset_sha':sha,'page_url':row['page_url'],'duplicate_of':sha,'reason':'same_bytes_this_run'});continue
                            if search_only:
                                if confirmed()>=target or per_note>=browser.note_image_limit:
                                    _discard_temporary(row);break
                            elif len(candidates)>=target or calls()>=agent.candidate_limit or len(received)>=agent.candidate_limit or per_note>=3:
                                _discard_temporary(row);break
                            if (sha in {r['asset_sha'] for r in (agent.references or [])}
                                    or not Path(row['original_path']).resolve().is_relative_to(folder.resolve())):
                                _discard_temporary(row)
                                seen.add(sha);collisions.append({'asset_sha':sha,'page_url':row['page_url'],'reason':'reference media or wrong namespace; never photography'});continue
                            valid=True;error=''
                            if search_only:
                                valid,error=_valid_search_row(row,folder)
                            elif hashlib.sha256(Path(row['original_path']).read_bytes()).hexdigest()!=sha:
                                raise AgentUnavailable('收到的原图SHA不一致；停止，不采用未绑定图片。')
                            if not valid:
                                _discard_temporary(row)
                                seen.add(sha);received_errors.append({'asset_sha':sha,'page_url':row['page_url'],'error':error})
                                save(folder/'search-errors.json',received_errors);checkpoint();continue
                            seen.add(sha)
                            if history is not None:
                                with timing.span('history_consider'):duplicate=history.consider(Path(row['original_path']))
                                if duplicate and duplicate.get('reason')=='same_bytes_library' and duplicate.get('reuse'):
                                    # The identical original already exists in the
                                    # library under another project's use. This
                                    # project keeps its own candidate and reuses
                                    # the retained bytes; nothing is reported as a
                                    # second download and no inherited choice,
                                    # identity or acceptance travels with it.
                                    row['original_reuse']={'reason':'same_bytes_library',
                                                           'keeper_path':duplicate.get('keeper_path'),
                                                           'note':'复用全库已有原件，只保存一份；本项目参考关系与人工选择独立建立。'}
                                    duplicate=None
                                if duplicate:
                                    _discard_temporary(row)
                                    duplicates.append({'asset_sha':sha,'page_url':row['page_url'],**duplicate,
                                                       'temporary_copy_removed':bool(row.get('temporary'))})
                                    save(folder/'duplicates.json',duplicates);checkpoint();continue
                            from ref_lab.search_relevance import associate_detail
                            detail_relevance=associate_detail(card,row,names=name_records,work_terms=work_terms,other_terms=other_terms)
                            if search_only and str(detail_relevance.get('tier')) in ('target_context','unconfirmed'):
                                source_images=exploration_image_count(
                                    [r for r in received if urlsplit(r.get('page_url','')).hostname==parsed.hostname])
                                query_images=exploration_image_count(
                                    [r for r in received if r.get('search_query')==query])
                                if (exploration_image_count(received)>=exploration_limit(target)
                                        or source_images>=max(1,(exploration_limit(target)+len(sources)-1)//len(sources))
                                        or query_images>=1):
                                    _discard_temporary(row)
                                    skipped['exploration_budget']+=1
                                    state.setdefault('exploration_skipped',[]).append({
                                        'asset_sha':sha,'page_url':row.get('page_url'),'query':query,
                                        'tier':detail_relevance.get('tier'),'at':time.time(),
                                        'reason':'image_quota_exhausted','temporary_copy_removed':bool(row.get('temporary'))})
                                    save(folder/'duplicates.json',duplicates);checkpoint();continue
                            if row.get('temporary'):
                                temporary_path=Path(row['original_path'])
                                _promote_temporary(folder,row)
                                if history is not None:history.rekey(temporary_path,Path(row['original_path']))
                            row={**row,'search_query':query,'discovery_url':snapshot['url'],
                                 'acquired_at':time.time(),'relevance':detail_relevance if search_only else relevance}
                            received.append(row);attempted+=1;per_note+=1
                            by_sha[sha]=row
                            if search_only and first_usable is None:
                                first_usable=time.monotonic()-started
                                timing.event('first_received',asset_sha=sha)
                            save(folder/'received.json',received)
                            checkpoint()
                            if search_only and collage_worker is not None:
                                # Local, model-free post-processing runs off the
                                # download path: the original is already durable
                                # and visible before any tile is produced.
                                collage_worker.enqueue(row)
                            if not search_only:
                                pending.submit(row)
                                checkpoint()
                                if workers==1:finish_one()
                        # Any row the loop skipped (quota, limit, duplicate) must
                        # not keep its temporary copy around for the whole Job.
                        for leftover in rows:
                            if leftover.get('temporary'):_discard_temporary(leftover)
                        pages.add(page_key);checkpoint()
                        if getattr(browser,'return_error',None) is not None:
                            raise browser.return_error
                        if getattr(browser,'return_failed',False):
                            reason='search_return_unconfirmed_change_query';break
                    if not search_only:drain();checkpoint()
                    if reason=='login_or_challenge' or getattr(browser,'return_failed',False):break
                    if not new_cards:
                        reason='no_new_visible_posts_change_query';break
                    if len(received)>window_before and len(candidates)==kept_before and not search_only:
                        reason='no_verified_match_change_name_or_source';break
                    if search_only:
                        if type_worker is not None:
                            collage_worker.drain(timeout=3)
                            type_worker.drain(timeout=min(60,max(0,getattr(agent,'deadline',time.monotonic())-time.monotonic()-30)))
                        if confirmed()>=target:
                            reason='target_reached';break
                        if pending_qualifications(canonical_counts()):
                            reason='qualification_pending'
                        elif confirmed()>confirmed_before:
                            reason='target_named_candidates_found'
                        elif len(received)>window_before:
                            reason='no_qualified_yield'
                        else:
                            reason='no_new_valid_candidates'
                    else:
                        reason=reason or ('verified_matches' if len(candidates)>before else 'no_verified_match_change_name_or_source')
                    if (search_only and confirmed()==confirmed_before and not pending_qualifications(canonical_counts())
                            and source=='xiaohongshu' and sort_mode!='latest'):
                        # With no qualified gain and no pending qualification, try 最新 once.
                        latest_fallback_sources.add(source)
                    search['window']=window+1;search.pop('snapshot',None);checkpoint()
                    if pass_index<len(steps) and not coverage(steps,searches,sources)['explored']:
                        reason='bounded_breadth_next_query';break
            except AgentUnavailable:raise
            except (ValueError,OSError,subprocess.SubprocessError,httpx.HTTPError) as exc:
                if isinstance(exc,PlatformRestrictionError):
                    checks[source]={'source':source,'status':'blocked','detail':str(sanitize_diagnostics(exc.details))}
                    reason='login_or_challenge'
                elif is_infrastructure_error(exc):
                    errors=collection_queue.read_json(folder/'browser-errors.json',[])
                    errors.append(sanitize_diagnostics({'action':getattr(exc,'action','search_or_detail'),
                        'category':'infrastructure','code':getattr(exc,'code',type(exc).__name__),
                        'details':getattr(exc,'details',''),'result':'recovery_pending','at':time.time()}))
                    save(folder/'browser-errors.json',errors)
                    checkpoint('browser_recovering')
                    recovered=False
                    if hasattr(browser,'can_recover') and browser.can_recover():
                        try:recovered=browser.recover(step)
                        except Exception:recovered=False
                    if recovered:
                        reason='browser_recovered'
                        errors=collection_queue.read_json(folder/'browser-errors.json',[])
                        errors.append({
                            'action':'browser_recovery','category':'infrastructure',
                            'code':getattr(exc,'code',type(exc).__name__),
                            'result':'recovered','recovered':True,'at':time.time()
                        })
                        save(folder/'browser-errors.json',errors)
                        state.setdefault('operation_errors',[]).append({
                            'action':'browser_recovery','source':source,'query':query,
                            'code':getattr(exc,'code',type(exc).__name__),'result':'recovered','at':time.time()
                        })
                        should_advance=False
                    else:
                        reason='command_timeout' if getattr(exc,'is_timeout',False) else 'browser_unavailable'
                        stop_reason=reason
                        blocked=True
                        state.setdefault('operation_errors',[]).append({
                            'action':'browser_infrastructure','source':source,'query':query,
                            'code':getattr(exc,'code',type(exc).__name__),'result':'failed_unrecoverable','at':time.time()
                        })
                        if not search_only:drain()
                        break
                else:
                    reason='source_or_detail_failed_change_source'
                    search['retry_count']=int(search.get('retry_count',0))+1
                    state.setdefault('operation_errors',[]).append({'action':'search_or_more','source':source,
                        'query':query,'code':type(exc).__name__,'attempt':search['retry_count'],'result':'retry_pending'})
                    if not search_only:drain()
            finally:
                if should_advance:
                    pass_index+=1
                search['stop_reason']=reason or 'agent_blocked'
                from ref_lab.search_relevance import query_feedback
                search['feedback']=query_feedback(cards=len((search.get('snapshot') or {}).get('cards',[])),
                    named=int(search.get('scope_text_hits',0)),duplicates=len(duplicates)-feedback_before['duplicates'],
                    received=len(received)-feedback_before['received'],
                    rejected=canonical_counts().get('type_rejected',0)-feedback_before['rejected'],
                    detail_failures=len(state.get('operation_errors',[]))-feedback_before['details'],
                    blocked=reason=='login_or_challenge')
                if search_only:
                    current_counts=canonical_counts()
                    search['feedback']=_qualified_feedback(before=feedback_before['qualified'],after=confirmed(),
                        duplicates=len(duplicates)-feedback_before['duplicates'],received=len(received)-feedback_before['received'],
                        cards=len((snapshot or {}).get('cards',[])),pending=pending_qualifications(current_counts),
                        detail_failures=len(state.get('operation_errors',[]))-feedback_before['details'],
                        blocked=reason=='login_or_challenge')
                if sys.exc_info()[0] is None:
                    if not search.get('observed') or reason in ('browser_unavailable','browser_recovered'):
                        search['done']=False
                    else:
                        retryable=reason in ('source_or_detail_failed_change_source','detail_unavailable','search_return_unconfirmed_change_query','browser_recovered')
                        search['done']=(not retryable and reason!='bounded_breadth_next_query') or int(search.get('retry_count',0))>=2
                        if any(c.get('query')==query for c in state.get('deferred_cards',{}).values()):
                            search['done']=False
                entry={'source':source,'query':query,
                       'kept':(sum(r.get('search_query')==query for r in received) if search_only
                               else sum(c['source']['search_query']==query for c in candidates)),
                       'stop_reason':reason or 'agent_blocked'}
                if any(q['source']==source and q['query']==query for q in queries):
                    queries[:]=[entry if q['source']==source and q['query']==query else q for q in queries]
                else:queries.append(entry)
                if search_only and search.get('done'):
                    query_log=state.setdefault('query_history',[])
                    query_log.append({**entry,'attempt':int(state.get('search_attempts',1)),'at':time.time()})
                    if len(query_log)>120:del query_log[:len(query_log)-120]
                if search_only:
                    if search.get('feedback',{}).get('low_yield'):
                        poor_streak+=1
                    else:
                        poor_streak=0
                checkpoint()
    except BrowserInfrastructureError as exc:
        blocked=True;stop_reason='command_timeout' if exc.is_timeout else 'browser_unavailable'
        errors=collection_queue.read_json(folder/'browser-errors.json',[])
        errors.append(sanitize_diagnostics({'action':exc.action,'category':exc.category,
                                           'code':exc.code,'details':exc.details,'result':'failed','at':time.time()}))
        save(folder/'browser-errors.json',errors)
    except AgentUnavailable as exc:
        blocked=True;gaps.append(str(exc))
        category=getattr(exc,'category','')
        stop_reason=({'time_budget_exhausted':'time_budget_exhausted','call_budget_exhausted':'visual_budget_exhausted'}.get(category)
                     or ('unrecoverable_agent_failure' if fatal_visual_error(exc) else 'agent_failure'))
    except (KeyboardInterrupt,SystemExit):
        blocked=True;stop_reason='cancelled';interrupted=True
        raise
    except BaseException:
        import traceback
        try:(folder/'collector-error.log').write_text(traceback.format_exc(),'utf8')
        except Exception:pass
        blocked=True;stop_reason='internal_error';interrupted=True
        raise
    finally:
        incoming_cleanup=cleanup_incoming(folder)
        state['incoming_cleanup']=incoming_cleanup
        if pending is not None:pending.close(cancel=True)
        if collage_worker is not None and not collage_closed:
            # The download path never waits for splitting; the bounded drain here
            # only makes the final counts and gallery complete before the summary.
            deadline=getattr(agent,'deadline',float('inf'))
            collage_worker.close(timeout=max(1.0,min(30.0,deadline-time.monotonic())))
            collage_closed=True
        if type_worker is not None:
            type_worker.close(timeout=max(0,getattr(agent,'deadline',time.monotonic())-time.monotonic()-5))
        if not search_only and hasattr(agent,'cache_references'):agent.cache_references(project)
        if not stop_reason and sources and all(checks.get(s,{}).get('status') in ('login_required','blocked') for s in sources):
            stop_reason='sources_blocked';blocked=True
        stop_reason=stop_reason or limit_reason()
        if not stop_reason:
            if searches and not any(s.get('observed') for s in searches.values()):
                stop_reason='browser_unavailable';blocked=True
            elif any(not s.get('observed') or s.get('stop_reason') in (
                    'source_or_detail_failed_change_source','detail_unavailable',
                    'search_return_unconfirmed_change_query') for s in searches.values()):
                stop_reason='search_incomplete'
            else:
                stop_reason='search_plan_exhausted'
        confirmed_total=canonical_counts(force=True)['target_progress'] if search_only else len(candidates)
        termination_reason=stop_reason
        if search_only and not interrupted:
            if stop_reason=='target_reached' and confirmed_total<target:
                # A target_reached reason must be backed by confirmed names, never downloads alone.
                stop_reason=('qualified_count_decreased' if job.get('goal_id') else
                             'relevance_unconfirmed' if not confirmed_total else 'target_partial')
            elif not job.get('goal_id') and confirmed_total<target and stop_reason in ('search_plan_exhausted','no_new_valid_candidates'):
                stop_reason=('relevance_unconfirmed' if received and not confirmed_total
                             else ('target_partial' if confirmed_total else stop_reason))
        if search_only:
            if interrupted:
                status='cancelled'
            elif confirmed_total>=target:
                status='completed'
            elif stop_reason=='browser_unavailable':
                status='partial' if received else 'blocked'
            elif stop_reason=='sources_blocked':
                status='partial' if received else 'blocked'
            elif received:
                status='partial'
            else:
                status='blocked'
            state['outcome']=status
            attempt_elapsed=time.monotonic()-started
            if isinstance(job.get('search_attempt_started_at'),(int,float)):
                attempt_elapsed=max(attempt_elapsed,time.time()-job['search_attempt_started_at'])
            elapsed_total=previous_elapsed+attempt_elapsed
            collage_totals=collage_worker.summary() if collage_worker is not None else {}
            canonical=canonical_counts()
            summary=write_search_summary(
                folder,status=status,stop_reason=stop_reason,received=received,queries=queries,checks=checks,
                searches=searches,started=started,
                first_received=(started+first_usable if isinstance(first_usable,(int,float)) else None),
                duplicates=duplicates,
                errors=received_errors,extra={'target':target,'target_reached':confirmed_total>=target,
                                              'termination_reason':termination_reason,
                                              'query_budget':query_budget,
                                              'requested_target':requested_total,'effective_target':target,
                                              'budget_note':('本轮上限 100 张；请求 %s 张，按 %s 张执行。' % (requested_total,target)
                                                             if requested_total>target else ''),
                                              'search_only':True,
                                              'canonical':canonical,
                                              'usable_independent_named':canonical['usable_named'],
                                              'collage':collage_totals,
                                              'collage_errors':list(getattr(collage_worker,'errors',[]))[:10],
                                              'collage_seconds':round(getattr(collage_worker,'seconds',0.0),3),
                                              'collage_processed':int(getattr(collage_worker,'processed',0)),
                                              'preview_bytes_reused':int(getattr(browser,'preview_reused',0)),
                                              'preview_payloads':dict(getattr(browser,'preview_payloads',{})),
                                              'history_restore':history_restore,
                                              'incoming_cleaned':incoming_cleanup,
                                              'duplicates_pre_download':sum(1 for r in duplicates
                                                  if r.get('reason')=='known_source_url'),
                                              'duplicates_temp_cleaned':sum(1 for r in duplicates
                                                  if r.get('temporary_copy_removed')),
                                              'known_source_images':len(known_sources),
                                              'history_skipped_runs':len(getattr(history,'skipped_runs',[])),
                                              'history_files':getattr(history,'known_count',None),
                                              'cumulative_elapsed_seconds':round(elapsed_total,3),
                                              'continue':continue_info,
                                              'query_history':len(state.get('query_history',[])),
                                              'skipped_other_character':skipped['other_character'],
                                              'skipped_non_photo':skipped['non_photo'],
                                              'skipped_exploration_budget':skipped['exploration_budget'],
                                              'history_ready':getattr(history,'ready',None),
                                              'history_known':getattr(history,'known_count',getattr(history,'initial_count',0)),
                                              'history_errors':len(getattr(history,'errors',[])),
                                              'source_blocked':any(c.get('status') in ('blocked','login_required') for c in checks.values())})
            is_search_complete=(status=='completed') or (stop_reason in ('target_reached','soft_target_reached','search_plan_exhausted'))
            state.update(search_complete=is_search_complete,search_summary=summary,search_stop_reason=stop_reason,
                         phase='search_finished',first_usable=first_usable,elapsed_seconds_total=elapsed_total)
            try:browser.close()
            except (ValueError,OSError,subprocess.SubprocessError):
                gaps.append('本轮浏览器会话清理未确认，请检查自有会话。')
            summary['browser_cleanup']=read_json(folder/'browser-session.json',{}).get('cleanup',{})
            summary['elapsed_seconds']=round(time.monotonic()-started,3)
            elapsed_total=previous_elapsed+max(summary['elapsed_seconds'],
                time.time()-job['search_attempt_started_at'] if isinstance(job.get('search_attempt_started_at'),(int,float)) else 0.)
            summary['cumulative_elapsed_seconds']=round(elapsed_total,3)
            state['elapsed_seconds_total']=elapsed_total
            save(folder/'search-summary.json',summary)
            save(folder/'received.json',received);save(folder/'search-errors.json',received_errors)
            save(folder/'duplicates.json',duplicates);save(folder/'reference-collisions.json',collisions)
            save(folder/'counts.json',{
                # Canonical numbers shared with the stop condition, queue API and
                # search-summary. Do not recompute them here.
                **canonical,
                'unique_images_received':canonical['found'],
                'duplicates':len(duplicates),
                'target_confirmed':canonical['target_confirmed'],
                'exploration':canonical['exploration'],
                'other_character':canonical['other_character'],
                'non_photo':canonical['non_photo'],
                'original_singles':canonical['original_singles'],
                'collages':canonical['collages'],
                'collage_split_ok':canonical['collage_split_ok'],
                'collage_needs_manual':canonical['collage_needs_manual'],
                'collage_low_resolution':canonical['collage_low_resolution'],
                'collage_failed':canonical['collage_failed'],
                'derived_valid':canonical['derived_valid'],
                'derived_rejected':canonical['derived_rejected'],
                'derived_duplicate':canonical['derived_duplicate'],
                'usable_independent':canonical['usable_independent'],
                'usable_independent_named':canonical['usable_named'],
                'awaiting_manual':canonical['awaiting_manual'],
                'outdated_records':canonical['outdated_records'],
                'unprocessed':canonical['unprocessed'],
                'integrity_failures':canonical['integrity_failures'],
                'collage':collage_totals,
                'history_restore':history_restore,
                'skipped_other_character':skipped['other_character'],
                'skipped_non_photo':skipped['non_photo'],
                'skipped_exploration_budget':skipped['exploration_budget'],
                'search_errors':len(received_errors),'detail_pages':details,
                'visible_windows':windows,'stop_reason':stop_reason,
                'first_received_seconds':first_usable,
                'history_images':getattr(history,'known_count',getattr(history,'initial_count',0)),
                'history_ready':getattr(history,'ready',None),
                'model_calls':summary['model_calls'],'tokens':summary['tokens'],
                'vision_cli_calls':summary['model_calls'],'usage_complete':summary['usage_complete'],
                'preview_bytes_reused':int(getattr(browser,'preview_reused',0))})
            summary['preview_payloads']=dict(getattr(browser,'preview_payloads',{}))
            checkpoint('finished')
            summary['qualified_timeline']=state['qualified_timeline']
            save(folder/'search-summary.json',summary)
            search_summary_result=summary
        else:
            completed={r['asset_sha'] for r in audit}
            for row in received:
                if row['asset_sha'] not in completed:
                    audit.append({'asset_sha':row['asset_sha'],'source_page':row['page_url'],'review':None,'accepted':False,
                                  'decision':'NEEDS_EVIDENCE','execution_error':'Not committed before '+stop_reason})
            order={r['asset_sha']:i for i,r in enumerate(received)}
            audit.sort(key=lambda r:order[r['asset_sha']])
            try:browser.close()
            except (ValueError,OSError,subprocess.SubprocessError):gaps.append('本轮浏览器会话清理未确认，请检查自有会话。');blocked=True
            save(folder/'received.json',received);save(folder/'visual-audit.json',audit);save(folder/'reference-collisions.json',collisions)
            save(folder/'duplicates.json',duplicates);checkpoint('interrupted' if interrupted else 'finalizing')
            save(folder/'counts.json',{'attempted_visual_calls':calls(),'unique_images_received':len(received),'unique_images_inspected':reviewed,'completed_image_reviews':reviewed,
                                      'accepted':len(candidates),'reference_collisions':len(collisions),
                                      'needs_evidence':sum(r['decision']=='NEEDS_EVIDENCE' for r in audit),
                                      'execution_unreviewed':sum(r.get('review') is None for r in audit),
                                      'vision_cli_calls':getattr(agent,'vision_cli_calls',calls()),
                                      'historical_images':getattr(history,'known_count',getattr(history,'initial_count',0)),'duplicates':len(duplicates),
                                       'preview_duplicates':sum(r.get('asset_role')=='discovery_preview' for r in duplicates),
                                      'detail_pages':details,'visible_windows':windows,'stop_reason':stop_reason,
                                      'first_usable_seconds':first_usable,'vision_workers':workers})
        timing.event('collection_finished',accepted=len(candidates),reviewed=reviewed,stop_reason=stop_reason)
    if search_only:
        return search_summary_result,{}
    for source in sources:
        if source not in checks:checks[source]={'source':source,'status':'untested','detail':'预算或前置Agent阻断；未实际确认来源。'}
    coverage_result=coverage(steps,searches,sources)
    gaps.extend(coverage_result['gaps'])
    if len(candidates)<requested:gaps.append(f'已视觉确认{len(candidates)}/{requested}；不以未知或错误图片凑数。')
    outcome='complete' if len(candidates)>=requested and coverage_result['satisfied'] and not blocked else ('partial' if candidates else 'blocked')
    if blocked and stop_reason in ('unrecoverable_agent_failure','agent_failure','internal_error'):outcome='blocked'
    label={'complete':'达标完成','partial':'部分完成','blocked':'执行受阻'}[outcome]
    manifest={'schema_version':3,'job_id':job['id'],'batch_id':state['batch_id'],
              'candidates':candidates,'execution_report':{'producer':agent.producer,
              'status':'completed' if outcome=='complete' else 'blocked',
              'summary':f'{label}：Agent逐图确认{len(candidates)}/{requested}张，实际检查{reviewed}张不同图片、摄影核验调用{calls()}次；停止原因：{stop_reason}。',
              'source_checks':list(checks.values()),'query_log':queries,'gaps':list(dict.fromkeys(gaps))[:30]}}
    CandidatePackage.model_validate(manifest)
    exhausted=stop_reason in ('time_budget_exhausted','visual_budget_exhausted','detail_budget_exhausted')
    exhausted=exhausted or (stop_reason=='search_plan_exhausted' and not any(c['status'] in ('blocked','login_required') for c in checks.values()))
    state.update(final_manifest=manifest,outcome=outcome,
                 terminal=outcome=='complete' or (exhausted and all(r.get('review') for r in audit)))
    checkpoint('finished')
    save(folder/'manifest.json',manifest)
    render_result(folder,manifest,images)
    return manifest,images


def _search_terminal(folder):
    summary=read_json(folder/'search-summary.json',{})
    if isinstance(summary,dict) and summary and summary.get('status') in ('completed','blocked','failed','cancelled'):
        return True,str(summary.get('status'))
    state=read_json(folder/'collector-state.json',{})
    if isinstance(state,dict) and state.get('search_complete'):
        return True,'completed'
    return False,'running'


def _load_review_audit(folder,project):
    context=scope_sha(project)
    data=read_json(folder/'review-audit.json',{})
    if not isinstance(data,dict) or data.get('version')!=1 or not isinstance(data.get('items'),dict):
        return {'version':1,'context_sha':context,'items':{}}
    if data.get('context_sha')!=context:
        # Keep the stale verdict file for inspection but never reuse it under new constraints.
        archive=folder/('review-audit-stale-'+str(data.get('context_sha',''))[:12]+'.json')
        if not archive.exists():save(archive,data)
        return {'version':1,'context_sha':context,'items':{}}
    return data


def _review_state(folder,**values):
    current=read_json(folder/'review-state.json',{})
    if not isinstance(current,dict):current={}
    current.update(values)
    save(folder/'review-state.json',current)
    return current


def _review_package(job,project,folder,state,received,items,human,*,status,stop_reason,
                    started,agent,prepare_error='',sample_limit=0):
    target=min(int(job.get('target_count') or 12),100)
    candidates=[];images={};errors=[]
    warned=set()
    for row in received:
        sha=row['asset_sha'];item=items.get(sha)
        if not item or item.get('status')!='accepted':continue
        if (human.get(sha) or {}).get('decision')=='reject':continue
        if source_warnings(row):
            # A platform warning blocks the qualified count, also when the
            # photo was accepted before the warning appeared on a repeat.
            warned.add(sha)
            errors.append(f'{sha[:12]}：平台来源提示可能含AI生成内容，待人工确认。')
            continue
        try:
            value=CollectionVision.model_validate(item['review'])
            references=item.get('references') or []
            if value.asset_sha!=sha or value.context_sha!=scope_sha(project):
                raise AgentUnavailable('审核结论不属于当前原图或项目要求。')
            if not accepted(value,project,references=references):
                raise AgentUnavailable('审核结论不满足冻结准入规则。')
            raw=original_bytes(row,folder)
            if hashlib.sha256(raw).hexdigest()!=sha:
                raise AgentUnavailable('候选原图SHA在审核期间改变。')
            candidate=verified_candidate(row,value,project,references,row.get('search_query',''),row.get('discovery_url',''))
            candidates.append(candidate);images[Path(candidate['file']).name]=raw
        except (AgentUnavailable,OSError,ValueError) as exc:
            errors.append(f'{sha[:12]}：{str(exc)[:160]}')
    counts={'found':len(received),'accepted':0,'rejected':0,'blocked':0,'pending':0,
            'human_keep':0,'human_reject':0}
    for row in received:
        sha=row['asset_sha'];item=items.get(sha) or {};decision=(human.get(sha) or {}).get('decision')
        if decision=='keep':counts['human_keep']+=1
        elif decision=='reject':counts['human_reject']+=1
        elif item.get('status')=='accepted' and sha in warned:counts['blocked']+=1
        elif item.get('status')=='accepted':counts['accepted']+=1
        elif item.get('status') in ('rejected','duplicate'):counts['rejected']+=1
        elif item.get('status')=='blocked':counts['blocked']+=1
        else:counts['pending']+=1
    complete=counts['accepted']>=target and not counts['blocked'] and not counts['pending']
    package_status='completed' if complete else ('partial' if candidates else 'blocked')
    calls,tokens,with_usage=_attempt_usage(folder)
    summary={'version':1,'status':package_status,'stop_reason':stop_reason,
             'target':target,'counts':counts,'accepted_candidates':len(candidates),
             'started_at':time.time()-max(0.0,time.monotonic()-started),
             'elapsed_seconds':round(time.monotonic()-started,3),'finished_at':time.time(),
             'model_calls':calls,'tokens':tokens,'attempts_with_usage':with_usage,
             'prepare_error':prepare_error[:600],
             'sample_limit':int(sample_limit or 0),
             'search_status':read_json(folder/'search-summary.json',{}).get('status',''),
             'human_decisions_are_separate':True,
             'errors':errors[:20]}
    gaps=[f'审核受阻/未通过：{n}张。' for n in [counts['blocked']] if n]
    gaps.extend(errors)
    if counts['accepted']<target:gaps.append(f'独立审核通过{counts["accepted"]}/{target}；不以未审核图片凑数。')
    if sample_limit:gaps.append(f'本轮有界审核样本上限 {int(sample_limit)} 张；其余 {counts["pending"]} 张保持待审，未自动判拒绝。')
    if prepare_error:gaps.append('参照阶段：'+prepare_error[:300])
    report={'producer':agent.producer,'status':'completed' if complete else 'blocked',
             'summary':(f'独立审核：通过{counts["accepted"]}/{target}，拒绝{counts["rejected"]}，'
                        f'受阻{counts["blocked"]}，待审{counts["pending"]}；停止原因：{stop_reason}。'),
             'source_checks':list((state.get('checks') or {}).values()),
             'query_log':state.get('queries',[]),'gaps':list(dict.fromkeys(gaps))[:30]}
    manifest={'schema_version':3,'job_id':job['id'],'batch_id':state['batch_id'],
              'candidates':candidates,'execution_report':report}
    CandidatePackage.model_validate(manifest)
    save(folder/'review-summary.json',summary)
    save(folder/'review-audit.json',{'version':1,'context_sha':scope_sha(project),'items':items,
                                     'updated_at':time.time()})
    _review_state(folder,phase='finished',current_sha=None,status=package_status,
                  stop_reason=stop_reason,finished_at=time.time())
    return manifest,images,summary


def review_candidates(job,agent,folder:Path,*,history=None,wait_for_search=False,deadline=None):
    """Independent Review consumer. Reads originals already persisted by Search.

    ``LAB_REVIEW_MAX_IMAGES`` (0 = unlimited) is a minimal bounded-batch control:
    after that many new per-image judgments the run finishes normally, writes a
    partial schema3 package for what it actually reviewed, and leaves the remaining
    candidates pending. It never marks un-reviewed images as rejected.
    """
    project={**job['project_snapshot'],'notes':job.get('notes','')};context=scope_sha(project)
    target=min(int(job.get('target_count') or 12),100)
    try:sample_limit=max(0,min(100,int(os.environ.get('LAB_REVIEW_MAX_IMAGES','0') or 0)))
    except (TypeError,ValueError):sample_limit=0
    started=time.monotonic()
    state=load_checkpoint(folder,job,getattr(agent,'model',agent.producer))
    received=state['received']
    if wait_for_search and not received:
        _review_state(folder,phase='waiting_search',started_at=time.time())
        while not received:
            if deadline is not None and time.monotonic()>=deadline:
                break
            if _search_terminal(folder)[0]:
                break
            time.sleep(1)
            state=load_checkpoint(folder,job,getattr(agent,'model',agent.producer))
            received=state['received']
    if not received:
        manifest,images,summary=_review_package(job,project,folder,state,received,{}, {},
                                                status='blocked',stop_reason='no_candidates',
                                                started=started,agent=agent)
        return manifest,images,summary
    if history is not None:
        # Search already imported these originals into the project asset store;
        # they are this Job's own candidates, not historical repeats of themselves.
        history.exclude([row['asset_sha'] for row in received])
    existing_audit=_load_review_audit(folder,project)
    terminal,_= _search_terminal(folder)
    human_preview={row['asset_sha']:collection_queue.human_decision(folder,row['asset_sha']) for row in received}
    if terminal and all(human_preview.get(row['asset_sha'])
                        or (existing_audit['items'].get(row['asset_sha']) or {}).get('status') in
                            ('accepted','rejected','duplicate') for row in received):
        # A second launch must not create a new NamePlan, references or vision call.
        manifest,images,summary=_review_package(job,project,folder,state,received,
                                                existing_audit['items'],human_preview,
                                                status='completed',stop_reason='review_already_complete',
                                                started=started,agent=agent)
        return manifest,images,summary
    _review_state(folder,phase='planning',started_at=time.time())
    try:
        plan=agent.plan(project)
    except AgentUnavailable as exc:
        items={}
        manifest,images,summary=_review_package(job,project,folder,state,received,items,{},
                                                status='blocked',stop_reason='review_plan_blocked',
                                                started=started,agent=agent,prepare_error=str(exc))
        return manifest,images,summary
    save(folder/'review-name-plan.json',{'plan':plan.model_dump(),'origin':'review_agent_discovery_hypothesis'})
    _review_state(folder,phase='reference_prepare')
    prepare_error=''
    try:
        agent.prepare(project,plan)
    except AgentUnavailable as exc:
        prepare_error=str(exc)
    references=list(agent.references or [])
    if not references:
        # Honest blocked state: do not turn missing evidence into a character mismatch.
        items={}
        for row in received:
            sha=row['asset_sha']
            if collection_queue.human_decision(folder,sha):continue
            items[sha]={'asset_sha':sha,'status':'blocked','accepted':False,'decision':'REVIEW_BLOCKED',
                        'error':'参照研究未取得可核查来源；保留候选原图，审核受阻。'+(' '+prepare_error if prepare_error else ''),
                        'attempts':0,'completed_at':time.time()}
        manifest,images,summary=_review_package(job,project,folder,state,received,items,{},
                                                status='blocked',stop_reason='reference_blocked',
                                                started=started,agent=agent,prepare_error=prepare_error)
        return manifest,images,summary
    audit=_load_review_audit(folder,project);items=audit['items'];human_cache={}
    blocked_this_run=set();fatal=False;stop_reason='';search_status='running';reviewed_new=0
    while True:
        state=load_checkpoint(folder,job,getattr(agent,'model',agent.producer))
        received=state['received']
        if history is not None:
            history.exclude([row['asset_sha'] for row in received])
        terminal,search_status=_search_terminal(folder)
        human_cache={row['asset_sha']:collection_queue.human_decision(folder,row['asset_sha']) for row in received}
        for row in received:
            sha=row['asset_sha']
            if sha in blocked_this_run:continue
            if human_cache.get(sha):continue
            current=items.get(sha) or {}
            if current.get('status') in ('accepted','rejected','duplicate'):continue
            if deadline is not None and time.monotonic()>=deadline:
                stop_reason='review_timeout';break
            if sample_limit and reviewed_new>=sample_limit:
                stop_reason='review_sample_limit';break
            attempts=int(current.get('attempts',0))+1
            items[sha]={'asset_sha':sha,'status':'reviewing','attempts':attempts,
                        'started_at':time.time(),'source_page':row.get('page_url','')}
            save(folder/'review-audit.json',{'version':1,'context_sha':context,'items':items,'updated_at':time.time()})
            _review_state(folder,phase='reviewing',current_sha=sha,current_started_at=time.time())
            try:
                if history is not None:
                    duplicate=history.match(Path(row['original_path']))
                    if duplicate:
                        if duplicate.get('state') == 'needs_review':
                            raise AgentUnavailable('history_relation_unconfirmed: '+duplicate.get('reason','unknown'))
                        items[sha]={'asset_sha':sha,'status':'duplicate','accepted':False,'decision':'DUPLICATE',
                                    'error':duplicate.get('reason','duplicate'),'duplicate_of':duplicate.get('duplicate_of'),
                                    'attempts':attempts,'completed_at':time.time()}
                        save(folder/'review-audit.json',{'version':1,'context_sha':context,'items':items,'updated_at':time.time()})
                        continue
                reviewed_new+=1
                value=agent.review(Path(row['original_path']),project)
                if value.asset_sha!=sha or value.context_sha!=context:
                    raise AgentUnavailable('审核结论绑定了其他原图或项目要求。')
                valid=accepted(value,project,references=agent.references)
                refs=copy.deepcopy(agent.references)
                verdict=('CONFIRMED' if valid else
                         ('MISMATCH' if value.kind not in ('cosplay_photo','portrait_photo','unknown')
                          or (value.identity=='match' and value.costume=='mismatch' and reference_supported(value,refs))
                          else 'NEEDS_EVIDENCE'))
                items[sha]={'asset_sha':sha,'status':'accepted' if valid else 'rejected','accepted':valid,
                            'decision':verdict,'review':value.model_dump(),'reference_shas':[r['asset_sha'] for r in refs],
                            'references':refs,'attempts':attempts,'completed_at':time.time(),
                            'source_page':row.get('page_url','')}
                timing=getattr(agent,'timing',None)
                if timing:timing.event('review_committed',asset_sha=sha,accepted=valid)
            except AgentUnavailable as exc:
                items[sha]={'asset_sha':sha,'status':'blocked','accepted':False,'decision':'REVIEW_BLOCKED',
                            'error':str(exc),'attempts':attempts,'completed_at':time.time(),
                            'source_page':row.get('page_url','')}
                blocked_this_run.add(sha)
                if fatal_visual_error(exc):
                    fatal=True;stop_reason='unrecoverable_review_failure'
            except (OSError,ValueError) as exc:
                items[sha]={'asset_sha':sha,'status':'blocked','accepted':False,'decision':'REVIEW_BLOCKED',
                            'error':type(exc).__name__+': '+str(exc),'attempts':attempts,
                            'completed_at':time.time(),'source_page':row.get('page_url','')}
                blocked_this_run.add(sha)
            save(folder/'review-audit.json',{'version':1,'context_sha':context,'items':items,'updated_at':time.time()})
            if fatal:break
        if stop_reason or fatal:break
        if terminal:break
        if not wait_for_search:break
        if deadline is not None and time.monotonic()>=deadline:
            stop_reason='review_timeout';break
        _review_state(folder,phase='waiting_search',current_sha=None)
        time.sleep(1)
    if stop_reason=='review_timeout' or (deadline is not None and time.monotonic()>=deadline and any(
            (items.get(row['asset_sha']) or {}).get('status') in (None,'reviewing','blocked') and not human_cache.get(row['asset_sha'])
            for row in received)):
        stop_reason=stop_reason or 'review_timeout'
        for row in received:
            sha=row['asset_sha']
            if human_cache.get(sha):continue
            current=items.get(sha) or {}
            if current.get('status') in ('accepted','rejected','duplicate'):continue
            items[sha]={'asset_sha':sha,'status':'blocked','accepted':False,'decision':'REVIEW_BLOCKED',
                        'error':'审核时间预算耗尽；候选原图保留，可稍后重试。','attempts':int(current.get('attempts',0)),
                        'completed_at':time.time(),'source_page':row.get('page_url','')}
        save(folder/'review-audit.json',{'version':1,'context_sha':context,'items':items,'updated_at':time.time()})
    if not stop_reason:
        stop_reason='review_complete' if terminal else 'review_budget_reached'
    manifest,images,summary=_review_package(job,project,folder,state,received,items,human_cache,
                                            status='completed',stop_reason=stop_reason,
                                            started=started,agent=agent,prepare_error=prepare_error,
                                            sample_limit=sample_limit)
    return manifest,images,summary


def _discard_temporary(row):
    """Delete this run's temporary copy; never touches a durable original."""
    path=row.get('original_path')
    if row.get('temporary') and path:
        try:Path(path).unlink(missing_ok=True)
        except OSError:pass


def _promote_temporary(folder:Path,row):
    """Move a judged-new temporary file into the run's durable image area.

    A row marked ``original_reuse`` hard-links the retained library copy
    instead of writing a second physical original; the received bytes are the
    same either way and the fallback keeps the promotion working across
    filesystem boundaries.
    """
    source=Path(row['original_path']);sha=row['asset_sha']
    ext=str(row.get('ext') or source.suffix.lstrip('.') or 'jpg').lower()
    target=(Path(folder)/'images'/f'{sha}.{ext}')
    target.parent.mkdir(parents=True,exist_ok=True)
    if target.exists():
        if hashlib.sha256(target.read_bytes()).hexdigest()!=sha:raise ValueError('Immutable file conflict')
        source.unlink(missing_ok=True)
    else:
        keeper=Path(str((row.get('original_reuse') or {}).get('keeper_path') or ''))
        linked=False
        if keeper.is_file() and not keeper.is_symlink():
            try:
                os.link(keeper,target)
                if hashlib.sha256(target.read_bytes()).hexdigest()!=sha:
                    target.unlink(missing_ok=True);raise ValueError('Reused keeper bytes changed')
                linked=True
            except OSError:
                linked=False
        if linked:
            source.unlink(missing_ok=True)
        else:
            os.replace(source,target)
    row['original_path']=str(target.resolve());row.pop('temporary',None)
    return target


def cleanup_incoming(folder:Path)->dict:
    """Remove only this run's leftover temporary downloads after failure/exit.

    The preview staging area belongs to the same temporary lifetime: a
    confirmed duplicate must not stay on disk as a second copy of a picture
    the library already owns.
    """
    incoming=Path(folder)/'incoming'
    if (not incoming.is_dir() or incoming.is_symlink()
            or getattr(incoming,'is_junction',lambda:False)()):return {'files':0,'bytes':0}
    files=0;size=0
    for path in incoming.glob('*'):
        if path.is_dir():
            if path.is_symlink() or getattr(path,'is_junction',lambda:False)() or path.name!='previews':continue
            for preview in path.glob('*'):
                if not preview.is_file() or preview.is_symlink():continue
                if not re.fullmatch(r'[0-9a-f]{32}\.(jpg|png|webp|avif)',preview.name):continue
                if preview.stat().st_nlink!=1:continue
                try:
                    size+=preview.stat().st_size;preview.unlink();files+=1
                except OSError:
                    pass
            try:path.rmdir()
            except OSError:pass
            continue
        if not path.is_file() or path.is_symlink():continue
        if path.stat().st_nlink!=1:continue
        try:
            size+=path.stat().st_size;path.unlink();files+=1
        except OSError:
            pass
    return {'files':files,'bytes':size}


def _known_image_sources(history,current:Path)->dict:
    """Map previously received source-image addresses to verified SHAs.

    Only addresses whose SHA already belongs to the verified duplicate history
    are reused, so an unknown, edited or re-encoded image is still fetched and
    judged. A matching address skips that one known transmission; it never
    skips a whole post. The scanned runs are the current project's own
    attributed runs: another project's sightings neither block a download nor
    demote a post of this project.
    """
    if history is None:return {}
    known=set(getattr(history,'known_shas',()) or ())|set(getattr(history,'records',{}))
    if not known:return {}
    attributed=[Path(path) for path in (getattr(history,'attributed_run_dirs',()) or ())]
    if attributed:
        candidates=[directory/'received.json' for directory in attributed]
    else:
        roots=list(dict.fromkeys(base/'.local'/kind for base in
            [ROOT,*getattr(history,'discovery_roots',[])] for kind in ('collection-runs','backups')))
        candidates=[]
        for root in roots:
            if not root.is_dir():continue
            candidates.extend(root.glob('*/received.json'))
            candidates.extend(root.glob('*/*/received.json'))
            candidates.extend(root.glob('*/*/*/received.json'))
    sources={}
    seen_posts=set()
    current=Path(current).resolve()
    for path in candidates:
        try:
            resolved=path.resolve()
        except OSError:continue
        if resolved.parent.is_relative_to(current):continue
        try:payload=json.loads(resolved.read_text('utf8'))
        except (OSError,ValueError):continue
        records=payload.get('candidates',[]) if isinstance(payload,dict) else payload
        if not isinstance(records,list):continue
        try:prior=read_json(resolved.parent/'collector-state.json',{})
        except (OSError,ValueError):prior={}
        if isinstance(prior,dict):
            attempts_by_page=prior.get('page_attempts')
            for page,attempts in (attempts_by_page if isinstance(attempts_by_page,dict) else {}).items():
                key=_post_key('https://'+page)
                if key and isinstance(attempts,int) and attempts>0:seen_posts.add(key)
            observations=prior.get('post_observations')
            for observation in (observations if isinstance(observations,dict) else {}).values():
                if isinstance(observation,dict) and isinstance(observation.get('images'),list):
                    records.extend(observation['images'])
        for row in records:
            if not isinstance(row,dict):continue
            sha=row.get('asset_sha')
            if not isinstance(sha,str) or sha not in known:continue
            post=_post_key(row.get('page_url'))
            if post:seen_posts.add(post)
            key=normalize_image_url(row.get('image_url'))
            if key:sources.setdefault(key,sha)
    history.seen_posts=seen_posts
    return sources


def _valid_search_row(row,folder):
    """Cheap deterministic file check; never a visual identity or quality verdict."""
    try:
        path=Path(row['original_path']).resolve()
        root=Path(folder).resolve()
        if path.is_symlink() or not path.is_file() or not path.is_relative_to(root):
            return False,'original_path_outside_run'
        if not (path.is_relative_to((Path(folder)/'images').resolve())
                or path.is_relative_to((Path(folder)/'incoming').resolve())):
            return False,'original_path_outside_staging'
        raw=path.read_bytes()
        if len(raw)>20*1024*1024:return False,'image_too_large'
        if hashlib.sha256(raw).hexdigest()!=row.get('asset_sha'):return False,'sha_mismatch'
        with Image.open(io.BytesIO(raw)) as image:
            image.load();width,height=image.size
            if width<200 or height<200:return False,'image_too_small'
            if width/max(1,height)>4.5 or width/max(1,height)<0.22:return False,'extreme_aspect_ratio'
            if getattr(image,'n_frames',1)!=1:return False,'animated_or_multiframe'
        row['width']=width;row['height']=height
        return True,''
    except (OSError,ValueError,Image.DecompressionBombError) as exc:
        return False,type(exc).__name__


def _attempt_usage(folder):
    calls=0;tokens=0;with_usage=0
    for path in folder.glob('attempt-*.json'):
        try:value=json.loads(path.read_text('utf8'))
        except (OSError,ValueError):continue
        if value.get('result_type')=='CollectionVision':calls+=1
        usage=((value.get('result') or {}).get('usage') or {})
        if isinstance(usage,dict) and isinstance(usage.get('total_tokens'),int):
            tokens+=usage['total_tokens'];with_usage+=1
    types=read_json(folder/'photo-types.json',{}).get('calls',[])
    calls+=len(types)
    for entry in types:
        if isinstance(entry.get('tokens'),int):tokens+=entry['tokens'];with_usage+=1
    return calls,tokens,with_usage


def write_search_summary(folder,*,status,stop_reason,received,queries,checks,searches,
                         started,first_received,duplicates,errors,extra=None):
    calls,tokens,with_usage=_attempt_usage(folder)
    relevance=relevance_counts(received)
    canonical=(extra or {}).get('canonical') if isinstance(extra,dict) else None
    counts={'found':len(received),'duplicates':len(duplicates),'errors':len(errors),
            'target_confirmed':relevance['confirmed'],
            'exploration':relevance['exploration'],
            'other_character':relevance['other_character'],
            'non_photo':relevance['non_photo']}
    if isinstance(canonical,dict):
        # Canonical numbers from ref_lab.collection_counts.compute; the same
        # values the stop condition and counts.json used.
        counts.update(canonical)
    summary={'version':1,'status':status,'stop_reason':stop_reason,
             'target':int(extra.get('target',0)) if extra else 0,
             'target_reached':bool(extra.get('target_reached')) if extra else False,
             'counts':counts,
             'first_received_seconds':(round(first_received-started,3)
                                       if isinstance(first_received,(int,float)) else None),
             'elapsed_seconds':round(time.monotonic()-started,3),
             'finished_at':time.time(),'queries':queries,'checks':checks,
             'browser_errors':collection_queue.read_json(folder/'browser-errors.json',[])[-20:],'source_checks':list(checks.values()),
             'searches':searches,'errors':list(errors)[:20],
             'model_calls':calls,'tokens':tokens,'attempts_with_usage':with_usage,
             'counts_source':'ref_lab.collection_counts.compute',
             'model_calls_note':'包含本候选集的真实图片类型模型调用及失败；Token只加总供应商实际报告值，未报告部分未知。',
             'usage_complete':with_usage==calls}
    attempts=read_json(folder/'photo-types.json',{}).get('calls',[])
    summary.update(type_images=len(read_json(folder/'photo-types.json',{}).get('items',{})),
                   type_attempts=len(attempts), type_successes=sum(c.get('status')=='succeeded' for c in attempts),
                   confirmed_model_invocations=sum(c.get('invoked') is True for c in attempts),
                   unknown_model_invocations=sum('invoked' not in c for c in attempts))
    if extra:
        for key in ('target','requested_target','effective_target','target_reached','budget_note',
                    'termination_reason','query_budget',
                    'search_only','history_ready','history_known','history_errors','source_blocked',
                    'cumulative_elapsed_seconds','continue','query_history','canonical',
                    'usable_independent_named','collage','collage_errors','collage_seconds',
                    'collage_processed','preview_bytes_reused','history_restore',
                    'preview_payloads',
                    'skipped_other_character','skipped_non_photo','skipped_exploration_budget',
                    'incoming_cleaned','duplicates_pre_download','duplicates_temp_cleaned',
                    'known_source_images','history_skipped_runs','history_files'):
            if key in extra:summary[key]=extra[key]
    save(folder/'search-summary.json',summary)
    return summary


def _publish_same_bytes(source:Path,target:Path,expected_sha:str)->bool:
    """Publish the same bytes without keeping a second physical copy.

    A hard link shares physical bytes. If linking is unavailable, the caller
    links the page to the verified original instead of writing another copy.
    """
    from ref_lab.integrity import sha_matches
    if source.is_symlink() or target.is_symlink() or not sha_matches(source,expected_sha):
        raise ValueError('Gallery original SHA or boundary changed')
    if target.exists():
        if not sha_matches(target,expected_sha):raise ValueError('Immutable gallery image conflict')
        return True
    try:
        os.link(source,target)
        if not os.path.samefile(source,target):raise ValueError('Gallery link identity changed')
    except OSError:
        if target.exists():
            if not sha_matches(target,expected_sha):raise ValueError('Immutable gallery image conflict')
            return True
        return False
    return sha_matches(target,expected_sha)


def render_search_gallery(folder,rows,*,running=False):
    """Read-only fallback view of acquired originals plus their usable crops.

    Every referenced original is SHA-verified. A hard link next to the page
    shares storage; without link support the page references the original.
    """
    from ref_lab.collage import DerivedStore, VALID, record_is_current
    from ref_lab.integrity import sha_matches
    public=folder/'public';public.mkdir(exist_ok=True);figures=[]
    if public.is_symlink() or getattr(public,'is_junction',lambda:False)() or public.resolve().parent!=folder.resolve():raise ValueError('Gallery boundary changed')
    records=DerivedStore(folder).items()
    problems=[]
    def ensure(source: Path, expected_sha: str):
        if not source.resolve().is_relative_to(folder.resolve()) or not any(
                not (folder/role).is_symlink() and not getattr(folder/role,'is_junction',lambda:False)()
                and source.resolve().is_relative_to((folder/role).resolve()) for role in ('images','derived')):
            raise ValueError('Gallery original outside run')
        target=public/source.name
        try:
            if not _publish_same_bytes(source,target,expected_sha):
                return Path(os.path.relpath(source,public)).as_posix()
        except (OSError,ValueError):
            problems.append({'file':source.name,'reason':'original_or_gallery_invalid'});return None
        if not sha_matches(target,expected_sha):
            problems.append({'file':target.name,'reason':'sha_mismatch'});return None
        return target.name
    for i,row in enumerate(rows,1):
        source=Path(row['original_path'])
        original_name=ensure(source,str(row['asset_sha']))
        if original_name is None:continue
        record=records.get(row['asset_sha']) or {}
        current=record_is_current(record)
        children=[child for child in (record.get('children') or []) if isinstance(child,dict)]
        usable=[child for child in children if child.get('status')==VALID] if current else []
        child_figures=''
        if usable:
            cards=[]
            for index,child in enumerate(usable,1):
                child_sha=str(child.get('child_sha') or '')
                child_path=Path(str(child.get('path') or ''))
                if not child_sha or not sha_matches(child_path,child_sha):
                    problems.append({'file':child_path.name,'reason':'child_sha_mismatch'})
                    continue
                child_name=ensure(child_path,child_sha)
                if child_name is None:continue
                cards.append('<figure style="margin:0;max-width:220px"><img style="max-height:200px;margin:0" src="'
                             +html.escape(child_name,quote=True)+'" alt="子图'+str(index)+'">'
                             '<figcaption style="font-size:12px">子图 '+str(index)+' · '
                             +html.escape('×'.join(str(value) for value in (child.get('size') or [])))
                             +'</figcaption></figure>')
            if cards:
                child_figures='<div style="display:flex;flex-wrap:wrap;gap:10px;margin-top:12px">'+''.join(cards)+'</div>'
        status=str(record.get('status') or 'no_collage')
        if not record or status=='no_collage':
            collage_note=''
        elif not current:
            collage_note='<p>本地拼图记录版本待更新：未计入可用照片，重新处理后才生效；原拼图仍可查看。</p>'
        elif status=='needs_manual_crop':
            collage_note=('<p>检测到更密或不可靠的拼图分界（'+html.escape(str(record.get('reason','')))
                          +'），已标记待人工裁切，不产生可计数的拼图大块；原拼图仍可查看。</p>')
        elif status=='low_resolution':
            collage_note=('<p>本地图片处理：'+html.escape(str(record.get('layout','')))
                          +'，子图分辨率或画质不足，未作为可用照片；原拼图仍可查看。</p>')
        elif status=='failed':
            collage_note=('<p>派生记录完整性检查失败，未计入可用照片；原拼图与现有文件保留可查看。</p>')
        elif usable:
            collage_note=('<p>本地图片处理：'+html.escape(str(record.get('layout','')))
                          +' · 子图 '+str(len(children))+' 张，可用 '+str(len(usable))
                          +' 张。原图与其子图不重复计入可用照片。</p>')
        else:
            collage_note=('<p>本地图片处理：'+html.escape(str(record.get('layout','')))
                          +'，没有合格子图，未计入可用照片；原拼图仍可查看。</p>')
        figures.append('<article><h2>'+str(i)+' · 候选原图</h2><img src="'+html.escape(original_name,quote=True)+'" alt="候选原图'+str(i)+'">'
                       '<p>来源：<a target="_blank" rel="noreferrer" href="'+html.escape(row.get('page_url',''),quote=True)+'">原帖</a>'
                       ' · 搜索词：'+html.escape(row.get('search_query',''))+'</p>'
                       '<p>状态：已下载，待审核。不是已通过摄影审核。</p>'
                       +collage_note+child_figures+'</article>')
    body=('<!doctype html><html lang="zh-CN"><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">'
          '<title>快速搜图候选</title><style>body{margin:0;background:#f5f3ed;color:#242824;font:16px/1.7 system-ui}'
          'main{max-width:960px;margin:auto;padding:24px}h1{font-size:26px}h2{font-size:20px}'
          'article{border-top:1px solid #ccc;padding:24px 0}img{display:block;max-width:100%;max-height:84vh;margin:auto}a{color:#205f43}</style>'
          '<main><h1>快速搜图候选 · '+str(len(figures))+'张</h1>'
          '<p>原图已保存并可在网页候选图库查看；这里只表示下载成功，不代表身份或摄影质量已经审核。</p>'
          +(''.join(figures) or '<p>尚未取得候选原图。</p>')+'</main></html>')
    if running:body=body.replace('<title>','<meta http-equiv="refresh" content="5"><title>',1)
    atomic_write(public/'search-index.html',body.encode('utf8'))


def render_result(folder,manifest,images,*,running=False):
    """A read-only view of the original Agent output, without Root selection."""
    public=folder/'public';public.mkdir(exist_ok=True);figures=[]
    if public.is_symlink() or getattr(public,'is_junction',lambda:False)() or public.resolve().parent!=folder.resolve():raise ValueError('Gallery boundary changed')
    for i,candidate in enumerate(manifest['candidates'],1):
        name=Path(candidate['file']).name;raw=images[name];target=public/name
        if target.exists() and target.read_bytes()!=raw:raise ValueError('Immutable gallery image conflict')
        source=folder/'images'/name
        if ((folder/'images').is_symlink() or getattr(folder/'images','is_junction',lambda:False)()
                or source.is_symlink() or not source.resolve().is_relative_to(folder.resolve()/'images')):
            raise ValueError('Gallery original outside run')
        if not source.exists():atomic_write(source,raw)
        if not _publish_same_bytes(source,target,hashlib.sha256(raw).hexdigest()):
            name=Path(os.path.relpath(source,public)).as_posix()
        figures.append('<article><h2>'+str(i)+' · '+html.escape(candidate['title'])+'</h2><img src="'+html.escape(name,quote=True)+'" alt="AGY摄影参考'+str(i)+'"><p>'+html.escape(candidate['notes'])+'</p><a target="_blank" rel="noreferrer" href="'+html.escape(candidate['source']['page_url'],quote=True)+'">查看来源帖子</a></article>')
    report=manifest['execution_report']
    body='<!doctype html><html lang="zh-CN"><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>AGY本轮摄影参考</title><style>body{margin:0;background:#f5f3ed;color:#242824;font:16px/1.7 system-ui}main{max-width:960px;margin:auto;padding:24px}h1{font-size:26px}h2{font-size:20px}article{border-top:1px solid #ccc;padding:24px 0}img{display:block;max-width:100%;max-height:84vh;margin:auto}a{color:#205f43}</style><main><h1>AGY本轮摄影参考 · '+str(len(figures))+'张</h1><p>本轮自动核验通过的原图与原说明。角色/服装为模型判断，具体版本名和摄影署名未全部核实；个人喜好由你决定，无需评分提交。</p>'+(''.join(figures) or '<p>本轮没有可交付的已核验图片。</p>')+'<details><summary>本轮结果与停止原因</summary><p>'+html.escape(report['summary'])+'</p><ul>'+''.join('<li>'+html.escape(g)+'</li>' for g in report['gaps'])+'</ul></details></main></html>'
    if running:
        body=body.replace('<title>','<meta http-equiv="refresh" content="10"><title>',1)
        body=body.replace('<main>','<main><p role="status">任务仍在运行；这里只展示已经正式核验通过的图片。每10秒刷新。</p>',1)
    atomic_write(public/'index.html',body.encode('utf8'))


def write_result(path,manifest,images,*,previous_result=None,allow_omitted=()):
    from ref_lab.agent_collection import _read_result
    if previous_result is None and path.exists():previous_result=_read_result(path,manifest['job_id'])
    allowed=set(allow_omitted)
    if previous_result:
        content,previous=previous_result
        if path.exists() and path.read_bytes()!=content:raise ValueError('Result changed during collection')
        with zipfile.ZipFile(io.BytesIO(content)) as archive:
            if any(images.get(Path(c.file).name)!=archive.read(c.file) for c in previous.candidates
                   if c.id not in allowed):
                raise ValueError('Existing admitted original changed or was omitted')
        if previous.model_dump()==CandidatePackage.model_validate(manifest).model_dump():
            if not path.exists():atomic_write(path,content)
            return
        backup=path.with_name('result-'+hashlib.sha256(content).hexdigest()+'.zip')
        if backup.exists() and backup.read_bytes()!=content:raise ValueError('Previous result archive conflict')
        if not backup.exists():atomic_write(backup,content)
    path.parent.mkdir(parents=True,exist_ok=True)
    stream=io.BytesIO()
    with zipfile.ZipFile(stream,'w',zipfile.ZIP_DEFLATED) as archive:
        archive.writestr('manifest.json',json.dumps(manifest,ensure_ascii=False))
        for name,data in images.items():archive.writestr('images/'+name,data)
    atomic_write(path,stream.getvalue())


def _write_run_info(folder,job,agent,workers,*,mode):
    if (folder/'run-info.json').exists():return
    target=min(int(job.get('target_count') or 12)+max(0,int(job.get('search_extra_target') or 0)),100)
    save(folder/'run-info.json',{'job_id':job['id'],'mode':mode,
         'adapter_sha256':hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
         'agent_contract_sha256':hashlib.sha256((ROOT/'ref_lab/verified_collection.py').read_bytes()).hexdigest(),
         'reference_research_sha256':hashlib.sha256((ROOT/'ref_lab/automatic_references.py').read_bytes()).hexdigest(),
         'model':agent.model,'query_budget':MAX_GOAL_QUERIES if mode=='search_only' and job.get('goal_id') else MAX_QUERIES,
         'candidate_budget':min(MAX_IMAGES,max(24,target*3) if mode=='search_only' else max(20,target*2)),
         'search_timeout_seconds':job.get('search_timeout_seconds'),
         'windows_per_query':MAX_WINDOWS,'detail_page_budget':MAX_DETAIL_PAGES,
         'visual_call_budget':min(MAX_IMAGES,max(20,target*2)),
         'vision_workers':workers,'pid':os.getpid(),'started_at':time.time(),'binding':job_binding(job,agent.model)})


def _job_project_id(job) -> str:
    """The verifiable project identity of a collection job."""
    snapshot = job.get('project_snapshot') or {}
    return str(job.get('project_id') or snapshot.get('id') or '')


def _validated_history_scope(*args, **kwargs):
    try:
        return collect_history_scope(*args, **kwargs)
    except (OSError, ValueError) as exc:
        raise HistoryIntegrityBlocked('History bytes or keeper validation failed') from exc


def _history_for_search(folder, project_id):
    common=Path(subprocess.check_output(['git','rev-parse','--git-common-dir'],cwd=ROOT,text=True).strip())
    canonical=(ROOT/common).resolve().parent
    history_roots=[canonical,*[Path(p) for p in json.loads(os.environ.get('LAB_COLLECTION_HISTORY_ROOTS','[]'))]]
    skipped_history=[]
    unattributed_history=[]
    scope=_validated_history_scope(ROOT,folder,project_id,history_roots=history_roots,
                                   skipped=skipped_history,unattributed=unattributed_history)
    goal=read_json(folder/'goal.json',{})
    if goal:
        from ref_lab.collection_history import goal_baseline
        baseline=goal_baseline(folder,goal)
    history=ImageHistory(scope.paths,cache_path=ROOT/'.local/history-fingerprints.json',
                         lazy=not bool(goal),library_keepers=scope.library_keepers)
    history.discovery_roots=history_roots
    history.skipped_runs=skipped_history
    history.unattributed_runs=unattributed_history
    history.attributed_run_dirs=scope.project_run_dirs
    history.project_id=project_id
    history.scope_report=dict(scope.report)
    if skipped_history:
        save(folder/'history-skips.json',skipped_history[-20:])
    if unattributed_history:
        # Unknown-attribution runs keep their records untouched and are
        # reported; they never fall back into a whole-library scan.
        save(folder/'history-unattributed.json',unattributed_history[-50:])
    if goal:
        if not history.ready or history.errors:
            raise AgentCallFailed('history_index_unavailable',fatal=True)
        with history._lock:
            for item in baseline['items']:
                history.known_shas.add(item['sha'])
                history.records[item['sha']]=item['fingerprint']
            history.known_count=len(history.known_shas)
        history.baseline_sha=goal['baseline_sha']

    return history


def main():
    from ref_lab.collection_checkpoint import implementation_digest
    if os.environ.get('LAB_CODE_DIGEST') and os.environ['LAB_CODE_DIGEST'] != implementation_digest():
        raise ValueError('Adapter source differs from the running server; refusing split-brain collection')
    ap=argparse.ArgumentParser(description=__doc__);ap.add_argument('task',type=Path);ap.add_argument('result',type=Path)
    ap.add_argument('--resume',type=Path,help='仅续核已保存原图；结果路径须在对应.local/collection-resumes状态目录内。')
    ap.add_argument('--vision-workers',type=int,choices=(1,2),default=2,help='最多两个独立摄影初判；1用于串行对照。')
    ap.add_argument('--search-only',action='store_true',help='搜索、下载和持久化候选原图；不研究身份参照；绑定Goal时逐张实际读图确认类型。')
    ap.add_argument('--review-only',action='store_true',help='只消费已下载候选的独立审核队列；不重新搜索。')
    ap.add_argument('--wait-search',action='store_true',help='审核继续消费 Search 在运行期间新增的候选，直到 Search 结束。')
    args=ap.parse_args();job,_=load_job_info(args.task)
    if not re.fullmatch(r'[A-Za-z0-9_-]{1,100}',job['id']):raise ValueError('Invalid job identity')
    if args.search_only and args.review_only:raise ValueError('Choose search-only or review-only, not both')
    if args.resume and (args.search_only or args.review_only):raise ValueError('Resume mode is only for the historical one-pass pipeline')
    if args.search_only:
        with resume_lock(ROOT/'.local/collection-runs'/job['id'],'search-cli.lock'):
            folder=ROOT/'.local'/'collection-runs'/job['id']/'current'
            folder.mkdir(parents=True,exist_ok=True)
            existing=read_json(folder/'search-summary.json',{})
            requested=int(job.get('target_count') or 12)+max(0,int(job.get('search_extra_target') or 0))
            extra=int(job.get('search_extra_target') or 0)
            previous_target=(int(existing.get('effective_target') or existing.get('target') or 0)
                             if isinstance(existing,dict) and existing else 0)
            terminal=isinstance(existing,dict) and existing.get('status') in ('completed','partial','blocked','failed','cancelled')
            prior=read_json(folder/'collector-state.json',{})
            continuing=(bool(extra) and previous_target<requested) or int(job.get('search_resume_generation',0))>int(prior.get('search_resume_generation',0))
            if terminal and not continuing:
                print('Search already finished; no new acquisition: '+json.dumps(existing.get('counts',{}),ensure_ascii=False))
                return
            if terminal and continuing:
                # A continued job must not be judged by the previous terminal
                # summary. Keep it for inspection, then let the new attempt write
                # a fresh receipt; a killed continue is reported as incomplete,
                # never as the old success.
                archive=folder/f'search-summary-previous-{int(time.time())}.json'
                if archive.exists():archive=folder/f'search-summary-previous-{int(time.time())}-{uuid4().hex[:6]}.json'
                (folder/'search-summary.json').replace(archive)
                print('SEARCH_CONTINUE '+json.dumps({'archived':archive.name,'extra_target':extra,
                                                     'target_total':requested},ensure_ascii=False))
            agent=AntigravityCollectionAgent(folder,target_count=int(job.get('target_count') or 12),runtime_budget=False)
            from ref_lab.collection_stages import _remaining
            agent.deadline=time.monotonic()+_remaining(job,'search')-30
            _write_run_info(folder,job,agent,1,mode='search_only')
            project_id=_job_project_id(job)
            if not project_id:
                from ref_lab.collection_stages import _summary_blocked
                _summary_blocked(job['id'],'history_integrity_blocked',
                                 '采集任务缺少可验证的项目归属（project_id）；未启动浏览器或模型，未建立任何全库查重范围。',
                                 target=int(job.get('target_count') or 0),
                                 found=len(collection_queue._received_rows(folder)))
                return
            try:
                history=_history_for_search(folder,project_id)
            except (AgentUnavailable,OSError,ValueError,KeyError) as exc:
                from ref_lab.collection_stages import _summary_blocked
                category=getattr(exc,'category','history_index_unavailable')
                detail=('历史原件缺失且无可验证保留件；排重基线不完整，未启动浏览器或模型。'
                        if category=='history_integrity_blocked'
                        else '历史基线或索引无法验证；未启动浏览器或模型：'+type(exc).__name__)
                _summary_blocked(job['id'],category,detail,
                                 target=int(job.get('target_count') or 0),
                                 found=len(collection_queue._received_rows(folder)))
                return
            save(folder/'history-index.json',{'project_id':project_id,'scope':getattr(history,'scope_report',{}),
                                              'unattributed_runs':len(getattr(history,'unattributed_runs',[]) or []),
                                              'library_keepers':len(getattr(history,'library_keepers',{}) or {}),
                                              'images':list(history.records.values()),
                                              'fingerprint_stats':getattr(history,'fingerprint_stats',{}),
                                              'lazy':not bool(job.get('goal_id')),'ready':history.ready,'known_shas':history.known_count,
                                              'historical_images':history.known_count})
            try:
                browser=Browser(folder);browser.cover_cache_path=ROOT/'.local/cover-duplicate-cache.json'
                summary,_=collect(job,agent,browser,folder,history=history,workers=1,search_only=True)
            finally:
                history.close(wait=False,timeout=3)
                save(folder/'history-index.json',{'project_id':project_id,'scope':getattr(history,'scope_report',{}),
                                                  'unattributed_runs':len(getattr(history,'unattributed_runs',[]) or []),
                                                  'library_keepers':len(getattr(history,'library_keepers',{}) or {}),
                                                  'images':list(history.records.values()),
                                                  'fingerprint_stats':getattr(history,'fingerprint_stats',{}),
                                                  'lazy':not bool(job.get('goal_id')),'ready':history.ready,
                                                  'known_shas':history.known_count,
                                                  'history_errors':history.errors,
                                                  'historical_images':history.known_count})
            print('SEARCH_ONLY '+json.dumps({'found':summary.get('counts',{}).get('found',0),
                                              'stop_reason':summary.get('stop_reason',''),
                                              'first_received_seconds':summary.get('first_received_seconds'),
                                              'elapsed_seconds':summary.get('elapsed_seconds'),
                                              'model_calls':summary.get('model_calls',0),
                                              'tokens':summary.get('tokens',0)},ensure_ascii=False))
        return
    if args.review_only:
        with resume_lock(ROOT/'.local/collection-runs'/job['id'],'review-cli.lock'):
            folder=ROOT/'.local'/'collection-runs'/job['id']/'current'
            folder.mkdir(parents=True,exist_ok=True)
            agent=AntigravityCollectionAgent(folder,target_count=int(job.get('target_count') or 12))
            _write_run_info(folder,job,agent,args.vision_workers,mode='review_only')
            history=None
            save_state=read_json(folder/'collector-state.json',{})
            if save_state.get('received'):
                common=Path(subprocess.check_output(['git','rev-parse','--git-common-dir'],cwd=ROOT,text=True).strip())
                canonical=(ROOT/common).resolve().parent
                history_roots=[canonical,*[Path(p) for p in json.loads(os.environ.get('LAB_COLLECTION_HISTORY_ROOTS','[]'))]]
                try:
                    scope=_validated_history_scope(ROOT,folder,_job_project_id(job),history_roots=history_roots)
                    history=ImageHistory(scope.paths,cache_path=ROOT/'.local/history-fingerprints.json',
                                         library_keepers=scope.library_keepers)
                except HistoryIntegrityBlocked as exc:
                    # The review may not run on an unproven history: the
                    # candidates stay, the stage stops with a named reason.
                    _review_state(folder,phase='blocked',stop_reason='history_integrity_blocked',
                                  detail='历史原件缺失且无可验证保留件；排重基线不完整，审核未启动。')
                    save(folder/'review-summary.json',{'version':1,'status':'blocked',
                         'stop_reason':'history_integrity_blocked','counts':{'found':len(save_state['received']),
                         'accepted':0,'blocked':len(save_state['received']),'pending':0,'rejected':0}})
                    raise SystemExit('history_integrity_blocked: 历史原件缺失且无可验证保留件；排重基线不完整，审核未启动。')
            from ref_lab.agent_collection import stage_timeout_seconds
            deadline=time.monotonic()+max(30.0,stage_timeout_seconds('review',int(job.get('target_count') or 12))-10)
            previous=None
            if args.result.exists():
                from ref_lab.agent_collection import _read_result
                previous=_read_result(args.result,job['id'])
            manifest,images,summary=review_candidates(job,agent,folder,history=history,
                                                      wait_for_search=args.wait_search,deadline=deadline)
            human=collection_queue.human_items(folder)
            omitted={('verified-'+sha[:20]) for sha,item in human.items()
                     if (item or {}).get('decision')=='reject'}
            write_result(args.result,manifest,images,previous_result=previous,allow_omitted=omitted)
            print('REVIEW_ONLY '+json.dumps({'accepted':summary.get('counts',{}).get('accepted',0),
                                              'rejected':summary.get('counts',{}).get('rejected',0),
                                              'blocked':summary.get('counts',{}).get('blocked',0),
                                              'pending':summary.get('counts',{}).get('pending',0),
                                              'stop_reason':summary.get('stop_reason',''),
                                              'elapsed_seconds':summary.get('elapsed_seconds'),
                                              'model_calls':summary.get('model_calls',0),
                                              'tokens':summary.get('tokens',0)},ensure_ascii=False))
        return
    if args.resume:
        folder=ROOT/'.local/collection-resumes'/job['id']/args.resume.resolve().name
        if not args.result.resolve().is_relative_to(folder.resolve()):raise ValueError('Resume result must stay inside its own state directory')
        manifest,images=resume_collection(job,args.resume,folder)
        stream=io.BytesIO()
        with zipfile.ZipFile(stream,'w',zipfile.ZIP_DEFLATED) as archive:
            archive.writestr('manifest.json',json.dumps(manifest,ensure_ascii=False))
            for name,data in images.items():archive.writestr('images/'+name,data)
        atomic_write(args.result,stream.getvalue())
        print(manifest['execution_report']['status']+': '+str(len(manifest['candidates']))+' verified candidates; no new search')
        return
    with resume_lock(ROOT/'.local/collection-runs'/job['id']):
        folder=ROOT/'.local'/'collection-runs'/job['id']/'current'
        folder.mkdir(parents=True,exist_ok=True)
        previous_result=None
        if args.result.exists():
            from ref_lab.agent_collection import _read_result,AttemptStop
            try:previous_result=_read_result(args.result,job['id'])
            except AttemptStop as exc:raise ValueError('Result already exists but is not a valid bound package') from exc
        recovery=os.environ.get('LAB_COLLECTION_RECOVERY_MODE','')
        imported_sha=os.environ.get('LAB_COLLECTION_IMPORTED_RESULT_SHA256','')
        if recovery or imported_sha:
            if recovery!='continue_imported_partial' or not re.fullmatch('[0-9a-f]{64}',imported_sha):
                raise ValueError('Invalid partial recovery receipt')
            if not previous_result:
                from ref_lab.agent_collection import _read_result
                previous_result=_read_result(args.result.parent/('result-'+imported_sha+'.zip'),job['id'])
            previous_bytes=previous_result[0]
            if hashlib.sha256(previous_bytes).hexdigest()!=imported_sha:raise ValueError('Imported result SHA changed')
            saved=read_json(folder/'collector-state.json',{})
            if not saved.get('final_manifest') or not saved.get('binding'):
                raise ValueError('Partial recovery requires its bound collector checkpoint')
            load_checkpoint(folder,job,saved['binding']['model'])
        elif previous_result:
            saved=read_json(folder/'collector-state.json',{})
            if not saved.get('binding'):raise ValueError('Existing result has no bound collector checkpoint')
            saved=load_checkpoint(folder,job,saved['binding']['model'])
            if CandidatePackage.model_validate(saved['final_manifest'])!=previous_result[1]:
                raise ValueError('Existing result differs from its checkpoint')
            originals={Path(row['original_path']).name:original_bytes(row,folder) for row in saved['received']}
            with zipfile.ZipFile(io.BytesIO(previous_result[0])) as archive:
                if any(c.file not in archive.namelist() or archive.read(c.file)!=originals.get(Path(c.file).name) for c in previous_result[1].candidates):
                    raise ValueError('Existing result original bytes changed')
            print('Existing verified result reused; no new collection')
            return
        agent=AntigravityCollectionAgent(folder,target_count=int(job.get('target_count') or 12));browser=Browser(folder)
        browser.cover_cache_path=ROOT/'.local/cover-duplicate-cache.json'
        if not (folder/'run-info.json').exists():save(folder/'run-info.json',{'job_id':job['id'],'adapter_sha256':hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
             'agent_contract_sha256':hashlib.sha256((ROOT/'ref_lab/verified_collection.py').read_bytes()).hexdigest(),
             'reference_research_sha256':hashlib.sha256((ROOT/'ref_lab/automatic_references.py').read_bytes()).hexdigest(),
             'model':agent.model,'query_budget':MAX_QUERIES,'windows_per_query':MAX_WINDOWS,'detail_page_budget':MAX_DETAIL_PAGES,
             'visual_call_budget':min(MAX_IMAGES,max(20,min(int(job.get('target_count') or 12),100)*2)),
             'vision_workers':args.vision_workers,'pid':os.getpid(),'started_at':time.time(),'binding':job_binding(job,agent.model)})
        saved_state=read_json(folder/'collector-state.json',{})
        sealed=saved_state.get('final_manifest') and saved_state.get('terminal',saved_state.get('outcome')=='complete')
        history=None
        if not sealed:
            common=Path(subprocess.check_output(['git','rev-parse','--git-common-dir'],cwd=ROOT,text=True).strip())
            canonical=(ROOT/common).resolve().parent
            history_roots=[canonical,*[Path(p) for p in json.loads(os.environ.get('LAB_COLLECTION_HISTORY_ROOTS','[]'))]]
            with agent.timing.span('history_index'):
                try:
                    scope=_validated_history_scope(ROOT,folder,_job_project_id(job),history_roots=history_roots)
                    history=ImageHistory(scope.paths,cache_path=ROOT/'.local/history-fingerprints.json',
                                         library_keepers=scope.library_keepers)
                except HistoryIntegrityBlocked as exc:
                    save(folder/'history-index.json',{'ready':False,'history_errors':[
                        {'code':'history_integrity_blocked','error':str(exc)[:200]}]})
                    raise SystemExit('history_integrity_blocked: 历史原件缺失且无可验证保留件；排重基线不完整，未启动采集。')
            history.discovery_roots=history_roots
            history.project_id=_job_project_id(job)
            history.scope_report=dict(scope.report)
            history.unattributed_runs=scope.unattributed_runs
            history.attributed_run_dirs=scope.project_run_dirs
            save(folder/'history-index.json',{'project_id':history.project_id,'scope':history.scope_report,
                                             'unattributed_runs':len(getattr(history,'unattributed_runs',[]) or []),
                                             'library_keepers':len(history.library_keepers),
                                             'images':list(history.records.values()),'historical_images':history.known_count,
                                             'fingerprint_stats':getattr(history,'fingerprint_stats',{})})
        print('Read-only gallery (updates during collection): '+str(folder/'public/index.html'),flush=True)
        manifest,images=collect(job,agent,browser,folder,history=history,workers=args.vision_workers)
        with agent.timing.span('final_export'):
            write_result(args.result,manifest,images,previous_result=previous_result)
    print(manifest['execution_report']['status']+': '+str(len(manifest['candidates']))+' verified candidates')
    print('Read-only gallery: '+str(folder/'public/index.html'))


if __name__=='__main__':main()
