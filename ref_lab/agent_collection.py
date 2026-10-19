"""Opt-in native Agent transport; task packages, not a built-in website scraper.

The owner configures argv for an installed local adapter. This module does not
invent vendor CLI flags, install software, start a browser or make model calls.
Process exit is transport evidence, never proof of image identity or quality.
"""
from __future__ import annotations

import ctypes
import hashlib
import json
import math
import os
from pathlib import Path
import shutil
import signal
import subprocess
import sys
import time
from uuid import uuid4

if os.name == "nt":
    import msvcrt
else:
    import fcntl

from .export import build_job_pack
from .imports import import_candidates, read_archive, MAX_ARCHIVE_BYTES
from .models import CandidatePackage
from .service import Library, Problem


class AttemptStop(Exception):
    def __init__(self, code: str, detail: str, status: str = "blocked"):
        super().__init__(detail)
        self.code, self.detail, self.status = code, detail, status


def configured_command() -> list[str]:
    raw = os.environ.get("LAB_COLLECTION_COMMAND", "")
    if not raw.strip():
        raise AttemptStop("adapter_not_configured", "未配置 LAB_COLLECTION_COMMAND；请下载任务 ZIP 交给本地 Agent，或配置适配器。没有自动启动浏览器或备用抓图。")
    try:
        command = json.loads(raw)
    except (ValueError, TypeError):
        raise AttemptStop("invalid_configuration", "LAB_COLLECTION_COMMAND 必须是 JSON 字符串数组，不是 shell 命令。") from None
    if (not isinstance(command, list) or not command or len(command) > 100
            or any(not isinstance(arg, str) or not arg or "\0" in arg for arg in command)):
        raise AttemptStop("invalid_configuration", "采集适配命令格式无效；不执行、不打印命令内容。")
    if not any("{task_dir}" in arg or "{task_file}" in arg for arg in command[1:]) or not any("{result_file}" in arg for arg in command[1:]):
        raise AttemptStop("missing_placeholders", "适配器参数须包含 {task_dir} 或 {task_file}，以及 {result_file}。")
    executable = shutil.which(command[0])
    if not executable:
        raise AttemptStop("executable_missing", "配置的本地适配程序不存在或不可执行；请检查当前服务进程的 PATH。")
    # WSL cannot reliably own/reap a Windows process tree using POSIX killpg.
    if os.name != "nt" and executable.lower().endswith(".exe"):
        raise AttemptStop("cross_runtime_unsupported", "不跨 WSL 启动 Windows exe；请让服务与适配器在同一运行环境执行，或使用手动任务包。")
    return [executable, *command[1:]]


def timeout_seconds(target_count: int = 12) -> float:
    try:
        # A real BrowserSkill pass drives a live browser: 8+ queries, lazy page
        # loads and per-card detail pages routinely run past ten minutes, and a
        # 600s default killed the adapter mid-run every time.
        default=min(3600,max(1800,int(target_count)*90+300))
        seconds = float(os.environ.get("LAB_COLLECTION_TIMEOUT_SECONDS",str(default)))
        if not math.isfinite(seconds) or not 0.1 <= seconds <= 3600:
            raise ValueError
        return seconds
    except ValueError:
        raise AttemptStop("invalid_timeout", "采集超时设置须为 0.1 到 3600 之间的有限秒数。") from None


def stop_process_tree(process: subprocess.Popen) -> None:
    """Terminate only this attempt's process group, never the owner's browser."""
    if os.name == "nt":
        if process.poll() is None:
            # Terminate the held supervisor handle; Windows closes its owned job
            # and kills descendants, including those whose adapter root exited.
            process.terminate()
    else:
        try:
            # A child may remain in the group after the parent exits.
            os.killpg(process.pid, signal.SIGKILL)
        except ProcessLookupError:
            pass  # No such group is the desired cleanup outcome, not a lost error.
    process.wait(timeout=10)


