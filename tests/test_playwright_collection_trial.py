from __future__ import annotations

import hashlib
from pathlib import Path
import tempfile
from types import SimpleNamespace
import unittest

from tools.playwright_collection_trial import (
    TrialError,
    bounded_navigation_timeout,
    is_download_navigation_signal,
    launch_visible_context,
    profile_lock,
    pump_visible_context,
    resolve_profile,
    save_attachment,
    validate_http_url,
)


TEST_TMP = Path(__file__).resolve().parent


class FakeTargetClosed(Exception):
    pass


class FakeLifecycleFailure(Exception):
    pass


class FakePage:
    def __init__(self, events=()):
        self.events = list(events)
        self.closed = False
        self.waits = []

    def is_closed(self):
        return self.closed

    def wait_for_timeout(self, milliseconds):
        self.waits.append(milliseconds)
        if self.events:
            event = self.events.pop(0)
            if isinstance(event, BaseException):
                raise event
        return None


class FakeContext:
    def __init__(self, pages):
        self.pages = pages


class FakeDownload:
    def __init__(self, payload, suggested_filename="download.bin"):
        self.payload = payload
        self.suggested_filename = suggested_filename
        self.save_calls = 0

    def save_as(self, destination):
        self.save_calls += 1
        Path(destination).write_bytes(self.payload)


class FakePending:
    def __init__(self, download, ready):
        self.download = download
        self.ready = ready
        self.value = None
        self.exited = False

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc, traceback):
        self.exited = True
        if exc_type is None:
            if not self.ready:
                raise TimeoutError("real download event did not arrive")
            self.value = self.download
        return False


