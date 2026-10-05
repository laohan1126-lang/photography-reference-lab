"""Asset-first discovery. Navigation annotations never grant review/card acceptance."""
from __future__ import annotations

import json
from collections import defaultdict
from uuid import uuid4

from fastapi import Query
from pydantic import Field, field_validator

from .db import encode, now
from .policy import preflight_filter_sql, effective_preflight_filtered, trusted_producer_sql
from .models import Strict, Kind
from .service import Problem, row_data, ensure_active_project

FACETS = {
    "viewpoint": {"eye_level": "平视", "high_angle": "俯拍", "low_angle": "仰拍", "overhead": "顶视"},
    "framing": {"close_up": "特写", "half_body": "半身", "three_quarter": "大半身", "full_body": "全身", "environmental": "环境人像"},
    "pose": {"standing": "站姿", "seated": "坐姿", "kneeling": "跪姿", "lying": "卧姿", "turning": "转身／回眸", "walking": "行走"},
    "orientation": {"portrait": "竖幅", "landscape": "横幅", "square": "方形"},
}
ANNOTATION_KEYS = ("viewpoint", "framing", "pose")

# Additive extension tables, compatible with schema 3 and old clients. They do
# not rewrite any existing rows. SQLite backup/restore includes them unchanged.
SCHEMA = """
CREATE TABLE IF NOT EXISTS library_annotations (
 asset_sha TEXT PRIMARY KEY REFERENCES assets(id), revision INTEGER NOT NULL, data TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS library_saved_searches (
 id TEXT PRIMARY KEY, name TEXT NOT NULL UNIQUE, revision INTEGER NOT NULL, data TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS library_project_navigation (
 project_id TEXT PRIMARY KEY REFERENCES projects(id), pinned INTEGER NOT NULL DEFAULT 0, visited_at TEXT
);
CREATE INDEX IF NOT EXISTS library_ref_asset ON refs(asset_sha);
"""


class BrowseFilters(Strict):
    q: str = Field(default="", max_length=400)
    scope: str = "all"
    project_id: str = Field(default="", max_length=64)
    kind: str = ""
    viewpoint: str = ""
    framing: str = ""
    pose: str = ""
    orientation: str = ""

    @field_validator("scope")
    @classmethod
    def valid_scope(cls, value):
        if value not in {"all", "kept", "inspiration"}:
            raise ValueError("未知图库范围")
        return value

    @field_validator("kind")
    @classmethod
    def valid_kind(cls, value):
        from typing import get_args
        if value and value not in get_args(Kind):
            raise ValueError("未知图片类型")
        return value

    @field_validator("viewpoint", "framing", "pose", "orientation")
    @classmethod
    def valid_facet(cls, value, info):
        if value not in {"", "unknown", *FACETS[info.field_name]}:
            raise ValueError("未知摄影分类")
        return value


class PhotographyFacets(Strict):
    viewpoint: str = "unknown"
    framing: str = "unknown"
    pose: str = "unknown"

    @field_validator(*ANNOTATION_KEYS)
    @classmethod
    def valid_facet(cls, value, info):
        if value not in {"unknown", *FACETS[info.field_name]}:
            raise ValueError("未知摄影分类")
        return value


class AnnotationInput(PhotographyFacets):
    expected_revision: int = Field(ge=0)


class SearchInput(Strict):
    name: str = Field(min_length=1, max_length=80)
    filters: BrowseFilters


class PinInput(Strict):
    pinned: bool


