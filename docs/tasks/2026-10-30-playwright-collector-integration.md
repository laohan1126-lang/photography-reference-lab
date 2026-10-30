# Playwright collector integration and original Nico continuation

Owner: “把 Playwright 接入参考库采集流程，继续之前矢泽妮可的任务，实际验证搜图、下载和入库。还是派子代理执行，你来审核，别新建重复任务，也别动原图和筛选记录。”

Use existing Job `333d31dec51f41b5a22d4ecc3b4d0270`, project `a89b8b768cd7445495ce7d648bffb87d`. Baseline status blocked, revision10, target30, search elapsed97.64548673057288s, resume generation1, no process owner. Do not create another job/project, extend budget, overwrite original bytes or alter preexisting human decisions.

Baseline HEAD68477f7aa0f0214e56dad76d57f47a5238b15853 on codex/search-experience-20261029. Parent transaction01a18cee-e6df-78c1-b57d-f45e51fdc4ed started before edits. SQLite backup `.local/backups/20261030-playwright-nico/library.sqlite3`; row/file baseline `.local/playwright-nico-integration/baseline.json`:29 projects,99 jobs,1535 refs,1775 assets,23 inspirations and5325 files under data/assets.

Frozen acceptance: explicit visible Playwright transport preserving existing collector semantics; normal same-job search retry with unchanged target/total budget; actual observed search/detail/download/source provenance and same-job import; preexisting file hashes and reference rows unchanged. Local fixtures, connection success and old images do not satisfy new-image acceptance. Stop on login/challenge/restrictions, preserve partial results; no silent BSK/headless fallback.

Implementation delegated to existing DeepSeek worker in `.local/worktrees/playwright-nico/implementation`, a source-only copy of the actual dirty daily checkout. Terra performs browser acceptance after parent code review. Root retains integration, data audit and publication. Prior Playwright trial demonstrated real login persistence with TUN off; that does not establish this pipeline's acceptance. Browser profile is already owned by the retained trial process and must be released normally before collector startup.

Status: implementation in progress. No real search started, no new images imported, no publication claimed.

## Installed implementation and actual result

Implemented same-file `PlaywrightBrowser(Browser)` and explicit backend factory, preserving the existing higher-level source/return checks and download/queue logic. Async Playwright calls run under bounded command/Job deadlines; unknown timed-out effects stop reuse. Profile locking, owned cleanup and explicit no-fallback paths are tested. Windows launch selects Playwright and no longer starts/checks BrowserSkill. Runtime digest now covers the shared trial helper. Parent caught missing evaluate deadlines and resource-release gaps before installation.

Parent executed async/boundary tests outside the Windows sandbox after the child environment could not run even a basic event loop:28 passed/16 subtests. Final integrated launcher/backend suite:24 passed. Terra's actual headed local smoke passed in7.91s, including click/DOM effect/scroll/close and zero remaining processes. Source hash46f58237c0df1eb8ef418b7bcdd253c4e738d0315125628803f88e5b0b76cb61 matched before/after. These checks did not count as real source acquisition.

Started the normal local service with original scripts, PID35920 at execution; code digest matched. Terra sent exactly one normal `POST /api/jobs/333d31dec51f41b5a22d4ecc3b4d0270/search`; revision11/running, resume generation2, unchanged target30/total3600s. Actual Xiaohongshu search/detail/download produced29 new distinct originals, all SHA-valid and decodable, none in the old asset set. First receipt52.141s. Background type/collage processing prolonged finalization; run elapsed1199.797s and final cumulative search elapsed1302.5712527217838s. Do not describe this as a20-minute download.

The existing automatic stage-finalization importer created29 references under the original Nico project/Job, all pending, with29 added assets. First image1080x1620/211978 bytes, SHA44fd632a7518497d2a2173dd73ecc9a38409c14b6d93a2109ce1571f5022be08. Original API/DB/source evidence is in `.local/playwright-nico-integration/verification/first-import-evidence.json`. Final Job is **partial**, reason `browser_unavailable`; qualified progress25/30, with4 collage-related candidates not counted as usable singles. These are system checks, not owner aesthetic acceptance.

Failure: evaluation lost its execution context during navigation. Read-only trace review points to the inherited evaluate-based `history.back`, but the log did not identify the exact script, so attribution remains an inference. A separate candidate replaces only Playwright `_go_back` with native `page.go_back`, preserving source/query/cards confirmation and no replay. Its16 tests passed after restoring a missing isolated temp parent directory. Real native-back smoke returned to the correct query/cards but failed close with `cleanup_pending`; this candidate was **not installed**. Keep its failed evidence and current working integration separate. No automatic retry or extra budget was used after the partial run.

Final parent data audit PASS:29 projects and99 jobs unchanged; all1535 old reference rows and all1775 old asset rows unchanged; all5325 old asset-file hashes unchanged; inspirations unchanged. Added exactly29 refs/assets. Task ID, project ID, creation timestamp, target30 and budget3600s preserved. Profile process count returned to0 after the formal run. No old original or human screening record was overwritten.

Status: real search/download/normal same-job import established; continuous acquisition through navigation recovery remains PARTIALLY_VERIFIED,25/30 target progress. Formal delivery deferred while the recovery failure and preexisting collector dependency ownership remain unresolved. No current-task commit/push or Notion success is claimed.
