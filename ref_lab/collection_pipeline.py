"""Bounded photo work; the caller alone owns browsing, research and admission."""
from collections import deque
from concurrent.futures import ThreadPoolExecutor, wait
import copy
from pathlib import Path
import time

from .policy import digest
from .verified_collection import save_evidence


class OrderedReviews:
    def __init__(self,agent,project,*,workers=1):
        if workers not in (1,2):raise ValueError('Vision workers must be 1 or 2')
        self.agent=agent;self.project=project;self.workers=workers
        self.pending=deque();self.closed=False
        self.pool=ThreadPoolExecutor(max_workers=workers,thread_name_prefix='collection-vision') if workers>1 else None

    def __len__(self):return len(self.pending)

    def submit(self,row):
        if self.closed:raise RuntimeError('Review queue is closed')
        if len(self.pending)>=self.workers:raise ValueError('Review queue is full')
        queued=time.monotonic();refs=copy.deepcopy(self.agent.references)
        def initial():
            self.agent.timing.event('vision_queue',asset_sha=row['asset_sha'],queue_wait_seconds=time.monotonic()-queued)
            return self.agent._review_once(Path(row['original_path']),self.project,references=refs)
        future=self.pool.submit(initial) if self.pool else None
        self.pending.append((row,future,refs))

    def take(self):
        row,future,refs=self.pending.popleft();path=Path(row['original_path'])
        if future is None:return row,self.agent.review(path,self.project),copy.deepcopy(self.agent.references)
        with self.agent.timing.span('ordered_commit_wait',asset_sha=row['asset_sha']):value=future.result()
        changed=digest(refs)!=digest(self.agent.references)
        if changed or self.agent.needs_supplement(value,self.project):
            # Research changes one shared reference version only after all readers finish.
            wait([f for _,f,_ in self.pending])
        if changed:
            save_evidence(self.agent.folder/('superseded-initial-'+row['asset_sha']+'.json'),
                          {'review':value.model_dump(),'references':refs,'reason':'reference_version_changed_before_commit'})
            value=self.agent.review(path,self.project)
        else:value=self.agent.complete_review(path,self.project,value)
        return row,value,copy.deepcopy(self.agent.references)

    def close(self,*,cancel=False):
        self.closed=True
        if cancel and hasattr(self.agent,'cancelled'):self.agent.cancelled.set()
        if self.pool:self.pool.shutdown(wait=True,cancel_futures=cancel)
