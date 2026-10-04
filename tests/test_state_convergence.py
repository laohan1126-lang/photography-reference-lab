"""Snapshot and projection regressions; synthetic pixels, isolated test library."""
from pathlib import Path
import json
import pytest
from conftest import add_reference, ready_reference, card_data, image_bytes
from ref_lab.archiver import sync_project_confirmed_archive
from ref_lab.models import CandidatePreflight, IdentityContextInput, ProjectInput, ReferenceEdit


def test_project_identity_change_expires_predictions_and_relative_review(client, app, project):
    lib=app.state.library
    selected=ready_reference(client, project)
    candidate=add_reference(client, project, seed=44)
    prediction=CandidatePreflight(content_type="real_person_cosplay",identity_prediction="mismatch",confidence="high",visual_evidence=["Synthetic prediction for old target"],reason="Old target mismatch")
    candidate=lib.apply_candidate_preflight(candidate["id"],prediction,candidate["revision"],"synthetic_agent")
    old_context=lib.identity_context(project["id"])
    changed=lib.edit_project(project["id"],ProjectInput(character="新角色",work="新作品",costume="新版本",brief="新要求",gear=project["gear"]),project["revision"])
    current=lib.identity_context(project["id"])
    assert current["canonical_name"]=="新角色"
    assert current["id"]!=old_context["id"]
    candidate=lib.reference(candidate["id"])
    assert not candidate["preflight_filtered"]
    assert candidate["preflight_status"]=="unreviewed"
    assert candidate["preflight_history"][-1]["preflight"]["identity_prediction"]=="mismatch"
    selected=lib.reference(selected["id"])
    assert selected["decision"]=="keep"
    assert selected["review"]["character_match"]=="exact"
    assert "stale_identity_context" in {x["code"] for x in selected["blockers"]}
    assert selected["recommendation"]["evidence"]["visual_observations"]["items"]==[]
    assert selected["recommendation"]["identity_status"]=="身份未核验"
    saved=client.post(f"/api/references/{selected['id']}/card",json={"expected_revision":selected["revision"],"card":card_data()})
    assert saved.status_code==200
    assert client.post(f"/api/references/{selected['id']}/accept",json={"expected_revision":saved.json()["revision"]}).status_code==409
    assert lib.scan_project_preflight(changed["id"])["scanned"]==2


def test_archive_aggregates_same_character_and_never_confuses_same_title(client, app):
    lib=app.state.library
    projects=[lib.create_project(ProjectInput(character="共享角色",costume=str(i))) for i in range(2)]
    refs=[add_reference(client,p,seed=60+i,title="同名参考") for i,p in enumerate(projects)]
    kept=[lib.edit_reference(r["id"],ReferenceEdit(expected_revision=r["revision"],decision="keep")) for r in refs]
    report=sync_project_confirmed_archive(lib,projects[1]["id"])
    assert report["count"]==2
    assert set(report["mapping"])=={r["id"] for r in kept}
    paths=[Path(lib.reference(r["id"])["archive_path"]) for r in kept]
    assert paths[0]!=paths[1]
    assert all(p.is_file() for p in paths)
    assert paths[0].read_bytes()!=paths[1].read_bytes()


