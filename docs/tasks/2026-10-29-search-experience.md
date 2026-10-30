# Reliable one-form character search

Owner: “最早版本的时候搜图只要角色、作品、需要多少就可以开始了”；“别名不应该人工来添加，而是 AI 自己去搜索对应角色名然后翻译”；“按建议顺序和验收目标，派子代理执行，父代理审核派发验收”。

## Frozen objective and acceptance

1. Repair browser start/navigation/recovery. A failed start must not request extra budget. Preserve the Job, downloaded originals and remaining time when retrying. Show actual connection/navigation/login/empty-result states and exercise real recovery.
2. One form accepts character, work, quantity and optional notes. Advanced options do not create a compulsory second step. Reuse compatible projects without overwriting selections. Visible click feedback within 200 ms, including slow requests.
3. Automatically discover common multilingual names through the existing authorized AI/browser tooling, retaining source provenance and a cache. Original name queries can begin while enrichment runs. Ambiguity is explicit; query aliases are not visual identity proof. A previously unsupported character must work without manual aliases.
4. Move history preparation outside the blocking request/write transaction, preserve baseline integrity and recovery, and return lightweight paginated task summaries. Measure three fresh-process create/list requests, each below 1 second, and distinguish warm results.
5. Execute three genuine fresh-character one-form searches through the UI to a newly downloaded original with source URL/hash/timestamps and visible first-image evidence. Record actual latency under available sources; fixtures and preexisting assets cannot substitute. Also exercise failure/recovery.
6. Preserve existing original bytes, human selections/notes and concurrent work. Verify relevant callers and rendered flows. ROOT alone performs scoped publication, independently reporting Git and Notion; never merge main or publish private files.

## Baseline and implementation boundaries

Current Windows/Python/FastAPI application uses `ref_lab/service.py`, `api.py`, `collection_stages.py`, `tools/collect_verified.py` and `web/app.js`. Reuse existing Job states, file locks, task packages, BrowserSkill ownership and alias/provenance types. No framework, dependency, daemon or second application is required.

The diagnosed Nico Job is `333d31dec51f41b5a22d4ecc3b4d0270`: two first-query navigations took 27.219/27.281 seconds before timing out; session-stop recovery timed out after six seconds; zero downloads and zero image-model calls. Creating its empty Goal consumed 6.094 seconds. A real GET `/api/jobs` returned 98 jobs / 817629 bytes in 21.599 seconds, while the Nico detail median was 25.2 ms. These are the original measurements, not improvement evidence.

ROOT starts from `7facf3e` on `codex/search-experience-20261029`. The prior local character-library delivery remains dirty and is preserved, including 866 unrelated historical deletions. Exact source baseline, SQLite backup, contract, route proofs and acceptance evidence live under `.local/search-experience-20261029/` and `.local/backups/20261029-search-experience/`. Five preexisting UI/test/document paths are explicitly adopted for this continuation; unrelated changes remain outside publication.

Parallel write ownership: recovery worker owns browser collector/recovery code and its focused tests; service worker owns asynchronous task preparation, API/service/start state and focused tests; form worker owns `web/app.js` and UI tests; name worker owns alias resolution implementation/tests. ROOT integrates the name hook into collector code after disjoint candidates are accepted. UI verification is delegated only after actual Terra attribution; coding only after actual DeepSeek attribution. Workers never change daily data or publish.

Initial routing rejected one automatic DeepSeek502-to-Terra fallback before any tool use; other service/form workers and the Terra browser verifier passed their own routing gates. No global routing setting was changed.

Status: implementation active; complete acceptance remains unproven.

## Installed checkpoint, 2026-10-30 (Asia/Tokyo)

The reviewed implementation is installed in the canonical checkout and the managed Windows service is running at port 18765, PID 35092, source digest `fb1eb44262e74d770af2c0802397a91cc2ca55611f8f3f142f818571f8ec7570`. Installation verified exact hashes for 22 owned code/test/document paths before copying and preserved the original source archive. The launcher ran with `-NoOpen -NoWait -SkipExternalServices`: no Edge, shared BrowserSkill daemon, tunnel or browser setting was restarted. All 20 existing database tables are unchanged and all 1,775 original hashes still match.

The page now uses one form and explicitly creates `collection_mode=search`, shows a pending window before waiting on requests, separates retry from budget extension, and reads paginated task summaries. Goal creation is quick; baseline preparation happens outside the write transaction. Both modern and legacy direct start paths enforce the prepared-baseline gate. Recovery reads the actual page after a navigation timeout and retains an unconfirmed session when cleanup cannot be proven. Name discovery runs in a dedicated cancellable worker, preserves executed query records and continuation order, shares successful character/work caches across Jobs, and exposes progress or ambiguity to the candidate window.

Parent review rejected several defects before installation: the first one-form candidate omitted `collection_mode` and would have received verified-mode/start-409; summaries omitted action fields and classified legacy Jobs as split; direct search starts could bypass pending preparation; a new test fixture missed `os`; old result/package fixtures omitted the new preparation step; name scheduling dropped pending steps and overwrote its saved order; the cache was scoped per Job; and the public name-progress file could remain running after cancellation. Corrections preserve the actual acceptance assertions and original failure logs.

