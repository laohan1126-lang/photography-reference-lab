# NIGHTLY HANDOFF — 2026-09-29

## Intent recorded before changes

The owner requested a reliable next-day checkpoint, not more features or open-ended polishing. Review real code, history and execution evidence; use VERIFIED / FAILED / UNVERIFIED precisely. Only small, demonstrable fixes are authorized. The original intent was committed as `c3e9bec924cbaf80e086af83ba78bae42d4914a0` before the CI change.

Product scope remains request-driven reference search with effective filtering. No random game-image modes, paid model API, new ML infrastructure, or feature expansion. No main merge, force push, deployment, user-database mutation, image deletion, or Notion write was performed.

- Repository: `laohan1126-lang/photography-reference-lab`.
- Product branch: `codex/reference-library-rebuild`.
- Audited baseline: `2b1e843be901aa193d8d0828a8366e4b88f477ae`.
- Isolated handoff branch: `codex/nightly-consolidation-2026-09-29`.
- Tested CI change: `e2e0b219337941cd7b6dab01c7e79c88649c1b74`.
- Date boundary: this file uses the requested nightly label. GitHub timestamps below remain UTC. The latest product commit is `2026-09-28T17:51:41Z`; do not reinterpret historical task dates as current execution evidence.

## Today

Reviewed the latest development batch by comparing `a930cfdfec01013ac0d52d6bd7744febb96fb29c` (last commit before 2026-09-28 00:00 UTC) to the audited baseline: 51 commits and 47 changed files. The comparison contains added/modified files, not whole-file deletions. This is the audited batch, not a claim about invisible local work.

Major changes actually present in the diff:

1. Added identity/preflight/ranking/screening/aesthetic-profile modules, candidate APIs and persistence, command-adapter transport, reference transfer/contact-board work, tests, task records, and Windows launch/stop scripts.
2. Tightened `tools/collect_adapter.py` search boundaries and preflight metadata handling, added legacy adapter-result invalidation, and expanded core CI coverage. Intent: stop unrelated game/effect/illustration results from being described as valid real-person references.
3. `d16f95c` reprioritized BrowserSkill/Edge over the command adapter and changed evaluate argument order. This retained a different production collection path from the normal pytest path.
4. `2b1e843` added global-inspiration archive/detach behavior without consuming retained project-reference slots, plus API regression coverage. Its browser-filmstrip test removed I from the existing K/I/M loop; an API regression does not replace browser interaction coverage.

The code exists, but existence is not proof that the real search-and-filter goal is complete. Earlier task reports claiming 457 scanned / 403 passed / 54 filtered / 0 uncertain and 137 passing tests are historical Agent reports, not the acceptance evidence for this snapshot. README also retains stale descriptions of some pipeline work as absent; this handoff distinguishes implementation presence from verification.

## Current State

**ACTIVE — not release-ready acceptance and not a polishing-only phase.**

Configured CI workflows run successfully. However, synthetic tests and actual user collection take different dispatcher paths, metadata-only positive modality exceptions remain, and helper retrieval can select an old or another project's preflight. The owner's current Windows workflow, real image quality, local diff, and user database remain UNVERIFIED.

The immediate bottleneck is correctness of the actual search/filter path and honesty of its evidence, not insufficient features. The existing profile/ranking/transfer/board surface is already broader than the current request; do not expand it or refactor it tonight. Do not call a test fixture a Golden Path.

## Verified

### VERIFIED — execution evidence, with exact scope

| Evidence | Observed result | What it does NOT prove |
| --- | --- | --- |
| Baseline Actions run `36461151099`, HEAD `2b1e843...` | Core Python 3.11, core Python 3.13, browser jobs completed successfully | Current local deployment, external search, visual identity accuracy |
| New Actions run `36464556152`, HEAD `e2e0b219...` | All three jobs completed successfully after adding collector UI coverage | Production BrowserSkill route parity or live acceptance |
| New core 3.11 job `109071239016`, decoded log | `140 passed, 4 warnings in 27.26s`; node syntax and compileall steps succeeded | Untested failure mechanisms below |
| New core 3.13 job `109071239387` | Test/syntax/compile steps succeeded; individual test count not independently read | A separate measured test count |
| New browser job `109071239302`, decoded log | `23 passed, 1 warning in 129.66s`; command explicitly includes `tests/test_collection_ui.py` | Real platform results, real BrowserSkill session, human visual acceptance |
| New browser evidence artifact | `synthetic-browser-evidence`, ID `10988982150`, uploaded successfully; ZIP SHA256 `7ee76facca739c37f2aabfddc3ab78e0c2f85d3d49a6c8ad0a68cda2f7ab5c1c` | Individual screenshots were not independently visually reviewed in this audit |
| Product-branch recheck before final handoff | Comparison with `2b1e843...` returned identical | The owner's uncommitted, staged, or untracked state |

Run: https://github.com/laohan1126-lang/photography-reference-lab/actions/runs/36464556152

