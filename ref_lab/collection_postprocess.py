"""Task-scoped local post-processing for downloaded collection originals."""
from __future__ import annotations

import os
from pathlib import Path
import subprocess
import sys
import threading
import time

from . import collection_queue
from .agent_collection import AttemptFileLock, _owner_record, _process_owner_active
from .collage import CollageWorker


_ACTIVE: dict[str, "PostprocessManager"] = {}
_ACTIVE_LOCK = threading.RLock()
_TERMINAL = {"completed", "partial", "blocked", "failed", "cancelled"}


def _postprocess_budget(job: dict) -> float:
    try:
        configured = float(os.environ.get("LAB_POSTPROCESS_TIMEOUT_SECONDS", ""))
    except ValueError:
        configured = 0
    target = max(1, int(job.get("target_count") or 1))
    return configured if 30 <= configured <= 3600 else min(3600, max(600, target * 120))


def _write_state(folder: Path, **values) -> dict:
    path = folder / "postprocess.json"
    state = collection_queue.read_json(path, {})
    if not isinstance(state, dict):
        state = {}
    state.update(values, version=1, updated_at=time.time())
    collection_queue.write_json(path, state)
    return state


def manager_receipt_state(exit_code, post: dict) -> dict:
    """Map a child outcome to manager state without inferring success."""
    if exit_code != 0:
        return {"state": "blocked", "phase": (post or {}).get("phase", "failed"),
                "reason": "postprocess_process_failed", "exit_code": exit_code}
    if not isinstance(post, dict) or not post.get("phase"):
        return {"state": "blocked", "phase": "failed", "reason": "postprocess_receipt_missing",
                "exit_code": exit_code}
    if post["phase"] == "complete":
        return {"state": "complete", "phase": "complete", "exit_code": exit_code}
    if post["phase"] == "blocked":
        return {"state": "blocked", "phase": "blocked",
                "reason": post.get("reason", "postprocess_blocked"), "exit_code": exit_code}
    return {"state": "restart_pending", "phase": post.get("phase"), "exit_code": exit_code}


def run_postprocess_job(job: dict, folder: Path) -> dict:
    """Consume collages and the pre-authorized type receipts until Search is done."""
    from .photo_types import PhotoTypeWorker, verified_type, receipt_intact

    folder = Path(folder)
    lock = AttemptFileLock(folder / "postprocess.lock")
    if not lock.acquire():
        existing = collection_queue.read_json(folder / "postprocess.json", {})
        return {**existing, "lock_contended": True, "reason": "postprocess_already_running"}
    collage = None
    types = None
    history = None
    try:
        target = min(100, max(1, int(job.get("target_count") or 1)))
        limit = min(200, max(20, target * 2))
        budget_seconds = _postprocess_budget(job)
        deadline = time.monotonic() + budget_seconds
        _write_state(folder, phase="running", owner=_owner_record(os.getpid(), phase="postprocess"),
                     budget={"type_calls": limit, "wall_seconds": budget_seconds}, error="")
        project_id = str(job.get("project_id") or (job.get("project_snapshot") or {}).get("id") or "")
        if not project_id:
            return _write_state(folder, phase="blocked", reason="history_project_identity_missing")
        from tools.collect_verified import _history_for_search
        history = _history_for_search(folder, project_id)
        goal = collection_queue.read_json(folder / "goal.json", {})
        if goal:
            types = PhotoTypeWorker(folder, limit=limit,
                                    model=str(job.get("model") or "gemini-3.8-flash-medium"),
                                    history=history, deadline=deadline)

        def record_type(record):
            if types is not None:
                types.enqueue(record)

        collage = CollageWorker(folder, history=history,
                                known_shas={row["asset_sha"] for row in collection_queue._received_rows(folder)},
                                on_record=record_type)
        enqueued = set()
        idle_since = time.monotonic()
        while True:
            if time.monotonic() >= deadline:
                reason = "postprocess_budget_exhausted"
                if types is not None:
                    types.stop.set()
                collage.close(timeout=0)
                return _write_state(
                    folder, phase="blocked", reason=reason, pending=True,
                    collage=collage.summary(), collage_errors=list(collage.errors)[:20],
                    type_phase=(types.block_reason if types is not None and types.blocked else "pending"),
                )
            rows = collection_queue._received_rows(folder)
            for row in rows:
                sha = row.get("asset_sha")
                if sha and sha not in enqueued:
                    enqueued.add(sha)
                    collage.enqueue(row)
                    idle_since = time.monotonic()
            summary = collection_queue.read_json(folder / "search-summary.json", {})
            # A retry must not finish background work on the previous search's receipt.
            started = job.get("search_attempt_started_at")
            finished = summary.get("finished_at") if isinstance(summary, dict) else None
            same_attempt = (not isinstance(started, (int, float)) or
                            (isinstance(finished, (int, float)) and finished >= started))
            terminal = isinstance(summary, dict) and summary.get("status") in _TERMINAL and same_attempt
            if terminal:
                remaining = max(0.0, deadline - time.monotonic())
                collage.drain(timeout=min(1.0, remaining))
                if types is not None:
                    remaining = max(0.0, deadline - time.monotonic())
                    types.drain(timeout=min(1.0, remaining))
            queues_idle = (collage._queue.unfinished_tasks == 0
                           and (types is None or types.pending.unfinished_tasks == 0))
            if terminal and queues_idle and time.monotonic() - idle_since >= 0.25:
                break
            time.sleep(0.2)

        remaining = max(0.0, deadline - time.monotonic())
        collage.drain(timeout=remaining)
        if types is not None:
            remaining = max(0.0, deadline - time.monotonic())
            types.drain(timeout=remaining)
        if collage._queue.unfinished_tasks or (types is not None and types.pending.unfinished_tasks):
            if types is not None:
                types.stop.set()
            return _write_state(folder, phase="blocked", reason="postprocess_budget_exhausted", pending=True,
                                collage=collage.summary(), collage_errors=list(collage.errors)[:20])
        type_items = collection_queue.read_json(folder / "photo-types.json", {}).get("items", {})
        type_incomplete = any(isinstance(item, dict) and item.get("status") in {"running", "blocked", "failed"}
                              for item in type_items.values())
        blocked_reason = ("collage_processing_incomplete" if collage.errors else
                          (getattr(types, "block_reason", "") or "type_processing_incomplete")
                          if types is not None and (types.blocked or type_incomplete) else "")
        state = _write_state(
            folder, phase="blocked" if blocked_reason else "complete", seen_shas=sorted(enqueued),
            collage=collage.summary(), collage_errors=list(collage.errors)[:20],
            type_phase=(getattr(types, "block_reason", "") or ("incomplete" if type_incomplete else "complete")
                        if types is not None else "disabled"),
            reason=blocked_reason, pending=bool(blocked_reason), error="",
        )
        return state
    except BaseException as exc:
        return _write_state(folder, phase="blocked",
                            reason=type(exc).__name__, error=str(exc)[:800])
    finally:
        if types is not None:
            types.close(timeout=5)
        if collage is not None:
            collage.close(timeout=5)
        if history is not None:
            history.close(wait=False, timeout=1)
        lock.release()


