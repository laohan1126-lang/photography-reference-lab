# Local character library and storage organization

## Owner request

“先让我能按角色直接找到所有下载的图片，再把散落的图片和临时文件梳理清楚，别误删原图和我之前的筛选记录。你派子agent去执行，你来派发任务和审核验收。”

## Scope and baseline

2026-10-29: Parent coordinates, reviews and publishes; independent DeepSeek workers implement the local browsing projection, audit storage, and review acceptance. Exact model gate evidence is private under `.local/character-library-20261029/`. No image generation, paid/external API, public release, database migration, original relocation, or main merge.

Baseline HEAD `cda6d55c68c597abb8e5dd8d6192d24168105018`, branch `codex/astra-r1r7-final-20261024`. Existing 866 tracked deletions, 13 modified files, and the UI-v14 task are unrelated; preserve them. Worktrees are under `.local/worktrees/character-library-20261029/{code,audit,review}`. Do not overwrite the concurrently edited `docs/tasks/CURRENT.md`.

Keep the existing FastAPI/SQLite/Pillow implementation and content-addressed originals. Add a local, read-only-input browsing projection and refresh entry. Downloaded pending/rejected/unimported images remain discoverable; project association never claims confirmed character identity. Browsing files are independent derivatives. The normal service and its current UI remain running.

## Frozen acceptance

- A clear local entry finds all downloaded material by associated character/project, including pending and rejected items and multiple project uses.
- Unattributed/unimported files are accessible or honestly reported without inferring image identity.
- Scattered images and temporary directories have exact, traceable classification; unknown/active/source material is retained.
- Original hashes and historical database choices, notes, acceptance and inspiration remain unchanged.
- Refresh is repeatable, prevents path escape and unsafe destinations, and never hardlinks editable browsing files to originals.
- Necessary organization is reversible, with an exact protection/move manifest and backups. Parent verifies the actual delivered result and scoped publication.

## Progress and verification

- Formal transaction started and immutable contract declared before implementation; initial restricted Publisher write failed, authorized escalation succeeded.
- Three native default/Sol dispatch entries were correlated by child response ID to fresh Magpie usage/routing records: all served `opencode-go/deepseek-v4.1-flash`, HTTP 200, one attempt each. Code worker high effort; inventory/reviewer gates low effort as chosen by the existing intent router. No global routing changes.
- Independent acceptance was frozen before implementation. Implementation and inventory were dispatched independently; parent preserves the real database snapshot and original hash baseline.
- Implementation, verification, and publication are pending. This record does not establish completion.

### Additional request and concurrent checkout update

While work was active, the owner requested three further fixes with screenshots: left-side character decoration interferes with controls; More workspaces expansion overlaps the project area; another search for 安养寺姬芽 creates a duplicate project and project deletion is inaccessible. Separate code workers own layout CSS/studio behavior and project lifecycle behavior. A route-verified Terra agent owns real browser inspection and acceptance; the parent remains final reviewer.

Source checkout concurrently advanced to `main` / `5399590863258060a9a34328f727693a34da183e`. All three first worktrees were created at that newer HEAD, so the initial stated cda6d55 worktree baseline was corrected before integration. The original formal Publisher baseline remains unchanged; do not overwrite concurrent work or recapture a late baseline. Two additional isolated worktrees are `lifecycle` and `layout` at explicit 5399590.

Read-only preservation baseline: 21 database tables, integrity_check ok, 1,774 original files present and matching their content IDs, 52 source sidecar hashes. The snapshot already contains 72 foreign-key check findings (24 each in preflights, aliases and discoveries); these are pre-existing and this task must not silently repair them.

Real browser reproduction at 1528 x 651: expanded navigation overlays the project controls, and the Find references button center hits the Photography notes link. Scrolling about 326 px puts the left scene print across the statistics/search region. Owner screenshots and Terra baseline screenshots stay private in `.local/character-library-20261029/`.

The owner's new duplicate project has a running search and one manually kept reference; the older compatible project has 20 references. Preserve both live projects and the running search during implementation. Test deletion/restoration only on isolated fixture data. The local catalogue may reflect legitimate new downloads/user changes; distinguish those from any task-origin state mutation.

## Verified local result

The accepted files are installed in the canonical daily checkout. The daily service at port 18765 returns byte-identical `app.js`, `kana.js`, `styles.css` and `kana-editorial.css`; no service restart or real collection operation was used for acceptance.

