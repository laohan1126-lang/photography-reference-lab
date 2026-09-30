"""Opt-in native Agent transport; task packages, not a built-in website scraper.

The owner configures argv for an installed local adapter. This module does not
invent vendor CLI flags, install software, start a browser or make model calls.
Process exit is transport evidence, never proof of image identity or quality.
"""
from __future__ import annotations

import json
import math
import os
from pathlib import Path
import shutil
import signal
import subprocess
import sys
import tempfile
import time
from uuid import uuid4

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
    if os.name == "nt" and not shutil.which("taskkill"):
        raise AttemptStop("process_cleanup_unavailable", "缺少 Windows 子进程树清理工具；未启动适配器。")
    return [executable, *command[1:]]


def timeout_seconds() -> float:
    try:
        # A real BrowserSkill pass drives a live browser: 8+ queries, lazy page
        # loads and per-card detail pages routinely run past ten minutes, and a
        # 600s default killed the adapter mid-run every time.
        seconds = float(os.environ.get("LAB_COLLECTION_TIMEOUT_SECONDS", "1800"))
        if not math.isfinite(seconds) or not 0.1 <= seconds <= 3600:
            raise ValueError
        return seconds
    except ValueError:
        raise AttemptStop("invalid_timeout", "采集超时设置须为 0.1 到 3600 之间的有限秒数。") from None


def stop_process_tree(process: subprocess.Popen, *, windows_job_owned: bool = False) -> None:
    """Terminate only this attempt's process group, never the owner's browser."""
    if os.name == "nt":
        if process.poll() is None:
            if windows_job_owned:
                # Kill the actual supervisor by its held process handle. Its job
                # handle closes in the kernel; no slow/PID-based taskkill launch.
                process.terminate()
            else:
                result = subprocess.run(["taskkill", "/PID", str(process.pid), "/T", "/F"],
                                        stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, timeout=10)
                if result.returncode and process.poll() is None:
                    raise AttemptStop("cleanup_failed", "Windows 子进程树清理失败，请检查本地进程；未宣称本轮成功。", "failed")
    else:
        try:
            # A child may remain in the group after the parent exits.
            os.killpg(process.pid, signal.SIGKILL)
        except ProcessLookupError:
            pass  # No such group is the desired cleanup outcome, not a lost error.
    process.wait(timeout=10)


def run_process(library: Library, job_id: str, attempt_id: str, command: list[str],
                directory: Path, seconds: float) -> int:
    env = dict(os.environ)
    env.pop("LAB_ACCESS_TOKEN", None)
    env.pop("LAB_COLLECTION_COMMAND", None)
    # A wrapper must return an artifact, not import into the real personal DB.
    env["LAB_DATA_DIR"] = str(directory / "adapter-scratch")
    options = {"creationflags": subprocess.CREATE_NEW_PROCESS_GROUP} if os.name == "nt" else {"start_new_session": True}
    if os.name == "nt":
        # Venv python.exe can be a redirector parent. The stdlib-only supervisor
        # must be the process whose handle we hold; the adapter keeps its venv.
        command = [sys._base_executable, str(Path(__file__).with_name("windows_adapter_runner.py")), *command]
    process = subprocess.Popen(command, cwd=directory, env=env, stdin=subprocess.DEVNULL,
                               stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, shell=False, **options)
    try:
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
        stop_process_tree(process, windows_job_owned=os.name == "nt")


def run_collection_attempt(library: Library, job_id: str) -> dict:
    initial = library.job(job_id)
    attempt_id = uuid4().hex
    job = library.start_collection_attempt(job_id, initial["revision"], attempt_id)
    evidence: dict = {"code": "not_started", "created": 0, "existing": 0}
    status, detail = "blocked", "本轮尚未得到有效回执；历史候选保留。"
    try:
        command, seconds = configured_command(), timeout_seconds()
        # Temporary task artifacts can contain private project context. They are
        # removed on exit; only safe metadata and imported originals persist.
        root = library.settings.data_dir / "agent-runs"
        root.mkdir(mode=0o700, parents=True, exist_ok=True)
        with tempfile.TemporaryDirectory(prefix=attempt_id + "-", dir=root) as tmp:
            directory = Path(tmp).resolve()
            pack = build_job_pack(library, job_id)
            try:
                # Only expand the application's own generated collection pack.
                for name, content in read_archive(pack.read_bytes()).items():
                    dest = directory / name
                    dest.parent.mkdir(parents=True, exist_ok=True)
                    dest.write_bytes(content)
            finally:
                pack.unlink(missing_ok=True)
            task = directory / "AGENT_TASK.md"
            result_file = directory / "result.zip"
            task.write_text(task.read_text(encoding="utf-8") +
                            "\n## 本次自动适配器交付约束（替代上文 import-job 指示）\n"
                            "只生成 result.zip 到适配器指定位置。不要自行导入、操作网页 API 或修改个人数据库。"
                            "网页负责校验并导入；stdout/stderr 不作为结果也不会记录。\n", encoding="utf-8")
            replacements = {"{task_dir}": str(directory), "{task_file}": str(task), "{result_file}": str(result_file)}
            argv = []
            for arg in command:
                for key, value in replacements.items():
                    arg = arg.replace(key, value)
                argv.append(arg)
            code = run_process(library, job_id, attempt_id, argv, directory, seconds)
            evidence["returncode"] = code
            if code:
                raise AttemptStop("process_failed", f"本地适配程序退出码 {code}；未接受未完成的结果，历史候选不变。", "failed")
            latest = library.job(job_id)
            if latest["status"] != "running" or latest.get("active_attempt_id") != attempt_id:
                raise AttemptStop("attempt_superseded", "任务已结束或被替代，拒绝导入过期输出。")
            if result_file.is_symlink() or not result_file.is_file():
                raise AttemptStop("result_missing", "适配程序未返回普通 result.zip 文件；退出码 0 不等于采集完成。")
            with result_file.open("rb") as stream:
                content = stream.read(MAX_ARCHIVE_BYTES + 1)
            if len(content) > MAX_ARCHIVE_BYTES:
                raise AttemptStop("result_too_large", "候选包超过限制；未导入。")
            files = read_archive(content)
            manifest = CandidatePackage.model_validate_json(files["manifest.json"])
            if manifest.job_id != job_id:
                raise AttemptStop("wrong_job", "适配器返回了其他任务的结果；未导入。")
        # Complete private temporary-file cleanup before recording a successful receipt.
        imported = import_candidates(library, job["project_id"], content, job_id, attempt_id=attempt_id)
        evidence.update(code="result_imported", created=imported["created"], existing=imported["existing"],
                        errors=len(imported["errors"]), reference_ids=imported["reference_ids"])
        # The importer owns final status. A blocked report stays blocked.
    except AttemptStop as exc:
        status, detail = exc.status, exc.detail
        evidence["code"] = exc.code
    except (ValueError, KeyError, TypeError, OSError, Problem, subprocess.SubprocessError) as exc:
        status, detail = "blocked", "本地适配或候选包校验失败；未宣称采集成功，已导入的候选保留。"
        evidence.update(code="adapter_or_result_error", error_type=type(exc).__name__)
    except Exception as exc:
        # Never leave the job falsely running on an unexpected implementation error.
        library.finish_collection_attempt(job_id, attempt_id, "failed", "采集执行器内部异常；需检查代码，不是成功。",
                                          {**evidence, "code": "internal_error", "error_type": type(exc).__name__})
        raise
    return library.finish_collection_attempt(job_id, attempt_id, status, detail, evidence)
