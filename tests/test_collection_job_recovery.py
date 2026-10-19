"""Synthetic recovery and ownership checks; never invokes a real Agent or search."""
from __future__ import annotations

import json
import hashlib
import os
from pathlib import Path
import shutil
import subprocess
import sys
import time
import types
import zipfile
import io

import pytest

from ref_lab.agent_collection import collection_can_resume, run_collection_attempt
from ref_lab.config import Settings
from ref_lab.models import JobInput, ProjectInput, ReferenceEdit
from ref_lab.service import Library, Problem
from test_personal_library import candidate_zip

ROOT = Path(__file__).resolve().parents[1]


def attempt_receipt(library, job_id):
    with library.db.read() as con:
        rows = con.execute(
            "SELECT data FROM events WHERE entity_id=? AND action='collection.attempt_finished' ORDER BY id",
            (job_id,)).fetchall()
    return json.loads(rows[-1][0])


def new_job(library, *, target=1, sources=None):
    project = library.create_project(ProjectInput(character="Synthetic recovery"))
    job = library.create_job(project["id"], JobInput(
        kind="collection", target_count=target,
        preferred_sources=sources or ["xiaohongshu", "pinterest"]))
    return project, job


def complete_report():
    return {
        "producer": "synthetic-recovery-fixture",
        "status": "completed",
        "summary": "Synthetic fixture only",
        "source_checks": [{"source": "pinterest", "status": "usable"}],
        "query_log": [{"source": "pinterest", "query": "synthetic fixture", "kept": 1}],
        "gaps": [],
    }


def write_collector_state(job, package, settings, monkeypatch, tmp_path, *, steps=None, bad=None,
                          outcome="complete"):
    with zipfile.ZipFile(io.BytesIO(package)) as archive:
        manifest = json.loads(archive.read("manifest.json"))
    if steps is None:
        steps = [{"source": item["source"], "query": item["query"], "language": "en",
                  "alias_origin": "synthetic-fixture"}
                 for item in manifest["execution_report"]["query_log"]]

    def job_binding(value, model):
        return {"job_id": value["id"], "project": value["project_snapshot"],
                "notes": value.get("notes", ""), "target_count": value.get("target_count", 12),
                "preferred_sources": value.get("preferred_sources"), "model": model,
                "rules": "synthetic-frozen-rules"}

    module = types.ModuleType("ref_lab.collection_checkpoint")
    module.job_binding = job_binding
    monkeypatch.setitem(sys.modules, "ref_lab.collection_checkpoint", module)

    binding = job_binding(job, settings.classification_model)
    if bad == "binding":
        binding = {**binding, "project": {**binding["project"], "character": "Other job"}}
    if bad == "manifest":
        manifest = {**manifest, "batch_id": "different-final-manifest"}
    state = {"version": 1, "binding": binding, "batch_id": manifest["batch_id"],
             "plan": {"names": ["synthetic"], "costume_names": []}, "steps": steps,
             "queries": manifest["execution_report"]["query_log"],
             "checks": {item["source"]: item for item in manifest["execution_report"]["source_checks"]},
             "received": [], "audit": [], "pages": [], "page_attempts": {},
             "duplicates": [], "collisions": [], "gaps": manifest["execution_report"]["gaps"],
             "details": 0, "windows": len(steps), "first_usable": 1.0, "phase": "finished",
             "searches": {str(i): {**step, "observed": True, "usable": True,
                                    "window": 1, "done": True}
                          for i, step in enumerate(steps)},
             "final_manifest": manifest, "outcome": outcome, "terminal": outcome == "complete"}
    state_path = tmp_path / "collector-state.json"
    state_path.write_text(json.dumps(state, ensure_ascii=False), encoding="utf-8")
    monkeypatch.setattr("ref_lab.agent_collection._collector_state_path",
                        lambda job_id: state_path, raising=False)