class LibraryBrowser:
    def __init__(self, library):
        self.library = library
        self.db = library.db
        with self.db.transaction() as con:
            for statement in SCHEMA.split(";"):
                if statement.strip():
                    con.execute(statement)

    @staticmethod
    def _annotation(row=None):
        if row:
            return json.loads(row["data"])
        return {"revision": 0, **{key: "unknown" for key in ANNOTATION_KEYS}, "actor": None}

    def annotate(self, sha, data):
        with self.db.transaction() as con:
            asset = row_data(con, "assets", sha)
            if asset.get("storage_status") in {"purged", "purge_failed"}:
                raise Problem(409, "图片已清理，不能根据缺失图片分类")
            if not self.library.assets.path(asset).is_file():
                raise Problem(409, "原图缺失，请先恢复图片")
            old = self._annotation(con.execute("SELECT data FROM library_annotations WHERE asset_sha=?", (sha,)).fetchone())
            if old["revision"] != data.expected_revision:
                raise Problem(409, "分类已被其他窗口修改，请重新打开后再保存")
            item = {**data.model_dump(exclude={"expected_revision"}), "revision": old["revision"] + 1,
                    "actor": "human", "updated_at": now()}
            con.execute("INSERT INTO library_annotations VALUES(?,?,?) ON CONFLICT(asset_sha) DO UPDATE SET revision=excluded.revision,data=excluded.data",
                        (sha, item["revision"], encode(item)))
            self.db.event(con, None, sha, "library.annotation_updated", {"before": old, "after": item})
            return item

    def browse(self, filters, limit=60, offset=0):
        if not 1 <= limit <= 100 or offset < 0:
            raise ValueError("分页参数无效")
        f = filters
        # A scope predicate applies to the SAME reference. In particular, keep
        # in project B must not make a pending reference in project A a keep.
        eligible = ["r.decision <> 'reject'", "COALESCE(json_extract(r.data,'$.detached_at'),'')=''",
                    f"NOT {preflight_filter_sql('r.data')}",
                    "COALESCE(json_extract(p.data,'$.archived_at'),'')=''"]
        params = []
        if f.project_id:
            eligible.append("r.project_id=?")
            params.append(f.project_id)
        if f.scope == "kept":
            eligible += ["r.decision='keep'", "json_extract(r.data,'$.lane')='field'"]
        cte = "WITH eligible AS (SELECT r.*,p.data AS project_data FROM refs r JOIN projects p ON p.id=r.project_id WHERE " + " AND ".join(eligible) + ") "
        joins = f""" FROM assets a
 LEFT JOIN inspirations i ON i.asset_sha=a.id AND i.active=1
 LEFT JOIN library_annotations n ON n.asset_sha=a.id
 LEFT JOIN asset_observations o ON o.rowid=(SELECT MAX(ob.rowid) FROM asset_observations ob WHERE ob.asset_sha=a.id AND json_extract(ob.data,'$.facts.asset_sha')=a.id AND json_extract(ob.data,'$.actor') IN ('human','ai') AND {trusted_producer_sql('producer', 'ob.data')})
"""
        exists = "EXISTS(SELECT 1 FROM eligible e WHERE e.asset_sha=a.id)"
        if f.scope == "inspiration":
            membership = "i.id IS NOT NULL" + (" AND " + exists if f.project_id else "")
        elif f.scope == "kept" or f.project_id:
            membership = exists
        else:
            membership = f"({exists} OR i.id IS NOT NULL)"
        where = [f"({membership})", "COALESCE(json_extract(a.data,'$.storage_status'),'available') NOT IN ('purged','purge_failed')"]
        if f.q:
            needle = f.q.lower()
            where.append("""(EXISTS(SELECT 1 FROM eligible e WHERE e.asset_sha=a.id AND
 instr(lower(COALESCE(json_extract(e.data,'$.title'),'')||' '||COALESCE(json_extract(e.data,'$.source.author'),'')||' '||COALESCE(json_extract(e.data,'$.preference'),'')||' '||COALESCE(json_extract(e.project_data,'$.character'),'')||' '||COALESCE(json_extract(e.project_data,'$.costume'),'')),?)>0)
 OR instr(lower(COALESCE(json_extract(i.data,'$.title'),'')||' '||COALESCE(json_extract(i.data,'$.preference'),'')),?)>0)""")
            params.extend([needle, needle])
        if f.kind:
            where.append("COALESCE(json_extract(o.data,'$.facts.kind'),'unknown')=?")
            params.append(f.kind)
        for key in ANNOTATION_KEYS:
            value = getattr(f, key)
            if value:
                where.append(f"COALESCE(json_extract(n.data,'$.{key}'),'unknown')=?")
                params.append(value)
        orientation = "CASE WHEN json_extract(a.data,'$.width')>json_extract(a.data,'$.height') THEN 'landscape' WHEN json_extract(a.data,'$.width')<json_extract(a.data,'$.height') THEN 'portrait' WHEN json_extract(a.data,'$.width')=json_extract(a.data,'$.height') THEN 'square' ELSE 'unknown' END"
        if f.orientation:
            where.append(orientation + "=?")
            params.append(f.orientation)
        query = joins + " WHERE " + " AND ".join(where)
        with self.db.read() as con:
            con.execute("BEGIN")  # count, page and use metadata share one snapshot
            if f.project_id:
                ensure_active_project(row_data(con, "projects", f.project_id))
            total = con.execute(cte + "SELECT COUNT(*)" + query, params).fetchone()[0]
            offset = min(offset, ((total - 1) // limit) * limit) if total else 0
            rows = con.execute(cte + "SELECT a.id,a.data,n.data AS annotation,i.data AS inspiration,o.data AS observation," + orientation + " AS orientation" + query + " ORDER BY a.rowid DESC,a.id LIMIT ? OFFSET ?", (*params, limit, offset)).fetchall()
            by_asset = defaultdict(list)
            if rows:
                marks = ",".join("?" for _ in rows)
                uses = con.execute(f"SELECT r.*,p.data AS project_data FROM refs r JOIN projects p ON p.id=r.project_id WHERE r.asset_sha IN ({marks}) AND COALESCE(json_extract(p.data,'$.archived_at'),'')='' AND COALESCE(json_extract(r.data,'$.detached_at'),'')='' ORDER BY r.rowid DESC", [r["id"] for r in rows])
                for row in uses:
                    ref, project = json.loads(row["data"]), json.loads(row["project_data"])
                    by_asset[row["asset_sha"]].append({"id": ref["id"], "project_id": project["id"], "character": project["character"], "costume": project.get("costume", ""), "title": ref["title"], "decision": ref["decision"], "lane": ref.get("lane", "field"), "filtered": effective_preflight_filtered(ref)})
            items = []
            for row in rows:
                asset = json.loads(row["data"])
                saved = json.loads(row["inspiration"]) if row["inspiration"] else None
                observation = json.loads(row["observation"]) if row["observation"] else {}
                uses = by_asset[row["id"]]
                preferred = next((u for u in uses if u["decision"] != "reject" and not u["filtered"] and (not f.project_id or u["project_id"] == f.project_id) and (f.scope != "kept" or (u["decision"] == "keep" and u["lane"] == "field"))), None)
                title = preferred["title"] if preferred else (saved or {}).get("title", "未命名图片")
                items.append({"id": row["id"], "asset_sha": row["id"], "asset": asset, "title": title,
                              "uses": uses, "inspiration_id": saved["id"] if saved else None,
                              "file_available": self.library.assets.path(asset).is_file(),
                              "kind": observation.get("facts", {}).get("kind", "unknown"), "kind_actor": observation.get("actor"),
                              "orientation": row["orientation"],
                              "annotation": json.loads(row["annotation"]) if row["annotation"] else self._annotation()})
            return {"items": items, "total": total, "offset": offset, "limit": limit, "filters": f.model_dump()}

    def searches(self):
        with self.db.read() as con:
            return [json.loads(r[0]) for r in con.execute("SELECT data FROM library_saved_searches ORDER BY rowid DESC")]

    def save_search(self, data):
        with self.db.transaction() as con:
            if con.execute("SELECT 1 FROM library_saved_searches WHERE name=?", (data.name,)).fetchone():
                raise Problem(409, "已有同名常用搜索，请换个名字或先删除旧搜索")
            if con.execute("SELECT COUNT(*) FROM library_saved_searches").fetchone()[0] >= 40:
                raise Problem(409, "最多保存 40 个常用搜索，请先整理旧搜索")
            if data.filters.project_id:
                ensure_active_project(row_data(con, "projects", data.filters.project_id))
            item = {"id": uuid4().hex, "name": data.name, "revision": 1, "filters": data.filters.model_dump(), "created_at": now()}
            con.execute("INSERT INTO library_saved_searches VALUES(?,?,?,?)", (item["id"], item["name"], 1, encode(item)))
            self.db.event(con, None, item["id"], "library.search_saved", item)
            return item

    def delete_search(self, ident, revision):
        with self.db.transaction() as con:
            row = con.execute("SELECT revision FROM library_saved_searches WHERE id=?", (ident,)).fetchone()
            if not row:
                raise Problem(404, "常用搜索不存在")
            if row[0] != revision:
                raise Problem(409, "常用搜索已改变，请刷新重试")
            con.execute("DELETE FROM library_saved_searches WHERE id=?", (ident,))
            self.db.event(con, None, ident, "library.search_deleted", {})
            return {"deleted": True}

    def navigation(self):
        with self.db.read() as con:
            rows = con.execute("SELECT n.* FROM library_project_navigation n JOIN projects p ON p.id=n.project_id WHERE COALESCE(json_extract(p.data,'$.archived_at'),'')='' ORDER BY n.visited_at DESC,n.project_id").fetchall()
            return {"pinned_ids": [r["project_id"] for r in rows if r["pinned"]],
                    "recent_ids": [r["project_id"] for r in rows if r["visited_at"]][:8]}

    def navigate_project(self, ident, pinned=None):
        with self.db.transaction() as con:
            ensure_active_project(row_data(con, "projects", ident))
            con.execute("INSERT OR IGNORE INTO library_project_navigation(project_id) VALUES(?)", (ident,))
            if pinned is None:
                con.execute("UPDATE library_project_navigation SET visited_at=? WHERE project_id=?", (now(), ident))
            else:
                count = con.execute("SELECT COUNT(*) FROM library_project_navigation n JOIN projects p ON p.id=n.project_id WHERE pinned=1 AND n.project_id<>? AND COALESCE(json_extract(p.data,'$.archived_at'),'')=''", (ident,)).fetchone()[0]
                if pinned and count >= 8:
                    raise Problem(409, "最多置顶 8 个项目；其他项目仍可搜索打开")
                con.execute("UPDATE library_project_navigation SET pinned=? WHERE project_id=?", (int(pinned), ident))
        return self.navigation()


def install_browser_routes(app):
    browser = LibraryBrowser(app.state.library)
    app.state.library_browser = browser

    @app.get("/api/library/facets")
    def facets():
        return {"facets": FACETS, "annotation_keys": ANNOTATION_KEYS}

    @app.get("/api/library/assets")
    def assets(q: str = Query("", max_length=400), scope: str = "all", project_id: str = "", kind: str = "",
               viewpoint: str = "", framing: str = "", pose: str = "", orientation: str = "",
               limit: int = Query(60, ge=1, le=100), offset: int = Query(0, ge=0)):
        return browser.browse(BrowseFilters(q=q, scope=scope, project_id=project_id, kind=kind, viewpoint=viewpoint, framing=framing, pose=pose, orientation=orientation), limit, offset)

    @app.put("/api/library/assets/{sha}/annotation")
    def annotate(sha: str, data: AnnotationInput):
        return browser.annotate(sha, data)

    @app.get("/api/library/searches")
    def searches():
        return browser.searches()

    @app.post("/api/library/searches", status_code=201)
    def save_search(data: SearchInput):
        return browser.save_search(data)

    @app.delete("/api/library/searches/{ident}")
    def delete_search(ident: str, expected_revision: int = Query(..., ge=1)):
        return browser.delete_search(ident, expected_revision)

    @app.get("/api/library/navigation")
    def navigation():
        return browser.navigation()

    @app.post("/api/library/projects/{ident}/visit")
    def visit(ident: str):
        return browser.navigate_project(ident)

    @app.put("/api/library/projects/{ident}/pin")
    def pin(ident: str, data: PinInput):
        return browser.navigate_project(ident, data.pinned)
