"""Compare fixed receipt replay or an explicitly selected four-photo live smoke.

All outputs stay under this checkout's .local. Replay never starts a model or browser.
Live smoke uses the original model, photos, references, prompt and evidence parser;
it is a vision-stage comparison, not a complete fresh-search benchmark.
"""
from __future__ import annotations

import argparse
from collections import Counter
import hashlib
import json
from pathlib import Path
import statistics
import sys
import time

ROOT=Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:sys.path.insert(0,str(ROOT))

from ref_lab.collection_pipeline import OrderedReviews
from ref_lab.reference_cache import ReferenceCache
from ref_lab.automatic_references import ReferenceResearch
from ref_lab.verified_collection import AntigravityCollectionAgent, AgentUnavailable, CollectionVision, NamePlan, accepted, scope_sha, save_evidence


def load(path):return json.loads(path.read_text('utf8'))
def sha(path):return hashlib.sha256(path.read_bytes()).hexdigest()


def baseline(directory):
    job=load(directory/'job.json');reported=load(directory/'report.json')
    source=Path(reported['run_folder']).resolve();info=load(source/'run-info.json')
    rows=load(source/'received.json');audit=load(source/'visual-audit.json')
    refs=load(source/'reference-research/report.json')['references']
    project={**job['project_snapshot'],'notes':job.get('notes','')}
    if info['job_id']!=job['id']:raise ValueError('Wrong baseline job')
    for item in rows:
        path=Path(item['original_path']).resolve()
        if not path.is_relative_to(source/'images') or sha(path)!=item['asset_sha']:raise ValueError('Baseline photo changed')
    for ref in refs:
        path=Path(ref['path']).resolve()
        if not path.is_relative_to(source/'reference-research/images') or sha(path)!=ref['asset_sha']:raise ValueError('Baseline reference changed')
    reviews={r['asset_sha']:CollectionVision.model_validate(r['review']) for r in audit if r.get('review')}
    if len(reviews)!=len(rows) or any(v.context_sha!=scope_sha(project) for v in reviews.values()):
        raise ValueError('Baseline must have one bound result per photo')
    receipts=[load(p) for p in source.glob('agent-*.json')]
    durations={};attempts=[]
    for path in source.glob('attempt-*.json'):
        record=load(path);attempts.append(record);terminal=record.get('result') or {}
        if record.get('result_type')!='CollectionVision' or terminal.get('status')!='SUCCESS':continue
        value=terminal.get('structured_output')
        if value is None:
            raw=terminal.get('response','').strip()
            if raw.startswith('```'):raw=raw.split('\n',1)[1].rsplit('```',1)[0].strip()
            try:value=json.loads(raw)
            except ValueError:continue
        try:parsed=CollectionVision.model_validate(value)
        except ValueError:continue
        if parsed.asset_sha not in reviews or parsed!=reviews[parsed.asset_sha]:continue
        if not any(r.get('result')==parsed.model_dump() and r.get('reads')==record.get('tools') for r in receipts):
            raise ValueError('Original model receipt differs from baseline result')
        durations[parsed.asset_sha]=float(terminal['duration_seconds'])
    if set(durations)!=set(reviews):raise ValueError('Baseline successful durations are incomplete')
    info_metrics={
        'evidence_level':'previous_complete_real_run','wall_seconds':load(directory/'invocation.json')['wall_seconds'],
        'accepted':sum(r['accepted'] for r in audit),'photos':len(rows),
        'vision_cli_attempts':sum(a.get('result_type')=='CollectionVision' for a in attempts),
        'all_cli_attempts':len(attempts),'model_reported_vision_seconds':sum(durations.values()),
        'median_model_reported_vision_seconds':statistics.median(durations.values()),
        'errors':dict(Counter(a.get('diagnostic',{}).get('category','unknown') for a in attempts
                             if (a.get('result') or {}).get('status')!='SUCCESS')),
        'stop_reason':load(source/'counts.json')['stop_reason'],
        'first_search_fs_approx_seconds':min(p.stat().st_mtime for p in source.glob('search-*-window-1.json'))-info['started_at']}
    return source,job,project,refs,rows,reviews,durations,info_metrics


