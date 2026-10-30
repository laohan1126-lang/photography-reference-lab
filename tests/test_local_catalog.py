from __future__ import annotations

import hashlib
import json
import os
import sqlite3
from html.parser import HTMLParser
from pathlib import Path
from urllib.parse import unquote, urlsplit

from PIL import Image

from ref_lab.local_catalog import refresh_catalog


def image_bytes(color: str) -> bytes:
    from io import BytesIO
    output = BytesIO()
    Image.new("RGB", (32, 40), color).save(output, "PNG")
    return output.getvalue()


def write(path: Path, data: bytes) -> str:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(data)
    return hashlib.sha256(data).hexdigest()


def compressed_has(payload: dict, sha: str) -> bool:
    return any(item.get("sha") == sha for item in payload.get("items", []))


class ImageSources(HTMLParser):
    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.sources: list[str] = []

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        if tag.casefold() != "img":
            return
        values = dict(attrs)
        if values.get("src"):
            self.sources.append(values["src"] or "")


class RelativeLinks(HTMLParser):
    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.links: list[str] = []

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        values = dict(attrs)
        for attribute in ("src", "href"):
            value = values.get(attribute)
            if value and not urlsplit(value).scheme:
                self.links.append(value)


def assert_page_images_decode(output: Path, page: Path, minimum: int) -> int:
    parser = ImageSources()
    parser.feed(page.read_text(encoding="utf-8"))
    assert parser.sources
    if minimum:
        assert len(parser.sources) >= minimum
    root = output.resolve()
    for source in parser.sources:
        parsed = urlsplit(source)
        assert not parsed.scheme and not parsed.netloc and not parsed.query
        target = (page.parent / unquote(parsed.path)).resolve()
        assert target.is_relative_to(root)
        assert target.is_file() and not target.is_symlink()
        with Image.open(target) as image:
            assert getattr(image, "n_frames", 1) == 1
            image.verify()
    return len(parser.sources)


def assert_relative_links_resolve(output: Path, page: Path) -> None:
    parser = RelativeLinks()
    parser.feed(page.read_text(encoding="utf-8"))
    assert parser.links
    root = output.resolve()
    for link in parser.links:
        parsed = urlsplit(link)
        assert not parsed.scheme and not parsed.netloc and not parsed.query and not parsed.fragment
        target = (page.parent / unquote(parsed.path)).resolve()
        assert target.is_relative_to(root)
        assert target.is_file()


def make_db(root: Path, known_sha: str, missing_sha: str) -> Path:
    data_dir = root / "data"
    data_dir.mkdir(exist_ok=True)
    db = data_dir / "library.sqlite3"
    with sqlite3.connect(db) as con:
        con.executescript("""
        CREATE TABLE projects(id TEXT PRIMARY KEY,data TEXT NOT NULL);
        CREATE TABLE assets(id TEXT PRIMARY KEY,data TEXT NOT NULL);
        CREATE TABLE refs(id TEXT PRIMARY KEY,project_id TEXT,asset_sha TEXT,decision TEXT,state TEXT,data TEXT);
        CREATE TABLE inspirations(id TEXT PRIMARY KEY,asset_sha TEXT,active INTEGER,data TEXT);
        CREATE TABLE study_candidates(id TEXT PRIMARY KEY,batch_id TEXT,asset_sha TEXT,status TEXT,data TEXT);
        CREATE TABLE jobs(id TEXT PRIMARY KEY,project_id TEXT,kind TEXT,status TEXT,data TEXT);
        """)
        projects = {
            "p-yo": {"id": "p-yo", "character": "渡辺曜", "work": "Sunshine", "archived_at": None},
            "p-old": {"id": "p-old", "character": "旧角色", "archived_at": "2026-01-01"},
        }
        for ident, item in projects.items():
            con.execute("INSERT INTO projects VALUES(?,?)", (ident, json.dumps(item, ensure_ascii=False)))
        assets = {known_sha: {"id": known_sha, "ext": "png", "received_name": "原图.png"},
                  missing_sha: {"id": missing_sha, "ext": "png", "received_name": "丢失.png"}}
        for ident, item in assets.items():
            con.execute("INSERT INTO assets VALUES(?,?)", (ident, json.dumps(item, ensure_ascii=False)))
        for ident, project, sha, decision, detached in (
                ("r1", "p-yo", known_sha, "pending", False),
                ("r2", "p-old", known_sha, "reject", True)):
            data = {"title": "共同图片", "detached_at": "2026-01-02" if detached else None}
            con.execute("INSERT INTO refs VALUES(?,?,?,?,?,?)",
                        (ident, project, sha, decision, "detached" if detached else "candidate", json.dumps(data)))
        con.execute("INSERT INTO inspirations VALUES(?,?,?,?)",
                    ("fav", known_sha, 1, json.dumps({"title": "收藏"})))
        con.execute("INSERT INTO study_candidates VALUES(?,?,?,?,?)",
                    ("dot:1", "batch", known_sha, "pending", json.dumps({"title": "学习"})))
        job = {"id": "job-history", "status": "blocked"}
        con.execute("INSERT INTO jobs VALUES(?,?,?,?,?)",
                    ("job-history", "p-yo", "collection", "blocked", json.dumps(job)))
    return db


