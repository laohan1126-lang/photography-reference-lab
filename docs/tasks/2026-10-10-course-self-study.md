# Course self-study refinement and owner-photo follow-up

## Owner intent and boundaries

The owner asked: “你把这种自己填写的区域删掉 本身就是自学教材 没必要 保留问题就行”. They then asked to find their own photographs in Google Drive and add memorable negative/adjustment cases to this chapter. No local synced copy exists; the owner requested another Drive attempt after a connection failure.

Keep the questions, original explanatory chapter, folded analyses and navigation. Remove the course's answer fields, choice widgets, reflection form and self-assessment save action. Change writing instructions into thinking prompts. Preserve previous gateways, ability-map records, original image bytes and unrelated work. Do not turn a single image into proof of capture settings, treat all stylistic exaggeration as error, or create a fabricated corrected photo.

## Blueprint and dry-run

FastAPI serves the static validated GATEWAYS catalogue and a plain JS reader. The sample is distinguished by `kind=course`; existing gateways share the reader but retain their private exercise forms. Render course exercise title/prompt only, skip its reflection form and conditionally bind the form handler. Keep catalogue exercise IDs and existing state allowlists. Update the HTTP/Chromium course regression; make the existing stale-skill regression explicitly open its original gateway instead of relying on the course-first link order. Rebuild the canonical bundle.

Planned owned paths: this task record, `web/learning-gateways.js`, `docs/research/photography-atlas/GATEWAYS.json`, `web/learning-atlas.json`, `tests/test_learning_course_ui.py`, `tests/test_learning_gateways_ui.py`, and the course paragraph in `README.md`. Photo catalogue/provenance changes are conditional on inspecting actual owner-photo pixels. No backend/data migration or owner-data write is required for the reader change.

ROOT started and declared the immutable Publisher transaction before the first edit. Reviewed receipts `01a123f2-f2f4-7461-becc-18df4fdce44e` and `01a12346-b317-7412-82e3-0bd04d62c7d0`: preserve the course/map/media boundary; this is an explicit reader preference, not another knowledge-index expansion. Existing unrelated dirty `web/app.js` and untracked items are excluded.

## Acceptance and evidence

- Course contains its three thinking questions and folded analyses, with no answer/assessment/save fields on desktop or mobile.
- Closing/reopening, chapter navigation and skill navigation still work; reading sends no writes and preserves existing private records. Previous gateways retain their real forms and conflict handling.
- Canonical build, reader syntax, scoped browser regressions and diff checks execute successfully.
- Inspect real Drive photos before any photographic claim. If connection remains unavailable, owner-photo integration is explicitly pending; completed reader work does not certify this second request or teaching effectiveness.

## Outcomes

Pending verification. Initial connector folder listing and image search failed in transport to `chatgpt.com/backend-api/ps/mcp`; a further owner-requested root listing failed the same way. Connected Edge inspection/creation failed with `nodeRepl.fetch request failed`; direct in-app Drive creation timed out. No photograph has been read, selected, copied or added on that evidence.


### Verified reader change

The course now renders three thinking prompts without textareas, choice controls, a reflection assessment form or a save button. Existing gateways retain their input forms. The red course regression failed as expected (7 form widgets versus the required 0); after implementation the scoped suite passed 25 tests. A follow-up seeded-record course run passed 3 tests, including no UI writes, unchanged old saved records, no browser page errors, reopening and desktop/mobile reading. Canonical build/write and build/check passed; `node --check web/learning-gateways.js` and `git diff --check` passed. The actual in-app course page was reloaded and inspected without input fields. Reshoot-variable tracking instructions remain useful field practice; they are not an answer-entry UI.

### Drive recovery attempts and owner priority

After the initial connector errors, the authenticated in-app Drive browser reached the owner's 剑斩 folder. ROOT inspected DSC02260.JPG and DSC02268.JPG on screen and saved clearly derived, complete photo-preview screenshots under ignored `.local/course-owner-preview/`. These are not original JPG/ARW bytes. The originals were neither modified nor deleted. DSC02260 received an independent pixel review. No photograph has yet been registered or added to the chapter.

The owner then explicitly prioritized diagnosing download/connection failure and stabilizing the plugin. Photo integration is deferred while that priority is investigated. Drive list-folder and Plugin Management search both fail with the same transport error to `https://chatgpt.com/backend-api/ps/mcp`; the latter rules out treating this as only a Drive-file permission problem. A 2026-10-10T06:45:47Z Drive list call still failed in 2.805 seconds. An old repository upload token separately returned `invalid_grant`; it is not the connected plugin credential and was not changed.

Read-only connectivity checks: the existing system proxy endpoint 127.0.0.1:12002 is listening under iKuuuVPNCore. Python urllib, using the existing system route, received Drive HTTP 200 in 1.11s and anonymous HEAD to the OpenAI shared endpoint HTTP 403 in 0.38s. The latter proves an HTTP response, not authenticated plugin success. Default curl connections to both hosts timed out after 15s before TCP/TLS completion. Current process proxy environment names are absent. No network, proxy, credential, plugin configuration or software installation was changed. These checks support a route/session hypothesis, not a proven Rust-client routing diagnosis.

Desktop logs at 05:33 UTC show shared MCP initialization/handshake failures adjacent to `net::ERR_PROXY_CONNECTION_FAILED`. This evidence does not by itself establish why the target failed or whether current failures are cached. Reinstallation or new Drive permissions are not justified by the observations. Plugin stability and original-file download remain unverified; the owner-photo teaching cases remain pending.


Later log review: the 05:33Z proxy errors are historical. The latest desktop log (`codex-desktop-0b549a74-2f0f-4087-a213-464f938cebfb-36012-t0-i1-000002-1.log`, lines 23783–23833, 24762–24825 and 24911–25295) reports `codex_apps` ready at 06:40:06.200Z; 06:30–06:45Z contains no exact shared-endpoint error. An unrelated NotebookLM connection-test startup failed and is outside this task. Ready/discovery metadata does not prove the actual Drive invocation succeeded: the timed 06:45Z tool request above still failed. Historical proxy errors are not a verified current root cause.

The lowest-change recovery experiment is to reopen the client so it can establish a fresh plugin session, retaining all existing network/Drive settings. That action has not been executed. After recovery, acceptance requires actual folder listing and one original JPG download with readable pixels/hash, followed by another successful read; it cannot be claimed stable from discovery-ready state or one webpage preview.

Owner folder locator: https://drive.google.com/drive/folders/1VCmGYapyG-_t9szWUp4Xdw636BdqKkIg (DSC02260.JPG / DSC02268.JPG). No temporary authenticated preview URL or credential is committed. Final in-app recheck: 0 course input/assessment/save widgets, 3 thinking prompts and 8 chapter sections. The original circled prompt was viewed with only the question and folded explanation; screenshot saved privately as `.local/course-owner-preview/course-question-only.jpg`.


Publication scope: verified question-only reader plus the factual connection-attempt record, explicitly a partial-acceptance checkpoint. Owner-photo integration and plugin recovery are not completed. Final `tools/build_photography_atlas.py --check` passed (14/71/247; version cbe5388ae5fad780decf610f7ba0f57a5270c3ef1deb17f977faa95d3417ac15); an initial invocation of nonexistent `tools/build_learning_atlas.py` failed with file-not-found and was corrected to the inspected canonical tool. Final reader JS syntax and diff checks passed. Private preview/screenshots and unrelated work are excluded from the commit.
