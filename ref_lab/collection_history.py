"""Local-only duplicate exclusion. Never changes source images or human choices.

Search must not wait for a full perceptual rebuild. A path/size/mtime keyed cache
lets a warm run load fingerprints by ``stat`` only; a cold run can fill expensive
fingerprints in the background while download/display proceeds. The Review stage
uses the same cache synchronously before admitting an image, so a duplicate that
was not yet visible during Search cannot reach the formal schema3 package.
"""
from __future__ import annotations

import hashlib
import json
import math
import os
import re
import tempfile
import threading
from pathlib import Path

from PIL import Image, ImageOps

from .preflight import compute_dhash, hamming_distance


# Bump when the decoded representation, dHash, colour sample, or cache key changes.
FINGERPRINT_ALGORITHM_VERSION=1
CACHE_SCHEMA_VERSION=2
_DHASH=re.compile(r"[0-9a-f]{16}\Z")
_SAMPLE=re.compile(r"[0-9a-f]{384}\Z")
_SHA=re.compile(r"[0-9a-f]{64}\Z")


def _is_link_or_junction(path):
    return path.is_symlink() or getattr(path,'is_junction',lambda:False)()


def historical_paths(root: Path, current: Path, history_roots=()):
    root=Path(root)
    if _is_link_or_junction(root):raise ValueError('History root cannot be a link')
    root=root.resolve();current=Path(current).resolve();paths=set()
    roots=[]
    for candidate in (root,*history_roots):
        candidate=Path(candidate)
        if _is_link_or_junction(candidate):raise ValueError('History root cannot be a link')
        try:candidate=candidate.resolve(strict=True)
        except (OSError,RuntimeError) as exc:raise ValueError('History root is unavailable') from exc
        if not candidate.is_dir():raise ValueError('History root is unavailable')
        if candidate not in roots:roots.append(candidate)
    local=root/'.local'
    if _is_link_or_junction(local):raise ValueError('History root local directory cannot be a link')
    config=local/'windows-runtime.json'
    configured=os.environ.get('LAB_DATA_DIR')
    if not configured and config.exists():configured=json.loads(config.read_text('utf-8-sig'))['data_dir']
    data=Path(configured) if configured else root/'data'
    if not data.is_absolute():data=root/data
    originals=Path(os.environ.get('LAB_COLLECTION_HISTORY_DIR') or data/'assets')
    for path in originals.glob('*/*/original.*'):
        if path.is_file() and not path.is_symlink():paths.add(path.resolve())
    for history_root in roots:
        history_local=history_root/'.local'
        if _is_link_or_junction(history_local):raise ValueError('History root local directory cannot be a link')
        local_root=history_local.resolve()
        history_config=history_local/'windows-runtime.json'
        if _is_link_or_junction(history_config):raise ValueError('History runtime configuration cannot be a link')
        history_data=Path(json.loads(history_config.read_text('utf-8-sig'))['data_dir']) if history_config.exists() else history_root/'data'
        if not history_data.is_absolute():history_data=history_root/history_data
        for path in (history_data/'assets').glob('*/*/original.*'):
            if path.is_file() and not path.is_symlink():paths.add(path.resolve())
        for base,dirs,files in os.walk(history_local,followlinks=False):
            base=Path(base)
            # Archived batches under ``backups`` stay in duplicate history: moving
            # a diagnostic run aside for evidence must not let its received bytes
            # be counted as new later. Synthetic test fixtures are excluded by
            # name so generated material never enters the real history scope.
            dirs[:]=[name for name in dirs if name not in {'worktrees','public','baseline','reference-research','reference-images','visual-references','node_modules','__pycache__','.git','restored-library'}
                     and name.casefold() not in {'.venv','venv'}
                     and not name.casefold().startswith(('test','pytest','browser','fixture')) and not _is_link_or_junction(base/name)
                     and not (base/name).is_relative_to(current)]
            # Roots are resolved and every linked directory is pruned before descent.
            if base.is_relative_to(current) or 'received.json' not in files:continue
            received=json.loads((base/'received.json').read_text('utf8'))
            records=received.get('candidates',[]) if isinstance(received,dict) else received
            for row in records:
                path=Path(row['original_path']).resolve()
                if not path.is_relative_to(local_root):raise ValueError('Historical image escapes local collection boundary')
                if not path.is_file():raise ValueError('Historical original is missing; cannot prove no repeat')
                if hashlib.sha256(path.read_bytes()).hexdigest()!=row['asset_sha']:raise ValueError('Historical image SHA changed')
                paths.add(path)
            # Valid derived tiles of older, never-imported batches are real images
            # too: a new download identical to one of them is a repeat, not a new
            # independent reference. Only current-algorithm, verified tiles count.
            derived=base/'derived.json'
            if derived.is_file():
                from .collage import ALGORITHM_VERSION, VALID
                try:data=json.loads(derived.read_text('utf8'))
                except (OSError,ValueError):data={}
                items=data.get('items') if isinstance(data,dict) else None
                for parent_sha,record in (items or {}).items():
                    if not isinstance(record,dict):continue
                    if str(record.get('algorithm_version',''))!=str(ALGORITHM_VERSION):continue
                    for child in record.get('children') or []:
                        if not isinstance(child,dict) or child.get('status')!=VALID:continue
                        sha=str(child.get('child_sha') or '')
                        if not sha:continue
                        path=Path(str(child.get('path') or '')).resolve()
                        if not path.is_relative_to(local_root):
                            raise ValueError('Historical derived tile escapes local collection boundary')
                        if not path.is_file():
                            raise ValueError('Historical derived tile is missing; cannot prove no repeat')
                        if hashlib.sha256(path.read_bytes()).hexdigest()!=sha:
                            raise ValueError('Historical derived tile SHA changed')
                        paths.add(path)
    return sorted(paths)