def _process_identity(pid: int) -> dict | None:
    if os.name == "nt":
        from ctypes import wintypes

        class FileTime(ctypes.Structure):
            _fields_ = [("low", wintypes.DWORD), ("high", wintypes.DWORD)]

        kernel = ctypes.WinDLL("kernel32", use_last_error=True)
        kernel.OpenProcess.argtypes = [wintypes.DWORD, wintypes.BOOL, wintypes.DWORD]
        kernel.OpenProcess.restype = wintypes.HANDLE
        kernel.GetProcessTimes.argtypes = [wintypes.HANDLE, ctypes.POINTER(FileTime), ctypes.POINTER(FileTime), ctypes.POINTER(FileTime), ctypes.POINTER(FileTime)]
        kernel.GetProcessTimes.restype = wintypes.BOOL
        kernel.QueryFullProcessImageNameW.argtypes = [wintypes.HANDLE, wintypes.DWORD, wintypes.LPWSTR, ctypes.POINTER(wintypes.DWORD)]
        kernel.QueryFullProcessImageNameW.restype = wintypes.BOOL
        kernel.WaitForSingleObject.argtypes = [wintypes.HANDLE, wintypes.DWORD]
        kernel.WaitForSingleObject.restype = wintypes.DWORD
        kernel.CloseHandle.argtypes = [wintypes.HANDLE]
        kernel.CloseHandle.restype = wintypes.BOOL
        handle = kernel.OpenProcess(0x00100000 | 0x1000, False, pid)  # SYNCHRONIZE | QUERY_LIMITED_INFORMATION
        if not handle:
            return None if ctypes.get_last_error() in {87, 1168} else {"pid": pid, "unknown": True}
        try:
            if kernel.WaitForSingleObject(handle, 0) == 0:
                return None
            created, exited, kernel_time, user_time = FileTime(), FileTime(), FileTime(), FileTime()
            if not kernel.GetProcessTimes(handle, ctypes.byref(created), ctypes.byref(exited), ctypes.byref(kernel_time), ctypes.byref(user_time)):
                return {"pid": pid, "unknown": True}
            path = ctypes.create_unicode_buffer(32768)
            size = wintypes.DWORD(len(path))
            if not kernel.QueryFullProcessImageNameW(handle, 0, path, ctypes.byref(size)):
                return {"pid": pid, "unknown": True}
            creation = (int(created.high) << 32) | int(created.low)
            return {"pid": pid, "creation": creation, "executable": path.value.casefold()}
        finally:
            kernel.CloseHandle(handle)
    try:
        fields = Path(f"/proc/{pid}/stat").read_text(encoding="ascii").rsplit(")", 1)[1].split()
        if fields[0] == "Z":
            return None
        executable = os.readlink(f"/proc/{pid}/exe")
        return {"pid": pid, "creation": fields[19], "executable": executable}
    except FileNotFoundError:
        return None
    except (OSError, IndexError):
        try:
            os.kill(pid, 0)
        except ProcessLookupError:
            return None
        except PermissionError:
            pass
        return {"pid": pid, "unknown": True}


def _process_owner_active(owner: dict | None) -> bool:
    if not owner:
        return False
    current = _process_identity(int(owner.get("pid", 0)))
    if current and current.get("unknown"):
        return True
    if current:
        if (current.get("creation") == owner.get("creation")
                and current.get("executable", "").casefold() == owner.get("executable", "").casefold()):
            return True
    if os.name != "nt" and owner.get("pgid"):
        try:
            os.killpg(int(owner["pgid"]), 0)
            return True
        except ProcessLookupError:
            pass
        except PermissionError:
            return True
    return False


