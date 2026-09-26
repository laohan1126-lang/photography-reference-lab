"""Bounded browser assertions without page-side eval or CSP exceptions."""
from __future__ import annotations

import time

from playwright.sync_api import Page


def wait_until(page: Page, expression: str, timeout: int = 10000) -> None:
    """Poll through Playwright's evaluation command, not a page-side eval loop.

    wait_for_function's polling implementation uses eval in the main world in
    some browser/Playwright versions. Keep the application's strict CSP intact.
    This helper is only for test-owned predicates, never untrusted expressions.
    """
    deadline = time.monotonic() + timeout / 1000
    while True:
        if page.evaluate(expression):
            return
        if time.monotonic() >= deadline:
            raise AssertionError(f"Browser condition timed out after {timeout} ms: {expression}")
        page.wait_for_timeout(25)
