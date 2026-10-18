"""Normal collection adapter: adaptive discovery, Agent verification, schema3 only."""
from __future__ import annotations

import argparse
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
from contextlib import contextmanager

ROOT=Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:sys.path.insert(0,str(ROOT))

import httpx
from PIL import Image

from ref_lab.models import CandidatePackage
from ref_lab.verified_collection import AntigravityCollectionAgent,AgentUnavailable,CollectionVision,accepted,query_steps,reference_supported,scope_sha
from ref_lab.storage import atomic_write
from ref_lab.collection_history import ImageHistory,historical_paths
from tools.collect_adapter import load_job_info,select_browserskill,fetch_pinterest_detail_metadata
from tools.exact_recall import assess_search,capture_note,save

MAX_QUERIES=8
MAX_IMAGES=200
SAMPLE_PER_QUERY=8
MAX_WINDOWS=3
MAX_DETAIL_PAGES=96


class SourceBlocked(ValueError):
    pass


def fatal_visual_error(exc):
    return getattr(exc,'fatal',False) or getattr(exc,'code','') in ('unexpected_tool','unexpected_read')


def verified_candidate(row,result,project,references,query='',discovery_url=''):
    sha=result.asset_sha
    return {'id':'verified-'+sha[:20],'file':'images/'+Path(row['original_path']).name,
            'title':project['character']+' · '+(result.observed_costume[:70] or '已逐图核验'),
            'source':{'page_url':row['page_url'],'image_url':row['image_url'],'author':'','search_query':query,
                      'rights':'unknown','source_confirmed':False,'obtained_as':'platform_variant'},
            'discovery_intent':'exact_character','discovery_url':discovery_url,
            'discovery_reason':'多语言发现后独立看图核验；不是搜索词或标题推断。','notes':result.reason,
            'preflight':{'content_type':'real_person_cosplay','identity_prediction':'match','confidence':result.confidence,
                         'visual_evidence':result.kind_evidence+result.identity_evidence+result.costume_evidence+['识别参照：'+r['page_url'] for r in references],
                         'reason':result.reason}}


@contextmanager
def resume_lock(folder):
    folder.mkdir(parents=True,exist_ok=True)
    with (folder/'resume.lock').open('a+b') as handle:
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
    info=load(source/'run-info.json');received=load(source/'received.json');original=load(source/'visual-audit.json')
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
    names=['run-info.json','received.json','visual-audit.json','reference-research/report.json','manifest.json','counts.json']
    binding={'job_id':job['id'],'context_sha':context,'source':str(source),'files':{n:sha(source/n) for n in names if (source/n).exists()},
             'image_shas':[r['asset_sha'] for r in received],'reference_shas':[r['asset_sha'] for r in references],'model':info['model']}
    state=folder/'resume-inputs.json'
    if state.exists() and load(state)!=binding:raise AgentUnavailable('续核输入/要求变化；未继承旧断点。')
    if not state.exists():
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
    output={'schema_version':3,'job_id':job['id'],'batch_id':uuid4().hex,'candidates':candidates,'execution_report':{
        'producer':agent.producer,'status':'blocked' if pending else 'completed',
        'summary':f'仅续核已保存候选，完成{len(received)-pending}/{len(received)}，AGY通过{len(candidates)}；本次新搜索0。',
        'source_checks':[],'query_log':[],'gaps':list(dict.fromkeys(failures))[:25]+([f'{pending}张仍未完成视觉执行。'] if pending else [])}}
    CandidatePackage.model_validate(output);save(folder/'manifest.json',output)
    return output,images

