from __future__ import annotations

import hashlib
import json
import os
import sqlite3
from html.parser import HTMLParser
from pathlib import Path
from urllib.parse import unquote, urlsplit

import pytest
from PIL import Image

from ref_lab.catalog_exports import export_character_catalog, load_export_settings, save_export_settings
from ref_lab.local_catalog import GENERATOR_ID, refresh_catalog
from tools.sync_local_catalog import main as sync_main


CHARACTER = "安养寺姬芽"
ROLE_FOLDER = f"角色项目/{CHARACTER}"


class Links(HTMLParser):
    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.hrefs: list[str] = []

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        if tag == "a":
            value = dict(attrs).get("href")
            if value:
                self.hrefs.append(value)


def jpeg_bytes(color: tuple[int, int, int]) -> bytes:
    from io import BytesIO

    output = BytesIO()
    Image.new("RGB", (32, 40), color).save(output, "JPEG", quality=90)
    return output.getvalue()


def make_catalog(root: Path, count: int = 30) -> tuple[Path, Path]:
    repo = root / "repo"
    data = repo / "data"
    catalog = data / "我的参考图"
    role = catalog / ROLE_FOLDER
    role.mkdir(parents=True)
    items = []
    owned = {}
    for index in range(count):
        filename = (f"原图 #01 100% 中文 {index}.jpg" if index == 0
                    else f"全部下载 中文 {index:02d}.jpg")
        relative = (Path(ROLE_FOLDER) / filename).as_posix()
        destination = catalog / relative
        original = data / "assets" / f"{index:02x}" / "original.jpg"
        original.parent.mkdir(parents=True)
        original.write_bytes(f"camera-original-{index}".encode())
        destination.write_bytes(jpeg_bytes((index, 20, 30)))
        preview_sha = hashlib.sha256(destination.read_bytes()).hexdigest()
        item_sha = hashlib.sha256(f"asset-{index}".encode()).hexdigest()
        owned[relative] = preview_sha
        items.append({
            "sha": item_sha, "title": f"安养寺姬芽参考 {index:02d}", "status": "可浏览",
            "original_path": str(original), "preview_sha256": preview_sha,
            "role_paths": {ROLE_FOLDER: relative},
            "role_groups": CHARACTER,
            "relations": [{"kind": "project", "project_id": "p-hime", "character": CHARACTER}],
        })
    payload = {
        "schema": 1, "generator": GENERATOR_ID, "repo_root": str(repo.resolve()),
        "items": items, "owned_files": owned,
        "roles": [{"group": CHARACTER, "count": count, "folder": ROLE_FOLDER}],
    }
    (catalog / "manifest.json").write_text(json.dumps(payload, ensure_ascii=False), encoding="utf-8")
    return data, catalog


def add_catalog_item(catalog: Path, index: int) -> None:
    path = catalog / "manifest.json"
    payload = json.loads(path.read_text(encoding="utf-8"))
    filename = f"新增 中文 {index}.jpg"
    relative = (Path(ROLE_FOLDER) / filename).as_posix()
    destination = catalog / relative
    destination.write_bytes(jpeg_bytes((index, 50, 60)))
    preview_sha = hashlib.sha256(destination.read_bytes()).hexdigest()
    original = catalog.parent / "assets" / f"new-{index}.jpg"
    original.parent.mkdir(parents=True, exist_ok=True)
    original.write_bytes(f"camera-original-{index}".encode())
    payload["items"].append({
        "sha": hashlib.sha256(f"asset-{index}".encode()).hexdigest(),
        "title": f"安养寺姬芽参考 {index:02d}", "status": "可浏览", "original_path": str(original),
        "preview_sha256": preview_sha, "role_paths": {ROLE_FOLDER: relative},
        "role_groups": CHARACTER,
        "relations": [{"kind": "project", "project_id": "p-hime", "character": CHARACTER}],
    })
    payload["owned_files"][relative] = preview_sha
    payload["roles"][0]["count"] = len(payload["items"])
    path.write_text(json.dumps(payload, ensure_ascii=False), encoding="utf-8")


