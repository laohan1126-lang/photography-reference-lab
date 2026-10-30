# BrowserSkill control and collector compatibility repair

Owner request: “先尝试一下修复吧，如果修复不了，你直接去修改插件……参考库的采集代码你也修复一下看看。”

## Scope and acceptance

Python acquisition runs through BrowserSkill CLI and its Edge extension. Reuse the current collector, error taxonomy, session ownership and monotonic task deadlines. Repair the shared command boundary used by search, details and downloads; retain source restrictions, human interruption and one-use observation guards.

Touch: `tools/collect_verified.py`, `tools/collect_adapter.py`, `tools/exact_recall.py`, `ref_lab/browser_recovery.py`, a shared CLI helper if required, focused tests and worker documentation. BrowserSkill source/build experiments stay in `.local/browser-skill-repair-20261030`; any maintained upstream patch belongs in `patches/browserskill`. No data migration, original modification, decision changes, automatic budget extension or unrelated UI work.

Accept collector changes through production-boundary tests, then local HTTP navigation/synchronization/read/owned cleanup. Run a real source read/download only after local control works. A blocked runtime remains explicitly unverified. If stock BrowserSkill remains stalled, inspect and attempt a reversible extension fix without disabling cooperation or security checks.

## Baseline and plan

Daily branch `codex/search-experience-20261029`, HEAD `7facf3ea76f38ef824debe2e34687fb1cf51b945`; preserve pre-existing dirty work and 866 unrelated deletions. Publisher transaction `01a18c06-60c4-7501-b43e-136719b8ddea` started before edits. Six relevant files backed up under `.local/backups/20261030-browser-skill-repair`; hashes and contract under `.local/browser-skill-repair-20261030`.

Prior live diagnosis: current stock CLI/daemon/Edge extension 0.4.0; ordinary HTTP health succeeds. Fresh owned session creation took 10.268 s, health navigation timed out after 32.876 s, then tab listing and cooperate sync returned `Previous operation is still settling; this action was not dispatched`. Owned stop succeeded. Windows sandbox IPC denial is distinct and was resolved for that probe with a per-command exception. Historical protocol mismatch is not the current matching-Edge failure.

Root causes to address: collector omits 0.4 cooperation contexts, repeats infrastructure timeouts, collapses distinct errors, and contains an unsafe stop-all recovery branch. Plugin control stall also reproduces without the collector. Keep bounded recovery and user-data invariants; remove blind retry/stop-all behavior rather than layering retries. Earlier evidence and unfinished three-character acceptance remain preserved; this task does not relabel them completed.

## Verification

The collector now shares `ref_lab/bsk_command.py` across its primary Browser controller, legacy adapter/CLI and exact-detail reader. Each protected action obtains one fresh context, and synchronization plus execution share a deadline. A sync timeout records no dispatch; an action timeout records unknown effects and is never replayed. Human abort ends collection as cancelled. Control errors retain reason/dispatch/effect metadata and propagate through detail handling. Recovery reads a rebuilt page before declaring success. Cleanup no longer stops all sessions; browser selection rejects ambiguous/unresponsive/mismatched instances. Fixed-extension wakeups and alternate-daemon startup were removed from active compatibility paths.

Subagent classification work used verified Magpie route `1793243869473`, response `resp_7e028308f19e412299e53805e6fe17c7`, provider `opencode-go`, served `deepseek-v4.1-flash`. Root review caught error-class propagation and nested reason omissions; one directed revision was integrated. No subagent browser operation or publication occurred.

- Added command-context regressions first: initial import failed before implementation; first implementation passed 7 cases. Final affected core command: `.venv/Scripts/python.exe -u -X utf8 -m pytest -q --tb=short --basetemp=.local/br5 tests/test_bsk_command_context.py tests/test_bsk_error_contract.py tests/test_browser_recovery_boundary.py tests/test_collect_adapter.py`: **68 passed**, 28.53 s.
- Broader caller/controller/budget/legacy UI run: **109 passed, 2 failed**, 634.88 s. The failures are `tests/test_browser.py::test_photography_workspace_entrance[True-1440]` and `[True-390]`: the expected current-page item under navigation `摄影工作区` was absent. UI source was not modified in this task; these failures remain recorded, not waived or claimed passed. Final core rerun covers subsequent transport edits; counts overlap and are not additive.
- Early test attempts hit Windows sandbox temporary-file permission failures. The next run used an explicit per-command exception. A long temporary path also caused an atomic-write filename failure; subsequent runs used short repository-local `.local/br4` / `.local/br5` paths. No assertions or runtime security settings were weakened.
- Stock extension source regression for stalled `Page.enable`: failed as expected (attachment setup never settled). Patch uses existing deadline/read-gate infrastructure for five diagnostic setup methods. Patched three adjacent suites: **154 passed**. TypeScript `--noEmit` and WXT production build: PASS. Installation and real-browser acceptance: **UNVERIFIED**.
- Original installed extension, browser profiles, CLI and daemon remain unchanged. Build, patch, archive hash and rollback are in `patches/browserskill/README.md`.
- Daily service safely restarted using `scripts/terminate.ps1 -NoWait` then `scripts/launch.ps1 -NoOpen -NoWait -SkipExternalServices`. Runtime PID39072 reports the daily source and matches `implementation_digest()`. **All 20 database table hashes match before/after restart**; 29 projects, 1775 assets, 1535 refs, 23 inspirations, 238 study candidates and 4781 events. Database backup is private under `.local/backups/20261030-browser-skill-repair`.

