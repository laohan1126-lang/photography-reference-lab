import urllib.request
import json
import pytest

from ref_lab.providers import antigravity_environment
from ref_lab.verified_collection import parse_agent_stream, NamePlan, AgentUnavailable


def test_current_windows_proxy_is_child_only(monkeypatch):
    monkeypatch.setattr(urllib.request, 'getproxies_registry', lambda: {
        'http': 'http://127.0.0.1:12345', 'https': 'http://127.0.0.1:12345', 'no': 'localhost,127.0.0.1'
    }, raising=False)
    original={'LAB_DATA_DIR': 'private'}
    result=antigravity_environment(original)
    assert result['HTTPS_PROXY']=='http://127.0.0.1:12345'
    assert result['HTTP_PROXY']==result['HTTPS_PROXY']
    assert result['NO_PROXY']=='localhost,127.0.0.1'
    assert original=={'LAB_DATA_DIR': 'private'}


def test_explicit_environment_and_no_proxy_preserved(monkeypatch):
    def unexpected():
        raise AssertionError('explicit proxy must take priority')
    monkeypatch.setattr(urllib.request, 'getproxies_registry', unexpected, raising=False)
    for name in ('HTTP_PROXY','HTTPS_PROXY','http_proxy','https_proxy','ALL_PROXY','all_proxy'):
        env={name:'http://chosen:9876','NO_PROXY':'localhost'}
        assert antigravity_environment(env)==env


def test_disabled_or_unavailable_system_proxy_does_not_guess(monkeypatch):
    monkeypatch.setattr(urllib.request, 'getproxies_registry', lambda: {}, raising=False)
    assert antigravity_environment({'NO_PROXY':'custom'})=={'NO_PROXY':'custom'}
    monkeypatch.delattr(urllib.request, 'getproxies_registry')
    assert antigravity_environment({})=={}


def test_system_proxy_keeps_explicit_bypass(monkeypatch):
    monkeypatch.setattr(urllib.request, 'getproxies_registry', lambda: {
        'https':'http://proxy:4321','no':'system-bypass'
    }, raising=False)
    assert antigravity_environment({'NO_PROXY':'my-bypass'})=={
        'HTTPS_PROXY':'http://proxy:4321','NO_PROXY':'my-bypass'
    }


def test_structured_agent_result_is_used_instead_of_concatenated_text():
    data={'names':['Example Person'],'costume_names':[],'uncertainty':''}
    event={'event':'result','result':{'status':'SUCCESS',
        'response':json.dumps(data)+json.dumps({**data,'toolAction':'metadata'}),
        'structured_output':data}}
    assert parse_agent_stream(json.dumps(event),NamePlan).names==['Example Person']
    event['result']['structured_output']={'names':[]}
    with pytest.raises(AgentUnavailable):parse_agent_stream(json.dumps(event),NamePlan)
    event['result']['structured_output']=data
    event['result']['denied_actions']=[{'action':'read_file'}]
    with pytest.raises(AgentUnavailable):parse_agent_stream(json.dumps(event),NamePlan)