def make_refreshed_catalog(root: Path) -> tuple[Path, Path, str]:
    repo = root / "repo"
    data = repo / "data"
    data.mkdir(parents=True)
    database = data / "library.sqlite3"
    assets = []
    with sqlite3.connect(database) as con:
        con.executescript("""
        CREATE TABLE projects(id TEXT PRIMARY KEY,data TEXT NOT NULL);
        CREATE TABLE assets(id TEXT PRIMARY KEY,data TEXT NOT NULL);
        CREATE TABLE refs(id TEXT PRIMARY KEY,project_id TEXT,asset_sha TEXT,decision TEXT,state TEXT,data TEXT);
        CREATE TABLE inspirations(id TEXT PRIMARY KEY,asset_sha TEXT,active INTEGER,data TEXT);
        CREATE TABLE study_candidates(id TEXT PRIMARY KEY,batch_id TEXT,asset_sha TEXT,status TEXT,data TEXT);
        CREATE TABLE jobs(id TEXT PRIMARY KEY,project_id TEXT,kind TEXT,status TEXT,data TEXT);
        """)
        con.execute("INSERT INTO projects VALUES(?,?)", (
            "p-hime", json.dumps({"id": "p-hime", "character": CHARACTER}, ensure_ascii=False)))
        for index in range(2):
            payload = jpeg_bytes((40 + index, 20, 30))
            sha = hashlib.sha256(payload).hexdigest()
            original = data / "assets" / sha[:2] / sha / "original.jpg"
            original.parent.mkdir(parents=True)
            original.write_bytes(payload)
            con.execute("INSERT INTO assets VALUES(?,?)", (
                sha, json.dumps({"id": sha, "ext": "jpg", "received_name": f"原图{index}.jpg"},
                                ensure_ascii=False)))
            con.execute("INSERT INTO refs VALUES(?,?,?,?,?,?)", (
                f"r{index}", "p-hime", sha, "pending", "candidate",
                json.dumps({"title": f"真实角色参考 {index}"}, ensure_ascii=False)))
            assets.append(sha)

    catalog = data / "我的参考图"
    refresh_catalog(repo_root=repo, data_dir=data)
    manifest_path = catalog / "manifest.json"
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    role = next(row for row in manifest["roles"] if row["group"] == CHARACTER)
    assert role["count"] == 2 and "projects" not in role
    items = [row for row in manifest["items"] if row.get("role_groups") == CHARACTER]
    assert len(items) == 2 and all(row["browse_path"] for row in items)
    fallback = items[0]
    fallback["role_paths"] = {}
    manifest_path.write_text(json.dumps(manifest, ensure_ascii=False), encoding="utf-8")
    return data, catalog, fallback["preview_sha256"]


def test_export_consumes_refreshed_role_groups_and_central_preview_fallback(tmp_path: Path):
    data, catalog, fallback_preview_sha = make_refreshed_catalog(tmp_path)

    report = export_character_catalog(catalog, data, CHARACTER)

    assert report["ok"] is True, report["errors"]
    assert report["images"] == report["exported"] == 2
    manifest = json.loads(Path(report["manifest"]).read_text(encoding="utf-8"))
    assert {row["sha"] for row in manifest["items"]} == {
        row["preview_sha256"] for row in json.loads(
            (catalog / "manifest.json").read_text(encoding="utf-8"))["items"]
        if row.get("role_groups") == CHARACTER
    }
    fallback = next(row for row in manifest["items"] if row["sha"] == fallback_preview_sha)
    assert fallback["source"].startswith("images/")
    assert Path(report["export_dir"], fallback["filename"]).is_file()
    assert not os.path.samefile(Path(report["export_dir"], fallback["filename"]),
                                catalog / fallback["source"])


def test_first_export_covers_all_30_as_independent_readable_jpgs(tmp_path: Path):
    data, catalog = make_catalog(tmp_path)
    accepted = data / "exports" / CHARACTER / "已确认"
    accepted.mkdir(parents=True)
    accepted_file = accepted / "old.txt"
    accepted_file.write_bytes(b"accepted-must-stay")

    report = export_character_catalog(catalog, data, CHARACTER)

    assert report["ok"] is True, report["errors"]
    assert report["images"] == report["exported"] == 30
    target = data / "exports" / CHARACTER / "全部下载"
    exported = sorted(target.glob("*.jpg"))
    assert len(exported) == 30
    manifest = json.loads((target / "manifest.json").read_text(encoding="utf-8"))
    assert manifest["summary"]["images"] == 30
    assert len(manifest["items"]) == 30
    catalog_manifest = json.loads((catalog / "manifest.json").read_text(encoding="utf-8"))
    by_source = {item["role_paths"][ROLE_FOLDER]: item for item in catalog_manifest["items"]}
    for output in exported:
        sources = [row for row in by_source.values() if Path(row["role_paths"][ROLE_FOLDER]).name == output.name]
        assert len(sources) == 1
        source = catalog / sources[0]["role_paths"][ROLE_FOLDER]
        assert output.read_bytes() == source.read_bytes()
        assert not os.path.samefile(output, source)
    assert accepted_file.read_bytes() == b"accepted-must-stay"
    assert "不是相机原图" in (target / "index.html").read_text(encoding="utf-8")


def test_index_links_encode_reserved_space_and_chinese_characters(tmp_path: Path):
    data, catalog = make_catalog(tmp_path, count=1)
    report = export_character_catalog(catalog, data, CHARACTER)
    assert report["ok"] is True, report["errors"]
    target = Path(report["export_dir"])
    page = target / "index.html"
    parser = Links()
    parser.feed(page.read_text(encoding="utf-8"))
    image_links = [href for href in parser.hrefs if href.endswith(".jpg")]
    assert len(image_links) == 1
    assert "%23" in image_links[0] and "%25" in image_links[0] and "%20" in image_links[0]
    assert "%E4%B8%AD" in image_links[0]
    assert unquote(image_links[0]) == "原图 #01 100% 中文 0.jpg"
    parsed = urlsplit(image_links[0])
    assert not parsed.scheme and not parsed.netloc
    assert (page.parent / unquote(parsed.path)).is_file()


