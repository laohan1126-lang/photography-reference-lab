"""Local timing records, without prompts, URLs, credentials or image contents."""
from contextlib import contextmanager
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

    @contextmanager
    def span(self,stage,**fields):
        started=time.monotonic();status='ok'
        try:yield
        except BaseException as exc:
            status=type(exc).__name__
            raise
        finally:self.event(stage,wall_seconds=round(time.monotonic()-started,6),status=status,**fields)
