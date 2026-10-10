---
name: codex-cc-minimax-dispatch
description: Delegate bounded repository fixes to an existing Claude Code CLI configured for MiniMax through CC Switch, while Codex owns isolation, independent acceptance, review and delivery. Use only for explicitly authorized external CC work; this is a project candidate awaiting reuse on another real task.
---

Codex is the controller. CC produces real patches; Codex prepares acceptance first,
inspects the diff, runs tests, directs bounded rework and publishes only owned paths.

## Confirm the route before any paid call

- Inspect `Get-Command claude`, `claude --version`, `claude --help`. Use the actual
  executable; this pilot verified native Claude Code 2.1.220, not other versions.
- Parse `~/.claude/settings.json` privately. Expose only the endpoint, model names
  and whether credentials exist. Never print tokens, auth files or entire settings.
- Read CC Switch's current selection and active Claude provider read-only. In its
  SQLite database inspect the schema, selected provider and routing/failover state;
  compare live settings to the active provider, including credential equality as a
  Boolean. Never assume localhost identifies the upstream provider. If local routing
  is active, require its active upstream and actual request-routing evidence first.
- Inspect inherited `ANTHROPIC_*` overrides privately. They can override user settings.
  Only after the selected MiniMax route is confirmed, construct a child environment
  that removes inherited `ANTHROPIC_*` and copies those keys from the existing selected
  user settings. Leave parent environment, proxy, credentials and CC Switch unchanged.
- Stop if the route is uncertain, mismatched, has unexplained failover or could request
  official Anthropic. Model names and the SDK's `provider: firstParty` label alone are
  insufficient. Require selected-provider evidence, effective endpoint/debug evidence
  and a real response; record the service-reported model without claiming weight-level
  attestation. Sanitize debug logs before displaying or saving shared evidence.

Use one bounded readiness call, with no tools or customizations:

```text
claude -p "只回复 CC_MINIMAX_READY" --output-format json --max-turns 1 --safe-mode --setting-sources user --tools "" --no-session-persistence
```

Capture PID, exit code, JSON `is_error`, result, stderr, route and usage. Re-audit
route/settings before and after each development call. Unknown cost stays unknown;
CLI `total_cost_usd` is an estimate, not verified MiniMax billing or quota consumption.

## Isolate and prepare independent acceptance

Verify the requested remote base SHA and current dirty state. Preserve unrelated work.
Use a separate worktree on the requested task branch; do not initialize a new repository.

```text
git ls-remote origin refs/heads/<requested-base>
git worktree add -b codex/<task> <isolated-path> <verified-base-sha>
```

Follow the repository's task contract/publisher instructions before the first edit.
Prepare meaningful behavioral tests outside CC's workspace before delegation; run them
on the baseline and record the file SHA256. Positive filesystem fixtures must contain
real nonempty bytes and calculated hashes. Describe structural fixtures honestly.
Keep tests out of CC's edit/read authorization; verify their hash after every call.

## Dispatch with exact file permission

Pass a concrete problem, allowed paths, observable acceptance, preserved invariants
and honest test limitations. Let CC read existing code. It must implement, not propose.
Use the verified executable in a subprocess with `cwd` equal to the worktree and the
confirmed child environment. Use fresh sessions, without `--resume`/`--continue`.

```text
claude -p <task-prompt> --output-format stream-json --verbose --max-turns 12 --permission-mode dontAsk --safe-mode --setting-sources user --tools Read,Edit,Write,Glob,Grep --allowedTools "Edit(./<exact-source-file>)" "Edit(./<exact-test-file>)" --no-session-persistence
```

Build subprocess arguments as a list, not shell interpolation. Add `--disallowedTools`
Read rules for credential/config directories, `.env` and the protected acceptance area;
on Windows absolute patterns use `//c/...`, `//d/...`. Exact `Edit(path)` rules cover
both Edit and Write. `Write(path)` rules were ignored by this verified CLI version.
`dontAsk` denies unapproved writes; read access inside cwd is still available.
No Bash/PowerShell/network/MCP/Agent tools are exposed. Do not broaden permissions to
make a task succeed; Codex runs tests. Do not use bypass flags or skip permissions.
`--safe-mode` disables customizations/hooks, so supply relevant project boundaries in
the prompt and let Codex perform the repository's normal finalization separately.

Record actual tool-use IDs, paths and corresponding success/error results, terminal
JSON, stderr, exit code, elapsed time, usage and diff. A zero exit or completion claim
does not prove correctness. A turn-limit exit can leave a partial real patch: retain
it, inspect it and run independent checks before deciding what needs rework. Eight
turns exhausted this pilot's first fix; twelve allowed the second session to finish.
Choose a bounded budget appropriate to scope, not unlimited continuation.

## Review, rework and stop

Run protected acceptance and required regressions against the isolated checkout;
verify imports resolve there. Check the exact diff, unchanged standards/settings and
unrelated paths. If historical tests depend on the bug, report the conflict and ask
CC to repair real fixtures while retaining assertions. Codex must not quietly replace
CC's main implementation or allow deleted tests, weaker assertions or ERROR downgrades.

Send actual failure behavior and narrow scope corrections to another real CC call.
Limit controller-directed rework to two rounds. Stop on persistent failure, unsafe
authorization, quota/auth errors, unknown route or unexpected provider switching.
After one fix passes, use a new independent session for the next bounded task.
Report process failures separately from independently verified task outcomes.

Good candidates have small code ownership, deterministic acceptance and reversible
patches. Do not delegate production changes, secrets/configuration, original data,
destructive operations, aesthetic decisions, broad architecture changes or tasks that
require unrestricted shell/network access under this file-only method.

## Delivery and cleanup

Report routes, calls, actual edits, baseline/after results, rework, unknown billing,
limitations and manual handoff count. Keep raw sanitized logs private; share only
necessary evidence. Commit/push only when authorized, with exact paths and remote-SHA
verification. No automatic global Skill install: require successful reuse first.
`--no-session-persistence` avoids resumable chat state, but makes no zero-retention claim.
Retain the worktree/evidence while review needs them; do not kill unrelated CC sessions.
Before later cleanup, verify the absolute target, clean/dirty state, saved evidence and
required backup. Use managed archival for managed worktrees; remove plain worktrees
only when their work is preserved and cleanup is authorized. Never recursively delete
a computed path, follow a test-venv junction into its target or delete original data.