### FAILED — actual isolated counterexamples

A separate local diagnostic run executed copies of the fetched, unchanged function bodies against synthetic pixels, in-memory SQLite, and explicit dependency stubs. It was **not** a full repository checkout, real browser run, or user-database test. The copied source is pinned to baseline blobs:

- `ref_lab/preflight.py`: `f7ee245171fb2586ce5f5f8301ed08a7fd503f25`.
- `ref_lab/collector.py`: `c6aa17767d2073e2e41d410826f2b1d557b90add`.

Command: `python -m pytest -q test_probes.py test_collector_probes.py --junitxml=combined-probe-results.xml`.

Actual result: **10 failed, 3 passed, 1 warning in 0.40s; pytest exit code 1.** Parameterized failures are not ten independent product bugs. No results were changed to make the probes green.

| Invariant under test | Actual observed output |
| --- | --- |
| Same non-person pixels must not become real-person evidence solely from COS_/LIVE_/SEL_ title prefixes | Three cases returned `real_person_cosplay` |
| Same pixels must not become real-person evidence solely from a couture-related URL substring | `irisvanherpen`, `haute-couture`, and `sensory-seas` produced `real_person_portrait` |
| Latest preflight should not depend on random UUID lexical order | Older `pf_ffffffffffff` returned instead of newer `pf_000000000000` |
| A project-scoped lookup must not inherit another project's identity record | Query for project-b returned project-a data when b had no record |
| An empty current browser attempt must not succeed solely because history contains an imported ID | With two empty mocked source results and one historical ID, `collect_via_bsk` requested `succeeded` and reported one imported candidate |
| Presence of a pytest marker must not change production dispatch with otherwise identical capability/configuration | Without marker: BrowserSkill endpoint; with marker: command-adapter endpoint |

Three passing controls: ordinary metadata did not create a positive modality; an obvious game/effect title stayed negative; an empty mocked browser attempt without historical IDs was blocked.

Local deliverable evidence contains `source_extract.py`, `collector_extract.py`, `test_probes.py`, `test_collector_probes.py`, raw stdout and JUnit XML. These are diagnostics, not product implementations. Next Agent should port the assertions to imports from the actual repository before using them as regression acceptance.

## Open Issues

**P1 — production/test collection split.** `ref_lab/collector.py::run_browser_collection_job` checks `PYTEST_CURRENT_TEST` and dispatches straight to `agent_collection.run_collection_attempt`. Without that marker, available BrowserSkill is preferred. The retained `collect_via_bsk` path hardcodes Xiaohongshu/Pinterest, ingests observed DOM images, and does not itself invoke the strict `tools/collect_adapter.py` filtering path. Thus green adapter/UI tests do not verify the route the owner normally uses. Downstream full-service effects still need integration validation. Preserve the user's BrowserSkill/Edge preference; do not solve this by silently replacing it with a different source or disabling it.

**P1 — attempt outcome uses historical totals.** The isolated collection probe reproduced a success request with zero new candidates and non-empty old `imported_ids`. It exercised the real extracted branching, but transition/storage dependencies were stubbed; final HTTP/database effects are not claimed as reproduced. Acceptance must distinguish this attempt from history, as well as empty results, duplicate-only retries, navigation errors, timeouts, cancellation, and partial completion. Several subprocess calls and broad exception handlers also warrant focused validation, not a crawler rewrite.

**P1 — remaining fake-positive modality evidence.** `detect_modality` still trusts arbitrary title prefixes and URL substrings as though optical/person evidence. Ordinary metadata now stays unknown, so these exceptions are inconsistent with the strict-search boundary. Fix the evidence semantics without adding a new visual-model service. Unknown is not rejection or deletion, and no human choices may be overwritten.

**P2 — preflight lookup helper.** `get_preflight` sorts UUID-derived IDs and falls back across projects. Function-level failures are reproduced; user-visible call-site impact was not established tonight. Trace callers before claiming UI corruption or designing a migration.

**UNVERIFIED — live/local acceptance.** Direct clone failed with `Could not resolve host: github.com`; local-workspace connector read also failed. No access to the owner's working tree, local server, active LAB_DATA_DIR, original private images, or authorized live browser session was established. No clean-worktree, deployment-success, current photo-hit-rate, or current real-DB count is claimed. The I archive action still needs a browser check covering continued selection, global-library presence, project-slot counts, refresh persistence, and restore behavior.

**Residual debt, not tonight's new feature work.** Multiple overlapping collection paths, scenario-specific visual heuristics, historic confidence reports, and documentation drift now create a misleading confidence gap. Non-failing dependency deprecation warnings were observed; they are not a reason for an unrelated upgrade/refactor tonight.

## Changes Made Tonight

