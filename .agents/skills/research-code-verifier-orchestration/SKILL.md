---
name: research-code-verifier-orchestration
description: Orchestrate explicitly authorized parallel agent work when independent research and code implementation need a separate frozen verifier (需要多 Agent 并行研究与实现并由独立验收时使用). Do not use for a single CSS or bug fix, pure Q&A, research-only work that does not need CC, or external-agent calls without explicit authorization.
---

# Research, code and independent verification

Use this experimental workflow only when the user authorizes the external agents and both independent source research and bounded code implementation can proceed at the same time, with a separate verifier needed to judge the result. For a narrow code fix, pure Q&A, or research that does not need CC, do not start this orchestration. Never call an external agent without authorization for that agent and service.

Reuse the project's existing `codex-cc-minimax-dispatch` Skill for CC setup, route checks, permissions and bounded edits. Use the installed, officially supported AGY CLI for research. Reuse existing invocation and evidence-capture helpers where available; do not build a persistent orchestration framework or broaden permissions to make a task pass.

Before dispatch, inspect the task instructions and dirty state, record acceptance criteria, and assign each agent a separate worktree and non-overlapping owned paths. Prepare the independent verifier's acceptance criteria and tests from the user goal, public interfaces and project rules before implementation starts. Give the verifier no implementation conversation, design, or expected output. Freeze its originals and record SHA-256 hashes before dispatch; keep them outside agent write access and confirm the hashes remain unchanged after calls.

Start the research and implementation subprocesses with `Popen` before waiting for either. Record each PID and actual start/end times, and establish a positive interval overlap from process evidence. Queued or sequential calls are not parallel execution. Capture real CLI tool events and their results, process exits, stderr and resulting artifacts. A model's `SUCCESS` text, a zero exit alone, or a non-fatal hook warning does not establish that a tool ran or that acceptance passed; inspect the corresponding events and outcomes.

Run the frozen checks independently against the produced work. Preserve failing tests and report failures plainly. If bounded repair is appropriate, send the concrete observed failure to the responsible agent and limit directed rework to two rounds. Re-run independent acceptance after each repair; stop and report remaining failures when the limit is reached. Never weaken or replace frozen assertions to obtain a pass.

Treat browser access and new video or timed-audio evidence as conditional on a supported browser connection and the source actually serving accessible material. Record unavailable connections, login or bot challenges, and HTTP errors such as 403 as blockers. Do not bypass access controls, export cookies, use hidden APIs, or retry challenges aggressively. Search results and titles do not prove video content.

Return exact changed paths, actual tool/process evidence, frozen-check results, failures, and unverified claims to the parent agent. The parent owns the Publisher and any authorized Git delivery; this workflow does not publish from a child agent.

## Pilot limits

The October 2026 pilot demonstrated real subprocess overlap, isolated worktrees, frozen independent checks and two directed CC rework calls. Product acceptance still failed with 77 checks passing and 4 failing; no new video evidence was verified, and some external calls ended without successful terminal completion. The evidence supports that the controller can perform bounded parallel dispatch and independent checking. It does not establish a mature orchestration system, accepted product behavior, complete research, or a cost or speed advantage.
