"""Local-only duplicate exclusion. Never changes source images or human choices."""
from __future__ import annotations

import hashlib
import json
import os
from pathlib import Path

from PIL import Image, ImageOps

from .preflight import compute_dhash, hamming_distance


def historical_paths(root: Path, current: Path):
    root=root.resolve();current=current.resolve();local=root/'.local';paths=set()
    config=local/'windows-runtime.json'
    configured=os.environ.get('LAB_DATA_DIR')
    if not configured and config.exists():configured=json.loads(config.read_text('utf-8-sig'))['data_dir']
    data=Path(configured) if configured else root/'data'
    if not data.is_absolute():data=root/data
    originals=Path(os.environ.get('LAB_COLLECTION_HISTORY_DIR') or data/'assets')
    for path in originals.glob('*/*/original.*'):
        if path.is_file() and not path.is_symlink():paths.add(path.resolve())
    for base,dirs,files in os.walk(local,followlinks=False):
        base=Path(base)
        dirs[:]=[name for name in dirs if name not in {'worktrees','backups','public','baseline','reference-research','reference-images','visual-references','node_modules','__pycache__','.git','restored-library'}
                 and not name.startswith(('test','pytest','browser')) and not (base/name).is_symlink()
                 and not getattr(base/name,'is_junction',lambda:False)()
                 and not (base/name).resolve().is_relative_to(current)]
        if base.resolve().is_relative_to(current) or 'received.json' not in files:continue
        received=json.loads((base/'received.json').read_text('utf8'))
        records=received.get('candidates',[]) if isinstance(received,dict) else received
        for row in records:
            path=Path(row['original_path']).resolve()
            if not path.is_relative_to(local.resolve()):raise ValueError('Historical image escapes local collection boundary')
            if not path.is_file():raise ValueError('Historical original is missing; cannot prove no repeat')
            if hashlib.sha256(path.read_bytes()).hexdigest()!=row['asset_sha']:raise ValueError('Historical image SHA changed')
            paths.add(path)
    return sorted(paths)


def fingerprint(path: Path):
    raw=path.read_bytes()
    if len(raw)>20*1024*1024:raise ValueError('Duplicate input exceeds image size limit')
    with Image.open(path) as im:
        if im.width*im.height>40_000_000 or getattr(im,'n_frames',1)!=1:raise ValueError('Unsafe duplicate image input')
        display=ImageOps.exif_transpose(im).convert('RGB')
        return {'asset_sha':hashlib.sha256(raw).hexdigest(),'path':str(path.resolve()),
                'ratio':display.width/display.height,'dhash':compute_dhash(display),
                'sample':display.resize((8,8),Image.Resampling.LANCZOS).tobytes().hex()}


class ImageHistory:
    def __init__(self,paths):
        self.records={}
        for path in paths:
            value=fingerprint(path);self.records[value['asset_sha']]=value
        self.initial_count=len(self.records)

    def consider(self,path):
        value=fingerprint(path);sha=value['asset_sha']
        if sha in self.records:return {'duplicate_of':sha,'reason':'same_bytes'}
        sample=bytes.fromhex(value['sample'])
        for other in self.records.values():
            if abs(value['ratio']/other['ratio']-1)>.03 or hamming_distance(value['dhash'],other['dhash'])>6:continue
            # Preserve originals; quarantine only close composition AND colour matches.
            difference=sum(abs(a-b) for a,b in zip(sample,bytes.fromhex(other['sample'])))/len(sample)
            if difference<=8:return {'duplicate_of':other['asset_sha'],'reason':'near_duplicate'}
        self.records[sha]=value
        return None
