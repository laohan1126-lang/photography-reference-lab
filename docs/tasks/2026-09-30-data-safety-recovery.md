# Data safety and auditable recovery — 2026-09-30

## User intent and boundaries

User asked to understand the real project, choose its most important current problem, and complete “发现问题 → 判断根因 → 实际修改 → 验证结果”. Preserve existing development work and actual image assets; mock success does not prove the real chain. Windows is the daily runtime. Do not mutate the live database from WSL, delete user history, invent image facts, or claim unrun checks.

## Direct initial evidence

- Checkout: D:\AI PROJECTS\photography-reference-lab; initial branch codex/windows-runtime-consolidation-20260929, HEAD d255a7c; one worktree. Substantial pre-existing uncommitted work, mainly CRLF plus 13 files of substantive edits and untracked experiments.
- Windows runtime PID record: 18816, this checkout's .venv\Scripts\python.exe, data directory this checkout's data, port 18765. Native interpreter confirms ref_lab resolves here.
- Native read-only SQLite inspection: schema 3 (docs still say 2), 18 projects, 732 assets, 735 refs, 890 discoveries, 2161 events; 72 FK violations: 24 each in aliases, discoveries, preflights, all referencing deleted split-action refs.
- tools/clean_and_reingest.py deletes pending action refs using a raw sqlite3 connection without foreign_keys, then imports a variable that only exists under another script's __main__. Deleted refs' candidate.imported events and source/assets survive; their complete historical Reference state cannot safely be inferred.
- Native Windows non-browser baseline: 4 failed, 170 passed, 1 skipped. Two failures are backup temporary SQLite handle leaks; one is the same connection-lifecycle error in a migration test; one fixture is normalized by Windows ZipInfo before archive validation.
- Secondary issues: normal curation does not call record_session_action; old session exists but graph/source show production has no caller. Ranking infers photographic claims from titles/search queries. The new refine endpoint only groups text while UI claims Skill synchronization. Split collection replaces received collage bytes with sharpened crops, without recording asset derivation. These are not fixed by a data recovery.

## Priority decision

Protect and restore data integrity before developing more acquisition or preference learning. Initially investigated aesthetic feedback, then revised priority after discovering current database damage and broken Windows backups.

## Observable acceptance criteria

1. Native Windows full backup returns successfully, releases SQLite handles, excludes secrets, and restores into an independent directory with identical received-byte hashes.
2. Legacy cleanup no longer deletes refs or re-ingests automatically; explicit project/data selection, dry-run default, revision-aware recoverable detach through the shared service, preserving aliases/discoveries/preflights/assets and choices.
3. Recovery creates a consistent database snapshot and a repaired copy in a new directory; source remains untouched. Only known dangling Reference edges can be removed, with exact previous rows archived in append-only events. Unknown FK errors fail visibly. No reconstructed human choices or fabricated refs.
4. Reproduce with the real library snapshot and validate integrity, foreign keys, preserved existing rows/events and all managed asset hashes; keep original snapshot and before/after receipt privately.
5. Run relevant automated and browser checks; record actual failures and unverified limits. Preserve original staging and unrelated edits. No push, main merge, or deployment claim.

## Outcomes

### Implemented

- `ref_lab/cli.py`: explicitly close SQLite snapshot/read connections with `contextlib.closing`; SQLite transaction contexts do not close handles. Native Windows backups now finish and release temporary files.
- `ref_lab/imports.py`: validate ZIP `orig_filename`, before Windows `ZipInfo` silently normalizes backslashes/truncates NUL. Test writer deliberately preserves hostile raw entry names.
- `tools/clean_and_reingest.py`: replaced top-level hard delete + broken automatic ingestion with explicit `--data-dir`, `--project`, dry-run default and recoverable service detachment with expected revisions. Existing damaged databases are rejected. No fabricated reassessment or upscaling.
- `tools/recover_orphaned_references.py`: read-only source -> SQLite backup including WAL -> untouched before snapshot + transactional recovered copy. Only dangling Reference edges in aliases/discoveries/preflights are supported. Exact previous rows are archived as recovery events. Optional edges become NULL with orphaned_reference_id; aliases survive as exact event receipts. Unknown violations roll back visibly. Existing output directories are refused. Database-only recovery is explicitly labelled.
- `tests/test_data_safety.py`: four regressions cover recoverable retirement with shared assets, WAL-aware recovery + exact receipts + source preservation, rollback for unsupported errors, and full backup/restore.
- Fixed the migration test's own SQLite handle leak. Added data safety/backup/import tests to Windows CI and data safety tests to core CI. CI itself has not run remotely this turn.