def test_catalog_is_read_only_repeatable_and_keeps_historical_runs(tmp_path: Path):
    root = tmp_path / "repo"
    root.mkdir()
    (root / ".local").mkdir()
    known = image_bytes("red")
    known_sha = hashlib.sha256(known).hexdigest()
    missing_sha = "f" * 64
    db = make_db(root, known_sha, missing_sha)
    db_before = hashlib.sha256(db.read_bytes()).hexdigest()
    cas = root / "data" / "assets" / known_sha[:2] / known_sha / "original.png"
    write(cas, known)

    job_root = root / ".local" / "collection-runs" / "job-history"
    historical = job_root / "archive-failed"
    historical.mkdir(parents=True)
    history_bytes = image_bytes("blue")
    history_sha = write(historical / "images" / "historical.png", history_bytes)
    (historical / "received.json").write_text(json.dumps([{
        "asset_sha": history_sha, "original_path": str(historical / "images" / "historical.png"),
        "title": "历史未导入图片"}]), encoding="utf-8")
    current = job_root / "current"
    stray_bytes = image_bytes("green")
    stray_path = current / "images" / "unlisted.png"
    write(stray_path, stray_bytes)

    staging = root / "staging" / "extra.png"
    extra_bytes = image_bytes("yellow")
    extra_sha = write(staging, extra_bytes)
    outside = root.parent / "outside.png"
    outside_sha = write(outside, image_bytes("black"))
    inventory = root / "inventory.json"
    inventory.write_text(json.dumps({
        "schema": 1, "root": str(root), "generated_at": "2026-10-29T00:00:00Z", "directories": [],
        "extra_images": [
            {"path": str(staging), "sha256": extra_sha, "bytes": len(extra_bytes), "source_hint": "staging", "category": "unknown"},
            {"path": str(cas), "sha256": known_sha, "bytes": len(known), "source_hint": "same", "category": "unknown"},
            {"path": str(outside), "sha256": outside_sha, "bytes": len(image_bytes("black")), "source_hint": "escape", "category": "unknown"},
        ], "errors": []
    }, ensure_ascii=False), encoding="utf-8")

    output = root / "data" / "我的参考图"
    source_roots = (root / "data" / "assets",)
    report = refresh_catalog(repo_root=root, data_dir=root / "data", inventory=inventory, source_roots=source_roots)
    assert report["projects"] == 2
    assert report["unknown"] >= 2
    assert hashlib.sha256(db.read_bytes()).hexdigest() == db_before
    manifest = json.loads((output / "manifest.json").read_text(encoding="utf-8"))
    items = {item["sha"]: item for item in manifest["items"]}
    assert history_sha in items
    assert hashlib.sha256(stray_path.read_bytes()).hexdigest() in items
    assert extra_sha in items
    assert missing_sha in items and items[missing_sha]["status"] == "原件缺失"
    assert outside_sha not in items
    known_item = items[known_sha]
    assert len([r for r in known_item["relations"] if r["kind"] == "project"]) == 2
    assert any(r["kind"] == "favorite" for r in known_item["relations"])
    assert any(r["kind"] == "scattered" for r in known_item["relations"])
    preview = output / known_item["browse_path"]
    assert preview.read_bytes()[:2] == b"\xff\xd8"
    assert preview.read_bytes() != known
    assert not os.path.samefile(cas, preview)
    yo_page = output / "角色项目" / "渡边曜（渡辺曜）" / "index.html"
    assert yo_page.is_file()
    assert "渡边曜" in yo_page.read_text(encoding="utf-8") and "渡辺曜" in yo_page.read_text(encoding="utf-8")
    assert len(list((yo_page.parent).glob("*.jpg"))) >= 2
    assert len(list((output / "其他" / "未分类（待归属）").glob("*.jpg"))) >= 1
    assert len(list((output / "其他" / "全局收藏").glob("*.jpg"))) >= 1
    mixed = output / "images" / "用户自行放入.txt"
    mixed.write_text("keep", encoding="utf-8")
    preview_hash = hashlib.sha256(preview.read_bytes()).hexdigest()
    refresh_catalog(repo_root=root, data_dir=root / "data")
    assert mixed.read_text(encoding="utf-8") == "keep"
    assert hashlib.sha256(preview.read_bytes()).hexdigest() == preview_hash
    refreshed = json.loads((output / "manifest.json").read_text(encoding="utf-8"))
    assert compressed_has(refreshed, extra_sha)
    assert refreshed["inventory"]["path"] == str(inventory.resolve())
    assert not any(error["kind"] == "inventory_unsafe" and outside_sha in json.dumps(error) for error in
                   json.loads((output / "manifest.json").read_text(encoding="utf-8"))["errors"])


