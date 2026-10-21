# BrowserSkill recovery independent audit — engineering complete, live acceptance blocked

## Intent and boundary
User requests independent acceptance of AGY 2385adf, safe correctness fixes, measured optimization, and an executable next Goal loop. Actual delivery means usable photos, not test counts. No main merge, daily deployment, model calls, user-data writes or changed photo admission in this audit.

## Pre-edit evidence and design
Base 2385adf; daily checkout/runtime record 77216b4; main 172b296. Isolated worktree under canonical .local/worktrees.
Python collector → BrowserSkill CLI → Edge; existing queue/API and JS UI. Fix shared transport/error boundaries, not a new scheduler.
Touch browser_recovery, collect_verified, detail adapters, queue, narrow UI diagnostics and regressions. Preserve AGY historical report; append corrections.
Confirmed: missing subprocess import; detail ValueError consumes typed infrastructure errors; Cookie replacement retains value; 403/challenge classified as infrastructure. R1–R6 replace Browser.recover; R7 does not test API/UI.
Normal-permission BSK status reports connected Edge 9d3f232a. Sandbox IPC denial is not extension disconnect.
Acceptance: before/after targeted reproductions, adjacent regression, real owned-session recovery/local app read, truthful unverified 30-photo workflow.

## Checkpoint
Publisher baseline captured before tracked edits. Git-only task-branch delivery. No production data touched.

## Independent findings and changes

A. Functional acceptance: PARTIAL. AGY 2385adf is not ready for reliable collection. Its seven scenarios pass, but they replace Browser.start/recover with handwritten fakes; R7 only tests sanitizer/classifier, not API/DOM. The original failure's artifact has 8 queries, zero observed pages, zero downloads, 32 navigate errors plus one session error. Collector elapsed is 252.438s; do not substitute this for the reported ~342s whole task.

Confirmed defects:
1. browser_recovery.is_infrastructure_error referenced subprocess without importing it. Ordinary ValueError/PlatformRestrictionError raised NameError.
2. collect's detail except ValueError consumed BrowserInfrastructureError; Pinterest detail adapter independently swallowed transport errors. Corrected reproduction on AGY base: 3 detail reads, 0 recoveries, search_plan_exhausted, all8 done.
3. recover rediscovered a different browser/profile, and checked 60s only before entering potentially long nested probes. Seven original tests did not execute this method.
4. Cookie string replacement retained its own secret capture, Authorization Bearer and short/quoted values survived. CLI challenge/403/429 defaulted to infrastructure.
5. A query already observed could become done after a later infrastructure failure. Startup infrastructure failure escaped as internal_error. Recovery progress/browser failures were absent from actual API/DOM.
6. Live reproduction found lost session-start replies: 12s timeout but daemon created a session whose ID the collector never received. Session creation success alone is not operational readiness.

Fix shared boundaries:
- One Browser.command attempt; typed error and sanitized evidence. Controller owns recovery. Download HTTP timeouts remain item failures.
- Detail adapters accept the existing command callback; standalone historical callers keep their prior default behavior. Typed transport errors cross inner detail handlers; interrupted page does not spend item retry allowance.
- Recovery pins the original instance, clamps every call to one monotonic recovery/job deadline, verifies actual snapshot after creating session, leaves failed queries pending, distinguishes incomplete reads from genuine exhaustion.
- BrowserSkill native recoverable start protocol: prepare -> start(request-id) -> claim; uncertain creation is cancelled by exact request ID. Pending identity is persisted in browser-session.json. Cleanup has its own bounded10s even if acquisition deadline expired; cancellation must return closed without cleanup_error before claiming closed.
- Sanitized diagnostics flow into progress/search-summary and queue API. UI exposes recovery and last recorded error, preserving historical failures.
- No model, query ranking, photo admission, asset schema or human choice change.

## Current real environment and limitations

Normal local permissions: daemon0.3.2/PID37848, Edge instance9d3f232a, extension0.3.3, protocol1.3, reported connected/responsive. Sandbox named-pipe denial was separately identified.
Owned session ycrv created; debug start timed out; local-app navigation RPC timed out32s and observe timed out30s. No platform search was started.
New recovery attempted once:19.812s, false. Old owned session stopped; new start timed out12s and created ywdc; independently identified and stopped ywdc.
New request-ID cancellation tested: initial experiment omitted required prepare and was rejected invalid_params (not a successful lost-reply test). After prepare, start timed out and cancellation returned; an immediate status still showed a pending placeholder. Subsequent exact request read returned state=closed/cleanup_error=null/session=null and session list[].
All identified audit sessions were cleaned. Still UNVERIFIED: actual successful BrowserSkill recovery, actual platform search/download/import,30-photo delivery, daily restart with new code, strict identity/costume/aesthetics.
Do not infer extension disconnection from RPC timeouts, nor blame version skew without a separate controlled compatibility test.