## Remaining acceptance and delivery

Windows Computer Use reported: “Computer Use has been stopped for this turn because it could not determine the current browser URL on Windows with enough confidence to enforce policy.” All further desktop input stopped. Independent source edits, isolated tests, packaging and managed service restart continued. No alternate UI backend, hidden API or browser-profile modification bypassed the stop.

Next required step is loading the prepared local extension in Edge (preserving the original for rollback), then verifying local navigation/sync/read/owned cleanup and real source acquisition. The patch bounds one reproduced initialization failure; it has not yet established recovery of this machine's full control channel. Earlier three-character first-image acceptance remains incomplete.

No commit/push or Notion publication is claimed. Formal delivery is deferred on R3 until installed-browser acceptance is possible; the current transaction and all earlier unfinished transactions retain their identities.

## Installed follow-up and second candidate

The owner loaded the local extension, disabled the original, and explicitly bound further sessions to `bd366854`. Its unpacked directory and background bytes matched the prepared build; daemon/CLI/extension were 0.4.0, protocol1.7. The source confirms the copied DeepSeek Harness text is a generic alternative, not an executor switch; `AntigravityCollectionAgent` remains the library's AI boundary.

Popup delay and automation failure were tested separately. Available memory sampled at260–702MB on a roughly16GB machine, committed-memory utilization93%, and heavy page reads. Photoshop private commitment was about20.28GB (not physical resident RAM). After the owner saved/exited Photoshop, commitment fell first to69% then47%; a windowless Photoshop process initially remained. The owner ultimately confirmed the popup was much faster. BSK session startup improved from13.710s to5.680s; these observations support memory pressure contributing to popup delay, not all automation failures.

The first installed patch still failed local health navigation at34.158s and34.167s. The prior host-managed daemon PID56744 later exited with stale discovery metadata and no observed shutdown reason. It was restored on its verified original port52800 through a managed foreground tool session, PID48184; the same `bd366854` reconnected. Navigation still failed at34.092s. The explicitly authorized foreground test also failed at34.107s; only owned sessions were cleaned up. Direct new-tab creation succeeded but cooperation reported a nonresponding frame. No real collection Job was launched.

Follow-up transaction `01a18c61-2ff4-74d2-8a75-9599189570ff` began before candidate2 edits. Candidate1 is backed up; scoped contract and build receipts remain in `.local/browser-skill-repair-20261030`. The previously unbounded raw debugger attachment is now bounded and fenced against duplicate requests and late publication. The red regression,161 passing adjacent tests,typecheck/build and exact candidate2 artifact are documented in the patch README. The owner has reloaded candidate2; installed validation is in progress. No original, selection or budget modification was performed in this follow-up.

## Diagnostic continuation (2026-10-30)

Candidate2 session `jxsw` returned `cancel_cleanup_timeout`, unknown effects, after34.115s. Its later state read reported session idle expiry; explicit stop found no registered session. Status confirmed no remaining sessions and the same connected `bd366854`. This supersedes the earlier pending installed-test statement: candidate2 did not restore navigation.

Reviewed upstream issue527 (0.4.0 observer capture blocking the session queue), issue452 (browser-specific CDP failure), the actual navigation/attachment/cooperation/dispatcher paths, and previous candidate1/2 evidence. Issue527 involves DSH automatic observation and therefore is not established as this direct-CLI failure's cause. No third speculative timeout was added. Transaction `01a18c8f-0cc5-73e0-8602-c68a7b97b30e` instead instruments pending native method names/times and the dispatcher phase in the existing blocked-operation response. It excludes parameters, results and other sessions' tabs, and preserves ownership, cancellation and single-operation guards. Earlier candidates remain available for rollback.

Two new regressions failed before implementation; five relevant suites then passed222 tests. TypeScript checking and WXT build passed. A first sandbox test attempt failed before running tests because Vitest could not rename its temporary cache; the explicit local execution passed. Tests are synthetic boundary verification, not browser recovery.

The owner reloaded candidate3. Bound session `nnpp` started in3.428s; health navigation still timed out at34.097s. Immediate sync returned the existing settling error **without the new diagnostic field**; owned stop succeeded with no failures. Both sandbox and host reads matched the new background SHA256 `205cfe1c513765bdc03294c574809a7256fd89166d8eae3b8a57a0ac8f1d0a83`; read-only extension metadata confirmed the intended unpacked path. The loaded-code identity is therefore unresolved, not proof of which CDP method stalls.

Prepared candidate3b with the same tested runtime logic, an explicit `localdiag3` build marker returned by existing debug capabilities, and a new background script filename in the local manifest. Rebuilt successfully; archive/install hashes are in `diagnostic-identified-prepared.json`. Next acceptance starts by reading that marker before navigation. No real search batch, original image, database choice, budget or other browser profile was changed. Formal delivery remains pending actual runtime evidence.
