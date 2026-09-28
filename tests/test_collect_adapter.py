from __future__ import annotations

import json
import os
from pathlib import Path
import sys
import zipfile

import pytest

from ref_lab.agent_collection import run_collection_attempt
from ref_lab.models import JobInput
from conftest import image_bytes


def test_collect_adapter_with_synthetic_fetch(library, project, monkeypatch, tmp_path):
    job = library.create_job(project["id"], JobInput(
        kind="collection",
        notes="测试适配器流程",
        target_count=2
    ))

    # Mock fetch_bing_candidates inside tools.collect_adapter so test runs offline and deterministically
    adapter_script = Path(__file__).resolve().parent.parent / "tools" / "collect_adapter.py"
    assert adapter_script.is_file()

    # Wrap collect_adapter with a test monkeypatch script
    wrapper = tmp_path / "mock_adapter.py"
    img1 = image_bytes(seed=1, size=(400, 400))
    img2 = image_bytes(seed=2, size=(450, 450))

    cache_dir = tmp_path / "cache"
    cache_dir.mkdir()
    (cache_dir / "img1.png").write_bytes(img1)
    (cache_dir / "img2.png").write_bytes(img2)

    repo_root = str(adapter_script.parent.parent).replace("\\", "/")
    if repo_root.startswith("D:"):
        repo_root = "/mnt/d" + repo_root[2:]
    elif repo_root.startswith("C:"):
        repo_root = "/mnt/c" + repo_root[2:]

    wrapper.write_text(f"""import sys
from pathlib import Path
sys.path.insert(0, "{repo_root}")
import tools.collect_adapter as ca

def mock_fetch(queries, target_count, character, costume):
    cand1_img = Path(r"{cache_dir / 'img1.png'}").read_bytes()
    cand2_img = Path(r"{cache_dir / 'img2.png'}").read_bytes()
    candidates = [
        {{
            "id": "cand-001",
            "file": "images/img1.png",
            "title": f"{{character}} {{costume}} 模拟测试 1",
            "source": {{
                "page_url": "https://example.com/p1",
                "image_url": "https://example.com/img1.png",
                "author": "tester",
                "title": "测试图1",
                "search_query": "mock query",
                "rights": "unknown",
                "source_confirmed": False
            }},
            "discovery_intent": "exact_character",
            "discovery_reason": "模拟检索发现",
            "discovery_url": "https://example.com/search",
            "notes": "测试说明",
            "preflight": {{
                "content_type": "real_person_cosplay",
                "identity_prediction": "match",
                "confidence": "high",
                "visual_evidence": ["测试实拍", "特征匹配"],
                "reason": "合成测试"
            }}
        }},
        {{
            "id": "cand-002",
            "file": "images/img2.png",
            "title": f"{{character}} {{costume}} 模拟测试 2",
            "source": {{
                "page_url": "https://example.com/p2",
                "image_url": "https://example.com/img2.png",
                "author": "tester",
                "title": "测试图2",
                "search_query": "mock query 2",
                "rights": "unknown",
                "source_confirmed": False
            }},
            "discovery_intent": "exact_character",
            "discovery_reason": "模拟检索发现 2",
            "discovery_url": "https://example.com/search",
            "notes": "测试说明 2",
            "preflight": {{
                "content_type": "real_person_portrait",
                "identity_prediction": "uncertain",
                "confidence": "medium",
                "visual_evidence": ["人像摄影"],
                "reason": "合成人像"
            }}
        }}
    ]
    images = {{"img1.png": cand1_img, "img2.png": cand2_img}}
    query_log = [{{"query": "mock query", "source": "mock", "kept": 2, "stop_reason": "done"}}]
    return candidates, images, query_log

ca.fetch_bing_candidates = mock_fetch
ca.main()
""", encoding="utf-8")

    monkeypatch.setenv("LAB_COLLECTION_COMMAND", json.dumps([
        sys.executable, str(wrapper), "{task_file}", "{result_file}"
    ]))
    monkeypatch.setenv("LAB_COLLECTION_TIMEOUT_SECONDS", "10")

    result = run_collection_attempt(library, job["id"])
    assert result["status"] == "succeeded"
    assert len(result["imported_ids"]) == 2

    # Check imported references
    ref1 = library.reference(result["imported_ids"][0])
    assert ref1["title"]
    assert ref1["preflight"] is not None
    assert ref1["preflight"]["content_type"] in {"real_person_cosplay", "real_person_portrait"}