SEARCH_JS=r"""(() => {
 const visible=x=>{const r=x.getBoundingClientRect();return r.width>0&&r.height>0};
 const text=document.body.innerText;
 const login=Array.from(document.querySelectorAll('[role="dialog"],.login-container,.login-box'))
   .some(x=>visible(x)&&/登录|登入|扫码|Log in|Sign up/.test(x.innerText));
 const challenge=!!document.querySelector('iframe[src*="captcha"]')||/访问过于频繁|验证后继续|Verify you are human/.test(text);
 const source=location.hostname.includes('xiaohongshu')?'xiaohongshu':'pinterest';
 let cards=[];
 if(source==='xiaohongshu'){
  cards=Array.from(document.querySelectorAll('section')).filter(x=>x.querySelector('img'))
   .map(x=>({text:x.innerText,page:x.querySelector('a[href*="/explore/"],a[href*="/search_result/"]')?.href}));
 }else{
  cards=Array.from(document.images).filter(x=>x.naturalWidth>=200&&x.naturalHeight>=200)
   .map(x=>({text:x.alt,page:x.closest('a')?.href})).filter(x=>x.page&&/\/pin\/\d+\//.test(x.page));
 }
 const seen=new Set();cards=cards.filter(x=>x.page&&!seen.has(x.page)&&seen.add(x.page)).slice(0,60);
 return {url:location.href,search:document.querySelector('input[placeholder],textarea[placeholder]')?.value,
         visibleMain:text.slice(0,8000),cards,login_required:login,challenge};
})()"""


class Browser:
    def __init__(self,folder:Path):
        self.folder=folder;self.session=None;self.bsk=None;self.env={**os.environ,'BSK_AUTO_START':'0'}

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

    def search(self,step):
        self.scroll_windows=0
        q=quote(step['query'])
        url=('https://www.pinterest.com/search/pins/?q='+q if step['source']=='pinterest'
             else 'https://www.xiaohongshu.com/search_result?keyword='+q)
        self.command('navigate',url,'--session',self.session,'--wait-until','domcontentloaded','--timeout','25s')
        snapshot={}
        for attempt in range(3):
            snapshot=self.snapshot()
            if snapshot.get('cards') or snapshot.get('login_required') or snapshot.get('challenge'):break
            if '找不到與這個搜尋條件相符的 Pin' in snapshot.get('visibleMain',''):break
            if attempt<2:time.sleep(1)
        return snapshot

    def more(self,step):
        self.scroll_windows+=1
        self.command('wheel','--delta-y',str(1800*self.scroll_windows),'--session',self.session,'--timeout','10s',timeout=15)
        time.sleep(1)
        return self.snapshot()

    def receive(self,card,step):
        page=card['page'];source=step['source']
        self.return_failed=False
        try:
            if source=='xiaohongshu':
                match=re.search(r'/(?:explore|search_result)/([a-f0-9]{24})',urlsplit(page).path)
                if not match:return []
                note=match.group(1)
                self.command('click','--selector',f'a.cover[href*="{note}"]','--session',self.session)
                visible=self.snapshot()
                if visible.get('login_required') or visible.get('challenge'):
                    raise SourceBlocked('登录或验证门槛')
                if '/404' in urlsplit(visible.get('url','')).path:
                    return []
                canonical='https://www.xiaohongshu.com/explore/'+note
                return capture_note(self.bsk,self.session,self.folder,canonical,limit=3)
            detail=fetch_pinterest_detail_metadata(self.bsk,self.session,page,self.env)
            if detail.get('is_login_wall'):raise SourceBlocked('登录门槛')
            url=detail.get('image_url')
            if not url:return []
            with httpx.stream('GET',url,timeout=15,follow_redirects=False) as response:
                response.raise_for_status();content=bytearray()
                for chunk in response.iter_bytes():
                    content.extend(chunk)
                    if len(content)>20*1024*1024:raise ValueError('Image exceeds size limit')
            raw=bytes(content)
            with Image.open(io.BytesIO(raw)) as image:
                image.load();width,height=image.size;fmt=image.format
            ext={'JPEG':'jpg','PNG':'png','WEBP':'webp','AVIF':'avif'}.get(fmt)
            if ext is None:return []
            sha=hashlib.sha256(raw).hexdigest();path=self.folder/'images'/f'{sha}.{ext}'
            path.parent.mkdir(exist_ok=True)
            if not path.exists():path.write_bytes(raw)
            elif hashlib.sha256(path.read_bytes()).hexdigest()!=sha:raise ValueError('Immutable image conflict')
            return [{'asset_sha':sha,'original_path':str(path.resolve()),'page_url':page,'image_url':url,
                     'source_text':detail.get('title','')+'\n'+detail.get('desc',''),'width':width,'height':height}]
        finally:
            # Restore the same search page; do not start another query or inspect a related feed.
            try:self.command('navigate-back','--session',self.session,'--timeout','5s',timeout=15)
            except (ValueError,OSError,subprocess.SubprocessError):self.return_failed=True

    def close(self):
        if self.session:self.command('session','stop',self.session,timeout=10)


