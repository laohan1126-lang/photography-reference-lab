"""One atomic task checkpoint; originals and model receipts remain independent evidence."""
from __future__ import annotations

import ast
import hashlib
import json
from pathlib import Path
from uuid import uuid4

from .policy import digest


def rule_contract():
    root=Path(__file__).resolve().parent
    selected={
        'verified_collection.py':{'CollectionVision','ReferenceComparison','accepted','scope_sha',
            'reference_supported','parse_agent_stream','_plan_fresh','needs_supplement','complete_review','_review_once'},
        'automatic_references.py':{'SourceAssessment','ReferenceImageAssessment','trusted_images','assessment_prompt'},
        'models.py':{'Source','PackCandidate','PackCandidateV3','CandidatePackage','CollectionReport','SourceCheck','QueryAttempt'},
    }
    return digest({name:[ast.dump(node,include_attributes=False) for node in ast.walk(ast.parse((root/name).read_text('utf8')))
                         if isinstance(node,(ast.ClassDef,ast.FunctionDef)) and node.name in names]
                   for name,names in selected.items()})


def job_binding(job,model):
    return {'job_id':job['id'],'project':job['project_snapshot'],'notes':job.get('notes',''),
            'target_count':job.get('target_count',12),'preferred_sources':job.get('preferred_sources',None),
            'model':model,'rules':rule_contract()}


def read_json(path,default):
    return json.loads(path.read_text('utf8')) if path.exists() else default


def original_bytes(row,folder):
    path=Path(row['original_path'])
    if path.is_symlink() or not path.resolve().is_relative_to((folder/'images').resolve()):
        raise ValueError('Original escapes this collection')
    raw=path.read_bytes()
    if hashlib.sha256(raw).hexdigest()!=row['asset_sha']:
        raise ValueError('Original SHA changed')
    return raw


def check_references(references):
    for ref in references:
        if 'path' in ref:
            path=Path(ref['path'])
            if path.is_symlink() or hashlib.sha256(path.read_bytes()).hexdigest()!=ref['asset_sha']:
                raise ValueError('Reference original changed')


def load_checkpoint(folder,job,model):
    binding=job_binding(job,model)
    state=read_json(folder/'collector-state.json',None)
    if state is None:
        state={'version':1,'binding':binding,'batch_id':uuid4().hex,'received':[],'audit':[],
               'queries':[],'checks':{},'pages':[],'page_attempts':{},'duplicates':[],
               'collisions':[],'gaps':[],'searches':{},'details':0,'windows':0,'first_usable':None}
    if state.get('version')!=1 or state.get('binding')!=binding:
        raise ValueError('Collection job/model/rule binding changed')
    known={r['asset_sha']:r for r in state['received']}
    for row in read_json(folder/'received.json',[]):
        if row['asset_sha'] in known:
            if known[row['asset_sha']]!=row:raise ValueError('Received provenance changed')
        else:state['received'].append(row);known[row['asset_sha']]=row
    for row in state['received']:original_bytes(row,folder)
    if len(known)!=len(state['received']):raise ValueError('Duplicate received SHA')
    for record in state['audit']:
        if record['asset_sha'] not in known:raise ValueError('Audit without a received original')
        check_references(record.get('references',[]))
    check_references(state.get('references',[]))
    for name,sha in state.get('reference_files',{}).items():
        path=folder/name
        if path.is_symlink() or not path.resolve().is_relative_to(folder.resolve()) or hashlib.sha256(path.read_bytes()).hexdigest()!=sha:
            raise ValueError('Reference provenance changed')
    return state


def coverage(steps,searches,sources):
    required_languages={step.get('language','unknown') for step in steps}-{'unknown'}
    visited_sources={value['source'] for value in searches.values() if value.get('observed')}
    usable_sources={value['source'] for value in searches.values() if value.get('usable')}
    visited_languages={value.get('language') for value in searches.values() if value.get('observed')}
    usable_languages={value.get('language') for value in searches.values() if value.get('usable')}
    supported={step['source'] for step in steps}
    gaps=[]
    for source in sources:
        if source not in usable_sources:gaps.append('来源覆盖未满足：'+source)
    for language in sorted(required_languages-usable_languages):gaps.append('检索语言覆盖未满足：'+language)
    return {'satisfied':not gaps,'explored':supported.issubset(visited_sources) and required_languages.issubset(visited_languages),
            'required_languages':sorted(required_languages),'visited_languages':sorted(visited_languages- {None}),
            'usable_languages':sorted(usable_languages-{None}),'searched_sources':sorted(visited_sources),
            'usable_sources':sorted(usable_sources),'gaps':gaps}