class ReplayAgent(AntigravityCollectionAgent):
    def __init__(self,folder,model,reviews,durations,scale):
        super().__init__(folder,model=model)
        self.reviews=reviews;self.durations=durations;self.scale=scale

    def _review_once(self,path,project,*,references=None):
        image_sha=sha(path);value=self.reviews[image_sha]
        if value.context_sha!=scope_sha(project):raise ValueError('Replay context changed')
        with self._budget_lock:self.candidate_calls+=1
        if self.cancelled.wait(self.durations[image_sha]*self.scale):raise AgentUnavailable('Replay cancelled')
        return value.model_copy(deep=True)


def smoke_rows(rows,reviews,project,refs,positive_controls=False):
    positive=[r for r in rows if accepted(reviews[r['asset_sha']],project,references=refs)]
    if positive_controls:
        if len(positive)<4:raise ValueError('At least four original admitted controls are required')
        return [positive[i] for i in (0,(len(positive)-1)//3,2*(len(positive)-1)//3,len(positive)-1)]
    negative=[r for r in rows if r not in positive]
    if len(positive)>=2 and len(negative)>=2:
        selected={r['asset_sha'] for r in (positive[0],positive[-1],negative[0],negative[-1])}
        return [r for r in rows if r['asset_sha'] in selected]
    return [rows[i] for i in sorted({0,(len(rows)-1)//3,2*(len(rows)-1)//3,len(rows)-1})]


def run_photos(agent,project,rows,workers):
    queue=OrderedReviews(agent,project,workers=workers);results=[];first=None;started=time.perf_counter()
    def take():
        nonlocal first
        item=queue.pending[0][0]
        try:
            row,value,refs=queue.take()
            if value.asset_sha!=row['asset_sha'] or value.context_sha!=scope_sha(project):raise ValueError('Result binding changed')
            valid=accepted(value,project,references=refs)
            if valid and first is None:first=time.perf_counter()-started
            results.append({'asset_sha':row['asset_sha'],'review':value.model_dump(),'accepted':valid})
        except AgentUnavailable as exc:
            results.append({'asset_sha':item['asset_sha'],'review':None,'accepted':False,
                            'error':getattr(exc,'category',getattr(exc,'code',type(exc).__name__))})
            if getattr(exc,'fatal',False):raise
    stop='fixed_input_exhausted'
    try:
        for row in rows:
            while len(queue)>=workers:take()
            queue.submit(row)
            if workers==1:take()
        while queue:take()
    except AgentUnavailable:
        stop='agent_blocked'
    finally:queue.close(cancel=True)
    done={r['asset_sha'] for r in results}
    results.extend({'asset_sha':r['asset_sha'],'review':None,'accepted':False,'error':'not_completed'} for r in rows if r['asset_sha'] not in done)
    wall=time.perf_counter()-started
    attempts=[load(p) for p in agent.folder.glob('attempt-*.json')]
    passed=sum(r['accepted'] for r in results)
    tokens=sum(((a.get('result') or {}).get('usage') or {}).get('total_tokens',0) for a in attempts)
    errors=Counter(a.get('validation_failure',{}).get('code') or a.get('diagnostic',{}).get('category',a.get('termination','unknown')) for a in attempts
                   if (a.get('result') or {}).get('status')!='SUCCESS' or a.get('validation_failure'))
    metrics={'workers':workers,'wall_seconds':wall,'first_usable_seconds':first,'accepted':passed,
             'completed':sum(r['review'] is not None for r in results),'input_count':len(rows),
             'seconds_per_accepted':wall/passed if passed else None,'vision_cli_attempts':len(attempts),
             'retries':sum(a.get('attempt',1)>1 for a in attempts),'errors':dict(errors),
             'total_tokens':tokens,'tokens_per_accepted':tokens/passed if passed else None,
             'stop_reason':stop,'results':results}
    save_evidence(agent.folder/'comparison.json',metrics)
    print(json.dumps({k:v for k,v in metrics.items() if k!='results'},ensure_ascii=False),flush=True)
    return metrics


def main():
    ap=argparse.ArgumentParser(description=__doc__)
    ap.add_argument('mode',choices=('replay','smoke'))
    ap.add_argument('--baseline',type=Path,required=True,help='Preserved directory containing job/report/invocation JSON')
    ap.add_argument('--output',type=Path,required=True)
    ap.add_argument('--scale',type=float,default=.002,help='Replay-only fraction of original reported model time')
    ap.add_argument('--positive-controls',action='store_true',help='Smoke-only: four fixed, evenly spaced previously admitted photos')
    args=ap.parse_args();output=args.output.resolve()
    if not output.is_relative_to((ROOT/'.local').resolve()):raise ValueError('Benchmark output must stay in checkout .local')
    if output.exists():raise ValueError('Benchmark output already exists; previous evidence must remain unchanged')
    if not 0<args.scale<=.1:raise ValueError('Replay scale must be >0 and <=0.1')
    source,job,project,refs,rows,reviews,durations,previous=baseline(args.baseline)
    model=load(source/'run-info.json')['model'];output.mkdir(parents=True)
    if args.positive_controls and args.mode!='smoke':raise ValueError('Positive controls only apply to the explicit live smoke')
    selected=rows if args.mode=='replay' else smoke_rows(rows,reviews,project,refs,args.positive_controls)
    code={str(p.relative_to(ROOT)):sha(p) for p in [ROOT/'tools/benchmark_collection.py',ROOT/'tools/collect_verified.py',
          *[ROOT/'ref_lab'/name for name in ('verified_collection.py','automatic_references.py','reference_cache.py','collection_pipeline.py','collection_timing.py')]]}
    freeze={'mode':args.mode,'model':model,'context_sha':scope_sha(project),'input_shas':[r['asset_sha'] for r in selected],
            'reference_shas':[r['asset_sha'] for r in refs],'code':code,'maximum_live_photo_results':8,'maximum_live_cli_attempts':12,
            'new_photography_searches':0,'fixed_reference_experiment':True,
            'selection':'all' if args.mode=='replay' else ('four fixed prior-admission controls' if args.positive_controls else 'prior-admission strata, preserving original order')}
    save_evidence(output/'freeze.json',freeze)
    cache=ReferenceCache(ROOT/'.local/reference-cache')
    started=time.perf_counter();entry=cache.seal(source,project,model)
    seed_seconds=time.perf_counter()-started
    started=time.perf_counter();cached=cache.load(project,model)
    research=ReferenceResearch(None,output/'warm-references',project,NamePlan.model_validate(cached['plan']))
    cache.restore(cached,research)
    warm={'seal_existing_evidence_seconds':seed_seconds,'load_validate_copy_seconds':time.perf_counter()-started,
          'references':len(research.references),'new_reference_model_calls':0,'new_reference_searches':0}
    comparisons=[];spent=0
    for workers in (1,2):
        folder=output/f'workers-{workers}';folder.mkdir()
        agent=(ReplayAgent(folder,model,reviews,durations,args.scale) if args.mode=='replay'
               else AntigravityCollectionAgent(folder,model=model,target_count=len(selected)))
        agent.references=json.loads(json.dumps(refs))
        agent.research=None  # Fixed-reference comparison; production adaptive research remains enabled.
        agent.candidate_limit=len(selected);agent.vision_cli_limit=12-spent
        agent.deadline=min(agent.deadline,time.monotonic()+600)
        result=run_photos(agent,project,selected,workers);spent+=result['vision_cli_attempts'];comparisons.append(result)
    before,after=comparisons
    agree=sum(a.get('review') is not None and b.get('review') is not None and a['accepted']==b['accepted'] for a,b in zip(before['results'],after['results']))
    exact=before['results']==after['results']
    reference_agree=[sum(r.get('review') is not None and r['review']==reviews[r['asset_sha']].model_dump() for r in m['results']) for m in comparisons]
    report={'evidence_level':'fixed_receipt_paced_replay' if args.mode=='replay' else 'real_model_fixed_four_photo_smoke',
            'previous_complete_run':previous,'warm_reference_reuse':warm,'comparisons':comparisons,
            'admission_agreement':agree,'compared_inputs':len(selected),'exact_output_equal':exact,
            'exact_original_receipt_matches':reference_agree,
            'wall_ratio':before['wall_seconds']/after['wall_seconds'],'code_unchanged':all(sha(ROOT/p)==h for p,h in code.items()),
            'replay_time_scale':args.scale if args.mode=='replay' else None,
            'limits':['No new complete collection run','No real browser/source acquisition in this comparison',
                      'Model-reported duration includes its own tools; it is not pure inference time',
                      'Live model outputs are non-deterministic; replay equality is a separate check']}
    save_evidence(output/'report.json',report)
    if not report['code_unchanged']:raise ValueError('Code changed during benchmark')
    if args.mode=='replay' and (not exact or reference_agree!=[len(selected)]*2):raise ValueError('Replay changed original results')
    print(json.dumps({k:v for k,v in report.items() if k not in ('comparisons','previous_complete_run')},ensure_ascii=False),flush=True)


if __name__=='__main__':main()
