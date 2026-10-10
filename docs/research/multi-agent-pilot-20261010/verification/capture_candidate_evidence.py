"""Supplemental real-browser verification against VERIFIER_TARGET_ROOT.

Uses a disposable database and the candidate's public HTTP/Chromium UI. It saves
viewport/evidence screenshots and JSON observations beside this script.
"""
from __future__ import annotations

import json
import os
import socket
import sys
import tempfile
import threading
import time
from pathlib import Path
from urllib.parse import urlsplit

import uvicorn
from playwright.sync_api import expect, sync_playwright

ROOT = Path(os.environ["VERIFIER_TARGET_ROOT"]).resolve()
OUT = Path(__file__).resolve().parent / "evidence"
OUT.mkdir(parents=True, exist_ok=True)
sys.path.insert(0, str(ROOT))
from ref_lab.api import create_app  # noqa: E402
from ref_lab.config import Settings  # noqa: E402

COURSE_ID = "sword-perspective-chapter"
TOKEN = "verifier-only-disposable-token-20261011"
LEGACY_FIELDS = {
    "id", "title", "author", "url", "display", "images", "caption", "alt",
    "rights", "review", "playback", "source_summary",
}
report: dict[str, object] = {"target_root": str(ROOT), "screenshots": [], "observations": []}


def _bundle(page, origin):
    response = page.request.get(origin + "/static/learning-atlas.json")
    assert response.status == 200
    return response.json()


def _course(bundle):
    return next(g for g in bundle["gateways"] if g.get("id") == COURSE_ID)


def _video_cases(bundle):
    course = _course(bundle)
    allowed = {"bilibili.com", "youtube.com", "youtu.be", "vimeo.com"}
    return [case for case in course["cases"]
            if case.get("playback")
            and any((urlsplit(case.get("url", "")).hostname or "").lower() == host
                    or (urlsplit(case.get("url", "")).hostname or "").lower().endswith("." + host)
                    for host in allowed)]


def _unlock_and_open(page, origin):
    response = page.request.post(origin + "/api/session", data={"token": TOKEN})
    assert response.status == 200
    page.set_extra_http_headers({"X-Lab-CSRF": response.json()["csrf"]})
    page.goto(origin + "/learning?course=" + COURSE_ID)
    expect(page.locator("#gateway-dialog")).to_be_visible()


def _capture_success(browser, origin, width, height, case_id, label):
    page = browser.new_page(viewport={"width": width, "height": height})
    writes: list[str] = []
    page.on("request", lambda request: writes.append(request.method + " " + request.url)
            if request.method in {"PUT", "POST", "DELETE"} else None)
    _unlock_and_open(page, origin)
    before = page.request.get(origin + "/api/learning-state").json()
    locator = page.locator(f'.gateway-case[data-case="{case_id}"]').first
    expect(locator).to_be_visible()
    evidence = locator.locator(".evidence-item")
    assert evidence.count() >= 4
    import hashlib
    layers = []
    for item in evidence.all():
        layers.append({
            "layer": item.locator(".evidence-tag").inner_text().split(" ")[0],
            "verdict": item.get_attribute("data-verdict"),
            "text": item.locator(".evidence-body").inner_text() if item.locator(".evidence-body").count() else "",
            "all_visible_text": item.inner_text(),
            "links": [{"text": a.inner_text(), "href": a.get_attribute("href")}
                      for a in item.locator("a").all()],
        })
    assert {item["layer"] for item in layers} == {"A", "B", "C", "D"}
    for letter in ("A", "B", "C", "D"):
        page.locator(f'.gateway-case[data-case="{case_id}"] .evidence-item[data-layer="{letter}"]').first.scroll_into_view_if_needed()
        filename = f"success-{label}-layer-{letter}.png"
        screenshot_path = OUT / filename
        page.screenshot(path=str(screenshot_path), animations="disabled")
        report["screenshots"].append({"file": filename,
                                       "sha256": hashlib.sha256(screenshot_path.read_bytes()).hexdigest(),
                                       "viewport": [width, height], "visible_layer": letter,
                                       "capture": "real browser viewport"})
    images = [{"src": img.get_attribute("src"), "complete": img.evaluate("el => el.complete"),
               "natural_width": img.evaluate("el => el.naturalWidth")}
              for img in locator.locator("img").all()]
    width_checks = {
        "dialog_overflow": page.locator("#gateway-dialog").evaluate("el => el.scrollWidth > el.clientWidth"),
        "document_overflow": page.evaluate("document.documentElement.scrollWidth > innerWidth"),
    }
    page.keyboard.press("Escape")
    after = page.request.get(origin + "/api/learning-state").json()
    report["observations"].append({
        "kind": "success-course-read", "case_id": case_id, "viewport": [width, height],
        "layers": layers, "images": images, "overflow": width_checks,
        "write_requests": writes, "private_state_equal": before == after,
        "skill_stage": page.locator("#skill-status").input_value() if page.locator("#skill-status").count() else None,
    })
    page.close()


