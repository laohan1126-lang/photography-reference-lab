# 2026-09-28 Collection runner safety checkpoint

## Intent and boundaries recorded BEFORE implementation

Continue the user's candidate-pipeline loop on `codex/reference-library-rebuild` without overwriting the existing task record. Starting product HEAD: `a930cfdfec01013ac0d52d6bd7744febb96fb29c`, whose parent is `18b2f308ecdbcb9da6608279bf13c65a80e29235`.

The full requested product remains SEARCH -> IDENTITY PREFLIGHT -> QUALITY PREFLIGHT -> RANKING -> HUMAN K/I/M/X -> SESSION SUMMARY -> VERSIONED AESTHETIC PROFILE. This is an **incomplete safety checkpoint, not that product's completion**.

## Observed environment and baseline

- Obtained existing baseline/current Git bundles from GitHub Actions artifacts 10938806106 and 10939027020. Verified their embedded SHA-256 manifests, bundle prerequisites, exact HEAD/ancestry and `git fsck`. No owner checkout or private database is mounted here. The isolated checkout was clean before this record.
- `git fetch origin`: exit 128, `Could not resolve host: github.com`. Offline bundle fetch succeeded; network fetch did not.
- The current GitHub connector exposes read operations, not commit/push. Plugin discovery found no available connected writer. **Publishing this turn is BLOCKED**; the historical task's description of a writable API does not describe this turn's tools.
- Unchanged-code backend baseline: `python -m pytest -q tests/test_library.py tests/test_imports_jobs.py tests/test_workers.py tests/test_operations.py tests/test_personal_library.py`: **84 passed in 8.58s**.
- Unchanged `tests/test_ui_components.py` timed out at the execution boundary twice (20s and 120s). Output reached six/eight dots respectively, not a complete result. No completed browser baseline is claimed. Preserve these failures/timeouts separately from new regressions.

## Root causes and narrowly scoped work

1. The new one-click runner hard-codes a Windows username, Edge extension and XHS->Pinterest order, infers intent from `cos`, swallows errors and silently falls back to headless Pinterest. Replace this automatic scraper with a **source-independent, explicitly configured local Agent task-package adapter**. Without a configured adapter, remain blocked and retain manual export/import. Do not guess installed vendor CLI syntax, auto-install anything or invoke a paid API.
2. One-click and legacy collection success uses cumulative imported IDs. An empty retry can claim success using old assets. Require current package/capture evidence while preserving idempotent valid reimports and earlier assets.
3. UI treats any HTTP 200 as completion, including a blocked worker. Show the returned status and retain recovery controls instead.
4. Add bounded subprocess lifecycle, attempt audit events, strict result validation and regression tests. Do not log command arguments, model output or credentials.

## Explicitly NOT implemented in this checkpoint

Independent identity/quality preflight, ranking, near-duplicate grouping, screening sessions, aesthetic profile learning/versions/rollback and their UI/migrations are still outstanding. A completed candidate import is not evidence of identity, quality, taste, or field-card acceptance. Existing analysis-provider portability issues are outside this collector-only checkpoint. No Golden Path, Notion write, main merge, public deployment or destructive user-data operation.

## Validation criteria

UNIT/INTEGRATION: absent/malformed configuration, missing executable/output, invalid ZIP, nonzero exit, timeout/cancellation, current-package receipts, repeat imports, preserved partial assets and safe event records. Run actual synthetic child processes; mock platform results never count as live search.

BROWSER/COMPONENT: exercise the real UI with the existing explicit TestClient bridge, verify HTTP-200 blocked/failed does not show success. Existing full browser regressions must be attempted and failures reported, not skipped to green.

LIVE EXTERNAL: Arima Kana and Kamen Rider Durendal **UNVERIFIED**, execution **BLOCKED** without an authorized local Agent/BrowserSkill/browser login and the user's private Durendal context. Windows/WSL cross-runtime behavior is also unverified here.

Append actual implementation, commands, results and remaining blockers below.


## Outcome appended after implementation and validation

**Status: OFFLINE CHECKPOINT / NOT RELEASED. Full candidate-pipeline exit conditions NOT MET.** Publishing remains blocked, remote last re-read still a930cfdfec01013ac0d52d6bd7744febb96fb29c. No push, main merge, public deployment, Notion write or Golden Path creation occurred.

### Actual changes