def collect(job:dict,agent,browser,folder:Path,*,history=None)->tuple[dict,dict[str,bytes]]:
    project={**job['project_snapshot'],'notes':job.get('notes','')}
    requested=int(job.get('target_count') or 12);target=min(requested,100)
    agent.candidate_limit=min(MAX_IMAGES,max(20,target*2))
    sources=job.get('preferred_sources') or ['xiaohongshu','pinterest']
    candidates=[];images={};queries=[];checks={};seen=set();pages=set();audit=[];received=[];collisions=[];duplicates=[];gaps=[];blocked=False;reviewed=0;attempted=0;details=0;windows=0;stop_reason=''
    started=time.monotonic()
    calls=lambda:getattr(agent,'candidate_calls',attempted)
    def limit_reason():
        if len(candidates)>=target:return 'soft_target_reached'
        if time.monotonic()>=getattr(agent,'deadline',float('inf'))-30:return 'time_budget_exhausted'
        if len(received)>=agent.candidate_limit or calls()>=agent.candidate_limit:return 'visual_budget_exhausted'
        if details>=MAX_DETAIL_PAGES:return 'detail_budget_exhausted'
        return ''
    def checkpoint(phase='collecting'):
        save(folder/'progress.json',{'phase':phase,'stop_reason':stop_reason,'soft_target':target,
             'accepted':len(candidates),'received':len(received),'reviewed':reviewed,'duplicates':len(duplicates),
             'queries':len(queries),'visible_windows':windows,'detail_pages':details,
             'vision_cli_calls':getattr(agent,'vision_cli_calls',calls()),'wall_seconds':round(time.monotonic()-started,3)})
    try:
        checkpoint('planning')
        plan=agent.plan(project)
        steps=query_steps(project,plan,sources)
        save(folder/'name-plan.json',{'plan':plan.model_dump(),'steps':steps,'origin':'agent_discovery_hypothesis'})
        if not steps:raise AgentUnavailable('当前所选来源没有正式适配器；未静默改用其他来源。')
        try:agent.prepare(project,plan)
        except AgentUnavailable as exc:
            gaps.append('参照阶段：'+str(exc))
            if fatal_visual_error(exc):raise
        agent.references=agent.references or []
        browser.start()
        for step in steps[:MAX_QUERIES]:
            source=step['source'];query=step['query']
            if checks.get(source,{}).get('status') in ('login_required','blocked'):continue
            stop_reason=limit_reason()
            if stop_reason:break
            kept=0;reason='';before=len(candidates)
            try:
                for window in range(MAX_WINDOWS):
                    stop_reason=limit_reason()
                    if stop_reason:break
                    if window and not hasattr(browser,'more'):break
                    snapshot=browser.search(step) if window==0 else browser.more(step)
                    windows+=1
                    save(folder/f'search-{len(queries)+1}-window-{window+1}.json',snapshot)
                    assessment=assess_search(snapshot,query,{'character':project['character'],'costume':project.get('costume','')})
                    if snapshot.get('login_required') or snapshot.get('challenge'):
                        checks[source]={'source':source,'status':'blocked','detail':'正常页面出现登录或验证门槛，已停止此来源。'}
                        reason='login_or_challenge';break
                    if assessment['action'] in ('STOP_STALE_QUERY','REVIEW_QUERY_REWRITE','CHANGE_QUERY_OR_SOURCE'):
                        reason=assessment['action'];break
                    checks[source]={'source':source,'status':'usable','detail':'实际查询正常页面；交付数量只计视觉通过。'}
                    inspected=0;window_before=len(received);kept_before=len(candidates)
                    for card in snapshot.get('cards',[]):
                        stop_reason=limit_reason()
                        if inspected>=SAMPLE_PER_QUERY or stop_reason:break
                        parsed=urlsplit(card['page'])
                        if parsed.scheme!='https' or not parsed.hostname:continue
                        page_key=parsed.hostname+parsed.path
                        if page_key in pages:continue
                        pages.add(page_key)
                        inspected+=1;details+=1;per_note=0
                        try:rows=browser.receive(card,step)
                        except SourceBlocked:
                            checks[source]={'source':source,'status':'blocked','detail':'已停止受登录/验证限制的来源，尝试其他授权来源。'}
                            reason='login_or_challenge';break
                        except ValueError:
                            reason='detail_unavailable';continue
                        for row in rows:
                            sha=row['asset_sha']
                            if sha in seen:
                                duplicates.append({'asset_sha':sha,'page_url':row['page_url'],'duplicate_of':sha,'reason':'same_bytes_this_run'});continue
                            if len(candidates)>=target or calls()>=agent.candidate_limit or len(received)>=agent.candidate_limit or per_note>=3:break
                            if (sha in {r['asset_sha'] for r in agent.references}
                                    or not Path(row['original_path']).resolve().is_relative_to((folder/'images').resolve())):
                                seen.add(sha);collisions.append({'asset_sha':sha,'page_url':row['page_url'],'reason':'reference media or wrong namespace; never photography'});continue
                            if hashlib.sha256(Path(row['original_path']).read_bytes()).hexdigest()!=sha:
                                raise AgentUnavailable('收到的原图SHA不一致；停止，不采用未绑定图片。')
                            seen.add(sha)
                            if history is not None:
                                duplicate=history.consider(Path(row['original_path']))
                                if duplicate:
                                    duplicates.append({'asset_sha':sha,'page_url':row['page_url'],**duplicate})
                                    save(folder/'duplicates.json',duplicates);checkpoint();continue
                            row={**row,'search_query':query,'discovery_url':snapshot['url']}
                            received.append(row);attempted+=1;per_note+=1
                            save(folder/'received.json',received)
                            try:
                                result=agent.review(Path(row['original_path']),project)
                            except AgentUnavailable as exc:
                                gap='视觉执行：'+str(exc)
                                if gap not in gaps:gaps.append(gap)
                                blocked=True
                                audit.append({'asset_sha':sha,'source_page':row['page_url'],'review':None,'accepted':False,
                                              'decision':'NEEDS_EVIDENCE','execution_error':str(exc)})
                                save(folder/'visual-audit.json',audit)
                                checkpoint()
                                if fatal_visual_error(exc):raise
                                continue
                            reviewed+=1
                            valid=accepted(result,project,references=agent.references)
                            verdict='CONFIRMED' if valid else ('MISMATCH' if result.kind not in ('cosplay_photo','portrait_photo','unknown') or (result.identity=='match' and result.costume=='mismatch' and reference_supported(result,agent.references)) else 'NEEDS_EVIDENCE')
                            audit.append({'asset_sha':sha,'source_page':row['page_url'],'review':result.model_dump(),'accepted':valid,'decision':verdict})
                            save(folder/'visual-audit.json',audit)
                            checkpoint()
                            if not valid:continue
                            raw=Path(row['original_path']).read_bytes()
                            if hashlib.sha256(raw).hexdigest()!=result.asset_sha:raise AgentUnavailable('核验后的图片字节变化；未导入。')
                            filename=Path(row['original_path']).name
                            candidates.append(verified_candidate(row,result,project,agent.references,query,snapshot['url']))
                            images[filename]=raw;kept+=1;checkpoint()
                        if getattr(browser,'return_failed',False):
                            reason='search_return_unconfirmed_change_query';break
                    checkpoint()
                    if reason=='login_or_challenge' or getattr(browser,'return_failed',False):break
                    if not inspected:
                        reason='no_new_visible_posts_change_query';break
                    if len(received)>window_before and len(candidates)==kept_before:
                        reason='no_verified_match_change_name_or_source';break
                    reason=reason or ('verified_matches' if len(candidates)>before else 'no_verified_match_change_name_or_source')
            except AgentUnavailable:raise
            except (ValueError,OSError,subprocess.SubprocessError,httpx.HTTPError):reason='source_or_detail_failed_change_source'
            finally:
                queries.append({'source':source,'query':query,'kept':kept,'stop_reason':reason or 'agent_blocked'})
                checkpoint()
    except AgentUnavailable as exc:
        blocked=True;gaps.append(str(exc))
        category=getattr(exc,'category','')
        stop_reason=({'time_budget_exhausted':'time_budget_exhausted','call_budget_exhausted':'visual_budget_exhausted'}.get(category)
                     or ('unrecoverable_agent_failure' if fatal_visual_error(exc) else 'agent_failure'))
    finally:
        stop_reason=stop_reason or limit_reason() or 'search_plan_exhausted'
        try:browser.close()
        except (ValueError,OSError,subprocess.SubprocessError):gaps.append('本轮浏览器会话清理未确认，请检查自有会话。');blocked=True
        save(folder/'received.json',received);save(folder/'visual-audit.json',audit);save(folder/'reference-collisions.json',collisions)
        save(folder/'duplicates.json',duplicates);checkpoint('finished')
        save(folder/'counts.json',{'attempted_visual_calls':calls(),'unique_images_received':len(received),'unique_images_inspected':reviewed,'completed_image_reviews':reviewed,
                                  'accepted':len(candidates),'reference_collisions':len(collisions),
                                  'needs_evidence':sum(r['decision']=='NEEDS_EVIDENCE' for r in audit),
                                  'execution_unreviewed':sum(r.get('review') is None for r in audit),
                                  'vision_cli_calls':getattr(agent,'vision_cli_calls',calls()),
                                  'historical_images':getattr(history,'initial_count',0),'duplicates':len(duplicates),
                                  'detail_pages':details,'visible_windows':windows,'stop_reason':stop_reason})
    for source in sources:
        if source not in checks:checks[source]={'source':source,'status':'untested','detail':'预算或前置Agent阻断；未实际确认来源。'}
    if len(candidates)<requested:gaps.append(f'已视觉确认{len(candidates)}/{requested}；不以未知或错误图片凑数。')
    gaps.append('自动停止原因：'+stop_reason)
    manifest={'schema_version':3,'job_id':job['id'],'batch_id':uuid4().hex,
              'candidates':candidates,'execution_report':{'producer':agent.producer,
              'status':'completed' if candidates and not blocked else 'blocked',
              'summary':f'Agent逐图确认{len(candidates)}张，实际检查{reviewed}张不同图片、摄影核验调用{calls()}次；自动识别参照独立保存，未混入摄影候选。'+(' '.join(gaps) if blocked else ''),
              'source_checks':list(checks.values()),'query_log':queries,'gaps':gaps}}
    CandidatePackage.model_validate(manifest)
    save(folder/'manifest.json',manifest)
    return manifest,images


