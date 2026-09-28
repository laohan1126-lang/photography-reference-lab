"""Application use cases shared by the API, migration CLI, and local workers."""
from __future__ import annotations

import json
import sqlite3
from pathlib import Path
from uuid import uuid4
from typing import Any
from .config import Settings
from .db import Database, encode, now
from .catalog_data import keep_inspiration, record_discovery, record_observation
from .models import (CandidateInput, ProjectInput, ReferenceEdit, Source, VisualReview, Card,
                     AnalysisResult, NoteInput, JobInput, InspirationInput, InspirationEdit, CollectionReport,
                     CandidatePreflight, ReferenceTransferInput)
from .storage import AssetStore
from .policy import (MESSAGES, acceptance_digest, blockers, context_digest, digest, state_for)


class Problem(Exception):
    def __init__(self, status: int, message: str, details: Any = None):
        self.status, self.message, self.details = status, message, details
        super().__init__(message)


def fresh_id() -> str:
    return uuid4().hex


def row_data(con: sqlite3.Connection, table: str, ident: str) -> dict:
    if table not in {"projects", "assets", "refs", "jobs", "notes", "inspirations"}:
        raise ValueError("Invalid table")
    row = con.execute(f"SELECT data FROM {table} WHERE id=?", (ident,)).fetchone()
    if not row:
        raise Problem(404, f"{table} record not found")
    return json.loads(row["data"])


def check_revision(record: dict, expected: int) -> None:
    if record["revision"] != expected:
        raise Problem(409, "内容已被其他窗口或 Agent 修改，请刷新后重试", {"current_revision": record["revision"]})


def ensure_active_project(project: dict) -> None:
    if project.get("archived_at"):
        raise Problem(409, "项目已删除到回收区；请先恢复项目再继续修改")


_REAL_PERSON_MODALITIES = {"real_person_cosplay", "real_person_portrait"}
_FILTERED_MODALITIES = {
    "game_screenshot", "anime_screenshot", "official_illustration", "fan_art",
    "costume_display", "mannequin", "product", "collage", "scenery", "equipment",
}


def candidate_preflight_status(preflight: CandidatePreflight) -> str:
    if preflight.content_type in _FILTERED_MODALITIES or preflight.identity_prediction == "mismatch":
        return "filtered"
    if preflight.content_type == "unknown" or preflight.identity_prediction == "uncertain":
        return "uncertain"
    if preflight.content_type in _REAL_PERSON_MODALITIES and preflight.identity_prediction == "match":
        return "passed"
    return "uncertain"


