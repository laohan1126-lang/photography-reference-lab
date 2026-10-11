"""Run fresh Codex skill-discovery sessions and preserve raw evidence."""
from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime, timezone
import argparse
import hashlib
import json
import os
from pathlib import Path
import re
import shutil
import subprocess
import winreg


ROOT = Path(r"D:\AI PROJECTS\photography-reference-lab")
OUT = ROOT / ".local/orchestration-rename/discovery"
EXTERNAL = Path(r"D:\AI PROJECTS\orchestration-rename-validation-20261011")
USER_SKILL = Path(r"C:\Users\Dell\.agents\skills\codex-multi-agent-orchestration\SKILL.md")
PROJECT_SKILL = ROOT / ".agents/skills/codex-multi-agent-orchestration/SKILL.md"
PROJECT_RULES = ROOT / "AGENTS.md"
EVALS = ROOT / ".forge/codex-multi-agent-orchestration/evals.json"
TIMEOUT_SECONDS = 300
MAX_PARALLEL = 3

PREFIX = (
    "本轮只评估 Codex 对已安装技能的发现行为。仅可读取本案例明确允许的 SKILL.md、"
    "以及明确允许的项目规则；不得改写或新建源码、配置、测试或其他文件，不得启动代理、"
    "浏览器或外部服务，不得运行代码，不得读取凭据、环境变量、用户数据、其他仓库或历史日志。"
    "不要尝试改变这些边界。只给简短计划然后停止。\n\n"
)


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def normalized(value: str) -> str:
    return value.replace("\r\n", "\n").replace("\r", "\n").strip("\n")


def normalized_path(value: str) -> str:
    return re.sub(r"\\+", r"\\", value.replace("/", "\\")).rstrip("\\").casefold()


def contains_complete_body(value: object, body: str) -> bool:
    if isinstance(value, str):
        return bool(normalized(body)) and normalized(body) in normalized(value)
    if isinstance(value, dict):
        return any(contains_complete_body(item, body) for item in value.values())
    if isinstance(value, list):
        return any(contains_complete_body(item, body) for item in value)
    return False


def has_path(value: object, target: Path, base_cwd: Path | None = None) -> bool:
    wanted = [normalized_path(str(target))]
    if base_cwd is not None:
        try:
            wanted.append(normalized_path(str(target.relative_to(base_cwd))))
        except ValueError:
            pass
    if isinstance(value, str):
        normalized_value = normalized_path(value)
        return any(path and path in normalized_value for path in wanted)
    if isinstance(value, dict):
        return any(has_path(item, target, base_cwd) for item in value.values())
    if isinstance(value, list):
        return any(has_path(item, target, base_cwd) for item in value)
    return False


def successful_tool_read(event: dict, target: Path, body: str, base_cwd: Path | None = None) -> bool:
    if event.get("type") != "item.completed":
        return False
    item = event.get("item", {})
    kind = item.get("type")
    if kind == "command_execution":
        return (
            item.get("exit_code") == 0
            and has_path(item.get("command", ""), target, base_cwd)
            and contains_complete_body(item.get("aggregated_output", ""), body)
        )
    if kind == "mcp_tool_call":
        result = item.get("result", {})
        return (
            result.get("isError") is not True if isinstance(result, dict) else True
        ) and has_path(item.get("arguments", {}), target, base_cwd) and contains_complete_body(result, body)
    return False


def skill_read_events(events: list[dict], target: Path, body: str, base_cwd: Path | None = None) -> list[dict]:
    return [event for event in events if successful_tool_read(event, target, body, base_cwd)]


def parse_events(path: Path) -> list[dict]:
    events = []
    for line in path.read_text(encoding="utf-8").splitlines():
        try:
            events.append(json.loads(line))
        except json.JSONDecodeError:
            events.append({"type": "malformed_line", "raw": line})
    return events


def child_environment() -> tuple[dict[str, str], bool]:
    env = os.environ.copy()
    for key in ("HTTP_PROXY", "HTTPS_PROXY", "ALL_PROXY", "http_proxy", "https_proxy", "all_proxy"):
        env.pop(key, None)
    forwarded = False
    with winreg.OpenKey(
        winreg.HKEY_CURRENT_USER,
        r"Software\Microsoft\Windows\CurrentVersion\Internet Settings",
    ) as key:
        enabled = winreg.QueryValueEx(key, "ProxyEnable")[0]
        if enabled:
            proxy = winreg.QueryValueEx(key, "ProxyServer")[0]
            if not proxy.startswith("127.0.0.1:"):
                raise RuntimeError("Configured proxy is not an allowed loopback proxy")
            env["HTTP_PROXY"] = env["HTTPS_PROXY"] = "http://" + proxy
            env["NO_PROXY"] = "localhost,127.0.0.1"
            forwarded = True
    return env, forwarded