def render_result(folder,manifest,images):
    """A read-only view of the original Agent output, without Root selection."""
    public=folder/'public';public.mkdir(exist_ok=True);figures=[]
    for i,candidate in enumerate(manifest['candidates'],1):
        name=Path(candidate['file']).name;raw=images[name];target=public/name
        if target.exists() and target.read_bytes()!=raw:raise ValueError('Immutable gallery image conflict')
        if not target.exists():atomic_write(target,raw)
        figures.append('<article><h2>'+str(i)+' · '+html.escape(candidate['title'])+'</h2><img src="'+html.escape(name,quote=True)+'" alt="AGY摄影参考'+str(i)+'"><p>'+html.escape(candidate['notes'])+'</p><a target="_blank" rel="noreferrer" href="'+html.escape(candidate['source']['page_url'],quote=True)+'">查看来源帖子</a></article>')
    report=manifest['execution_report']
    body='<!doctype html><html lang="zh-CN"><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>AGY本轮摄影参考</title><style>body{margin:0;background:#f5f3ed;color:#242824;font:16px/1.7 system-ui}main{max-width:960px;margin:auto;padding:24px}h1{font-size:26px}h2{font-size:20px}article{border-top:1px solid #ccc;padding:24px 0}img{display:block;max-width:100%;max-height:84vh;margin:auto}a{color:#205f43}</style><main><h1>AGY本轮摄影参考 · '+str(len(figures))+'张</h1><p>本轮自动核验通过的原图与原说明。角色/服装为模型判断，具体版本名和摄影署名未全部核实；个人喜好由你决定，无需评分提交。</p>'+(''.join(figures) or '<p>本轮没有可交付的已核验图片。</p>')+'<details><summary>本轮结果与停止原因</summary><p>'+html.escape(report['summary'])+'</p><ul>'+''.join('<li>'+html.escape(g)+'</li>' for g in report['gaps'])+'</ul></details></main></html>'
    atomic_write(public/'index.html',body.encode('utf8'))


