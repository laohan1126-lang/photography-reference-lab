# Ultra independent system audit — 2026-10-01

## Intent recorded before changes

User asks for independently verified information beyond Medium `6218a5f` and High `d29b6d7`, following actual user behavior from search through curation, visual observation, photographic guidance, feedback, future decisions and actual shooting. “不是三个 Bug。是三个如果错了，会让大量工作方向都错误的假设。” “使用越久，它会越懂用户，并帮助用户做出更好的摄影决策。” Distinguish new serious facts, new system explanations, product judgments and refinements of existing findings; choose one next stage if justified. No manufactured findings or large changes for their own sake.

## Boundaries / acceptance

- Worktree `photography-reference-lab-ultra`, branch `codex/sol61-ultra-20261001`, starts at exact High checkpoint `d29b6d7bd5607ba81dd5ee8a8545e911fe72a3ad`. Other checkpoints/worktrees remain untouched.
- No merge, push, production database switch, owner-service stop, paid API, publication or writes to the daily library. Native Windows readonly SQLite/online backup is permitted for evidence; experiments use independent scratch data.
- Recheck current processes/configuration/data and code differences; task documents are leads, not evidence. Record exact probes and actual results. Synthetic fixtures establish behavior only, never visual accuracy or owner preference.
- Trace actual consumers, use discriminating semantic counterexamples, retain evidence and qualify all negative/exhaustive claims by inspected scope.
- If a serious root cause warrants repair, record it first, make the minimum change here, add an actual-failure regression and run relevant checks. An audit with no application changes is acceptable.

## Outcomes

Private receipts are kept under `.local/ultra-20261001/` and excluded from Git.

### Finding recorded before the minimal repair

An isolated API → acceptance → export → actual offline Chromium probe against `d29b6d7` saved an explicit unresolved fall-risk warning and a conflicting verbal cue. Analysis, acceptance and export all returned 200; the raw manifest retained the warning, while the rendered shooting page displayed the cue and “已确认现场卡” without the warning. The online acceptance dialog shows warnings, but the normal card display also drops them. These synthetic inputs prove a consumer omission, not visual accuracy or a real owner's dangerous card.

Git `18b2f30` deliberately removed uncertainty blocking at the user's request. Do not undo that choice. Repair only the information loss: render the saved critical uncertainties beside card instructions online and offline; keep manual acceptance behavior. Expand the existing real HTTP/browser/offline regression to verify visible warning text after acceptance and after offline export. No feedback-model redesign or production mutation is part of this repair.

### Fresh operational facts

- `git worktree list --porcelain`, status and commit/diff inspection: main is Medium branch at `6218a5f`; redteam is High at `d29b6d7`; Ultra and existing xhigh worktrees initially both at High. Medium → High is 17 files, 758 insertions / 426 deletions. Main remains dirty: 11 tracked files have substantive changes after ignoring line endings, plus unpublished collection/pose/sync/Skill experiments. They were read, never adopted or staged here.
- Native Windows CIM + authenticated `/api/runtime` at 2026-09-30 19:01 UTC and final 19:13 UTC: managed parent 30932, serving child 27656, source main `ref_lab/api.py`, database main `data/library.sqlite3`, schema 3, maintenance false. Process start is 2026-09-30 21:54 Asia/Shanghai, preceding the Medium 22:23 commit. This identifies source checkout and data, **not the loaded source SHA**; neither committed checkpoint can be equated with the running process. Browser JS can also be served from subsequently changed files.
- Fresh native readonly online snapshot: 18 projects, 747 assets, 750 refs, 23 inspirations, 2235 events; integrity_check ok, 72 FK errors (24 missing Reference IDs). No queued/running jobs; the process snapshot found no matching collection/sync writer. This is a point-in-time observation, not an exclusive writer guarantee. Antigravity was running; WPS photo viewers held two training-set images, neither proves a collection job.
- All 747 received originals matched SHA, byte length and EXIF-oriented dimensions; all derived previews/thumbs decoded. This run did **not** independently compare every live derivative to deterministic reconstruction. Original fidelity is not camera-original authenticity, crop lineage or visual accuracy.
- Native readonly candidate inventory confirms several 732-asset copies and the newer 742-asset Medium candidate; High `fresh-repair` has 747 assets / 750 refs, FK=0, 2333 events. The original still has FK=72. The alternate import-tool default `D:\AI PROJECTS\photography-reference-lab-data` does not exist; `.local/library.sqlite3` is an empty auxiliary library, not the daily database.
- Final native readonly inspection: 2 cards have nonempty critical uncertainties, 0 accepted cards, 0 reflections. No claim that the owner viewed a dangerous card, performed its instructions or suffered an accident. Event counts remained 2235 across this audit's observations; no owner write was performed.

