# Windows Runtime Consolidation — 2026-09-29

## User intent
The owner wants the repository to return to a Windows-primary runtime because the actual interactive dependencies — Edge and BrowserSkill — live on Windows. The current live setup grew out of a WSL regression environment and now mixes a Windows launcher, a WSL FastAPI/SQLite process, a Windows BrowserSkill executable, and temporary worktree paths. The owner wants the repository corrected first, then Antigravity will pull it locally and perform the migration/acceptance work.

## Decision
**Primary daily runtime: Windows.**
**Compatibility/development runtime: WSL/Linux.**

This is a runtime/deployment convergence task, not a product rewrite. The application code remains cross-platform where practical; only the supported daily launch path changes.

## Why this is needed
The current repository launcher starts:

`start.bat -> scripts/launch.ps1 -> wsl.exe -> /home/dell/projects/photography-reference-lab-regression/run_server.sh`

That WSL script is outside Git, so the exact server path, data directory and collection adapter path are not versioned with the repository. The live acceptance run also temporarily pointed that external script at a task worktree. This allows one server process to load `ref_lab` from one checkout and `tools/collect_adapter.py` from another checkout — a split-brain deployment.

The application itself already supports native Windows Python (`install.ps1`, Windows process cleanup in `agent_collection.py`, loopback FastAPI, repo-local web assets). BrowserSkill and Edge are also Windows-native. The WSL indirection is therefore not required for the primary path.

## Non-negotiable boundaries
- Do not automatically move or delete the owner's existing WSL data.
- Do not let Windows and WSL alternately open the same live SQLite/WAL directory.
- Do not silently create a fresh empty library when a Windows data directory has not been configured.
- Do not depend on a regression checkout, temporary worktree, username-specific path, or untracked `run_server.sh`.
- Server and collector must come from the **same checkout / same Git revision**.
- BrowserSkill discovery must not hard-code `C:\Users\Dell`; prefer PATH and the current Windows user profile.
- Keep Bing fallback explicit opt-in only.
- Preserve the existing WSL/Linux CLI and testability as a compatibility path; do not make the application Windows-only.
- No database schema change and no automatic destructive migration.

## Repository acceptance criteria
1. `start.bat` launches the repo-local Windows `.venv\Scripts\python.exe`, not WSL.
2. The launcher derives repository paths from its own location and configures `LAB_COLLECTION_COMMAND` to the repo-local Windows Python + repo-local `tools\collect_adapter.py`.
3. Startup refuses to create a new accidental library when no Windows `LAB_DATA_DIR` has been configured and no existing repo-local library is present.
4. Local runtime configuration is stored only in a gitignored file/environment variable; secrets/data are not committed.
5. The launcher writes a PID file for the process it starts; the stop script stops that process instead of killing WSL/Python globally.
6. BrowserSkill candidate discovery is user-agnostic on Windows and retains WSL compatibility probing.
7. Documentation clearly states: Windows is the primary daily runtime; WSL/Linux remains a supported compatibility/development path with a separate data directory.
8. Antigravity receives explicit migration steps: stop old WSL server -> backup -> restore/copy into a new Windows data directory -> doctor -> Windows launch -> real BrowserSkill Golden Path -> owner approval.
9. No merge is claimed complete until that local migration and Golden Path have been performed.

## Local acceptance still required
GitHub CI can verify scripts textually and Python behavior, but cannot prove PowerShell process startup, Windows file locking, BrowserSkill daemon visibility, or migration of the owner's real 222 MB library. Antigravity must perform those checks on the owner's machine.

## Implementation outcome

Code-verified checkpoint: `404712829bd595df16dbc2084ee05c88f4793bac`.
The later `737d8042d9ccf32eca3a7f5154adb1dbc74e50af` commit only clarifies deployment documentation; runtime behavior is unchanged.

