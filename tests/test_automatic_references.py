import hashlib
import json
from pathlib import Path

import pytest

from ref_lab.automatic_references import (SourceAssessment, ReferenceResearch, parse_reference_page,
    public_url, trusted_images)
from ref_lab.verified_collection import AgentUnavailable, NamePlan


PROJECT={'character':'测试甲','work':'Example Work','costume':''}
PLAN=NamePlan(names=['测试甲','Example Person'],work_aliases=['Example Work'],rights_holders=['Example Studio'])
HTML='''<html><head><title>Example Work Official Site</title></head><body>
<header>Example Studio Official Site</header><h1>测试甲 Character Design</h1>
<p>Official character design for 测试甲.</p><img src="/character.png" alt="测试甲 official design">
<script>secret_image="https://example.org/hidden.png"</script><img src="/logo.png" alt="Logo">
<footer>Copyright Example Studio</footer></body></html>'''


def assessment(sha):
    return SourceAssessment(authority='official_publisher',operator_name='Example Studio',
        operator_quote='Example Studio Official Site',manufacturer_name='',manufacturer_quote='',license_quote='',
        reason='Synthetic primary-page fixture only',images=[{'asset_sha':sha,'usable':True,
        'label':'测试甲 · Design A','binding':'page_label','binding_quote':'Official character design for 测试甲.',
        'visible_evidence':['Visible clothing design fixture']}])


def test_supplement_authentication_failure_can_resume_its_saved_source(tmp_path):
    import io
    from PIL import Image
    from ref_lab.verified_collection import AgentCallFailed
    stream=io.BytesIO();Image.new('RGB',(320,480),'blue').save(stream,'PNG');raw=stream.getvalue()
    calls=[]
    class Agent:
        model='synthetic-only';blocked=True;last_tool_calls=[]
        def run(self,prompt,result_type,image_path=None,**kwargs):
            calls.append(result_type.__name__)
            if result_type.__name__=='ReferenceDiscovery':
                return result_type(urls=['https://example.org/role'],reason='Synthetic search')
            if self.blocked:raise AgentCallFailed('authentication_required',fatal=True)
            return assessment(hashlib.sha256(raw).hexdigest())
    def fetch(url,limit):return (raw,'image/png',url) if url.endswith('.png') else (HTML.encode(),'text/html',url)
    agent=Agent();research=ReferenceResearch(agent,tmp_path,PROJECT,PLAN,fetch=fetch)
    with pytest.raises(AgentUnavailable):research.supplement('Uncovered costume')
    charged=research.image_attempts
    agent.blocked=False
    recovered=ReferenceResearch(agent,tmp_path,PROJECT,PLAN,fetch=fetch)
    assert recovered.supplement('Uncovered costume')
    assert calls==['ReferenceDiscovery','SourceAssessment','SourceAssessment']
    assert recovered.image_attempts==charged and len(recovered.references)==1
    assert recovered.supplements[0]['status']=='added_evidence'


@pytest.mark.parametrize('meta,header',[
    ('<meta charset="GBK">','text/html'),
    ('<meta http-equiv="Content-Type" content="text/html; charset=gb2312">','text/html'),
    ('','text/html; charset=gb18030'),
])
def test_declared_html_encoding_preserves_primary_source_quotes(meta,header):
    markup=('<html><head>'+meta+'<title>西施 - 王者荣耀官方网站 - 腾讯游戏</title></head>'
            '<body><header>腾讯游戏</header><p>官方角色设定：西施</p>'
            '<img src="/design.png" alt="西施角色设定"><p>版权所有 腾讯游戏</p></body></html>')
    raw=markup.encode('gb18030');before=hashlib.sha256(raw).hexdigest()
    page=parse_reference_page('https://example.org/hero',raw,content_type=header)
    assert '西施' in page['title'] and '腾讯游戏' in page['identity_text']
    assert page['images'][0]['alt']=='西施角色设定'
    assert '\ufffd' not in page['text'] and hashlib.sha256(raw).hexdigest()==before


def test_html_bom_precedes_conflicting_charset_and_bad_bytes_fail_closed():
    raw=b'\xef\xbb\xbf'+ '<meta charset="gbk"><title>可信原文</title>'.encode('utf8')
    assert parse_reference_page('https://example.org/hero',raw)['title']=='可信原文'
    with pytest.raises(ValueError):parse_reference_page('https://example.org/hero',b'<title>\xff</title>')
    with pytest.raises(ValueError):parse_reference_page('https://example.org/hero',b'<meta charset="unknown-codec">')


