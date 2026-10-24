"""Local timing records, without prompts, URLs, credentials or image contents."""
from contextlib import contextmanager
import hashlib
import json
from pathlib import Path
import threading
import time


class CollectionTiming:
    def __init__(self, folder: Path):
        self.path=folder/'timings.jsonl'
        self.started=time.monotonic()
        self.lock=threading.Lock()

    def event(self,stage,**fields):
        record={'stage':stage,'at':time.time(),'elapsed_seconds':round(time.monotonic()-self.started,6),**fields}
        with self.lock:
            with self.path.open('a',encoding='utf8') as output:
                output.write(json.dumps(record,ensure_ascii=False)+'\n')

    def qualified_checkpoint(self,state,counts,*,job_id,attempt_id,collector_elapsed,cumulative_elapsed,
                             initial=False,resumed=False):
        shas=sorted(set(counts.get('goal_shas',[])));count=int(counts['usable_named'])
        if count!=len(shas):raise ValueError('Qualified count/SHA binding changed')
        timeline=state.setdefault('qualified_timeline',{'job_id':job_id,'milestones':{},'decreases':[],
            'resume_observations':[],'not_backfilled':[],'scope':'collector_canonical_checkpoint'})
        if timeline['job_id']!=job_id:raise ValueError('Qualified timeline belongs to another Job')
        previous=timeline.get('last')
        observation={'job_id':job_id,'attempt_id':attempt_id,'at':time.time(),'qualified_count':count,
            'binding_complete':bool(job_id and attempt_id),
            'collector_elapsed_seconds':round(collector_elapsed,6),'cumulative_elapsed_seconds':round(cumulative_elapsed,6),
            'qualified_shas':shas,'qualified_shas_digest':hashlib.sha256('\n'.join(shas).encode()).hexdigest(),
            'scope':'collector_canonical_checkpoint'}
        if initial and resumed:
            timeline['resume_observations'].append(observation)
            for threshold in (1,5,10,20,30):
                if (count>=threshold and str(threshold) not in timeline['milestones']
                        and threshold not in timeline['not_backfilled']):
                    timeline['not_backfilled'].append(threshold)
        changed=previous is None or previous['qualified_shas_digest']!=observation['qualified_shas_digest']
        if changed or initial:
            stage='qualified_resume_observed' if initial and resumed else 'qualified_count_observed'
            self.event(stage,**observation)
            if previous is not None and count<previous['qualified_count']:
                decrease={**observation,'previous_count':previous['qualified_count']}
                timeline['decreases'].append(decrease)
                self.event('qualified_count_decreased',**decrease)
            for threshold in (1,5,10,20,30):
                key=str(threshold)
                if (attempt_id and count>=threshold and key not in timeline['milestones']
                        and threshold not in timeline['not_backfilled'] and not (initial and resumed)):
                    milestone={**observation,'threshold':threshold}
                    timeline['milestones'][key]=milestone
                    self.event('qualified_milestone_observed',**milestone)
            timeline['last']=observation
        return timeline

    @contextmanager
    def span(self,stage,**fields):
        started=time.monotonic();status='ok'
        try:yield
        except BaseException as exc:
            status=type(exc).__name__
            raise
        finally:self.event(stage,wall_seconds=round(time.monotonic()-started,6),status=status,**fields)
