#!/usr/bin/env python3
"""Visible, persistent Playwright window for a bounded collection trial.

The account/site state stays in a project-local profile. This module does not
install browsers, read another profile, or bypass site access controls.
"""
from __future__ import annotations

import argparse
from contextlib import contextmanager
import hashlib
import os
from pathlib import Path
import sys
import tempfile
from urllib.parse import urlsplit


PROJECT_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_PROFILE = PROJECT_ROOT / ".local" / "playwright-collection-profile"
MIN_NAVIGATION_TIMEOUT_MS = 1_000
MAX_NAVIGATION_TIMEOUT_MS = 120_000


class TrialError(RuntimeError):
    """An expected setup or collection error with a user-readable message."""


def validate_http_url(value: str) -> str:
    url = str(value or "").strip()
    try:
        parsed = urlsplit(url)
    except ValueError as exc:
        raise TrialError("Invalid URL.") from exc
    if parsed.scheme not in {"http", "https"} or not parsed.hostname:
        raise TrialError("Only http:// and https:// URLs with a host are allowed.")
    if parsed.username or parsed.password:
        raise TrialError("URLs with embedded usernames or passwords are not allowed.")
    return url


def bounded_navigation_timeout(value: int | str) -> int:
    try:
        timeout = int(value)
    except (TypeError, ValueError) as exc:
        raise TrialError("Navigation timeout must be an integer in milliseconds.") from exc
    if not MIN_NAVIGATION_TIMEOUT_MS <= timeout <= MAX_NAVIGATION_TIMEOUT_MS:
        raise TrialError(
            f"Navigation timeout must be between {MIN_NAVIGATION_TIMEOUT_MS}"
            f" and {MAX_NAVIGATION_TIMEOUT_MS} milliseconds."
        )
    return timeout


def _navigation_timeout_arg(value: str) -> int:
    try:
        return bounded_navigation_timeout(value)
    except TrialError as exc:
        raise argparse.ArgumentTypeError(str(exc)) from exc


def _known_default_profile_roots() -> list[Path]:
    roots: list[Path] = []
    local_app_data = os.environ.get("LOCALAPPDATA")
    app_data = os.environ.get("APPDATA")
    if local_app_data:
        roots.extend(
            [
                Path(local_app_data) / "Google" / "Chrome" / "User Data",
                Path(local_app_data) / "Microsoft" / "Edge" / "User Data",
            ]
        )
    if app_data:
        roots.append(Path(app_data) / "Mozilla" / "Firefox" / "Profiles")
    return [root.resolve() for root in roots]


def resolve_profile(
    raw_profile: str | Path | None = None,
    *,
    project_root: str | Path = PROJECT_ROOT,
) -> Path:
    root = Path(project_root).resolve()
    local_root = (root / ".local").resolve()
    profile = (
        Path(raw_profile).expanduser()
        if raw_profile
        else root / ".local" / "playwright-collection-profile"
    )
    profile = profile.resolve()
    if profile == local_root or not profile.is_relative_to(local_root):
        raise TrialError(
            f"Profile must be a child of the project-local directory: {local_root}"
        )
    if profile.name.casefold() in {"default", "user data"}:
        raise TrialError("The browser's default user-data directory is not allowed.")
    for browser_root in _known_default_profile_roots():
        if profile.is_relative_to(browser_root):
            raise TrialError("Chrome, Edge, and Firefox default profiles are not allowed.")
    return profile


@contextmanager
def profile_lock(profile: Path):
    """Hold an OS-owned lock so two trial processes cannot share a profile."""
    try:
        profile.mkdir(mode=0o700, parents=True, exist_ok=True)
    except OSError as exc:
        raise TrialError(f"Cannot create the dedicated profile directory: {profile}") from exc
    lock_path = profile / ".playwright-collection-trial.lock"
    try:
        handle_context = lock_path.open("a+b")
    except OSError as exc:
        raise TrialError(f"Cannot open the profile lock file: {lock_path}") from exc
    with handle_context as handle:
        handle.seek(0, os.SEEK_END)
        if handle.tell() == 0:
            handle.write(b"0")
            handle.flush()
        handle.seek(0)
        try:
            if os.name == "nt":
                import msvcrt

                msvcrt.locking(handle.fileno(), msvcrt.LK_NBLCK, 1)
            else:
                import fcntl

                fcntl.flock(handle, fcntl.LOCK_EX | fcntl.LOCK_NB)
        except OSError as exc:
            raise TrialError(f"Profile is already in use by another Playwright trial: {profile}") from exc
        try:
            yield
        finally:
            handle.seek(0)
            if os.name == "nt":
                msvcrt.locking(handle.fileno(), msvcrt.LK_UNLCK, 1)
            else:
                fcntl.flock(handle, fcntl.LOCK_UN)


def _playwright_api():
    try:
        from playwright.sync_api import Error, TimeoutError, sync_playwright
        from playwright._impl._errors import TargetClosedError
    except ImportError as exc:
        raise TrialError(
            "Playwright is unavailable; use the project Python environment with Playwright installed."
        ) from exc
    return Error, TimeoutError, TargetClosedError, sync_playwright


