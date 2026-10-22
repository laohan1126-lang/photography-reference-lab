"""Local-only duplicate exclusion. Never changes source images or human choices.

Ordinary Search can use a path/size/mtime keyed cache while rebuilding. Goal
admission requires a complete, validated frozen baseline before it can count.
A path/size/mtime keyed cache
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


# Bump when representation or matching rules change; old admission needs review.
FINGERPRINT_ALGORITHM_VERSION=4
CACHE_SCHEMA_VERSION=4
_DHASH=re.compile(r"[0-9a-f]{16}\Z")
_SAMPLE=re.compile(r"[0-9a-f]{384}\Z")
_SHA=re.compile(r"[0-9a-f]{64}\Z")


def _is_link_or_junction(path):
    return path.is_symlink() or getattr(path,'is_junction',lambda:False)()


class HistoricalBytesMissing(ValueError):
    """A verified historical original no longer exists on disk."""


def _historical_file(base, declared, sha, role, boundaries):
    if not isinstance(sha,str) or not _SHA.fullmatch(sha):
        raise ValueError('Historical SHA binding is invalid')
    path=Path(declared).resolve()
    if not any(path.is_relative_to(boundary) for boundary in boundaries) or not path.is_file():
        # Archived/copied runs retain absolute paths; reclaim only identical bytes
        # from that run's expected image namespace, never an arbitrary substitute.
        candidates=(base/role).glob(sha+'.*')
        path=next((p.resolve() for p in candidates if p.is_file() and not p.is_symlink()
                   and hashlib.sha256(p.read_bytes()).hexdigest()==sha),path)
    if not any(path.is_relative_to(boundary) for boundary in boundaries):
        raise ValueError(f'Historical image escapes local collection boundary: {base} -> {path}')
    if not path.is_file() or path.is_symlink():
        raise HistoricalBytesMissing(f'Historical original is missing; cannot prove no repeat: {path}')
    if hashlib.sha256(path.read_bytes()).hexdigest()!=sha:
        raise ValueError(f'Historical image SHA changed: {path}')
    return path


def historical_paths(root: Path, current: Path, history_roots=(), skipped=None):
    """Return verified historical original paths.

    ``skipped`` optionally receives archived runs whose image directory was
    deliberately emptied by the duplicate cleanup. Their bytes still exist in the
    live asset store (that is why they were cleaned), so they remain covered by
    history; a run that still has files but cannot verify one still fails loudly.
    """
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
    boundaries=[(candidate/'.local').resolve() for candidate in roots]
    local=root/'.local'
    if _is_link_or_junction(local):raise ValueError('History root local directory cannot be a link')
    config=local/'windows-runtime.json'
    configured=os.environ.get('LAB_DATA_DIR')
    if not configured and config.exists():configured=json.loads(config.read_text('utf-8-sig'))['data_dir']
    data=Path(configured) if configured else root/'data'
    if not data.is_absolute():data=root/data
    originals=Path(os.environ.get('LAB_COLLECTION_HISTORY_DIR') or data/'assets')
    def add_asset(path):
        if not path.is_file() or path.is_symlink():return
        if _SHA.fullmatch(path.parent.name) and hashlib.sha256(path.read_bytes()).hexdigest()!=path.parent.name:
            raise ValueError(f'Historical asset SHA changed: {path}')
        paths.add(path.resolve())
    for path in originals.glob('*/*/original.*'):
        add_asset(path)
    for history_root in roots:
        history_local=history_root/'.local'
        if _is_link_or_junction(history_local):raise ValueError('History root local directory cannot be a link')
        local_root=history_local.resolve()
        history_config=history_local/'windows-runtime.json'
        if _is_link_or_junction(history_config):raise ValueError('History runtime configuration cannot be a link')
        history_data=Path(json.loads(history_config.read_text('utf-8-sig'))['data_dir']) if history_config.exists() else history_root/'data'
        if not history_data.is_absolute():history_data=history_root/history_data
        for path in (history_data/'assets').glob('*/*/original.*'):
            add_asset(path)
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
            images=base/'images'
            if _is_link_or_junction(images):raise ValueError('Historical image directory cannot be a link')
            run_files=list(images.glob('*')) if images.is_dir() else []
            try:
                for original in run_files:
                    sha=original.stem
                    if original.suffix.lower() in {'.jpg','.jpeg','.png','.webp','.avif'} and _SHA.fullmatch(sha):
                        paths.add(_historical_file(base,str(original),sha,'images',boundaries))
                for row in records:
                    path=_historical_file(base,row['original_path'],row['asset_sha'],'images',boundaries)
                    paths.add(path)
                # Valid derived tiles of older, never-imported batches are real images
                # too: a new download identical to one of them is a repeat, not a new
                # independent reference. Intact old tiles remain historical material.
                derived=base/'derived.json'
                if derived.is_file():
                    from .collage import VALID
                    data=json.loads(derived.read_text('utf8'))
                    items=data.get('items') if isinstance(data,dict) else None
                    if not isinstance(items,dict):raise ValueError('Historical derived records are invalid')
                    for parent_sha,record in (items or {}).items():
                        if not isinstance(record,dict):continue
                        if record.get('parent_sha')!=parent_sha:
                            raise ValueError('Historical tile parent binding changed')
                        for child in record.get('children') or []:
                            if not isinstance(child,dict) or child.get('status')!=VALID:continue
                            sha=str(child.get('child_sha') or '')
                            if not sha:continue
                            path=_historical_file(base,str(child.get('path') or ''),sha,'derived',boundaries)
                            paths.add(path)
            except HistoricalBytesMissing as exc:
                if run_files:
                    raise
                # The duplicate cleanup deliberately removed this archived run's
                # copies because every byte also exists in the live asset store.
                # The SHA set still covers them; record the skip instead of
                # pretending the run was scanned. Malformed metadata still fails.
                if skipped is not None:
                    skipped.append({'run':str(base),'reason':'archived copies cleaned; bytes covered by live assets',
                                    'received_rows':len(records),'error':str(exc)[:200]})
    return sorted(paths)


def _fingerprint_from_raw(path: Path,raw: bytes,sha: str):
    if len(raw)>20*1024*1024:raise ValueError('Duplicate input exceeds image size limit')
    with Image.open(path) as im:
        if im.width*im.height>40_000_000 or getattr(im,'n_frames',1)!=1:raise ValueError('Unsafe duplicate image input')
        display=ImageOps.exif_transpose(im).convert('RGB')
        return {'asset_sha':sha,'path':str(path.resolve()),
                'ratio':display.width/display.height,'dhash':compute_dhash(display),
                'sample':display.resize((8,8),Image.Resampling.LANCZOS).tobytes().hex(),
                'pixels':display.resize((128,128),Image.Resampling.LANCZOS).tobytes().hex()}


def fingerprint(path: Path):
    raw=path.read_bytes()
    if len(raw)>20*1024*1024:raise ValueError('Duplicate input exceeds image size limit')
    return _fingerprint_from_raw(path,raw,hashlib.sha256(raw).hexdigest())


def _valid_cache_value(value):
    return (isinstance(value,dict)
            and type(value.get('ratio')) in (int,float)
            and math.isfinite(value['ratio']) and value['ratio']>0
            and isinstance(value.get('dhash'),str) and _DHASH.fullmatch(value['dhash'])
            and isinstance(value.get('sample'),str) and _SAMPLE.fullmatch(value['sample'])
            and isinstance(value.get('pixels'),str) and re.fullmatch(r'[0-9a-f]{98304}',value['pixels']))


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
        if not isinstance(payload,dict) or payload.get('schema_version')!=CACHE_SCHEMA_VERSION or payload.get('algorithm_version')!=FINGERPRINT_ALGORITHM_VERSION:
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
    payload={'schema_version':CACHE_SCHEMA_VERSION,'algorithm_version':FINGERPRINT_ALGORITHM_VERSION,
             'files':dict(sorted(files.items()))}
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


from functools import lru_cache


@lru_cache(maxsize=4)
def _frozen_baseline(path, size, mtime, expected_sha):
    raw=Path(path).read_bytes()
    if hashlib.sha256(raw).hexdigest()!=expected_sha:
        raise ValueError('Goal baseline SHA changed')
    baseline=json.loads(raw)
    if baseline.get('fingerprint_algorithm_version')!=FINGERPRINT_ALGORITHM_VERSION:
        raise ValueError('Goal baseline fingerprints need explicit upgrade')
    for item in baseline['items']:
        fp=item.get('fingerprint')
        if not _valid_cache_value(fp) or fp.get('asset_sha')!=item.get('sha'):
            raise ValueError('Goal baseline fingerprint binding is invalid')
    return baseline


def goal_baseline(folder, goal):
    path=Path(folder)/'baseline.json'
    stat=path.stat()
    baseline=_frozen_baseline(str(path.resolve()),stat.st_size,stat.st_mtime_ns,goal.get('baseline_sha'))
    if (baseline.get('goal_id')!=goal.get('goal_id')
            or {item['sha'] for item in baseline['items']}!=set(goal.get('baseline_shas',[]))):
        raise ValueError('Goal baseline identity or SHA set changed')
    return baseline


def _photo_relation(value, other, context=None):
    """Fit a bounded crop by pixels; similar colours alone cannot reject a frame.

    ``context`` carries the per-query template cache and the lazily built 128px
    pyramids used by the fine fit. Records only keep their own downscaled
    pyramids, so a query image is resized once instead of once per record.
    """
    import numpy as np
    import cv2
    context = context if context is not None else _MatchContext()
    first, second = context.features(value), context.features(other)
    diff = np.abs(first['arr'].astype(float) - second['arr'].astype(float))
    direct = float(diff.mean())
    if abs(value['ratio']/other['ratio']-1)<=.03 and direct<=4 and diff.reshape(8,16,8,16,3).mean(axis=(1,3,4)).max()<=8:
        return {'reason':'near_duplicate','pixel_difference':round(direct,3)}
    for side,(source,query,source_ratio,query_ratio) in enumerate((
            (first,second,value['ratio'],other['ratio']),
            (second,first,other['ratio'],value['ratio']))):
        container_sha=value['asset_sha'] if side==0 else other['asset_sha']
        factor=source_ratio/query_ratio
        candidates=[]
        for resolution in (32,64):
            small=source[f'small{resolution}']
            for width in range(2,resolution+1):
                height=round(width*factor)
                if not 2<=height<=resolution+1:continue
                height=min(height,resolution)
                area=width*height
                # Increase sampling density for small crops, rather than using colour-only templates.
                if area<(9 if resolution==32 else 16) or (resolution==64 and area>=36):continue
                template,usable=context.template(side,query,'area',width,height,resolution)
                if not usable:continue
                _,correlation,_,(xx,yy)=cv2.minMaxLoc(cv2.matchTemplate(small,template,cv2.TM_CCOEFF_NORMED))
                if correlation>=.80:
                    candidates.append((xx/resolution,yy/resolution,min(width/resolution,1/factor)))
        if not candidates:continue
        target=query['target32']
        factor=source_ratio/query_ratio
        source_image=_materialize_image(source)
        def difference(x,y,width):
            height=width*factor
            if width<1/128 or height<1/128 or x<0 or y<0 or x+width>1.001 or y+height>1.001:
                return float('inf'),None
            tile=source_image.resize((32,32),Image.Resampling.BICUBIC,
                               box=(x*128,y*128,min(128,(x+width)*128),min(128,(y+height)*128)))
            pixels=np.asarray(tile,dtype=float)
            return float(np.abs(pixels-target).mean()),pixels
        fine=[]
        for x,y,width in candidates:
            coarse,probe=difference(x,y,width)
            if coarse>32 or probe is None:continue
            if coarse>8:
                a=probe.reshape(-1,3)-probe.reshape(-1,3).mean(axis=0)
                b=target.reshape(-1,3)-target.reshape(-1,3).mean(axis=0)
                norm=float(np.sqrt((a*a).sum()*(b*b).sum()))
                if norm==0 or float((a*b).sum())/norm<.80:continue
            for pixels_w in range(max(2,round(width*128)-4),min(128,round(width*128)+4)+1):
                pixels_h=round(pixels_w*factor)
                if not 2<=pixels_h<=128:continue
                left=max(0,round(x*128)-4);top=max(0,round(y*128)-4)
                right=min(128,round(x*128)+pixels_w+5);bottom=min(128,round(y*128)+pixels_h+5)
                if right-left<pixels_w or bottom-top<pixels_h:continue
                template,usable=context.template(side,query,'lanczos',pixels_w,pixels_h)
                if not usable:continue
                _,correlation,_,(xx,yy)=cv2.minMaxLoc(cv2.matchTemplate(source['arr'][top:bottom,left:right],template,cv2.TM_CCOEFF_NORMED))
                if correlation<.90 and coarse>8:continue
                pos=((left+xx)/128,(top+yy)/128,min(pixels_w/128,1/factor))
                error,tile=difference(*pos)
                if correlation>=.90 or error<=8:fine.append((error,*pos,tile))
        if not fine:continue
        score,x,y,width,pixels=min(fine,key=lambda item:item[0])
        for step in (1/256,1/512,1/1024):
            choices=[(score,x,y,width,pixels)]
            for dx in (-step,0,step):
                for dy in (-step,0,step):
                    for dw in (-step,0,step):
                        error,tile=difference(x+dx,y+dy,width+dw)
                        choices.append((error,x+dx,y+dy,width+dw,tile))
            score,x,y,width,pixels=min(choices,key=lambda item:item[0])
        if pixels is None:continue
        a=pixels.reshape(-1);b=target.reshape(-1)
        correlation=float(np.corrcoef(a,b)[0,1]) if a.std()>3 and b.std()>3 else 0
        delta=np.abs(pixels-target)
        patch_errors=delta.reshape(8,4,8,4,3).mean(axis=(1,3,4))
        local_error=float(patch_errors.max())
        if score<=4 and correlation>=.99 and local_error<=10:
            return {'reason':'crop_duplicate','pixel_difference':round(score,3),
                    'correlation':round(correlation,5),'crop_fraction':[x,y,width,width*factor],
                    'container_sha':container_sha}
        if score<=8 and correlation>=.98 and local_error<=16:
            return {'reason':'possible_crop_duplicate','state':'needs_review',
                    'pixel_difference':round(score,3),'correlation':round(correlation,5),'container_sha':container_sha}
        if score<=4:
            # A small conflicting region can be an overlay or a changed frame;
            # strong agreement elsewhere is inconclusive, never clearance as new.
            matching=patch_errors<=4
            if matching.mean()>=.90:
                mask=np.repeat(np.repeat(matching,4,axis=0),4,axis=1)
                a=pixels[mask].reshape(-1);b=target[mask].reshape(-1)
                clean_error=float(delta[mask].mean())
                clean_correlation=float(np.corrcoef(a,b)[0,1]) if a.std()>3 and b.std()>3 else 0
                if clean_error<=2 and clean_correlation>=.99:
                    return {'reason':'possible_crop_duplicate','state':'needs_review',
                            'pixel_difference':round(score,3),'correlation':round(correlation,5),
                            'matching_fraction':round(float(matching.mean()),4),
                            'matching_region_error':round(clean_error,3),'container_sha':container_sha}
    return None


class _MatchContext:
    """Per-query caches: 128px pyramids and query crop templates.

    Template crops depend only on the query image, so each (side, kind,
    width, height) is resized once per query instead of once per historical
    record. Historical pyramids live in a side cache keyed by asset SHA, so
    observable record dicts stay unchanged and later queries reuse the work.
    """
    __slots__=('_templates','_pyramids')

    def __init__(self, pyramids=None):
        self._templates={}
        self._pyramids=pyramids if pyramids is not None else {}

    def features(self,record):
        import numpy as np
        import cv2
        key=record.get('asset_sha')
        feature=self._pyramids.get(key)
        if feature is not None:
            return feature
        image=Image.frombytes('RGB',(128,128),bytes.fromhex(record['pixels']))
        arr=np.asarray(image)
        feature={
            'arr':arr,
            'image':None,
            'small32':cv2.resize(arr,(32,32),interpolation=cv2.INTER_AREA),
            'small64':cv2.resize(arr,(64,64),interpolation=cv2.INTER_AREA),
            'target32':np.asarray(image.resize((32,32),Image.Resampling.LANCZOS)),
        }
        self._pyramids[key]=feature
        return feature

    def template(self,side,query,kind,width,height,resolution=None):
        key=(side,kind,resolution,width,height)
        cached=self._templates.get(key)
        if cached is not None:
            return (cached, True) if cached is not False else (False, False)
        import numpy as np
        import cv2
        if kind=='lanczos':
            template=np.asarray(_materialize_image(query).resize((width,height),Image.Resampling.LANCZOS))
        else:
            template=cv2.resize(query['arr'],(width,height),interpolation=cv2.INTER_AREA)
        # The coarse proposal stage skips flat templates; the fine fit has always
        # scored every crop on the full pixels and must keep doing so.
        if kind!='lanczos' and template.reshape(-1,3).std(axis=0).max()<3:
            self._templates[key]=False
            return False, False
        self._templates[key]=template
        return template, True


def _materialize_image(feature):
    if feature.get('image') is None:
        feature['image']=Image.fromarray(feature['arr'])
    return feature['image']


class ImageHistory:
    def __init__(self,paths,cache_path=None,*,lazy=False):
        try:__import__('cv2')
        except (ImportError,OSError) as exc:raise ValueError('History matcher unavailable') from exc
        self.cache_path=Path(cache_path) if cache_path is not None else None
        self._cache_files=_read_cache(self.cache_path) if self.cache_path is not None else {}
        self._cache_dirty=False
        self._lock=threading.RLock()
        self._admission=threading.RLock()
        self._stop=threading.Event()
        self._thread=None
        self._pending=[]
        self.errors=[]
        self.ready=not lazy
        self.records={}
        self.known_shas=set()
        self._pyramids={}
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
                'dhash':cached['dhash'],'sample':cached['sample'],'pixels':cached['pixels']}

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
        self.ready=not self._stop.is_set() and not self.errors
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
                    'dhash':cached['dhash'],'sample':cached['sample'],'pixels':cached['pixels']}
        raw=path.read_bytes()
        if len(raw)>20*1024*1024:raise ValueError('Duplicate input exceeds image size limit')
        sha=hashlib.sha256(raw).hexdigest()
        value=_fingerprint_from_raw(path,raw,sha)
        self._cache_files[key]={'size':stat['size'],'mtime_ns':stat['mtime_ns'],'sha':sha,
                                'ratio':value['ratio'],'dhash':value['dhash'],'sample':value['sample'],'pixels':value['pixels']}
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

    def _match(self,value,exclude=()):
        sha=value['asset_sha']
        with self._lock:
            if sha in self.known_shas:return {'duplicate_of':sha,'reason':'same_bytes'}
            records=[other for key,other in self.records.items() if key not in exclude]
        if sha in {other.get('asset_sha') for other in records if isinstance(other,dict)}:return {'duplicate_of':sha,'reason':'same_bytes'}
        records=[other for other in records if _valid_cache_value(other)]
        if not records:return None
        candidate_collage=None
        context=_MatchContext(self._pyramids)
        # Build every historical pyramid once. The shared cache is then read-only
        # for the comparison workers, and only the query's crop templates are
        # per-worker state.
        for other in records:
            try:context.features(other)
            except (ValueError,OSError):pass
        start=0
        while start<len(records):
            candidate=self._first_relation(value,records,start)
            if candidate is None:return None
            index,other,relation=candidate
            if relation.get('container_sha')==sha:
                if candidate_collage is None:
                    from .collage import analyze, STATUS_SPLIT_OK
                    with Image.open(value['path']) as image:
                        candidate_collage=analyze(image)['status']==STATUS_SPLIT_OK
                if candidate_collage:
                    start=index+1
                    continue  # Match the collage's tiles; an old panel does not cover its new panels.
            return {'duplicate_of':other.get('asset_sha',sha),**relation}
        return None

    def _first_relation(self,value,records,start):
        """First matching historical record at or after ``start``.

        Chunks are compared in parallel but the earliest index wins, so the
        result is identical to a sequential scan. Pure pixel work releases the
        GIL inside OpenCV, and the comparison order never depends on scheduling.
        """
        import os
        from concurrent.futures import ThreadPoolExecutor
        workers=min(4,max(1,(os.cpu_count() or 4)-1))
        indexes=list(range(start,len(records)))
        if workers<2 or len(indexes)<64:
            context=_MatchContext(self._pyramids)
            for index in indexes:
                relation=_photo_relation(value,records[index],context)
                if relation:return index,records[index],relation
            return None
        chunks=[indexes[i::workers] for i in range(workers)]

        def scan(chunk):
            local=_MatchContext(self._pyramids)
            for index in chunk:
                relation=_photo_relation(value,records[index],local)
                if relation:return index,records[index],relation
            return None

        with ThreadPoolExecutor(max_workers=workers) as pool:
            results=[result for result in pool.map(scan,chunks) if result]
        return min(results,key=lambda item:item[0]) if results else None

    def consider(self,path,*,exclude=()):
        """Compare outside the lock, then commit atomically.

        The heavy perceptual comparison no longer holds the shared lock, so a
        concurrent Review/Goal admission can still inspect history. The final
        commit re-checks ``known_shas`` under the lock, keeping exact-byte
        dedupe atomic for concurrent image accounting.
        """
        value=self._fingerprint(path);sha=value['asset_sha']
        with self._admission:
            found=self._match(value,exclude) if exclude else self._match(value)
            if found:
                return found
            with self._lock:
                if sha in self.known_shas:
                    return {'duplicate_of':sha,'reason':'same_bytes'}
                self.records[sha]=value;self.known_shas.add(sha)
                self._cache_dirty=True
            return None

    def rekey(self,old,new):
        """Move a verified original from a temporary path to its durable path."""
        old_key=str(Path(old).resolve());new_path=Path(new).resolve();new_key=str(new_path)
        if old_key==new_key:return False
        with self._lock:
            entry=self._cache_files.pop(old_key,None)
            stat=self._stat_key(new_path)
            if entry is not None and stat is not None:
                entry=dict(entry);entry['size']=stat['size'];entry['mtime_ns']=stat['mtime_ns']
                self._cache_files[new_key]=entry;self._cache_dirty=True
            for record in self.records.values():
                if record.get('path')==old_key:
                    record['path']=new_key
            return entry is not None

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
                self._pyramids.pop(sha,None)
        return removed
