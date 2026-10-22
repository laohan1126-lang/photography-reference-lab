"""Run-scoped photographic admission, separate from identity and human choices."""
from __future__ import annotations

import hashlib
import json
from functools import lru_cache
import queue
import threading
import time
from pathlib import Path

from PIL import Image, ImageOps

from .classification import AntigravityClassifier, ClassificationUnavailable
from .collection_queue import read_json, write_json
from .collage import VALID, STATUS_NO_COLLAGE, _tile_quality

PHOTO_KINDS = {"cosplay_photo", "portrait_photo"}


def verified_type(item, sha):
    if not isinstance(item, dict):
        return False
    evidence = item.get("read_evidence") or {}
    result = item.get("result") or {}
    return (item.get("status") == "succeeded" and item.get("asset_sha") == sha
            and bool(item.get("producer")) and item.get("result_status") == "SUCCESS"
            and evidence.get("tool") == "view_file" and evidence.get("state") == "DONE"
            and evidence.get("asset_sha") == sha and bool(evidence.get("preview_sha"))
            and result.get("asset_sha") == sha
            and bool(result.get("evidence")))


def verified_photo(item, sha):
    return verified_type(item, sha) and item['result'].get('kind') in PHOTO_KINDS


@lru_cache(maxsize=1024)
def _native_type_result(path, size, mtime, stream_sha, image_path):
    from .classification import parse_vision_stream
    raw=Path(path).read_bytes()
    if hashlib.sha256(raw).hexdigest()!=stream_sha:
        raise ValueError('changed native stream')
    return parse_vision_stream(raw.decode('utf8'),Path(image_path)).model_dump(mode='json')


def receipt_intact(folder, item):
    """Bind the stored result to its intact native read/result, including on reuse."""
    from .classification import ClassificationResult
    from .providers import ProviderError
    if not isinstance(item, dict):
        return False
    path = Path(str(item.get('stream_path') or ''))
    if path.is_symlink() or not path.resolve().is_relative_to((Path(folder)/'type-evidence').resolve()):
        return False
    try:
        stat=path.stat()
        actual=_native_type_result(str(path.resolve()),stat.st_size,stat.st_mtime_ns,
                                   str(item.get('stream_sha') or ''),
                                   str((item.get('read_evidence') or {}).get('path') or ''))
        return actual==ClassificationResult.model_validate(item.get('result')).model_dump(mode='json')
    except (OSError,ValueError,TypeError,ProviderError):
        return False