def test_archive_projection_updates_detach_replace_archive_and_preserves_legacy(client,app,project):
    lib=app.state.library
    ref=add_reference(client,project,seed=71,title="稳定参考")
    ref=lib.edit_reference(ref["id"],ReferenceEdit(expected_revision=ref["revision"],decision="keep"))
    old=Path(ref["archive_path"])
    history=old.parent/"01_不可识别历史.jpg"
    history.write_bytes(b"historical export must survive")
    sha=lib.ingest_asset(image_bytes(72))["id"]
    lib.replace_asset(ref["id"],sha,ref["revision"])
    assert not old.exists()
    ref=lib.reference(ref["id"])
    ref=lib.edit_reference(ref["id"],ReferenceEdit(expected_revision=ref["revision"],decision="keep"))
    current=Path(ref["archive_path"])
    assert current!=old and current.is_file()
    response=client.post(f"/api/projects/{project['id']}/references/transfer",json={"mode":"remove","items":[{"reference_id":ref["id"],"expected_revision":ref["revision"]}]})
    assert response.status_code==200,response.text
    assert not current.exists()
    ref=lib.reference(ref["id"])
    restored=lib.restore_detached_reference(ref["id"],ref["revision"])
    assert restored["archive_path"]==str(current) and restored["archive_error"] is None
    assert current.is_file()
    lib.archive_project(project["id"],project["revision"])
    assert not current.exists()
    assert history.read_bytes()==b"historical export must survive"


def test_legacy_heuristic_preflight_is_only_history_and_does_not_hide_candidate(client,app,project):
    lib=app.state.library
    ref=add_reference(client,project,seed=99)
    with lib.db.transaction() as con:
        stored=json.loads(con.execute("SELECT data FROM refs WHERE id=?",(ref["id"],)).fetchone()[0])
        stored.update(preflight={"producer":"vision-preflight-gate","identity_prediction":"mismatch","reason":"old heuristic assertion"},preflight_status="filtered",preflight_filtered=True)
        con.execute("UPDATE refs SET data=? WHERE id=?",(json.dumps(stored),ref["id"]))
    shown=lib.reference(ref["id"])
    assert shown["preflight_status"]=="unreviewed"
    assert shown["preflight_evidence_status"]=="legacy_unverified"
    assert not shown["preflight_filtered"]
    assert shown["preflight"] is None
    assert shown["legacy_preflight"]["identity_prediction"]=="mismatch"
    assert shown["recommendation"]["evidence"]["preflight"]["items"]==[]
    assert ref["id"] in {r["id"] for r in lib.references(project["id"])["items"]}
    assert ref["id"] in {r["id"] for r in lib.references(project["id"],preflight_status="unreviewed")["items"]}
    assert lib.references(project["id"],preflight_status="filtered")["total"]==0
    with lib.db.read() as con:
        assert json.loads(con.execute("SELECT data FROM refs WHERE id=?",(ref["id"],)).fetchone()[0])["preflight_filtered"] is True


def test_archive_failure_keeps_business_commit_and_reports_error(client,app,project,monkeypatch):
    ref=add_reference(client,project,seed=121)
    monkeypatch.setattr("ref_lab.archiver.export_asset_as_jpeg",lambda *_:False)
    response=client.patch(f"/api/references/{ref['id']}",json={"expected_revision":ref["revision"],"decision":"keep"})
    assert response.status_code==200
    assert response.json()["decision"]=="keep"
    assert response.json()["archive_error"]
    assert response.json()["archive_path"] is None
    assert app.state.library.reference(ref["id"])["decision"]=="keep"


def test_bulk_transaction_projects_shared_archive_once(client,app,project,monkeypatch):
    from ref_lab.models import ReferenceTransferInput
    import ref_lab.archiver as archiver
    lib=app.state.library
    refs=[add_reference(client,project,seed=130+i) for i in range(2)]
    refs=[lib.edit_reference(r["id"],ReferenceEdit(expected_revision=r["revision"],decision="keep")) for r in refs]
    original=archiver.sync_project_confirmed_archive
    calls=[]
    def sync(*args,**kwargs):
        calls.append(kwargs.get("archive_dir"))
        return original(*args,**kwargs)
    monkeypatch.setattr(archiver,"sync_project_confirmed_archive",sync)
    lib.transfer_references(project["id"],ReferenceTransferInput(mode="remove",items=[{"reference_id":r["id"],"expected_revision":r["revision"]} for r in refs]))
    assert len(calls)==1
    assert lib.references(project["id"])["total"]==0