B. Engineering: scoped defects above repaired; actual BrowserSkill execution remains a delivery blocker. Daily port18765 independently owned by PID52148; code_revision/checkout77216b4, main172b296. AGY2385adf and this fix are task branches. No merge/deployment/data writes.
AGY local receipt reports Notion SUCCESS although its immutable contract says delivery.notion=false. This is a scope/record inconsistency; remote Notion content was not read or changed in this audit.

C. Measurement: actual invalid-owned-session CLI ABBA comparison, source paths explicitly bound:
before2.281/2.453s,2 subprocess calls each; after0.500/1.328s,1call each. This proves removal of redundant dead-session dispatch, not overall acquisition speed or token savings. Original benchmark mistakenly imported old module for both legs and is retained as invalid evidence. Zero model calls added.

## Verification checkpoints and failures retained

- Initial suite failed setup because new basetemp parent did not exist; corrected environment, not product.
- AGY baseline27 cases:26passed/1failed Windows MAX_PATH in test temp archive path. Re-run with shorter repository-local temp path passes.
- First12 new checks all failed on base. Detail fixture initially lacked query URL; corrected fixture re-run on base proves actual swallowed-disconnect failure as described above.
- After shared fixes:73passed (targeted9files).
- API/Goal/stages34cases:33passed, one new fixture used invalid collection_mode=search_only (422); corrected to documented search, then18 boundary cases cover API.
- Broad UI suite stalled; only verified owned pytest processes stopped. Focused real Chromium/TestClient-bridge candidate UI passed; it is not a platform E2E test.
- One test initially called openCandidateQueue with autoStart default; corrected autoStart:false so UI verification cannot launch acquisition.
- Subsequent final results and exact commands appended below; no full-repository all-green claim.

## Final regression and delivery boundary

Commands ran from the isolated audit worktree, using the canonical Windows venv:
~~~powershell
$py = 'D:/AI PROJECTS/photography-reference-lab/.venv/Scripts/python.exe'
& $py -X utf8 -m pytest -q -p no:cacheprovider --basetemp='D:/AI PROJECTS/photography-reference-lab/.local/ba6' tests/test_browser_recovery_boundary.py tests/test_browserskill_recovery.py tests/test_collection_audit.py tests/test_search_detail_timing.py tests/test_search_continue_recovery.py tests/test_collection_controller_recovery.py tests/test_collection_stages.py tests/test_search_relevance_regression.py tests/test_search_quality_loop.py tests/test_exact_recall.py tests/test_goal_independent_audit.py --tb=short
# 97 passed, 257.56s.
& $py -X utf8 -m pytest -q -p no:cacheprovider --basetemp='D:/AI PROJECTS/photography-reference-lab/.local/test-ba7' tests/test_browser_recovery_boundary.py tests/test_collection_ui.py::test_browser_recovery_details_are_visible_without_claiming_completion --tb=short
# 19 passed, 80.48s; includes subsequent JSON Cookie/empty-progress handling and current UI.
& $py -X utf8 -m pytest -q -p no:cacheprovider --basetemp='D:/AI PROJECTS/photography-reference-lab/.local/test-ba8' tests/test_browser_recovery_boundary.py tests/test_browserskill_recovery.py --tb=short
# 26 passed, 86.99s; after final cancelling-state guard.
node --check web/app.js
git diff --check
~~~
These sets overlap; do not sum them as distinct cases. Changed Python files also pass py_compile. No dependencies installed.

Temporary test dirs ba1–ba6 were created only by this audit and are now test-ba1–test-ba6 to guarantee exclusion by the existing history scanner. Before moving, exact workspace paths and absence of links were checked. All1749 files copied into .local/backups/browser-audit-tests-20261021 and then moved; destination and backup SHA verified individually. Manifest retained, no deletion. For reruns use --basetemp=.local/test-ba9 (a new directory). No user assets were moved.

Private evidence: canonical .local/test-browser-audit-20261021, including red.txt, corrected-red-detail/, baseline.txt, regression1.txt, final-regressions.txt, final-boundary-ui.txt, cleanup-regression.txt, command-benchmark-corrected.json, live-recovery/, live-prepared-cancel/. Superseded/failed experiments retained.

D. Actual scope: browser recovery/classification, command propagation through two existing detail readers, queue/JS diagnostics, three focused test files, task records and next Goal loop. No main merge, daily restart, user-library writes, photograph changes or AI calls. No database migration; reverting this scoped task commit on its task branch is sufficient for code rollback. Existing AGY2385adf remains intact.

E. Delivery: BLOCKED for reliable30-photo product acceptance; engineering audit/fixes are ready as a task-branch checkpoint. The remaining blocker is reproducible live BrowserSkill RPC/session execution, not evidence of insufficient cosplay content. Publishing a fix does not complete the30-photo Goal. Git result is recorded by this audit's canonical Publisher receipt; delivery.notion=false.

Next executable handoff: [AGY Goal loop](2026-10-21-browserskill-next-goal-loop.md). Preserve failure history and real outcome boundaries.