Actual validation, with overlaps between suites:

- Recovery boundary/API/search-return checks: 56 passed on the host, including the API cases the child's sandbox could not execute.
- Combined service/Goal/single-form/UI regression: 170 passed. These are Chromium/TestClient component checks, not a claim of three successful daily-browser searches.
- Adjacent stage, legacy runner and import callers: 67 passed.
- Name-progress/ambiguity and existing candidate-window checks: 20 passed.
- Final name lookup/cache/cancellation/CLI-continuation checks: 19 passed. Earlier partial failures are retained; a missing preparation step in a fixture was repaired using the real preparation functions.
- Three separate old server processes: creation 2202.858/3484.289/2416.697 ms; list exceeded the 12000 ms observation bound each time. A separate initial list run exceeded 45 seconds. Three separate final server processes: creation 61.808/63.666/60.660 ms; list 41.367/42.958/39.248 ms; warm list 26.746/35.732/27.148 ms. OS/disk caches were not flushed. The daily installed summary endpoint took 49.536 ms for 20 of 98 Jobs.
- Real existing Antigravity name lookup for 矢泽妮可 / Love Live! completed in 98.960 seconds with an actual search_web ACTIVE/DONE pair, multilingual names and returned search-source links. It is search-result evidence, not claimed page-body inspection. A cache-only second read took 4.280 ms and invoked no model. The slow first lookup is off the initial browser-search path.

Private evidence: `installed.json`, `daily-install-verification.json`, `originals-after.json`, `performance-before-bounded/measurements.json`, `performance-after-combined/measurements.json`, `combined-acceptance.txt`, `adjacent-callers.txt`, `name-visible-acceptance.txt`, `name-final2.txt`, and `name-live/nico/` under `.local/search-experience-20261029/`.

## Remaining acceptance and external dependency

R1 real browser recovery and R5 three fresh-character first-image runs remain UNVERIFIED, 0/3 completed. The daily browser's actual 200 ms feedback also remains unverified despite component checks. Terra reproduced renderer/frame-tree timeouts on both the app and the local `/health` page; direct HTTP is healthy. The native Computer Use tool then expressly stopped browser operation because it could not determine the current Windows browser URL reliably enough to enforce policy. This was not labelled an automatic approval-review rejection. No alternative interface was used to evade that stop. Owned sessions rizt/bkpt were subsequently absent from the registry; personal tabs and settings were untouched.

The owner has been asked asynchronously to save pending Edge work and manually reopen Edge. No reply or approval has been inferred from elapsed time or the date change. After that external-state change, re-establish a verifiable browser context, then execute the originally required three real searches and recovery check. Do not lower the criterion to unit tests, known images or API-only downloads. The thread goal stays active; the implementation checkpoint is not full task completion.

Routing audit also found automatic DeepSeek-to-Terra fallback during portions of form/recovery/name work. The initial failed gate was rejected; later fallback is recorded as mixed actual routing, not described as all-DeepSeek. The affected active name worker was frozen and ROOT reviewed and repaired its candidate. No shared routing settings were changed.

Branch: `codex/search-experience-20261029`; HEAD remains `7facf3ea76f38ef824debe2e34687fb1cf51b945`, with no task commit or push. Formal delivery is deferred on the real-browser dependency, using the original immutable transaction `01a187b4-849c-7b33-8dcf-0d1b67837046`; Notion remains disabled. Execution worktrees and backups are retained for continuation, not discarded before full acceptance.

## Edge reopened; bounded runtime repair prepared (2026-10-30)

The owner explicitly confirmed Edge was reopened. A fresh Terra response was verified against Magpie usage/routing (one Terra attempt, HTTP200). The extension reconnected as generation3, but a new explicitly bound session creation still timed out waiting for the extension; its subsequent session list was empty. No new Job or image was created, so the three-role first-image acceptance remains0/3. Evidence is `live-20261030/UI-RESULT.md`; the previously frozen acceptance hash is unchanged.

Read-only doctor and process inspection show CLI/daemon0.3.2 and Edge extension0.3.3, both protocol1.3 and reported compatible. The daemon is a foreground process serving52800; its original launch matches the project's existing hidden `Ensure-BrowserSkillDaemon` entry. Logs contain repeated failed auto-update downloads. A version mismatch is not established as the cause.

The official CLI0.3.3 Windows archive is staged under `live-20261030/bsk-update/`, SHA256-matched to the GitHub release asset. Its Tencent Authenticode signature is Valid and its executable reports0.3.3. The original binary is independently backed up and hash-checked under `.local/backups/20261030-bsk-update/`. The concrete restart/rollback plan is `live-20261030/bsk-update/PLAN.md`. No global executable replacement, daemon restart, browser-setting change or new browser-control attempt has been made during this preparation. The installed browser skill prohibits shared-daemon restarts; the next action needs a narrow explicit owner exception, with an empty-session recheck.

