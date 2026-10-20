"""Cache integrity and provenance fixtures; no network or real visual judgement."""
import copy
import hashlib
import json
from pathlib import Path
import time

from PIL import Image
import pytest

from ref_lab.automatic_references import SourceAssessment, ReferenceResearch, assessment_prompt, parse_reference_page, trusted_images
from ref_lab.policy import digest
from ref_lab.reference_cache import ReferenceCache
from ref_lab.verified_collection import AntigravityCollectionAgent, NamePlan, save_evidence
from test_automatic_references import HTML, PLAN, PROJECT, assessment


def cache_fixture(tmp_path):
    source=tmp_path/'source';media=source/'reference-research/images';media.mkdir(parents=True)
    project={**PROJECT,'notes':''};model='synthetic-cache-only'
    html=HTML.replace('</body>','<img src="/character2.png" alt="测试甲 official design"></body>')
    page=parse_reference_page('https://example.org/role',html)
    images=[]
    for i,item in enumerate(page['images']):
        path=media/f'{i}.png';Image.new('RGB',(320,480),(i*70,100,150)).save(path)
        images.append({'asset_sha':hashlib.sha256(path.read_bytes()).hexdigest(),'path':str(path.resolve()),
                       'image_url':item['url'],'observed_image_url':item['url'],'page_image_context':item})
    value=assessment(images[0]['asset_sha'])
    value.images=[assessment(r['asset_sha']).images[0] for r in images]
    refs=trusted_images(value,page,PLAN,images)
    evidence={'project':project,'known_name_hypotheses':PLAN.model_dump(),'source_page':page,'downloaded_images':images}
    save_evidence(source/'run-info.json',{'model':model,'started_at':time.time()})
    save_evidence(source/'name-plan.json',{'plan':PLAN.model_dump()})
    save_evidence(source/'reference-research/source-1.json',page)
    (source/'reference-research/source-1.html').write_text(html,encoding='utf8')
    save_evidence(source/'reference-research/report.json',{'references':refs,'pages':[
        {'url':page['url'],'status':'trusted','assessment':value.model_dump(),'evidence':evidence}]})

    def receipt(prompt,value,inputs):
        sha=hashlib.sha256(prompt.encode()).hexdigest();key=sha[:16]
        reads=[{'tool':'view_file','state':'DONE','path':name,'step_index':i,'query':''} for i,name in enumerate(inputs)]
        binding={'model':model,'prompt_sha256':sha,'schema_sha256':digest(type(value).model_json_schema()),'inputs':inputs}
        save_evidence(source/f'agent-{key}.json',{'producer':'synthetic-test-only','binding':binding,'reads':reads,'result':value.model_dump()})
        save_evidence(source/f'attempt-{key}-1.json',{'state':'finished','termination':'returned','exit_code':0,
            'result_type':type(value).__name__,'tools':reads,'result':{'status':'SUCCESS','structured_output':value.model_dump()}})
    probe=object.__new__(AntigravityCollectionAgent)
    probe.run=lambda prompt,*args,**kwargs:receipt(prompt,PLAN,{})
    probe._plan_fresh(project)
    receipt(assessment_prompt(evidence),value,{r['path']:r['asset_sha'] for r in [*images[1:],images[0]]})
    return ReferenceCache(tmp_path/'cache'),source,project,model


@pytest.mark.parametrize('legacy',[False,True])
def test_valid_cache_rechecks_all_original_source_bindings_and_keeps_bytes(tmp_path,legacy):
    cache,source,project,model=cache_fixture(tmp_path)
    if legacy:
        report=json.loads((source/'reference-research/report.json').read_text('utf8'))
        del report['pages'][0]['evidence']
        save_evidence(source/'reference-research/report.json',report)
    entry=cache.seal(source,project,model)
    assert cache.load(project,model)==entry and len(entry['references'])==2
    research=ReferenceResearch(None,tmp_path/'new-run',project,PLAN)
    cache.restore(entry,research)
    for old,new in zip(entry['references'],research.references):
        assert Path(old['path']).read_bytes()==Path(new['path']).read_bytes()
        assert Path(new['path']).is_relative_to(tmp_path/'new-run')
    assert research.report()['search_queries']==0


