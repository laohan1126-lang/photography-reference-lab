"""Local-only duplicate exclusion. Never changes source images or human choices."""
from __future__ import annotations

import hashlib
import json
import math
import os
import re
import tempfile
from pathlib import Path

from PIL import Image, ImageOps

from .preflight import compute_dhash, hamming_distance


# Bump when the decoded representation, dHash, or colour sample changes.
FINGERPRINT_ALGORITHM_VERSION=1
CACHE_SCHEMA_VERSION=1
_CACHE_KEY=re.compile(r"([1-9][0-9]*):([0-9a-f]{64})\Z")
_DHASH=re.compile(r"[0-9a-f]{16}\Z")
_SAMPLE=re.compile(r"[0-9a-f]{384}\Z")


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
        history_config=history_local/'windows-runtime.json'
        if _is_link_or_junction(history_config):raise ValueError('History runtime configuration cannot be a link')
        history_data=Path(json.loads(history_config.read_text('utf-8-sig'))['data_dir']) if history_config.exists() else history_root/'data'
        if not history_data.is_absolute():history_data=history_root/history_data
        for path in (history_data/'assets').glob('*/*/original.*'):
            if path.is_file() and not path.is_symlink():paths.add(path.resolve())
        for base,dirs,files in os.walk(history_local,followlinks=False):
            base=Path(base)
            dirs[:]=[name for name in dirs if name not in {'worktrees','backups','public','baseline','reference-research','reference-images','visual-references','node_modules','__pycache__','.git','restored-library'}
                     and name.casefold() not in {'.venv','venv'}
                     and not name.casefold().startswith(('test','pytest','browser')) and not _is_link_or_junction(base/name)
                     and not (base/name).resolve().is_relative_to(current)]
            if base.resolve().is_relative_to(current) or 'received.json' not in files:continue
            received=json.loads((base/'received.json').read_text('utf8'))
            records=received.get('candidates',[]) if isinstance(received,dict) else received
            local_root=history_local.resolve()
            for row in records:
                path=Path(row['original_path']).resolve()
                if not path.is_relative_to(local_root):raise ValueError('Historical image escapes local collection boundary')
                if not path.is_file():raise ValueError('Historical original is missing; cannot prove no repeat')
                if hashlib.sha256(path.read_bytes()).hexdigest()!=row['asset_sha']:raise ValueError('Historical image SHA changed')
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


def _cache_key(sha):
    return f'{FINGERPRINT_ALGORITHM_VERSION}:{sha}'


def _cache_checksum(entries):
    payload=json.dumps(entries,sort_keys=True,separators=(',',':'),allow_nan=False).encode('utf8')
    return hashlib.sha256(payload).hexdigest()


def _valid_cache_value(value):
    return (isinstance(value,dict)
            and type(value.get('ratio')) in (int,float)
            and math.isfinite(value['ratio']) and value['ratio']>0
            and isinstance(value.get('dhash'),str) and _DHASH.fullmatch(value['dhash'])
            and isinstance(value.get('sample'),str) and _SAMPLE.fullmatch(value['sample']))


def _read_cache(path):
    try:
        payload=json.loads(path.read_text(encoding='utf8'))
        if not isinstance(payload,dict):return {}
        entries=payload.get('entries')
        if (payload.get('schema_version')!=CACHE_SCHEMA_VERSION or not isinstance(entries,dict)
                or payload.get('checksum')!=_cache_checksum(entries)):
            return {}
        result={}
        for key,value in entries.items():
            match=_CACHE_KEY.fullmatch(key) if isinstance(key,str) else None
            if not match:return {}
            if match.group(1)==str(FINGERPRINT_ALGORITHM_VERSION):
                if not _valid_cache_value(value):return {}
                result[key]=value
        return result
    except (OSError,UnicodeError,ValueError,TypeError):
        return {}


def _write_cache(path,entries):
    payload={'schema_version':CACHE_SCHEMA_VERSION,'entries':dict(sorted(entries.items()))}
    payload['checksum']=_cache_checksum(payload['entries'])
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
    def __init__(self,paths,cache_path=None):
        self.cache_path=Path(cache_path) if cache_path is not None else None
        self._cache=_read_cache(self.cache_path) if self.cache_path is not None else {}
        self._cache_dirty=False
        self.records={}
        for path in paths:
            value=self._fingerprint(path);self.records[value['asset_sha']]=value
        self.initial_count=len(self.records)
        self._save_cache()

    def _fingerprint(self,path):
        raw=path.read_bytes()
        if len(raw)>20*1024*1024:raise ValueError('Duplicate input exceeds image size limit')
        sha=hashlib.sha256(raw).hexdigest();key=_cache_key(sha)
        cached=self._cache.get(key)
        if cached is not None:
            return {'asset_sha':sha,'path':str(path.resolve()),**cached}
        value=_fingerprint_from_raw(path,raw,sha)
        if self.cache_path is not None:
            self._cache[key]={key:value[key] for key in ('ratio','dhash','sample')}
            self._cache_dirty=True
        return value

    def _save_cache(self):
        if self.cache_path is not None and self._cache_dirty:
            self._cache_dirty=not _write_cache(self.cache_path,self._cache)

    def consider(self,path):
        value=self._fingerprint(path);sha=value['asset_sha']
        found=self._match(value)
        if not found:
            self.records[sha]=value
        return found

    def match(self,path):
        """A discovery preview can match history but must never become an original."""
        return self._match(self._fingerprint(path))

    def _match(self,value):
        sha=value['asset_sha']
        if sha in self.records:return {'duplicate_of':sha,'reason':'same_bytes'}
        sample=bytes.fromhex(value['sample'])
        for other in self.records.values():
            if abs(value['ratio']/other['ratio']-1)>.03 or hamming_distance(value['dhash'],other['dhash'])>6:continue
            # Preserve originals; quarantine only close composition AND colour matches.
            difference=sum(abs(a-b) for a,b in zip(sample,bytes.fromhex(other['sample'])))/len(sample)
            if difference<=8:return {'duplicate_of':other['asset_sha'],'reason':'near_duplicate'}
        return None