### Three assumptions and their evidence

1. **A current hash/revision plus a fresh confirmation means feedback belongs to the current image. False; new serious semantic fact.** Native isolated API experiment: image A → explicit A-specific preference/borrow → confirmed sample → replace with different image B → K only → confirm summary. B receives an eligible sample containing A's unchanged notes; A's reflections are included in B's new analysis bundle without their original image/card/context binding. `replace_asset` resets review/card but retains notes/origins/reflections; `_record_feedback` inherits them and binds the new action to B. Confirmation UI renders category summaries, not the per-image evidence details returned in `hypotheses.evidence`. Strict fingerprint checks pass because this is a new, internally consistent action. No downstream personalized ranking contamination was demonstrated; ranking is currently disabled. No owner data affected by this example was established.

   Related **system explanation**, not another serious bug: simply adding a reflection to A changes its full-reference fingerprint, so unchanged image/choice/notes lose current sample eligibility. High explicitly permits conservative invalidation, but this shows mutable view validity and historical evidence validity are different questions. New evidence should preserve which image, project intent and plan a judgment concerns; retaining old records must not silently retarget them.

2. **Confirmation permits removing unresolved doubts from shooting guidance. False; new serious consumer omission.** The before/after real HTTP + Chromium + offline probe shows analysis, raw storage, acceptance and manifest each working, while display omits the warning before this repair. Confirmation is permission, not proof that uncertainty disappeared. Only warning visibility was repaired: 7 added / 3 removed lines across exporter, UI and an existing browser regression. Manual acceptance still succeeds. No uncertainty blocker was restored.

3. **Accumulated curation naturally becomes better photographic decisions. Unsupported; product judgment and extension of High's existing finding, not a new bug.** Fresh snapshot has 225 raw actions across two active sessions, default profile v1 and zero confirmed profile exemplars; no reflections. There are outside-library human index selections, training packages and an uncommitted curator Skill, so this does not mean the owner supplied no feedback. In inspected `ref_lab` consumers, ranking never reads its profile parameter; search/analysis task bundles do not supply an aesthetic model; reflections are stored/displayed but not used to evaluate later recommendations. The outside benchmark path uses keywords/dimensions and some hard-coded absent manifests, not verified visual judgments or real shoot outcomes. No source inspected establishes improved real-world results.

The supported chain is search/import transport → received-byte assets → independent project/global uses → human curation → explicit image review/card protocol → optional confirmation/export. Actual real-image visual accuracy was not audited this round. Long-term feedback recording has a working synthetic API path but no confirmed daily samples. Preference-to-decision and shoot-result-to-next-recommendation loops have not been established.

### High findings that materially hold up