- Created an isolated review branch and recorded intent before changes.
- Changed exactly one CI command to include the already-existing `tests/test_collection_ui.py` suite. Commit: `e2e0b219337941cd7b6dab01c7e79c88649c1b74`.
- Reran through the push-triggered GitHub Actions workflow and read real run/job results plus core 3.11/browser decoded logs. All configured jobs passed; the newly included browser suite ran.
- Finalized this handoff and produced independent local failure-reproduction evidence.
- **No product runtime code changes made.** No merge into the product branch or main, no deployment, no user-data changes. The failed correctness probes remain open; the CI-coverage fix must not be described as fixing them.

Reason for limiting changes: collection routing and visual evidence are coupled to multiple entry points and the unavailable live environment. A narrow verified coverage fix is safer than claiming an unvalidated rewrite fixes search quality. The final documentation-only commit does not change the runtime/workflow content validated at `e2e0b219...`; do not misattribute that run to a different SHA.

## Tomorrow

### 1. Make the real BrowserSkill path testable and truthful — Strong Agent

Why: this is the owner's actual entry point, while the green tests currently take a different route. Resolve the highest-value correctness gap before touching UI styling.

Expected result: preserve BrowserSkill/Edge, exercise the same dispatcher in production and tests through mocked dependencies rather than production `PYTEST_CURRENT_TEST` behavior, ensure equivalent request filtering across active entry points, and use per-attempt evidence for outcome reporting.

Done when: repository-import regression tests cover both capability branches; obvious wrong-character/game/effect/product fixtures cannot pass the active path as valid target references; a zero-result/duplicate-only retry cannot fabricate new success from historical totals; failures stay visible; core/browser tests pass. Real external effectiveness still requires task 3.

### 2. Remove unsupported preflight certainty and repair lookup isolation — Strong Agent for semantics; ordinary Agent for bounded SQL regression

Why: trustworthy filtering is impossible if titles masquerade as vision or another project's context is reused.

Expected result: metadata-only positive exceptions remain unknown/uncertain unless independent trustworthy evidence exists; lookup respects project scope and an actual time/order definition. Trace helper callers first and do not invent a broad schema migration.

Done when: ported counterexamples fail on baseline and pass after changes; existing negative-category filtering, recoverability, human K/I/M/X decisions, global inspiration records, and cross-project shared assets remain intact. No blanket rescanning/overwriting of the owner's database without a protected, explicit plan.

### 3. One local real-use acceptance run, not another feature loop — ordinary local Agent + human image judgment

Why: only this can decide whether the current narrow product is useful. Automated totals do not measure photo relevance.

Expected result: first inspect local branch/diff, confirm deployed SHA and active data directory, preserve all local work and use a backed-up isolated copy where appropriate. Then run the existing strict-search case, e.g. 王昭君／长夜焕生／真人 COS 正片, through the owner's actual BrowserSkill session. Open the actual image files rather than trusting titles; measure target matches, wrong roles, non-person results, duplicates, unknowns, and recoverable filtered items. Check I-to-global-inspiration and refresh/restore once in the same user flow.

Done when: evidence ties task input, actual execution route, source images, candidate decisions and visible outcome to a specific SHA; unsupported items are not claimed as confirmed; the owner accepts whether the references meet the request. A login/capability block is recorded as blocked, not silently bypassed. Only after this acceptance should the workflow be recorded as a Golden Path.

## Start Here

Work on `laohan1126-lang/photography-reference-lab`, product branch `codex/reference-library-rebuild`; audit baseline `2b1e843...`. Nightly CI+handoff are on `codex/nightly-consolidation-2026-09-29`, not yet merged. Fetch and check status/diff before touching the owner's working tree; preserve unknown local changes. Read AGENTS.md, README.md, this handoff, `docs/tasks/2026-09-29-strict-search-filter.md`, and acquisition-specific rules before collector edits.

Start with `ref_lab/collector.py::run_browser_collection_job` and `collect_via_bsk`, then `ref_lab/preflight.py::detect_modality` and `get_preflight`. Fresh CI at `e2e0b219...` is green (core 3.11 140 passed; browser 23 passed), but isolated counterexamples are red (10 failed, 3 passed). Do not infer live correctness from green CI or the historical 403/457 report. Preserve the narrow search/filter scope and BrowserSkill preference. Tomorrow's first deliverable is a repository-level reproduction of the actual route mismatch, not another feature.

## Project Status

**ACTIVE**.

Not MATURE: the actual search/filter trust boundary still has reproducible defects, and real-use acceptance is absent. Not globally BLOCKED: remote CI, review and development are usable; only local/live acceptance is inaccessible from this session. The goal is to converge after the three actions above, not to expand the roadmap.

Not worth further polishing now: aesthetic-profile features, ranking weights, new source quotas, extra character presets, random game-image modes, contact-board ornament, broad refactors, and non-failing warning cleanup.

Use another Pro long task only for a reproduced core-path failure, a real data-integrity/recovery risk, conflicting state across entry points, or an explicitly approved product change. After a real accepted Golden Path and stable ordinary use, routine small fixes and checks belong to an ordinary Agent; no nightly Pro rewrite is required merely because another day passed.