def test_changed_html_interpretation_blocks_old_research_without_rewriting_evidence(tmp_path):
    class Agent:
        model='synthetic-only'
        def run(self,*args,**kwargs):pytest.fail('Old corrupted source must not be silently regraded')
    agent=Agent();research=ReferenceResearch(agent,tmp_path,PROJECT,PLAN)
    raw='<meta charset="gbk"><title>西施 王者荣耀官方网站 腾讯游戏</title>'.encode('gb18030')
    prefix=research.folder/'source-1';prefix.with_suffix('.html').write_bytes(raw)
    corrupted=parse_reference_page('https://example.org/hero',raw.decode('utf8',errors='replace'))
    prefix.with_suffix('.json').write_text(json.dumps(corrupted),encoding='utf8')
    research.pages=[{'url':'https://example.org/hero','discovery_url':'https://example.org/hero','status':'untrusted'}]
    research.save();before=prefix.with_suffix('.json').read_bytes()
    with pytest.raises(AgentUnavailable):ReferenceResearch(agent,tmp_path,PROJECT,PLAN)
    assert prefix.with_suffix('.json').read_bytes()==before


@pytest.mark.parametrize('url',['http://example.org/x','https://127.0.0.1/x','https://localhost/x',
    'https://10.0.0.1/x','https://user:pass@example.org/x','https://example.org:9000/x',
    'file:///private','https://thing.local/x'])
def test_reference_url_rejects_private_or_credential_bearing_destinations(url):
    with pytest.raises(ValueError):public_url(url)


def test_public_page_keeps_only_observed_image_urls_and_separate_site_identity():
    page=parse_reference_page('https://example.org/role',HTML)
    assert page['images'][0]['url']=='https://example.org/character.png'
    assert all('hidden' not in x['url'] for x in page['images'])
    assert 'Example Studio Official Site' in page['identity_text']
    assert '测试甲 Character Design' in page['text']


def test_profile_art_is_not_confused_with_navigation_graphics():
    page=parse_reference_page('https://example.org/member',HTML.replace('<img src="/character.png"',
        '<img src="/menu_news.png" alt="NEWS"><div style="background-image:url(/profile_visual.png)"></div><img src="/character.png"'))
    assert not any('menu_news' in row['url'] for row in page['images'])
    assert any(row['url']=='https://example.org/profile_visual.png' for row in page['images'])


def test_authority_label_without_actual_site_and_role_evidence_is_not_trusted():
    page=parse_reference_page('https://example.org/role',HTML)
    good=assessment('a'*64)
    assert len(trusted_images(good,page,PLAN,[{'asset_sha':'a'*64,'path':'unused'}]))==1
    bad=good.model_copy(deep=True);bad.operator_quote='Invented licensing assertion'
    assert trusted_images(bad,page,PLAN,[{'asset_sha':'a'*64}])==[]
    fan={**page,'title':'Example Work | Fandom','identity_text':'Fandom community wiki'}
    assert trusted_images(good,fan,PLAN,[{'asset_sha':'a'*64}])==[]
    bad=good.model_copy(deep=True);bad.images[0].binding_quote='A different person'
    assert trusted_images(bad,page,PLAN,[{'asset_sha':'a'*64}])==[]


def test_reference_image_must_be_one_of_the_actual_downloads():
    page=parse_reference_page('https://example.org/role',HTML)
    assert trusted_images(assessment('a'*64),page,PLAN,[{'asset_sha':'b'*64}])==[]


def test_licensed_work_credit_does_not_require_a_complete_translation_dictionary():
    html='''<title>Example Maker</title><header>Example Maker</header>
    <h1>测试甲 Model</h1><p>Series: Example Work</p>
    <p>Manufacturer: Example Maker. PVC scale model.</p>
    <p>© 2020 エグザンプル製作委員会</p><footer>© Example Maker</footer>'''
    page=parse_reference_page('https://example.org/product',html)
    source=SourceAssessment(authority='official_licensed_manufacturer',operator_name='Example Maker',
        operator_quote='Example Maker',manufacturer_name='Example Maker',
        manufacturer_quote='Manufacturer: Example Maker. PVC scale model.',
        license_quote='2020 エグザンプル製作委員会',work_quote='Series: Example Work',
        reason='Synthetic product/work credit in another language',images=assessment('a'*64).images)
    source.images[0].binding_quote='测试甲 Model'
    assert trusted_images(source,page,PLAN,[{'asset_sha':'a'*64}])
    for change in ({'work_quote':'Different Work'},{'license_quote':'Example Maker'},
                   {'license_quote':'Invented rights owner'},{'manufacturer_name':'Third-party reseller'}):
        assert not trusted_images(source.model_copy(update=change),page,PLAN,[{'asset_sha':'a'*64}])
    distributed=parse_reference_page('https://example.org/product',html.replace('<header>Example Maker</header>',
        '<header>Official Distributor</header>').replace('</p><footer>', '</p><p>Distributor: Official Distributor</p><footer>'))
    distributor=source.model_copy(update={'authority':'official_licensed_distributor','operator_name':'Official Distributor',
        'operator_quote':'Official Distributor','distributor_name':'Official Distributor','distributor_quote':'Distributor: Official Distributor'})
    assert trusted_images(distributor,distributed,PLAN,[{'asset_sha':'a'*64}])
    assert not trusted_images(distributor.model_copy(update={'distributor_quote':'Retail Store'}),distributed,PLAN,[{'asset_sha':'a'*64}])