def test_inventory_root_cannot_escape_repo(tmp_path: Path):
    root = tmp_path / "repo"
    (root / "data").mkdir(parents=True)
    make_db(root, "a" * 64, "b" * 64)
    outside = tmp_path / "outside"
    outside.mkdir()
    (outside / "images").mkdir()
    payload = {"schema": 1, "root": str(outside), "generated_at": "x", "directories": [], "extra_images": [], "errors": []}
    inventory = root / "inventory.json"
    inventory.write_text(json.dumps(payload), encoding="utf-8")
    import pytest
    with pytest.raises(ValueError, match="root"):
        refresh_catalog(repo_root=root, data_dir=root / "data", inventory=inventory)


def test_output_rejects_protected_and_nonempty_foreign(tmp_path: Path):
    root = tmp_path / "repo"
    (root / "data").mkdir(parents=True)
    make_db(root, "a" * 64, "b" * 64)
    import pytest
    with pytest.raises(ValueError, match="专用子目录"):
        refresh_catalog(repo_root=root, data_dir=root / "data", output=root / "data")
    foreign = root / "data" / "foreign"
    foreign.mkdir()
    (foreign / "mine.txt").write_text("keep", encoding="utf-8")
    with pytest.raises(ValueError, match="非空"):
        refresh_catalog(repo_root=root, data_dir=root / "data", output=foreign)
    assert (foreign / "mine.txt").read_text(encoding="utf-8") == "keep"


def test_unlisted_run_preview_survives_two_refreshes(tmp_path: Path):
    root = tmp_path / "repo"
    (root / "data").mkdir(parents=True)
    make_db(root, "a" * 64, "b" * 64)
    with sqlite3.connect(root / "data" / "library.sqlite3") as con:
        con.execute("INSERT INTO jobs VALUES(?,?,?,?,?)",
                    ("job-repeat", "p-yo", "collection", "succeeded", json.dumps({"id": "job-repeat"})))
    run = root / ".local" / "collection-runs" / "job-repeat" / "current"
    image = run / "images" / "unlisted.png"
    write(image, image_bytes("green"))
    (run / "received.json").write_text("[]", encoding="utf-8")
    output = root / "data" / "我的参考图"

    first = refresh_catalog(repo_root=root, data_dir=root / "data")
    first_manifest = json.loads((output / "manifest.json").read_text(encoding="utf-8"))
    first_item = next(item for item in first_manifest["items"] if item["sha"] == hashlib.sha256(image_bytes("green")).hexdigest())
    central = first_item["browse_path"]
    role = (Path("角色项目") / "渡边曜（渡辺曜）" / Path(central).name).as_posix()
    assert first["ok"] is True
    assert central in first_manifest["owned_files"]
    assert role in first_manifest["owned_files"]

    second = refresh_catalog(repo_root=root, data_dir=root / "data")
    second_manifest = json.loads((output / "manifest.json").read_text(encoding="utf-8"))
    second_item = next(item for item in second_manifest["items"] if item["sha"] == first_item["sha"])
    assert second["ok"] is True, second["errors"]
    assert second_item["browse_path"] == central
    assert (output / role).is_file()
    assert second_item["preview_sha256"] == first_item["preview_sha256"]