class Library:
    def __init__(self, settings: Settings):
        self.settings = settings
        self.db = Database(settings.data_dir / "library.sqlite3")
        self.assets = AssetStore(settings)
        self._repair_untrusted_local_adapter_preflights()

    def _repair_untrusted_local_adapter_preflights(self) -> None:
        """Replace one known-bad metadata-only preflight producer with conservative local gates.

        The 2026-09-29 local_collection_adapter mislabeled search results as
        visually verified because the query itself contained "cos". Preserve
        that old payload for audit, but never keep it as the active preflight.
        """
        from .identity import get_identity_context, build_identity_context, save_identity_context
        from .preflight import run_candidate_preflight, save_preflight

        with self.db.transaction() as con:
            rows = con.execute("SELECT id,data FROM refs").fetchall()
            for row in rows:
                ref = json.loads(row["data"])
                old = ref.get("preflight") or {}
                if old.get("producer") != "local_collection_adapter":
                    continue
                project = row_data(con, "projects", ref["project_id"])
                history = list(ref.get("invalidated_preflights") or [])
                history.append({**old, "invalidated_at": now(), "invalidated_reason": "metadata_only_adapter_false_positive"})
                ref["invalidated_preflights"] = history[-5:]

                asset = row_data(con, "assets", ref["asset_sha"]) if ref.get("asset_sha") else None
                if not asset or not self.assets.path(asset).is_file():
                    ref.update(preflight=None, preflight_status="unreviewed", preflight_reason="旧本地适配器判断已作废；图片不可用，未重新预检",
                               preflight_filtered=False, preflight_override=False)
                    self._save(con, ref, project, "candidate.preflight_invalidated",
                               {"old_producer": "local_collection_adapter", "reason": "metadata_only_false_positive"}, "system")
                    continue

                context = get_identity_context(con, project_id=project["id"])
                if not context:
                    context = build_identity_context(project["character"], project.get("work", ""), project.get("costume", ""), project.get("brief", ""))
                    save_identity_context(con, project["id"], context)
                fresh = run_candidate_preflight(
                    self.assets.path(asset), metadata=ref, context=context,
                    asset_sha=ref["asset_sha"], project_id=project["id"], reference_id=ref["id"],
                )
                save_preflight(con, fresh)
                ref.update(
                    preflight=fresh,
                    preflight_status=fresh["status"],
                    preflight_reason=fresh["status_reason"],
                    preflight_id=fresh["id"],
                    dhash=fresh.get("dhash", ""),
                    preflight_filtered=fresh["status"] == "filtered",
                    preflight_override=False,
                )
                self._save(con, ref, project, "candidate.preflight_repaired",
                           {"old_producer": "local_collection_adapter", "new_status": fresh["status"],
                            "new_producer": fresh["producer"]}, "system")

    def create_project(self, data: ProjectInput, *, ident: str | None = None) -> dict:
        project = {**data.model_dump(), "id": ident or fresh_id(), "revision": 1, "archived_at": None, "created_at": now(), "updated_at": now()}
        with self.db.transaction() as con:
            if con.execute("SELECT 1 FROM projects WHERE id=?", (project["id"],)).fetchone():
                return row_data(con, "projects", project["id"])
            con.execute("INSERT INTO projects VALUES(?,?)", (project["id"], encode(project)))
            self.db.event(con, project["id"], project["id"], "project.created", data.model_dump())
        return project

    def project(self, ident: str) -> dict:
        with self.db.read() as con:
            return row_data(con, "projects", ident)

    def projects(self, *, archived: bool = False) -> list[dict]:
        with self.db.read() as con:
            items = [json.loads(r["data"]) for r in con.execute("SELECT data FROM projects ORDER BY rowid DESC")]
            return [item for item in items if bool(item.get("archived_at")) is archived]

    def edit_project(self, ident: str, data: ProjectInput, revision: int) -> dict:
        with self.db.transaction() as con:
            project = row_data(con, "projects", ident)
            ensure_active_project(project)
            check_revision(project, revision)
            before = context_digest(project)
            project.update(data.model_dump())
            project.update(revision=revision + 1, updated_at=now())
            con.execute("UPDATE projects SET data=? WHERE id=?", (encode(project), ident))
            if context_digest(project) != before:
                refs = [json.loads(r[0]) for r in con.execute("SELECT data FROM refs WHERE project_id=?", (ident,))]
                for ref in refs:
                    ref["accepted_fingerprint"] = None
                    self._save(con, ref, project, "context.invalidated", {"project_revision": project["revision"]})
            self.db.event(con, ident, ident, "project.updated", data.model_dump())
            return project

    def archive_project(self, ident: str, revision: int) -> dict:
        with self.db.transaction() as con:
            project = row_data(con, "projects", ident)
            check_revision(project, revision)
            if project.get("archived_at"):
                raise Problem(409, "项目已经在回收区")
            project.update(archived_at=now(), revision=revision + 1, updated_at=now())
            con.execute("UPDATE projects SET data=? WHERE id=?", (encode(project), ident))
            self.db.event(con, ident, ident, "project.archived", {"archived_at": project["archived_at"]})
            return project

    def restore_project(self, ident: str, revision: int) -> dict:
        with self.db.transaction() as con:
            project = row_data(con, "projects", ident)
            check_revision(project, revision)
            if not project.get("archived_at"):
                raise Problem(409, "项目不在回收区")
            project.update(archived_at=None, revision=revision + 1, updated_at=now())
            con.execute("UPDATE projects SET data=? WHERE id=?", (encode(project), ident))
            self.db.event(con, ident, ident, "project.restored", {})
            return project

    def ingest_asset(self, content: bytes, filename: str = "") -> dict:
        # Share the writer lock with recycling so an import cannot race a purge.
        with self.db.transaction() as con:
            metadata = self.assets.ingest(content, filename)
            con.execute("INSERT OR IGNORE INTO assets VALUES(?,?)", (metadata["id"], encode(metadata)))
            previous = row_data(con, "assets", metadata["id"])
            if previous.get("storage_status") in {"purged", "purge_failed"}:
                previous.update(storage_status="available", integrity="ok", restored_at=now())
                con.execute("UPDATE assets SET data=? WHERE id=?", (encode(previous), previous["id"]))
                self.db.event(con, None, previous["id"], "asset.reimported", {"sha": previous["id"]})
            return previous

    def asset(self, sha: str) -> dict:
        with self.db.read() as con:
            return row_data(con, "assets", sha)

    def _asset_exists(self, con: sqlite3.Connection, ref: dict) -> bool:
        if not ref.get("asset_sha"):
            return False
        asset = row_data(con, "assets", ref["asset_sha"])
        return asset.get("storage_status") not in {"purged", "purge_failed"} and asset.get("integrity", "ok") == "ok" and self.assets.path(asset).is_file()

    def _save(self, con: sqlite3.Connection, ref: dict, project: dict, action: str,
              payload: object, actor: str = "human") -> dict:
        ref["revision"] += 1
        ref["updated_at"] = now()
        ref["state"] = "detached" if ref.get("detached_at") else state_for(ref, project, self._asset_exists(con, ref))
        con.execute("UPDATE refs SET asset_sha=?,decision=?,state=?,data=? WHERE id=?",
                    (ref["asset_sha"], ref["decision"], ref["state"], encode(ref), ref["id"]))
        self.db.event(con, ref["project_id"], ref["id"], action, payload, actor)
        return ref

    def _decorate(self, con: sqlite3.Connection, ref: dict, project: dict | None = None) -> dict:
        project = project or row_data(con, "projects", ref["project_id"])
        exists = self._asset_exists(con, ref)
        result = dict(ref)
        result["asset"] = row_data(con, "assets", ref["asset_sha"]) if ref["asset_sha"] else None
        detached = bool(ref.get("detached_at"))
        result["state"] = "detached" if detached else state_for(ref, project, exists)
        result["blockers"] = [{"code": x, "message": MESSAGES[x]} for x in blockers(ref, project, exists)]
        result["field_ready"] = not result["blockers"] and not detached
        result["file_available"] = exists
        result["selected_for_project"] = not detached and ref["decision"] == "keep" and ref["lane"] == "field"
        saved = con.execute("SELECT id FROM inspirations WHERE asset_sha=? AND active=1", (ref["asset_sha"],)).fetchone()
        result["inspiration_id"] = saved[0] if saved else None
        result["workflow_stage"] = self._workflow_stage(con, ref, project, result)
        return result

    def reference(self, ident: str) -> dict:
        with self.db.read() as con:
            return self._decorate(con, row_data(con, "refs", ident))

    def _insert_reference(self, con: sqlite3.Connection, project: dict, data: CandidateInput, decision: str, actor: str) -> dict:
        project_id = project["id"]
        ref = {"id": fresh_id(), "project_id": project_id, "asset_sha": data.asset_sha,
               "title": data.title or data.source.title or "未命名参考", "source": data.source.model_dump(),
               "discovered_sources": [data.source.model_dump()], "legacy_notes": data.legacy_notes,
               "decision": decision, "lane": "field", "preference": "", "borrow": [], "allow_cross_domain": False,
               "discovery_intent": data.discovery_intent, "discovery_reason": data.discovery_reason,
               "preflight": None, "preflight_status": "unreviewed", "preflight_filtered": False, "preflight_override": False,
               "detached_at": None, "detached_to_project_id": None, "detached_reason": "",
               "review": None, "review_actor": "", "review_producer": "", "card": None, "card_context": "",
               "card_producer": "", "accepted_fingerprint": None, "reflections": [], "revision": 1,
               "created_at": now(), "updated_at": now()}
        if decision == "reject":
            ref.update(rejected_at=now(), before_reject={"decision": "pending", "lane": "field"})
        ref["state"] = state_for(ref, project, self._asset_exists(con, ref))
        con.execute("INSERT INTO refs VALUES(?,?,?,?,?,?)",
                    (ref["id"], project_id, data.asset_sha, decision, ref["state"], encode(ref)))
        self.db.event(con, project_id, ref["id"], "candidate.imported", {"source": data.source.model_dump(), "decision": decision}, actor)
        return ref

    def add_candidate(self, project_id: str, data: CandidateInput, *, decision: str = "pending", actor: str = "import", record_context: bool = True, attempt_id: str = "") -> dict:
        with self.db.transaction() as con:
            project = row_data(con, "projects", project_id)
            ensure_active_project(project)
            if data.asset_sha:
                asset = row_data(con, "assets", data.asset_sha)
                if asset.get("storage_status") in {"purged", "purge_failed"}:
                    raise Problem(409, "原图已清理，请先重新导入相同图片字节")
            job = row_data(con, "jobs", data.job_id) if data.job_id else None
            if job and (job["project_id"] != project_id or job["kind"] != "collection" or job["status"] == "cancelled"):
                raise Problem(409, "Candidate does not belong to an open collection job")
            if attempt_id and (not job or job.get("active_attempt_id") != attempt_id or job["status"] != "running"):
                raise Problem(409, "采集轮次已取消、结束或被替代；拒绝过期写入")
            alias = con.execute("SELECT ref_id FROM aliases WHERE project_id=? AND import_key=?",
                                (project_id, data.import_key)).fetchone() if data.import_key else None
            existing = row_data(con, "refs", alias[0]) if alias else None
            if existing and existing["asset_sha"] != data.asset_sha:
                raise Problem(409, "Same import key points to changed image bytes; use explicit replace")
            if not existing and data.asset_sha:
                hit = con.execute("SELECT id FROM refs WHERE project_id=? AND asset_sha=?", (project_id, data.asset_sha)).fetchone()
                existing = row_data(con, "refs", hit[0]) if hit else None