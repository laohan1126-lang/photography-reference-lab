# Photography learning loop V2 · 2026-10-09

## Original intent and boundaries

The owner asks for expert observation and transfer, not a longer directory or merely a reading drawer. Preserve the 14-domain / 71-module / 247-skill tree, 205 source records, 46 companions, private records and evidence limits. Research first; compare candidate conceptual gateways; implement exactly three complete, individually authored learning paths; independently review photography, pedagogy and interaction; correct root causes and reverify. No source-photo/database migration, owner ability claims, bulk course generation, main merge or unrelated cleanup.

## Baseline and isolation

Local and remote `codex/evidence-photography-atlas` both resolve to `5335eda2e15e5e57eb7cbfdf9e5aed123d9fb686`. Implementation workspace: `.local/atlas-v2`, branch `codex/photography-learning-loop-v2`, created from that commit. Root `web/app.js` and existing untracked files belong to other work and must remain untouched. No graph tools are available; code discovery uses direct reads and rg.

The injected publication identity is host `codex`, session `01a111c0-c935-7770-a2ee-f4ce03ce4d9a`, task `01a11c4f-3f5c-72e1-a708-c095c840a8a9`, root cwd. The immutable root baseline is preserved. Once isolated implementation is verified, integrate only explicit task files whose root content still matches that baseline, then seal/finish at the mandated root. Concurrent changes block only the conflicting scope, never justify overwriting it.

## Blueprint before implementation

- Stack: existing FastAPI, plain JavaScript/CSS, revisioned private JSON learning store and pytest/Playwright. No new dependencies.
- Retain: map hierarchy, palette/type/spacing tokens, sources and companions, private photo paths, optimistic revisions, captured dialog ownership and same-origin navigation.
- Add: independent gateway catalogue with source/claim/case provenance, complete original teaching, three distinct observation activities, unseen transfer cases; an accessible wide reading dialog; explicit cognitive self-assessment separate from legacy skill status.
- Touch: learning frontend, atlas builder and validation, narrow private-state extension, tests, architecture/task/research records and packaging if needed.
- Avoid: reference app, SQLite schemas, collectors, original images, existing source truth markings, runtime configuration and publisher core.
- Risks: copyright/media access, confusing project analysis with source claims, teaching not transferring to real users, stale writes/dialog focus, private drafts and old-record compatibility.
- Acceptance: actual old-flow diagnosis; primary-source research; three complete browser paths, chapter navigation/close/reopen/scroll/focus/mobile; preserved old skill navigation and state; source integrity; independent reviews with exact findings/corrections; current tests and inspected screenshots. Engineering verification is separate from owner aesthetic and learning outcomes.

## Prior receipt review

Reviewed `migration-photography-reference-lab-717d3fd6` (publisher recovery, successful Git/Notion, no product teaching changes) and `01a1177f-9150-7452-a63e-25961de913b3` (canonical deferred after changed HEAD; separately authorized atlas push verified). The former is unrelated publisher work; the latter's route/modal ownership and explicit source-conflict mapping remain valid.

PATCH-LOOP DETECTED (semantic review before implementation): the recurring goal is usable learning, while the first research index and later companion links still do not model learning itself. Root cause: a source-directory model cannot represent an observation attempt, explanatory variables, controlled contrasts, counterexamples and unseen transfer. Keep the research index, source truth markings, private state and previous navigation corrections. Delete the assumption that additional summaries/links constitute complete teaching. Redesign around a separate many-skills-to-one-gateway teaching responsibility rather than growing every skill's summary. No publisher or old navigation patch layer is planned.

## Outcomes

Implementation and independent review are complete. Publication is recorded separately by the canonical task receipt; this document does not predict its outcome.

### Research and review outcomes

The three individually authored gateways link 17 existing skills, retain all original research assets, and add 17 scoped teaching-source records plus 10 reviewed cases. Research memos, actual baseline diagnosis and photography/pedagogy/interaction reviews are versioned under `docs/research/photography-atlas/v2/`. The full A–E response and user path are in `V2_ACCEPTANCE.md`.