def test_role_favorite_and_unknown_subpages_render_decodable_images(tmp_path: Path):
    root = tmp_path / "repo"
    (root / "data").mkdir(parents=True)
    known = image_bytes("red")
    known_sha = hashlib.sha256(known).hexdigest()
    make_db(root, known_sha, "f" * 64)
    write(root / "data" / "assets" / known_sha[:2] / known_sha / "original.png", known)
    with sqlite3.connect(root / "data" / "library.sqlite3") as con:
        con.execute("INSERT INTO jobs VALUES(?,?,?,?,?)",
                    ("job-page", "p-yo", "collection", "succeeded", json.dumps({"id": "job-page"})))
    run = root / ".local" / "collection-runs" / "job-page" / "current"
    unlisted = run / "images" / "unlisted.png"
    write(unlisted, image_bytes("green"))
    (run / "received.json").write_text("[]", encoding="utf-8")
    staging = root / "staging" / "unknown.png"
    unknown = image_bytes("yellow")
    unknown_sha = write(staging, unknown)
    inventory = root / "inventory.json"
    inventory.write_text(json.dumps({
        "schema": 1, "root": str(root), "generated_at": "x", "directories": [],
        "extra_images": [{"path": str(staging), "sha256": unknown_sha,
                           "bytes": len(unknown), "source_hint": "staging", "category": "unknown"}],
        "errors": [],
    }, ensure_ascii=False), encoding="utf-8")

    result = refresh_catalog(repo_root=root, data_dir=root / "data", inventory=inventory)
    assert result["ok"] is True, result["errors"]
    output = root / "data" / "我的参考图"
    manifest = json.loads((output / "manifest.json").read_text(encoding="utf-8"))
    role_page = output / "角色项目" / "渡边曜（渡辺曜）" / "index.html"
    favorite_page = output / "其他" / "全局收藏" / "index.html"
    unknown_page = output / "其他" / "未分类（待归属）" / "index.html"
    assert_page_images_decode(output, role_page, 2)
    assert_page_images_decode(output, favorite_page, 1)
    assert_page_images_decode(output, unknown_page, 1)
    role_item = next(item for item in manifest["items"] if item["sha"] == known_sha)
    assert role_item["role_paths"]["角色项目/渡边曜（渡辺曜）"]


def test_html_local_urls_encode_reserved_characters_without_double_encoding(tmp_path: Path):
    root = tmp_path / "repo"
    (root / "data").mkdir(parents=True)
    known = image_bytes("red")
    known_sha = hashlib.sha256(known).hexdigest()
    make_db(root, known_sha, "f" * 64)
    with sqlite3.connect(root / "data" / "library.sqlite3") as con:
        ref = json.loads(con.execute("SELECT data FROM refs WHERE id='r1'").fetchone()[0])
        ref["title"] = "【动作#01】可以给点建议吗 100%"
        con.execute("UPDATE refs SET data=? WHERE id='r1'", (json.dumps(ref, ensure_ascii=False),))
        project = json.loads(con.execute("SELECT data FROM projects WHERE id='p-yo'").fetchone()[0])
        project["character"] = "角色 # 100% 空格"
        con.execute("UPDATE projects SET data=? WHERE id='p-yo'", (json.dumps(project, ensure_ascii=False),))
    write(root / "data" / "assets" / known_sha[:2] / known_sha / "original.png", known)
    result = refresh_catalog(repo_root=root, data_dir=root / "data")
    assert result["ok"] is True, result["errors"]
    output = root / "data" / "我的参考图"
    manifest = json.loads((output / "manifest.json").read_text(encoding="utf-8"))
    item = next(row for row in manifest["items"] if row["sha"] == known_sha)
    assert "#" in Path(item["browse_path"]).name
    assert "%" in Path(item["browse_path"]).name
    assert " " in Path(item["browse_path"]).name
    for page in (output / "index.html",
                 output / "角色项目" / "角色 # 100% 空格" / "index.html"):
        assert page.is_file()
        html_text = page.read_text(encoding="utf-8")
        assert "#01" not in html_text.split('data-search=', 1)[0]
        assert_relative_links_resolve(output, page)
        assert_page_images_decode(output, page, 1)
    html_text = (output / "index.html").read_text(encoding="utf-8")
    assert "file://" in html_text
    assert "file%253A" not in html_text and "file%3A" not in html_text


