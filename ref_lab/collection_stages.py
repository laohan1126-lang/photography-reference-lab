"""Search / Acquire and independent Review stage runners.

The program state machine, not a new multi-agent layer, keeps the stages
independent:

* Search launches the existing collector with ``--search-only``.
* Review launches the same collector with ``--review-only`` and consumes the
  persistent candidate queue, waiting for new downloads if requested.
* Both stages have separate attempt ids, locks, process owners, wall budgets and
  terminal states. A blocked Review never rewinds Search.
"""
from __future__ import annotations

import hashlib
import json
import threading
from pathlib import Path
from uuid import uuid4

from . import collection_queue
from .agent_collection import (AttemptFileLock, AttemptStop, _owner_record, _prepare_task,
                               _process_owner_active, _read_result, configured_command,
                               run_process, stage_timeout_seconds)
from .collection_queue import read_json
from .imports import import_candidates, read_archive
from .service import Library, Problem

_LAUNCH_LOCK = threading.RLock()
_ARTIFACT_LOCK = threading.RLock()
_RUNNING: set[tuple[str, str]] = set()


def _folder(job_id: str) -> Path:
    return collection_queue.run_directory(job_id)


def _artifacts(library: Library, job_id: str) -> tuple[Path, Path, Path]:
    folder = _folder(job_id)
    folder.mkdir(mode=0o700, parents=True, exist_ok=True)
    task_dir = folder / "task"
    task_file = task_dir / "AGENT_TASK.md"
    with _ARTIFACT_LOCK:
        _prepare_task(library, job_id, task_dir, task_file)
        goal_id = library.job(job_id).get('goal_id')
        if goal_id:
            source = collection_queue.ROOT/'.local/goals'/goal_id/'goal.json'
            goal = json.loads(source.read_text('utf8'))
            existing = collection_queue.read_json(folder/'goal.json', None)
            if existing is not None and existing != goal:
                raise Problem(409, 'Goal历史基线发生变化；拒绝覆盖')
            collection_queue.write_json(folder/'goal.json', goal)
    return folder, task_dir, task_file


def _command(job: dict, task_dir: Path, task_file: Path, result_file: Path, stage: str) -> list[str]:
    command = configured_command()
    replacements = {"{task_dir}": str(task_dir), "{task_file}": str(task_file), "{result_file}": str(result_file)}
    argv = []
    for arg in command:
        for key, value in replacements.items():
            arg = arg.replace(key, value)
        argv.append(arg)
    if stage == "search":
        argv.append("--search-only")
    else:
        argv.append("--review-only")
        if job.get("collection_mode") == "search_review":
            argv.append("--wait-search")
    return argv


def _summary_blocked(job_id: str, reason: str, detail: str, *, target: int = 0,
                     found: int | None = None) -> dict:
    folder = _folder(job_id)
    if found is None:
        try:
            found = int(collection_queue.snapshot(job_id, limit=500)["counts"]["found"])
        except (OSError, ValueError):
            found = 0
    summary = {
        "version": 1, "status": "blocked", "stop_reason": reason,
        "target": int(target),
        "counts": {"found": int(found), "duplicates": 0, "errors": 1},
        "elapsed_seconds": 0.0, "finished_at": __import__("time").time(),
        "queries": [], "source_checks": [], "searches": {},
        "errors": [detail[:300]], "model_calls": 0, "tokens": 0,
    }
    collection_queue.write_json(folder / "search-summary.json", summary)
    return summary


def _stage_timeout(job: dict, stage: str) -> float:
    key = "search_timeout_seconds" if stage == "search" else "review_timeout_seconds"
    stored = job.get(key)
    if isinstance(stored, (int, float)) and float(stored) > 0:
        return float(stored)
    return stage_timeout_seconds(stage, int(job.get("target_count") or 12))


def _remaining(job: dict, stage: str) -> float:
    total = _stage_timeout(job, stage)
    elapsed_key = "search_elapsed_seconds" if stage == "search" else "review_elapsed_seconds"
    started_key = "search_attempt_started_at" if stage == "search" else "review_attempt_started_at"
    elapsed = float(job.get(elapsed_key, 0.0) or 0.0)
    if job.get(started_key):
        elapsed += max(0.0, __import__("time").time() - float(job[started_key]))
    return max(0.0, total - elapsed)


def _set_running(job_id: str, stage: str, running: bool) -> None:
    key = (job_id, stage)
    with _LAUNCH_LOCK:
        if running:
            if key in _RUNNING:
                raise Problem(409, "本阶段已在启动或运行中")
            _RUNNING.add(key)
        else:
            _RUNNING.discard(key)


