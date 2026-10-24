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
import sqlite3
import tempfile
import threading
from pathlib import Path

from PIL import Image, ImageOps

from .preflight import compute_dhash, hamming_distance


# Bump when representation or matching rules change; old admission needs review.
# Version 5: a crop template is bound to the image it was cut from, so a
# historical photo can no longer lend its template to the next one. Every
# admission receipt written under version 4 was produced by the old matching
# rules and must be re-checked instead of inherited.
FINGERPRINT_ALGORITHM_VERSION=5
CACHE_SCHEMA_VERSION=5
_DHASH=re.compile(r"[0-9a-f]{16}\Z")
_SAMPLE=re.compile(r"[0-9a-f]{384}\Z")
_SHA=re.compile(r"[0-9a-f]{64}\Z")


def _is_link_or_junction(path):
    return path.is_symlink() or getattr(path,'is_junction',lambda:False)()


class HistoricalBytesMissing(ValueError):
    """A verified historical original no longer exists on disk."""


class HistoryIntegrityBlocked(HistoricalBytesMissing):
    """A missing historical byte set has no verifiable retained copy.

    The history cannot be proven complete in this state, so the caller has to
    stop with a named reason instead of continuing on an unproven basis.
    """

    category = 'history_integrity_blocked'


class BaselineNeedsUpgrade(ValueError):
    """The frozen baseline was written under older matching rules."""


def _decodable_image(path):
    """True when the file is a complete image, not a truncated leftover."""
    try:
        with Image.open(path) as image:
            image.load()
        return True
    except Exception:  # noqa: BLE001 - an unreadable file is not a keeper
        return False


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


class HistoryScope:
    """Verified duplicate scope for one project plus the library exact index.

    ``paths`` is the perceptual comparison set: assets referenced by this
    project and originals received by this project's own collection jobs
    (including failed or never-imported batches). ``library_keepers`` is the
    whole-library lightweight exact-byte index (SHA -> retained file); it is
    built from content-addressed names only, never decoded up front, and is
    verified byte-for-byte before anything is reported or reused. Runs whose
    job cannot be attributed from a library database are kept out of both sets
    and reported, instead of falling back to a whole-library scan.
    """

    def __init__(self):
        self.project_id = ''
        self.paths: list[str] = []
        self.library_keepers: dict[str, str] = {}
        self.project_run_dirs: list[str] = []
        self.attributed_runs: dict[str, str] = {}
        self.unattributed_runs: list[dict] = []
        self.report: dict = {}


def _runtime_data_dir(root: Path, *, primary: bool) -> Path:
    """The library data directory that backs one checkout's history.

    The primary checkout honours the collector's explicit asset directory
    (``LAB_COLLECTION_HISTORY_DIR``), so an isolated adapter scratch
    ``LAB_DATA_DIR`` cannot hide the real library or its jobs database.
    """
    local = root / '.local'
    if _is_link_or_junction(local):
        raise ValueError('History root local directory cannot be a link')
    if primary:
        history_dir = os.environ.get('LAB_COLLECTION_HISTORY_DIR')
        if history_dir:
            return Path(history_dir).resolve().parent
        configured = os.environ.get('LAB_DATA_DIR')
        if configured:
            return Path(configured)
    config = local / 'windows-runtime.json'
    if _is_link_or_junction(config):
        raise ValueError('History runtime configuration cannot be a link')
    if config.exists():
        return Path(json.loads(config.read_text('utf-8-sig'))['data_dir'])
    return root / 'data'


def _read_only_library(data_dir: Path):
    """A read-only connection to one checkout's library, or None when absent."""
    if not isinstance(data_dir, Path):
        return None
    db = data_dir / 'library.sqlite3'
    if not db.is_file() or db.is_symlink():
        return None
    try:
        con = sqlite3.connect(db.resolve().as_uri() + '?mode=ro', uri=True)
        con.execute("SELECT 1 FROM sqlite_master WHERE type='table' AND name='jobs'").fetchone()
        return con
    except (sqlite3.Error, OSError, ValueError):
        return None


def _collection_job_owners(data_dir: Path) -> dict[str, str]:
    """job_id -> project_id for collection jobs, from one checkout's library."""
    con = _read_only_library(data_dir)
    if con is None:
        return {}
    try:
        rows = con.execute("SELECT id, project_id FROM jobs WHERE kind='collection'").fetchall()
    except sqlite3.Error:
        return {}
    finally:
        con.close()
    return {str(job_id): str(project_id) for job_id, project_id in rows
            if isinstance(job_id, str) and isinstance(project_id, str) and job_id and project_id}