Independent reviews found and corrected (1) remote transfer photos blocked by the original self-only image CSP, (2) an overbroad attention-plus-occlusion teaching promise, (3) an observation prompt asking about eyes hidden by sunglasses, and (4) a gateway conflict refresh making a stale underlying skill form able to overwrite newer notes. Before review, the parent also rejected mismatched night-scene and marsh-photo descriptions and reread actual pixels. Retractions remain in the research record; the final course does not repeat them.

An additional semantic review was emitted before the form fix: global revision freshness cannot stand in for what a form actually loaded. Keep shared revisions and drafts; remove implicit authorisation of old inputs; bind forms to loaded field snapshots and require explicit reconciliation when those fields changed. This extends the same ownership principle as the prior `01a1177f-9150-7452-a63e-25961de913b3` route/dialog work, without changing publication safeguards.

### Actual verification

All Python commands used the existing root `.venv/Scripts/python.exe -X utf8` with the isolated V2 checkout as cwd and separate `.local` pytest base directories. Native local-network permission was needed for TestClient/Uvicorn/Chromium; no dependency installation or private-library write was used.

- New catalogue/state/three-path reader suite: initially 14 passed; later additions verify authentication/CSRF, delayed save ownership, actual CSP image rendering and cross-form stale writes.
- `python -m pytest -q tests/test_library.py tests/test_imports_jobs.py tests/test_workers.py tests/test_operations.py tests/test_personal_library.py tests/test_collection_runner.py tests/test_learning_state.py tests/test_learning_ui.py tests/test_atlas_provenance.py tests/test_ui_components.py --basetemp=.local/v2-legacy-regression`: **175 passed**, 415.66s.
- Final `python -m pytest -q tests/test_learning_gateways.py tests/test_learning_gateways_state.py tests/test_learning_gateways_ui.py tests/test_learning_state.py tests/test_learning_ui.py tests/test_atlas_provenance.py --basetemp=.local/v2-final-learning --junitxml=.local/v2-final-learning.xml`: **57 passed**, 165.00s. These counts overlap with the preceding run and are not summed.
- Initial feature tests genuinely failed against the old bundle/absent validator. An initial temporary-directory fixture error was corrected, not treated as a product defect. The CSP reproduction first exposed a test expression disallowed by `unsafe-eval`; using an arrow-function predicate then reproduced the real image timeout. The stale-form regression failed with “备注已保存” before the fix, then passed with drafts/newer server notes preserved. No test threshold was weakened.
- `tools/build_photography_atlas.py --check`, three new catalogue tests, `node --check web/learning.js`, `node --check web/learning-gateways.js`, `node --check web/app.js`, and `git diff --check`: passed. An early syntax invocation used the root rather than isolated cwd and could not find the new script; it was rerun correctly.
- Real Edge and Chromium inspections covered desktop 1440×1000 and mobile 390×844, all three entries and 24 chapter buttons, Esc/focus/scroll restoration, draft isolation and keyboard containment. Parent inspected saved desktop/mobile screenshots. Three exact licensed photos were also actually seen in the reader after the CSP fix; no synthetic image is called photography evidence.

### Limits and preservation

The independent interaction reviewer reproduced the overwrite defect but its extended synthetic script stopped at a setup/state assertion; the parent-authored, real-HTTP regression is the executed closure evidence. Review reports preserve that distinction. Existing Starlette/httpx deprecation warning remains; no unrelated dependency upgrade was attempted.

Remote photos can load slowly (one cold load remained blank for over 13 seconds before succeeding on reopening). Loading and failure states are visible; original-site links remain. There is no offline media bundle. External professional pages can block access. Real user comprehension, delayed transfer and actual shooting improvement remain UNVERIFIED.

During this task the owner upgraded the finalization contract to 2.1.0. The root declared all six requirement IDs against the existing immutable task baseline; it did not create a late baseline. Scoped integration verifies preimages and preserves the dirty `web/app.js` and unrelated untracked work. No main merge, original-image copying into Git, reference/SQLite migration or new course beyond the three is included.