### What changed
- `scripts/launch.ps1` no longer calls `wsl.exe`, the regression checkout, or an external `run_server.sh`. It starts the current checkout's Windows `.venv\Scripts\python.exe -m ref_lab serve`.
- The launcher injects `LAB_COLLECTION_COMMAND` using that same Windows Python and the same checkout's `tools\collect_adapter.py`.
- `runtime-common.ps1` rejects a Python environment that imports `ref_lab` from another checkout, preventing the previous split-brain server/adapter state.
- Windows data location is explicit through `LAB_DATA_DIR` or gitignored `.local/windows-runtime.json`. Startup refuses a missing/accidental empty database. `-InitializeEmpty` creates a new database immediately and explicitly rather than persisting permission to recreate one later.
- `doctor-windows-runtime.ps1` checks the exact configured Windows data directory without requiring the operator to manually reproduce environment variables.
- `terminate.ps1` uses the launcher's PID record and `taskkill /PID ... /T /F`; it refuses a foreign checkout or reused PID instead of globally killing WSL/Python.
- `install.ps1` refuses to overwrite a pre-existing non-Windows `.venv` and verifies the editable package resolves to this checkout.
- BrowserSkill discovery no longer contains `C:\Users\Dell` or `/mnt/c/Users/Dell`. Windows PATH/current-user `~/.local/bin/bsk.exe` is primary; WSL compatibility probes mounted Windows user directories and still proves availability via `browsers --json`.
- CI now has a real `windows-latest` runtime job in addition to Linux core/browser jobs.
- `AGENTS.md`, README and deployment/compatibility docs now record Windows-primary runtime ownership and the prohibition on sharing one active SQLite/WAL directory between Windows and WSL.

### VERIFIED — GitHub runtime evidence
GitHub Actions run `36558169901` on code checkpoint `404712829bd595df16dbc2084ee05c88f4793bac`:

- Core / Python 3.11: **171 passed, 1 warning**.
- Core / Python 3.13: **171 passed, 1 warning**.
- Browser / Chromium: **23 passed, 1 warning**.
- Windows runtime / Python 3.12: **53 passed, 1 warning**.
- Windows runtime smoke test created an intentional empty Windows library, ran `doctor` with `database: ok`, started the repo-local Windows backend, received a healthy response on port 18765, then stopped the recorded Windows process tree successfully.
- PowerShell runtime scripts were parsed in the Windows CI job before the smoke test.
- All four jobs concluded `success`.

This verifies the repository-level Windows launcher/process/configuration path on GitHub Windows. It does **not** prove the owner's real 222 MB library migration, the owner's installed BrowserSkill daemon/Edge session, or the final real-photo Golden Path.

## Antigravity local landing checklist

Use branch `codex/windows-runtime-consolidation-20260929` (Draft PR #4). It already contains PR #3's search/preflight fixes, so local acceptance should test this branch directly.

1. Protect local work first: `git status --short`, `git fetch origin`; use a separate worktree if the current checkout is not clean. Do not reset/clean.
2. Confirm the old WSL service is stopped before touching data. The historical external `/home/dell/projects/photography-reference-lab-regression/run_server.sh` is no longer the intended production entry.
3. With the old WSL data still intact, create a full application backup of the real data directory. Record backup path, size and SHA-256. Do not delete the source.
4. Restore that trusted backup into a **new Windows-local data directory**. Never point Windows at the live WSL SQLite directory and never have both runtimes open the same database.
5. From this branch on Windows run `.\install.ps1`.
6. Configure the restored directory with `scripts\configure-windows-runtime.ps1 -DataDir "<windows path>"`; do not use `-InitializeEmpty` for the real library.
7. Run `scripts\doctor-windows-runtime.ps1`. Require database integrity, foreign keys and managed assets to pass before continuing.
8. Run `start.bat` (or `scripts\launch.ps1 -NoOpen -NoWait` for scripted acceptance). Confirm the process is Windows Python from this checkout, the PID record names this checkout/data directory, and `/health` is OK.
9. Confirm `/api/capabilities` reports the collection adapter configured. Run one real BrowserSkill search for 王昭君·长夜焕生 through the same UI/API path. Require `producer=local_browserskill_adapter`, no silent Bing source, real `detail_checked` activity, voice-line-title recovery, and imported items remaining unreviewed/uncertain unless genuine visual evidence exists.
10. The owner performs final per-image acceptance. Text-only mannequin/advertising false positives remain a known manual-review boundary.
11. Only after Windows Golden Path + owner acceptance: stop using the old WSL `run_server.sh` as production, keep the old WSL data and backup for rollback, and remove clearly identified test projects only after confirming they are not real user projects.

### Merge order
PR #4 is intentionally based on PR #3's branch. Do not merge PR #4 ahead of the search/preflight work it depends on. Local testing may use PR #4 directly; repository integration should land PR #3 first, then retarget/squash PR #4 as appropriate.

## Status
Repository implementation: **VERIFIED** within CI scope.
Owner-machine migration / BrowserSkill / real-library acceptance: **UNVERIFIED** until Antigravity completes the checklist above.

