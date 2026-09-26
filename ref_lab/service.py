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
                     AnalysisResult, NoteInput, JobInput, InspirationInput, InspirationEdit, CollectionReport)
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


class Library:
    def __init__(self, settings: Settings):
        self.settings = settings
        self.db = Database(settings.data_dir / "library.sqlite3")
        self.assets = AssetStore(settings)

    def create_project(self, data: ProjectInput, *, ident: str | None = None) -> dict:
        project = {**data.model_dump(), "id": ident or fresh_id(), "revision": 1, "created_at": now(), "updated_at": now()}
        with self.db.transaction() as con:
            if con.execute("SELECT 1 FROM projects WHERE id=?", (project["id"],)).fetchone():
                return row_data(con, "projects", project["id"])
            con.execute("INSERT INTO projects VALUES(?,?)", (project["id"], encode(project)))
            self.db.event(con, project["id"], project["id"], "project.created", data.model_dump())
        return project

    def project(self, ident: str) -> dict:
        with self.db.read() as con:
            return row_data(con, "projects", ident)

    def projects(self) -> list[dict]:
        with self.db.read() as con:
            return [json.loads(r["data"]) for r in con.execute("SELECT data FROM projects ORDER BY rowid DESC")]

    def edit_project(self, ident: str, data: ProjectInput, revision: int) -> dict:
        with self.db.transaction() as con:
            project = row_data(con, "projects", ident)
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
        ref["state"] = state_for(ref, project, self._asset_exists(con, ref))
        con.execute("UPDATE refs SET asset_sha=?,decision=?,state=?,data=? WHERE id=?",
                    (ref["asset_sha"], ref["decision"], ref["state"], encode(ref), ref["id"]))
        self.db.event(con, ref["project_id"], ref["id"], action, payload, actor)
        return ref

    def _decorate(self, con: sqlite3.Connection, ref: dict, project: dict | None = None) -> dict:
        project = project or row_data(con, "projects", ref["project_id"])
        exists = self._asset_exists(con, ref)
        result = dict(ref)
        result["asset"] = row_data(con, "assets", ref["asset_sha"]) if ref["asset_sha"] else None
        result["state"] = state_for(ref, project, exists)
        result["blockers"] = [{"code": x, "message": MESSAGES[x]} for x in blockers(ref, project, exists)]
        result["field_ready"] = not result["blockers"]
        result["file_available"] = exists
        result["selected_for_project"] = ref["decision"] == "keep" and ref["lane"] == "field"
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

    def add_candidate(self, project_id: str, data: CandidateInput, *, decision: str = "pending", actor: str = "import", record_context: bool = True) -> dict:
        with self.db.transaction() as con:
            project = row_data(con, "projects", project_id)
            if data.asset_sha:
                asset = row_data(con, "assets", data.asset_sha)
                if asset.get("storage_status") in {"purged", "purge_failed"}:
                    raise Problem(409, "原图已清理，请先重新导入相同图片字节")
            job = row_data(con, "jobs", data.job_id) if data.job_id else None
            if job and (job["project_id"] != project_id or job["kind"] != "collection" or job["status"] == "cancelled"):
                raise Problem(409, "Candidate does not belong to an open collection job")
            alias = con.execute("SELECT ref_id FROM aliases WHERE project_id=? AND import_key=?",
                                (project_id, data.import_key)).fetchone() if data.import_key else None
            existing = row_data(con, "refs", alias[0]) if alias else None
            if existing and existing["asset_sha"] != data.asset_sha:
                raise Problem(409, "Same import key points to changed image bytes; use explicit replace")
            if not existing and data.asset_sha:
                hit = con.execute("SELECT id FROM refs WHERE project_id=? AND asset_sha=?", (project_id, data.asset_sha)).fetchone()
                existing = row_data(con, "refs", hit[0]) if hit else None
            if job and job["status"] == "succeeded":
                if not existing or existing["id"] not in job["imported_ids"] or data.source.model_dump() not in existing["discovered_sources"]:
                    raise Problem(409, "已完成任务不接受新的候选，请新建采集任务")
                return {"created": False, "reference": self._decorate(con, existing, project)}
            if existing:
                ref = existing
                source = data.source.model_dump()
                if source not in ref["discovered_sources"]:
                    ref["discovered_sources"].append(source)
                    self._save(con, ref, project, "candidate.additional_source", source, actor)
                created = False
            else:
                if decision not in {"pending", "keep", "maybe", "reject"}:
                    raise ValueError("Invalid initial decision")
                ref = self._insert_reference(con, project, data, decision, actor)
                created = True
            if record_context:
                record_discovery(con, ref, data.source.model_dump(), job_id=data.job_id or None,
                                 project_snapshot=(job.get("project_snapshot") if job else project) if actor != "legacy_migration" else None,
                                 intent=data.discovery_intent, reason=data.discovery_reason,
                                 discovery_url=data.discovery_url, import_key=data.import_key,
                                 legacy=actor == "legacy_migration")
            if data.import_key:
                con.execute("INSERT OR IGNORE INTO aliases VALUES(?,?,?)", (project_id, data.import_key, ref["id"]))
            if job and ref["id"] not in job["imported_ids"]:
                job["imported_ids"].append(ref["id"])
                self._save_job(con, job, "collection.imported", {"reference_id": ref["id"]}, actor)
            return {"created": created, "reference": self._decorate(con, ref, project)}

    def references(self, project_id: str, *, limit: int = 60, offset: int = 0, query: str = "",
                   decision: str = "", state: str = "", lane: str = "", kind: str = "",
                   include_rejected: bool = False, job_id: str = "", focus_id: str = "") -> dict:
        clauses, args = ["project_id=?"], [project_id]
        if not include_rejected and decision != "reject" and state != "rejected":
            clauses.append("decision<>'reject'")
        if job_id:
            job = self.job(job_id)
            if job["project_id"] != project_id or job["kind"] != "collection":
                raise Problem(409, "采集任务不属于当前项目")
            clauses.append("id IN (SELECT reference_id FROM discoveries WHERE job_id=?)")
            args.append(job_id)
        for column, value in (("decision", decision), ("state", state)):
            if value:
                clauses.append(f"{column}=?")
                args.append(value)
        if lane:
            clauses.append("json_extract(data,'$.lane')=?")
            args.append(lane)
        if kind:
            clauses.append("COALESCE(json_extract(data,'$.review.kind'),'unknown')=?")
            args.append(kind)
        if query:
            clauses.append("(json_extract(data,'$.title') LIKE ? ESCAPE '\\' OR json_extract(data,'$.preference') LIKE ? ESCAPE '\\' OR json_extract(data,'$.source.author') LIKE ? ESCAPE '\\')")
            term = "%" + query.replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_") + "%"
            args.extend([term, term, term])
        where = " AND ".join(clauses)
        with self.db.read() as con:
            project = row_data(con, "projects", project_id)
            if focus_id and con.execute(f"SELECT 1 FROM refs WHERE {where} AND id=?", (*args, focus_id)).fetchone():
                position = con.execute(f"SELECT COUNT(*) FROM refs WHERE {where} AND rowid < (SELECT rowid FROM refs WHERE id=?)", (*args, focus_id)).fetchone()[0]
                offset = position // limit * limit
            count = con.execute(f"SELECT COUNT(*) FROM refs WHERE {where}", args).fetchone()[0]
            rows = con.execute(f"SELECT data FROM refs WHERE {where} ORDER BY rowid LIMIT ? OFFSET ?", (*args, limit, offset))
            return {"items": [self._decorate(con, json.loads(r[0]), project) for r in rows], "total": count, "offset": offset, "limit": limit}

    def stats(self, project_id: str) -> dict:
        with self.db.read() as con:
            row_data(con, "projects", project_id)
            result = {"total": 0, "pending": 0, "keep": 0, "maybe": 0, "reject": 0, "ready": 0}
            for row in con.execute("SELECT decision,COUNT(*) FROM refs WHERE project_id=? GROUP BY decision", (project_id,)):
                result[row[0]] = row[1]
                result["total"] += row[1]
            result["ready"] = con.execute("SELECT COUNT(*) FROM refs WHERE project_id=? AND state='ready'", (project_id,)).fetchone()[0]
            result["selected"] = con.execute("SELECT COUNT(*) FROM refs WHERE project_id=? AND decision='keep' AND json_extract(data,'$.lane')='field'", (project_id,)).fetchone()[0]
            result["visible"] = result["total"] - result["reject"]
            return result

    def edit_reference(self, ident: str, data: ReferenceEdit) -> dict:
        changes = data.model_dump(exclude_none=True, exclude={"expected_revision"})
        with self.db.transaction() as con:
            ref = row_data(con, "refs", ident)
            project = row_data(con, "projects", ref["project_id"])
            check_revision(ref, data.expected_revision)
            if changes:
                if changes.get("decision") == "reject" and ref["decision"] != "reject":
                    ref["before_reject"] = {"decision": ref["decision"], "lane": ref["lane"]}
                    ref["rejected_at"] = now()
                elif changes.get("decision") and changes["decision"] != "reject":
                    ref["rejected_at"] = None
                ref.update(changes)
                ref["accepted_fingerprint"] = None
                # Only an explicit human choice saves a global membership. Merely
                # reading or re-importing an old ref never resurrects removed favorites.
                if ref["decision"] == "keep" and ref["lane"] == "inspiration" and ("decision" in changes or "lane" in changes):
                    item, _ = keep_inspiration(con, asset_sha=ref["asset_sha"], title=ref["title"], source=ref["source"],
                                               preference=ref["preference"], borrow=ref["borrow"], origin_ref=ref)
                    self.db.event(con, None, item["id"], "inspiration.saved", {"reference_id": ident})
                self._save(con, ref, project, "reference.updated", changes)
            return self._decorate(con, ref, project)

    def review_reference(self, ident: str, review: VisualReview, revision: int) -> dict:
        with self.db.transaction() as con:
            ref = row_data(con, "refs", ident)
            check_revision(ref, revision)
            if ref["asset_sha"] != review.asset_sha:
                raise Problem(409, "核验结果对应的不是当前图片")
            project = row_data(con, "projects", ref["project_id"])
            ref.update(review=review.model_dump(), review_actor="human", review_producer="manual",
                       accepted_fingerprint=None)
            record_observation(con, ref)
            self._save(con, ref, project, "review.saved", review.model_dump())
            return self._decorate(con, ref, project)

    def save_card(self, ident: str, card: Card, revision: int) -> dict:
        with self.db.transaction() as con:
            ref = row_data(con, "refs", ident)
            check_revision(ref, revision)
            project = row_data(con, "projects", ref["project_id"])
            if ref["decision"] != "keep":
                raise Problem(409, "请先保留参考，再编写资料卡")
            if not ref["review"] or ref["review"]["kind"] not in {"cosplay_photo", "portrait_photo"}:
                raise Problem(409, "请先核验为真人摄影参考；其他素材只能归入灵感库")
            ref.update(card=card.model_dump(), card_context=context_digest(project), card_producer="manual", accepted_fingerprint=None)
            self._save(con, ref, project, "card.saved", card.model_dump())
            return self._decorate(con, ref, project)

    def apply_analysis(self, ident: str, result: AnalysisResult, revision: int, producer: str, job_id: str = "") -> dict:
        with self.db.transaction() as con:
            ref = row_data(con, "refs", ident)
            check_revision(ref, revision)
            if ref["decision"] != "keep":
                raise Problem(409, "只分析人工保留的参考")
            if result.review.asset_sha != ref["asset_sha"]:
                raise Problem(409, "分析对应的图片版本已改变")
            project = row_data(con, "projects", ref["project_id"])
            if job_id:
                job = row_data(con, "jobs", job_id)
                snapshot = job["snapshots"].get(ident)
                if job["project_id"] != ref["project_id"] or job["kind"] != "analysis" or not snapshot:
                    raise Problem(409, "分析结果不属于此任务")
                if job["status"] in {"succeeded", "cancelled"} or snapshot["revision"] != revision or job["context"] != context_digest(project):
                    raise Problem(409, "任务快照已过期，请重新建立分析任务")
            review = result.review.model_dump()
            eligible = (review["kind"] in {"cosplay_photo", "portrait_photo"} and review["visible_person"] and
                        review["pose_readable"] and review["single_image"] and review["sufficiently_clear"] and not review["critical_uncertainties"])
            ref.update(review=review, review_actor="ai", review_producer=producer,
                       card=result.card.model_dump() if result.card and eligible else None,
                       card_context=context_digest(project), card_producer=producer, accepted_fingerprint=None)
            record_observation(con, ref)
            self._save(con, ref, project, "analysis.imported", {"producer": producer, "result": result.model_dump(), "job_id": job_id}, "ai")
            if job_id and ident not in job["completed_ids"]:
                job["completed_ids"].append(ident)
                if set(job["completed_ids"]) == set(job["reference_ids"]):
                    job.update(status="succeeded", detail="逐图分析结果已全部导入；资料卡仍等待你核对确认")
                self._save_job(con, job, "analysis.completed_item", {"reference_id": ident}, "ai")
            return self._decorate(con, ref, project)

    def accept_card(self, ident: str, revision: int, *, source: Source | None = None,
                    allow_cross_domain: bool | None = None) -> dict:
        with self.db.transaction() as con:
            ref = row_data(con, "refs", ident)
            project = row_data(con, "projects", ref["project_id"])
            check_revision(ref, revision)
            if source is not None:
                ref["source"] = source.model_dump()
            if allow_cross_domain is not None:
                ref["allow_cross_domain"] = allow_cross_domain
            reasons = blockers(ref, project, self._asset_exists(con, ref), require_acceptance=False)
            if reasons:
                raise Problem(409, "尚不能发布为现场卡", [{"code": x, "message": MESSAGES[x]} for x in reasons])
            if not self.assets.verify(row_data(con, "assets", ref["asset_sha"])):
                raise Problem(409, "图片文件完整性校验失败")
            ref["accepted_fingerprint"] = acceptance_digest(ref, project)
            self._save(con, ref, project, "card.accepted", {"fingerprint": ref["accepted_fingerprint"]})
            return self._decorate(con, ref, project)

    def replace_asset(self, ident: str, sha: str, revision: int) -> dict:
        with self.db.transaction() as con:
            ref = row_data(con, "refs", ident)
            check_revision(ref, revision)
            row_data(con, "assets", sha)
            duplicate = con.execute("SELECT id FROM refs WHERE project_id=? AND asset_sha=? AND id<>?", (ref["project_id"], sha, ident)).fetchone()
            if duplicate:
                raise Problem(409, "本项目已存在相同文件", {"reference_id": duplicate[0]})
            old_sha = ref["asset_sha"]
            project = row_data(con, "projects", ref["project_id"])
            ref.update(asset_sha=sha, decision="pending", rejected_at=None, before_reject=None, review=None, review_actor="", review_producer="", card=None,
                       card_context="", card_producer="", accepted_fingerprint=None)
            ref["source"]["source_confirmed"] = False
            self._save(con, ref, project, "asset.replaced", {"before": old_sha, "after": sha})
            return self._decorate(con, ref, project)

    def reflect(self, ident: str, data: dict) -> dict:
        with self.db.transaction() as con:
            ref = row_data(con, "refs", ident)
            check_revision(ref, data.pop("expected_revision"))
            project = row_data(con, "projects", ref["project_id"])
            ref["reflections"].append({**data, "at": now()})
            self._save(con, ref, project, "reflection.added", data)
            return self._decorate(con, ref, project)

    def duplicates(self, project_id: str, ident: str, threshold: int = 6) -> list[dict]:
        target = self.reference(ident)
        if target["project_id"] != project_id:
            raise Problem(404, "Reference does not belong to project")
        if not target["asset"]: return []
        fingerprint = int(target["asset"]["dhash"], 16)
        with self.db.read() as con:
            matches = []
            for row in con.execute("SELECT r.id,a.data FROM refs r JOIN assets a ON r.asset_sha=a.id WHERE r.project_id=? AND r.id<>?", (project_id, ident)):
                asset = json.loads(row[1])
                distance = (fingerprint ^ int(asset["dhash"], 16)).bit_count()
                if distance <= threshold:
                    matches.append({"id": row[0], "asset_sha": asset["id"], "distance": distance})
            return sorted(matches, key=lambda x: x["distance"])[:30]

    def add_note(self, project_id: str | None, note: NoteInput) -> dict:
        fingerprint = digest(note.model_dump())
        with self.db.transaction() as con:
            if project_id is not None:
                row_data(con, "projects", project_id)
            previous = con.execute("SELECT data FROM notes WHERE project_id IS ? AND fingerprint=?", (project_id, fingerprint)).fetchone()
            if previous: return json.loads(previous[0])
            data = {**note.model_dump(), "id": fresh_id(), "project_id": project_id, "revision": 1, "created_at": now(), "updated_at": now()}
            con.execute("INSERT INTO notes VALUES(?,?,?,?)", (data["id"], project_id, fingerprint, encode(data)))
            self.db.event(con, project_id, data["id"], "note.imported", {"title": note.title, "source_path": note.source_path})
            return data

    def edit_note(self, ident: str, title: str, body: str, revision: int) -> dict:
        with self.db.transaction() as con:
            note = row_data(con, "notes", ident)
            check_revision(note, revision)
            note.update(title=title, body=body, revision=revision + 1, updated_at=now())
            # Keep the import fingerprint unchanged: re-importing the same archive cannot overwrite edits.
            con.execute("UPDATE notes SET data=? WHERE id=?", (encode(note), ident))
            self.db.event(con, note["project_id"], ident, "note.updated", {"title": title, "revision": note["revision"]})
            return note

    def notes(self, project_id: str | None = None) -> list[dict]:
        with self.db.read() as con:
            if project_id is not None:
                row_data(con, "projects", project_id)
                rows = con.execute("SELECT data FROM notes WHERE project_id=? ORDER BY rowid DESC", (project_id,))
            else:
                rows = con.execute("SELECT data FROM notes ORDER BY rowid DESC")
            return [json.loads(r[0]) for r in rows]

    def events(self, project_id: str, after: int = 0, limit: int = 100) -> list[dict]:
        with self.db.read() as con:
            row_data(con, "projects", project_id)
            return [{**dict(r), "data": json.loads(r["data"])} for r in con.execute(
                "SELECT * FROM events WHERE project_id=? AND id>? ORDER BY id DESC LIMIT ?", (project_id, after, limit))]

    def create_job(self, project_id: str, request: JobInput) -> dict:
        with self.db.transaction() as con:
            project = row_data(con, "projects", project_id)
            ids = list(dict.fromkeys(request.reference_ids))
            snapshots = {}
            if request.kind == "analysis":
                if not ids: raise Problem(422, "请先选择要分析的已保留参考")
                for ident in ids:
                    ref = row_data(con, "refs", ident)
                    if ref["project_id"] != project_id or ref["decision"] != "keep" or not ref["asset_sha"]:
                        raise Problem(409, "分析任务只能包含本项目已保留且有图片的条目")
                    snapshots[ident] = {"revision": ref["revision"], "asset_sha": ref["asset_sha"]}
            elif ids:
                raise Problem(422, "Collection jobs do not accept reference IDs")
            base = " ".join(x for x in [project["character"], project["work"], project["costume"]] if x)
            plan = [f"{base} cosplay 摄影", f"{base} cos 漫展 姿势", f"{base} コスプレ 写真"]
            if request.kind == "analysis":
                for row in con.execute("SELECT data FROM jobs WHERE project_id=? AND kind='analysis' AND status IN ('blocked','queued','running')", (project_id,)):
                    previous = json.loads(row[0])
                    if previous["snapshots"] == snapshots and previous["context"] == context_digest(project) and previous["notes"] == request.notes:
                        return previous
            job = {"id": fresh_id(), "project_id": project_id, "kind": request.kind, "status": "blocked", "revision": 1,
                   "detail": "等待 Codex / Antigravity 接手；尚未执行搜索／分析", "notes": request.notes,
                   "project_snapshot": dict(project), "executor": "agent_browserskill" if request.kind == "collection" else "agent",
                   "target_count": request.target_count if request.kind == "collection" else len(ids),
                   "preferred_sources": request.preferred_sources if request.kind == "collection" else [],
                   "execution_report": None,
                   "queries": plan if request.kind == "collection" else [], "brief": project["brief"],
                   "reference_ids": ids, "snapshots": snapshots, "context": context_digest(project),
                   "imported_ids": [], "completed_ids": [], "created_at": now(), "updated_at": now()}
            con.execute("INSERT INTO jobs VALUES(?,?,?,?,?)", (job["id"], project_id, request.kind, job["status"], encode(job)))
            self.db.event(con, project_id, job["id"], "job.created", job)
            return job

    def _save_job(self, con: sqlite3.Connection, job: dict, action: str, payload: object, actor: str = "human") -> dict:
        job.update(revision=job["revision"] + 1, updated_at=now())
        con.execute("UPDATE jobs SET status=?,data=? WHERE id=?", (job["status"], encode(job), job["id"]))
        self.db.event(con, job["project_id"], job["id"], action, payload, actor)
        return job

    def job(self, ident: str) -> dict:
        with self.db.read() as con: return row_data(con, "jobs", ident)

    def jobs(self, project_id: str | None = None) -> list[dict]:
        with self.db.read() as con:
            if project_id is not None:
                row_data(con, "projects", project_id)
                rows = con.execute("SELECT data FROM jobs WHERE project_id=? ORDER BY rowid DESC", (project_id,))
            else:
                rows = con.execute("SELECT data FROM jobs ORDER BY rowid DESC")
            return [json.loads(r[0]) for r in rows]

    def transition_job(self, ident: str, status: str, revision: int, detail: str, *, actor: str = "human") -> dict:
        transitions = {"blocked": {"running", "cancelled"}, "queued": {"running", "blocked", "cancelled"},
                       "running": {"blocked", "failed", "succeeded", "cancelled"}, "failed": {"running", "cancelled"},
                       "succeeded": set(), "cancelled": set()}
        with self.db.transaction() as con:
            job = row_data(con, "jobs", ident)
            check_revision(job, revision)
            if status not in transitions[job["status"]]:
                raise Problem(409, f"不允许 {job['status']} → {status}")
            if status == "succeeded":
                if job["kind"] == "collection" and not job["imported_ids"]:
                    raise Problem(409, "没有已导入的候选，不能宣称采集成功")
                if job["kind"] == "analysis" and set(job["completed_ids"]) != set(job["reference_ids"]):
                    raise Problem(409, "仍有分析条目未完成")
            job.update(status=status, detail=detail)
            return self._save_job(con, job, "job.transitioned", {"status": status, "detail": detail}, actor)

    def job_bundle(self, ident: str) -> dict:
        from .acquisition import acquisition_contract, agent_instructions
        job = self.job(ident)
        current_project = self.project(job["project_id"])
        project = job.get("project_snapshot") or current_project
        refs = [self.reference(x) for x in job["reference_ids"]]
        if job["kind"] == "analysis":
            if job["context"] != context_digest(current_project):
                raise Problem(409, "项目要求已经改变，请重新建立制卡任务")
            for ref in refs:
                snapshot = job["snapshots"].get(ref["id"], {})
                if ref["id"] not in job["completed_ids"] and (snapshot.get("revision") != ref["revision"] or snapshot.get("asset_sha") != ref["asset_sha"]):
                    raise Problem(409, "任务图片或选择已改变，请重新建立制卡任务")
            refs = [r for r in refs if r["id"] not in job["completed_ids"]]
        return {"schema_version": 2, "job": job, "project": project, "references": refs,
                "project_snapshot_is_original": bool(job.get("project_snapshot")),
                "acquisition": acquisition_contract(job) if job["kind"] == "collection" else None,
                "agent_instructions": agent_instructions(job),
                "rules": ["Search intent is discovery context, never an observed character or image fact.",
                          "Preserve received bytes and original post provenance; no credentials or access bypass.",
                          "Inspect each selected image separately; no contact sheets as pose evidence.",
                          "Return null card for irrelevant/uncertain images. Never accept a field card for the user."]}

    def _workflow_stage(self, con: sqlite3.Connection, ref: dict, project: dict, result: dict) -> str:
        if ref["decision"] == "reject": return "rejected"
        if ref["decision"] != "keep": return "candidate"
        if ref["lane"] == "inspiration": return "inspiration"
        if result["field_ready"]: return "ready"
        row = con.execute("SELECT data FROM jobs WHERE project_id=? AND kind='analysis' AND status IN ('blocked','queued','running') "
                          "AND EXISTS (SELECT 1 FROM json_each(jobs.data,'$.reference_ids') WHERE value=?) ORDER BY rowid DESC LIMIT 1",
                          (ref["project_id"], ref["id"])).fetchone()
        if row:
            job = json.loads(row[0])
            snapshot = job["snapshots"].get(ref["id"], {})
            if snapshot == {"revision": ref["revision"], "asset_sha": ref["asset_sha"]} and job["context"] == context_digest(project):
                result["analysis_job"] = {k: job[k] for k in ("id", "status", "detail", "revision")}
                return "analyzing" if job["status"] == "running" else "waiting_analysis"
        if ref.get("card"): return "card_draft"
        return "analyzed" if ref.get("review") else "selected"

    def restore_reference(self, ident: str, revision: int) -> dict:
        with self.db.transaction() as con:
            ref = row_data(con, "refs", ident)
            check_revision(ref, revision)
            if ref["decision"] != "reject": raise Problem(409, "此参考不在回收站")
            if ref["asset_sha"] and row_data(con, "assets", ref["asset_sha"]).get("storage_status") in {"purged", "purge_failed"}:
                raise Problem(409, "图片字节已被清理；请重新导入相同图片后再恢复")
            previous = ref.get("before_reject") or {"decision": "pending", "lane": ref["lane"]}
            ref.update(decision=previous["decision"], lane=previous["lane"], rejected_at=None, accepted_fingerprint=None)
            project = row_data(con, "projects", ref["project_id"])
            self._save(con, ref, project, "reference.restored", {"decision": ref["decision"]})
            return self._decorate(con, ref, project)

    def _decorate_inspiration(self, con: sqlite3.Connection, item: dict) -> dict:
        result = dict(item)
        result["asset"] = row_data(con, "assets", item["asset_sha"]) if item["asset_sha"] else None
        result["file_available"] = self._asset_exists(con, item)
        result["state"] = "inspiration" if item["active"] else "rejected"
        result["decision"] = "keep" if item["active"] else "reject"
        result["used_in_projects"] = [dict(r) for r in con.execute(
            "SELECT r.project_id,r.id AS reference_id,json_extract(p.data,'$.character') AS character FROM refs r JOIN projects p ON p.id=r.project_id WHERE r.asset_sha=? AND r.decision='keep' AND json_extract(r.data,'$.lane')='field'", (item["asset_sha"],))]
        return result

    def inspirations(self, *, limit: int = 60, offset: int = 0, query: str = "", recycled: bool = False) -> dict:
        where, args = "active=?", [int(not recycled)]
        if query:
            where += " AND (instr(lower(json_extract(data,'$.title')),lower(?))>0 OR instr(lower(json_extract(data,'$.preference')),lower(?))>0 OR instr(lower(json_extract(data,'$.borrow')),lower(?))>0)"
            args += [query, query, query]
        with self.db.read() as con:
            total = con.execute(f"SELECT COUNT(*) FROM inspirations WHERE {where}", args).fetchone()[0]
            rows = con.execute(f"SELECT data FROM inspirations WHERE {where} ORDER BY rowid LIMIT ? OFFSET ?", (*args, limit, offset))
            return {"items": [self._decorate_inspiration(con, json.loads(r[0])) for r in rows], "total": total, "limit": limit, "offset": offset}

    def inspiration(self, ident: str) -> dict:
        with self.db.read() as con:
            return self._decorate_inspiration(con, row_data(con, "inspirations", ident))

    def create_inspiration(self, data: InspirationInput) -> dict:
        with self.db.transaction() as con:
            if not self._asset_exists(con, {"asset_sha": data.asset_sha}):
                raise Problem(409, "需要实际可用的图片；请先上传或修复原图")
            item, created = keep_inspiration(con, **data.model_dump())
            record_discovery(con, {"id": None, "asset_sha": data.asset_sha, "project_id": None}, data.source.model_dump())
            self.db.event(con, None, item["id"], "inspiration.saved", {"created": created, "asset_sha": data.asset_sha})
            return {"created": created, "item": self._decorate_inspiration(con, item)}

    def save_reference_inspiration(self, ident: str, revision: int) -> dict:
        with self.db.transaction() as con:
            ref = row_data(con, "refs", ident)
            check_revision(ref, revision)
            item, created = keep_inspiration(con, asset_sha=ref["asset_sha"], title=ref["title"], source=ref["source"],
                                             preference=ref["preference"], borrow=ref["borrow"], origin_ref=ref)
            self.db.event(con, None, item["id"], "inspiration.saved", {"reference_id": ident})
            return {"created": created, "item": self._decorate_inspiration(con, item)}

    def edit_inspiration(self, ident: str, data: InspirationEdit) -> dict:
        with self.db.transaction() as con:
            item = row_data(con, "inspirations", ident)
            check_revision(item, data.expected_revision)
            changes = data.model_dump(exclude_none=True, exclude={"expected_revision"})
            if changes.get("active") and item["asset_sha"]:
                asset = row_data(con, "assets", item["asset_sha"])
                if asset.get("storage_status") in {"purged", "purge_failed"}:
                    raise Problem(409, "图片字节已清理；重新导入相同图片后才可恢复")
            item.update(changes)
            item.update(revision=item["revision"] + 1, updated_at=now(), removed_at=None if item["active"] else now())
            con.execute("UPDATE inspirations SET active=?,data=? WHERE id=?", (int(item["active"]), encode(item), ident))
            self.db.event(con, None, ident, "inspiration.updated", changes)
            return self._decorate_inspiration(con, item)

    def use_inspiration(self, ident: str, project_id: str, revision: int) -> dict:
        # The membership check and link creation share a writer transaction. A
        # concurrent remove/recycle cannot slip between revision check and use.
        with self.db.transaction() as con:
            item = row_data(con, "inspirations", ident)
            check_revision(item, revision)
            project = row_data(con, "projects", project_id)
            if not item["active"] or not self._asset_exists(con, item):
                raise Problem(409, "请先恢复可用的收藏图片")
            existing = con.execute("SELECT id FROM refs WHERE project_id=? AND asset_sha=?", (project_id, item["asset_sha"])).fetchone()
            if existing:
                return {"created": False, "preserved_existing_choice": True,
                        "reference": self._decorate(con, row_data(con, "refs", existing[0]), project)}
            source = {**item["source"], "source_confirmed": False, "search_query": "", "search_category": ""}
            data = CandidateInput(asset_sha=item["asset_sha"], title=item["title"], source=Source(**source))
            ref = self._insert_reference(con, project, data, "keep", "human_reuse")
            self.db.event(con, project_id, ref["id"], "project.asset_reused", {"inspiration_id": ident, "asset_sha": item["asset_sha"]})
            return {"created": True, "preserved_existing_choice": False, "reference": self._decorate(con, ref, project)}

    def asset_context(self, sha: str) -> dict:
        with self.db.read() as con:
            asset = row_data(con, "assets", sha)
            return {"asset": asset,
                    "discoveries": [json.loads(r[0]) for r in con.execute("SELECT data FROM discoveries WHERE asset_sha=? ORDER BY rowid", (sha,))],
                    "observations": [json.loads(r[0]) for r in con.execute("SELECT data FROM asset_observations WHERE asset_sha=? ORDER BY rowid DESC", (sha,))],
                    "project_uses": [dict(r) for r in con.execute("SELECT id,project_id,decision,json_extract(data,'$.lane') AS lane FROM refs WHERE asset_sha=?", (sha,))]}

    def record_collection_report(self, ident: str, report: CollectionReport) -> dict:
        with self.db.transaction() as con:
            job = row_data(con, "jobs", ident)
            if job["kind"] != "collection" or job["status"] == "cancelled":
                raise Problem(409, "不是可接收回执的采集任务")
            if job["status"] == "succeeded":
                if job.get("execution_report") == report.model_dump(): return job
                raise Problem(409, "任务已完成，不能覆盖旧执行回执")
            job["execution_report"] = report.model_dump()
            status = {"completed": "succeeded", "blocked": "blocked", "failed": "failed"}[report.status]
            if status == "succeeded" and not job["imported_ids"]:
                status = "blocked"
            job.update(status=status, detail=report.summary if job["imported_ids"] else "未收到有效候选；" + report.summary)
            return self._save_job(con, job, "collection.reported", report.model_dump(), "agent")
