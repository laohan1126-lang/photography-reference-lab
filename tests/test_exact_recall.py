import hashlib
from pathlib import Path
from tools import exact_recall as r


SCOPE={'character':'公孙离','costume':'祈雪灵祝'}
QUERY='公孙离 祈雪灵祝'
URL='https://www.pinterest.com/search/pins/?q=%E5%85%AC%E5%AD%99%E7%A6%BB%20%E7%A5%88%E9%9B%AA%E7%81%B5%E7%A5%9D'


def test_correct_query_does_not_make_broad_results_relevant():
    snapshot={'url':URL,'search':QUERY,'cards':[{'text':'SkyeShi'},{'text':'liu shen'},{'text':'Save=Follow'}]}
    state=r.assess_search(snapshot,QUERY,SCOPE)
    assert state['action']=='SAMPLE_THEN_CHANGE_SOURCE'
    assert state['confirmed_count']==0
    assert r.after_visual_sample(['MISMATCH']*3)=='CHANGE_QUERY_OR_SOURCE'


def test_metadata_hit_routes_to_detail_never_confirmation():
    s={'url':URL,'search':QUERY,'cards':[{'text':'公孙离 祈雪灵祝 cos'}]}
    assert r.assess_search(s,QUERY,SCOPE)['action']=='INSPECT_TARGET_DETAILS'
    assert r.assess_search(s,QUERY,SCOPE)['confirmed_count']==0
    assert r.after_visual_sample(['NEEDS_EVIDENCE'])=='CHANGE_QUERY_OR_SOURCE'


def test_old_search_page_and_login_do_not_supply_candidates():
    assert r.assess_search({'url':URL,'search':'previous query'},QUERY,SCOPE)['action']=='STOP_STALE_QUERY'
    assert r.assess_search({'url':URL,'search':QUERY,'login_required':True},QUERY,SCOPE)['action']=='STOP_LOGIN_REQUIRED'


def fixture(tmp_path):
    f=tmp_path/'photo.jpg';f.write_bytes(b'immutable test bytes')
    sha=hashlib.sha256(f.read_bytes()).hexdigest()
    row={'asset_sha':sha,'original_path':str(f),'page_url':'https://www.xiaohongshu.com/explore/'+'a'*24}
    review={'asset_sha':sha,'opened_sha':sha,'context_sha':r.digest(SCOPE),'actor':'ai','producer':'synthetic',
            'kind':'cosplay_photo','identity':'match','costume':'match','evidence':{k:['test'] for k in ['kind','identity','costume']},
            'reference_use':'持伞','visible_evidence':'test','shooting_note':'test'}
    return row,review


def test_wrong_and_unknown_never_reach_owner_result(tmp_path):
    row,v=fixture(tmp_path)
    for key,val in [('identity','mismatch'),('identity','uncertain'),('costume','mismatch'),('kind','collage')]:
        assert r.confirmed_results([row],[{**v,key:val}],SCOPE)==[]
    assert r.confirmed_results([row],[{**v,'opened_sha':'wrong'}],SCOPE)==[]
    assert r.confirmed_results([row],[{**v,'context_sha':'stale'}],SCOPE)==[]
    assert r.confirmed_results([row],[{**v,'actor':'human'}],SCOPE)==[]
    assert len(r.confirmed_results([row],[v,v],SCOPE))==1


def test_empty_result_honest_no_rating_demand(tmp_path):
    r.render(tmp_path,[],[],SCOPE)
    page=(tmp_path/'public/index.html').read_text('utf8')
    assert '0 张' in page and '无需评价' in page
    assert '<input' not in page and '<form' not in page and '<script' not in page


def test_source_urls_are_escaped_in_static_result(tmp_path):
    row,v=fixture(tmp_path);v['reference_use']='<script>bad</script>'
    r.render(tmp_path,[row],[v],SCOPE)
    page=(tmp_path/'public/index.html').read_text('utf8')
    assert '<script>bad</script>' not in page
    assert '&lt;script&gt;' in page


def test_nonweb_source_link_is_refused(tmp_path):
    import pytest
    row,v=fixture(tmp_path);row['page_url']='javascript:alert(1)'
    with pytest.raises(ValueError,match='Unsafe source URL'):
        r.render(tmp_path,[row],[v],SCOPE)


def test_visible_platform_rewrite_is_not_exact_query_success():
    q='Arli cosplay'
    snapshot={'url':'https://www.pinterest.com/search/pins/?q=Arli%20cosplay','search':q,
              'visibleMain':'這是我們針對 ali cosplay 找到的內容。要改為搜尋 Arli cosplay？',
              'cards':[{'text':'公孙离 祈雪灵祝'}]}
    outcome=r.assess_search(snapshot,q,SCOPE)
    assert outcome['action']=='REVIEW_QUERY_REWRITE'
    assert outcome['effective_query']=='ali cosplay'
    assert outcome['confirmed_count']==0


def test_no_results_page_is_not_a_pool_of_suggestion_images():
    snapshot={'url':URL,'search':QUERY,'visibleMain':'抱歉！找不到與這個搜尋條件相符的 Pin。',
              'cards':[{'text':'窗帘'},{'text':'书房'}]}
    outcome=r.assess_search(snapshot,QUERY,SCOPE)
    assert outcome['result_state']=='EXPLICIT_NO_RESULTS'
    assert outcome['confirmed_count']==0