@pytest.mark.parametrize('field,value',[('character','Other Person'),('work','Other Work'),('costume','Other Version'),('notes','Other instructions'),('brief','Other brief')])
def test_cache_requires_the_same_full_project_scope(tmp_path,field,value):
    cache,source,project,model=cache_fixture(tmp_path);cache.seal(source,project,model)
    assert cache.load({**project,field:value},model) is None
    assert cache.load(project,model+'-other') is None


@pytest.mark.parametrize('name',['reference-research/images/0.png','reference-research/source-1.html',
                               'reference-research/source-1.json','name-plan.json','reference-research/report.json'])
def test_changed_source_evidence_invalidates_cache_and_restore(tmp_path,name):
    cache,source,project,model=cache_fixture(tmp_path);entry=cache.seal(source,project,model)
    path=source/name;path.write_bytes(path.read_bytes()+b'changed')
    assert cache.load(project,model) is None
    with pytest.raises(ValueError):cache.restore(entry,ReferenceResearch(None,tmp_path/'new',project,PLAN))


def test_cache_age_is_original_evidence_age_and_not_refreshed_by_loading(tmp_path,monkeypatch):
    cache,source,project,model=cache_fixture(tmp_path);entry=cache.seal(source,project,model)
    import ref_lab.reference_cache as module
    monkeypatch.setattr(module.time,'time',lambda:entry['created_at']+86401)
    assert cache.load(project,model) is None
    with pytest.raises(ValueError,match='expired'):cache.seal(source,project,model)


def test_cache_cannot_be_resealed_to_assert_different_reference_labels(tmp_path):
    cache,source,project,model=cache_fixture(tmp_path);entry=cache.seal(source,project,model)
    entry['references'][0]['label']='Unverified replacement'
    entry.pop('seal_sha256');entry['seal_sha256']=digest(entry)
    save_evidence(cache.root/(entry['key']+'.json'),entry)
    assert cache.load(project,model) is None


@pytest.mark.parametrize('change',['missing_reads','wrong_prompt','wrong_schema','denied','no_attempt'])
def test_cache_rejects_success_without_exact_input_source_and_terminal_evidence(tmp_path,change):
    cache,source,project,model=cache_fixture(tmp_path)
    path=next(p for p in source.glob('agent-*.json') if json.loads(p.read_text('utf8'))['binding']['inputs'])
    receipt=json.loads(path.read_text('utf8'));attempt=source/('attempt-'+path.stem[6:]+'-1.json')
    if change=='missing_reads':receipt['reads']=[]
    elif change=='wrong_prompt':receipt['binding']['prompt_sha256']='f'*64
    elif change=='wrong_schema':receipt['binding']['schema_sha256']='f'*64
    elif change=='denied':
        data=json.loads(attempt.read_text('utf8'));data['result']['denied_actions']=['view_file'];save_evidence(attempt,data)
    elif change=='no_attempt':attempt.unlink()
    save_evidence(path,receipt)
    with pytest.raises(ValueError):cache.seal(source,project,model)


def test_reference_cache_rejects_code_contract_change(tmp_path,monkeypatch):
    cache,source,project,model=cache_fixture(tmp_path);cache.seal(source,project,model)
    import ref_lab.reference_cache as module
    original=module.file_sha
    monkeypatch.setattr(module,'file_sha',lambda p:'0'*64 if p.suffix=='.py' else original(p))
    assert cache.load(project,model) is None


def test_hot_reference_supplement_cannot_exceed_original_reference_capacity(tmp_path):
    research=ReferenceResearch(None,tmp_path,PROJECT,PLAN)
    research.references=[{'asset_sha':str(i)*64,'page_url':'https://example.org/official'} for i in range(8)]
    assert research.supplement('not covered') is False
    assert research.report()['search_queries']==0
