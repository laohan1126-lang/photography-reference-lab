# Nightly Project Consolidation — 2026-09-29

## Intent recorded before editing
The owner asks for evidence-first consolidation, not more features: inspect current code/history/tests, distinguish VERIFIED / FAILED / UNVERIFIED, make only narrow justified repairs, and leave 1–3 high-value next actions. Preserve user data and local uncommitted work. No main merge, deployment, paid API, new product scope, or broad refactor.

Target: `laohan1126-lang/photography-reference-lab`, `codex/reference-library-rebuild`.
Audit snapshot: `2b1e843be901aa193d8d0828a8366e4b88f477ae`.
Window: `a930cfdfec01013ac0d52d6bd7744febb96fb29c` (last commit before 2026-09-28 UTC) through snapshot; GitHub comparison reports 51 commits. Snapshot authored 2026-09-28 17:51:41 UTC / 2026-09-29 01:51:41 UTC+08. File dates are not UTC timestamps.

## Observable acceptance criteria
1. One-click collection must not bypass the configured command/receipt ownership by opportunistically detecting BrowserSkill. No adapter means visibly blocked, with task-package recovery.
2. `PYTEST_CURRENT_TEST` must not change production dispatch.
3. Cover BrowserSkill present/absent, pytest marker present/absent, and configured/missing adapter. Existing transport tests cover actual subprocess/import behavior.
4. CI must include existing collection-status browser regressions.
5. Preserve manual BrowserSkill + Agent task packages and historical explicit helpers; do not invent a provider or claim live visual acceptance.
6. Verify changed code, record exact scope, and refresh target HEAD before integration. No force push.

## Findings and bounded changes
**FAILED at snapshot, reproduced:** the exact dispatcher extracted from the fetched source selected the unfiltered BrowserSkill helper when `PYTEST_CURRENT_TEST` was absent, even with `LAB_COLLECTION_COMMAND` configured. With the pytest marker present it selected the adapter. A four-case isolated routing probe produced 2 passed / 2 failed. The complete source copy was checked against Git blob `c6aa17767d2073e2e41d410826f2b1d557b90add` before modification.

The default dispatcher now always delegates to `run_collection_attempt`; the transport remains responsible for configuration, attempt ownership, validated result imports and truthful blocked states. BrowserSkill remains available through a configured adapter or explicit Agent task-package workflow. This removes an undocumented automatic DOM-scraper bypass; it does not remove BrowserSkill support or rewrite old helper functions. The same source-extracted routing probe then produced 4 passed / 0 failed; changed Python files compiled. These probes prove routing only, not application/browser/visual quality.

Added 8 dispatch regression cases using actual application fixtures, and included both those cases and `tests/test_collection_ui.py` in CI. Full new CI results will be appended after inspection; not yet claimed passed here.

## Existing runtime evidence
Snapshot has successful GitHub Actions runs, including PR run `36461151099`. Its workflow omitted `tests/test_collection_ui.py`, and production dispatch bypassed the tested path. Therefore green CI did not prove live acquisition correctness.

## Environment boundary
GitHub connector can read/write repository metadata and text. The isolated container could not resolve github.com, so clone failed; this is not an application test failure. No access to the owner's Windows worktree, live service, database, BrowserSkill session, or uncommitted changes. No private data changed. Source-extracted probes are not full-suite runs. Live specific-skin cosplay hit rate, local upgrade/restart and UI acceptance remain UNVERIFIED.

## Other audit leads — do not silently expand tonight's scope
- README/architecture retain obsolete statements that screening sessions, quality/ranking and versioned profiles are not implemented. Source modules and API handlers now exist; implementation existence is not product acceptance.
- `makeTransferable()` says downgrade moves into the inspiration library, but `make_transferable_candidate()` only updates project-reference flags/lane. Unlike `archive_reference_to_inspiration()`, it does not save a global inspiration or detach project use. This is a concrete code/UI discrepancy, not yet application-runtime reproduced in this checkpoint.
- Historical `collect_via_bsk()` still uses cumulative imported IDs for success and catches individual import errors. It is no longer the automatic entry point; do not re-enable it without current-attempt/filter/cancellation tests.
- The latest I/archive action has an API test, but I was removed from the existing filmstrip shortcut loop. Do not interpret K/M/X coverage as coverage of the new I UI path.

## Next verification
Inspect new Actions job steps/logs for exact code SHA, core Python matrix and browser suite; append outcomes. Then perform only the owner's real constrained search and verify the two inspiration entry points locally. Do not expand taste learning, add providers, tune UI cosmetics or declare the project mature merely to fill a nightly plan.