def test_three_refresh_chain_updates_html_and_new_download_without_conflicts(tmp_path: Path):
    root = tmp_path / "repo"
    (root / "data").mkdir(parents=True)
    make_db(root, "a" * 64, "b" * 64)
    run = root / ".local" / "collection-runs" / "job-repeat" / "current"
    first_path = run / "images" / "first.png"
    write(first_path, image_bytes("red"))
    (run / "received.json").write_text("[]", encoding="utf-8")
    output = root / "data" / "我的参考图"
    first = refresh_catalog(repo_root=root, data_dir=root / "data")
    first_manifest = json.loads((output / "manifest.json").read_text(encoding="utf-8"))
    pages = ["index.html", "角色项目/渡边曜（渡辺曜）/index.html"]
    for page in pages:
        digest = hashlib.sha256((output / page).read_bytes()).hexdigest()
        assert first_manifest["owned_files"][page] == digest

    with sqlite3.connect(root / "data" / "library.sqlite3") as con:
        ref = json.loads(con.execute("SELECT data FROM refs WHERE id='r1'").fetchone()[0])
        ref["title"] = "改写后的标题"
        con.execute("UPDATE refs SET data=? WHERE id='r1'", (json.dumps(ref, ensure_ascii=False),))
    second_path = run / "images" / "second.png"
    write(second_path, image_bytes("blue"))
    second = refresh_catalog(repo_root=root, data_dir=root / "data")
    second_manifest = json.loads((output / "manifest.json").read_text(encoding="utf-8"))
    assert first["ok"] is True and second["ok"] is True, second["errors"]
    for page in pages:
        digest = hashlib.sha256((output / page).read_bytes()).hexdigest()
        assert second_manifest["owned_files"][page] == digest
    assert sum(1 for item in second_manifest["items"] if item.get("browse_path")) == len(
        [output / path for path in [item["browse_path"] for item in second_manifest["items"] if item.get("browse_path")]])

    third = refresh_catalog(repo_root=root, data_dir=root / "data")
    third_manifest = json.loads((output / "manifest.json").read_text(encoding="utf-8"))
    assert third["ok"] is True, third["errors"]
    assert {item["sha"]: item["browse_path"] for item in third_manifest["items"]} == {
        item["sha"]: item["browse_path"] for item in second_manifest["items"]}
    for page in pages:
        digest = hashlib.sha256((output / page).read_bytes()).hexdigest()
        assert third_manifest["owned_files"][page] == digest


def test_legacy_long_hash_preview_is_renamed_without_duplicate(tmp_path: Path):
    root = tmp_path / "repo"
    (root / "data").mkdir(parents=True)
    known = image_bytes("red")
    known_sha = hashlib.sha256(known).hexdigest()
    make_db(root, known_sha, "f" * 64)
    write(root / "data" / "assets" / known_sha[:2] / known_sha / "original.png", known)
    output = root / "data" / "我的参考图"
    refresh_catalog(repo_root=root, data_dir=root / "data")
    manifest_path = output / "manifest.json"
    old = json.loads(manifest_path.read_text(encoding="utf-8"))
    item = next(row for row in old["items"] if row["sha"] == known_sha)
    old_relative = item["browse_path"]
    old_file = output / old_relative
    digest = hashlib.sha256(old_file.read_bytes()).hexdigest()
    old_relative2 = f"images/{known_sha}_{known_sha[:12]}.jpg"
    role_relatives = list(dict.fromkeys(item.get("role_paths", {}).values()))
    assert role_relatives and all(path.endswith(".jpg") for path in role_relatives)
    old_file.replace(output / old_relative2)
    moved_roles = []
    for role_relative in role_relatives:
        role_relative2 = (Path(role_relative).parent / Path(old_relative2).name).as_posix()
        (output / role_relative).replace(output / role_relative2)
        moved_roles.append(role_relative2)
    item["browse_path"] = old_relative2
    item["preview_sha256"] = digest
    old["owned_files"] = {key: value for key, value in old["owned_files"].items()
                          if key not in {old_relative, *role_relatives}}
    manifest_path.write_text(json.dumps(old, ensure_ascii=False), encoding="utf-8")

    repaired = refresh_catalog(repo_root=root, data_dir=root / "data")
    new = json.loads(manifest_path.read_text(encoding="utf-8"))
    current = next(row for row in new["items"] if row["sha"] == known_sha)
    assert repaired["ok"] is True, repaired["errors"]
    assert current["browse_path"] != old_relative2
    assert current["browse_path"].endswith("_" + known_sha[:12] + ".jpg")
    assert not (output / old_relative2).exists()
    assert not any((output / role_relative).exists() for role_relative in moved_roles)
    assert len(list((output / "角色项目" / "渡边曜（渡辺曜）").glob("*.jpg"))) == 1
    assert all((output / path).is_file() for path in new["owned_files"] if path.endswith(".jpg"))