def _fingerprint_from_raw(path: Path,raw: bytes,sha: str):
    if len(raw)>20*1024*1024:raise ValueError('Duplicate input exceeds image size limit')
    with Image.open(path) as im:
        if im.width*im.height>40_000_000 or getattr(im,'n_frames',1)!=1:raise ValueError('Unsafe duplicate image input')
        display=ImageOps.exif_transpose(im).convert('RGB')
        return {'asset_sha':sha,'path':str(path.resolve()),
                'ratio':display.width/display.height,'dhash':compute_dhash(display),
                'sample':display.resize((8,8),Image.Resampling.LANCZOS).tobytes().hex()}


def fingerprint(path: Path):
    raw=path.read_bytes()
    if len(raw)>20*1024*1024:raise ValueError('Duplicate input exceeds image size limit')
    return _fingerprint_from_raw(path,raw,hashlib.sha256(raw).hexdigest())


def _valid_cache_value(value):
    return (isinstance(value,dict)
            and type(value.get('ratio')) in (int,float)
            and math.isfinite(value['ratio']) and value['ratio']>0
            and isinstance(value.get('dhash'),str) and _DHASH.fullmatch(value['dhash'])
            and isinstance(value.get('sample'),str) and _SAMPLE.fullmatch(value['sample']))


def _valid_file_entry(value):
    return (_valid_cache_value(value)
            and isinstance(value.get('sha'),str) and _SHA.fullmatch(value['sha'])
            and type(value.get('size')) is int and value['size']>=0
            and type(value.get('mtime_ns')) is int and value['mtime_ns']>=0)


def _cache_checksum(files):
    payload=json.dumps(files,sort_keys=True,separators=(',',':'),allow_nan=False).encode('utf8')
    return hashlib.sha256(payload).hexdigest()


def _read_cache(path):
    try:
        payload=json.loads(path.read_text(encoding='utf8'))
        if not isinstance(payload,dict) or payload.get('schema_version')!=CACHE_SCHEMA_VERSION:
            return {}
        files=payload.get('files')
        if not isinstance(files,dict) or payload.get('checksum')!=_cache_checksum(files):
            return {}
        result={}
        for key,value in files.items():
            if not isinstance(key,str) or not Path(key).is_absolute() or not _valid_file_entry(value):
                return {}
            result[key]=value
        return result
    except (OSError,UnicodeError,ValueError,TypeError):
        return {}


def _write_cache(path,files):
    payload={'schema_version':CACHE_SCHEMA_VERSION,'files':dict(sorted(files.items()))}
    payload['checksum']=_cache_checksum(payload['files'])
    temporary=None
    try:
        path.parent.mkdir(parents=True,exist_ok=True)
        with tempfile.NamedTemporaryFile('w',encoding='utf8',newline='\n',dir=path.parent,
                                         prefix=f'.{path.name}.',suffix='.tmp',delete=False) as stream:
            temporary=Path(stream.name)
            json.dump(payload,stream,sort_keys=True,separators=(',',':'),allow_nan=False)
            stream.write('\n');stream.flush();os.fsync(stream.fileno())
        os.replace(temporary,path)
    except OSError:
        return False
    finally:
        if temporary is not None:
            try:temporary.unlink(missing_ok=True)
            except OSError:pass
    return True


