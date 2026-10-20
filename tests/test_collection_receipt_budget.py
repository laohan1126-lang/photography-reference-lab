"""Receipt replay must remain possible after the final paid call has finished."""
import json

import pytest

from ref_lab import verified_collection as vision
from test_collection_resume import fake_processes, terminal
from test_verified_collection import PROJECT, result


def photo_receipt(tmp_path, monkeypatch):
    path = tmp_path / 'photo.png'
    path.write_bytes(b'synthetic-original')
    value = result(path)
    opened = {'step_update': {'tool_name': 'view_file', 'state': 'DONE',
              'tool_info': {'parameters': {'AbsolutePath': str(path.resolve())}}}}
    calls = fake_processes(monkeypatch, [(0, json.dumps(opened) + '\n' + terminal('SUCCESS', value.model_dump()), '')])
    agent = vision.AntigravityCollectionAgent(tmp_path, model='synthetic-only')
    agent.candidate_limit = agent.vision_cli_limit = 1
    assert agent._review_once(path, PROJECT, references=[]) == value
    return path, value, calls


def test_last_call_receipt_can_be_recovered_without_charging_again(tmp_path, monkeypatch):
    path, value, calls = photo_receipt(tmp_path, monkeypatch)
    recovered = vision.AntigravityCollectionAgent(tmp_path, model='synthetic-only')
    recovered.candidate_limit = recovered.vision_cli_limit = 1
    for _ in range(2):
        assert recovered._review_once(path, PROJECT, references=[]) == value
        assert recovered.candidate_calls == recovered.vision_cli_calls == 1
    assert len(calls) == 1

    with pytest.raises(vision.AgentUnavailable):
        recovered._review_once(path, {**PROJECT, 'notes': 'changed conditions'}, references=[])
    assert len(calls) == 1


def test_original_attempt_format_without_binding_is_read_only_compatible(tmp_path, monkeypatch):
    path, value, calls = photo_receipt(tmp_path, monkeypatch)
    attempt=next(tmp_path.glob('attempt-*.json'))
    saved=json.loads(attempt.read_text('utf8'));saved.pop('binding')
    attempt.write_text(json.dumps(saved),encoding='utf8')
    recovered=vision.AntigravityCollectionAgent(tmp_path,model='synthetic-only')
    recovered.candidate_limit=recovered.vision_cli_limit=1
    assert recovered._review_once(path,PROJECT,references=[])==value
    assert len(calls)==1
    saved['producer']='another model'
    attempt.write_text(json.dumps(saved),encoding='utf8')
    with pytest.raises(vision.AgentUnavailable):recovered._review_once(path,PROJECT,references=[])


@pytest.mark.parametrize('damage', ['missing', 'failed', 'changed_result'])
def test_cached_receipt_needs_its_successful_attempt_evidence(tmp_path, monkeypatch, damage):
    path, _, calls = photo_receipt(tmp_path, monkeypatch)
    attempt = next(tmp_path.glob('attempt-*.json'))
    if damage == 'missing':
        attempt.unlink()
    else:
        saved = json.loads(attempt.read_text('utf8'))
        if damage == 'failed':
            saved['result']['status'] = 'ERROR'
        else:
            saved['result']['structured_output']['reason'] = 'Changed terminal prediction'
        attempt.write_text(json.dumps(saved), encoding='utf8')
    recovered = vision.AntigravityCollectionAgent(tmp_path, model='synthetic-only')
    with pytest.raises(vision.AgentUnavailable):
        recovered._review_once(path, PROJECT, references=[])
    assert len(calls) == 1