def _project_reference_shas(data_dir: Path, project_id: str) -> set[str]:
    """Asset SHAs this project actually uses; detached uses are not current."""
    con = _read_only_library(data_dir)
    if con is None:
        return set()
    try:
        rows = con.execute(
            "SELECT asset_sha, data FROM refs WHERE project_id=? AND asset_sha IS NOT NULL",
            (project_id,)).fetchall()
    except sqlite3.Error:
        return set()
    finally:
        con.close()
    shas = set()
    for sha, blob in rows:
        if not isinstance(sha, str) or not _SHA.fullmatch(sha):
            continue
        try:
            record = json.loads(blob) if isinstance(blob, (str, bytes)) else {}
        except ValueError:
            continue
        if isinstance(record, dict) and record.get('detached_at'):
            continue
        shas.add(sha)
    return shas


def _run_bases(root: Path, job_owners: dict[str, str]):
    """Bounded run discovery: attributed runs by job id, unattributed reported.

    Only ``collection-runs/<job_id>/`` and ``backups/<...>/<job_id>/`` shapes
    are ever read, and each is attributed through a library database. There is
    no recursive walk of ``.local`` and no directory-name heuristic: synthetic
    test, QA or probe directories (no job row) can never enter the real history
    scope, and nothing is deleted from them.
    """
    local = root / '.local'
    if _is_link_or_junction(local):
        raise ValueError('History root local directory cannot be a link')
    attributed: list[tuple[Path, str]] = []
    unattributed: list[dict] = []
    runs_dir = local / 'collection-runs'
    if runs_dir.is_dir() and not _is_link_or_junction(runs_dir):
        for entry in sorted(runs_dir.iterdir()):
            if _is_link_or_junction(entry) or not entry.is_dir():
                continue
            owner = job_owners.get(entry.name)
            bases = [entry / 'current', *sorted(
                base.parent for base in entry.glob('*') if base.name != 'current'
                and (base / 'received.json').is_file())]
            if (entry / 'received.json').is_file():
                bases.append(entry)
            for base in bases:
                if not ((base / 'received.json').is_file() or (base / 'images').is_dir()):
                    continue
                if owner:
                    attributed.append((base, owner))
                else:
                    unattributed.append(base)
    backups = local / 'backups'
    if backups.is_dir() and not _is_link_or_junction(backups):
        for base in sorted(backups.glob('*/*/*/received.json')):
            base = base.parent
            if _is_link_or_junction(base):
                continue
            owner = job_owners.get(base.parent.name)
            if owner:
                attributed.append((base, owner))
            else:
                unattributed.append(base)
    return attributed, unattributed


def _received_row_count(base: Path) -> int:
    try:
        payload = json.loads((base / 'received.json').read_text('utf8'))
    except (OSError, ValueError):
        return 0
    records = payload.get('candidates', []) if isinstance(payload, dict) else payload
    return len(records) if isinstance(records, list) else 0


def _run_exact_names(base: Path) -> dict[str, str]:
    """SHA -> file path for a run's received originals (verified on use).

    Both the SHA-named files in the run's image directory and the verified
    SHA bindings in ``received.json`` feed the library-wide exact index.
    """
    images = base / 'images'
    names: dict[str, str] = {}
    if _is_link_or_junction(images) or not images.is_dir():
        return names
    for path in images.iterdir():
        sha = path.stem
        if path.is_file() and not path.is_symlink() and _SHA.fullmatch(sha):
            names.setdefault(sha, str(path.resolve()))
    try:
        payload = json.loads((base / 'received.json').read_text('utf8'))
    except (OSError, ValueError):
        return names
    records = payload.get('candidates', []) if isinstance(payload, dict) else payload
    if not isinstance(records, list):
        return names
    for row in records:
        if not isinstance(row, dict):
            continue
        sha = row.get('asset_sha')
        path = row.get('original_path')
        if isinstance(sha, str) and _SHA.fullmatch(sha) and isinstance(path, str):
            resolved = Path(path)
            if resolved.is_file() and not resolved.is_symlink():
                names.setdefault(sha, str(resolved.resolve()))
    return names