def run_case(case: dict, codex: str, bodies: dict[str, str], hashes: dict[str, str]) -> dict:
    session_dir = EXTERNAL / case["id"]
    if session_dir.exists():
        raise RuntimeError(f"Refusing to reuse existing session directory: {session_dir}")
    session_dir.mkdir(parents=True)
    process_cwd = ROOT if case.get("execution_cwd") == "project" else session_dir
    events_path = session_dir / "events.jsonl"
    stderr_path = session_dir / "stderr.txt"
    final_path = session_dir / "final.txt"
    prompt = PREFIX + case["prompt"]
    argv = [
        codex, "exec", "--ephemeral", "--json", "--color", "never",
        "--skip-git-repo-check", "--sandbox", "danger-full-access",
        "-C", str(process_cwd), "-o", str(final_path), prompt,
    ]
    record = {
        "case_id": case["id"],
        "expected_skill": case["expected_skill"],
        "expected_path": case["expected_path"],
        "prompt": prompt,
        "cwd": str(process_cwd),
        "session_dir": str(session_dir),
        "argv": argv,
        "started_at_utc": utc_now(),
        "skill_sha256_before": hashes,
        "timeout_seconds": TIMEOUT_SECONDS,
        "host_sandbox": "danger-full-access; prompt is read-only constraint, not an OS sandbox",
    }
    env, proxy_forwarded = child_environment()
    record["loopback_proxy_forwarded_to_child"] = proxy_forwarded
    with events_path.open("w", encoding="utf-8", newline="\n") as stdout, stderr_path.open(
        "w", encoding="utf-8", newline="\n"
    ) as stderr:
        process = subprocess.Popen(
            argv,
            cwd=process_cwd,
            env=env,
            stdout=stdout,
            stderr=stderr,
            creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0),
        )
        record["pid"] = process.pid
        record["process_started_at_utc"] = utc_now()
        (session_dir / "started.json").write_text(
            json.dumps(record, ensure_ascii=False, indent=2), encoding="utf-8"
        )
        print(json.dumps({"case": case["id"], "pid": process.pid, "started_at_utc": record["process_started_at_utc"]}), flush=True)
        timed_out = False
        try:
            process.wait(timeout=TIMEOUT_SECONDS)
        except subprocess.TimeoutExpired:
            timed_out = True
            process.kill()
            process.wait()
        record["timeout"] = timed_out
        record["exit_code"] = process.returncode
        record["ended_at_utc"] = utc_now()

    events = parse_events(events_path)
    user_skill_reads = skill_read_events(events, USER_SKILL, bodies["user"], process_cwd)
    project_skill_reads = skill_read_events(events, PROJECT_SKILL, bodies["project"], process_cwd)
    target_read = {
        "user": user_skill_reads,
        "project": project_skill_reads,
        "none": [],
    }[case["expected_skill"]]
    other_skill_read = {
        "user": project_skill_reads,
        "project": user_skill_reads,
        "none": user_skill_reads + project_skill_reads,
    }[case["expected_skill"]]
    rules_read = skill_read_events(events, PROJECT_RULES, bodies["rules"], process_cwd)
    record["qualification_base_cwd"] = str(process_cwd)
    record["events"] = events
    record["thread_ids"] = [event.get("thread_id") for event in events if event.get("type") == "thread.started"]
    record["terminal_events"] = [
        event for event in events if event.get("type") in ("turn.completed", "turn.failed", "error")
    ]
    record["tool_failures_or_denials"] = [
        event for event in events
        if event.get("type") in ("item.failed", "error")
        or (event.get("type") == "item.completed" and event.get("item", {}).get("type") == "command_execution"
            and event.get("item", {}).get("exit_code") not in (0, None))
    ]
    record["expected_skill_read_events"] = target_read
    record["observed_expected_skill_read"] = bool(target_read)
    record["user_skill_read_events"] = user_skill_reads
    record["project_skill_read_events"] = project_skill_reads
    record["other_scope_skill_read_events"] = other_skill_read
    record["observed_other_scope_skill_read"] = bool(other_skill_read)
    record["project_rules_read_events"] = rules_read
    record["observed_project_rules_read"] = bool(rules_read)
    record["final_text"] = final_path.read_text(encoding="utf-8") if final_path.exists() else ""
    record["skill_sha256_after"] = {
        "user": sha256(USER_SKILL), "project": sha256(PROJECT_SKILL), "rules": sha256(PROJECT_RULES)
    }
    record["skill_files_unchanged"] = record["skill_sha256_after"] == hashes
    record["matches_expected"] = (
        not timed_out and process.returncode == 0
        and record["observed_expected_skill_read"] == (case["expected_skill"] != "none")
        and not record["observed_other_scope_skill_read"]
        and (not case.get("require_project_rules_read") or record["observed_project_rules_read"])
        and record["skill_files_unchanged"]
    )
    (session_dir / "result.json").write_text(json.dumps(record, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps({
        "case": case["id"], "pid": record["pid"], "exit_code": record["exit_code"],
        "timeout": timed_out, "skill_read": record["observed_expected_skill_read"],
        "other_scope_skill_read": record["observed_other_scope_skill_read"],
        "matches_expected": record["matches_expected"],
    }), flush=True)
    return record


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--case", action="append", dest="selected_cases", help="run only this case ID; may be repeated")
    parser.add_argument("--batch", required=True, help="new evidence subdirectory name under the discovery output")
    args = parser.parse_args()
    if Path(args.batch).name != args.batch or args.batch in (".", ".."):
        raise RuntimeError("Batch name must be one path component")
    out_dir = OUT / args.batch
    if out_dir.exists():
        raise RuntimeError(f"Refusing to overwrite batch evidence directory: {out_dir}")
    out_dir.mkdir(parents=True)
    EXTERNAL.mkdir(parents=True, exist_ok=True)
    codex = shutil.which("codex")
    if not codex:
        raise RuntimeError("codex executable not found on PATH")
    all_cases = json.loads(EVALS.read_text(encoding="utf-8"))["cases"]
    if args.selected_cases:
        requested = set(args.selected_cases)
        cases = [case for case in all_cases if case["id"] in requested]
        found = {case["id"] for case in cases}
        missing = requested - found
        if missing:
            raise RuntimeError(f"Unknown case IDs: {sorted(missing)}")
    else:
        cases = [case for case in all_cases if not case.get("diagnostic_only")]
    bodies = {
        "user": USER_SKILL.read_bytes().decode("utf-8"),
        "project": PROJECT_SKILL.read_bytes().decode("utf-8"),
        "rules": PROJECT_RULES.read_bytes().decode("utf-8"),
    }
    hashes = {key: hashlib.sha256(value.encode("utf-8")).hexdigest() for key, value in bodies.items()}
    version = subprocess.run([codex, "--version"], capture_output=True, text=True, check=True).stdout.strip()
    manifest = {
        "started_at_utc": utc_now(),
        "cwd_root": str(EXTERNAL),
        "codex_path": codex,
        "codex_version": version,
        "evals_path": str(EVALS),
        "skill_paths": {"user": str(USER_SKILL), "project": str(PROJECT_SKILL), "project_rules": str(PROJECT_RULES)},
        "skill_sha256": hashes,
        "user_skill_version": "1.0.0",
        "timeout_seconds_per_session": TIMEOUT_SECONDS,
        "max_parallel": MAX_PARALLEL,
        "sandbox": "inherited host danger-full-access; prompts restrict planning sessions to read-only behavior",
        "session_files": ["started.json", "events.jsonl", "stderr.txt", "final.txt", "result.json"],
    }
    manifest["batch"] = args.batch
    manifest["selected_case_ids"] = [case["id"] for case in cases]
    manifest["initial_pilot_evidence"] = str(OUT)
    (out_dir / "manifest.json").write_text(json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8")
    (out_dir / "evals.snapshot.json").write_text(json.dumps({"suite": "codex-multi-agent-orchestration-rename-discovery-v1", "cases": cases}, ensure_ascii=False, indent=2), encoding="utf-8")
    results = []
    with ThreadPoolExecutor(max_workers=MAX_PARALLEL) as pool:
        futures = [pool.submit(run_case, case, codex, bodies, hashes) for case in cases]
        for future in as_completed(futures):
            results.append(future.result())
    results.sort(key=lambda item: next(i for i, case in enumerate(cases) if case["id"] == item["case_id"]))
    summary = {
        "ended_at_utc": utc_now(),
        "skill_sha256_after": {"user": sha256(USER_SKILL), "project": sha256(PROJECT_SKILL), "rules": sha256(PROJECT_RULES)},
        "all_sessions_completed_and_matched": all(item["matches_expected"] for item in results),
        "results": [{
            "case_id": item["case_id"], "pid": item["pid"], "thread_ids": item["thread_ids"],
            "started_at_utc": item["process_started_at_utc"], "ended_at_utc": item["ended_at_utc"],
            "exit_code": item["exit_code"], "timeout": item["timeout"],
            "expected_skill": item["expected_skill"], "observed_expected_skill_read": item["observed_expected_skill_read"],
            "observed_other_scope_skill_read": item["observed_other_scope_skill_read"],
            "matches_expected": item["matches_expected"], "session_dir": item["session_dir"],
        } for item in results],
    }
    (out_dir / "summary.json").write_text(json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps({"summary_path": str(out_dir / "summary.json"), "all_matched": summary["all_sessions_completed_and_matched"]}, ensure_ascii=False))
    return 0 if summary["all_sessions_completed_and_matched"] else 2


if __name__ == "__main__":
    raise SystemExit(main())