def test_manual_identity_update_versions_and_expires_old_relative_assertions(client,app,project):
    lib=app.state.library
    selected=ready_reference(client,project)
    before=lib.identity_context(project["id"])
    supplied=IdentityContextInput(canonical_name=project["character"],work="人工核对作品",costume="新依据",visual_identifiers=["人工提供的角色依据"],reference_provenance="用户核对")
    current=lib.update_identity_context(project["id"],supplied)
    assert current["id"]!=before["id"] and current["version"]==before["version"]+1
    assert lib.identity_context(project["id"])["id"]==current["id"]
    shown=lib.reference(selected["id"])
    assert shown["decision"]=="keep" and shown["review"]["character_match"]=="exact"
    assert "stale_identity_context" in {b["code"] for b in shown["blockers"]}
    assert shown["recommendation"]["evidence"]["visual_observations"]["items"]==[]
    with lib.db.read() as con:
        assert con.execute("SELECT COUNT(*) FROM identity_contexts WHERE project_id=?",(project["id"],)).fetchone()[0]==2


def test_gear_change_expires_card_but_preserves_identity_review(client,app,project):
    lib=app.state.library
    selected=ready_reference(client,project)
    before=lib.identity_context(project["id"])
    lib.edit_project(project["id"],ProjectInput(**{key:("new camera" if key=="gear" else project[key]) for key in ("character","work","costume","brief","gear")}),project["revision"])
    assert lib.identity_context(project["id"])["id"]==before["id"]
    shown=lib.reference(selected["id"])
    codes={b["code"] for b in shown["blockers"]}
    assert "stale_context" in codes and "not_accepted" in codes
    assert "stale_identity_context" not in codes
    assert shown["review_current_context"]
    assert shown["recommendation"]["evidence"]["visual_observations"]["items"]


def test_ranking_preserves_file_check_origin_and_rejects_old_fake_visual_assertions(client,app,project):
    from ref_lab.ranking import score_and_rank_candidates
    lib=app.state.library
    ref=add_reference(client,project,seed=145)
    # A deterministic checker may describe file validity, never claim a vision agent.
    ref["preflight"]={"asset_sha":ref["asset_sha"],"producer":"deterministic_preflight","visual_evidence":[]}
    evidence=score_and_rank_candidates([ref])[0]["recommendation"]["evidence"]
    assert evidence["preflight"]["origin"]=="deterministic_file_check"
    assert evidence["preflight"]["items"]==[]
    ref=ready_reference(client,project,seed=146)
    with lib.db.transaction() as con:
        stored=json.loads(con.execute("SELECT data FROM refs WHERE id=?",(ref["id"],)).fetchone()[0])
        stored["review_producer"]="vision-preflight-gate"
        con.execute("UPDATE refs SET data=? WHERE id=?",(json.dumps(stored),ref["id"]))
    shown=lib.reference(ref["id"])
    assert shown["review"] is None
    assert shown["legacy_review"]==ref["review"]
    assert lib.references(project["id"],kind="cosplay_photo")["total"]==0
    assert ref["id"] in {r["id"] for r in lib.references(project["id"],kind="unknown")["items"]}
    assert lib.stats(project["id"])["ready"]==0
    assert "untrusted_review" in {b["code"] for b in shown["blockers"]}
    assert shown["recommendation"]["identity_status"]=="身份未核验"
    assert shown["recommendation"]["evidence"]["visual_observations"]["items"]==[]