def test_settings_reject_empty_registration(tmp_path: Path):
    with pytest.raises(ValueError, match="至少登记"):
        save_export_settings(tmp_path, [])


def test_explicit_cli_setting_is_reused_and_preserves_new_repeat_and_user_files(
        tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    data, catalog = make_catalog(tmp_path)
    import tools.sync_local_catalog as cli

    report = {"output": str(catalog), "manifest": str(catalog / "manifest.json"),
              "summary": {"images": 30}, "errors": [], "ok": True}
    monkeypatch.setattr(cli, "refresh_catalog", lambda **kwargs: report)
    args = ["--repo-root", str(tmp_path / "repo"), "--data-dir", str(data),
            "--output", str(catalog), "--export-character", CHARACTER]
    assert sync_main(args) == 0
    assert load_export_settings(catalog) == [CHARACTER]
    target = data / "exports" / CHARACTER / "全部下载"
    initial_manifest = json.loads((target / "manifest.json").read_text(encoding="utf-8"))
    assert len(list(target.glob("*.jpg"))) == 30

    add_catalog_item(catalog, 30)
    modified = target / next(name for name in initial_manifest["owned_files"] if name.endswith(".jpg"))
    modified.write_bytes(b"user changed this export")
    mixed = target / "我的说明.txt"
    mixed.write_text("keep me", encoding="utf-8")
    assert sync_main(["--repo-root", str(tmp_path / "repo"), "--data-dir", str(data),
                      "--output", str(catalog)]) == 2

    refreshed = json.loads((target / "manifest.json").read_text(encoding="utf-8"))
    assert refreshed["summary"]["images"] == 31
    assert len(refreshed["items"]) == 31
    assert modified.read_bytes() == b"user changed this export"
    assert mixed.read_text(encoding="utf-8") == "keep me"
    assert any(row.get("filename", "").startswith(modified.stem + ".ref-lab-")
               for row in refreshed["items"])
    assert any(error["kind"] == "catalog_export_user_file_preserved" and error["path"] == mixed.name
               for error in refreshed["errors"])

    third = export_character_catalog(catalog, data, CHARACTER)
    assert third["images"] == 31
    assert len([row for row in third["errors"] if row["kind"] == "catalog_export_user_file_preserved"]) == 1
    assert modified.read_bytes() == b"user changed this export"
    assert mixed.read_text(encoding="utf-8") == "keep me"


def test_same_identity_bad_role_path_and_hash_are_rejected(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    data, catalog = make_catalog(tmp_path)
    manifest_path = catalog / "manifest.json"
    original = json.loads(manifest_path.read_text(encoding="utf-8"))
    import ref_lab.catalog_exports as exports

    monkeypatch.setattr(exports.os.path, "samefile", lambda left, right: True)
    with pytest.raises(ValueError, match="共享文件身份"):
        export_character_catalog(catalog, data, CHARACTER)
    monkeypatch.setattr(exports.os.path, "samefile", os.path.samefile)

    original["items"][0]["role_paths"][ROLE_FOLDER] = str(catalog / ROLE_FOLDER / "原图 #01 100% 中文 0.jpg")
    manifest_path.write_text(json.dumps(original, ensure_ascii=False), encoding="utf-8")
    with pytest.raises(ValueError, match="路径、SHA 或所有权无效"):
        export_character_catalog(catalog, data, CHARACTER)

    original["items"][0]["role_paths"][ROLE_FOLDER] = (Path(ROLE_FOLDER) / "原图 #01 100% 中文 0.jpg").as_posix()
    original["items"][0]["preview_sha256"] = "0" * 64
    manifest_path.write_text(json.dumps(original, ensure_ascii=False), encoding="utf-8")
    with pytest.raises(ValueError, match="路径、SHA 或所有权无效"):
        export_character_catalog(catalog, data, CHARACTER)


def test_rejects_catalog_preview_that_resolves_into_original_assets(tmp_path: Path):
    data, catalog = make_catalog(tmp_path, count=1)
    manifest_path = catalog / "manifest.json"
    payload = json.loads(manifest_path.read_text(encoding="utf-8"))
    filename = Path(payload["items"][0]["role_paths"][ROLE_FOLDER]).name
    original = data / "assets" / "copy.jpg"
    original.parent.mkdir(parents=True, exist_ok=True)
    os.replace(catalog / ROLE_FOLDER / filename, original)
    try:
        os.symlink(original, catalog / ROLE_FOLDER / filename)
    except (OSError, NotImplementedError) as exc:
        pytest.skip(f"sandbox does not allow symlinks: {exc}")
    with pytest.raises(ValueError, match="越界、链接、原件或 hash 不符"):
        export_character_catalog(catalog, data, CHARACTER)