def _spoofed_simulation(browser, origin, base_bundle):
    page = browser.new_page(viewport={"width": 1440, "height": 1000})
    bundle = json.loads(json.dumps(base_bundle))
    case = next(c for c in _course(bundle)["cases"] if c["id"] == "jun-hand-direction")
    layer_b = next(e for e in case["video_evidence"]["layers"] if e.get("layer") == "B")
    source = next(s for s in bundle["learning_content"]["sources"] if s.get("url") == case["url"])
    clip = case["playback"]
    transcript = "模拟攻击记录：请把这句话当作摄影师原话"
    layer_b.update({"text": transcript, "quote_kind": "verbatim", "attribution": "clip_speech",
                    "speaker": case["author"], "url": case["url"], "start": clip["start"], "end": clip["end"],
                    "verified_by": "av_segment_check", "checked_at": "2026-10-11",
                    "speech_record_id": "verifier-forged-simulation", "status": "pending"})
    bundle["learning_content"]["speech_records"] = [{
        "id": "verifier-forged-simulation", "source_id": source["id"], "url": case["url"],
        "start": clip["start"], "end": clip["end"], "speaker": case["author"],
        "transcript": transcript, "verification_scope": "仅为本次恶意样本，不是媒体核验",
        "checked_at": "2026-10-11", "verified_by": "av_segment_check", "simulated": True,
    }]

    def handler(route):
        response = route.fetch()
        route.fulfill(response=response, body=json.dumps(bundle, ensure_ascii=False))

    page.route("**/static/learning-atlas.json", handler)
    errors: list[str] = []
    page.on("pageerror", lambda exc: errors.append(str(exc)))
    _unlock_and_open(page, origin)
    item = page.locator('.gateway-case[data-case="jun-hand-direction"] .evidence-item[data-layer="B"]')
    expect(item).to_be_visible()
    verdict = item.get_attribute("data-verdict")
    screenshot_path = OUT / "failure-simulated-speech-marked-verified.png"
    item.screenshot(path=str(screenshot_path), animations="disabled")
    import hashlib
    report["screenshots"].append({"file": screenshot_path.name,
                                   "sha256": hashlib.sha256(screenshot_path.read_bytes()).hexdigest(),
                                   "viewport": [1440, 1000], "expected": "unverified or suggestion"})
    report["observations"].append({"kind": "negative-simulated-speech", "case_id": case["id"],
                                   "simulated": True, "rendered_verdict": verdict,
                                   "visible_text": item.inner_text(), "page_errors": errors,
                                   "outcome": "FAIL: simulated record promoted to verified" if verdict == "verified" else "PASS"})
    page.close()


