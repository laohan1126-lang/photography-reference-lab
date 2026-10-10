# Research / code / independent verification pilot — PARTIAL

**Actual concurrent external dispatch is proven. Full research and implementation
acceptance is not.** The experiment took place in this one Codex controller
session; the owner did not open another application or transfer files manually.

## Isolation and baseline

Remote `codex/cc-minimax-delegation-pilot-20261010` was freshly checked at
`c217f81f366a28eee5eb32c271fcf2e6f64ae346`. Four separate worktrees were created
from that commit: integration, CC, AGY and protected Verifier. Final delivery
branch: `codex/research-code-verifier-pilot-20261010`.

AGY could write its research directory; CC received exact-file frontend/test edit
permissions; the independent Verifier owned separate frozen tests. Root handled
public evidence integration and delivery. No two external agents edited the
same product file, no ordinary course/main branch was replaced, and original
data/settings were preserved. Publisher baselines and immutable contracts were
declared before edits, with exact protected external paths.

Main HEAD stayed `805c289beaa2a75b75a8a888fbd1f190baa1dc27`; a comparison to its
original Publisher snapshot found **zero changed recorded paths**, including
all pre-existing dirty files. Full settings/protected hashes are in EXECUTION.json.
The isolation worktrees are retained for review, not silently deleted.

## Genuine external process overlap (UTC)

| Process | PID | Start | End | Exit / terminal |
|---|---:|---|---|---|
| AGY initial | 6344 | 15:59:30.720170 | 16:05:50.348211 | root stopped / 4294967295, no terminal |
| CC implementation | 61072 | 15:59:30.773623 | 16:00:56.766700 | 1 / error_max_turns |
| AGY recovery | 60776 | 16:05:50.505226 | 16:11:10.209360 | root stopped / 4294967295, no terminal |
| CC rework 1 | 54000 | 16:05:50.592417 | 16:07:53.501378 | 1 / error_max_turns |
| CC rework 2 | 18056 | 16:12:15.900097 | 16:13:16.629895 | 1 / error_max_turns |

All intervals begin on **2026-10-10 UTC** (local China time crosses October 11).
Initial overlap: **85.993077 seconds**. Recovery/rework overlap: **122.908961
seconds**, including actual AGY tool activity. Both child launches preceded either
wait; root also observed initial PIDs simultaneously alive. This is neither a
serialized queue nor a simulated orchestrator.

The AGY recovery reused an existing proxy only in that child environment.
Read/search/write events actually executed despite nonfatal hook warnings.
Root prematurely terminated it after misreading those warnings, and corrected
that assessment from stream events. No successful AGY terminal state is inferred.

## Independent verification and actual repairs

The Codex Verifier was spawned with **no inherited implementation conversation**.
It received the original user objective, existing public interfaces, architecture
and data-protection rules, not CC's design or expected outputs. It froze its
standards at **15:59:09 UTC**, before external launches at 15:59:30.

| Frozen original | SHA256 |
|---|---|
| ACCEPTANCE.md | 857b11c0014203c519130767ef14add01874d6ac576c0bbce882418671be08e7 |
| test_video_evidence.py | 6f6109a5d73db640b64d7533aeff702482854c3d0251df497cff7039e1bcad0e |
| freeze.json | 4f284725687451be7fa935516e38db1ab68225018ef06fd57358e1aa3cfbd678 |

Every development call checked the protected hashes. Byte-identical copies are
delivered under [acceptance/](acceptance/). Added final semantic/browser checks
are separate from the immutable originals. Their actual results and screenshots
are in [VERIFIER_REPORT.md](VERIFIER_REPORT.md); they do not certify external
video facts or human teaching quality.

Final independent runs: frozen Chromium tests **5 PASS**; the dedicated evidence
suite **77 PASS / 4 FAIL**; existing course UI checks **19 PASS**. Supplemental
real-browser captures at 1440×1000 and 390×844 independently reproduced both
remaining errors. The capture script's exit 0 means observations were saved,
not that the deliberately exercised failure states passed acceptance.

Two **actual external CC rework calls** followed independent/root observable
failures. CC repaired several identity/status/malformed-input boundaries, but
three calls exhausted their turn budgets. After the two-round limit, a Codex
tester repaired only the CC development harness wiring, not business code.
Its final result is **77 passed / 4 failed**: untrusted registered B records
still gain verified status, and one malformed quote kind crashes the renderer.
The red regression tests are retained; this is not an accepted implementation.

