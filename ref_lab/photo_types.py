"""Run-scoped photographic admission, separate from identity and human choices."""
from __future__ import annotations

import hashlib
import queue
import threading
import time
from pathlib import Path

from PIL import Image, ImageOps

from .classification import AntigravityClassifier, ClassificationUnavailable
from .collection_queue import read_json, write_json
from .collage import VALID, STATUS_NO_COLLAGE, _tile_quality

PHOTO_KINDS = {"cosplay_photo", "portrait_photo"}


def verified_photo(item, sha):
    if not isinstance(item, dict):
        return False
    evidence = item.get("read_evidence") or {}
    result = item.get("result") or {}
    return (item.get("status") == "succeeded" and item.get("asset_sha") == sha
            and bool(item.get("producer")) and item.get("result_status") == "SUCCESS"
            and evidence.get("tool") == "view_file" and evidence.get("state") == "DONE"
            and evidence.get("asset_sha") == sha and bool(evidence.get("preview_sha"))
            and result.get("asset_sha") == sha and result.get("kind") in PHOTO_KINDS
            and bool(result.get("evidence")))


def receipt_intact(folder, item):
    """A claimed read is reusable only while its original stream still verifies."""
    from .integrity import sha_matches
    if not isinstance(item, dict):
        return False
    path = Path(str(item.get('stream_path') or ''))
    return (not path.is_symlink() and path.resolve().is_relative_to((Path(folder)/'type-evidence').resolve())
            and sha_matches(path, str(item.get('stream_sha') or '')))


class PhotoTypeWorker:
    """One bounded consumer, receiving only this run's actual split records."""

    def __init__(self, folder, *, analyzer=None, limit=45, model="gemini-3.8-flash-medium"):
        self.folder = Path(folder)
        self.analyzer = analyzer or AntigravityClassifier(model, evidence_dir=self.folder/'type-evidence')
        self.limit = limit
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
        if record.get('status') == STATUS_NO_COLLAGE:
            candidates = [(sha, next(iter((self.folder/'images').glob(sha+'.*')), None))]
        else:
            candidates = [(c['child_sha'], Path(c['path'])) for c in record.get('children', [])
                          if c.get('status') == VALID]
        for sha, path in candidates:
            if self.stop.is_set() or self.blocked:
                break
            data = read_json(self.folder/'photo-types.json', {"version": 1, "items": {}, "calls": []})
            previous = data['items'].get(sha, {})
            if (previous.get('status') == 'succeeded' and previous.get('asset_sha') == sha
                    and receipt_intact(self.folder, previous)):
                continue
            if len(data['calls']) >= self.limit:
                self.blocked = True
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
                data['calls'].append(entry.copy())
                data['items'][sha] = entry
                write_json(self.folder/'photo-types.json', data)
                result = self.analyzer.classify(raw, sha, self.stop)
                receipt = dict(getattr(self.analyzer, 'last_receipt', {}))
                entry.update(receipt, result=result.model_dump(mode='json'))
                if not (entry.get('status') == 'succeeded' and entry.get('read_evidence')):
                    raise ValueError('missing_actual_read_receipt')
            except Exception as exc:
                entry.update(getattr(self.analyzer, 'last_receipt', {}))
                entry.update(status='blocked' if isinstance(exc, ClassificationUnavailable) else 'failed',
                             error=type(exc).__name__, finished_at=time.time())
                if isinstance(exc, ClassificationUnavailable):
                    self.blocked = True
            data['items'][sha] = entry
            if data['calls'] and data['calls'][-1]['asset_sha'] == sha:
                data['calls'][-1] = entry.copy()
            write_json(self.folder/'photo-types.json', data)

    def drain(self, timeout=30):
        deadline = time.monotonic() + max(0, timeout)
        while self.pending.unfinished_tasks and time.monotonic() < deadline:
            time.sleep(.05)

    def close(self, timeout=30):
        self.drain(timeout)
        self.stop.set()
        self.thread.join(15)