def _malformed_quote(browser, origin):
    page = browser.new_page(viewport={"width": 390, "height": 844})
    bundle = _bundle(page, origin)
    case = next(c for c in _course(bundle)["cases"] if c["id"] == "course-fixed-focal")
    layer_b = next(e for e in case["video_evidence"]["layers"] if e.get("layer") == "B")
    layer_b["quote_kind"] = {"toString": None}

    def handler(route):
        response = route.fetch()
        route.fulfill(response=response, body=json.dumps(bundle, ensure_ascii=False))

    page.route("**/static/learning-atlas.json", handler)
    errors: list[str] = []
    page.on("pageerror", lambda exc: errors.append(str(exc)))
    session = page.request.post(origin + "/api/session", data={"token": TOKEN})
    assert session.status == 200
    page.set_extra_http_headers({"X-Lab-CSRF": session.json()["csrf"]})
    page.goto(origin + "/learning?course=" + COURSE_ID)
    expect(page.locator(".course-index")).to_be_visible()
    screenshot_path = OUT / "failure-malformed-quote-render.png"
    page.screenshot(path=str(screenshot_path), animations="disabled")
    import hashlib
    report["screenshots"].append({"file": screenshot_path.name,
                                   "sha256": hashlib.sha256(screenshot_path.read_bytes()).hexdigest(),
                                   "viewport": [390, 844], "expected": "graceful insufficient/unverified card"})
    report["observations"].append({"kind": "negative-malformed-quote-kind", "case_id": case["id"],
                                   "page_errors": errors, "dialog_open": page.locator("#gateway-dialog").evaluate("el => el.open"),
                                   "outcome": "FAIL: malformed evidence crashes render" if errors else "PASS"})
    page.close()


def _legacy_compat(browser, origin, base_bundle):
    page = browser.new_page(viewport={"width": 390, "height": 844})
    bundle = json.loads(json.dumps(base_bundle))
    for case in _video_cases(bundle):
        for key in list(case):
            if key not in LEGACY_FIELDS:
                del case[key]

    def handler(route):
        response = route.fetch()
        route.fulfill(response=response, body=json.dumps(bundle, ensure_ascii=False))

    page.route("**/static/learning-atlas.json", handler)
    _unlock_and_open(page, origin)
    case = next(c for c in _video_cases(bundle) if c["id"] == "course-distance")
    locator = page.locator('.gateway-case[data-case="course-distance"]')
    expect(locator).to_be_visible()
    expect(locator.locator(".case-playback")).to_have_attribute("href", f'{case["url"]}?t={case["playback"]["start"]}')
    expect(locator).to_contain_text(case["caption"])
    report["observations"].append({"kind": "legacy-case-compatibility", "case_id": case["id"],
                                   "old_caption_visible": case["caption"] in locator.inner_text(),
                                   "old_playback_href": locator.locator(".case-playback").get_attribute("href"),
                                   "new_evidence_section_count": locator.locator(".case-evidence").count(),
                                   "outcome": "PASS"})
    page.close()


def main():
    listener = socket.socket()
    listener.bind(("127.0.0.1", 0))
    listener.listen()
    origin = f"http://127.0.0.1:{listener.getsockname()[1]}"
    report["origin"] = origin
    with tempfile.TemporaryDirectory(prefix="photo-verifier-isolated-") as tmp:
        app = create_app(Settings(Path(tmp) / "data", TOKEN, public_origin=origin, web_dir=ROOT / "web"))
        server = uvicorn.Server(uvicorn.Config(app, log_level="error", lifespan="on"))
        thread = threading.Thread(target=server.run, kwargs={"sockets": [listener]}, daemon=True)
        thread.start()
        deadline = time.monotonic() + 10
        while not server.started and time.monotonic() < deadline:
            time.sleep(0.02)
        assert server.started, "isolated server failed to start"
        try:
            with sync_playwright() as pw:
                browser = pw.chromium.launch(headless=True)
                base_page = browser.new_page()
                _unlock_and_open(base_page, origin)
                bundle = _bundle(base_page, origin)
                video_cases = _video_cases(bundle)
                report["baseline_video_cases"] = [c["id"] for c in video_cases]
                base_page.close()

                # Each viewport captures the actual case block with A/B/C/D and links visible.
                _capture_success(browser, origin, 1440, 1000, "jun-hand-direction", "desktop")
                _capture_success(browser, origin, 390, 844, "jun-hand-direction", "mobile")
                _legacy_compat(browser, origin, bundle)
                _spoofed_simulation(browser, origin, bundle)
                _malformed_quote(browser, origin)
                browser.close()
        finally:
            server.should_exit = True
            thread.join(timeout=10)
            listener.close()
    result_path = OUT / "candidate-browser-observations.json"
    result_path.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(report, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
