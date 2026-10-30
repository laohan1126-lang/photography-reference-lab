#!/usr/bin/env python3
"""Browser-only local fixture check for playwright_collection_trial.

This is intentionally separate from the interactive login window. A passing
run proves fixture navigation, a browser download hash, and synthetic
localStorage persistence across a profile close/reopen. It does not prove any
website login or collection access.
"""
from __future__ import annotations

from hashlib import sha256
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
import json
from pathlib import Path
import sys
import tempfile
import threading

from tools.playwright_collection_trial import (
    TrialError,
    launch_visible_context,
    navigate_page,
    profile_lock,
    resolve_profile,
    save_attachment,
)


ATTACHMENT_BYTES = b"playwright-trial-attachment\x00v1\n"
PROJECT_ROOT = Path(__file__).resolve().parents[1]


class FixtureHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        if self.path == "/page":
            body = (
                "<!doctype html><html><head><title>Playwright Trial Fixture</title></head>"
                "<body><h1 id='heading'>fixture-navigation-ok</h1>"
                "<input id='note'></body></html>"
            ).encode("utf-8")
            self.send_response(200)
            self.send_header("Content-Type", "text/html; charset=utf-8")
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)
            return
        if self.path == "/attachment":
            self.send_response(200)
            self.send_header("Content-Type", "application/octet-stream")
            self.send_header("Content-Disposition", "attachment; filename=trial.bin")
            self.send_header("Content-Length", str(len(ATTACHMENT_BYTES)))
            self.end_headers()
            self.wfile.write(ATTACHMENT_BYTES)
            return
        self.send_response(404)
        self.end_headers()

    def log_message(self, format, *args):
        return


def run_fixture_check() -> dict:
    try:
        from playwright.sync_api import sync_playwright
    except ImportError as exc:
        raise TrialError("The verifier requires Playwright in the project Python environment.") from exc

    server = ThreadingHTTPServer(("127.0.0.1", 0), FixtureHandler)
    thread = threading.Thread(target=server.serve_forever, name="playwright-trial-fixture", daemon=True)
    thread.start()
    origin = f"http://127.0.0.1:{server.server_port}"
    receipt: dict = {"website_login": "NOT_TESTED"}
    try:
        local_root = PROJECT_ROOT / ".local"
        local_root.mkdir(parents=True, exist_ok=True)
        with tempfile.TemporaryDirectory(prefix="playwright-trial-", dir=local_root) as temp_dir:
            project_root = Path(temp_dir)
            profile = resolve_profile(project_root / ".local" / "fixture-profile", project_root=project_root)
            download_dir = project_root / "downloads"
            with profile_lock(profile), sync_playwright() as playwright:
                context = launch_visible_context(playwright, profile)
                page = context.pages[0] if context.pages else context.new_page()
                try:
                    navigate_page(page, origin + "/page", 30_000)
                    assert page.title() == "Playwright Trial Fixture"
                    assert page.locator("#heading").inner_text() == "fixture-navigation-ok"
                    page.fill("#note", "synthetic-write")
                    assert page.input_value("#note") == "synthetic-write"
                    page.evaluate("localStorage.setItem('trial-key', 'persisted-value')")
                    attachment = save_attachment(page, origin + "/attachment", download_dir)
                    expected_hash = sha256(ATTACHMENT_BYTES).hexdigest()
                    assert attachment["sha256"] == expected_hash
                finally:
                    context.close()

                reopened = launch_visible_context(playwright, profile)
                try:
                    page = reopened.pages[0] if reopened.pages else reopened.new_page()
                    navigate_page(page, origin + "/page", 30_000)
                    assert page.evaluate("localStorage.getItem('trial-key')") == "persisted-value"
                finally:
                    reopened.close()

            receipt.update(
                {
                    "fixture_navigation": "PASS",
                    "fixture_dom_write": "PASS",
                    "attachment_sha256": expected_hash,
                    "attachment_hash": "PASS",
                    "localstorage_reopen": "PASS",
                    "profile_retained_during_check": profile.is_dir(),
                }
            )
    finally:
        server.shutdown()
        server.server_close()
        thread.join(timeout=5)
    return receipt


def main() -> int:
    for stream in (sys.stdout, sys.stderr):
        if hasattr(stream, "reconfigure"):
            stream.reconfigure(errors="backslashreplace")
    try:
        print(json.dumps(run_fixture_check(), ensure_ascii=False, indent=2))
    except Exception as exc:
        print(f"ERROR: {type(exc).__name__}: {exc}")
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