### Actual verification

Executed in the original D-drive checkout using its native Windows Python 3.12.8 unless stated otherwise:

1. Baseline: `.venv/Scripts/python.exe -m pytest -q tests --ignore=tests/test_browser.py --ignore=tests/test_live_system_regression.py --ignore=tests/test_ui_components.py --ignore=tests/test_collection_ui.py`: **4 failed, 170 passed, 1 skipped**.
2. First targeted run after closing fixes: `... -m pytest -q tests/test_data_safety.py tests/test_imports_jobs.py tests/test_personal_library.py`: **1 failed, 39 passed**, exposing that raw ZIP filenames are normalized again while reading on Windows. Corrected production validation to orig_filename; repeated exact targeted command: **40 passed**.
3. Final full non-browser command from (1): **178 passed, 1 skipped**, 1 Starlette deprecation warning. The skipped aesthetic manifest test depends on files outside the repo; it is not visual accuracy evidence.
4. WSL compatibility, isolated pytest temp data only: `/home/dell/projects/photography-reference-lab-regression/.venv/bin/python -m pytest -q tests/test_data_safety.py tests/test_imports_jobs.py tests/test_personal_library.py`: **40 passed**. The interpreter/dependencies are reused, but pytest imports the D-drive checkout. WSL never opens the primary data SQLite for these tests.
5. `node --check web/app.js`: exit 0. Native `... -X utf8 -m compileall -q ref_lab tools/recover_orphaned_references.py tools/clean_and_reingest.py tests/test_data_safety.py`: exit 0.
6. `... -m tools.recover_orphaned_references --source data/library.sqlite3 --output-dir .local/data-safety-20260930/recovered-real`: **72 archived rows, 0 remaining FK violations**, source unchanged. Raw rows precisely matched retained snapshot. Existing project/asset/ref/job/note/inspiration/session/profile records and all 2161 old events compared byte-for-byte at the SQLite row level.
7. Real asset verification: **732 received originals SHA-256 verified**. Full recovered backup **208,527,763 bytes**, SHA-256 `5d61a698407476f487b995b8ee0269052a517b19a8409498a7bb7edb149dc9dc`. ZIP CRC verified, extracted to independent directory, all originals verified again. Both recovered and restored application doctors reported `ok:true`. Receipt: `.local/data-safety-20260930/real-validation.json`.
8. Cleanup CLI on the recovered copy, without --apply: **dry_run, 24 current pending slices**, no automatic re-ingestion. Apply/restoration is validated only on isolated synthetic fixtures; real pending choices remain intact.
9. Native Windows actual HTTP UI on restored real library, explicit Settings at port 18766: login, actual sidebar project selection, available real image rendering, screenshot. **10 active projects visible, main image loaded, no JS page errors**. Viewed the screenshot with view_image. This is display/read verification, not per-image aesthetic acceptance. Private screenshot and ui-receipt.json are in `.local/data-safety-20260930/`.
10. Native component/browser invocation without `-X utf8` hit GBK decoding in test harness read_text. Attempt with WSL env `PYTHONUTF8=1` did not reach Windows. Explicit `-X utf8` component suite, stop on first failure: **3 passed, 1 failed**, because new X opens the uncommitted rejection-reason dialog whereas old stable-strip regression expects immediate removal. Separate actual HTTP/offline + collection UI command `... -X utf8 -m pytest -q tests/test_browser.py tests/test_collection_ui.py`: **8 passed, 2 failed**, same dialog mismatch in both stable-strip modes. These remain failures; no skip/forced click added to hide them.
11. `... -X utf8 -m pytest -q -x tests/test_live_system_regression.py`: **1 passed, 1 failed**, after historical migration/backup, image rendering, global inspiration, second-project creation and asset reuse passed; the same new rejection dialog blocked the old immediate-X expectation. Remaining cases were not run because -x stopped.
12. Initial browser suite was interrupted after repeated errors to diagnose encoding instead of waiting through duplicate timeouts; it is not counted as a completed run.

### Corrected assumptions and limitations