def _thread(job_id: str, stage: str, target, *args) -> None:
    def body():
        try:
            target(*args)
        finally:
            _set_running(job_id, stage, False)

    threading.Thread(target=body, name=f"collection-{stage}-{job_id[:8]}", daemon=True).start()


def launch_search(library: Library, job_id: str) -> dict:
    job = library.job(job_id)
    if job["kind"] != "collection":
        raise Problem(400, "不是采集任务")
    if job.get("collection_mode", "verified") == "verified":
        raise Problem(409, "历史一体式任务请使用原执行入口")
    if job["status"] == "cancelled":
        raise Problem(409, "已取消的采集任务不能继续")
    if job.get("search_state") == "completed" and job.get("review_state") in {"idle", "completed", "partial", "blocked"}:
        return library.job(job_id)
    # Prepare the shared task package before either stage thread starts; this
    # avoids two Windows threads replacing the same directory.
    _artifacts(library, job_id)
    with _LAUNCH_LOCK:
        if (job_id, "search") in _RUNNING:
            raise Problem(409, "搜索阶段仍在运行")
        attempt_id = job.get("search_attempt_id") or uuid4().hex
        if job.get("search_state") == "running" and job.get("search_attempt_id"):
            if job.get("collection_process_owner") and _process_owner_active(job.get("collection_process_owner")):
                raise Problem(409, "本 Job 的搜索进程仍在运行，不能抢占当前轮次")
            job = library.resume_collection_attempt(job_id, job["revision"], attempt_id,
                                                    owner=_owner_record(__import__("os").getpid(), phase="initializing"))
        else:
            job = library.start_collection_attempt(job_id, job["revision"], attempt_id,
                                                   owner=_owner_record(__import__("os").getpid(), phase="initializing"),
                                                   timeout=_stage_timeout(job, "search"))
        _set_running(job_id, "search", True)
        _thread(job_id, "search", run_search_stage, library, job_id, attempt_id)
    return library.job(job_id)


def launch_review(library: Library, job_id: str) -> dict:
    job = library.job(job_id)
    if job["kind"] != "collection":
        raise Problem(400, "不是采集任务")
    if job.get("collection_mode", "verified") == "verified":
        raise Problem(409, "历史一体式任务请使用原执行入口")
    if job["status"] == "cancelled":
        raise Problem(409, "已取消的采集任务不能启动审核")
    _artifacts(library, job_id)
    with _LAUNCH_LOCK:
        if (job_id, "review") in _RUNNING:
            raise Problem(409, "审核阶段仍在运行")
        if job.get("review_state") == "running" and job.get("review_attempt_id"):
            if job.get("review_process_owner") and _process_owner_active(job.get("review_process_owner")):
                raise Problem(409, "本 Job 的审核进程仍在运行，不能抢占当前轮次")
            attempt_id = job["review_attempt_id"]
            job = library.resume_review_stage(job_id, attempt_id,
                                              owner=_owner_record(__import__("os").getpid(), phase="initializing"))
        else:
            attempt_id = uuid4().hex
            job = library.start_review_stage(job_id, attempt_id,
                                             owner=_owner_record(__import__("os").getpid(), phase="initializing"),
                                             timeout=_stage_timeout(job, "review"))
        _set_running(job_id, "review", True)
        _thread(job_id, "review", run_review_stage, library, job_id, attempt_id)
    return library.job(job_id)


def start_job(library: Library, job_id: str) -> dict:
    job = library.job(job_id)
    mode = job.get("collection_mode", "verified")
    if mode == "verified":
        raise Problem(409, "历史一体式任务请使用原执行入口")
    launched = launch_search(library, job_id)
    if mode == "search_review":
        launched = launch_review(library, job_id)
    return launched