def test_product_credit_parser_excludes_footer_and_scripts():
    page=parse_reference_page('https://example.org/product',
        '<p>© Other Studio</p><script>© Hidden Studio</script><footer>© Website Owner</footer>')
    assert 'Other Studio' in page['product_credits']
    assert 'Hidden Studio' not in page['product_credits'] and 'Website Owner' not in page['product_credits']


def test_copyright_credit_alone_does_not_make_an_archive_the_publisher():
    page=parse_reference_page('https://example.org/archive',HTML.replace('Example Work Official Site','Fan Art Archive').replace('Example Studio Official Site','Archive Community'))
    claimed=assessment('a'*64);claimed.operator_quote='Copyright Example Studio'
    assert trusted_images(claimed,page,PLAN,[{'asset_sha':'a'*64}])==[]


def test_automatic_research_is_generic_bounded_and_keeps_images_outside_photos(tmp_path):
    import io
    from PIL import Image
    image=io.BytesIO();Image.new('RGB',(320,480),'blue').save(image,'PNG');raw=image.getvalue()
    class Fetch:
        def __call__(self,url,limit):
            return (raw,'image/png',url) if url.endswith('.png') else (HTML.encode(),'text/html',url)
    class Agent:
        def __init__(self):self.last_tool_calls=[];self.prompts=[]
        def run(self,prompt,result_type,image_path=None,**kwargs):
            self.prompts.append(prompt)
            if result_type.__name__=='ReferenceDiscovery':
                self.last_tool_calls=[{'tool':'search_web','state':'DONE','query':kwargs['search_query']}]
                return result_type(urls=['https://example.org/role'],reason='Synthetic discovery only')
            return assessment(hashlib.sha256(raw).hexdigest())
    agent=Agent();research=ReferenceResearch(agent,tmp_path,PROJECT,PLAN,fetch=Fetch())
    research.prepare()
    assert len(research.references)==1
    assert Path(research.references[0]['path']).is_relative_to(tmp_path/'reference-research')
    assert not (tmp_path/'images').exists()
    assert research.report()['search_queries']==2 and research.report()['source_pages']==1
    assert research.report()['limited_reference_coverage'] is True
    assert not research.supplement('Uncovered outfit')  # Same source/bytes provide no new evidence.
    assert research.report()['search_queries']<=6 and research.report()['reference_image_attempts']<=8


@pytest.mark.parametrize('small_directory',['thumb','gallery'])
def test_small_named_thumbnails_do_not_hide_observed_full_size_reference(tmp_path,small_directory):
    import io
    from PIL import Image
    def pixels(size):
        b=io.BytesIO();Image.new('RGB',size,'blue').save(b,'PNG');return b.getvalue()
    small=pixels((75,75));large=pixels((320,480));fetched=[]
    page=HTML.replace('<img src="/character.png" alt="测试甲 official design">',
        f'<img src="/{small_directory}/first.png" alt="测试甲 official design">'
        f'<img src="/{small_directory}/second.png" alt="测试甲 official design">'
        '<img src="/large/design.png" alt="">')
    class Agent:
        last_tool_calls=[]
        def run(self,prompt,result_type,image_path=None,**kwargs):
            if result_type.__name__=='ReferenceDiscovery':return result_type(urls=['https://example.org/role'],reason='Fixture')
            assert Path(image_path).read_bytes()==large
            return assessment(hashlib.sha256(large).hexdigest())
    def fetch(url,limit):
        fetched.append(url)
        return ((small if f'/{small_directory}/' in url else large),'image/png',url) if url.endswith('.png') else (page.encode(),'text/html',url)
    research=ReferenceResearch(Agent(),tmp_path,PROJECT,PLAN,fetch=fetch);research.prepare()
    assert research.references and research.references[0]['image_url']=='https://example.org/large/design.png'
    assert set(fetched)<={'https://example.org/role',f'https://example.org/{small_directory}/first.png',f'https://example.org/{small_directory}/second.png','https://example.org/large/design.png'}
    assert research.image_attempts<=8