class PlaywrightCollectionTrialTests(unittest.TestCase):
    def test_url_boundary_accepts_only_http_and_https_with_host(self):
        self.assertEqual(validate_http_url("https://example.com/path"), "https://example.com/path")
        self.assertEqual(validate_http_url("http://127.0.0.1:8080/"), "http://127.0.0.1:8080/")
        for value in ("file:///tmp/a", "data:text/plain,x", "https:///missing", ""):
            with self.subTest(value=value), self.assertRaises(TrialError):
                validate_http_url(value)
        with self.assertRaises(TrialError):
            validate_http_url("https://user:secret@example.com/")

    def test_navigation_timeout_is_bounded(self):
        self.assertEqual(bounded_navigation_timeout(1_000), 1_000)
        self.assertEqual(bounded_navigation_timeout(120_000), 120_000)
        for value in (999, 120_001, "bad"):
            with self.subTest(value=value), self.assertRaises(TrialError):
                bounded_navigation_timeout(value)

    def test_default_profile_is_project_local(self):
        with tempfile.TemporaryDirectory(dir=TEST_TMP) as temp_dir:
            root = Path(temp_dir)
            profile = resolve_profile(project_root=root)
            self.assertEqual(profile, (root / ".local" / "playwright-collection-profile").resolve())

    def test_profile_cannot_escape_project_local_or_use_default_name(self):
        with tempfile.TemporaryDirectory(dir=TEST_TMP) as temp_dir:
            root = Path(temp_dir)
            with self.assertRaises(TrialError):
                resolve_profile(root / "outside-profile", project_root=root)
            with self.assertRaises(TrialError):
                resolve_profile(root / ".local" / "Default", project_root=root)

    def test_profile_lock_rejects_concurrent_reuse(self):
        with tempfile.TemporaryDirectory(dir=TEST_TMP) as temp_dir:
            profile = Path(temp_dir) / ".local" / "profile"
            with profile_lock(profile):
                with self.assertRaises(TrialError):
                    with profile_lock(profile):
                        pass
            with profile_lock(profile):
                pass
            self.assertTrue(profile.is_dir())

    def test_visible_launch_has_explicit_timeout(self):
        captured = {}

        class FakeChromium:
            def launch_persistent_context(self, **kwargs):
                captured.update(kwargs)
                return object()

        launch_visible_context(SimpleNamespace(chromium=FakeChromium()), Path("profile"))
        self.assertEqual(captured["timeout"], 30_000)
        self.assertFalse(captured["headless"])
        self.assertTrue(captured["accept_downloads"])

    def test_visible_lifecycle_pumps_page_until_closed(self):
        page = FakePage()
        context = FakeContext([page])

        class CloseAfterTwoPumps:
            def __init__(self):
                self.calls = 0

        original_wait = page.wait_for_timeout
        calls = CloseAfterTwoPumps()

        def wait(milliseconds):
            original_wait(milliseconds)
            calls.calls += 1
            if calls.calls == 2:
                page.closed = True

        page.wait_for_timeout = wait
        pump_visible_context(context, FakeTargetClosed)
        self.assertEqual(page.waits, [250, 250])

    def test_visible_lifecycle_handles_target_closed(self):
        page = FakePage([FakeTargetClosed("window closed")])
        pump_visible_context(FakeContext([page]), FakeTargetClosed)
        self.assertEqual(page.waits, [250])

    def test_visible_lifecycle_propagates_other_errors(self):
        page = FakePage([FakeLifecycleFailure("renderer failed")])
        with self.assertRaisesRegex(FakeLifecycleFailure, "renderer failed"):
            pump_visible_context(FakeContext([page]), FakeTargetClosed)

    def test_attachment_name_cannot_escape_or_overwrite(self):
        payload = b"download payload"

        class FakeDownloadPage:
            def __init__(self, suggested_filename):
                self.download = FakeDownload(payload, suggested_filename)

            def expect_download(self, timeout):
                return FakePending(self.download, ready=True)

            def goto(self, *args, **kwargs):
                return None

        dangerous_names = (
            "..",
            "../../escape.bin",
            "NUL",
            "CON.txt",
            "file.txt:stream",
            "existing.bin",
        )
        with tempfile.TemporaryDirectory(dir=TEST_TMP) as temp_dir:
            root = Path(temp_dir)
            output_dir = root / "downloads"
            output_dir.mkdir()
            existing = output_dir / "existing.bin"
            existing.write_bytes(b"keep me")
            for name in dangerous_names:
                with self.subTest(name=name):
                    result = save_attachment(FakeDownloadPage(name), "http://example.test/file", output_dir)
                    saved = Path(result["path"]).resolve()
                    self.assertEqual(saved.parent, output_dir.resolve())
                    self.assertTrue(saved.name.startswith("attachment-"))
                    self.assertEqual(saved.read_bytes(), payload)
            self.assertEqual(existing.read_bytes(), b"keep me")
            self.assertFalse((root / "escape.bin").exists())

    def test_download_navigation_signal_waits_for_real_event_and_hashes(self):
        payload = b"download event payload"
        download = FakeDownload(payload)

        class FakeDownloadPage:
            def __init__(self):
                self.pending = None
                self.goto_called = False

            def expect_download(self, timeout):
                self.pending = FakePending(download, ready=True)
                return self.pending

            def goto(self, *args, **kwargs):
                self.goto_called = True
                raise RuntimeError(
                    "Page.goto: Download is starting\n"
                    "=========================== logs ===========================\n"
                )

        with tempfile.TemporaryDirectory(dir=TEST_TMP) as temp_dir:
            output_dir = Path(temp_dir) / "downloads"
            page = FakeDownloadPage()
            result = save_attachment(page, "https://example.test/attachment", output_dir)
            self.assertTrue(page.goto_called)
            self.assertTrue(page.pending.exited)
            self.assertEqual(result["sha256"], hashlib.sha256(payload).hexdigest())
            self.assertEqual(download.save_calls, 1)

    def test_download_signal_without_real_event_times_out(self):
        download = FakeDownload(b"must not save")

        class FakeDownloadPage:
            def __init__(self):
                self.pending = None

            def expect_download(self, timeout):
                self.pending = FakePending(download, ready=False)
                return self.pending

            def goto(self, *args, **kwargs):
                raise RuntimeError("Page.goto: Download is starting")

        with tempfile.TemporaryDirectory(dir=TEST_TMP) as temp_dir:
            page = FakeDownloadPage()
            with self.assertRaisesRegex(TimeoutError, "real download event"):
                save_attachment(page, "https://example.test/attachment", Path(temp_dir) / "downloads")
            self.assertTrue(page.pending.exited)
            self.assertEqual(download.save_calls, 0)

    def test_download_navigation_does_not_swallow_network_error(self):
        download = FakeDownload(b"must not save")

        class FakeDownloadPage:
            def __init__(self):
                self.pending = None

            def expect_download(self, timeout):
                self.pending = FakePending(download, ready=True)
                return self.pending

            def goto(self, *args, **kwargs):
                raise RuntimeError(
                    "Page.goto: net::ERR_CONNECTION_RESET at https://example.test/attachment"
                )

        with tempfile.TemporaryDirectory(dir=TEST_TMP) as temp_dir:
            page = FakeDownloadPage()
            with self.assertRaisesRegex(RuntimeError, "ERR_CONNECTION_RESET"):
                save_attachment(page, "https://example.test/attachment", Path(temp_dir) / "downloads")
            self.assertTrue(page.pending.exited)
            self.assertEqual(download.save_calls, 0)

    def test_download_signal_match_is_strict(self):
        self.assertTrue(
            is_download_navigation_signal(RuntimeError("Page.goto: Download is starting\nlogs"))
        )
        self.assertTrue(
            is_download_navigation_signal(
                RuntimeError("Page.goto: net::ERR_ABORTED at https://example.test/file")
            )
        )
        for message in (
            "Page.goto: net::ERR_CONNECTION_RESET at https://example.test/file",
            "Page.goto: Download is starting elsewhere",
            "Download is starting",
        ):
            expected = message == "Download is starting"
            with self.subTest(message=message):
                self.assertEqual(is_download_navigation_signal(RuntimeError(message)), expected)


if __name__ == "__main__":
    unittest.main()
