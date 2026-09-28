from __future__ import annotations

import io
import zipfile

from PIL import Image

from conftest import add_reference, image_bytes, ready_reference


def transfer_item(ref: dict) -> dict:
    return {"reference_id": ref["id"], "expected_revision": ref["revision"]}


def test_copy_to_other_project_reuses_asset_without_inheriting_project_judgment(client, project):
    source = ready_reference(client, project)
    assert source["field_ready"] and source["review"] and source["card"]
    target = client.post("/api/projects", json={"character": "食蜂操祈", "work": "某科学的超电磁炮"}).json()

    response = client.post(
        f"/api/projects/{project['id']}/references/transfer",
        json={
            "items": [transfer_item(source)],
            "mode": "copy",
            "target_project_id": target["id"],
            "target_decision": "pending",
        },
    )
    assert response.status_code == 200, response.text
    result = response.json()["items"][0]
    assert result["target_created"] is True
    assert result["source_detached"] is False

    copied = client.get(f"/api/references/{result['target_reference_id']}").json()
    current_source = client.get(f"/api/references/{source['id']}").json()
    assert copied["asset_sha"] == source["asset_sha"]
    assert copied["project_id"] == target["id"]
    assert copied["decision"] == "pending"
    assert copied["preflight"] is None
    assert copied["review"] is None
    assert copied["card"] is None
    assert copied["accepted_fingerprint"] is None
    assert copied["source"]["source_confirmed"] is False
    assert current_source["detached_at"] is None
    assert current_source["field_ready"] is True


def test_copy_preserves_existing_target_choice(client, project):
    source = add_reference(client, project, seed=31)
    target = client.post("/api/projects", json={"character": "另一个角色"}).json()
    existing = client.post(
        f"/api/projects/{target['id']}/references",
        json={"asset_sha": source["asset_sha"], "title": "target already chose this"},
    ).json()["reference"]
    existing = client.patch(
        f"/api/references/{existing['id']}",
        json={"expected_revision": existing["revision"], "decision": "maybe", "preference": "目标项目自己的判断"},
    ).json()

    response = client.post(
        f"/api/projects/{project['id']}/references/transfer",
        json={
            "items": [transfer_item(source)],
            "mode": "copy",
            "target_project_id": target["id"],
            "target_decision": "keep",
        },
    )
    assert response.status_code == 200, response.text
    item = response.json()["items"][0]
    assert item["target_created"] is False
    assert item["preserved_existing_choice"] is True
    target_after = client.get(f"/api/references/{existing['id']}").json()
    assert target_after["decision"] == "maybe"
    assert target_after["preference"] == "目标项目自己的判断"


def test_move_detaches_source_without_x_and_restore_is_reversible(client, project):
    source = add_reference(client, project, seed=32)
    target = client.post("/api/projects", json={"character": "目标角色"}).json()

    response = client.post(
        f"/api/projects/{project['id']}/references/transfer",
        json={
            "items": [transfer_item(source)],
            "mode": "move",
            "target_project_id": target["id"],
            "target_decision": "pending",
        },
    )
    assert response.status_code == 200, response.text
    result = response.json()["items"][0]
    moved_source = client.get(f"/api/references/{source['id']}").json()
    moved_target = client.get(f"/api/references/{result['target_reference_id']}").json()

    assert result["source_detached"] is True
    assert moved_source["detached_at"]
    assert moved_source["detached_to_project_id"] == target["id"]
    assert moved_source["decision"] == source["decision"]  # move is not X
    assert moved_source["workflow_stage"] == "detached"
    assert moved_target["decision"] == "pending"
    assert moved_target["asset_sha"] == source["asset_sha"]

    normal = client.get(f"/api/projects/{project['id']}/references").json()
    assert all(item["id"] != source["id"] for item in normal["items"])
    recycle = client.get(f"/api/projects/{project['id']}/references?view_recycle=true").json()
    assert any(item["id"] == source["id"] for item in recycle["items"])

    restored = client.post(
        f"/api/references/{source['id']}/restore-project-use",
        json={"expected_revision": moved_source["revision"]},
    )
    assert restored.status_code == 200, restored.text
    restored_ref = restored.json()
    assert restored_ref["detached_at"] is None
    assert restored_ref["decision"] == source["decision"]
    assert any(item["id"] == source["id"] for item in client.get(f"/api/projects/{project['id']}/references").json()["items"])