def test_unchanged_legacy_acceptance_keeps_its_original_input_digest(client,app,project):
    import hashlib
    from ref_lab.db import encode
    lib=app.state.library
    ref=ready_reference(client,project,seed=147)
    # Freeze the pre-revision contract as a legacy accepted record.
    old_context=hashlib.sha256(encode({k:project.get(k,"") for k in ("character","work","costume","brief","gear")}).encode("utf-8")).hexdigest()
    old_acceptance=hashlib.sha256(encode({"asset":ref["asset_sha"],"review":ref["review"],"card":ref["card"],"context":old_context,"source":ref["source"],"title":ref["title"],"borrow":ref["borrow"],"allow_cross_domain":ref["allow_cross_domain"],"preference":ref["preference"]}).encode("utf-8")).hexdigest()
    with lib.db.transaction() as con:
        stored=json.loads(con.execute("SELECT data FROM refs WHERE id=?",(ref["id"],)).fetchone()[0])
        stored.update(card_context=old_context,accepted_fingerprint=old_acceptance)
        stored.pop("review_identity_context",None)
        con.execute("UPDATE refs SET data=? WHERE id=?",(encode(stored),ref["id"]))
    assert lib.reference(ref["id"])["field_ready"]
    lib.edit_project(project["id"],ProjectInput(**{key:("legacy new camera" if key=="gear" else project[key]) for key in ("character","work","costume","brief","gear")}),project["revision"])
    shown=lib.reference(ref["id"])
    assert shown["review_current_context"]
    assert "stale_identity_context" not in {b["code"] for b in shown["blockers"]}
    assert "stale_context" in {b["code"] for b in shown["blockers"]}


def test_preflight_history_api_marks_old_heuristics_without_rewriting_evidence(client,app,project):
    from ref_lab.preflight import save_preflight
    lib=app.state.library
    ref=add_reference(client,project,seed=148)
    old={"id":"pf_old_gate","project_id":project["id"],"asset_sha":ref["asset_sha"],"producer":"vision-preflight-gate","status":"passed","content_type":"real_person_cosplay","identity_prediction":"match","visual_evidence":["False old assertion"]}
    with lib.db.transaction() as con:
        save_preflight(con,old)
    shown=next(p for p in client.get(f"/api/projects/{project['id']}/preflights").json() if p["id"]==old["id"])
    assert shown["status"]=="unreviewed" and not shown["effective"]
    assert shown["content_type"]=="unknown" and shown["visual_evidence"]==[]
    assert shown["legacy_preflight"]==old
    assert not any(p["id"]==old["id"] for p in client.get(f"/api/projects/{project['id']}/preflights?status=passed").json())
    with lib.db.read() as con:
        assert json.loads(con.execute("SELECT data FROM preflights WHERE id=?",(old["id"],)).fetchone()[0])==old


def test_unknown_legacy_review_without_accepted_snapshot_requires_new_review(client,app,project):
    from ref_lab.db import encode
    lib=app.state.library
    ref=ready_reference(client,project,seed=149)
    with lib.db.transaction() as con:
        stored=json.loads(con.execute("SELECT data FROM refs WHERE id=?",(ref["id"],)).fetchone()[0])
        stored.pop("review_identity_context",None)
        stored["accepted_fingerprint"]=None
        con.execute("UPDATE refs SET data=? WHERE id=?",(encode(stored),ref["id"]))
    shown=lib.reference(ref["id"])
    assert not shown["review_current_context"]
    assert "stale_identity_context" in {b["code"] for b in shown["blockers"]}
    assert shown["recommendation"]["evidence"]["visual_observations"]["items"]==[]
    response=client.post(f"/api/references/{ref['id']}/accept",json={"expected_revision":ref["revision"]})
    assert response.status_code==409


def test_history_preflight_from_previous_project_inputs_is_not_effective(client,app,project):
    lib=app.state.library
    ref=add_reference(client,project,seed=150)
    before=next(p for p in lib.preflights(project["id"]) if p["reference_id"]==ref["id"])
    assert before["effective"]
    lib.edit_project(project["id"],ProjectInput(character="另一个目标",gear=project["gear"]),project["revision"])
    after=next(p for p in lib.preflights(project["id"]) if p["id"]==before["id"])
    assert not after["effective"] and after["status"]=="unreviewed"
    assert after["legacy_preflight"]["project_context"]==before["project_context"]
