# Shared Codex / Antigravity project contract

## Product intent
Private cosplay and everyday portrait reference library. The owner's goals are social connection, aesthetic exploration and reliable field guidance, not compulsory monetization or elaborate commercial sets. Character name is required; other requirements are free text. Preserve human taste and choices.

## Read before editing
Read README.md, docs/ARCHITECTURE.md, and the relevant docs/tasks entry. For acquisition also read notes/collection-workflow.md and docs/WORKER_PROTOCOL.md. The v0.2 entry point is `python -m ref_lab`; old generated boards and collectors are historical, not trusted verification paths.

## Non-negotiable invariants
- Search queries, titles and existing categories are discovery metadata, NOT image observations.
- Never fill missing evidence with positive prose or promote legacy annotations to verified facts.
- Open each actual selected image before claiming a visual review. Synthetic tests are not visual accuracy evidence. Equipment, locations, illustrations, collages and generated images cannot become real-person pose field cards.
- Preserve received original bytes. Derived previews are not originals. Never rewrite CDN URLs to guess higher resolution; never bypass access controls, export cookies, use hidden APIs or retry challenges aggressively.
- Human keep/reject, AI analysis and human card acceptance are separate. Unknown means blocked. New image bytes invalidate review/card/acceptance; changed project constraints invalidate card acceptance. Honor expected_revision conflicts; do not overwrite newer edits.
- Preserve historical batches, original assets, source provenance, human choices, and intent history. Imports are repeatable and must report failures. Do not delete legacy artifacts merely to make tests green.
- No automatic publication, multi-user exposure, domain change, external paid API invocation, whole-person image regeneration or main-branch merge. Keep runtime secrets, databases, browser profiles and new reference images out of Git.

## Task and handoff protocol
1. Before code changes, record the user's intent, boundaries and observable acceptance criteria in `docs/tasks/<task>.md`; preserve key user wording. Append outcomes rather than rewriting the original intention to fit an implementation.
2. Work on a task branch. Concurrent agents use separate worktrees/branches. Do not stage unrelated files or force-push.
3. Implement and run the relevant tests. Record exact commands and actual results, including failed/blocked/skipped checks. AI self-tests do not equal user aesthetic acceptance.
4. Update task outcomes, limitations and next regression steps. Run `tools/finish_task.py` with explicit paths, or equivalent reviewed commands. Push the task branch only when authorized; verify the remote SHA before claiming success. An incomplete checkpoint must be explicitly labelled, never presented as released.
5. Git versioned tasks are canonical. Sync a compact Notion view only when configured and authorized. A failed Notion sync is pending, not a successful write, and must not erase a valid Git checkpoint.
6. Final handoff: branch + commit + tested scope + unverified scope + runnable regression instructions. Never call a waiting job completed, or an unrun test passed.

Default regression: `python -m pytest -q tests/test_library.py tests/test_imports_jobs.py tests/test_workers.py tests/test_operations.py`; `node --check web/app.js`; browser/component tests per docs/CODEX_REGRESSION.md. Every bug fix should add or update a regression that represents the actual failure.