def bound_collector_package(job, settings, monkeypatch, tmp_path, *, bad=None):
    languages = ("zh", "en", "ja")
    steps = [{"source": "pinterest", "query": f"synthetic-{language}",
              "language": language, "alias_origin": "synthetic-fixture"}
             for language in languages]
    report = {"producer": "synthetic-recovery-fixture", "status": "completed",
              "summary": "bound collector-state fixture",
              "source_checks": [{"source": "pinterest", "status": "usable"}],
              "query_log": [{"source": step["source"], "query": step["query"], "kept": 1}
                            for step in steps],
              "gaps": ["自动停止原因：soft_target_reached"]}
    package = candidate_zip(job, execution_report=report)
    write_collector_state(job, package, settings, monkeypatch, tmp_path, steps=steps, bad=bad)
    return package


def configure(monkeypatch, tmp_path, script, *args):
    command = [sys.executable, str(script), "{task_file}", "{result_file}", *map(str, args)]
    monkeypatch.setenv("LAB_COLLECTION_COMMAND", json.dumps(command))
    monkeypatch.setenv("LAB_COLLECTION_TIMEOUT_SECONDS", "5")


def test_exhausted_partial_budget_replays_existing_zip_without_executor(library, settings, tmp_path, monkeypatch):
    _,job=new_job(library)
    folder=settings.data_dir/'agent-runs'/job['id'];folder.mkdir(parents=True)
    package=candidate_zip(job);(folder/'result.zip').write_bytes(package)
    monkeypatch.setattr('ref_lab.agent_collection.run_process',lambda *a,**kw:pytest.fail('Budget must not start executor'))
    first=run_collection_attempt(library,job['id'])
    assert first['collection_outcome']=='partial' and first['last_receipt_reference_ids']
    with library.db.transaction() as con:
        saved=json.loads(con.execute('SELECT data FROM jobs WHERE id=?',(job['id'],)).fetchone()[0])
        saved.update(collection_elapsed_seconds=100,collection_timeout_seconds=1)
        con.execute('UPDATE jobs SET data=? WHERE id=?',(json.dumps(saved),job['id']))
    again=run_collection_attempt(library,job['id'])
    assert again['collection_outcome']=='partial'
    assert again['last_receipt_reference_ids']==first['last_receipt_reference_ids']
    assert again['last_imported_result_sha256']==hashlib.sha256(package).hexdigest()


def test_retries_keep_task_and_result_paths_and_reuse_completed_zip(library, settings, monkeypatch, tmp_path):
    _, job = new_job(library, target=1, sources=["pinterest"])
    package = tmp_path / "complete.zip"
    package.write_bytes(candidate_zip(job, execution_report=complete_report()))
    calls = tmp_path / "calls.jsonl"
    script = tmp_path / "adapter.py"
    script.write_text("""import json, pathlib, shutil, sys
calls = pathlib.Path(sys.argv[3])
with calls.open('a', encoding='utf8') as stream:
    stream.write(json.dumps({'cwd':str(pathlib.Path.cwd()),'task':sys.argv[1],'result':sys.argv[2]})+'\\n')
if len(calls.read_text(encoding='utf8').splitlines()) == 1:
    raise SystemExit(17)
shutil.copyfile(sys.argv[4], sys.argv[2])
""", encoding="utf-8")
    configure(monkeypatch, tmp_path, script, calls, package)

    first = run_collection_attempt(library, job["id"])
    with zipfile.ZipFile(io.BytesIO(package.read_bytes())) as archive:
        manifest = json.loads(archive.read("manifest.json"))
    state_steps = [{"source": item["source"], "query": item["query"], "language": "en",
                    "alias_origin": "synthetic-fixture"}
                   for item in manifest["execution_report"]["query_log"]]
    write_collector_state(job, package.read_bytes(), settings, monkeypatch, tmp_path, steps=state_steps)
    second = run_collection_attempt(library, job["id"])
    third = run_collection_attempt(library, job["id"])

    recorded = [json.loads(line) for line in calls.read_text(encoding="utf-8").splitlines()]
    assert first["status"] == "failed"
    assert second["status"] == third["status"] == "succeeded"
    assert len(recorded) == 2
    assert recorded[0] == recorded[1]
    assert Path(recorded[0]["task"]).is_file()
    assert Path(recorded[0]["result"]).is_file()
    assert Path(recorded[0]["cwd"]).is_dir()
    assert len(second["imported_ids"]) == 1


