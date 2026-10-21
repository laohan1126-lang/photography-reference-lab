"""Explicit mocked image-read evidence for program tests, never visual evidence."""
import hashlib
import json
from pathlib import Path
from ref_lab.collection_queue import read_json, write_json


def synthetic_type(folder, row, kind='cosplay_photo'):
    sha=row['asset_sha']
    result={'asset_sha':sha,'kind':kind,'evidence':'Synthetic fixture; no photographic accuracy claim.'}
    stream=(json.dumps({'event':'step_update','step_update':{'tool_name':'view_file','state':'DONE',
        'tool_info':{'parameters':{'AbsolutePath':row['original_path']}}}})+'\n'+
        json.dumps({'event':'result','result':{'status':'SUCCESS','response':json.dumps(result)}}))
    path=Path(folder)/'type-evidence'/f'{sha[:8]}.jsonl';path.parent.mkdir(exist_ok=True)
    path.write_text(stream,'utf8')
    data=read_json(Path(folder)/'photo-types.json',{'items':{},'calls':[]})
    data['items'][sha]={'asset_sha':sha,'status':'succeeded','producer':'synthetic-fixture',
        'result_status':'SUCCESS','result':result,'stream_path':str(path),
        'stream_sha':hashlib.sha256(path.read_bytes()).hexdigest(),
        'read_evidence':{'tool':'view_file','state':'DONE','asset_sha':sha,'preview_sha':sha}}
    write_json(Path(folder)/'photo-types.json',data)