- Independent before/after experiment: same-sized decodable wrong preview, correct original hash. Medium `doctor_ok=true` / backup accepted; High `doctor_ok=false` / backup rejected. This strengthens backup/display evidence at those entry points, not every interactive asset request.
- Native functional regressions independently pass High's stale-confirmation, decision provenance, repeated-sample, cross-project and local fake-vision isolation boundaries. Native collection scope includes the parent-exits-first descendant regression. Native process restart/browser test preserves feedback and rejects a stale summary. These tests establish mechanisms, not visual accuracy, owner preference or complete hard-crash recovery.
- Offline historical comparison independently verifies all 2235 old events preserved in High's recovered copy, all 72 exact orphan rows archived and 40 same-ID/different-payload conflicts against the Medium stale copy. No deleted Reference was fabricated. No residual deleted-ref IDs were found in the inspected JSON consumer tables; that additional-damage hypothesis was rejected.
- **No new severe recovery fact beyond High was found.** Events cannot be used as a replay log even after ID renumbering: both checkpoints' note events omit the note body, and raw SQL writers can bypass events. This is a system explanation/refinement, not a request to add event sourcing. The 26 reported doctor reindexes in High's historical copy were detached → detached revision/time changes, not 26 changed owner choices; a low-priority report refinement, left unfixed.

### One next stage

After the already-required controlled runtime/data adoption prerequisite, choose a **small real shooting feedback loop**, not more automatic analysis, fields or Skills. For a few actual references, preserve the reference image and plan versions, the owner's intended borrowing, actual shooting context/result and the owner's worked/failed/next-time judgment. Explicitly bring that evidence into the next preparation and ask whether it helped. Start with text and existing private assets; no automatic learner is needed to test whether a consumer helps.

This direction was partly anticipated by High. The new reason to prioritize it is that even validated, reconfirmed records can currently change their meaning through normal editing, and even a complete accepted card can lose decision-critical information when consumed. More storage or smarter generation would otherwise amplify poorly attributable evidence. SHA remains a useful byte identity; nothing found justifies replacing it with perceptual deduplication or redesigning K/I/M/X wholesale.

### Actual validation / runnable handoff

All application writes used independent temporary data. Native interpreter: main repo `.venv/Scripts/python.exe -X utf8`, importing the specified audit worktree. Private receipts retain probe scripts and before/after results; no originals, SQLite, runtime secrets or private receipts are staged.

| Exact command / scope | Actual result |
| --- | --- |
| Native High baseline in Ultra before patch: `python -X utf8 -m pytest -q tests/test_library.py tests/test_imports_jobs.py tests/test_workers.py tests/test_operations.py tests/test_personal_library.py tests/test_collection_runner.py tests/test_redteam.py tests/test_data_safety.py tests/test_evidence_boundaries.py` | 141 passed, 1 dependency warning, 56.67s |
| Native after patch: `python -X utf8 -m pytest -q tests/test_browser.py::test_browser_agent_result_accept_and_offline_pack` | 1 passed, 1 dependency warning, 10.48s; real HTTP/Chromium/confirmation/offline file page |
| Native after patch: `python -X utf8 -m pytest -q tests/test_redteam_runtime.py` | 1 passed, 1 dependency warning, 10.66s; actual process stop/restart on temporary data |
| WSL real HTTP/Chromium warning probe, `field_warning_probe.py --repo <redteam>` and `--repo <ultra>` using regression venv | Both exit 0; before warning absent in draft/accepted/offline, after present in all three; acceptance still ready; zero browser errors |
| Native `feedback_probe.py` in independent temporary data | Two completed runs, exit 0; old notes and reflections retargeted to B as described |
| Independent WSL 7 existing provenance/storage/role tests | 7 passed, 1 warning, 2.07s |
| Independent native data-safety + derivative tests | 5 passed, 1 warning, 2.21s |
| `node --check web/app.js`; `git diff --check` | Both exit 0 |

Initial agent probes using default Python failed on missing PyYAML before application initialization; subsequent explicit interpreter probes succeeded. No initial failure was treated as success. The full browser suite and remote CI were not run this round. No fresh live acquisition, real-image AI accuracy, actual shoot, owner aesthetic acceptance, production deployment/rollback, merge or push was performed.

Reproduce the changed path from this branch with the native browser command above and `node --check web/app.js`. The six-module default regression is included in the 141-test baseline. This is an unreleased local audit checkpoint, not production recovery or a learned photography system.
