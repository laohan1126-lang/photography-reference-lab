#!/usr/bin/env python3
"""Install only the owner's separately supplied Kana art; no network or Git writes."""
from __future__ import annotations
import argparse,hashlib,json,shutil,time
from pathlib import Path
EXPECTED = {'portrait.webp': '869c847d5561dbaaec6bbdadabe1aa31b1ef077e0e7dcc8cf09a32a8587a6bce', 'rain.webp': '3614c04eb47a8a0acf8216c913a5d3beb5c8c7a5ac5fc4c9a30e44f9d328cf8c', 'summer.webp': 'f823b3d6e703c7f981eca018c7d1686299f52e184f5108140347a067b3a1f041'}

def install(source: Path, root: Path) -> list[str]:
    source=source.resolve();root=root.resolve()
    target=root/'web'/'private'/'kana'
    if not target.resolve().is_relative_to(root):
        raise ValueError('Destination must stay inside this checkout')
    payload={}
    for name,digest in EXPECTED.items():
        p=source/name
        if not p.is_file():raise ValueError(f'Missing required asset: {name}')
        data=p.read_bytes()
        if hashlib.sha256(data).hexdigest()!=digest:raise ValueError(f'Asset hash mismatch: {name}')
        payload[name]=data
    target.mkdir(parents=True,exist_ok=True)
    written=[]
    for name,data in payload.items():
        dest=target/name
        if dest.is_symlink():raise ValueError(f'Refusing symlink: {name}')
        if dest.exists() and dest.read_bytes()!=data:
            backup=target/('.backup-'+str(time.time_ns())+'-'+name)
            shutil.copy2(dest,backup)
        temp=target/(name+'.installing');temp.write_bytes(data);temp.replace(dest);written.append(name)
    return written

def main() -> int:
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--source',type=Path,required=True)
    p.add_argument('--repo-root',type=Path,default=Path(__file__).resolve().parents[1])
    args=p.parse_args()
    try: print(json.dumps({'status':'INSTALLED','files':install(args.source,args.repo_root)},ensure_ascii=False));return 0
    except (OSError,ValueError) as error: print(json.dumps({'status':'ERROR','message':str(error)},ensure_ascii=False));return 1
if __name__=='__main__':raise SystemExit(main())
