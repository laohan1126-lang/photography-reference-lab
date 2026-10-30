"""One BrowserSkill action per fresh observation, within one caller deadline."""
from __future__ import annotations

import json
import subprocess
import time


_ACTIONS = frozenset({
    "navigate", "back", "forward", "reload", "evaluate", "click", "hover", "wheel",
    "scroll-to", "fill", "press", "select", "drag", "focus", "blur", "upload", "download",
})


def run_bsk(argv, *, timeout=35, initial_navigation=False, **kwargs):
    """Never replay an action: a failed/unknown result belongs to its controller."""
    argv = list(argv)
    deadline = time.monotonic() + timeout
    options = {"capture_output": True, "text": True, "encoding": "utf-8", "errors": "replace", **kwargs}
    check = options.pop("check", False)

    def run(command):
        remaining = deadline - time.monotonic()
        if remaining <= 0:
            raise subprocess.TimeoutExpired(command, timeout)
        return subprocess.run(command, timeout=remaining, **options)

    def finish(result):
        if check and result.returncode:
            raise subprocess.CalledProcessError(result.returncode, argv, result.stdout, result.stderr)
        return result

    action = argv[1] if len(argv) > 1 else ""
    if action in _ACTIONS and "--session" in argv and not (initial_navigation and action == "navigate"):
        # A caller cannot smuggle an old context through a newer observation.
        if "--context" in argv:
            raise ValueError("run_bsk owns observation contexts")
        sync = [argv[0], "cooperate", "sync", "--session", argv[argv.index("--session") + 1], "--json"]
        if "--tab-id" in argv:
            sync += ["--tab-id", argv[argv.index("--tab-id") + 1]]
        try:
            observed = run(sync)
        except subprocess.TimeoutExpired:
            error = {"code": "cooperation_sync_required", "message": "Timed out synchronizing the page; no action was sent",
                     "data": {"reason": "cooperation_sync_required", "dispatched": False, "effect_state": "none"}}
            return finish(subprocess.CompletedProcess(sync, 4, json.dumps(error), ""))
        if observed.returncode:
            return finish(observed)
        try:
            state = json.loads(observed.stdout)
        except (ValueError, TypeError):
            state = {}
        if not isinstance(state, dict):
            state = {}
        context = state.get("context_id")
        page_state = state.get("state")
        mode = page_state.get("mode") if isinstance(page_state, dict) else None
        if not isinstance(context, str) or not context or state.get("ready") is False or mode not in (None, "ready"):
            error = {"code": "cooperation_sync_required", "message": "Browser page is not ready for an agent action",
                     "data": {"reason": "cooperation_sync_required", "dispatched": False, "effect_state": "none"}}
            return finish(subprocess.CompletedProcess(sync, 1, json.dumps(error), ""))
        argv += ["--context", context]
    try:
        result = run(argv)
    except subprocess.TimeoutExpired:
        if action not in _ACTIONS:
            raise
        error = {"code": "operation_outcome_unknown", "message": "Command timed out; page effects are unknown; do not replay",
                 "data": {"reason": "operation_outcome_unknown", "effect_state": "unknown"}}
        result = subprocess.CompletedProcess(argv, 4, json.dumps(error), "")
    return finish(result)