- Initial priority was feedback learning; current primary data damage + broken native backup made data safety more urgent.
- The initial readonly counts found one session with 215 actions, correcting any assumption that the session table is empty. Graph + source still show production has no record_session_action caller; actions may come from prior tools, not current K/I/M/X routes.
- Existing default .local is distinct from configured production data. A first auxiliary Windows server launched with WSL environment assignments did not receive those variables and initialized the default .local; login was blocked by origin mismatch. It was stopped, and replaced with explicit Settings for the restored copy. No primary data writes were performed. Subsequent screenshot navigation initially changed only the hash on the same document and stayed on an empty project; actual sidebar selection fixed the harness. Failed attempts are not display success.
- BrowserSkill Linux daemon failed startup; native Windows CLI proved Edge connected and an Agent Window navigated successfully, but its session disappeared before observation. It was confirmed absent via session list. No live BrowserSkill search, image download, or collector accuracy was claimed. The UI evidence uses actual HTTP with native Playwright instead.
- No restored library has been promoted to daily runtime. Original configured `data` still has **72 FK errors**; the original snapshot and recovered full backup are retained. The missing 24 Reference rows' full state is not recovered; this repair preserves surviving provenance, not unknowable deleted choices. Product owner can later restore a known full earlier snapshot to recover more.
- Full real backup/restore verified intact originals, but does not establish visual truth, real collection quality, Agent analysis or human acceptance. No paid API, publication, push, main merge or live service replacement.

### Product assessment and next priorities

| Area | Evidence-based state |
| --- | --- |
| Startup/runtime | Native Windows process/venv and current checkout confirmed; configured data is repo/data, differing from earlier migration receipt. WSL dev remains separate. |
| Storage/reuse | Existing content-addressed bytes + project relations + global inspirations; current API tests and new shared-asset retirement test pass. Old direct-SQL experiments bypass protections. |
| Acquisition | Adapter integrates BrowserSkill and optional explicit Bing; real new acquisition not run. Current crops drop downloaded parent bytes and call locally generated crops platform_variant; provenance must be fixed before expansion. |
| Human curation | Server choice persistence/API passes; UI real library displays and K/M browser steps pass, but X now needs dialog confirmation and old browser regression fails. |
| Preferences/Agent | Sessions/profiles exist but current curation not wired. Keyword summaries change weights, rejects without explicit aesthetic intent become supposed aesthetic negatives. Refinement endpoint only groups text; UI's Skill sync claim is false and showEditor/closeEditor are undefined. |
| Ranking | Titles/search queries generate photographic labels; default eye-level/static claims lack image evidence. Real screenshot contains these labels on an unreviewed image. This contradicts the project's evidence boundary. |
| Field guidance | Synthetic HTTP/offline workflows pass within 8 browser successes; actual Agent CLI execution/real card accuracy and owner acceptance not established. Current provider has owner-specific paths and fixed CLI flags/model. |
| Verification | Core is working after data fixes; Windows CI previously omitted backup tests, now expanded. Browser failures and legacy-manifest skip remain visible. README/architecture say schema 2 while actual schema is 3; dated VERIFIED notes are historical scope, not current acceptance. |

Next: (1) controlled adoption of repaired full backup after stopping the daily service and checking whether the owner has newer writes; (2) enforce received-parent/crop lineage and honest visual labels; (3) wire real curation events and require explicit aesthetic feedback without automatic keyword-based weight updates; (4) bring UI regression into agreement with intended quick X interaction and remove false Skill completion messaging.

### Git handoff

Task branch: codex/data-safety-recovery-20260930. Preserve pre-existing edits and untracked experiments. Stage only this task's normalized patch against the pre-edit snapshot plus its new/rewritten files; no mass newline normalization and no unrelated staging. Checkpoint commit and exact validation scope appended below after reviewed closeout.

### Reviewed checkpoint receipt

- Code checkpoint: `5297599ec40a6c4b3b41e74250964cc0b6b6beb9`, 9 files, 334 insertions / 7 deletions. No unrelated changes or newline normalization were staged. Existing personal-library rejection/refine test additions are preserved in the working tree and excluded from this commit.
- Exported the exact committed tree to `.local/data-safety-20260930/checkpoint`; native Windows interpreter explicitly asserted `ref_lab.__file__` belongs to that snapshot. Ran `pytest.main(["-q", "tests/test_data_safety.py", "tests/test_imports_jobs.py", "tests/test_personal_library.py"])`: **39 passed**, 1 deprecation warning. The working checkout had 40 because it also contains the owner's uncommitted additional test. This proves the checkpoint does not depend on those uncommitted additions.
- Exact reproduction from a clean checkout, Windows: `.venv\Scripts\python.exe -X utf8 -m pytest -q tests/test_data_safety.py tests/test_imports_jobs.py tests/test_personal_library.py`.
- No push, remote CI or deployment claimed. Working tree still contains the pre-existing owner/Agent work and CRLF changes; staged index was reviewed empty after code commit. Recovery artifacts are private under `.local/data-safety-20260930`, including raw before snapshot, recovered library, full ZIP, restored library, exact validation JSON, runnable validation scripts, and actual screenshot.