def run_search_stage(library: Library, job_id: str, attempt_id: str) -> dict:
    folder, task_dir, task_file = _artifacts(library, job_id)
    lock = AttemptFileLock(folder / "search.lock")
    if not lock.acquire():
        raise Problem(409, "本 Job 的搜索阶段仍由本地执行进程持有")
    try:
        job = library.job(job_id)
        if job.get("search_state") == "completed":
            return job
        target = int(job.get("target_count") or 0)
        remaining = _remaining(job, "search")
        if remaining <= 0:
            summary = _summary_blocked(job_id, "time_budget_exhausted", "搜索时间预算已用尽；已下载候选保留。",
                                       target=target)
            return library.update_search_stage(job_id, attempt_id, "blocked", summary,
                                               "搜索时间预算已用尽；已下载候选保留。")
        result_file = folder / "search-result.zip"
        try:
            argv = _command(job, task_dir, task_file, result_file, "search")
        except AttemptStop as exc:
            summary = _summary_blocked(job_id, exc.code, exc.detail, target=target)
            return library.update_search_stage(job_id, attempt_id, "blocked", summary, exc.detail)
        try:
            code = run_process(library, job_id, attempt_id, argv, task_dir, remaining, lock.file, stage="search")
            if code:
                raise AttemptStop("process_failed", f"搜索适配程序退出码 {code}；候选原图保留。")
        except AttemptStop as exc:
            if library.job(job_id).get("active_attempt_id") != attempt_id:
                return library.job(job_id)
            summary = read_json(folder / "search-summary.json", {})
            if not isinstance(summary, dict) or summary.get("status") not in {"completed", "partial", "blocked", "failed", "cancelled"}:
                summary = _summary_blocked(job_id, exc.code, exc.detail, target=target)
            result = library.update_search_stage(job_id, attempt_id, "blocked", summary, exc.detail)
            _import_search(library, job_id)
            return result
        except Exception as exc:  # noqa: BLE001 - stage failures must be durable, not a false success
            if library.job(job_id).get("active_attempt_id") != attempt_id:
                return library.job(job_id)
            summary = _summary_blocked(job_id, "internal_error", f"搜索阶段内部异常：{type(exc).__name__}",
                                       target=target)
            result = library.update_search_stage(job_id, attempt_id, "blocked", summary,
                                                 "搜索阶段内部异常；已下载候选保留。")
            _import_search(library, job_id)
            return result
        summary = read_json(folder / "search-summary.json", {})
        if not isinstance(summary, dict) or summary.get("status") not in {"completed", "partial", "blocked", "failed", "cancelled"}:
            summary = _summary_blocked(job_id, "summary_missing", "搜索进程没有留下阶段回执；未宣称完成。",
                                       target=target)
        if library.job(job_id).get("active_attempt_id") != attempt_id:
            return library.job(job_id)
        status = str(summary.get("status", "blocked"))
        found = int((summary.get("counts") or {}).get("found", 0) or 0)
        confirmed = int((summary.get("counts") or {}).get("target_confirmed", 0) or 0)
        if status == "completed":
            detail = f"搜索阶段完成：找到 {found} 张候选原图，其中角色名称命中 {confirmed} 张；审核状态另行记录。"
        elif status == "partial":
            detail = (f"搜索部分完成：找到 {found} 张候选原图，其中角色名称命中 {confirmed} 张；"
                      f"未达目标，停止原因 {summary.get('stop_reason', '未知')}。")
        else:
            detail = f"搜索阶段受阻：{summary.get('stop_reason', '未知原因')}；已下载候选保留。"
        result = library.update_search_stage(job_id, attempt_id, status, summary, detail)
        _import_search(library, job_id)
        _import_review(library, job_id)
        return result
    finally:
        lock.release()


