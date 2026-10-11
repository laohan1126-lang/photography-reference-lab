# Rewrite the two photography courses around field decisions

## Owner intent and fixed scope

“请你从架构上调整而不是打补丁，重新使用三agent工作流完整重写有问题的课程。” The owner selected both Action Directing and Forward-leaning Sword / Low Viewpoint / Head-body Proportion. Preserve the twelve useful perspective notes as material.

The learning outcome is a better next photographic decision: identify a visible problem, choose one adjustment, give an executable direction, and judge the next image against the intended expression. Source audit remains available without interrupting every instruction.

## Baseline, boundaries and delivery

ROOT branch `codex/course-field-architecture-20261011`, initial HEAD `fc6290cc4978529fdd9f58ed6cea02bab736de8a`. Canonical Publisher transaction `01a12ae2-f669-7091-91e9-74a93554cf22` started after branch selection and before edits; immutable R1–R4 declared. Existing staged/unstaged work, unpublished earlier courses, private media, data and settings are preserved. Only ROOT integrates and publishes. Publication cannot adopt baseline-dirty paths under the canonical ownership gate; actual receipt will be reported independently.

Keep canonical skill/course IDs, twelve notes, private records/revisions, older gateways and the original research/history. No production deployment, main merge, paid endpoint change, image regeneration, secret/image/database commit or unrelated cleanup.

## Blueprint and semantic review before implementation

Stack: Python/FastAPI, generated JSON, plain JavaScript/CSS, existing gateway/course dialog. Reuse media identity, source registry and route/state ownership. Inspect the shared content/reader boundary that promotes audit fields into compulsory prose; replace that boundary with a common decision-oriented course structure used by both rewrites, rather than per-course exceptions or text substitutions.

ROOT owns course composition/integration and this task record. Real AGY owns research materials in a separate private worktree; real Claude Code owns the bounded shared model/builder/reader/test implementation in another worktree. Fresh independent Verifier owns its standards and evidence in a third worktree. Original processes and screenshots stay private; publish a compact evidence summary rather than another pile of test receipts.

Reviewed prior course reconstruction, action-directing task/fact/acceptance records and Publisher histories `01a1293a-29b3-7582-8a42-cbd900f40ac9` / `01a129b5-9769-7b80-b4c9-a9a7dae0730a`. Root cause: provenance and process completeness are treated as a visible teaching sequence, while specific field operations and continuous directing demonstrations remain underdeveloped. Keep truthful provenance and compatibility. Remove mandatory repeated audit rows from the new courses' main reading flow. Redesign the course contract, research depth and observable acceptance together.

## Observable acceptance and execution

Independent standards are frozen before substantive implementation. Two-course content must support real images, relevant continuous video-process navigation, actionable controls/utterances/stopping points/checks, conditions for numeric guidance and concise reasons. Synthetic fixtures validate software only. Each selected teaching image is actually opened. Limit directed repair to two rounds; preserve failed evidence and do not relax the standard after seeing a candidate.

Use appropriate existing learning builder/schema and legacy-reader/state/UI regressions, plus real desktop/mobile reading of both new courses. Record exact actual commands/results below. Aesthetic preference and learning transfer await the owner's reading and reshoot.

## Outcomes

Both courses are fully rewritten around the shared `field-guide-v1` contract. A field recipe contains the problem, setup, spoken direction, visible stopping point or conditional practice parameter, actual image references, success/failure checks, cost and a short reason. Continuous video navigation is a separate ordered block. Case/source audit is available in closed details; it is not the compulsory lesson sequence. Python validation, browser preflight and Markdown export share this boundary. Existing conceptual gateways retain their teaching and private-write behavior.

Action Directing now starts with real Cosplay face/sleeve/sword relationships, includes static and three-second slow-action rounds, near-eye continuous focus or stop-and-refocus, and separate motion-blur/focus failure branches. The sword course separates equipment bulk, cropping, foreshortening, near/far scale and optical distortion; its distance experiment specifies equivalent 50mm, chest-plane 2→3m and half/three-quarter framing as course practice starting conditions. Height, pitch and pose are changed in separate rounds, with a no-retreat alternative. Both include an unseen real-image exercise before a closed explanation. A verified short-dagger comparison remains unavailable and is stated where relevant rather than filled with another weapon's evidence.