def test_changed_owned_preview_is_preserved_on_refresh(tmp_path: Path):
    root = tmp_path / "repo"
    (root / "data").mkdir(parents=True)
    known = image_bytes("red")
    known_sha = hashlib.sha256(known).hexdigest()
    make_db(root, known_sha, "f" * 64)
    write(root / "data" / "assets" / known_sha[:2] / known_sha / "original.png", known)
    output = root / "data" / "我的参考图"
    first = refresh_catalog(repo_root=root, data_dir=root / "data")
    manifest = json.loads((output / "manifest.json").read_text(encoding="utf-8"))
    preview = output / next(iter(path for path in manifest["owned_files"] if path.startswith("images/")))
    preview.write_bytes(b"user-modified")

    second = refresh_catalog(repo_root=root, data_dir=root / "data")
    assert first["ok"] is True
    assert second["ok"] is False
    assert preview.read_bytes() == b"user-modified"
    assert any(error["kind"] == "catalog_user_path_conflict" and error["path"].startswith("images/")
               for error in second["errors"])


def test_ref_title_wins_over_hash_like_received_name(tmp_path: Path):
    root = tmp_path / "repo"
    (root / "data").mkdir(parents=True)
    known = image_bytes("red")
    known_sha = hashlib.sha256(known).hexdigest()
    make_db(root, known_sha, "f" * 64)
    with sqlite3.connect(root / "data" / "library.sqlite3") as con:
        item = json.loads(con.execute("SELECT data FROM assets WHERE id=?", (known_sha,)).fetchone()[0])
        item["received_name"] = known_sha + ".jpg"
        con.execute("UPDATE assets SET data=? WHERE id=?", (json.dumps(item, ensure_ascii=False), known_sha))
        ref = json.loads(con.execute("SELECT data FROM refs WHERE id='r1'").fetchone()[0])
        ref["title"] = "海边转身"
        con.execute("UPDATE refs SET data=? WHERE id='r1'", (json.dumps(ref, ensure_ascii=False),))
    write(root / "data" / "assets" / known_sha[:2] / known_sha / "original.png", known)
    refresh_catalog(repo_root=root, data_dir=root / "data")
    manifest = json.loads((root / "data" / "我的参考图" / "manifest.json").read_text(encoding="utf-8"))
    item = next(row for row in manifest["items"] if row["sha"] == known_sha)
    assert item["original_name"]
    assert Path(item["browse_path"]).name.startswith("海边转身_")
    assert known_sha not in Path(item["browse_path"]).name
    assert known_sha in item["sha"]


def test_hash_only_title_falls_back_to_short_reference_name(tmp_path: Path):
    root = tmp_path / "repo"
    (root / "data").mkdir(parents=True)
    known = image_bytes("blue")
    known_sha = hashlib.sha256(known).hexdigest()
    make_db(root, known_sha, "f" * 64)
    with sqlite3.connect(root / "data" / "library.sqlite3") as con:
        item = json.loads(con.execute("SELECT data FROM assets WHERE id=?", (known_sha,)).fetchone()[0])
        item["received_name"] = known_sha + ".jpg"
        con.execute("UPDATE assets SET data=? WHERE id=?", (json.dumps(item, ensure_ascii=False), known_sha))
        ref = json.loads(con.execute("SELECT data FROM refs WHERE id='r1'").fetchone()[0])
        ref["title"] = known_sha
        con.execute("UPDATE refs SET data=? WHERE id='r1'", (json.dumps(ref, ensure_ascii=False),))
    write(root / "data" / "assets" / known_sha[:2] / known_sha / "original.png", known)
    refresh_catalog(repo_root=root, data_dir=root / "data")
    manifest = json.loads((root / "data" / "我的参考图" / "manifest.json").read_text(encoding="utf-8"))
    item = next(row for row in manifest["items"] if row["sha"] == known_sha)
    assert Path(item["browse_path"]).name.startswith("参考图_" + known_sha[:12] + "_")
    assert known_sha in item["sha"]