- `data/我的参考图/` contains 2,056 available image assets by exact content identity, 19 character groups, and 261 unattributed assets. These counts describe file content, not a claim that every encoding/crop is a different photograph. `角色项目/渡边曜（渡辺曜）/` contains exactly 49 independent JPG browsing copies, including 32 library references and historical collection material. Files are also available without the website.
- The final audit contributed 244 scattered paths / 243 content hashes, including 117 explicitly identified crop derivatives. Test fixtures and preview/header slices were removed from daily image inputs but retained in the inventory. No role identity or human choice was inferred from names.
- Real refresh ran twice successfully after correction, including automatic reuse of the saved inventory. All 4,132 HTML image references resolve to existing local files; role-folder file counts agree with the manifest. HTML URL encoding covers `#`, `%`, spaces and Chinese names.
- Parent preservation checks found all 21 database tables byte-semantically unchanged during the final projection, all 52 original sidecars unchanged, and all 1,774 original baseline assets present in the newly hash-verified catalogue. The current CAS has 1,775 assets because the owner's running search added one before the final projection snapshot.
- The original duplicate 安养寺姬芽 projects and their running search were retained. New searches refresh the project list, reuse a unique compatible project or ask which version to use. Submitted requirements and equipment carry into this Job's notes without rewriting the existing project. Delete/restore is reachable through the existing revision-protected soft archive API.
- Left decorative print interference is removed. Navigation and project controls share one left-column flow; menu expansion does not cover controls or leave the old 78px compensation. The final 1528px real-browser check measured a 9.5px menu-to-title gap, correct hit targets, natural expansion and restoration. Mobile photography-learning navigation was clicked through and returned successfully.

## Actual verification and retained failures

- Integrated `python -m pytest -q tests/test_local_catalog.py`: **13 passed**.
- Five real Chromium/TestClient lifecycle cases: **5 passed**, covering both global search entries, compatibility/ambiguity, new costume and project delete/restore with notes preserved. Four focused JavaScript/API helper cases also passed.
- Final rendered navigation suite `tests/test_left_rail_layout.py`: **4 passed**, including 1920x1080, 1366x768, 1528x651 and 390px mobile behavior using the actual `kana.js` entry.
- The independent review reproduced first-build/repeat-refresh ownership loss, then verified the corrected ownership/write ledger, multi-refresh changes, legacy first-build recovery and protected user files. Its original and follow-up reports remain in private evidence. Parent additionally found and fixed real filename-fragment links; all actual page links were checked after generation.
- Windows launcher invocation through `cmd.exe`: `--help` returned 0 with real argparse help; an unsafe output destination returned 1 without modifying that path. The launcher uses ASCII batch commands and CRLF, preserves the Python exit code and does not hang at `pause`.
- `node --check` for installed JavaScript and scoped `git diff --check` passed. Existing Starlette/httpx deprecation warnings were retained; no dependency upgrade was introduced.

Failures were not discarded: first audit fixture misclassification, interrupted preview generation, default-browser fixture hangs, incorrect test interaction/scroll coordinates, a first-batch launcher encoding failure, missing preview ownership, 90 fragment-broken links, obsolete layout padding and edits initially aimed at an unloaded presentation script all have explicit evidence. Tests were corrected to exercise real page behavior rather than forcing interactions or opting out by default. Native dialog acceptance through CUA timed out; deletion/restoration was verified by the successful real Chromium/API regression on synthetic data. No real user's project was deleted for testing.

## Reversible organization and scope

Three old test-output directories were backed up and moved into `.local/tests/历史测试-20261029/`; two were empty and the third contained two 12-byte test receipts. Forty-one unchanged first-build JPG duplicates and two interrupted preview directories (1,320 derived files) were verified and archived under `.local/backups/20261029-character-library/`. Unknown directories, originals, databases, source provenance, active jobs and historical decisions were retained. No disk-space saving claim is made from overlapping logical directory totals.

Execution checkouts are archived with full file manifests and verified ZIP contents after integration; evidence and reports remain under `.local/character-library-20261029/`. A readable `图片存放说明.html` and the detailed storage report are beside the new local catalogue. Product records and private images stay out of Git.

## Publication

Engineering acceptance is complete locally. Formal Git delivery must retain the original transaction baseline; concurrent main integration changed both branch and HEAD after that baseline. The actual seal/deferral receipt is recorded separately below. This task never merges or force-pushes main. Notion delivery is disabled by project policy.

Canonical `seal` returned `WORKSPACE_BRANCH_CHANGED`. Current checkout is `main` at the unrelated existing commit `7facf3e`; no task commit or push was made, and no remote SHA is claimed for this task. The original baseline was not replaced. Canonical deferral saves the concrete dependency blocker and exact accepted manifest for later recovery; Git remains unpublished, independently of verified local functionality. Notion was not invoked because `delivery.notion=false`.

## Owner follow-up: duplicate Hime and legacy export

The owner clarified that the expected entry was `data/exports/安养寺姬芽`, not only the separate catalogue. The [follow-up repair](2026-10-29-hime-project-consolidation.md) safely consolidates the two existing projects and supplies all 30 current/historical downloads there as independent browsing copies. It also closes a missed legacy case: nine run-only files existed on disk but lacked role-page ownership/links; known project identity plus matching preview bytes now recover them. The earlier file-count check alone did not establish complete role-page coverage. Original failure evidence and this correction are retained.

The follow-up carries forward this task's exact 14 attributable files after accepted-hash verification and explicit pre-existing-path authorization, on `codex/hime-project-consolidation-20261029`. This does not rewrite the original deferred transaction or authorize main integration. See the follow-up record and its separate Publisher receipt for the actual delivery result.