The canonical entries are `docs/research/photography-atlas/action-directing/COURSE.json` and `GATEWAYS.json`; their readable exports are `action-directing/MODULE.md` and `SWORD_FIELD_GUIDE.md`. Generated web payloads match these sources. The original three gateways, twelve perspective notes, skill-tree bytes, historical materials, private records and unrelated working-tree/index content are preserved.

Real installed AGY performed research in its isolated worktree; real Claude Code performed scoped implementation in another. AGY's source-domain denial was resolved only after the owner's explicit `read_url(cosplaymode.net)` authorization, with backup and semantic comparison. Other provider/settings files remain byte-identical. Both AGY runs exited 0; both CC runs hit the turn limit and exited 1 while producing actual scoped edits, so process exits are not presented as implementation success. ROOT integrated and corrected the returned work. First-round failures remain recorded; two directed repair rounds were used without relaxing the frozen standard.

The independent Verifier passed all fourteen frozen product criteria, including actual pixels, continuous playback, desktop/mobile reading, attribution, generated outputs and private-state preservation. It independently watched the cited 65–89s Adler and 98–137s Manny intervals; neither an entire-film watch nor dialogue transcription is claimed. Its final candidate manifest SHA256 is `b176467cd67798fb0125f19164c335b7c28821ea50ffa90aa7d3b3cd872295ec`; criteria SHA256 remains `4d6eefb75c5274b3ba3f76ed892631b6837677bf890c264577c42d2f553a40ed`. A fresh Tester used only the real UI, wrote two answers before expanding the explanations, and retained a conditional alternative in the sword exercise. This verifies an executable transfer exercise, not the owner's reshoot or aesthetic acceptance.

Legacy reading regression exposed a genuine shared lifecycle defect: rebuilding a closed reader discarded settled photo/error layout before restoring its scroll offset. ROOT preserves observed media presentation by exact URL and restores responsive geometry before the reading position. Tests cover successful and failed images with browser cache disabled, both viewports, exact chapter coordinates, independent drafts, focus/history and delayed-save ownership. The original failure and unsuccessful dimensions-only attempt remain in private evidence; neither timing sleeps nor looser position assertions are the fix.

Actual verification (Windows repo-local Python, isolated temporary data):

- `python -X utf8 tools/build_photography_atlas.py --check` and `python -X utf8 tools/build_action_directing.py --check`: PASS. The independent Verifier re-rendered both Markdown exports and compared exact bytes: PASS.
- `python -X utf8 -m pytest tests/test_field_guide.py tests/test_learning_course.py tests/test_action_directing.py tests/test_learning_course_ui.py tests/test_action_directing_acceptance.py -q --basetemp .local/course-field-rebuild/final-course-tests`: 75 passed. Unchanged model/validation evidence is reused; subsequent course and reader changes have the fresh reading checks below.
- An earlier 112-test legacy run returned 109 passed / 3 failed: two obsolete whole-course/source-count assumptions and the real returning-reader position bug. Updated contract checks and the final affected UI run close these failures; the failed run is not labelled green.
- `python -X utf8 -m pytest tests/test_learning_gateways_ui.py tests/test_learning_course_ui.py tests/test_action_directing_acceptance.py -q --basetemp .local/course-field-rebuild/final-reader-regression`: 24 passed, 156.78s, exit 0. This is also the runnable focused regression for the final reader.
- `python -X utf8 -m pytest tests/test_learning_gateways.py -q --basetemp .local/course-field-rebuild/final-legacy-contract`: 6 passed, exit 0. `node --check web/learning-gateways.js`, `node --check web/learning.js` and scoped `git diff --check`: PASS.
- Independent final checks: 77 model/course/contract tests passed; six final media-position/failure/delayed-save tests passed; both courses at 390×844 and 1440×1000 read through actual HTTP with no overflow, JavaScript exception or private write. Original image review and browser/video evidence are separate from synthetic software fixtures.

## Delivery boundary

The original canonical Publisher transaction remains the only delivery identity. Read-only delivery audit finds exactly 21 owned changed paths, unchanged HEAD/index, and no unrelated repository/provider changes. Fourteen owned paths were already dirty at the immutable baseline; preexisting unrelated staged work also remains. The Publisher ownership gate does not permit adopting that work or recapturing a late baseline. No manual commit, push, new transaction, main merge or production deployment is used to bypass it. Engineering/acceptance are complete; formal Git delivery must report the actual seal/finish receipt under transaction `01a12ae2-f669-7091-91e9-74a93554cf22`, with Git and Notion states separate. Owner reshoot and personal preference remain unverified.