class AttemptFileLock:
    def __init__(self, path: Path):
        self.path = path
        self.file = None

    def acquire(self) -> bool:
        self.path.parent.mkdir(mode=0o700, parents=True, exist_ok=True)
        stream = self.path.open("a+b")
        try:
            stream.seek(0, os.SEEK_END)
            if stream.tell() == 0:
                stream.write(b"\0")
                stream.flush()
            stream.seek(0)
            if os.name == "nt":
                msvcrt.locking(stream.fileno(), msvcrt.LK_NBLCK, 1)
            else:
                fcntl.flock(stream.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
        except OSError:
            stream.close()
            return False
        self.file = stream
        return True

    def release(self) -> None:
        if self.file is None:
            return
        try:
            self.file.seek(0)
            if os.name == "nt":
                msvcrt.locking(self.file.fileno(), msvcrt.LK_UNLCK, 1)
            else:
                fcntl.flock(self.file.fileno(), fcntl.LOCK_UN)
        finally:
            self.file.close()
            self.file = None


def _run_directory(library: Library, job_id: str) -> Path:
    root = library.settings.data_dir / "agent-runs"
    folder = root / job_id
    if root.is_symlink() or folder.is_symlink():
        raise AttemptStop("run_directory_invalid", "本轮持久工作目录不能是符号链接。")
    folder.mkdir(mode=0o700, parents=True, exist_ok=True)
    return folder.resolve()


def _job_artifacts(job: dict, folder: Path) -> tuple[Path, Path, Path]:
    stored = job.get("collection_artifacts") or {}
    task_dir = Path(stored["task_dir"]) if stored.get("task_dir") else folder / "task"
    task_file = Path(stored["task_file"]) if stored.get("task_file") else task_dir / "AGENT_TASK.md"
    result_file = Path(stored["result_file"]) if stored.get("result_file") else folder / "result.zip"
    try:
        for path in (task_dir.resolve(), task_file.resolve(), result_file.resolve()):
            path.relative_to(folder)
    except ValueError:
        raise AttemptStop("run_directory_invalid", "已保存的采集任务路径不属于本 Job 的私有工作目录。") from None
    if task_dir.is_symlink() or task_file.is_symlink() or result_file.is_symlink():
        raise AttemptStop("run_directory_invalid", "采集任务、结果和目录不能是符号链接。")
    return task_dir, task_file, result_file


def _prepare_task(library: Library, job_id: str, task_dir: Path, task_file: Path) -> None:
    if task_dir.is_dir():
        if not task_file.is_file():
            raise AttemptStop("task_package_incomplete", "已保存的任务包不完整，保留现有文件并停止恢复。")
        return
    stage = task_dir.parent / ("task-init-" + uuid4().hex)
    stage.mkdir(mode=0o700)
    pack = build_job_pack(library, job_id)
    try:
        for name, content in read_archive(pack.read_bytes()).items():
            dest = stage / name
            dest.parent.mkdir(mode=0o700, parents=True, exist_ok=True)
            dest.write_bytes(content)
    finally:
        pack.unlink(missing_ok=True)
    staged_task = stage / "AGENT_TASK.md"
    staged_task.write_text(staged_task.read_text(encoding="utf-8") +
                           "\n## 本次自动适配器交付约束（替代上文 import-job 指示）\n"
                           "只生成 result.zip 到适配器指定位置。不要自行导入、操作网页 API 或修改个人数据库。"
                           "网页负责校验并导入；stdout/stderr 不作为结果也不会记录。\n", encoding="utf-8")
    stage.replace(task_dir)


def _read_result(result_file: Path, job_id: str) -> tuple[bytes, CandidatePackage]:
    if result_file.is_symlink() or not result_file.is_file():
        raise AttemptStop("result_missing", "适配器未返回普通 result.zip 文件；退出码 0 不等于采集完成。")
    with result_file.open("rb") as stream:
        content = stream.read(MAX_ARCHIVE_BYTES + 1)
    if len(content) > MAX_ARCHIVE_BYTES:
        raise AttemptStop("result_too_large", "候选包超过限制；未导入。")
    try:
        files = read_archive(content)
        manifest = CandidatePackage.model_validate_json(files["manifest.json"])
    except (ValueError, KeyError, TypeError) as exc:
        raise AttemptStop("result_invalid", "保存的 result.zip 未通过归档或 schema 校验；保留文件供检查。") from exc
    if manifest.job_id != job_id:
        raise AttemptStop("wrong_job", "适配器返回了其他任务的结果；未导入。")
    return content, manifest


def _existing_checkpoint(result_file: Path, job_id: str) -> tuple[bytes, CandidatePackage] | None:
    if not result_file.exists():
        return None
    try:
        return _read_result(result_file, job_id)
    except AttemptStop as exc:
        if exc.code not in {"result_invalid", "result_too_large"}:
            raise
        archived = result_file.with_name(f"result.invalid-{uuid4().hex}.zip")
        result_file.replace(archived)
        return None


def _collector_state_path(job_id: str) -> Path:
    return (Path(__file__).resolve().parents[1] / ".local" / "collection-runs"
            / str(job_id) / "current" / "collector-state.json")


def _canonical_sha256(value: object) -> str:
    encoded = json.dumps(value, ensure_ascii=False, sort_keys=True,
                         separators=(",", ":")).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


def _is_sha256(value: object) -> bool:
    return (isinstance(value, str) and len(value) == 64
            and all(char in "0123456789abcdef" for char in value))


def _collector_coverage_snapshot(library: Library, job: dict,
                                 manifest: CandidatePackage) -> dict | None:
    state_path = _collector_state_path(str(job["id"]))
    current_dir = state_path.parent
    job_dir = current_dir.parent
    root_dir = job_dir.parent
    if any(path.is_symlink() for path in (root_dir, job_dir, current_dir, state_path)):
        raise AttemptStop("collector_state_invalid", "采集器状态路径不能是符号链接。")
    try:
        state_path.resolve().relative_to(current_dir.resolve())
    except ValueError:
        raise AttemptStop("collector_state_invalid", "采集器状态超出本 Job 的稳定目录。") from None
    if not state_path.is_file():
        return None

    try:
        state = json.loads(state_path.read_text(encoding="utf-8"))
        from .collection_checkpoint import job_binding
        expected_binding = job_binding(job, library.settings.classification_model)
    except (OSError, ValueError, TypeError, KeyError, ImportError) as exc:
        raise AttemptStop("collector_state_invalid", "采集器状态或当前规则绑定不可验证。") from exc
    if (not isinstance(state, dict) or state.get("version") != 1
            or state.get("binding") != expected_binding):
        raise AttemptStop("collector_state_invalid", "采集器状态不属于当前 Job、项目条件或模型规则。")
    try:
        state_manifest = CandidatePackage.model_validate(state.get("final_manifest"))
    except (ValueError, TypeError) as exc:
        raise AttemptStop("collector_state_invalid", "采集器状态没有有效的冻结 final_manifest。") from exc
    if state_manifest.model_dump() != manifest.model_dump():
        raise AttemptStop("collector_state_invalid", "result.zip 与采集器冻结 final_manifest 不一致。")

    steps = state.get("steps")
    searches = state.get("searches")
    if not isinstance(steps, list) or not isinstance(searches, dict):
        raise AttemptStop("collector_state_invalid", "采集器状态缺少语言计划或搜索覆盖记录。")
    languages_by_query: dict[tuple[str, str], str] = {}
    planned_sources: set[str] = set()
    required_languages: set[str] = set()
    for step in steps:
        if not isinstance(step, dict):
            continue
        source, query, language = step.get("source"), step.get("query"), step.get("language")
        if not all(isinstance(value, str) and value.strip() for value in (source, query, language)):
            continue
        planned_sources.add(source)
        if language != "unknown":
            required_languages.add(language)
        key = (source, query)
        previous = languages_by_query.get(key)
        if previous is not None and previous != language:
            raise AttemptStop("collector_state_invalid", "同一冻结检索步骤绑定了多种语言。")
        languages_by_query[key] = language

    report = manifest.execution_report
    reported_pairs = {(item.source, item.query) for item in report.query_log if item.query.strip()}
    reported_sources = {source for source, _ in reported_pairs}
    reported_languages = {languages_by_query[pair] for pair in reported_pairs
                          if pair in languages_by_query and languages_by_query[pair] != "unknown"}
    state_observed_sources: set[str] = set()
    state_usable_sources: set[str] = set()
    state_observed_languages: set[str] = set()
    state_usable_languages: set[str] = set()
    for search in searches.values():
        if not isinstance(search, dict):
            continue
        source, query, language = search.get("source"), search.get("query"), search.get("language")
        key = (source, query) if isinstance(source, str) and isinstance(query, str) else None
        if key is None or key not in languages_by_query or languages_by_query[key] != language:
            continue
        if key not in reported_pairs:
            continue
        if search.get("observed"):
            state_observed_sources.add(source)
            if language != "unknown":
                state_observed_languages.add(language)
        if search.get("observed") and search.get("usable"):
            state_usable_sources.add(source)
            if language != "unknown":
                state_usable_languages.add(language)
    report_usable_sources = {item.source for item in report.source_checks if item.status == "usable"}
    return {
        "job_id": str(job["id"]),
        "collector_outcome": state.get("outcome"),
        "binding_sha256": _canonical_sha256(state["binding"]),
        "plan_sha256": _canonical_sha256({"plan": state.get("plan"), "steps": steps}),
        "manifest_sha256": _canonical_sha256(state_manifest.model_dump()),
        "planned_sources": sorted(planned_sources),
        "required_languages": sorted(required_languages),
        "observed_languages": sorted(state_observed_languages & reported_languages),
        "usable_languages": sorted(state_usable_languages & reported_languages),
        "reported_languages": sorted(reported_languages),
        "usable_sources": sorted(state_usable_sources & report_usable_sources & reported_sources),
        "reported_sources": sorted(reported_sources),
    }


def _owner_record(pid: int, *, phase: str, pgid: int | None = None) -> dict:
    owner = _process_identity(pid)
    if not owner:
        return {"pid": pid, "unknown": True, "phase": phase}
    owner["phase"] = phase
    if pgid is not None:
        owner["pgid"] = pgid
    return owner


def collection_can_resume(library: Library, job: dict) -> bool:
    if job.get("kind") != "collection" or job.get("status") in {"succeeded", "cancelled"}:
        return False
    if job.get("active_attempt_id") and _process_owner_active(job.get("collection_process_owner")):
        return False
    run_dir = library.settings.data_dir / "agent-runs" / str(job["id"])
    if not run_dir.exists():
        return job.get("status") in {"blocked", "queued", "failed"} or (job.get("status") == "running" and bool(job.get("active_attempt_id")))
    lock = AttemptFileLock(run_dir / "attempt.lock")
    if not lock.acquire():
        return False
    lock.release()
    if job.get("status") == "running":
        return bool(job.get("active_attempt_id"))
    return job.get("status") in {"blocked", "queued", "failed"}


def run_process(library: Library, job_id: str, attempt_id: str, command: list[str],
                directory: Path, seconds: float, lock_file=None, *,
                imported_result_sha256: str = "") -> int:
    env = dict(os.environ)
    env.pop("LAB_ACCESS_TOKEN", None)
    env.pop("LAB_COLLECTION_COMMAND", None)
    env.pop("LAB_COLLECTION_RECOVERY_MODE", None)
    env.pop("LAB_COLLECTION_IMPORTED_RESULT_SHA256", None)
    if imported_result_sha256:
        if not _is_sha256(imported_result_sha256):
            raise AttemptStop("collector_receipt_invalid", "已导入 ZIP 的 SHA256 回执格式无效。")
        env["LAB_COLLECTION_RECOVERY_MODE"] = "continue_imported_partial"
        env["LAB_COLLECTION_IMPORTED_RESULT_SHA256"] = imported_result_sha256
    env["LAB_DATA_DIR"] = str(directory / "adapter-scratch")
    env["LAB_COLLECTION_HISTORY_DIR"] = str((library.settings.data_dir / "assets").resolve())
    if os.name == "nt":
        command = [sys._base_executable, str(Path(__file__).with_name("windows_adapter_runner.py")), *command]
        options = {"close_fds": False}
        if lock_file is not None:
            os.set_inheritable(lock_file.fileno(), True)
    else:
        options = {"start_new_session": True}
        if lock_file is not None:
            options["pass_fds"] = (lock_file.fileno(),)
    library.set_collection_process_owner(job_id, attempt_id, _owner_record(os.getpid(), phase="launching"))
    try:
        process = subprocess.Popen(command, cwd=directory, env=env, stdin=subprocess.DEVNULL,
                                   stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, shell=False, **options)
    finally:
        if os.name == "nt" and lock_file is not None:
            os.set_inheritable(lock_file.fileno(), False)
    try:
        pgid = os.getpgid(process.pid) if os.name != "nt" else None
        library.set_collection_process_owner(job_id, attempt_id, _owner_record(process.pid, phase="running", pgid=pgid))
        deadline = time.monotonic() + seconds
        while process.poll() is None:
            job = library.job(job_id)
            if job["status"] != "running" or job.get("active_attempt_id") != attempt_id:
                raise AttemptStop("attempt_superseded", "任务已取消或状态已改变，停止本轮子进程。")
            if time.monotonic() >= deadline:
                raise AttemptStop("process_timeout", "本地 Agent 执行超时，已停止本轮进程；历史候选保留，可重试或手动交接。")
            time.sleep(min(0.05, max(0, deadline - time.monotonic())))
        return process.returncode
    finally:
        stop_process_tree(process)


def run_collection_attempt(library: Library, job_id: str) -> dict:
    initial = library.job(job_id)
    if initial["kind"] != "collection":
        raise Problem(400, "不是采集任务")
    if initial["status"] == "succeeded":
        return initial
    if initial["status"] == "cancelled":
        raise Problem(409, "已取消的采集任务不能继续")

    folder = _run_directory(library, job_id)
    lock = AttemptFileLock(folder / "attempt.lock")
    if not lock.acquire():
        raise Problem(409, "本 Job 的采集轮次仍由本地执行进程持有")
    try:
        initial = library.job(job_id)
        if initial["status"] == "succeeded":
            return initial
        if initial["status"] == "cancelled":
            raise Problem(409, "已取消的采集任务不能继续")
        previous_attempt = initial.get("active_attempt_id")
        if previous_attempt:
            if _process_owner_active(initial.get("collection_process_owner")):
                raise Problem(409, "本 Job 的采集进程仍在运行，不能抢占当前轮次")
            attempt_id = previous_attempt
            job = library.resume_collection_attempt(job_id, initial["revision"], attempt_id,
                                                    owner=_owner_record(os.getpid(), phase="initializing"))
        else:
            attempt_id = uuid4().hex
            job = library.start_collection_attempt(job_id, initial["revision"], attempt_id,
                                                   owner=_owner_record(os.getpid(), phase="initializing"))
        evidence: dict = {"code": "not_started", "created": 0, "existing": 0}
        status, detail = "blocked", "本轮尚未得到有效回执；历史候选保留。"
        try:
            task_dir, task_file, result_file = _job_artifacts(job, folder)
            _prepare_task(library, job_id, task_dir, task_file)
            paths = {"task_dir": str(task_dir), "task_file": str(task_file), "result_file": str(result_file)}
            if job.get("collection_artifacts") != paths:
                job = library.set_collection_artifacts(job_id, attempt_id, paths)

            checkpoint = _existing_checkpoint(result_file, job_id)
            previous_checkpoint = checkpoint
            recovery_receipt_sha256 = ""
            imported_sha256 = job.get("last_imported_result_sha256", "")
            can_continue_imported_partial = (
                job.get("collection_outcome") in {"partial", "blocked"}
                and _is_sha256(imported_sha256)
            )
            if checkpoint is not None and can_continue_imported_partial:
                checkpoint_sha256 = hashlib.sha256(checkpoint[0]).hexdigest()
                if checkpoint_sha256 == imported_sha256:
                    recovery_receipt_sha256 = imported_sha256
                    checkpoint = None
            elif checkpoint is None and can_continue_imported_partial:
                recovery_receipt_sha256 = imported_sha256

            if recovery_receipt_sha256 and job.get("collection_timeout_seconds") is not None:
                spent = float(job.get("collection_elapsed_seconds", 0)) + max(
                    0.0, time.time() - float(job.get("collection_attempt_started_at", time.time())))
                if spent >= float(job["collection_timeout_seconds"]):
                    checkpoint = previous_checkpoint or _read_result(
                        result_file.with_name("result-" + recovery_receipt_sha256 + ".zip"), job_id)
                    if hashlib.sha256(checkpoint[0]).hexdigest() != recovery_receipt_sha256:
                        raise AttemptStop("result_invalid", "已导入的部分结果 SHA 已变化；拒绝复用。")
                    state_path = _collector_state_path(job_id)
                    if state_path.is_file() and json.loads(state_path.read_text("utf8")).get("final_manifest"):
                        from types import SimpleNamespace
                        from tools.collect_verified import collect, write_result
                        model = library.settings.classification_model
                        sealed, images = collect(job, SimpleNamespace(model=model, producer="local-finalization"),
                                                 None, state_path.parent, finalize_only=True)
                        write_result(result_file, sealed, images, previous_result=checkpoint)
                        checkpoint = _read_result(result_file, job_id)

            if checkpoint is None:
                command = configured_command()
                limit = job.get("collection_timeout_seconds")
                if limit is None:
                    job = library.set_collection_timeout(job_id, attempt_id, timeout_seconds(job.get("target_count") or 12))
                    limit = job["collection_timeout_seconds"]
                elapsed = float(job.get("collection_elapsed_seconds", 0))
                started = float(job.get("collection_attempt_started_at", time.time()))
                remaining = float(limit) - (elapsed + max(0.0, time.time() - started))
                if remaining <= 0:
                    raise AttemptStop("process_timeout", "本 Job 已用尽累计执行时间预算；保留现有任务和候选，不重置预算。")
                replacements = {"{task_dir}": str(task_dir), "{task_file}": str(task_file), "{result_file}": str(result_file)}
                argv = []
                for arg in command:
                    for key, value in replacements.items():
                        arg = arg.replace(key, value)
                    argv.append(arg)
                code = run_process(library, job_id, attempt_id, argv, task_dir, remaining, lock.file,
                                   imported_result_sha256=recovery_receipt_sha256)
                evidence["returncode"] = code
                if code:
                    raise AttemptStop("process_failed", f"本地适配程序退出码 {code}；已保留其结果文件，历史候选不变。", "failed")
                try:
                    checkpoint = _read_result(result_file, job_id)
                except AttemptStop as exc:
                    if exc.code == "result_invalid":
                        raise AttemptStop("adapter_or_result_error", exc.detail) from exc
                    raise
            content, manifest = checkpoint
            if manifest.job_id != job_id:
                raise AttemptStop("wrong_job", "适配器返回了其他任务的结果；未导入。")
            latest = library.job(job_id)
            if latest["status"] != "running" or latest.get("active_attempt_id") != attempt_id:
                raise AttemptStop("attempt_superseded", "任务已结束或被替代，拒绝导入过期输出。")
            collector_coverage = _collector_coverage_snapshot(library, latest, manifest)
            result_sha256 = hashlib.sha256(content).hexdigest()
            imported = import_candidates(
                library, job["project_id"], content, job_id, attempt_id=attempt_id,
                collector_coverage=collector_coverage, result_sha256=result_sha256)
            evidence.update(code="result_imported", created=imported["created"], existing=imported["existing"],
                            errors=len(imported["errors"]), reference_ids=imported["reference_ids"])
        except AttemptStop as exc:
            status, detail = exc.status, exc.detail
            evidence["code"] = exc.code
        except (ValueError, KeyError, TypeError, OSError, Problem, subprocess.SubprocessError) as exc:
            status, detail = "blocked", "本地适配或候选包校验失败；未宣称采集成功，已导入的候选保留。"
            evidence.update(code="adapter_or_result_error", error_type=type(exc).__name__)
        except Exception as exc:
            library.finish_collection_attempt(job_id, attempt_id, "failed", "采集执行器内部异常；需检查代码，不是成功。",
                                              {**evidence, "code": "internal_error", "error_type": type(exc).__name__})
            raise
        return library.finish_collection_attempt(job_id, attempt_id, status, detail, evidence)
    finally:
        lock.release()
