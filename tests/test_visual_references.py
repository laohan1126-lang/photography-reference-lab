import hashlib
import json
from pathlib import Path

import pytest
from PIL import Image

from ref_lab.policy import digest
from ref_lab.verified_collection import (AgentUnavailable, CollectionVision, load_visual_references,
                                         parse_agent_stream, scope_sha)


def test_missing_reads_and_invalid_structure_have_distinct_diagnostics(tmp_path):
    path=tmp_path/'target.png'
    final={'event':'result','result':{'status':'SUCCESS','structured_output':{'invalid':'shape'}}}
    with pytest.raises(AgentUnavailable) as missing:
        parse_agent_stream(json.dumps(final),CollectionVision,path)
    assert missing.value.code=='missing_reads'
    opened={'step_update':{'tool_name':'view_file','state':'DONE','tool_info':{'parameters':{'AbsolutePath':str(path.resolve())}}}}
    with pytest.raises(AgentUnavailable) as invalid:
        parse_agent_stream(json.dumps(opened)+'\n'+json.dumps(final),CollectionVision,path)
    assert invalid.value.code=='invalid_structure'


PROJECT={'character':'Example Person','work':'Example','costume':''}


def pack(tmp_path):
    root=tmp_path/'catalog';root.mkdir()
    image=root/'reference.png';Image.new('RGB',(16,16),'blue').save(image)
    ref={'file':image.name,'asset_sha':hashlib.sha256(image.read_bytes()).hexdigest(),
         'page_url':'https://example.org/official','label':'Example outfit A','authority':'official_publisher'}
    path=root/(digest({k:PROJECT.get(k,'') for k in ('character','work')})+'.json')
    path.write_text(json.dumps({**{k:PROJECT[k] for k in ('character','work')},'references':[ref]}),encoding='utf8')
    folder=tmp_path/'run';folder.mkdir()
    return root,folder,path,ref,image


def test_reference_pack_binds_role_and_preserves_image_bytes(tmp_path):
    root,folder,_,ref,image=pack(tmp_path)
    loaded=load_visual_references(PROJECT,folder,root=root)
    assert len(loaded)==1 and loaded[0]['asset_sha']==ref['asset_sha']
    assert Path(loaded[0]['path']).read_bytes()==image.read_bytes()
    assert Path(loaded[0]['path']).is_relative_to(folder)
    assert load_visual_references({**PROJECT,'character':'Other'},folder,root=root)==[]


@pytest.mark.parametrize('change',['wrong_sha','outside_path','wrong_role','secondary_source'])
def test_invalid_reference_pack_is_blocked_not_silently_trusted(tmp_path,change):
    root,folder,path,ref,image=pack(tmp_path)
    data=json.loads(path.read_text('utf8'))
    if change=='wrong_sha':data['references'][0]['asset_sha']='0'*64
    if change=='outside_path':data['references'][0]['file']='../outside.png'
    if change=='wrong_role':data['character']='Other'
    if change=='secondary_source':data['references'][0]['authority']='search_title'
    path.write_text(json.dumps(data),encoding='utf8')
    with pytest.raises(AgentUnavailable):load_visual_references(PROJECT,folder,root=root)


def test_success_requires_actual_target_and_all_reference_reads(tmp_path):
    target=tmp_path/'target.png';ref=tmp_path/'reference.png'
    value=dict(asset_sha='a'*64,context_sha=scope_sha(PROJECT),kind='cosplay_photo',identity='match',
               costume='not_required',confidence='high',kind_evidence=['Photo'],identity_evidence=['Outfit details'],
               costume_evidence=[],reason='Synthetic fixture only')
    def opened(path):return {'step_update':{'tool_name':'view_file','state':'DONE',
        'tool_info':{'parameters':{'AbsolutePath':str(path.resolve())}}}}
    final={'event':'result','result':{'status':'SUCCESS','structured_output':value}}
    stream='\n'.join(json.dumps(x) for x in [opened(target),final])
    with pytest.raises(AgentUnavailable):parse_agent_stream(stream,CollectionVision,target,reference_paths=(ref,))
    stream='\n'.join(json.dumps(x) for x in [opened(target),opened(ref),final])
    assert parse_agent_stream(stream,CollectionVision,target,reference_paths=(ref,)).identity=='match'
    broken=opened(ref);broken['step_update']['tool_info']['error']={'message':'denied'}
    with pytest.raises(AgentUnavailable):parse_agent_stream('\n'.join(json.dumps(x) for x in [opened(target),broken,final]),CollectionVision,target,reference_paths=(ref,))


def test_nested_schema_is_passed_as_a_real_base_file(tmp_path,monkeypatch):
    import ref_lab.verified_collection as module
    captured=[]
    value=dict(asset_sha='a'*64,context_sha=scope_sha(PROJECT),kind='unknown',identity='uncertain',
        costume='not_required',confidence='low',kind_evidence=[],identity_evidence=[],costume_evidence=[],reason='Synthetic transport fixture')
    class Process:
        returncode=0
        def communicate(self,**kwargs):return json.dumps({'event':'result','result':{'status':'SUCCESS','structured_output':value}}),''
        def poll(self):return 0
        def wait(self,**kwargs):return 0
    import ref_lab.agent_collection as runner
    monkeypatch.setattr(runner,'stop_process_tree',lambda process:process.wait(timeout=10))
    monkeypatch.setattr(module,'find_antigravity_cli',lambda:'agy')
    monkeypatch.setattr(module.subprocess,'Popen',lambda command,**kwargs:captured.append(command) or Process())
    module.AntigravityCollectionAgent(tmp_path).run('Synthetic transport only',CollectionVision)
    command=captured[0];schema=Path(command[command.index('--json-schema')+1])
    assert schema.is_file() and '$defs' in json.loads(schema.read_text('utf8'))