def test_legacy_manifest_recovers_explicit_central_preview_ownership(tmp_path: Path):
    root = tmp_path / "repo"
    (root / "data").mkdir(parents=True)
    known = image_bytes("red")
    known_sha = hashlib.sha256(known).hexdigest()
    make_db(root, known_sha, "f" * 64)
    write(root / "data" / "assets" / known_sha[:2] / known_sha / "original.png", known)
    output = root / "data" / "我的参考图"
    refresh_catalog(repo_root=root, data_dir=root / "data")
    path = output / "manifest.json"
    old = json.loads(path.read_text(encoding="utf-8"))
    item = next(row for row in old["items"] if row["browse_path"])
    old["owned_files"].pop(item["browse_path"])
    path.write_text(json.dumps(old, ensure_ascii=False), encoding="utf-8")

    repaired = refresh_catalog(repo_root=root, data_dir=root / "data")
    new = json.loads(path.read_text(encoding="utf-8"))
    repaired_item = next(row for row in new["items"] if row["sha"] == item["sha"])
    assert repaired["ok"] is True, repaired["errors"]
    assert repaired_item["browse_path"] == item["browse_path"]
    assert new["owned_files"][item["browse_path"]] == item["preview_sha256"]


def test_legacy_recovery_does_not_claim_unlisted_or_mismatched_files(tmp_path: Path):
    root = tmp_path / "repo"
    (root / "data").mkdir(parents=True)
    known = image_bytes("red")
    known_sha = hashlib.sha256(known).hexdigest()
    make_db(root, known_sha, "f" * 64)
    write(root / "data" / "assets" / known_sha[:2] / known_sha / "original.png", known)
    output = root / "data" / "我的参考图"
    refresh_catalog(repo_root=root, data_dir=root / "data")
    path = output / "manifest.json"
    old = json.loads(path.read_text(encoding="utf-8"))
    item = next(row for row in old["items"] if row["browse_path"])
    old["owned_files"].pop(item["browse_path"])
    (output / item["browse_path"]).write_bytes(b"not-the-manifest-preview")
    path.write_text(json.dumps(old, ensure_ascii=False), encoding="utf-8")
    unrelated = output / "images" / "mine.jpg"
    unrelated.write_bytes(b"user-owned")

    repaired = refresh_catalog(repo_root=root, data_dir=root / "data")
    new = json.loads(path.read_text(encoding="utf-8"))
    assert item["browse_path"] not in new["owned_files"]
    assert (output / item["browse_path"]).read_bytes() == b"not-the-manifest-preview"
    assert unrelated.read_bytes() == b"user-owned"
    assert "images/mine.jpg" not in new["owned_files"]
    assert repaired["ok"] is False


def test_legacy_run_only_role_copy_recovers_through_project_identity(tmp_path: Path):
    root = tmp_path / "repo"
    (root / "data").mkdir(parents=True)
    raw = image_bytes("purple")
    sha = hashlib.sha256(raw).hexdigest()
    make_db(root, "a" * 64, "f" * 64)
    write(root / ".local/collection-runs/job-history/current/images" / f"{sha}.png", raw)
    refresh_catalog(repo_root=root, data_dir=root / "data")
    output = root / "data/我的参考图"
    path = output / "manifest.json"
    old = json.loads(path.read_text(encoding="utf-8"))
    item = next(row for row in old["items"] if row["sha"] == sha)
    role_path = item["role_paths"]["角色项目/渡边曜（渡辺曜）"]
    prior_bytes = (output / role_path).read_bytes()
    del old["owned_files"][role_path]
    item["role_paths"] = {}
    path.write_text(json.dumps(old, ensure_ascii=False), encoding="utf-8")

    report = refresh_catalog(repo_root=root, data_dir=root / "data")
    new = json.loads(path.read_text(encoding="utf-8"))
    repaired = next(row for row in new["items"] if row["sha"] == sha)
    assert report["ok"], report["errors"]
    assert repaired["role_paths"]["角色项目/渡边曜（渡辺曜）"] == role_path
    assert new["owned_files"][role_path] == item["preview_sha256"]
    assert (output / role_path).read_bytes() == prior_bytes
