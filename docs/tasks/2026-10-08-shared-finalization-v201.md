# Shared Windows task finalization v2.0.1

## Owner intent and boundary

The owner requested one shared Task Finalization core for Windows Codex, Claude Code and AntiGravity. The existing standing authorization permits a scoped commit and a normal push to the current safe GitHub work branch.

This record is created before the v2.0.1 generated entrypoint update. The earlier v2.0.0 migration had already changed the entrypoint without a versioned intent document; this file does not claim to have existed before that earlier change. The original immutable migration task baseline is retained.

Only tools/finish_task.py and this task record belong to the project upgrade. The entrypoint delegates to the canonical shared CLI, remains import-safe, and preserves path-safety checks. Product behavior, user data and other agents' changes remain outside the publication scope.

## Observable acceptance

- Import and the configured repository-local test suite pass; node --check web/app.js and git diff --check pass.
- The core's isolated recovery checks and UTF-8 transport checks pass; installed generated files match recorded hashes.
- The publisher stages only the declared two paths and verifies the pushed remote SHA. A missing required local interpreter prevents publication rather than borrowing another checkout's runtime.
- Notion failures retain a separate pending record for AI Playbook. No alternate database is selected.

## Anti-patch review before this upgrade

PATCH-LOOP DETECTED
Root cause: separate attempts and inconsistent transport allowed failed publication to lose its recovery path.
Keep: immutable task baselines, scoped manifests and independent Git/Notion receipts.
Delete: duplicated finish/retry decisions and implicit encoding assumptions.
Redesign: one attempt protocol, saved destination proofs and explicit UTF-8 read-back.

## Verification and outcome

Results are intentionally not predeclared here. Exact commands, failures, deferred work and publication evidence are stored in the shared task receipt and the migration report. This entrypoint acceptance does not establish AntiGravity GUI dispatch or Notion service permissions.