class PhotoTypeWorker:
    """One bounded consumer, receiving only this run's actual split records."""

    def __init__(self, folder, *, analyzer=None, limit=45, model="gemini-3.8-flash-medium", history=None, deadline=float("inf")):
        self.folder = Path(folder)
        self.analyzer = analyzer or AntigravityClassifier(model, evidence_dir=self.folder/'type-evidence')
        self.limit = limit
        self.history = history
        self.deadline = deadline
        self.analyzer.deadline = deadline
        self.block_reason = ""
        self.stop = threading.Event()
        self.pending = queue.Queue()
        self.blocked = False
        self.thread = threading.Thread(target=self._run, name="candidate-photo-types", daemon=True)
        self.thread.start()

    def enqueue(self, record):
        self.pending.put(record)

    def _run(self):
        while not self.stop.is_set():
            try:
                record = self.pending.get(timeout=.2)
            except queue.Empty:
                continue
            try:
                self._process(record)
            finally:
                self.pending.task_done()

    def _process(self, record):
        if self.blocked:
            return
        sha = record['parent_sha']
        from .search_relevance import source_warnings
        parent = next((row for row in read_json(self.folder/'received.json', [])
                       if row.get('asset_sha') == sha), {})
        if source_warnings(parent):
            return
        if record.get('status') == STATUS_NO_COLLAGE:
            candidates = [(sha, next(iter((self.folder/'images').glob(sha+'.*')), None))]
        else:
            candidates = [(c['child_sha'], Path(c['path'])) for c in record.get('children', [])
                          if c.get('status') == VALID]
        for sha, path in candidates:
            if self.stop.is_set() or self.blocked:
                break
            ledger = self.folder/'photo-types.json'
            try:
                data = json.loads(ledger.read_text('utf8')) if ledger.exists() else {"version":1,"items":{},"calls":[]}
                if not isinstance(data.get('items'),dict) or not isinstance(data.get('calls'),list):
                    raise ValueError('invalid type ledger')
            except (OSError,ValueError,TypeError,AttributeError):
                self.blocked = True
                self.block_reason = 'type_evidence_invalid'
                return
            goal = read_json(self.folder/'goal.json', {})
            history_check = None
            if goal:
                from .collection_history import FINGERPRINT_ALGORITHM_VERSION, goal_baseline
                try:
                    goal_baseline(self.folder, goal)
                    if (self.history is None or not self.history.ready or self.history.errors
                            or getattr(self.history, 'baseline_sha', None) != goal.get('baseline_sha')):
                        raise ValueError('history_not_ready')
                    history_check = {'state':'clear', 'baseline_sha':goal['baseline_sha'],
                                     'algorithm_version':FINGERPRINT_ALGORITHM_VERSION}
                except (OSError, ValueError, KeyError):
                    self.blocked = True
                    self.block_reason = 'history_index_unavailable'
                    break
            previous = data['items'].get(sha, {})
            if verified_type(previous, sha) and receipt_intact(self.folder, previous):
                if history_check:
                    previous['history_check'] = history_check
                    write_json(self.folder/'photo-types.json', data)
                continue
            if len(data['calls']) >= self.limit:
                self.blocked = True
                self.block_reason = 'visual_budget_exhausted'
                break
            entry = {"asset_sha": sha, "producer": self.analyzer.producer_name,
                     "status": "running", "started_at": time.time(), "tokens": None}
            try:
                if path is None or path.is_symlink():
                    raise ValueError('missing_original')
                raw = path.read_bytes()
                if hashlib.sha256(raw).hexdigest() != sha:
                    raise ValueError('sha_mismatch')
                with Image.open(path) as image:
                    quality = _tile_quality(ImageOps.exif_transpose(image))
                if quality['status'] != VALID:
                    data['items'][sha] = {**entry, "status": "quality_failed", "quality": quality}
                    write_json(self.folder/'photo-types.json', data)
                    continue
            except Exception as exc:
                data['items'][sha] = {**entry, "status": "failed", "error": type(exc).__name__,
                                      "finished_at": time.time()}
                write_json(self.folder/'photo-types.json', data)
                continue
            for attempt in range(2):
                if self.stop.is_set() or time.monotonic() >= self.deadline or len(data['calls']) >= self.limit:
                    self.blocked = True
                    self.block_reason = 'time_budget_exhausted' if time.monotonic() >= self.deadline else 'visual_budget_exhausted'
                    break
                entry = {"asset_sha": sha, "producer": self.analyzer.producer_name,
                         "status": "running", "started_at": time.time(), "tokens": None,
                         "attempt": len(data['calls']) + 1, "attempt_budget": self.limit}
                data['calls'].append(entry.copy())
                data['items'][sha] = entry
                write_json(self.folder/'photo-types.json', data)
                self.analyzer.last_receipt = {}
                unavailable = False
                try:
                    result = self.analyzer.classify(raw, sha, self.stop)
                    entry.update(dict(getattr(self.analyzer, 'last_receipt', {})),
                                 result=result.model_dump(mode='json'))
                    if time.monotonic() >= self.deadline:
                        raise ClassificationUnavailable('type deadline exhausted')
                    if not verified_type(entry, sha) or not receipt_intact(self.folder, entry):
                        raise ValueError('missing_actual_read_receipt')
                except Exception as exc:
                    entry.update(dict(getattr(self.analyzer, 'last_receipt', {})))
                    unavailable = isinstance(exc, ClassificationUnavailable)
                    entry.update(status='blocked' if unavailable else 'failed', error=type(exc).__name__)
                entry.update(finished_at=time.time(), history_check=history_check)
                entry['elapsed_seconds'] = max(0, entry['finished_at'] - entry['started_at'])
                data['items'][sha] = entry
                data['calls'][-1] = entry.copy()
                write_json(self.folder/'photo-types.json', data)
                if not unavailable:
                    break
                if attempt == 1 or len(data['calls']) >= self.limit:
                    self.blocked = True
                    self.block_reason = ('time_budget_exhausted' if time.monotonic() >= self.deadline
                                         else 'visual_budget_exhausted' if len(data['calls']) >= self.limit else 'model_unavailable')
                    break
                if self.stop.wait(1):
                    break

    def drain(self, timeout=30):
        deadline = time.monotonic() + max(0, timeout)
        while self.pending.unfinished_tasks and time.monotonic() < deadline:
            time.sleep(.05)

    def close(self, timeout=30):
        self.drain(timeout)
        self.stop.set()
        self.thread.join(15)