def test_supplement_execution_failure_preserves_first_prediction_and_trace(tmp_path,monkeypatch):
    from ref_lab.verified_collection import AntigravityCollectionAgent,CollectionVision,scope_sha
    agent=AntigravityCollectionAgent(tmp_path);agent.references=[]
    class Research:
        references=[]
        def supplement(self,hint):raise AgentUnavailable('Synthetic unavailable supplement')
    agent.research=Research()
    first=CollectionVision(asset_sha='a'*64,context_sha=scope_sha(PROJECT),kind='cosplay_photo',identity='uncertain',
        costume='not_required',confidence='low',photography_usable='yes',kind_evidence=['Synthetic photo'],
        identity_evidence=[],costume_evidence=[],photography_evidence=['手部姿态可辨'],reason='Fixture gap')
    monkeypatch.setattr(agent,'_review_once',lambda *args:first)
    assert agent.review(tmp_path/'unused.png',PROJECT)==first
    trace=json.loads((tmp_path/('candidate-trace-'+'a'*64+'.json')).read_text('utf8'))
    assert trace['model_predictions']==[first.model_dump()] and trace['supplement_error']


def test_missing_primary_evidence_blocks_before_photography(tmp_path):
    class Agent:
        last_tool_calls=[]
        def run(self,prompt,result_type,**kwargs):return result_type(urls=[],reason='No reliable primary result')
    research=ReferenceResearch(Agent(),tmp_path,PROJECT,PLAN,fetch=lambda *args:None)
    with pytest.raises(AgentUnavailable):research.prepare()
    assert not research.references and research.report()['search_queries']<=6


def test_invalid_model_evidence_does_not_promote_source_or_abort_other_sources(tmp_path):
    import io
    from PIL import Image
    from ref_lab.verified_collection import AgentEvidenceInvalid
    from ref_lab.automatic_references import ReferenceDiscovery
    stream=io.BytesIO();Image.new('RGB',(320,480),'blue').save(stream,'PNG');raw=stream.getvalue()
    class Agent:
        last_tool_calls=[]
        calls=0
        def run(self,prompt,result_type,*args,**kwargs):
            if result_type is ReferenceDiscovery:return result_type(urls=['https://example.org/a','https://example.org/b'],reason='Fixture')
            self.calls+=1
            if self.calls==1:raise AgentEvidenceInvalid('No valid structured result')
            return assessment(hashlib.sha256(raw).hexdigest())
    def fetch(url,limit):return (raw,'image/png',url) if url.endswith('.png') else (HTML.encode(),'text/html',url)
    research=ReferenceResearch(Agent(),tmp_path,PROJECT,PLAN,fetch=fetch);research.prepare()
    assert len(research.references)==1
    assert [p['status'] for p in research.pages]==['model_invalid','trusted']


def test_uncovered_outfit_gets_new_evidence_and_recheck_without_user_feedback(tmp_path,monkeypatch):
    from ref_lab.verified_collection import AntigravityCollectionAgent,CollectionVision,scope_sha,accepted
    agent=AntigravityCollectionAgent(tmp_path)
    old={'asset_sha':'c'*64};new={'asset_sha':'d'*64}
    agent.references=[old]
    class Research:
        references=[old]
        hints=[]
        def supplement(self,hint):self.hints.append(hint);self.references=[old,new];return True
    agent.research=Research()
    first=CollectionVision(asset_sha='a'*64,context_sha=scope_sha(PROJECT),kind='cosplay_photo',identity='uncertain',
        costume='not_required',confidence='low',photography_usable='yes',photography_evidence=['合成测试中姿态可辨'],kind_evidence=['Synthetic photo'],identity_evidence=['Unknown outfit'],costume_evidence=[],reason='Synthetic gap',observed_costume='Outfit B')
    final=CollectionVision.model_validate({**first.model_dump(),'identity':'match','confidence':'high','reference_comparisons':[
        {'reference_sha':'d'*64,'assessment':'supports','supporting_features':['Garment structure','Accessory detail'],'conflicting_features':[]}]})
    values=iter([first,final])
    def review(*args):agent.candidate_calls+=1;return next(values)
    monkeypatch.setattr(agent,'_review_once',review)
    actual=agent.review(tmp_path/'unused.png',PROJECT)
    assert agent.research.hints==['Outfit B'] and agent.candidate_calls==2
    assert accepted(actual,PROJECT,references=agent.references)
    trace=json.loads((tmp_path/('candidate-trace-'+'a'*64+'.json')).read_text('utf8'))
    assert trace['model_predictions'][0]['identity']=='uncertain' and trace['model_predictions'][1]['identity']=='match'
    assert not accepted(final,PROJECT,references=[])  # A model-positive label alone is insufficient.
