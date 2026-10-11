---
name: codex-multi-agent-orchestration
description: "Organize substantive research plus coding plus independent testing, explicit multi-agent collaboration, or authorized external research/coding agents. Select only when the requested goal needs this coordination and external-agent use is authorized. Do not load for button colors, simple CSS edits, routine bug fixes or knowledge questions; an authorization or a planning wrapper alone is not a trigger."
---

# Codex Multi-Agent Orchestration

## Decide before dispatch

Read the actual task and project rules. Use multiple agents only when independently useful research, implementation or acceptance work exists. A routine edit stays with Codex; never consume quota merely to show parallelism. Confirm current or standing authorization for external agents and probe the installed tools. Skill selection does not create authorization, solve permissions or authorize paid APIs. If external use is unauthorized, keep execution local and report the missing boundary.

Separate this orchestration procedure from domain skills: choose the narrow domain skill for research methods, evidence interpretation, browser operation or implementation conventions. Keep those rules out of this skill.

## Roles and isolated ownership

| Role | Responsibility | Handoff |
| --- | --- | --- |
| Codex | Control, requirement decomposition, acceptance design, scheduling, integration and delivery | Frozen goal, dependency graph, exact writable paths |
| AGY | Information exploration, visual research, webpage/image/video understanding | Research materials with actual evidence and source limitations; not final course/product copy |
| CC | Code implementation, bounded refactoring and test repair | Diff, actual commands/results, unresolved issues |
| Verifier | Independent test design, red-team checks and failure reproduction | PASS / REVISE / BLOCKED with reproducible evidence |

Create separate worktrees and branches from an inspected baseline for execution and verification. For this project, resolve every new worktree, experiment, verification and backup destination inside `D:\AI PROJECTS\photography-reference-lab`; use `.local/worktrees/<task>/<role>` and `.local/backups/<timestamp>`. Never create project siblings at `D:\AI PROJECTS` top level or use a default external managed-worktree location. Give each agent exact writable paths; never allow concurrent edits to the same key file. Preserve unrelated dirty work. ROOT alone integrates and publishes under the project's delivery rules; child agents return files and evidence only.

Start Verifier in a fresh context containing only the goal, constraints and existing product. Do not pass implementation discussions, agent prompts, self-assessments or suggested tests. Freeze its observable acceptance criteria before dispatching implementation; record their hash and time. Codex may reconcile criteria against the user's requirements before freezing, but cannot relax them after seeing results. Verifier subsequently receives candidate artifacts and original evidence only. Independent does not mean unable to inspect the finished code.

## Schedule and observe

1. Record intent, observable requirements, dependencies, ownership and applicable delivery transaction before editing.
2. Dispatch only genuinely independent tasks in parallel. Research and a generic compatible renderer may overlap; integrating research content waits for the research result. Acceptance waits for candidate artifacts. Do not prescribe a specific vendor in the user's reuse goal; derive roles from the selected skill and available authorized agents.
3. Before substantive dispatch, verify the current model entry point and a small representative operation through the exact transport required by the task. Executable presence, logged-in UI and an old successful run are insufficient. Record readiness separately for model, permissions, selected execution context, actual operation and returned artifact. Use the installed external AGY and CC CLI/MCP interfaces with scoped permissions; never simulate them with an internal Codex subagent. A necessary unavailable or denied capability is BLOCKED. Resolve an authorized setup repair as a separate dependency before resuming; never bypass controls or silently substitute another provider. See [external handoffs](references/external-handoffs.md).
4. For every process record role, exact non-secret argv, cwd/branch/baseline, PID, UTC start/end, exit code, timeout/denied tools, writable paths and evidence locations. Preserve failed attempts. Keep long runs checkpointed and poll without restarting successes.
5. Inspect actual tool events, files, diffs and tests. CLI SUCCESS/exit 0 is transport evidence only; an agent's self-assessment is never acceptance. Missing evidence remains unknown.

## Independent acceptance and directed revision

- **PASS:** every frozen criterion has complete actual evidence; distinguish engineering checks from human/domain acceptance.
- **REVISE:** identify the failed criterion, reproduction, observed/expected behavior and responsible agent. Return source/evidence defects to AGY and code/compatibility/state defects to CC. Send only the actionable failure, not a new easier standard.
- **BLOCKED:** a necessary permission/input/capability is missing, or two directed revision rounds have failed. Report the exact blocker and retain artifacts. Resume only when new authorization/evidence resolves it.

Allow at most **two** directed revision rounds per task after the initial candidate. Before a repair, review prior relevant failures and root cause; repair the responsible boundary rather than stacking exceptions. Rerun the failed check and affected regressions against the same frozen criteria. Hash-check the criteria before and after acceptance. Never delete failing tests, lower standards, edit Verifier to make an implementation pass, or manufacture a defect just to demonstrate revision.

## Evidence and delivery

Record selection/dispatch, real process overlap when applicable, acceptance failures, directed revision and final reruns. Separate VERIFIED, PARTIALLY VERIFIED, UNVERIFIED and BLOCKED claims. Report actual Git/Notion receipts independently. A published checkpoint does not prove domain truth or product acceptance. A claim of improvement over one agent needs comparable baseline evidence; otherwise report the observed defects caught without claiming an A/B win.

## Limits

This skill does not resolve browser permissions, perform video forensics, define photography research, choose aesthetic judgments or design code architecture. Domain skills and the user's decisions own those boundaries. It creates no agent platform, daemon, global skill installation, deployment permission or automatic learning-state writes.
