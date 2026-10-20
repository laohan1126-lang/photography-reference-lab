"""A sealed collector result can finish locally after its external budget expires."""
import hashlib
import json
from pathlib import Path

import pytest

from conftest import image_bytes
from ref_lab import agent_collection as runner
from ref_lab.imports import import_candidates
from ref_lab.models import CandidatePackage, JobInput
from tools import collect_verified as worker
from test_verified_collection import FakeAgent, FakeBrowser, row


def test_sealed_new_manifest_with_old_zip_finishes_without_new_executor(library, project, settings, tmp_path, monkeypatch):
    task=library.create_job(project['id'],JobInput(kind='collection',target_count=2))
    folder=tmp_path/'controller';folder.mkdir()
    class Agent(FakeAgent):model=settings.classification_model
    class Browser(FakeBrowser):
        gated=True
        def search(self,step):
            value=super().search(step)
            value['cards']=[{'page':'https://example.org/old' if self.gated else 'https://example.org/new'}]
            if self.gated and step['source']=='pinterest':value['login_required']=True
            return value
    monkeypatch.setattr(runner,'_collector_state_path',lambda _:folder/'collector-state.json')
    first=Agent();a,images_a=worker.collect(task,first,Browser([row(folder,'old.png',image_bytes(1))]),folder)
    result=settings.data_dir/'agent-runs'/task['id']/'result.zip'
    worker.write_result(result,a,images_a)
    old=result.read_bytes();old_sha=hashlib.sha256(old).hexdigest()
    coverage=runner._collector_coverage_snapshot(library,task,CandidatePackage.model_validate(a))
    imported=import_candidates(library,project['id'],old,task['id'],collector_coverage=coverage,result_sha256=old_sha)
    assert imported['job']['collection_outcome']=='partial'
    browser=Browser([row(folder,'new.png',image_bytes(60))]);browser.gated=False
    second=Agent();b,images_b=worker.collect(task,second,browser,folder)
    assert b['execution_report']['status']=='completed' and len(images_b)==2
    assert result.read_bytes()==old  # Crash after sealing B, before replacing ZIP A.
    with library.db.transaction() as con:
        saved=json.loads(con.execute('SELECT data FROM jobs WHERE id=?',(task['id'],)).fetchone()[0])
        saved.update(collection_elapsed_seconds=100,collection_timeout_seconds=1)
        con.execute('UPDATE jobs SET data=? WHERE id=?',(json.dumps(saved),task['id']))
    monkeypatch.setattr(runner,'run_process',lambda *a,**kw:pytest.fail('Only local export is allowed'))
    recovered=runner.run_collection_attempt(library,task['id'])
    assert recovered['status']=='succeeded' and recovered['collection_outcome']=='complete'
    assert len(recovered['last_receipt_reference_ids'])==2
    assert result.with_name('result-'+old_sha+'.zip').read_bytes()==old
    assert first.calls==second.calls==1
    assert recovered['last_imported_result_sha256']==hashlib.sha256(result.read_bytes()).hexdigest()
