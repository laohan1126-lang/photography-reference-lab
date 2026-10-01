"""Test suite for confirmed references auto-archive to character folder."""
from __future__ import annotations

import io
from pathlib import Path
from PIL import Image
import pytest

from conftest import add_reference, image_bytes
from ref_lab.archiver import (
    sanitize_filename,
    get_project_archive_dir,
    get_reference_archive_filename,
    export_asset_as_jpeg,
    sync_project_confirmed_archive,
)
from ref_lab.config import Settings
from ref_lab.models import ProjectInput, ReferenceEdit
from ref_lab.service import Library


def test_sanitize_filename():
    assert sanitize_filename("托尔:龙女仆/婚纱?*") == "托尔_龙女仆_婚纱"
    assert sanitize_filename("") == "未命名"
    assert sanitize_filename("   ...   ") == "未命名"
    assert len(sanitize_filename("a" * 100, max_length=30)) == 30


def test_get_project_archive_dir(tmp_path: Path):
    proj = {"character": "托尔", "costume": "女仆装"}
    p = get_project_archive_dir(tmp_path, proj)
    assert p == tmp_path / "exports" / "托尔" / "已确认"


def test_export_asset_as_jpeg(tmp_path: Path):
    # Test converting a PNG with transparency to clean JPEG
    src = tmp_path / "sample.png"
    im = Image.new("RGBA", (100, 100), (255, 0, 0, 128))
    im.save(src, format="PNG")

    dest = tmp_path / "output.jpg"
    success = export_asset_as_jpeg(src, dest)
    assert success is True
    assert dest.is_file()

    # Verify JPEG format
    with Image.open(dest) as out_im:
        assert out_im.format == "JPEG"
        assert out_im.mode == "RGB"


def test_sync_project_confirmed_archive(client, app):
    lib = app.state.library
    proj_resp = client.post("/api/projects", json={"character": "托尔", "costume": "女仆装"})
    assert proj_resp.status_code == 201
    proj = proj_resp.json()

    r1 = add_reference(client, proj, seed=1, title="托尔营业中")
    r2 = add_reference(client, proj, seed=2, title="龙女仆婚礼")
    r3 = add_reference(client, proj, seed=3, title="未确认候选")

    # Mark r1 and r2 as keep
    client.patch(f"/api/references/{r1['id']}", json={"expected_revision": r1["revision"], "decision": "keep", "lane": "field"})
    r2_fresh = lib.reference(r2["id"])
    client.patch(f"/api/references/{r2['id']}", json={"expected_revision": r2_fresh["revision"], "decision": "keep", "lane": "field"})

    res = sync_project_confirmed_archive(lib, proj["id"])
    archive_dir = Path(res["archive_dir"])
    assert archive_dir.is_dir()
    assert res["count"] == 2

    files = list(archive_dir.glob("*.jpg"))
    assert len(files) == 2
    names = {f.name for f in files}
    assert any("托尔营业中" in n for n in names)
    assert any("龙女仆婚礼" in n for n in names)

    # Now reject r2, sync again, r2 should be removed from archive
    r2_fresh = lib.reference(r2["id"])
    client.patch(f"/api/references/{r2['id']}", json={"expected_revision": r2_fresh["revision"], "decision": "reject"})

    res2 = sync_project_confirmed_archive(lib, proj["id"])
    assert res2["count"] == 1
    files2 = list(archive_dir.glob("*.jpg"))
    assert len(files2) == 1
    assert "托尔营业中" in files2[0].name


def test_edit_reference_auto_archives_and_reveals(client, app):
    proj_resp = client.post("/api/projects", json={"character": "托尔", "costume": "日常女仆"})
    assert proj_resp.status_code == 201
    proj = proj_resp.json()

    ref = add_reference(client, proj, seed=10, title="托尔端茶")

    # Before keep, archive_path is None
    ref_detail = client.get(f"/api/references/{ref['id']}").json()
    assert ref_detail["archive_dir"].endswith("托尔\\已确认") or ref_detail["archive_dir"].endswith("托尔/已确认")
    assert ref_detail["archive_path"] is None

    # Patch decision to keep -> auto-archive triggered
    patched = client.patch(
        f"/api/references/{ref['id']}",
        json={"expected_revision": ref["revision"], "decision": "keep", "lane": "field"}
    )
    assert patched.status_code == 200
    ref_updated = patched.json()
    assert ref_updated["archive_path"] is not None
    archived_file = Path(ref_updated["archive_path"])
    assert archived_file.is_file()
    assert archived_file.suffix == ".jpg"
    assert "托尔端茶" in archived_file.name

    # Reveal reference should return the archived path
    rev = client.post(f"/api/references/{ref['id']}/reveal")
    assert rev.status_code == 200
    assert rev.json()["revealed"] is True
    assert rev.json()["path"] == str(archived_file)

    # Reveal project export folder
    rev_proj = client.post(f"/api/projects/{proj['id']}/reveal-export")
    assert rev_proj.status_code == 200
    assert rev_proj.json()["revealed"] is True
    assert rev_proj.json()["path"] == ref_updated["archive_dir"]

    # Reject -> file removed from archive
    client.patch(
        f"/api/references/{ref['id']}",
        json={"expected_revision": ref_updated["revision"], "decision": "reject"}
    )
    assert not archived_file.exists()

