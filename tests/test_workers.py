from __future__ import annotations

import json
import httpx
import pytest
from ref_lab.collector import allowed_image_url, capture_page, download_observed
from ref_lab.models import AnalysisResult, JobInput
from ref_lab.providers import OpenAIAnalyzer, ProviderError, run_analysis_job, sync_task_to_notion
from ref_lab.service import Problem
from conftest import add_reference, card_data, image_bytes, review_data


def test_openai_protocol_and_no_remote_call_without_config():
    with pytest.raises(ProviderError): OpenAIAnalyzer("", "")
    sha = "b" * 64
    result = {"review": review_data(sha), "card": card_data()}
    def respond(request):
        payload = json.loads(request.content)
        assert request.url == "https://api.openai.com/v1/responses"
        assert payload["store"] is False and payload["text"]["format"]["strict"] is True
        assert payload["input"][1]["content"][1]["image_url"].startswith("data:image/jpeg;base64,")
        return httpx.Response(200, json={"status": "completed", "output": [{"type": "message", "content": [{"type": "output_text", "text": json.dumps(result)}]}]})
    analyzer = OpenAIAnalyzer("fixture-not-live", "explicit-test-model", transport=httpx.MockTransport(respond))
    assert analyzer.analyze(b"synthetic", {"asset_sha": sha}).review.asset_sha == sha


@pytest.mark.parametrize("response", [{"status": "incomplete"}, {"status": "completed", "output": [{"content": [{"type": "refusal"}]}]}, {"status": "completed", "output": []}])
def test_openai_incomplete_refused_or_invalid_output_is_not_success(response):
    analyzer = OpenAIAnalyzer("fixture", "fixture", transport=httpx.MockTransport(lambda request: httpx.Response(200, json=response)))
    with pytest.raises(ProviderError): analyzer.analyze(b"test", {})


def test_worker_checkpoint_and_human_approval_stays_separate(client, project, library):
    ref = add_reference(client, project)
    ref = client.patch(f"/api/references/{ref['id']}", json={"expected_revision": ref["revision"], "decision": "keep"}).json()
    job = library.create_job(project["id"], JobInput(kind="analysis", reference_ids=[ref["id"]]))
    class SyntheticAnalyzer:
        model = "synthetic-not-vision"
        def analyze(self, image, context): return AnalysisResult(review=review_data(context["asset_sha"]), card=card_data())
    finished = run_analysis_job(library, job["id"], SyntheticAnalyzer())
    assert finished["status"] == "succeeded"
    actual = library.reference(ref["id"])
    assert actual["card"] and actual["review_actor"] == "ai"
    assert not actual["field_ready"] and actual["accepted_fingerprint"] is None


def test_worker_failure_preserves_honest_state(client, project, library):
    ref = add_reference(client, project)
    ref = client.patch(f"/api/references/{ref['id']}", json={"expected_revision": ref["revision"], "decision": "keep"}).json()
    job = library.create_job(project["id"], JobInput(kind="analysis", reference_ids=[ref["id"]]))
    class FailedAnalyzer:
        model = "fixture"
        def analyze(self, image, context): raise ProviderError("fixture network failure")
    with pytest.raises(ProviderError): run_analysis_job(library, job["id"], FailedAnalyzer())
    assert library.job(job["id"])["status"] == "failed"
    assert library.reference(ref["id"])["card"] is None


@pytest.mark.parametrize("url", ["http://i.pinimg.com/a.jpg", "https://127.0.0.1/a.jpg", "https://pinimg.com.evil.example/a", "https://user:pass@i.pinimg.com/a"])
def test_collector_rejects_private_unapproved_or_credential_urls(url):
    assert not allowed_image_url(url)


def test_visible_capture_preserves_observed_url_and_does_not_classify(library, project):
    job = library.create_job(project["id"], JobInput(kind="collection"))
    url = "https://i.pinimg.com/236x/exact-observed-url.png"
    class Page:
        url = "https://www.pinterest.com/pin/12345/"
        def evaluate(self, expression):
            return [{"currentSrc": url, "width": 800, "height": 1200, "title": "Cosplay equipment fixture", "page_url": self.url}]
    def respond(request):
        assert str(request.url) == url
        assert "cookie" not in request.headers
        return httpx.Response(200, content=image_bytes())
    result = capture_page(library, job["id"], Page(), transport=httpx.MockTransport(respond))
    assert result["created"] == 1
    ref = library.references(project["id"])["items"][0]
    assert ref["source"]["image_url"] == url and ref["review"] is None
    assert not ref["field_ready"]
    with pytest.raises(Problem): download_observed(url, 100000, transport=httpx.MockTransport(lambda request: httpx.Response(403)))


def test_notion_sync_idempotency_and_ambiguous_failure(tmp_path, monkeypatch):
    monkeypatch.setenv("NOTION_API_TOKEN", "fixture-not-live")
    monkeypatch.setenv("NOTION_PARENT_PAGE_ID", "fixture-parent")
    task = tmp_path / "task.md"; task.write_text("# Intent\nFix evidence gates", encoding="utf-8")
    seen = []
    def respond(request):
        seen.append(request)
        assert request.headers["Notion-Version"] == "2025-09-03"
        return httpx.Response(200, json={"id": "fixture-page"})
    transport = httpx.MockTransport(respond)
    result = sync_task_to_notion(task, tmp_path / "receipts", "test-sha", transport=transport)
    assert result["status"] == "synced"
    sync_task_to_notion(task, tmp_path / "receipts", "test-sha", transport=transport)
    assert len(seen) == 1
    task.write_text("# Intent\nUpdated", encoding="utf-8")
    sync_task_to_notion(task, tmp_path / "receipts", "next-sha", transport=transport)
    assert seen[-1].method == "PATCH"
    task.write_text("# Intent\nThird update", encoding="utf-8")
    def timeout(request): raise httpx.ReadTimeout("fixture")
    with pytest.raises(ProviderError): sync_task_to_notion(task, tmp_path / "receipts", transport=httpx.MockTransport(timeout))
    with pytest.raises(ProviderError, match="结果未知"): sync_task_to_notion(task, tmp_path / "receipts", transport=transport)