def test_remove_from_project_preserves_global_inspiration_and_other_project(client, project):
    source = add_reference(client, project, seed=33)
    saved = client.post(
        f"/api/references/{source['id']}/inspiration",
        json={"expected_revision": source["revision"]},
    )
    assert saved.status_code == 200, saved.text

    target = client.post("/api/projects", json={"character": "另一个项目"}).json()
    copied = client.post(
        f"/api/projects/{project['id']}/references/transfer",
        json={
            "items": [transfer_item(source)],
            "mode": "copy",
            "target_project_id": target["id"],
            "target_decision": "pending",
        },
    ).json()
    assert copied["items"][0]["target_reference_id"]

    source = client.get(f"/api/references/{source['id']}").json()
    removed = client.post(
        f"/api/projects/{project['id']}/references/transfer",
        json={"items": [transfer_item(source)], "mode": "remove", "target_project_id": "", "target_decision": "pending"},
    )
    assert removed.status_code == 200, removed.text
    assert removed.json()["items"][0]["source_detached"] is True

    assert client.get("/api/inspirations").json()["total"] == 1
    assert client.get(f"/api/projects/{target['id']}/references").json()["total"] == 1
    assert client.get(f"/api/assets/{source['asset_sha']}/original").status_code == 200


def test_transfer_batch_rejects_stale_revision_without_partial_move(client, project):
    first = add_reference(client, project, seed=34)
    second = add_reference(client, project, seed=35)
    target = client.post("/api/projects", json={"character": "批量目标"}).json()
    changed = client.patch(
        f"/api/references/{second['id']}",
        json={"expected_revision": second["revision"], "decision": "maybe"},
    ).json()

    response = client.post(
        f"/api/projects/{project['id']}/references/transfer",
        json={
            "items": [transfer_item(first), transfer_item(second)],
            "mode": "move",
            "target_project_id": target["id"],
            "target_decision": "pending",
        },
    )
    assert response.status_code == 409
    assert client.get(f"/api/references/{first['id']}").json()["detached_at"] is None
    assert client.get(f"/api/references/{changed['id']}").json()["detached_at"] is None
    assert client.get(f"/api/projects/{target['id']}/references").json()["total"] == 0


def test_contact_board_one_page_png_contains_without_mutating_original(client, project):
    portrait = add_reference(client, project, seed=40)
    landscape_asset = client.post(
        "/api/assets",
        files={"file": ("landscape.png", image_bytes(41, size=(1200, 700)), "image/png")},
    ).json()
    landscape = client.post(
        f"/api/projects/{project['id']}/references",
        json={"asset_sha": landscape_asset["id"], "title": "横图"},
    ).json()["reference"]
    before = client.get(f"/api/assets/{portrait['asset_sha']}/original").content

    response = client.post(
        f"/api/projects/{project['id']}/contact-board",
        json={
            "title": "给模特看的动作参考",
            "items": [
                {"reference_id": portrait["id"], "note": "喜欢这个站姿"},
                {"reference_id": landscape["id"], "note": "主要看构图，不照搬服装"},
            ],
        },
    )
    assert response.status_code == 200, response.text
    assert response.headers["content-type"].startswith("image/png")
    with Image.open(io.BytesIO(response.content)) as board:
        assert board.size == (1800, 1400)
        assert board.format == "PNG"
    assert client.get(f"/api/assets/{portrait['asset_sha']}/original").content == before


def test_contact_board_more_than_four_is_paginated_zip(client, project):
    refs = [add_reference(client, project, seed=50 + i) for i in range(5)]
    response = client.post(
        f"/api/projects/{project['id']}/contact-board",
        json={
            "title": "五张参考",
            "items": [{"reference_id": ref["id"], "note": f"参考 {i+1}"} for i, ref in enumerate(refs)],
        },
    )
    assert response.status_code == 200, response.text
    assert response.headers["content-type"].startswith("application/zip")
    with zipfile.ZipFile(io.BytesIO(response.content)) as archive:
        assert archive.namelist() == ["contact-board-01.png", "contact-board-02.png"]
        for name in archive.namelist():
            with Image.open(io.BytesIO(archive.read(name))) as board:
                assert board.size == (1800, 1400)
                assert board.format == "PNG"


def test_contact_board_rejects_detached_or_rejected_references(client, project):
    detached = add_reference(client, project, seed=60)
    detached_result = client.post(
        f"/api/projects/{project['id']}/references/transfer",
        json={"items": [transfer_item(detached)], "mode": "remove", "target_project_id": "", "target_decision": "pending"},
    )
    assert detached_result.status_code == 200

    rejected = add_reference(client, project, seed=61)
    rejected = client.patch(
        f"/api/references/{rejected['id']}",
        json={"expected_revision": rejected["revision"], "decision": "reject"},
    ).json()

    for ref_id in (detached["id"], rejected["id"]):
        response = client.post(
            f"/api/projects/{project['id']}/contact-board",
            json={"items": [{"reference_id": ref_id, "note": ""}]},
        )
        assert response.status_code == 409
