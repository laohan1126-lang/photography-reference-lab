import json

import pytest

from ref_lab.browser_recovery import (
    BrowserError,
    BrowserInfrastructureError,
    PlatformRestrictionError,
    classify_bsk_error,
    is_infrastructure_error,
)


def _error(code, message="", data=None):
    payload = {"code": code, "message": message}
    if data is not None:
        payload["data"] = data
    return classify_bsk_error("evaluate", 1, json.dumps(payload), "")


@pytest.mark.parametrize(
    ("code", "message"),
    [
        ("ipc_access_denied", "IPC access denied (HTTP 403)"),
        ("protocol_mismatch", "unsupported protocol version"),
        ("cooperation_sync_required", "cooperation sync required"),
        ("user_aborted", "operation aborted by user"),
    ],
)
def test_control_failures_keep_their_semantics_and_are_not_platform_errors(code, message):
    error = _error(code, message)

    assert isinstance(error, BrowserInfrastructureError)
    assert error.code == code
    assert error.is_timeout is False
    assert not isinstance(error, PlatformRestrictionError)
    assert is_infrastructure_error(error) is True


@pytest.mark.parametrize(
    ("stdout", "stderr"),
    [
        (json.dumps({"code": "session_busy", "message": "busy"}), ""),
        ("", "error: previous operation still settling; session unfinished"),
    ],
)
def test_session_busy_is_distinct_from_timeout_and_stops_retry_recovery(stdout, stderr):
    error = classify_bsk_error("evaluate", 1, stdout, stderr)

    assert error.code == "session_busy"
    assert isinstance(error, BrowserInfrastructureError)
    assert error.is_timeout is False
    assert is_infrastructure_error(error) is True


@pytest.mark.parametrize(
    ("reason", "expected_code", "expected_timeout"),
    [
        ("cooperation_sync_required", "cooperation_sync_required", False),
        ("renderer_read_timeout", "renderer_not_answering", True),
    ],
)
def test_real_permission_and_cdp_payload_reasons_are_classified(reason, expected_code, expected_timeout):
    code = "permission_denied" if reason == "cooperation_sync_required" else "cdp_failed"
    error = _error(code, "operation failed", {"reason": reason})

    assert isinstance(error, BrowserInfrastructureError)
    assert error.code == expected_code
    assert error.is_timeout is expected_timeout
    assert error.reason == reason
    assert not isinstance(error, PlatformRestrictionError)


def test_user_stop_wins_over_unknown_effect_and_preserves_safety_fields():
    error = _error(
        "permission_denied",
        "cancel requested after operation was dispatched",
        {"reason": "user_aborted", "dispatched": True, "effect_state": "unknown"},
    )

    assert isinstance(error, BrowserInfrastructureError)
    assert error.code == "user_aborted"
    assert error.is_timeout is False
    assert error.reason == "user_aborted"
    assert error.dispatched is True
    assert error.effect_state == "unknown"


def test_non_user_cancel_with_unknown_effect_is_outcome_unknown():
    error = _error(
        "cdp_failed",
        "operation cancelled by controller",
        {"reason": "effect_receipt_missing", "dispatched": True, "effect_state": "unknown"},
    )

    assert isinstance(error, BrowserInfrastructureError)
    assert error.code == "operation_outcome_unknown"
    assert error.is_timeout is False
    assert error.dispatched is True
    assert error.effect_state == "unknown"


def test_explicit_unknown_outcome_reason_does_not_require_cancel_text():
    error = _error(
        "cdp_failed",
        "operation failed",
        {"reason": "operation_outcome_unknown", "dispatched": True, "effect_state": "unknown"},
    )

    assert isinstance(error, BrowserInfrastructureError)
    assert error.code == "operation_outcome_unknown"
    assert error.is_timeout is False


def test_cleanup_timeout_keeps_its_existing_code():
    error = _error("cleanup_timeout", "background execution cleanup timed out")

    assert isinstance(error, BrowserInfrastructureError)
    assert error.code == "cleanup_timeout"
    assert error.is_timeout is True


def test_public_browser_error_fields_remain_backward_compatible():
    error = BrowserError("legacy")

    assert error.reason == ""
    assert error.dispatched is None
    assert error.effect_state == ""


def test_raw_output_is_sanitized_bounded_and_keeps_the_actual_tail_error():
    stderr = (
        "token=secret-value\n"
        + ("irrelevant renderer log line\n" * 120)
        + "IPC access denied at C:\\Users\\Dell\\AppData\\Local\\bsk.pipe"
    )

    error = classify_bsk_error("evaluate", 1, "", stderr)

    assert error.code == "ipc_access_denied"
    assert len(error.raw_output) <= 4000
    assert "IPC access denied" in error.raw_output
    assert "secret-value" not in error.raw_output
    assert "C:\\Users\\Dell" not in error.raw_output