class ImageHistory:
    def __init__(self,paths,cache_path=None,*,lazy=False):
        self.cache_path=Path(cache_path) if cache_path is not None else None
        self._cache_files=_read_cache(self.cache_path) if self.cache_path is not None else {}
        self._cache_dirty=False
        self._lock=threading.RLock()
        self._stop=threading.Event()
        self._thread=None
        self._pending=[]
        self.errors=[]
        self.ready=not lazy
        self.records={}
        self.known_shas=set()
        ordered=[]
        seen=set()
        for path in paths:
            try:resolved=Path(path).resolve()
            except (OSError,RuntimeError):continue
            if resolved in seen:continue
            seen.add(resolved);ordered.append(resolved)
            # Asset stores and collection runs embed the exact SHA in a path
            # component. This catches same-byte history immediately, before the
            # expensive perceptual index has finished in the background.
            for value in (resolved.name.split('.')[0],resolved.parent.name,resolved.parent.parent.name):
                if isinstance(value,str) and _SHA.fullmatch(value):
                    self.known_shas.add(value);break
        self.known_count=len(self.known_shas)
        if lazy:
            # Only stat()/remembered fingerprints here; a cold decode cannot delay first download.
            for path in ordered:
                record=self._cached_record(path)
                if record is None:self._pending.append(path)
                else:self.records[record['asset_sha']]=record
            self.initial_count=len(self.records)
            self._thread=threading.Thread(target=self._fill,args=(self._pending,),daemon=True,
                                          name='history-fingerprints')
            self._thread.start()
        else:
            for path in ordered:self._remember(path)
            self.initial_count=len(self.records)
            self.ready=True
            self._save_cache()

    def _stat_key(self,path):
        try:
            stat=path.stat()
            if not path.is_file() or path.is_symlink():return None
        except OSError:
            return None
        return {'size':int(stat.st_size),'mtime_ns':int(stat.st_mtime_ns)}

    def _cached_record(self,path):
        key=str(path)
        cached=self._cache_files.get(key)
        stat=self._stat_key(path)
        if not cached or not stat:return None
        if cached.get('size')!=stat['size'] or cached.get('mtime_ns')!=stat['mtime_ns']:
            return None
        return {'asset_sha':cached['sha'],'path':key,'ratio':cached['ratio'],
                'dhash':cached['dhash'],'sample':cached['sample']}

    def _remember(self,path):
        value=self._fingerprint(path)
        with self._lock:self.records[value['asset_sha']]=value
        return value

    def _fill(self,paths):
        for path in paths:
            if self._stop.is_set():break
            try:self._remember(path)
            except (OSError,ValueError) as exc:
                self.errors.append({'path':str(path),'error':type(exc).__name__})
        self.ready=True
        self._save_cache()

    def _fingerprint(self,path):
        path=Path(path).resolve()
        key=str(path)
        stat=self._stat_key(path)
        if stat is None:raise ValueError('Duplicate input is unavailable')
        cached=self._cache_files.get(key)
        if (cached is not None and cached.get('size')==stat['size']
                and cached.get('mtime_ns')==stat['mtime_ns']
                and _valid_file_entry(cached)):
            return {'asset_sha':cached['sha'],'path':key,'ratio':cached['ratio'],
                    'dhash':cached['dhash'],'sample':cached['sample']}
        raw=path.read_bytes()
        if len(raw)>20*1024*1024:raise ValueError('Duplicate input exceeds image size limit')
        sha=hashlib.sha256(raw).hexdigest()
        value=_fingerprint_from_raw(path,raw,sha)
        self._cache_files[key]={'size':stat['size'],'mtime_ns':stat['mtime_ns'],'sha':sha,
                                'ratio':value['ratio'],'dhash':value['dhash'],'sample':value['sample']}
        self._cache_dirty=True
        return value

    def _save_cache(self):
        if self.cache_path is None:return
        with self._lock:
            if not self._cache_dirty:return
            self._cache_dirty=not _write_cache(self.cache_path,self._cache_files)

    def wait(self,timeout=None):
        if self._thread is not None:self._thread.join(timeout)
        return not self._thread.is_alive() if self._thread is not None else True

    def close(self,*,wait=True,timeout=10):
        self._stop.set()
        if self._thread is not None and wait:self._thread.join(timeout)
        self._save_cache()

    def _match(self,value):
        sha=value['asset_sha']
        with self._lock:
            if sha in self.known_shas:return {'duplicate_of':sha,'reason':'same_bytes'}
            records=list(self.records.values())
        if sha in {other['asset_sha'] for other in records}:return {'duplicate_of':sha,'reason':'same_bytes'}
        sample=bytes.fromhex(value['sample'])
        for other in records:
            if abs(value['ratio']/other['ratio']-1)>.03 or hamming_distance(value['dhash'],other['dhash'])>6:continue
            # Preserve originals; quarantine only close composition AND colour matches.
            difference=sum(abs(a-b) for a,b in zip(sample,bytes.fromhex(other['sample'])))/len(sample)
            if difference<=8:return {'duplicate_of':other['asset_sha'],'reason':'near_duplicate'}
        return None

    def consider(self,path):
        value=self._fingerprint(path);sha=value['asset_sha']
        found=self._match(value)
        if not found:
            with self._lock:
                self.records[sha]=value;self.known_shas.add(sha)
            self._cache_dirty=True
        return found

    def match(self,path):
        """A discovery preview can match history but must never become an original."""
        return self._match(self._fingerprint(path))

    def exclude(self,shas):
        """Drop already-acquired images from history comparison.

        Search imports each downloaded original into the project asset store, so a
        later Review sees those exact bytes as "historical". They are the current
        job's own candidates, not repeats: comparing them against history would
        quarantine every candidate as ``same_bytes`` before any visual call.
        """
        removed=False
        with self._lock:
            for sha in shas:
                if sha in self.known_shas:
                    self.known_shas.discard(sha);removed=True
                if sha in self.records:
                    self.records.pop(sha,None);removed=True
        return removed
