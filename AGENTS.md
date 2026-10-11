# Shared Codex / Antigravity project contract

## Product intent
Private cosplay and everyday portrait reference library. The owner's goals are social connection, aesthetic exploration and reliable field guidance, not compulsory monetization or elaborate commercial sets. Character name is required; other requirements are free text. Preserve human taste and choices.

## Read before editing
Read README.md, docs/ARCHITECTURE.md, and the relevant docs/tasks entry. For acquisition also read notes/collection-workflow.md and docs/WORKER_PROTOCOL.md. The current entry point is `python -m ref_lab`; old generated boards and collectors are historical, not trusted verification paths.

## Non-negotiable invariants
- Search queries, titles and existing categories are discovery metadata, NOT image observations.
- Never fill missing evidence with positive prose or promote legacy annotations to verified facts.
- Open each actual selected image before claiming a visual review. Synthetic tests are not visual accuracy evidence. Equipment, locations, illustrations, collages and generated images cannot become real-person pose field cards.
- Preserve received original bytes. Derived previews are not originals. Never rewrite CDN URLs to guess higher resolution; never bypass access controls, export cookies, use hidden APIs or retry challenges aggressively.
- Human keep/reject, AI analysis and human card acceptance are separate. Unknown means blocked. New image bytes invalidate review/card/acceptance; changed project constraints invalidate card acceptance. Honor expected_revision conflicts; do not overwrite newer edits.
- Preserve historical batches, original assets, source provenance, human choices, and intent history. Imports are repeatable and must report failures. Do not delete legacy artifacts merely to make tests green.
- No automatic production deployment, public release, multi-user exposure, domain change, external paid API invocation, whole-person image regeneration or main-branch merge. Keep runtime secrets, databases, browser profiles and new reference images out of Git.

## Task and handoff protocol
1. Before code changes, record the user's intent, boundaries and observable acceptance criteria in `docs/tasks/<task>.md`; preserve key user wording. Append outcomes rather than rewriting the original intention to fit an implementation.
2. Work on a task branch. Concurrent agents use separate worktrees/branches. Do not stage unrelated files or force-push.
3. Implement and run the relevant tests. Record exact commands and actual results, including failed/blocked/skipped checks. AI self-tests do not equal user aesthetic acceptance.
4. Update task outcomes, limitations and next regression steps. Run `tools/finish_task.py` with explicit paths, or equivalent reviewed commands. Push the task branch only when authorized; verify the remote SHA before claiming success. An incomplete checkpoint must be explicitly labelled, never presented as released.
5. Git versioned tasks are canonical. Sync a compact Notion view only when configured and authorized. A failed Notion sync is pending, not a successful write, and must not erase a valid Git checkpoint.
6. Final handoff: branch + commit + tested scope + unverified scope + runnable regression instructions. Never call a waiting job completed, or an unrun test passed.

## Canonical checkout and workspace placement (owner instruction, 2026-10-11)
- The sole daily checkout is `D:\AI PROJECTS\photography-reference-lab`; `main` is the consolidated current version. This task explicitly authorizes integrating the current complete version into main. Future main merges still need the owner's authorization.
- All new Reference Lab worktrees, experimental copies, verification folders and backups must be descendants of this checkout. Use `.local/worktrees/<task>/<role>` and `.local/backups/<timestamp>`; resolve and verify the destination before creation.
- Never create a sibling `photography-reference-lab-*` checkout or this project's backup/test folders at `D:\AI PROJECTS` top level, nor use Codex's default external managed-worktree location for this project. Explicitly choose a repository-local path.
- Parallel agents use isolated worktrees inside this boundary. Keep private assets, databases and recovery archives ignored. Archive unique bytes and refs before removing an old worktree; do not overwrite the current version with an experimental branch.

Select verification by impact using existing commands in `docs/CODEX_REGRESSION.md`. Course prose/data changes require source/attribution review, the affected builder check and actual reading; shared reader changes also check affected legacy cases. State, identity, shared services, persistence, imports or dependencies require relevant callers and integration/UI paths; broad changes or an explicitly required release may justify the full suite at the Agent's judgment. Reuse evidence while tested worktree content, dependencies, configuration, command and relevant environment remain unchanged. Do not rerun unrelated suites merely for another Agent, commit or Publisher finish. Every bug fix should add or update a regression representing the actual failure; content tests protect attribution and observable reading behavior, not mandatory audit headings or disclaimer strings.

## Standing task publication authorization (2026-10-07)
- The owner explicitly requires the configured finish-task-publisher workflow after completed changes, including scoped commits and task-branch pushes when `git.push=true`. This is standing authorization; do not ask again or defer merely because Git publication was not repeated in the latest prompt.
- Verify the remote SHA before claiming a push succeeded. Record tests and unverified visual acceptance honestly. Unrelated cleanup awaiting approval must not defer publication of completed code.
- Publish the configured task receipt; report failed Notion synchronization as pending without concealing an already successful Git push. Preserve unrelated working-tree files.
- This authorization does not permit main-branch merges, force pushes, production deployment, or committing private images, databases, browser profiles or secrets.

## Personal-library invariants (v0.3)
- Asset identity, discovery intent, actual observations, global inspiration and project use are distinct. Never infer character identity from the search project.
- Global inspiration has no project parent; changing one project selection must not remove other uses. Preserve keyed filmstrip nodes during curation.
- BrowserSkill + local Codex / Antigravity task packages are the default; no standalone paid API requirement. Report waiting/blocked honestly.
- Cleanup is explicit, delayed and reference-aware. Do not run destructive tests against the owner’s normal data.
- Cross-project copy/move changes Reference use relationships, never Asset bytes. A new target relation must not inherit another project’s identity/preflight/review/card/acceptance; an existing target choice must not be overwritten.
- Detaching a Reference from one project is not X/reject and must remain recoverable. Contact-board export is read-only communication output, not a new decision state or field-card acceptance.

## Collector checkpoint boundary (2026-09-28)
Read `docs/tasks/2026-09-28-collector-checkpoint.md`. The optional command adapter is a tested internal transport, not a verified vendor/BrowserSkill connection or complete candidate pipeline. Keep live HTTP/platform blocks visible. Do not label missing identity/quality/session/profile work complete. Run the new collector and UI regressions too; never revive the silent headless fallback.

## Runtime ownership boundary (2026-09-29)
- Windows is the owner's primary daily runtime: repo-local Windows Python/FastAPI + repo-local collection adapter + Windows BrowserSkill/Edge.
- WSL/Linux remains supported for development, CI and compatibility only. Do not make the normal launcher depend on a regression checkout, temporary worktree or untracked `run_server.sh`.
- Server code and `tools/collect_adapter.py` must come from the same checkout/revision. Refuse split-brain deployments rather than silently mixing paths.
- Windows and WSL must not alternately open the same active SQLite/WAL directory. Move a real library between runtimes only through a stopped-service backup/restore and `doctor` verification.
- BrowserSkill availability means a probed binary can actually report a connected browser; executable presence alone is insufficient. Bing fallback remains explicit opt-in only.
- Do not delete or overwrite the old WSL data during Windows migration. Keep the backup and old directory until the Windows Golden Path and owner image review pass.

