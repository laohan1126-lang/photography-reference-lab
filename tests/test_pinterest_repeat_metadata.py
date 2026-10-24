"""Producer -> discovery merge regressions; no browser, network or model calls."""
import hashlib
import io

import pytest
from PIL import Image

from ref_lab.search_relevance import is_confirmed
from tools import collect_verified as worker


@pytest.mark.parametrize('reason',['known_source_url','same_bytes_known'])
@pytest.mark.parametrize('title,tier',[('西木野真姬 cos 摄影','target_named'),('其他角色的摄影','other_character')])
def test_pinterest_repeat_preserves_fetched_author_evidence(tmp_path,monkeypatch,reason,title,tier):
    stream=io.BytesIO();Image.new('RGB',(300,400),'green').save(stream,format='PNG');raw=stream.getvalue()
    sha=hashlib.sha256(raw).hexdigest();url='https://i.pinimg.com/received.png'
    browser=worker.Browser(tmp_path);browser.bsk='synthetic';browser.session='owned-session'
    browser.known_sources={worker.normalize_image_url(url):sha} if reason=='known_source_url' else {}
    browser.known_shas={sha}
    monkeypatch.setattr(worker,'fetch_pinterest_detail_metadata',lambda *a,**k:{
        'image_url':url,'title':title,'desc':'author description'})
    downloads=[]
    def download(*args):
        downloads.append(url)
        return raw,300,400,'PNG',False
    monkeypatch.setattr(browser,'_pinterest_bytes',download)
    monkeypatch.setattr(browser,'_go_back',lambda:None)
    monkeypatch.setattr(browser,'snapshot',lambda:{'url':'https://www.pinterest.com/search/pins/?q=query',
        'search':'query','cards':[{'page':'https://www.pinterest.com/pin/123/'}]})
    card={'page':'https://www.pinterest.com/pin/123/','text':'generic photography'}
    rows=browser.receive(card,{'source':'pinterest','query':'query'})
    assert rows[0]['reason']==reason
    assert rows[0]['author_detail']=={'title':title,'description':'author description'}
    assert len(downloads)==int(reason=='same_bytes_known')
    original={'asset_sha':sha,'relevance':{'tier':'unconfirmed'},'visual_receipt':{'identity':'unknown'}}
    by_sha={sha:original}
    assert worker._merge_repeat_evidence(by_sha,card,rows[0],names=['西木野真姬'],work_terms=(),other_terms=())
    trail=original['discovery_evidence_history']
    assert trail[-1]['tier']==tier and len(by_sha)==1
    assert is_confirmed(original)==(tier=='target_named')
    assert original['visual_receipt']=={'identity':'unknown'}


def test_arbitrary_source_text_is_not_author_name_evidence():
    original={'asset_sha':'a'*64,'relevance':{'tier':'unconfirmed'}}
    worker._merge_repeat_evidence({'a'*64:original},{'text':'generic'},
        {'asset_sha':'a'*64,'source_text':'西木野真姬 cos 摄影','author_detail':{'title':'generic'}},
        names=['西木野真姬'],work_terms=(),other_terms=())
    assert not is_confirmed(original)
    assert original['discovery_evidence_history'][-1]['detail']['evidence']=={'title':'generic'}