def launch_visible_context(playwright, profile: Path):
    """Launch the dedicated visible context; callers own its lifetime."""
    return playwright.chromium.launch_persistent_context(
        user_data_dir=str(profile),
        headless=False,
        accept_downloads=True,
        timeout=30_000,
    )


def navigate_page(page, url: str, timeout_ms: int):
    return page.goto(
        validate_http_url(url),
        wait_until="domcontentloaded",
        timeout=bounded_navigation_timeout(timeout_ms),
    )


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def is_download_navigation_signal(exc: BaseException) -> bool:
    """Accept only Playwright's known navigation-to-download messages."""
    lines = str(exc).splitlines()
    if not lines:
        return False
    first_line = lines[0].strip()
    return first_line in {
        "Download is starting",
        "Page.goto: Download is starting",
    } or first_line.startswith("Page.goto: net::ERR_ABORTED at http")


def save_attachment(page, url: str, output_dir: Path, timeout_ms: int = 30_000) -> dict:
    """Save one browser-provided attachment without guessing its URL."""
    output_dir.mkdir(parents=True, exist_ok=True)
    timeout_ms = bounded_navigation_timeout(timeout_ms)
    with page.expect_download(timeout=timeout_ms) as pending:
        try:
            page.goto(validate_http_url(url), wait_until="domcontentloaded", timeout=timeout_ms)
        except Exception as exc:
            # The context manager still has to produce a real download below.
            if not is_download_navigation_signal(exc):
                raise
    download = pending.value
    output_dir = output_dir.resolve()
    descriptor, raw_destination = tempfile.mkstemp(
        prefix="attachment-", suffix=".bin", dir=output_dir
    )
    os.close(descriptor)
    destination = Path(raw_destination)
    try:
        download.save_as(destination)
    except Exception:
        destination.unlink(missing_ok=True)
        raise
    return {
        "path": str(destination),
        "suggested_filename": download.suggested_filename,
        "sha256": sha256_file(destination),
        "bytes": destination.stat().st_size,
    }


def pump_visible_context(context, target_closed_errors) -> None:
    """Pump Playwright events until the user closes every page."""
    while True:
        try:
            pages = [page for page in context.pages if not page.is_closed()]
            if not pages:
                return
            pages[0].wait_for_timeout(250)
        except target_closed_errors:
            return


def open_for_manual_use(
    url: str,
    *,
    profile: str | Path | None = None,
    timeout_ms: int = 30_000,
) -> None:
    url = validate_http_url(url)
    timeout_ms = bounded_navigation_timeout(timeout_ms)
    profile = resolve_profile(profile)
    Error, TimeoutError, TargetClosedError, sync_playwright = _playwright_api()

    with profile_lock(profile), sync_playwright() as playwright:
        try:
            context = launch_visible_context(playwright, profile)
        except Error as exc:
            raise TrialError(f"Cannot launch visible Chromium: {exc}") from exc
        page = context.pages[0] if context.pages else context.new_page()
        try:
            try:
                response = navigate_page(page, url, timeout_ms)
            except TimeoutError as exc:
                raise TrialError(f"DOM navigation exceeded {timeout_ms} ms: {url}") from exc
            except Error as exc:
                raise TrialError(f"Page navigation failed: {exc}") from exc
            status = response.status if response is not None else "no HTTP response"
            print(f"profile={profile}", flush=True)
            print(f"url={page.url}", flush=True)
            print(f"http_status={status}", flush=True)
            print("Log in manually in the visible window. Close the window to finish; the profile is retained.", flush=True)
            try:
                pump_visible_context(context, TargetClosedError)
            except Error as exc:
                raise TrialError(f"Browser lifecycle failed: {exc}") from exc
        finally:
            try:
                context.close()
            except TargetClosedError:
                pass
            except Error as exc:
                raise TrialError(f"Visible browser cleanup failed: {exc}") from exc


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Open visible Playwright Chromium with a dedicated persistent profile."
    )
    parser.add_argument("--url", required=True, help="HTTP or HTTPS URL to open")
    parser.add_argument(
        "--profile",
        help=f"Dedicated profile path under project .local (default: {DEFAULT_PROFILE})",
    )
    parser.add_argument(
        "--navigation-timeout-ms",
        default=30_000,
        type=_navigation_timeout_arg,
        help="Navigation timeout from 1000 to 120000 milliseconds",
    )
    return parser


def main(argv: list[str] | None = None) -> int:
    for stream in (sys.stdout, sys.stderr):
        if hasattr(stream, "reconfigure"):
            stream.reconfigure(errors="backslashreplace")
    args = build_parser().parse_args(argv)
    try:
        open_for_manual_use(
            args.url,
            profile=args.profile,
            timeout_ms=args.navigation_timeout_ms,
        )
    except KeyboardInterrupt:
        print("Interrupted; the dedicated profile was retained.", file=sys.stderr)
        return 130
    except TrialError as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 2
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
