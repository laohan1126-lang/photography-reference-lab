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
from urllib.parse import quote,urlsplit
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
from ref_lab.collection_history import ImageHistory,historical_paths
from ref_lab import collection_queue
from ref_lab.collection_pipeline import OrderedReviews
from ref_lab.collection_timing import CollectionTiming
from ref_lab.collection_checkpoint import load_checkpoint,original_bytes,coverage,read_json,rule_contract,job_binding
from ref_lab.search_relevance import (classify_card, confirmed_count, exploration_count,
                                      exploration_limit, is_confirmed, relevance_counts)
from tools.collect_adapter import load_job_info,select_browserskill,fetch_pinterest_detail_metadata,NEGATIVE_TYPE_MARKERS
from tools.exact_recall import assess_search,capture_note,save

MAX_QUERIES=8
MAX_IMAGES=200
SAMPLE_PER_QUERY=8
MAX_WINDOWS=3
MAX_DETAIL_PAGES=96


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
 const text=document.body.innerText;
 const login=Array.from(document.querySelectorAll('[role="dialog"],.login-container,.login-box'))
   .some(x=>visible(x)&&/登录|登入|扫码|Log in|Sign up/.test(x.innerText));
 const challenge=Array.from(document.querySelectorAll('iframe[src*="captcha"]')).some(visible)||/访问过于频繁|验证后继续|Verify you are human/.test(text);
 const source=location.hostname.includes('xiaohongshu')?'xiaohongshu':'pinterest';
 let cards=[];
 if(source==='xiaohongshu'){
  cards=Array.from(document.querySelectorAll('section')).filter(x=>x.querySelector('img'))
   .map(x=>({text:x.innerText,page:x.querySelector('a[href*="/explore/"],a[href*="/search_result/"]')?.href}));
 }else{
  cards=Array.from(document.images).filter(x=>x.naturalWidth>=200&&x.naturalHeight>=200)
   .map(x=>({text:[x.alt,x.getAttribute('aria-label'),x.closest('[data-test-id="pin"], [data-grid-item], [role="listitem"]')?.innerText].filter(Boolean).join('\n'),
             page:x.closest('a')?.href,cover_url:x.currentSrc||x.src,cover_width:x.naturalWidth,cover_height:x.naturalHeight}))
   .filter(x=>x.page&&/\/pin\/\d+\//.test(x.page));
 }
 const seen=new Set();cards=cards.filter(x=>x.page&&!seen.has(x.page)&&seen.add(x.page)).slice(0,60);
 return {url:location.href,search:document.querySelector('input[placeholder],textarea[placeholder]')?.value,
         visibleMain:text.slice(0,8000),cards,login_required:login,challenge,
         sort_latest:source==='xiaohongshu'&&Array.from(document.querySelectorAll('.tags.active'))
           .some(x=>!x.closest('[aria-hidden="true"]')&&x.textContent.trim()==='最新')};
})()"""


DETAIL_PROBE_JS=r"""(() => {
 const visible=x=>{const r=x.getBoundingClientRect();return r.width>0&&r.height>0
   &&(!x.checkVisibility||x.checkVisibility({checkOpacity:true,checkVisibilityCSS:true}));};
 const text=(document.body.innerText||'').slice(0,4000);
 const login=Array.from(document.querySelectorAll('[role="dialog"],.login-container,.login-box'))
   .some(x=>visible(x)&&/登录|登入|扫码|Log in|Sign up/.test(x.innerText));
 const challenge=Array.from(document.querySelectorAll('iframe[src*="captcha"]')).some(visible)
   ||/访问过于频繁|验证后继续|Verify you are human/.test(text);
 const notFound=/当前笔记暂时无法浏览|内容不存在|页面不见了|Note not found/i.test(text);
 return {url:location.href,login_required:login,challenge,not_found:notFound};
})()"""


class Browser:
    supports_sort=True
    def __init__(self,folder:Path):
        self.folder=folder;self.session=None;self.bsk=None;self.env={**os.environ,'BSK_AUTO_START':'0'}
        self.timing=None;self.preview=None;self.preview_reused=0

    def _span(self,name,**fields):
        timing=getattr(self,'timing',None)
        return timing.span(name,**fields) if timing is not None else nullcontext()

    def _probe_detail(self):
        """Cheap binding/login/404 check for a just-opened detail page."""
        data=json.loads(self.command('evaluate','--session',self.session,'--json',DETAIL_PROBE_JS))
        if data.get('ok') is not True or not isinstance(data.get('value'),dict):
            raise ValueError('Detail page read failed')
        return data['value']

    def command(self,*args,timeout=35):
        # Retry only idempotent reads/navigation; never repeat a click or challenge.
        attempts=2 if args[0] in ('navigate','navigate-back','evaluate') else 1
        for attempt in range(attempts):
            try:
                result=subprocess.run([self.bsk,*args],capture_output=True,text=True,encoding='utf8',errors='replace',env=self.env,timeout=timeout)
                if result.returncode:raise ValueError('BrowserSkill action failed')
                return result.stdout
            except (ValueError,subprocess.TimeoutExpired):
                if attempt+1==attempts:raise
                time.sleep(1)

    def start(self):
        self.bsk,browser=select_browserskill(self.env)
        if not self.bsk or not browser:raise AgentUnavailable('没有可用的已连接BrowserSkill浏览器；未安装或重启共享服务。')
        data=json.loads(self.command('session','start','--browser',browser,'--no-focus','--json'))
        self.session=data.get('session_id')
        if not self.session:raise AgentUnavailable('无法创建本轮独立浏览器会话。')

    def snapshot(self):
        data=json.loads(self.command('evaluate','--session',self.session,'--json',SEARCH_JS))
        if data.get('ok') is not True:raise ValueError('Visible page read failed')
        return data['value']

    def search(self,step,sort='relevance'):
        self.scroll_windows=0
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

    def check_duplicate(self,card,history):
        # shortcut: single primary-image Pins only; revisit when Pin galleries are collected.
        self.preview=None
        page=urlsplit(card.get('page',''));url=card.get('cover_url','');parsed=urlsplit(url)
        if (page.scheme!='https' or page.username or page.password or page.hostname not in ('pinterest.com','www.pinterest.com')
                or not re.fullmatch(r'/pin/\d+/?',page.path) or parsed.scheme!='https' or parsed.username or parsed.password
                or not (parsed.hostname=='pinimg.com' or (parsed.hostname or '').endswith('.pinimg.com'))
                or min(card.get('cover_width',0),card.get('cover_height',0))<200):return None
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
            previews=self.folder/'discovery-previews';previews.mkdir(exist_ok=True)
            if previews.is_symlink() or not previews.resolve().is_relative_to(self.folder.resolve()):return None
            path=previews/(sha+'.'+ext)
            if path.is_symlink():return None
            if not path.exists():atomic_write(path,raw)
            elif path.read_bytes()!=raw:return None
            self.preview={'url':url,'sha':sha,'path':str(path.resolve())}
            match=history.match(path)
            if match:return {**match,'reason':'visible_cover_matches_history','preview_match':match['reason'],
                             'asset_role':'discovery_preview','preview_sha256':sha,'preview_path':str(path.resolve()),
                             'observed_cover_url':url,'preview_pixel_size':list(pixels),
                             'observed_intrinsic_size':[card['cover_width'],card['cover_height']]}
        except (OSError,ValueError,httpx.HTTPError,Image.DecompressionBombError):return None
        return None

    def receive(self,card,step):
        page=card['page'];source=step['source']
        self.return_failed=False
        entered_detail=source!='xiaohongshu'
        try:
            if source=='xiaohongshu':
                match=re.search(r'/(?:explore|search_result)/([a-f0-9]{24})',urlsplit(page).path)
                if not match:return []
                note=match.group(1)
                with self._span('detail_click',source=source):
                    self.command('click','--selector',f'a.cover[href*="{note}"]','--session',self.session)
                with self._span('detail_dom_wait',source=source):
                    probe=self._probe_detail()
                entered_detail=bool(re.fullmatch(r'/(?:explore|search_result)/[a-f0-9]{24}',
                                                 urlsplit(probe.get('url','')).path))
                if probe.get('login_required') or probe.get('challenge'):
                    raise SourceBlocked('登录或验证门槛')
                if probe.get('not_found') or '/404' in str(probe.get('url','')):
                    self.return_failed=True
                    return []
                if not entered_detail:raise ValueError('Note did not open; search page preserved')
                canonical='https://www.xiaohongshu.com/explore/'+note
                errors=[]
                rows=capture_note(self.bsk,self.session,self.folder,canonical,limit=3,errors=errors,
                                  timing=getattr(self,'timing',None))
                self.download_errors=getattr(self,'download_errors',[])+errors
                return rows
            # Navigation and DOM are timed inside the adapter; an outer span here
            # duplicated the same stage name and made a naive sum double count it.
            detail=fetch_pinterest_detail_metadata(self.bsk,self.session,page,self.env,
                                                   timing=getattr(self,'timing',None))
            if detail.get('is_login_wall'):raise SourceBlocked('登录门槛')
            url=detail.get('image_url')
            if not url:return []
            with self._span('detail_download',source=source):
                raw,width,height,fmt,reused=self._pinterest_bytes(url)
            ext={'JPEG':'jpg','PNG':'png','WEBP':'webp','AVIF':'avif'}.get(fmt)
            if ext is None:return []
            sha=hashlib.sha256(raw).hexdigest();path=self.folder/'images'/f'{sha}.{ext}'
            path.parent.mkdir(exist_ok=True)
            if not path.exists():path.write_bytes(raw)
            elif hashlib.sha256(path.read_bytes()).hexdigest()!=sha:raise ValueError('Immutable image conflict')
            return [{'asset_sha':sha,'original_path':str(path.resolve()),'page_url':page,'image_url':url,
                     'source_text':detail.get('title','')+'\n'+detail.get('desc',''),'width':width,'height':height,
                     'preview_bytes_reused':reused}]
        finally:
            # Restore the same search page; do not start another query or inspect a related feed.
            try:
                if entered_detail:
                    with self._span('detail_return',source=source):
                        self.command('navigate-back','--session',self.session,'--timeout','5s',timeout=15)
            except (ValueError,OSError,subprocess.SubprocessError):self.return_failed=True

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
        if self.session:self.command('session','stop',self.session,timeout=10)


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


def collect(job:dict,agent,browser,folder:Path,*,history=None,workers=1,finalize_only=False,
            search_only=False)->tuple[dict,dict[str,bytes]]:
    project={**job['project_snapshot'],'notes':job.get('notes','')}
    requested=int(job.get('target_count') or 12)
    extra_target=int(job.get('search_extra_target') or 0)
    requested_total=requested+max(0,extra_target)
    target=min(requested_total,100)
    agent.candidate_limit=min(MAX_IMAGES,max(24,target*3) if search_only else max(20,target*2))
    sources=job.get('preferred_sources',['xiaohongshu','pinterest'])
    try:state=load_checkpoint(folder,job,getattr(agent,'model',agent.producer))
    except (OSError,ValueError,KeyError,TypeError) as exc:raise AgentUnavailable('恢复绑定或原图完整性检查失败：'+str(exc)) from exc
    if finalize_only and not state.get('final_manifest'):
        raise AgentUnavailable('本地收尾缺少已封存的最终判断；不启动新的外部调用。')
    received=state['received'];audit=state['audit'];queries=state['queries'];checks=state['checks']
    pages=set(state['pages']);page_attempts=state['page_attempts'];searches=state['searches']
    duplicates=state['duplicates'];collisions=state['collisions'];gaps=state['gaps']
    details=state['details'];windows=state['windows'];steps=state.get('steps',[])
    previous_elapsed=float(state.get('elapsed_seconds_total') or 0.0)
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
        if state.get('search_complete') and summary_exists and not extra_target:
            return saved_summary,{}
        if extra_target:
            # Same job, additional target. The local dicts are the objects that
            # ``checkpoint`` persists, so every reset must mutate them in place:
            # rebinding ``state['searches']`` alone silently restored the old
            # ``done=True`` flags on the next save. Originals, human decisions,
            # duplicate/error logs and cumulative budget counters stay untouched.
            previous_target=(int(saved_summary.get('effective_target') or saved_summary.get('target') or 0)
                             if summary_exists else 0)
            if summary_exists and previous_target>=target:
                return saved_summary,{}
            state['search_complete']=False;state['search_summary']={}
            state['search_attempts']=int(state.get('search_attempts',0))+1
            searches.clear();pages.clear()
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
            gaps.append('用户继续加搜：目标累计 %s 张；已有候选、原图与人工决定保留。' % target)
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
    collage_closed=False
    if search_only:
        from ref_lab.collage import CollageWorker
        collage_worker=CollageWorker(folder,history=history,known_shas=seen)
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
    def canonical_counts(force=False):
        """The one count used by the stop condition, summary and counts.json."""
        from ref_lab.collage import DerivedStore
        from ref_lab.collection_counts import compute
        try:
            stat=(folder/'derived.json').stat();key=(len(received),stat.st_size,stat.st_mtime_ns)
        except OSError:
            key=(len(received),0,0)
        if force or canonical_cache['key']!=key or canonical_cache['value'] is None:
            canonical_cache['value']=compute(folder,received,DerivedStore(folder).items())
            canonical_cache['key']=key
        return canonical_cache['value']
    def confirmed():
        return canonical_counts()['usable_named'] if search_only else len(candidates)
    def exploration():
        return exploration_count(received) if search_only else 0
    def limit_reason():
        if search_only:
            if confirmed()>=target:return 'target_reached'
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
        nonlocal displayed,displayed_received
        state.update(received=received,audit=audit,queries=queries,checks=checks,pages=sorted(pages),page_attempts=page_attempts,
                     searches=searches,duplicates=duplicates,collisions=collisions,gaps=gaps,details=details,windows=windows,
                     first_usable=first_usable,candidate_calls=calls(),references=getattr(agent,'references',None) or [],steps=steps,phase=phase)
        if search_only:state['search_errors']=received_errors
        reference_files=state.setdefault('reference_files',{})
        for path in (folder/'reference-research').glob('source-*.*'):
            if path.suffix in ('.html','.json'):reference_files[str(path.relative_to(folder))]=hashlib.sha256(path.read_bytes()).hexdigest()
        save(folder/'collector-state.json',state)
        save(folder/'visual-audit.json',audit)
        save(folder/'progress.json',{'phase':phase,'stop_reason':stop_reason,'soft_target':target,
             'accepted':len(candidates),'received':len(received),'reviewed':reviewed,'duplicates':len(duplicates),
             'queries':len(queries),'visible_windows':windows,'detail_pages':details,
             'vision_cli_calls':getattr(agent,'vision_cli_calls',calls()),'wall_seconds':round(time.monotonic()-started,3),
             'first_usable_seconds':first_usable,'pending_reviews':len(pending) if pending is not None else 0,'vision_workers':workers,
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
    try:
        checkpoint('planning')
        from ref_lab.verified_collection import NamePlan,deterministic_plan
        if search_only:
            if state.get('plan'):
                plan=NamePlan.model_validate(state['plan'])
                origin='saved_search_plan'
            else:
                plan=deterministic_plan(project, identity_context=job.get('identity_context'),
                                        user_aliases=job.get('search_aliases') or ())
                origin='trusted_project_names'
        else:
            with timing.span('name_plan'):
                plan=NamePlan.model_validate(state['plan']) if state.get('plan') else agent.plan(project)
            origin='agent_discovery_hypothesis'
        steps=steps or query_steps(project,plan,sources)
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
        with timing.span('browser_start'):browser.start()
        latest_fallback_sources=set()
        for pass_index in range(2*min(len(steps),MAX_QUERIES)):
            step_index=pass_index%min(len(steps),MAX_QUERIES);step=steps[step_index]
            source=step['source'];query=step['query']
            search=searches.setdefault(str(step_index),{'source':source,'query':query,'language':step.get('language','unknown'),
                                                      'observed':False,'usable':False,'window':0,'done':False,
                                                      'sort_mode':'relevance'})
            if search.get('done'):continue
            if checks.get(source,{}).get('status') in ('login_required','blocked'):continue
            if source=='xiaohongshu' and source in latest_fallback_sources and not search.get('latest_fallback_used'):
                search['sort_mode']='latest';search['latest_fallback_used']=True
            sort_mode=search.get('sort_mode','relevance')
            stop_reason=limit_reason()
            if stop_reason:break
            kept=0;reason='';before=len(candidates)
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
                    ranked=sorted(snapshot.get('cards',[]),key=lambda c:classify_card(
                        c,names=name_records,work_terms=work_terms,other_terms=other_terms)['rank'])
                    for card in ranked:
                        if not search_only:
                            while pending and pending.pending[0][1] is not None and pending.pending[0][1].done():finish_one()
                            while pending and len(candidates)+len(pending)>=target:finish_one()
                        stop_reason=limit_reason()
                        if inspected>=SAMPLE_PER_QUERY or stop_reason:break
                        parsed=urlsplit(card['page'])
                        if parsed.scheme!='https' or not parsed.hostname:continue
                        page_key=parsed.hostname+parsed.path
                        if page_key in pages:continue
                        new_cards+=1
                        relevance=classify_card(card,names=name_records,work_terms=work_terms,
                                                other_terms=other_terms)
                        if search_only and relevance['tier']=='other_character':
                            skipped['other_character']+=1;pages.add(page_key);continue
                        if search_only and relevance['tier']=='non_photo':
                            skipped['non_photo']+=1;pages.add(page_key);continue
                        if (search_only and relevance['tier'] in ('target_context','unconfirmed')
                                and exploration()>=exploration_limit(target)):
                            skipped['exploration_budget']+=1;pages.add(page_key);continue
                        if history is not None and hasattr(browser,'check_duplicate'):
                            with timing.span('discovery_preview'):duplicate=browser.check_duplicate(card,history)
                            if duplicate:
                                duplicates.append({'page_url':card['page'],**duplicate})
                                pages.add(page_key);save(folder/'duplicates.json',duplicates);checkpoint();continue
                        if page_attempts.get(page_key,0)>=3:
                            pages.add(page_key);gaps.append('原帖读取重试已耗尽：'+page_key);continue
                        inspected+=1
                        if page_key not in page_attempts:details+=1
                        page_attempts[page_key]=page_attempts.get(page_key,0)+1;per_note=0
                        checkpoint()
                        try:
                            with timing.span('browser_receive'):rows=browser.receive(card,step)
                        except SourceBlocked:
                            checks[source]={'source':source,'status':'blocked','detail':'已停止受登录/验证限制的来源，尝试其他授权来源。'}
                            reason='login_or_challenge';break
                        except ValueError:
                            pages.add(page_key);reason='detail_unavailable';checkpoint();continue
                        new_download_errors=getattr(browser,'download_errors',[])
                        if new_download_errors:
                            received_errors.extend(new_download_errors)
                            browser.download_errors=[]
                            save(folder/'download-errors.json',received_errors)
                        for row in rows:
                            if not search_only:
                                while pending and (len(pending)>=workers or len(candidates)+len(pending)>=target):finish_one()
                            sha=row['asset_sha']
                            if sha in seen:
                                duplicates.append({'asset_sha':sha,'page_url':row['page_url'],'duplicate_of':sha,'reason':'same_bytes_this_run'});continue
                            if search_only:
                                if confirmed()>=target or per_note>=3:break
                            elif len(candidates)>=target or calls()>=agent.candidate_limit or len(received)>=agent.candidate_limit or per_note>=3:
                                break
                            if (sha in {r['asset_sha'] for r in (agent.references or [])}
                                    or not Path(row['original_path']).resolve().is_relative_to((folder/'images').resolve())):
                                seen.add(sha);collisions.append({'asset_sha':sha,'page_url':row['page_url'],'reason':'reference media or wrong namespace; never photography'});continue
                            valid=True;error=''
                            if search_only:
                                valid,error=_valid_search_row(row,folder)
                            elif hashlib.sha256(Path(row['original_path']).read_bytes()).hexdigest()!=sha:
                                raise AgentUnavailable('收到的原图SHA不一致；停止，不采用未绑定图片。')
                            if not valid:
                                seen.add(sha);received_errors.append({'asset_sha':sha,'page_url':row['page_url'],'error':error})
                                save(folder/'search-errors.json',received_errors);checkpoint();continue
                            seen.add(sha)
                            if history is not None:
                                with timing.span('history_consider'):duplicate=history.consider(Path(row['original_path']))
                                if duplicate:
                                    duplicates.append({'asset_sha':sha,'page_url':row['page_url'],**duplicate})
                                    save(folder/'duplicates.json',duplicates);checkpoint();continue
                            row={**row,'search_query':query,'discovery_url':snapshot['url'],
                                 'acquired_at':time.time(),'relevance':relevance}
                            received.append(row);attempted+=1;per_note+=1
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
                        pages.add(page_key);checkpoint()
                        if getattr(browser,'return_failed',False):
                            reason='search_return_unconfirmed_change_query';break
                    if not search_only:drain();checkpoint()
                    if reason=='login_or_challenge' or getattr(browser,'return_failed',False):break
                    if not new_cards:
                        reason='no_new_visible_posts_change_query';break
                    if len(received)>window_before and len(candidates)==kept_before and not search_only:
                        reason='no_verified_match_change_name_or_source';break
                    if search_only:
                        if confirmed()>=target:
                            reason='target_reached';break
                        if confirmed()>confirmed_before:
                            reason='target_named_candidates_found'
                        elif len(received)>window_before:
                            reason='exploration_candidates_found'
                        else:
                            reason='no_new_valid_candidates'
                    else:
                        reason=reason or ('verified_matches' if len(candidates)>before else 'no_verified_match_change_name_or_source')
                    if search_only and confirmed()==confirmed_before and len(received)==window_before and source=='xiaohongshu' and sort_mode!='latest':
                        # Bounded fallback: if relevance sort found no usable name hit in this
                        # window, allow exactly one later XHS query to try 最新. Never loop.
                        latest_fallback_sources.add(source)
                    search['window']=window+1;search.pop('snapshot',None);checkpoint()
                    if pass_index<len(steps) and not coverage(steps,searches,sources)['explored']:
                        reason='bounded_breadth_next_query';break
            except AgentUnavailable:raise
            except (ValueError,OSError,subprocess.SubprocessError,httpx.HTTPError):
                reason='source_or_detail_failed_change_source'
                if not search_only:drain()
            finally:
                search['stop_reason']=reason or 'agent_blocked'
                if sys.exc_info()[0] is None:search['done']=reason!='bounded_breadth_next_query'
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
                checkpoint()
    except AgentUnavailable as exc:
        blocked=True;gaps.append(str(exc))
        category=getattr(exc,'category','')
        stop_reason=({'time_budget_exhausted':'time_budget_exhausted','call_budget_exhausted':'visual_budget_exhausted'}.get(category)
                     or ('unrecoverable_agent_failure' if fatal_visual_error(exc) else 'agent_failure'))
    except (KeyboardInterrupt,SystemExit):
        blocked=True;stop_reason='cancelled';interrupted=True
        raise
    except BaseException:
        blocked=True;stop_reason='internal_error';interrupted=True
        raise
    finally:
        if pending is not None:pending.close(cancel=True)
        if collage_worker is not None and not collage_closed:
            # The download path never waits for splitting; the bounded drain here
            # only makes the final counts and gallery complete before the summary.
            deadline=getattr(agent,'deadline',float('inf'))
            collage_worker.close(timeout=max(1.0,min(30.0,deadline-time.monotonic())))
            collage_closed=True
        if not search_only and hasattr(agent,'cache_references'):agent.cache_references(project)
        if not stop_reason and sources and all(checks.get(s,{}).get('status') in ('login_required','blocked') for s in sources):
            stop_reason='sources_blocked';blocked=True
        stop_reason=stop_reason or limit_reason() or 'search_plan_exhausted'
        confirmed_total=canonical_counts(force=True)['usable_named'] if search_only else len(candidates)
        if search_only and not interrupted:
            if stop_reason=='target_reached' and confirmed_total<target:
                # A target_reached reason must be backed by confirmed names, never downloads alone.
                stop_reason='relevance_unconfirmed' if not confirmed_total else 'target_partial'
            elif confirmed_total<target and stop_reason in ('search_plan_exhausted','no_new_valid_candidates'):
                stop_reason=('relevance_unconfirmed' if received and not confirmed_total
                             else ('target_partial' if confirmed_total else stop_reason))
        if search_only:
            if interrupted:
                status='cancelled'
            elif confirmed_total>=target:
                status='completed'
            elif received:
                status='partial'
            else:
                status='blocked'
            elapsed_total=previous_elapsed+(time.monotonic()-started)
            collage_totals=collage_worker.summary() if collage_worker is not None else {}
            canonical=canonical_counts()
            summary=write_search_summary(
                folder,status=status,stop_reason=stop_reason,received=received,queries=queries,checks=checks,
                searches=searches,started=started,
                first_received=(started+first_usable if isinstance(first_usable,(int,float)) else None),
                duplicates=duplicates,
                errors=received_errors,extra={'target':target,'target_reached':confirmed_total>=target,
                                              'requested_target':requested_total,'effective_target':target,
                                              'budget_note':('本轮上限 100 张；请求 %s 张，按 %s 张执行。' % (requested_total,target)
                                                             if requested_total>target else ''),
                                              'search_only':True,
                                              'canonical':canonical,
                                              'usable_independent_named':confirmed_total,
                                              'collage':collage_totals,
                                              'collage_errors':list(getattr(collage_worker,'errors',[]))[:10],
                                              'collage_seconds':round(getattr(collage_worker,'seconds',0.0),3),
                                              'collage_processed':int(getattr(collage_worker,'processed',0)),
                                              'preview_bytes_reused':int(getattr(browser,'preview_reused',0)),
                                              'history_restore':history_restore,
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
            state.update(search_complete=True,search_summary=summary,search_stop_reason=stop_reason,
                         phase='search_finished',first_usable=first_usable,elapsed_seconds_total=elapsed_total)
            try:browser.close()
            except (ValueError,OSError,subprocess.SubprocessError):
                gaps.append('本轮浏览器会话清理未确认，请检查自有会话。')
            save(folder/'received.json',received);save(folder/'search-errors.json',received_errors)
            save(folder/'duplicates.json',duplicates);save(folder/'reference-collisions.json',collisions)
            save(folder/'counts.json',{
                # Canonical numbers shared with the stop condition, queue API and
                # search-summary. Do not recompute them here.
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
                'preview_bytes_reused':int(getattr(browser,'preview_reused',0))})
            checkpoint('finished')
            search_summary_result=summary
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
    for row in received:
        sha=row['asset_sha'];item=items.get(sha)
        if not item or item.get('status')!='accepted':continue
        if (human.get(sha) or {}).get('decision')=='reject':continue
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


def _valid_search_row(row,folder):
    """Cheap deterministic file check; never a visual identity or quality verdict."""
    try:
        path=Path(row['original_path']).resolve()
        if path.is_symlink() or not path.is_relative_to((folder/'images').resolve()) or not path.is_file():
            return False,'original_path_outside_run'
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
        for key in ('found','target_confirmed','exploration','other_character','non_photo',
                    'original_singles','derived_valid','usable_independent','usable_named',
                    'awaiting_manual'):
            if key in canonical:
                counts[key] = canonical[key]
    summary={'version':1,'status':status,'stop_reason':stop_reason,
             'target':int(extra.get('target',0)) if extra else 0,
             'target_reached':bool(extra.get('target_reached')) if extra else False,
             'counts':counts,
             'first_received_seconds':(round(first_received-started,3)
                                       if isinstance(first_received,(int,float)) else None),
             'elapsed_seconds':round(time.monotonic()-started,3),
             'finished_at':time.time(),'queries':queries,'source_checks':list(checks.values()),
             'searches':searches,'errors':list(errors)[:20],
             'model_calls':calls,'tokens':tokens,'attempts_with_usage':with_usage,
             'counts_source':'ref_lab.collection_counts.compute',
             'model_calls_note':'快速搜图不调用名称/参照/视觉模型；此计数仅兼容历史回执。'}
    if extra:
        for key in ('target','requested_target','effective_target','target_reached','budget_note',
                    'search_only','history_ready','history_known','history_errors','source_blocked',
                    'cumulative_elapsed_seconds','continue','query_history','canonical',
                    'usable_independent_named','collage','collage_errors','collage_seconds',
                    'collage_processed','preview_bytes_reused','history_restore',
                    'skipped_other_character','skipped_non_photo','skipped_exploration_budget'):
            if key in extra:summary[key]=extra[key]
    save(folder/'search-summary.json',summary)
    return summary


def render_search_gallery(folder,rows,*,running=False):
    """Read-only fallback view of acquired originals plus their usable crops.

    Every referenced file is copied next to the page and its SHA is verified
    before the link is written, so the page never points at a missing or changed
    image. Existing copies are reused; the previous version re-read every original
    twice on every checkpoint, which was pure duplicated disk I/O.
    """
    from ref_lab.collage import DerivedStore, VALID, record_is_current
    from ref_lab.integrity import sha_matches
    public=folder/'public';public.mkdir(exist_ok=True);figures=[]
    records=DerivedStore(folder).items()
    problems=[]
    def ensure(source: Path, expected_sha: str):
        target=public/source.name
        if not target.exists():
            try:atomic_write(target,source.read_bytes())
            except OSError:
                problems.append({'file':source.name,'reason':'copy_failed'});return None
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
    for i,candidate in enumerate(manifest['candidates'],1):
        name=Path(candidate['file']).name;raw=images[name];target=public/name
        if target.exists() and target.read_bytes()!=raw:raise ValueError('Immutable gallery image conflict')
        if not target.exists():atomic_write(target,raw)
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
    save(folder/'run-info.json',{'job_id':job['id'],'mode':mode,
         'adapter_sha256':hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
         'agent_contract_sha256':hashlib.sha256((ROOT/'ref_lab/verified_collection.py').read_bytes()).hexdigest(),
         'reference_research_sha256':hashlib.sha256((ROOT/'ref_lab/automatic_references.py').read_bytes()).hexdigest(),
         'model':agent.model,'query_budget':MAX_QUERIES,'windows_per_query':MAX_WINDOWS,'detail_page_budget':MAX_DETAIL_PAGES,
         'visual_call_budget':min(MAX_IMAGES,max(20,min(int(job.get('target_count') or 12),100)*2)),
         'vision_workers':workers,'pid':os.getpid(),'started_at':time.time(),'binding':job_binding(job,agent.model)})


def _history_for_search(folder):
    common=Path(subprocess.check_output(['git','rev-parse','--git-common-dir'],cwd=ROOT,text=True).strip())
    canonical=(ROOT/common).resolve().parent
    history_roots=[canonical,*[Path(p) for p in json.loads(os.environ.get('LAB_COLLECTION_HISTORY_ROOTS','[]'))]]
    return ImageHistory(historical_paths(ROOT,folder,history_roots=history_roots),
                        cache_path=ROOT/'.local/history-fingerprints.json',lazy=True)


def main():
    ap=argparse.ArgumentParser(description=__doc__);ap.add_argument('task',type=Path);ap.add_argument('result',type=Path)
    ap.add_argument('--resume',type=Path,help='仅续核已保存原图；结果路径须在对应.local/collection-resumes状态目录内。')
    ap.add_argument('--vision-workers',type=int,choices=(1,2),default=2,help='最多两个独立摄影初判；1用于串行对照。')
    ap.add_argument('--search-only',action='store_true',help='只搜索、下载和持久化候选原图；不研究参照、不调用视觉模型。')
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
            terminal=isinstance(existing,dict) and existing.get('status') in ('completed','blocked','failed','cancelled')
            continuing=bool(extra) and previous_target<requested
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
            _write_run_info(folder,job,agent,args.vision_workers,mode='search_only')
            history=_history_for_search(folder)
            save(folder/'history-index.json',{'images':list(history.records.values()),
                                              'lazy':True,'known_shas':history.known_count,
                                              'historical_images':history.known_count})
            try:
                summary,_=collect(job,agent,Browser(folder),folder,history=history,workers=1,search_only=True)
            finally:
                history.close(wait=False,timeout=3)
                save(folder/'history-index.json',{'images':list(history.records.values()),
                                                  'lazy':True,'ready':history.ready,
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
                history=ImageHistory(historical_paths(ROOT,folder,history_roots=history_roots),
                                     cache_path=ROOT/'.local/history-fingerprints.json')
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
                history=ImageHistory(historical_paths(ROOT,folder,history_roots=history_roots),cache_path=ROOT/'.local/history-fingerprints.json')
            save(folder/'history-index.json',{'images':list(history.records.values()),'historical_images':history.known_count})
        print('Read-only gallery (updates during collection): '+str(folder/'public/index.html'),flush=True)
        manifest,images=collect(job,agent,browser,folder,history=history,workers=args.vision_workers)
        with agent.timing.span('final_export'):
            write_result(args.result,manifest,images,previous_result=previous_result)
    print(manifest['execution_report']['status']+': '+str(len(manifest['candidates']))+' verified candidates')
    print('Read-only gallery: '+str(folder/'public/index.html'))


if __name__=='__main__':main()
