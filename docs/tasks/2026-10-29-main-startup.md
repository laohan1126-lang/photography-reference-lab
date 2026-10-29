# Main integration and Windows launcher recovery, 2026-10-29

## Owner request
“合并现在的到main”，修复start.bat的启动问题。The supplied diagnosis names four removed history roots in .local/windows-runtime.json. Preserve the real library, existing changes, original artwork, and all history still available. No new collection or paid/model calls.

## Plan and baseline
Primary checkout cda6d55 on codex/astra-r1r7-final-20261024 with 14 dirty/untracked paths. Latest current Kana fidelity branch5399590 includes this base and corrects the previously rejected UI. main/origin main172b296 are ancestors. Use clean codex/main-startup-20261029 based on5399590 for scoped documentation/regression delivery, then fast-forward main and operate the sole canonical checkout. Back up dirty files/patch/config; retain old UI work in an explicit stash, and keep unrelated rules/.gitignore edits present. Never overlay rejected old UI onto the latest candidate.

## Root causes and boundaries
- Reproduced Get-ReferenceLabRuntimeConfig -RequireLibrary failing History root unavailable. All four configured optional roots were removed in the October27 worktree cleanup. Preserve cleanup/bundle records; remove only nonexistent roots from the local config. Keep strict missing-path checks, data_dir, port, auto_classify and budget unchanged. start.bat and launcher scripts do not need changes.
- Actual runtime also has broken Pillow12.3.0 missing Image.py, repaired at the same version. pip check then identified eight missing transitive dependencies (annotated-types,anyio,click,h11,greenlet,colorama,iniconfig,packaging); restore only those required dependencies. No full environment replacement.
- Existing original/library history is not deleted or rewritten. Removed optional history roots cannot contribute to future dedup; this repair does not claim to restore private files previously deleted by another cleanup.

## Verification to complete
Official backup plus isolated restore checks before daily startup; real Windows config regression for empty optional roots and strict rejection of a configured missing root. Focused UI regression for the actual adopted version. Fast-forward canonical main, launch through the normal Windows entry, verify /api/runtime source/data/revision identity, health and loaded Kana resources. Verify main remote SHA. Owner aesthetic acceptance remains separate.

## Progress
14 original dirty files and config backed up to ignored .local/backups/main-startup-20261029. Pre-fix config error reproduced. Local history_roots now [] with every other field preserved. Runtime dependency recovery/official backup and integration pending.

## Verified integration checkpoint
Owner explicitly confirmed “允许，合并到 main 并运行” after automatic review twice applied the old no-main-merge scope. Main was then fast-forwarded172b296 ->5399590. Canonical checkout is main, not a preview worktree.

The 13 preexisting modified paths are retained in stash `owner-pre-main-startup-20261029-preserve-ui`; the original untracked UI task file remains. AGENTS.md and .gitignore were copied back byte-for-byte from the protected backup to remain visible as unrelated changes. 866 previously deleted tracked reference/screenshot files were discovered during refreshed Git status and left untouched, outside the stash/commit scope. The original patch and status inventory are retained locally. A zero-byte .git/index.lock from October27 with no live Git process blocked the scoped stash; it was moved into the same backup, not blindly deleted.

Runtime recovery expanded only after concrete failures: Pillow import failed, then annotated_types missing, then FastAPI missing in the verification environment. Existing RECORD inventory and pip check were inspected; finally `pip install -e '.[test]'` restored the project's declared requirements without recreating the venv. `pip check` now reports no broken requirements.

Official backup:1774assets; isolated extraction CRC/integrity checks OK,1534refs,26projects. Isolated doctor:0 missing/corrupt originals,0 missing derivatives,72 existing FK errors; doctor reindexed42 states only in the disposable restore copy. The live assets/refs/projects rows hash-identically to the original backup after daily startup, so owner selections and originals metadata are preserved. No live doctor or repair was run.

Real `cmd.exe /d /c start.bat` completed with exit0 on main5399590; PID35820 source/data/adapter all canonical. Cloudflare existing configured endpoint verified the same runtime and BrowserSkill reported connected Edge9d3f232a. No reference collection was started. Browser opened automatically. Actual Edge1366x768 and390x844: real photo/private art decoded, editorial CSS200, no page exceptions, no horizontal overflow, zero browser write requests. Runtime identity and local screenshots are in ignored .local/main-startup. Phone visual review and new live acquisition remain untested; aesthetics still PENDING.

`tests/test_windows_runtime_scripts.py`:10passed, including actual PowerShell empty-root success and configured missing-root rejection. This preserves fail-closed history validation rather than silently skipping configured paths. Actual launch before config repair failed History root unavailable; after repair completes. start.bat, launch.ps1 and runtime-common.ps1 bytes remain unchanged.

Final source receipt, main/remote SHA and post-delivery normal-launch identity will be saved independently; relevant UI regression is still running at this checkpoint.

## Focused acceptance complete
`python -X utf8 -m pytest -q tests/test_kana_static.py tests/test_kana_presentation.py tests/test_kana_fidelity.py tests/test_ui_components.py` on the isolated current version:40passed in614.66seconds, no failures; includes actual HTTP login and real business components. Windows script/config regression10passed. Reuse these results for delivery; tested source/requirements/environment unchanged. Existing Starlette/httpx deprecation warning only, not a test failure.

The implementation task is technically verified for main integration and normal Windows startup. Final Git publication and canonical main fast-forward to the task-record commit follow through Publisher and normal reviewed Git commands; final remote/runtime SHA is saved in the ignored handoff receipt instead of manufacturing another documentation-only commit. Main merge was explicitly authorized by the human confirmation. No new photos, collection, model calls, cleanup or user-data repair performed.
