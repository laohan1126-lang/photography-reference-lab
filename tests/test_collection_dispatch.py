"""Production dispatch parity. No real browser, vendor CLI, or live search.

Missing configuration uses the real transport and synthetic library database.
Configured dispatch replaces only the transport boundary; its subprocess/import
behavior is covered separately by test_collection_runner/test_collect_adapter.
"""
import json
import sys
from unittest.mock import Mock

import pytest

from ref_lab import agent_collection, collector
from ref_lab.models import JobInput


def set_runtime(monkeypatch, pytest_marker, bsk_present):
    if pytest_marker:
        monkeypatch.setenv("PYTEST_CURRENT_TEST", "synthetic dispatch parity probe")
    else:
        monkeypatch.delenv("PYTEST_CURRENT_TEST", raising=False)
    discover = Mock(return_value="simulated-bsk" if bsk_present else None)
    connect = Mock(side_effect=AssertionError("Unexpected automatic browser startup"))
    scrape = Mock(side_effect=AssertionError("Unexpected legacy collector bypass"))
    monkeypatch.setattr(collector, "find_bsk_cli", discover)
    monkeypatch.setattr(collector, "ensure_bsk_browser", connect)
    monkeypatch.setattr(collector, "collect_via_bsk", scrape)
    return discover, connect, scrape


@pytest.mark.parametrize("pytest_marker", [False, True])
@pytest.mark.parametrize("bsk_present", [False, True])
def test_no_adapter_stays_blocked_without_browser_fallback(library, project, monkeypatch, pytest_marker, bsk_present):
    boundaries = set_runtime(monkeypatch, pytest_marker, bsk_present)
    monkeypatch.delenv("LAB_COLLECTION_COMMAND", raising=False)
    job = library.create_job(project["id"], JobInput(kind="collection"))
    result = collector.run_browser_collection_job(library, job["id"])
    assert result["status"] == "blocked"
    assert "未配置 LAB_COLLECTION_COMMAND" in result["detail"]
    assert library.job(job["id"])["status"] == "blocked"
    assert not result["imported_ids"]
    for boundary in boundaries:
        boundary.assert_not_called()


@pytest.mark.parametrize("pytest_marker", [False, True])
@pytest.mark.parametrize("bsk_present", [False, True])
def test_configured_adapter_is_not_overridden_by_browser_discovery(library, project, monkeypatch, pytest_marker, bsk_present):
    boundaries = set_runtime(monkeypatch, pytest_marker, bsk_present)
    monkeypatch.setenv("LAB_COLLECTION_COMMAND", json.dumps([
        sys.executable, "adapter.py", "{task_file}", "{result_file}"
    ]))
    job = library.create_job(project["id"], JobInput(kind="collection"))
    # A dispatch sentinel, explicitly not evidence of completed collection.
    receipt = {"status": "blocked", "detail": "synthetic adapter receipt"}
    transport = Mock(return_value=receipt)
    monkeypatch.setattr(agent_collection, "run_collection_attempt", transport)
    result = collector.run_browser_collection_job(library, job["id"])
    assert result is receipt
    transport.assert_called_once_with(library, job["id"])
    for boundary in boundaries:
        boundary.assert_not_called()