- Removed the new hard-coded BSK/Edge fixed-source scraper and silent headless fallback from the default one-click collection entry. Kept the explicitly opt-in legacy visible capture, correcting its per-run counts.
- Added `agent_collection.py`: explicitly configured argv adapter, private complete task package, no inferred CLI flags, bounded native process execution, cancellation/attempt ownership, strict result/job validation and safe attempt evidence. No real vendor adapter was installed or exercised.
- Current-package receipt IDs, not historical cumulative imported_ids, determine automatic package completion. Empty retry stays blocked; valid repeated packages remain idempotent; partial blocked results preserve candidates. A known-stale attempt is rejected before asset ingestion; writer transactions also recheck ownership.
- UI checks returned job.status, keeps blocked/failed recovery controls, never interprets HTTP 200 alone as completion, and does not close/overwrite another dialog on a late response.
- Added 25 UNIT/INTEGRATION tests and 5 Chromium component tests. Updated README, ARCHITECTURE, WORKER_PROTOCOL, CODEX_REGRESSION and AGENTS boundaries. No existing tests were removed, loosened or skipped.

### Database and preservation

No new schema migration: user_version remains 2. Only optional current job metadata and append-only existing events were added. Original assets, hashes, choices, inspirations, reviews, cards, sources and notes were not intentionally changed. The owner’s normal database was never mounted or used. The isolated existing legacy/schema1 upgrade/idempotence regression passed; this does not constitute an upgrade test on the owner’s private database.

### Actual verification

Environment: Linux x86_64, Python 3.13.5, pytest 9.0.2, installed Chromium. All tests used isolated data; synthetic process/image fixtures are explicitly labelled.

| Command / scope | Actual result |
| --- | --- |
| Unchanged-code backend baseline: `python -m pytest -q tests/test_library.py tests/test_imports_jobs.py tests/test_workers.py tests/test_operations.py tests/test_personal_library.py` | 84 passed, 8.58s |
| First unchanged component attempts | Tool execution boundary timeouts; only incomplete logs, not passes |
| `python -m pytest -q tests/test_collection_runner.py tests/test_collection_ui.py` | 30 passed, 16.51s |
| Final `python -m pytest -q tests --junitxml=.../full-regression.xml` | **125 passed / 6 failed / 0 skipped / 0 errors**, 104.32s; NOT green |
| Final full suite: backend excluding historical migration | 109 passed |
| Final full suite: Chromium component + explicit TestClient bridge | 15 passed, NOT HTTP E2E |
| Final full suite: isolated legacy migration/schema1 upgrade/idempotence | 1 passed |
| Final full suite: real HTTP/Chromium workflows | 6 failed at `page.goto`: `net::ERR_BLOCKED_BY_ADMINISTRATOR` for localhost; environment BLOCKED |
| Pristine starting a930cfd worktree: `python -m pytest -q tests/test_browser.py::test_browser_select_persist_filter_and_mobile` | Same administrator navigation block; 1 failed, 1.52s |
| `node --check web/app.js` | exit 0 |
| `python -m compileall -q ref_lab tools tests` | exit 0 |
| `git diff --check` | exit 0 |

The outer tool returned before long test processes completed; final results above come from completed pytest logs AND parsed JUnit XML, not from an assumed successful tool return. Six real HTTP tests remain failed in the XML; no administrator policy was changed, and no bridge/mock was substituted into those tests. Two dependency deprecation warnings were also reported.

### Evidence and residual work

The offline handoff archive includes the incremental Git bundle/patch, this task record, actual logs/JUnit, verification-summary.json and a synthetic Chromium screenshot of the blocked UI. No owner database, credentials or reference-image originals are included in that handoff. Local commit SHA and artifact hashes are written in the external handoff manifest, avoiding a self-referential commit hash in this file.

Arima Kana and Kamen Rider Durendal are both **UNVERIFIED**; live execution is blocked by unavailable authorized local Agent/BrowserSkill/login/private project context. No actual candidate images for these cases were inspected. Native Windows process-tree handling (particularly descendants after an early parent exit) remains unverified/incomplete; service hard-crash recovery remains unimplemented. Do not claim all-platform lifecycle reliability. The old explicit job-status endpoint still permits manual compatibility transitions; it is not automatic acquisition evidence. Existing analysis-provider fixed paths/CLI assumptions remain outside this collector checkpoint.

Most importantly: identity context/preflight, quality preflight, ranking/exploration, screening sessions and versioned aesthetic learning/profile UI are **NOT IMPLEMENTED** here. These are continuing tasks from the original loop, not delivered features or mere deployment toggles.

### Local continuation, not deployment approval

Keep the live LAB_DATA_DIR and working tree untouched; fetch/check remote and back up first. Import the bundled commit into an independent worktree for review, not a destructive folder replacement. Wire an actual installed Agent adapter from its real skill/docs (or keep manual task packages), complete the missing product features, address Windows/crash lifecycle, rerun the failed HTTP suite in an authorized environment, then perform the two actual visual cases. Only after evidence review should the local agent integrate/push the authorized product branch. No force push and no main merge.
