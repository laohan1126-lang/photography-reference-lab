"""Application use cases shared by the API, migration CLI, and local workers."""
from __future__ import annotations

import json
import sqlite3
from pathlib import Path
from uuid import uuid4
from typing import Any
from .config import Settings
from .db import Database, encode, now
from .models import (CandidateInput, ProjectInput, ReferenceEdit, Source, VisualReview, Card,
                     AnalysisResult, NoteInput, JobInput)
from .storage import AssetStore
from .policy import (MESSAGES, acceptance_digest, blockers, context_digest, digest, state_for)


class Problem(Exception):
    def __init__(self, status: int, message: str, details: Any = None):
        self.status, self.message, self.details = status, message, details
        super().__init__(message)


def fresh_id() -> str:
    return uuid4().hex


def row_data(con: sqlite3.Connection, table: str, ident: str) -> dict:
    if table not in {"projects", "assets", "refs", "jobs", "notes"}:
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
        metadata = self.assets.ingest(content, filename)
        with self.db.transaction() as con:
            con.execute("INSERT OR IGNORE INTO assets VALUES(?,?)", (metadata["id"], encode(metadata)))
            return row_data(con, "assets", metadata["id"])

    def asset(self, sha: str) -> dict:
        with self.db.read() as con:
            return row_data(con, "assets", sha)

    def _asset_exists(self, con: sqlite3.Connection, ref: dict) -> bool:
        if not ref.get("asset_sha"):
            return False
        asset = row_data(con, "assets", ref["asset_sha"])
        return asset.get("integrity", "ok") == "ok" and self.assets.path(asset).is_file()

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
        return result

    def reference(self, ident: str) -> dict:
        with self.db.read() as con:
            return self._decorate(con, row_data(con, "refs", ident))

    def add_candidate(self, project_id: str, data: CandidateInput, *, decision: str = "pending", actor: str = "import") -> dict:
        with self.db.transaction() as con:
            project = row_data(con, "projects", project_id)
            if data.asset_sha:
                row_data(con, "assets", data.asset_sha)
            job = row_data(con, "jobs", data.job_id) if data.job_id else None
            if job and (job["project_id"] != project_id or job["kind"] != "collection" or job["status"] in {"succeeded", "cancelled"}):
                raise Problem(409, "Candidate does not belong to an open collection job")
            alias = con.execute("SELECT ref_id FROM aliases WHERE project_id=? AND import_key=?",
                                (project_id, data.import_key)).fetchone() if data.import_key else None
            existing = row_data(con, "refs", alias[0]) if alias else None
            if existing and existing["asset_sha"] != data.asset_sha:
                raise Problem(409, "Same import key points to changed image bytes; use explicit replace")
            if not existing and data.asset_sha:
                hit = con.execute("SELECT id FROM refs WHERE project_id=? AND asset_sha=?", (project_id, data.asset_sha)).fetchone()
                existing = row_data(con, "refs", hit[0]) if hit else None
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
                ref = {"id": fresh_id(), "project_id": project_id, "asset_sha": data.asset_sha,
                       "title": data.title or data.source.title or "未命名参考", "source": data.source.model_dump(),
                       "discovered_sources": [data.source.model_dump()], "legacy_notes": data.legacy_notes,
                       "decision": decision, "lane": "field", "preference": "", "borrow": [], "allow_cross_domain": False,
                       "review": None, "review_actor": "", "review_producer": "", "card": None, "card_context": "",
                       "card_producer": "", "accepted_fingerprint": None, "reflections": [], "revision": 1,
                       "created_at": now(), "updated_at": now()}
                ref["state"] = state_for(ref, project, self._asset_exists(con, ref))
                con.execute("INSERT INTO refs VALUES(?,?,?,?,?,?)",
                            (ref["id"], project_id, data.asset_sha, decision, ref["state"], encode(ref)))
                self.db.event(con, project_id, ref["id"], "candidate.imported", {"source": data.source.model_dump(), "decision": decision}, actor)
                created = True
            if data.import_key:
                con.execute("INSERT OR IGNORE INTO aliases VALUES(?,?,?)", (project_id, data.import_key, ref["id"]))
            if job and ref["id"] not in job["imported_ids"]:
                job["imported_ids"].append(ref["id"])
                self._save_job(con, job, "collection.imported", {"reference_id": ref["id"]}, actor)
            return {"created": created, "reference": self._decorate(con, ref, project)}

    def references(self, project_id: str, *, limit: int = 60, offset: int = 0, query: str = "",
                   decision: str = "", state: str = "", lane: str = "", kind: str = "") -> dict:
        clauses, args = ["project_id=?"], [project_id]
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
            return result

    def edit_reference(self, ident: str, data: ReferenceEdit) -> dict:
        changes = data.model_dump(exclude_none=True, exclude={"expected_revision"})
        with self.db.transaction() as con:
            ref = row_data(con, "refs", ident)
            project = row_data(con, "projects", ref["project_id"])
            check_revision(ref, data.expected_revision)
            if changes:
                ref.update(changes)
                ref["accepted_fingerprint"] = None
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
            self._save(con, ref, project, "analysis.imported", {"producer": producer, "result": result.model_dump(), "job_id": job_id}, "ai")
            if job_id and ident not in job["completed_ids"]:
                job["completed_ids"].append(ident)
                self._save_job(con, job, "analysis.completed_item", {"reference_id": ident}, "ai")
            return self._decorate(con, ref, project)

    def accept_card(self, ident: str, revision: int) -> dict:
        with self.db.transaction() as con:
            ref = row_data(con, "refs", ident)
            project = row_data(con, "projects", ref["project_id"])
            check_revision(ref, revision)
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
            ref.update(asset_sha=sha, decision="pending", review=None, review_actor="", review_producer="", card=None,
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

    def add_note(self, project_id: str, note: NoteInput) -> dict:
        fingerprint = digest(note.model_dump())
        with self.db.transaction() as con:
            row_data(con, "projects", project_id)
            previous = con.execute("SELECT data FROM notes WHERE project_id=? AND fingerprint=?", (project_id, fingerprint)).fetchone()
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

    def notes(self, project_id: str) -> list[dict]:
        with self.db.read() as con:
            row_data(con, "projects", project_id)
            return [json.loads(r[0]) for r in con.execute("SELECT data FROM notes WHERE project_id=? ORDER BY rowid DESC", (project_id,))]

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
            job = {"id": fresh_id(), "project_id": project_id, "kind": request.kind, "status": "blocked", "revision": 1,
                   "detail": "等待本地执行器或人工导入；尚未执行搜索／分析", "notes": request.notes,
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

    def jobs(self, project_id: str) -> list[dict]:
        with self.db.read() as con:
            row_data(con, "projects", project_id)
            return [json.loads(r[0]) for r in con.execute("SELECT data FROM jobs WHERE project_id=? ORDER BY rowid DESC", (project_id,))]

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
        job = self.job(ident)
        project = self.project(job["project_id"])
        refs = [self.reference(x) for x in job["reference_ids"]]
        return {"schema_version": 1, "job": job, "project": project, "references": refs,
                "rules": ["Search queries are discovery hints, never image classifications.",
                          "Preserve received image bytes and original post provenance; no cookie/token exports or access bypass.",
                          "Inspect each selected image separately; never infer poses from titles or contact sheets.",
                          "Return null card for irrelevant or uncertain images. All generated cards remain drafts."]}