Root additionally rejected AGY's swapped prior author identities, unsupported
search-derived teaching claims and incorrect DENIED labels. No new-video content
was admitted. Real display examples use eight existing registered stills reopened
this turn, explicit unknown speech, narrowly sourced optical explanation and
project suggestions. See [AGY_EVIDENCE.md](AGY_EVIDENCE.md).

## Commands and reproducible verification

Actual existing regression run in the integration worktree:

```powershell
$env:PYTHONPATH = (Get-Location).Path
.venv/Scripts/python.exe -X utf8 -m pytest -q `
  tests/test_library.py tests/test_imports_jobs.py tests/test_workers.py `
  tests/test_operations.py tests/test_personal_library.py `
  tests/test_collection_runner.py tests/test_learning_course.py `
  tests/test_learning_gateways.py tests/test_learning_gateways_ui.py `
  tests/test_learning_course_ui.py `
  --basetemp .local/multi-pilot/final-regression-tmp
```

**154 passed**, one existing Starlette deprecation warning, 140.88 seconds,
exit 0. Earlier targeted learning data checks were **12 passed**; the Verifier's
preimplementation UI baseline was **19 passed**, and its frozen feature tests
initially found **2 failed / 3 passed** (missing evidence labels).

```powershell
.venv/Scripts/python.exe -X utf8 -m pytest -q --tb=short tests/test_video_evidence_display.py
node --check web/app.js
node --check web/learning-gateways.js
node --check web/learning.js
.venv/Scripts/python.exe -X utf8 tools/build_photography_atlas.py --check
git diff --check
```

Dedicated evidence tests: **4 FAIL / 77 PASS** (two remaining defect classes).
All three actual JS syntax checks passed. Builder `--write` was executed;
`--check` passed with 14 domains, 71 modules, 247 skills, 205 sources. An initial
syntax attempt referenced nonexistent `web/learning-course.js` and failed;
the actual existing file `web/learning.js` was then checked. No failure is counted
as a pass based on the later command in a shell sequence.

## Cost, gains and limitations

- External calls: **CC 4** (readiness + implementation + two reworks), **AGY 2**.
  Partial AGY step usage and CC's per-call tokens/SDK estimates are recorded;
  actual invoices, remaining quota and unexpected charges are **UNKNOWN**.
- No observed MiniMax supplier switch, broad shell permission, global config
  edit, private database read or user-mediated application handoff.
- Useful result: the controller can dispatch different external CLIs concurrently,
  preserve independent frozen criteria, integrate real edits, detect defects and
  request bounded external rework within a single Codex session.
- Extra cost versus Codex-only work: provider/environment auditing, worktree
  isolation, CLI tool/turn limits, raw-log review, failed network/hook diagnosis,
  repeated model context, and repairing the external model's test harness.
  This run does not establish a speed or cost advantage.
- Missing result: new verified continuous video/timed audio evidence, successful
  development terminal states, and complete hostile-data acceptance.

## Skill decision and next reuse

No `research-code-verifier-orchestration` candidate was created: actual research
and implementation acceptance did not reach the user's success condition.
The existing CC dispatch Skill was reused, not replaced with a new framework.
Explicit/implicit/negative/boundary Skill-discovery trials are **NOT_RUN** because
the candidate-creation prerequisite failed; automatic natural-language selection
has not been demonstrated. No global Skill or AGENTS trigger rule was installed.

Before attempting another real reuse, verify a legal accessible continuous video
source, correct the two remaining evidence-boundary defects through a separately
authorized bounded task, and distinguish hook warnings from fatal tool failures.
Then repeat independent acceptance before testing Skill discovery.

Git publication and Notion synchronization are separate delivery operations.
This isolated branch is authorized as a **PARTIAL checkpoint**; it is not merged,
deployed or labelled FULL. Canonical Publisher receipts and independently checked
remote SHA determine actual publication, not this pre-publication document.

The main workspace also has an immutable transaction anchor but no owned code
edits. Read-only inspection confirmed an existing active session mapping there;
canonical `bind-existing` requires an absent mapping and cannot overwrite it.
No checkpoint or pointer is edited manually. Its separate anchor must be deferred
with the real isolated-worktree receipt as dependency evidence; it cannot justify
a commit to the protected ordinary branch or another publication attempt.