def test_hard_service_exit_keeps_owner_until_result_is_ready_then_resumes_same_job(library, settings, tmp_path, monkeypatch):
    project, job = new_job(library)
    package = tmp_path / "partial.zip"
    package.write_bytes(candidate_zip(job))
    started, allow, finished, calls = (tmp_path / name for name in ("started", "allow", "finished", "calls"))
    adapter_script = tmp_path / "paused_adapter.py"
    adapter_script.write_text("""import json, os, pathlib, shutil, sys, time
result, package, started, allow, finished, calls = map(pathlib.Path, sys.argv[2:])
started.write_text('started')
with calls.open('a', encoding='utf8') as stream:
    stream.write(json.dumps({'task':sys.argv[1], 'result':sys.argv[2],
        'mode':os.environ.get('LAB_COLLECTION_RECOVERY_MODE'),
        'sha':os.environ.get('LAB_COLLECTION_IMPORTED_RESULT_SHA256')})+'\\n')
deadline = time.monotonic() + 15
while not allow.exists() and time.monotonic() < deadline: time.sleep(.02)
shutil.copyfile(package, result)
finished.write_text('finished')
""", encoding="utf-8")
    command = [sys.executable, str(adapter_script), "{task_file}", "{result_file}",
               str(package), str(started), str(allow), str(finished), str(calls)]
    env = dict(os.environ)
    env["LAB_DATA_DIR"] = str(settings.data_dir)
    env["LAB_COLLECTION_COMMAND"] = json.dumps(command)
    env["LAB_COLLECTION_TIMEOUT_SECONDS"] = "10"
    monkeypatch.setenv("LAB_COLLECTION_COMMAND", env["LAB_COLLECTION_COMMAND"])
    monkeypatch.setenv("LAB_COLLECTION_TIMEOUT_SECONDS", env["LAB_COLLECTION_TIMEOUT_SECONDS"])
    token = settings.token
    code = "\n".join([
        f"import os, sys, threading, time",
        f"sys.path.insert(0, {str(ROOT)!r})",
        "from pathlib import Path",
        "from ref_lab.agent_collection import run_collection_attempt",
        "from ref_lab.config import Settings",
        "from ref_lab.service import Library",
        f"lib=Library(Settings(Path({str(settings.data_dir)!r}), {token!r}, auto_classify=False))",
        f"job_id={job['id']!r}",
        f"started=Path({str(started)!r})",
        "def crash():",
        "    deadline=time.monotonic()+8",
        "    while not started.exists() and time.monotonic()<deadline: time.sleep(.01)",
        "    os._exit(86 if started.exists() else 87)",
        "threading.Thread(target=crash, daemon=True).start()",
        "run_collection_attempt(lib, job_id)",
        "os._exit(88)",
    ])
    child = subprocess.Popen([sys.executable, "-X", "utf8", "-c", code], cwd=ROOT,
                             env=env, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    try:
        deadline = time.monotonic() + 10
        while not started.exists() and time.monotonic() < deadline: time.sleep(.02)
        assert started.exists(), "synthetic adapter did not start"
        assert child.wait(timeout=10) == 86
        first = Library(Settings(settings.data_dir, token, auto_classify=False)).job(job["id"])
        attempt_id = first.get("active_attempt_id")
        assert first["status"] == "running" and attempt_id
        with pytest.raises(Problem):
            run_collection_attempt(library, job["id"])
        assert Library(Settings(settings.data_dir, token, auto_classify=False)).job(job["id"])["active_attempt_id"] == attempt_id

        allow.write_text("continue")
        deadline = time.monotonic() + 10
        while not finished.exists() and time.monotonic() < deadline: time.sleep(.02)
        assert finished.exists(), "surviving synthetic adapter did not finish its ZIP"
        deadline = time.monotonic() + 5
        while not collection_can_resume(library, library.job(job["id"])) and time.monotonic() < deadline:
            time.sleep(.02)
        assert collection_can_resume(library, library.job(job["id"]))
        resumed = run_collection_attempt(library, job["id"])
        assert resumed["status"] == "blocked"
        assert resumed.get("collection_outcome") == "partial"
        assert len(resumed["imported_ids"]) == 1
        assert resumed.get("active_attempt_id") is None
        finishes = []
        with library.db.read() as con:
            rows = con.execute("SELECT data FROM events WHERE entity_id=? AND action='collection.attempt_finished'", (job["id"],)).fetchall()
            finishes = [json.loads(row[0]) for row in rows]
        assert finishes[-1]["attempt_id"] == attempt_id

        again = run_collection_attempt(library, job["id"])
        assert again["imported_ids"] == resumed["imported_ids"]
        call_records = [json.loads(line) for line in calls.read_text(encoding="utf-8").splitlines()]
        assert len(call_records) == 2
        assert call_records[0]["mode"] is None and call_records[0]["sha"] is None
        assert call_records[1]["mode"] == "continue_imported_partial"
        assert call_records[1]["sha"] == hashlib.sha256(package.read_bytes()).hexdigest()
        assert call_records[0]["task"] == call_records[1]["task"]
        assert call_records[0]["result"] == call_records[1]["result"]
    finally:
        if child.poll() is None:
            child.kill()
            child.wait(timeout=5)
        if started.exists() and not allow.exists():
            allow.write_text("stop")


def _zip_with_mismatch_preflight(job):
    report = {"producer": "synthetic-recovery-fixture", "status": "blocked", "summary": "partial fixture",
              "source_checks": [], "query_log": [], "gaps": ["synthetic interruption"]}
    with zipfile.ZipFile(io.BytesIO(candidate_zip(job, execution_report=report))) as archive:
        entries = {name: archive.read(name) for name in archive.namelist()}
    manifest = json.loads(entries["manifest.json"])
    manifest["candidates"][0]["preflight"]["identity_prediction"] = "mismatch"
    entries["manifest.json"] = json.dumps(manifest).encode("utf-8")
    output = io.BytesIO()
    with zipfile.ZipFile(output, "w") as archive:
        for name, content in entries.items():
            archive.writestr(name, content)
    return output.getvalue()


def test_replay_override(library, settings, tmp_path):
    project, job = new_job(library, target=20)
    package = tmp_path / "checkpoint.zip"
    package.write_bytes(_zip_with_mismatch_preflight(job))
    calls = tmp_path / "calls.txt"
    script = tmp_path / "adapter.py"
    script.write_text("""import pathlib, shutil, sys
with pathlib.Path(sys.argv[3]).open('a') as stream: stream.write('called\\n')
shutil.copyfile(sys.argv[4], sys.argv[2])
""", encoding="utf-8")
    command = [sys.executable, str(script), "{task_file}", "{result_file}", str(calls), str(package)]
    env = dict(os.environ)
    env["LAB_COLLECTION_COMMAND"] = json.dumps(command)
    env["LAB_COLLECTION_TIMEOUT_SECONDS"] = "5"
    token = settings.token
    child_code = "\n".join([
        f"import os, sys",
        f"sys.path.insert(0, {str(ROOT)!r})",
        "from pathlib import Path",
        "from ref_lab.agent_collection import run_collection_attempt",
        "from ref_lab.config import Settings",
        "from ref_lab.service import Library",
        f"lib=Library(Settings(Path({str(settings.data_dir)!r}), {token!r}, auto_classify=False))",
        f"job_id={job['id']!r}",
        "original=lib.apply_candidate_preflight",
        "def exit_after_preflight(*args, **kwargs):",
        "    original(*args, **kwargs)",
        "    os._exit(91)",
        "lib.apply_candidate_preflight=exit_after_preflight",
        "run_collection_attempt(lib, job_id)",
        "os._exit(92)",
    ])
    child = subprocess.Popen([sys.executable, "-X", "utf8", "-c", child_code], cwd=ROOT,
                             env=env, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    try:
        exit_code = child.wait(timeout=15)
    finally:
        if child.poll() is None:
            child.kill()
            child.wait(timeout=5)
    assert exit_code == 91

    interrupted = library.job(job["id"])
    assert interrupted["status"] == "running" and len(interrupted["imported_ids"]) == 1
    ident = interrupted["imported_ids"][0]
    ref = library.reference(ident)
    assert ref["preflight_filtered"] is True
    ref = library.override_candidate_preflight(ident, ref["revision"])
    library.edit_reference(ident, ReferenceEdit(expected_revision=ref["revision"], decision="reject"))

    resumed = run_collection_attempt(library, job["id"])
    ref = library.reference(ident)
    assert resumed["status"] == "blocked" and resumed["collection_outcome"] == "partial"
    assert resumed["imported_ids"] == [ident]
    assert ref["decision"] == "reject"
    assert ref["preflight_override"] is True and ref["preflight_filtered"] is False
    assert ref["preflight"]["identity_prediction"] == "mismatch"
    assert len(calls.read_text(encoding="utf-8").splitlines()) == 1


def test_cancel_after_candidate_insert_rejects_late_preflight(library, monkeypatch):
    project, job = new_job(library)
    job = library.start_collection_attempt(job["id"], job["revision"], "owned-attempt")
    add_candidate = library.add_candidate

    def cancel_after_insert(*args, **kwargs):
        result = add_candidate(*args, **kwargs)
        latest = library.job(job["id"])
        library.transition_job(job["id"], "cancelled", latest["revision"], "synthetic cancel during import")
        return result

    monkeypatch.setattr(library, "add_candidate", cancel_after_insert)
    with pytest.raises(Problem):
        from ref_lab.imports import import_candidates
        import_candidates(library, project["id"], candidate_zip(job), job["id"], attempt_id="owned-attempt")

    saved = library.job(job["id"])
    ref = library.reference(saved["imported_ids"][0])
    assert saved["status"] == "cancelled"
    assert ref["decision"] == "pending"
    assert ref["preflight"] is None


def test_unimported_zip_is_imported_without_executor_then_same_receipt_resumes_with_signal(
        library, settings, monkeypatch, tmp_path):
    _, job = new_job(library, target=1, sources=["pinterest"])
    report = {"producer": "synthetic-recovery-fixture", "status": "blocked",
              "summary": "partial checkpoint", "source_checks": [], "query_log": [],
              "gaps": ["synthetic interruption"]}
    package = candidate_zip(job, execution_report=report)
    run_dir = settings.data_dir / "agent-runs" / job["id"]
    run_dir.mkdir(parents=True)
    result_file = run_dir / "result.zip"
    result_file.write_bytes(package)
    calls = tmp_path / "adapter-calls.jsonl"
    source_package = tmp_path / "next.zip"
    source_package.write_bytes(package)
    script = tmp_path / "resume-adapter.py"
    script.write_text("""import json, os, pathlib, shutil, sys
with pathlib.Path(sys.argv[3]).open('a', encoding='utf8') as stream:
    stream.write(json.dumps({'task':sys.argv[1], 'result':sys.argv[2],
        'mode':os.environ.get('LAB_COLLECTION_RECOVERY_MODE'),
        'sha':os.environ.get('LAB_COLLECTION_IMPORTED_RESULT_SHA256')})+'\\n')
shutil.copyfile(sys.argv[4], sys.argv[2])
""", encoding="utf-8")
    configure(monkeypatch, tmp_path, script, calls, source_package)

    imported = run_collection_attempt(library, job["id"])

    assert imported["status"] == "blocked"
    assert imported["last_imported_result_sha256"] == hashlib.sha256(package).hexdigest()
    assert not calls.exists(), "an unimported crash ZIP must be imported without starting the executor"

    resumed = run_collection_attempt(library, job["id"])

    recorded = json.loads(calls.read_text(encoding="utf-8").splitlines()[0])
    artifacts = resumed["collection_artifacts"]
    assert recorded["mode"] == "continue_imported_partial"
    assert recorded["sha"] == hashlib.sha256(package).hexdigest()
    assert recorded["task"] == artifacts["task_file"]
    assert recorded["result"] == artifacts["result_file"]
    assert resumed["collection_outcome"] == "partial"


def test_bound_collector_state_validates_languages_and_soft_stop_before_complete_import(
        library, settings, monkeypatch, tmp_path):
    _, job = new_job(library, target=1, sources=["pinterest"])
    package = bound_collector_package(job, settings, monkeypatch, tmp_path)
    run_dir = settings.data_dir / "agent-runs" / job["id"]
    run_dir.mkdir(parents=True)
    (run_dir / "result.zip").write_bytes(package)

    def forbidden(*args, **kwargs):
        raise AssertionError("a valid unimported ZIP must be imported without starting the executor")
    monkeypatch.setattr("ref_lab.agent_collection.subprocess.Popen", forbidden)

    saved = run_collection_attempt(library, job["id"])

    assert saved["status"] == "succeeded"
    assert saved["collection_outcome"] == "complete"
    assert saved["collection_coverage"]["required_languages"] == ["en", "ja", "zh"]
    assert saved["last_imported_result_sha256"] == hashlib.sha256(package).hexdigest()


def test_bound_blocked_collector_state_preserves_blocked_outcome_with_imported_candidate(
        library, settings, monkeypatch, tmp_path):
    _, job = new_job(library, target=1, sources=["pinterest"])
    steps = [{"source": "pinterest", "query": f"synthetic-{language}",
              "language": language, "alias_origin": "synthetic-fixture"}
             for language in ("zh", "en", "ja")]
    report = {"producer": "synthetic-recovery-fixture", "status": "blocked",
              "summary": "执行受阻", "source_checks": [{"source": "pinterest", "status": "usable"}],
              "query_log": [{"source": "pinterest", "query": steps[0]["query"], "kept": 1}],
              "gaps": ["不可恢复AgentCallFailed"]}
    package = candidate_zip(job, execution_report=report)
    write_collector_state(job, package, settings, monkeypatch, tmp_path,
                          steps=steps, outcome="blocked")
    run_dir = settings.data_dir / "agent-runs" / job["id"]
    run_dir.mkdir(parents=True)
    (run_dir / "result.zip").write_bytes(package)
    monkeypatch.setattr("ref_lab.agent_collection.subprocess.Popen",
                        lambda *args, **kwargs: (_ for _ in ()).throw(
                            AssertionError("a valid unimported ZIP must be imported without executor")))

    saved = run_collection_attempt(library, job["id"])

    assert saved["status"] == "blocked"
    assert saved["collection_outcome"] == "blocked"
    assert saved["collection_coverage"]["collector_outcome"] == "blocked"
    assert len(saved["last_receipt_reference_ids"]) == 1


@pytest.mark.parametrize("bad", ["binding", "manifest"])
def test_unbound_collector_state_rejects_zip_before_any_candidate_import(
        library, settings, monkeypatch, tmp_path, bad):
    _, job = new_job(library, target=1, sources=["pinterest"])
    package = bound_collector_package(job, settings, monkeypatch, tmp_path, bad=bad)
    run_dir = settings.data_dir / "agent-runs" / job["id"]
    run_dir.mkdir(parents=True)
    (run_dir / "result.zip").write_bytes(package)

    def forbidden(*args, **kwargs):
        raise AssertionError("a bound checkpoint failure must not start another executor")
    monkeypatch.setattr("ref_lab.agent_collection.subprocess.Popen", forbidden)

    saved = run_collection_attempt(library, job["id"])

    assert saved["status"] == "blocked"
    assert saved["imported_ids"] == []
    assert saved.get("last_imported_result_sha256") is None
    assert attempt_receipt(library, job["id"])["code"] == "collector_state_invalid"