The newly observed startup failure also exposed a missing UI explanation. `searchFailureText` now distinguishes session-creation and renderer/cleanup failures, and no longer treats a generic English `required` as a login request. The exact startup-error regression passed on isolated Chromium/TestClient; no broader unchanged suite was rerun. The live task is not complete and publication remains deferred. Continuation transaction `01a18836-f003-7af0-994a-9485d1180a10` preserves the prior transactions and explicitly adopts38 attributable same-thread paths for eventual coherent delivery, excluding unrelated work and private data.

## Authorized BrowserSkill update executed (2026-10-30)

The owner explicitly said “允许更新并重启 BrowserSkill”. Transaction `01a18867-8c46-7fa3-bb80-f4ff10dae84b` captured the external `C:/Users/Dell/.local/bin/bsk.exe` hash before replacement. After an empty-session and exact-process check, the official signed0.3.3 executable replaced0.3.2. Normal daemon stop and the original hidden foreground-launch parameters were used; the retained port is52800 and Edge instance9d3f232a reconnected automatically. The installed hash matches the staged official binary, and the old binary remains intact in the prepared backup.

Terra then performed one bound session-creation probe using the new CLI's documented `--focus`; it still timed out. The foreground process output was subsequently captured in private files under `live-20261030/bsk-update/`, with one authorized empty-session restart for diagnostics. Current serving PID30280 reports0.3.3, the extension reports0.3.3, and the runtime parameters remain unchanged otherwise. Protocol compatibility and heartbeat are not counted as a successful control test.

A distinct recoverable request-id probe was prepared once. Start reported `protocol_error`, a session/window identifier, and “extension did not finish rollback within 2s”. Inspection and cancellation of that exact request both returned `closed`, `session:null`, `cleanup_error:null`. The final daemon session list is empty; physical window destruction was not independently asserted. No personal tab, permission setting, browser storage, runtime-state file or unknown process was modified. No role Job or download was created, and all20 data tables still match the pre-trial snapshot.

Runtime update: PASS. Real browser control and the three fresh-character first-image trials: still UNVERIFIED,0/3. Matching versions did not resolve the observed creation failure; no specific extension-internal cause is claimed. The next requested evidence is the first error shown on the BrowserSkill card in Edge's extension-management page, or confirmation that no error button exists. No repeated window creation or unrelated tests are planned while that evidence is missing. Evidence: `bsk-update/installed.json`, `bsk-update/final-status.json`, `bsk-update/acceptance.json`, and `updated-runtime/request-probe/`.

## Owner-forwarded AGY recovery and follow-up (2026-10-30)

The owner reported no extension error button, manually opened the reference page, then forwarded AGY's claim that session wvek/window1236242287 and `/health` navigation/reading succeeded and were cleaned up. The forwarded command list also includes a main-app attempt exiting1 and stopping xwsd. AGY attributed recovery to foreground activity waking an MV3 Service Worker; no worker lifecycle trace or raw successful command output was supplied, so the practical procedure and the attributed diagnosis are recorded separately in `docs/WORKER_PROTOCOL.md`, not promoted to a uniquely proven root cause.

Parent source review confirmed that `about:blank` is the normal Agent Window startup page. A read-only approved-browser capability check still reported Edge unavailable, and the user-confirmed foreground page did not produce a tool-verifiable URL; no native input bypass was attempted. Later direct BSK probes did create ghix and cfhg. The ghix check followed an unsuccessful debug-start attempt; a separate cfhg check omitted debug capture, used `--focus` and a normal25s navigation deadline, and still timed out reading `/health` with `Page.getFrameTree`/renderer errors. Thus neither the successful AGY report nor the failed Codex probes alone prove the unique cause. Both runs' original evidence remains under `live-20261030/agy-recovery-validation/`; no new search Job was created.

Independent code review also found an actual retry defect: the plain retry endpoint reached `start_collection_attempt` without advancing `search_resume_generation`, so the search-only CLI could exit on the previous terminal receipt. A new regression reproduced the missing generation. The shared attempt transition now advances the generation for explicit retries of terminal split-search states while preserving Job ID, target and time budget. A real CLI regression now covers both extra-target continuation and a same-budget retry from a collector-generated startup failure. Relevant suites passed28 cases; the final service/CLI suite passed16 cases. Tests use synthetic adapters and do not count as first-image acceptance.

The retry fix and project worker guidance were backed up and installed from the isolated integration worktree. The daily service was restarted only after confirming no new trial Job had started. PID24444 now reports source digest `fd4df1e2ad6112f4cb67daec705a0f8afb3d17fd0679356d9c62f63337e143e2`, exactly matching the current local implementation. This also corrects a stale running digest left after the previous error-message edit; the digest includes `web/app.js`. The original full objective remains unfulfilled: actual three-character UI-to-first-image acceptance is0/3.

The owner requested project-local experience recording; no personal/global memory was edited. Current formal transaction is `01a18893-b1c5-7a80-a946-087a19f32af0`, preserving the earlier deferred transactions. No task commit, push or main merge has occurred.