def run_review_stage(library: Library, job_id: str, attempt_id: str) -> dict:
    folder, task_dir, task_file = _artifacts(library, job_id)
    lock = AttemptFileLock(folder / "review.lock")
    if not lock.acquire():
        raise Problem(409, "本 Job 的审核阶段仍由本地执行进程持有")
    try:
        job = library.job(job_id)
        remaining = _remaining(job, "review")
        result_file = folder / "review-result.zip"
        if remaining <= 0:
            summary = {"version": 1, "status": "blocked", "stop_reason": "review_timeout",
                       "counts": {"found": 0, "accepted": 0, "rejected": 0, "blocked": 0, "pending": 0},
                       "elapsed_seconds": 0.0, "model_calls": 0, "tokens": 0}
            collection_queue.write_json(folder / "review-summary.json", summary)
            return library.update_review_stage(job_id, attempt_id, "blocked", summary,
                                               "审核时间预算已用尽；候选原图保留。")
        try:
            argv = _command(job, task_dir, task_file, result_file, "review")
        except AttemptStop as exc:
            summary = {"version": 1, "status": "blocked", "stop_reason": exc.code,
                       "counts": {"found": 0, "accepted": 0, "rejected": 0, "blocked": 0, "pending": 0},
                       "errors": [exc.detail], "elapsed_seconds": 0.0, "model_calls": 0, "tokens": 0}
            collection_queue.write_json(folder / "review-summary.json", summary)
            return library.update_review_stage(job_id, attempt_id, "blocked", summary, exc.detail)
        try:
            code = run_process(library, job_id, attempt_id, argv, task_dir, remaining, lock.file, stage="review")
            if code:
                raise AttemptStop("review_process_failed", f"审核适配程序退出码 {code}；候选原图保留。")
        except AttemptStop as exc:
            if library.job(job_id).get("review_attempt_id") != attempt_id:
                return library.job(job_id)
            summary = read_json(folder / "review-summary.json", {})
            if not isinstance(summary, dict) or not summary:
                summary = {"version": 1, "status": "blocked", "stop_reason": exc.code,
                           "counts": {"found": 0, "accepted": 0, "rejected": 0, "blocked": 0, "pending": 0},
                           "errors": [exc.detail], "elapsed_seconds": 0.0, "model_calls": 0, "tokens": 0}
                collection_queue.write_json(folder / "review-summary.json", summary)
            result = library.update_review_stage(job_id, attempt_id, "blocked", summary, exc.detail)
            _import_review(library, job_id)
            return result
        except Exception as exc:  # noqa: BLE001
            if library.job(job_id).get("review_attempt_id") != attempt_id:
                return library.job(job_id)
            summary = {"version": 1, "status": "blocked", "stop_reason": "internal_error",
                       "counts": {"found": 0, "accepted": 0, "rejected": 0, "blocked": 0, "pending": 0},
                       "errors": [type(exc).__name__], "elapsed_seconds": 0.0, "model_calls": 0, "tokens": 0}
            collection_queue.write_json(folder / "review-summary.json", summary)
            result = library.update_review_stage(job_id, attempt_id, "blocked", summary,
                                                 "审核阶段内部异常；候选原图保留。")
            _import_review(library, job_id)
            return result
        summary = read_json(folder / "review-summary.json", {})
        if not isinstance(summary, dict) or not summary:
            summary = {"version": 1, "status": "blocked", "stop_reason": "summary_missing",
                       "counts": {"found": 0, "accepted": 0, "rejected": 0, "blocked": 0, "pending": 0},
                       "errors": ["审核进程没有留下阶段回执"], "elapsed_seconds": 0.0, "model_calls": 0, "tokens": 0}
            collection_queue.write_json(folder / "review-summary.json", summary)
        if library.job(job_id).get("review_attempt_id") != attempt_id:
            return library.job(job_id)
        status = str(summary.get("status", "blocked"))
        state = {"completed": "completed", "partial": "partial", "blocked": "blocked"}.get(status, "blocked")
        counts = summary.get("counts") or {}
        detail = (f"独立审核结束：通过 {counts.get('accepted', 0)}，拒绝 {counts.get('rejected', 0)}，"
                  f"受阻 {counts.get('blocked', 0)}，待审 {counts.get('pending', 0)}。")
        result = library.update_review_stage(job_id, attempt_id, state, summary, detail)
        _import_review(library, job_id)
        return result
    finally:
        lock.release()


def _import_search(library: Library, job_id: str) -> dict:
    """Persist acquired originals as *pending* project candidates for normal UI use.

    Idempotent, and it replays human decisions taken before the reference existed.
    """
    return library.import_search_candidates(job_id)


def _import_review(library: Library, job_id: str) -> dict | None:
    """Import the validated schema3 review package once both stages are settled."""
    job = library.job(job_id)
    if job.get("search_state") == "running" or job["status"] == "cancelled":
        return None
    folder = _folder(job_id)
    # Make sure every acquired original is already a pending project candidate
    # before a narrower accepted package can complete the job.
    _import_search(library, job_id)
    job = library.job(job_id)
    path = folder / "review-result.zip"
    if not path.is_file():
        return None
    try:
        content, manifest = _read_result(path, job_id)
    except AttemptStop:
        return None
    result_sha = hashlib.sha256(content).hexdigest()
    if job.get("last_review_result_sha256") == result_sha and job.get("review_imported_ids"):
        return {"skipped": True}
    with __import__("zipfile").ZipFile(__import__("io").BytesIO(content)) as archive:
        received = {item["asset_sha"] for item in collection_queue.snapshot(job_id, limit=500)["items"]}
        human = collection_queue.human_items(folder)
        for candidate in manifest.candidates:
            try:
                raw = archive.read(candidate.file)
            except KeyError:
                return None
            sha = hashlib.sha256(raw).hexdigest()
            if sha not in received:
                return None
            if (human.get(sha) or {}).get("decision") == "reject":
                # A human rejection is a later decision; never import it as verified.
                return None
    report = import_candidates(library, job["project_id"], content, job_id, record_report=False)
    summary = read_json(folder / "review-summary.json", {})
    library.record_review_import(job_id, report["reference_ids"],
                                 accepted=len(manifest.candidates),
                                 target=int(job.get("target_count") or 1),
                                 result_sha256=result_sha,
                                 summary=summary if isinstance(summary, dict) else {})
    return report