def main():
    ap=argparse.ArgumentParser(description=__doc__);ap.add_argument('task',type=Path);ap.add_argument('result',type=Path)
    ap.add_argument('--resume',type=Path,help='仅续核已保存原图；结果路径须在对应.local/collection-resumes状态目录内。')
    args=ap.parse_args();job,_=load_job_info(args.task)
    if not re.fullmatch(r'[A-Za-z0-9_-]{1,100}',job['id']):raise ValueError('Invalid job identity')
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
    folder=ROOT/'.local'/'collection-runs'/job['id']/uuid4().hex
    folder.mkdir(parents=True)
    agent=AntigravityCollectionAgent(folder,target_count=int(job.get('target_count') or 12));browser=Browser(folder)
    save(folder/'run-info.json',{'job_id':job['id'],'adapter_sha256':hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
         'agent_contract_sha256':hashlib.sha256((ROOT/'ref_lab/verified_collection.py').read_bytes()).hexdigest(),
         'reference_research_sha256':hashlib.sha256((ROOT/'ref_lab/automatic_references.py').read_bytes()).hexdigest(),
         'model':agent.model,'query_budget':MAX_QUERIES,'windows_per_query':MAX_WINDOWS,'detail_page_budget':MAX_DETAIL_PAGES,
         'visual_call_budget':min(MAX_IMAGES,max(20,min(int(job.get('target_count') or 12),100)*2)),
         'pid':os.getpid(),'started_at':time.time()})
    history=ImageHistory(historical_paths(ROOT,folder))
    save(folder/'history-index.json',{'images':list(history.records.values()),'historical_images':history.initial_count})
    manifest,images=collect(job,agent,browser,folder,history=history)
    args.result.parent.mkdir(parents=True,exist_ok=True)
    with zipfile.ZipFile(args.result,'x',zipfile.ZIP_DEFLATED) as archive:
        archive.writestr('manifest.json',json.dumps(manifest,ensure_ascii=False))
        for name,data in images.items():archive.writestr('images/'+name,data)
    render_result(folder,manifest,images)
    print(manifest['execution_report']['status']+': '+str(len(manifest['candidates']))+' verified candidates')
    print('Read-only gallery: '+str(folder/'public/index.html'))


if __name__=='__main__':main()