def collect_history_scope(root, current, project_id, history_roots=(), skipped=None,
                          unattributed=None) -> HistoryScope:
    """Build one project's verified duplicate scope and the library exact index.

    Raises :class:`HistoryIntegrityBlocked` when a verifiable historical byte
    set of this project is missing without a retained keeper: the scope must
    stay provably complete instead of silently shrinking.
    """
    root = Path(root)
    if _is_link_or_junction(root):
        raise ValueError('History root cannot be a link')
    if not isinstance(project_id, str) or not project_id:
        raise HistoryIntegrityBlocked(
            'Collection history requires a verifiable project identity; refusing a whole-library scope')
    root = root.resolve()
    current = Path(current).resolve()
    scope = HistoryScope()
    scope.project_id = project_id
    paths: set[Path] = set()
    roots = []
    for candidate in (root, *history_roots):
        candidate = Path(candidate)
        if _is_link_or_junction(candidate):
            raise ValueError('History root cannot be a link')
        try:
            candidate = candidate.resolve(strict=True)
        except (OSError, RuntimeError) as exc:
            raise ValueError('History root is unavailable') from exc
        if not candidate.is_dir():
            raise ValueError('History root is unavailable')
        if candidate not in roots:
            roots.append(candidate)
    boundaries = [(candidate / '.local').resolve() for candidate in roots]
    data_dir = _runtime_data_dir(root, primary=True)
    originals = Path(os.environ.get('LAB_COLLECTION_HISTORY_DIR') or data_dir / 'assets')
    # One index of the canonical retained copies across every authorized asset
    # store. Names are content-addressed by ingestion; the bytes of a keeper are
    # re-verified before it stands in for anything or is reused.
    keepers: dict[str, Path] = {}
    def add_asset_name(path: Path):
        if not path.is_file() or path.is_symlink():
            return
        sha = path.parent.name
        if _SHA.fullmatch(sha):
            keepers.setdefault(sha, path.resolve())
    for path in originals.glob('*/*/original.*'):
        add_asset_name(path)
    for history_root in roots[1:]:
        store = _runtime_data_dir(history_root, primary=False) / 'assets'
        for path in store.glob('*/*/original.*'):
            add_asset_name(path)

    def resolve(base: Path, declared, sha, role):
        """The verified file that stands for one historical byte set.

        A cleaned-up archived run can be missing its own copy while the library
        still holds the canonical asset; that keeper is accepted only when its
        bytes and decodability are proven, and its use is counted.
        """
        try:
            return _historical_file(base, str(declared), sha, role, boundaries), False
        except HistoricalBytesMissing:
            keeper = keepers.get(sha)
            if keeper is None:
                raise HistoryIntegrityBlocked(
                    f'No verifiable keeper for missing historical bytes: {sha}') from None
            if hashlib.sha256(keeper.read_bytes()).hexdigest() != sha or not _decodable_image(keeper):
                raise HistoryIntegrityBlocked(f'No verifiable keeper for missing historical bytes: {sha}')
            return keeper, True

    def read_run(base: Path) -> int:
        """Verify one attributed run into the perceptual scope; keeper uses."""
        if base.resolve().is_relative_to(current):
            return 0
        received = base / 'received.json'
        if not received.is_file():
            return 0
        payload = json.loads(received.read_text('utf8'))
        records = payload.get('candidates', []) if isinstance(payload, dict) else payload
        images = base / 'images'
        if _is_link_or_junction(images):
            raise ValueError('Historical image directory cannot be a link')
        keeper_uses = 0
        for original in (images.glob('*') if images.is_dir() else []):
            sha = original.stem
            if original.suffix.lower() in {'.jpg', '.jpeg', '.png', '.webp', '.avif'} and _SHA.fullmatch(sha):
                path, kept = resolve(base, original, sha, 'images')
                paths.add(path)
                keeper_uses += kept
        for row in records:
            path, kept = resolve(base, row['original_path'], row['asset_sha'], 'images')
            paths.add(path)
            keeper_uses += kept
        derived = base / 'derived.json'
        if derived.is_file():
            from .collage import VALID
            data = json.loads(derived.read_text('utf8'))
            items = data.get('items') if isinstance(data, dict) else None
            if not isinstance(items, dict):
                raise ValueError('Historical derived records are invalid')
            for parent_sha, record in (items or {}).items():
                if not isinstance(record, dict):
                    continue
                if record.get('parent_sha') != parent_sha:
                    raise ValueError('Historical tile parent binding changed')
                for child in record.get('children') or []:
                    if not isinstance(child, dict) or child.get('status') != VALID:
                        continue
                    sha = str(child.get('child_sha') or '')
                    if not sha:
                        continue
                    path, kept = resolve(base, child.get('path') or '', sha, 'derived')
                    paths.add(path)
                    keeper_uses += kept
        return keeper_uses

    run_counts = {'attributed': 0, 'project_runs': 0, 'unattributed': 0, 'keeper_resolved': 0}
    for history_root in roots:
        primary = history_root == roots[0]
        root_data = data_dir if primary else _runtime_data_dir(history_root, primary=False)
        job_owners = _collection_job_owners(root_data)
        attributed, unowned = _run_bases(history_root, job_owners)
        for base, owner in attributed:
            scope.attributed_runs[str(base)] = owner
            run_counts['attributed'] += 1
            if owner == project_id:
                scope.project_run_dirs.append(str(base))
                keeper_uses = read_run(base)
                run_counts['project_runs'] += 1
                run_counts['keeper_resolved'] += keeper_uses
                if keeper_uses and skipped is not None:
                    skipped.append({'run': str(base),
                                    'reason': 'archived copies cleaned; every missing byte set resolved to a verified keeper',
                                    'received_rows': _received_row_count(base),
                                    'resolved_shas': keeper_uses})
        for base in unowned:
            run_counts['unattributed'] += 1
            entry = {'run': str(base), 'received_rows': _received_row_count(base),
                     'reason': 'collection run has no verifiable project attribution in any '
                               'library database; excluded from similar-image dedup scope, '
                               'original records kept unchanged'}
            scope.unattributed_runs.append(entry)
            if unattributed is not None:
                unattributed.append(entry)

    # This project's referenced assets join the perceptual scope from their
    # retained canonical copies; a copy whose bytes no longer match its
    # content address blocks the scope instead of quietly shrinking it.
    reference_shas = _project_reference_shas(data_dir, project_id)
    reference_in_scope = 0
    for sha in sorted(reference_shas):
        keeper = keepers.get(sha)
        if keeper is None or not keeper.is_file() or keeper.is_symlink():
            continue
        if hashlib.sha256(keeper.read_bytes()).hexdigest() != sha:
            raise ValueError(f'Historical asset SHA changed: {keeper}')
        paths.add(keeper)
        reference_in_scope += 1

    # Whole-library exact index: retained asset copies plus every attributed
    # run's received originals. Unattributed runs are reported, never indexed.
    for sha, path in keepers.items():
        scope.library_keepers.setdefault(sha, str(path))
    for base, owner in scope.attributed_runs.items():
        for sha, path in _run_exact_names(Path(base)).items():
            scope.library_keepers.setdefault(sha, path)
    scope.paths = sorted(paths)
    scope.report = {
        'project_id': project_id,
        'reference_assets_in_scope': reference_in_scope,
        'reference_assets_missing': len(reference_shas) - reference_in_scope,
        'runs': run_counts,
        'project_run_dirs': len(scope.project_run_dirs),
        'library_keepers': len(scope.library_keepers),
        'perceptual_paths': len(scope.paths),
    }
    return scope


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
        raise BaselineNeedsUpgrade('Goal baseline fingerprints need explicit upgrade')
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

    A template is a crop of one specific image, so its cache key names that
    image's SHA. Only the candidate's own templates are reused across the
    historical records of one scan; a template cut from a historical image is
    rebuilt for that record. Reusing it would let one photo lend its template
    to the next one and make the verdict depend on the order of the history.
    Historical pyramids live in a side cache keyed by asset SHA, so observable
    record dicts stay unchanged and later queries reuse the work.
    """
    __slots__=('_templates','_pyramids','_candidate')

    def __init__(self, pyramids=None, candidate=None):
        self._templates={}
        self._pyramids=pyramids if pyramids is not None else {}
        self._candidate=candidate

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
            'asset_sha':key,
            'arr':arr,
            'image':None,
            'small32':cv2.resize(arr,(32,32),interpolation=cv2.INTER_AREA),
            'small64':cv2.resize(arr,(64,64),interpolation=cv2.INTER_AREA),
            'target32':np.asarray(image.resize((32,32),Image.Resampling.LANCZOS)),
        }
        self._pyramids[key]=feature
        return feature

    def template(self,side,query,kind,width,height,resolution=None):
        sha=query.get('asset_sha')
        key=(sha,kind,resolution,width,height)
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
        if kind!='lanczos':
            spread=float(cv2.meanStdDev(template)[1].max())
            # Keep the original numerical decision at the threshold boundary.
            if abs(spread-3)<1e-7:spread=template.reshape(-1,3).std(axis=0).max()
            if spread<3:
                if sha==self._candidate:self._templates[key]=False
                return False, False
        if sha==self._candidate:self._templates[key]=template
        return template, True


def _materialize_image(feature):
    if feature.get('image') is None:
        feature['image']=Image.fromarray(feature['arr'])
    return feature['image']


class ImageHistory:
    def __init__(self,paths,cache_path=None,*,lazy=False,library_keepers=None):
        try:__import__('cv2')
        except (ImportError,OSError) as exc:raise ValueError('History matcher unavailable') from exc
        self.cache_path=Path(cache_path) if cache_path is not None else None
        self._cache_files=_read_cache(self.cache_path) if self.cache_path is not None else {}
        # Whole-library lightweight exact-byte index: SHA -> retained file. It
        # never blocks a candidate; a hit means the identical original already
        # exists and the current project may reuse it as its own reference.
        self.library_keepers=dict(library_keepers or {})
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
        self._fingerprints_by_sha={}
        self.fingerprint_stats={'decoded':0,'content_reused':0,'hashed_bytes':0,'path_cache_hits':0}
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
            value={'asset_sha':cached['sha'],'path':key,'ratio':cached['ratio'],
                   'dhash':cached['dhash'],'sample':cached['sample'],'pixels':cached['pixels']}
            with self._lock:
                self._fingerprints_by_sha.setdefault(cached['sha'],value)
                self.fingerprint_stats['path_cache_hits']+=1
            return value
        raw=path.read_bytes()
        if len(raw)>20*1024*1024:raise ValueError('Duplicate input exceeds image size limit')
        sha=hashlib.sha256(raw).hexdigest()
        with self._lock:
            self.fingerprint_stats['hashed_bytes']+=len(raw)
            features=self._fingerprints_by_sha.get(sha) or self.records.get(sha)
            if features is None:
                features=_fingerprint_from_raw(path,raw,sha)
                self._fingerprints_by_sha[sha]=features
                self.fingerprint_stats['decoded']+=1
            else:self.fingerprint_stats['content_reused']+=1
            value={**features,'path':key}
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
        context=_MatchContext(self._pyramids, value['asset_sha'])
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
            context=_MatchContext(self._pyramids, value['asset_sha'])
            for index in indexes:
                relation=_photo_relation(value,records[index],context)
                if relation:return index,records[index],relation
            return None
        chunks=[indexes[i::workers] for i in range(workers)]

        def scan(chunk):
            local=_MatchContext(self._pyramids, value['asset_sha'])
            for index in chunk:
                relation=_photo_relation(value,records[index],local)
                if relation:return index,records[index],relation
            return None

        with ThreadPoolExecutor(max_workers=workers) as pool:
            results=[result for result in pool.map(scan,chunks) if result]
        return min(results,key=lambda item:item[0]) if results else None

    def _verified_keeper(self,sha):
        """The retained copy of a whole-library exact hit, bytes proven.

        Returns None when the SHA belongs to this project's own duplicate scope
        (that is a repeat, not a reuse) or when no verifiable keeper exists.
        """
        if sha in self.known_shas:
            return None
        path=self.library_keepers.get(sha)
        if not path:
            return None
        path=Path(path)
        try:
            if not path.is_file() or path.is_symlink():
                return None
            if hashlib.sha256(path.read_bytes()).hexdigest()!=sha:
                return None
        except OSError:
            return None
        return path

    def consider(self,path,*,exclude=()):
        """Compare outside the lock, then commit atomically.

        The heavy perceptual comparison no longer holds the shared lock, so a
        concurrent Review/Goal admission can still inspect history. The final
        commit re-checks ``known_shas`` under the lock, keeping exact-byte
        dedupe atomic for concurrent image accounting.

        A whole-library exact hit that is not this project's own bytes is a
        reuse, not a duplicate: the value is committed into this project's
        records (later candidates must compare against it) and the caller is
        told which retained file stands for the identical bytes.
        """
        value=self._fingerprint(path);sha=value['asset_sha']
        with self._admission:
            found=self._match(value,exclude) if exclude else self._match(value)
            if found:
                return found
            with self._lock:
                if sha in self.known_shas:
                    return {'duplicate_of':sha,'reason':'same_bytes'}
                keeper=self._verified_keeper(sha)
                self.records[sha]=value;self.known_shas.add(sha)
                self._cache_dirty=True
            if keeper is not None:
                return {'duplicate_of':sha,'reason':'same_bytes_library','reuse':True,
                        'keeper_path':str(keeper)}
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
