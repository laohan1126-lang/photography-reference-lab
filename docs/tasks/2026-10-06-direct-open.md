# Direct website access (2026-10-06)

## Original user intent
“把访问口令这个东西取消掉 以后不要了 打开网页直接启动即可”

## Brief and boundaries
FastAPI runtime settings select the existing SQLite library; the browser already supports direct entry through GET /api/session. Replace the marker-dependent default with direct entry and remove cached/URL-token auto-login. Keep the existing explicitly enabled protected mode for separate deployments and internal session signing; normal start.bat requires neither a passphrase nor a no-auth marker.

Touch configuration, browser startup, deployment examples, and focused runtime/browser regressions. No new checkout, data migration, image edits, classification taxonomy changes, DNS/tunnel publication, remote Git or Notion writes.

## Observable acceptance
- A configured library without a no-auth marker opens without submitting a token.
- New browser contexts and server restarts still allow reads and writes.
- A stale cached token does not cause login attempts or prevent entry.
- Normal UI hides the passphrase form and lock button; mobile save/reload works.
- Existing explicit protected mode and cross-origin write rejection retain their tests.

## Outcomes
- Replaced the marker-dependent runtime default with direct access. Existing explicitly configured protected mode remains opt-in; no new authentication branch was added.
- Removed URL/localStorage-token auto-login and persistence (including the swallowed startup failure path). Normal startup calls the existing session endpoint directly; connection failures show an error instead of requesting a passphrase.
- Normal startup instructions and environment examples now describe direct entry; internal session signing and runtime ownership stay intact. No database, asset, decision, DNS or tunnel configuration was edited.
- Before implementation: the two new runtime regressions failed (no_auth=False; anonymous GET projects=401), proving the old default.
- Focused command: `.venv\Scripts\python.exe -B -m pytest -q tests/test_runtime_convergence.py tests/test_library.py tests/test_browser.py -k 'runtime or private_api or session_signature or no_auth' --junitxml=.local/classification-evidence/direct-open-focused.xml`: 38 passed, 36 deselected, 53.82s.
- Default and component regression: `.venv\Scripts\python.exe -B -m pytest -q tests/test_library.py tests/test_imports_jobs.py tests/test_workers.py tests/test_operations.py tests/test_personal_library.py tests/test_collection_runner.py tests/test_ui_components.py --junitxml=.local/classification-evidence/direct-open-regression.xml`: 137 passed, 110.50s.
- `node --check web/app.js` and `git diff --check`: passed. Existing optional protected mode, host/origin/CSRF checks retained their passing regressions.
- Actual official `scripts/launch.ps1 -NoOpen -NoWait -SkipExternalServices` started the configured 18766 library. Fresh desktop (1440px) and mobile (390px) browser contexts opened and reloaded without cookie, token submission, login UI, unauthorized response, overflow or JavaScript errors. Each showed 60 library tiles; token-free projects API returned 14 visible projects. Evidence: `.local/classification-evidence/direct-open-live.json`, `direct-open-1440.png`, `direct-open-390.png`.
- The mobile synthetic workflow saved a keep decision and reloaded successfully. Actual owner data was only read during this verification; its original images and human choices were not changed.
- Local task branch: `codex/patch-convergence-20261004`. Remote Git/Notion publication deferred because it is outside the authorized request. Phone/public tunnel routing is unverified in this task.
- Runnable acceptance: double-click this checkout's `start.bat`, open `http://127.0.0.1:18766/#view=library`, then refresh or open a new browser. No passphrase step is required.