class PostprocessManager:
    """Own one collector post-process for one Job without becoming a daemon."""

    def __init__(self, library, job_id: str):
        self.library = library
        self.job_id = job_id
        self.folder = collection_queue.run_directory(job_id)
        self.stop_event = threading.Event()
        self.process = None
        self.worker_done = threading.Event()
        self.background_state = None
        self.thread = threading.Thread(target=self._run, name=f"postprocess-{job_id[:8]}", daemon=True)
        self.import_thread = threading.Thread(target=self._watch_imports, name=f"live-import-{job_id[:8]}", daemon=True)

    def start(self) -> None:
        self.import_thread.start()
        self.thread.start()

    def _watch_imports(self) -> None:
        """Follow Search and candidate artifacts even if post-processing fails."""
        signature = None
        import_pending = True
        terminal_seen = False
        while not self.stop_event.is_set():
            current = self._artifact_signature()
            if current != signature or import_pending:
                signature = current
                import_pending = bool(self._import().get("errors"))
            try:
                job = self.library.job(self.job_id)
            except Exception:
                self.stop_event.wait(0.25)
                continue
            terminal = job.get("status") == "cancelled" or job.get("search_state") in _TERMINAL
            if terminal and terminal_seen and self.worker_done.is_set() and not import_pending:
                outcome = self.background_state or {"state": "blocked", "phase": "missing",
                                                   "reason": "postprocess_receipt_missing"}
                self._manager_state(state="complete" if outcome.get("state") == "complete" else "blocked",
                                    phase=outcome.get("phase", "failed"),
                                    postprocess_state=outcome.get("state", "blocked"),
                                    reason=outcome.get("reason", ""))
                break
            terminal_seen = terminal
            self.stop_event.wait(0.25)
        with _ACTIVE_LOCK:
            if self.worker_done.is_set():
                _ACTIVE.pop(self.job_id, None)

    def _artifact_signature(self):
        values = []
        for name in ("received.json", "derived.json"):
            try:
                stat = (self.folder / name).stat()
                values.append((stat.st_size, stat.st_mtime_ns))
            except OSError:
                values.append((0, 0))
        return tuple(values)

    def _import(self) -> dict:
        try:
            result = self.library.import_search_candidates(self.job_id)
        except Exception as exc:
            result = {"errors": 1, "error": f"{type(exc).__name__}: {str(exc)[:300]}"}
        collection_queue.write_json(self.folder / "live-import.json",
                                    {**result, "updated_at": time.time()})
        return result

    def _manager_state(self, **values) -> None:
        path = self.folder / "postprocess-manager.json"
        state = collection_queue.read_json(path, {})
        if not isinstance(state, dict):
            state = {}
        state.update(values, version=1, updated_at=time.time())
        collection_queue.write_json(path, state)

    def _terminate(self) -> None:
        if self.process is None or self.process.poll() is not None:
            return
        try:
            self.process.terminate()
            self.process.wait(timeout=5)
        except (OSError, subprocess.TimeoutExpired):
            try: self.process.kill()
            except OSError: pass

    def _run(self) -> None:
        existing = collection_queue.read_json(self.folder / "postprocess-manager.json", {})
        if isinstance(existing, dict) and existing.get("state") == "running" and _process_owner_active(existing.get("owner")):
            while (_process_owner_active(existing.get("owner")) and not self.stop_event.is_set()):
                self.stop_event.wait(1.0)
            existing = collection_queue.read_json(self.folder / "postprocess-manager.json", {})
            if isinstance(existing, dict) and existing.get("state") in {"complete", "blocked", "cancelled"}:
                self.worker_done.set()
                return
        task_file = self.folder / "task" / "AGENT_TASK.md"
        result_file = self.folder / "postprocess-result.zip"
        command = [sys.executable, str(Path(__file__).resolve().parents[1] / "tools" / "collect_verified.py"),
                   str(task_file), str(result_file), "--postprocess-only"]
        if os.name == "nt":
            command = [sys.executable,
                       str(Path(__file__).resolve().with_name("windows_adapter_runner.py")), *command]
        stdout_path = self.folder / "postprocess.stdout.log"
        stderr_path = self.folder / "postprocess.stderr.log"
        self._manager_state(state="running", phase="starting")
        try:
            with stdout_path.open("ab") as stdout, stderr_path.open("ab") as stderr:
                options = {"cwd": str(self.folder), "env": dict(os.environ),
                           "stdin": subprocess.DEVNULL, "stdout": stdout, "stderr": stderr}
                if os.name == "nt":
                    options["creationflags"] = subprocess.CREATE_NO_WINDOW
                self.process = subprocess.Popen(command, **options)
            self._manager_state(state="running", phase="processing", owner=_owner_record(self.process.pid, phase="postprocess"))
            while self.process.poll() is None and not self.stop_event.is_set():
                job = self.library.job(self.job_id)
                if job.get("status") == "cancelled":
                    self.stop_event.set()
                    break
                self.stop_event.wait(0.25)
            if self.stop_event.is_set():
                self._terminate()
                self._manager_state(state="restart_pending", phase="paused", exit_code=self.process.poll())
                return
            post = collection_queue.read_json(self.folder / "postprocess.json", {})
            self.background_state = manager_receipt_state(self.process.returncode, post)
            self._manager_state(state="running", phase="monitoring",
                                postprocess_state=self.background_state["state"],
                                reason=self.background_state.get("reason", ""),
                                exit_code=self.process.returncode)
        except Exception as exc:
            self.background_state = {"state": "blocked", "phase": "failed",
                                     "reason": type(exc).__name__}
            self._manager_state(state="running", phase="monitoring", postprocess_state="blocked",
                                reason=type(exc).__name__, error=str(exc)[:800])
        finally:
            self.worker_done.set()
            with _ACTIVE_LOCK:
                if not self.import_thread.is_alive():
                    _ACTIVE.pop(self.job_id, None)

    def stop(self) -> None:
        self.stop_event.set()
        self._terminate()
        self.thread.join(timeout=8)
        self.import_thread.join(timeout=8)


def start_collection_postprocess(library, job_id: str) -> PostprocessManager:
    folder = collection_queue.run_directory(job_id)
    folder.mkdir(parents=True, exist_ok=True)
    with _ACTIVE_LOCK:
        current = _ACTIVE.get(job_id)
        if current is not None and (current.thread.is_alive() or current.import_thread.is_alive()):
            return current
        manager = PostprocessManager(library, job_id)
        _ACTIVE[job_id] = manager
        manager.start()
        return manager


def resume_collection_postprocessors(library) -> list[str]:
    """Resume only Jobs that already entered this task-scoped processor."""
    started = []
    for job in library.jobs():
        if job.get("kind") != "collection" or job.get("collection_mode") != "search":
            continue
        if job.get("status") == "cancelled":
            continue
        folder = collection_queue.run_directory(job["id"])
        manager = collection_queue.read_json(folder / "postprocess-manager.json", {})
        if isinstance(manager, dict) and manager.get("state") in {"running", "starting", "restart_pending"}:
            start_collection_postprocess(library, job["id"])
            started.append(job["id"])
    return started


def stop_collection_postprocessors() -> None:
    with _ACTIVE_LOCK:
        managers = list(_ACTIVE.values())
    for manager in managers:
        manager.stop()
