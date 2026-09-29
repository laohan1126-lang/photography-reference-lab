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
