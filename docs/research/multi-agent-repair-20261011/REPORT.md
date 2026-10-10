# Bounded continuation: CC repair, browser diagnosis and Skill discovery

**Two specified code defects are repaired and independently accepted.** The
experimental project Skill was actually discovered in fresh Codex sessions.
AGY browser integration remains unresolved; overall browser/video capability
is **PARTIAL**. This continuation did not repeat the three-party research run,
watch new videos, modify formal course data or merge into a daily-use branch.

Verified remote baseline: `07e4ec1fc8d979a07423425b75840cced9a6f2fd` on
`codex/research-code-verifier-pilot-20261010`. Isolated branch:
`codex/research-code-verifier-repair-20261011`, worktree
`D:/AI PROJECTS/photography-reference-lab-multi-repair-20261011`.

## A — actual CC/MiniMax repair

Reused the existing `codex-cc-minimax-dispatch` Skill and audited invocation
helper. Native Claude Code **2.1.220** made two real subprocess calls:

| Call | PID | UTC start–end, 2026-10-10 | Exit / terminal |
|---|---:|---|---|
| Readiness | 49060 | 17:10:45.722340–17:10:48.921577 | 0 / `CC_MINIMAX_READY`, no error |
| Bounded repair | 35920 | 17:11:35.239301–17:12:13.739350 | 0 / success, no permission denial |

CC Switch's selected provider and existing settings matched **MiniMax**,
`https://api.minimaxi.com/anthropic`, model
`MiniMax-M3.1-Flash-Preview`; local routing/failover were off. The parent had an
inherited endpoint override, so only the child's `ANTHROPIC_*` environment was
rebuilt from the already selected user settings. Effective endpoint debug and
the actual responses corroborated that route. Configuration and parent
environment were unchanged. Service-reported model identity is not weight-level
attestation; the SDK's `firstParty` label alone is not evidence of Anthropic use.

The repair exposed only Read/Edit/Write/Glob/Grep, exact
`Edit(./web/learning-gateways.js)` write permission, and explicit protected-area
read denials, with `dontAsk`, `--safe-mode` and no session persistence. No shell,
network, Agent, Git or Publisher tools were exposed. No permission bypass was
used. Although `--max-turns 12` was supplied, the terminal reported 13 turns;
the report retains the actual value without interpreting its counting scheme.

CC itself executed two successful Edit calls (`call_8cae5b303801416287061d02`,
`call_fb3a1be93ca84c83a0954232`). Its business patch is **12 additions / 3
deletions**, only in `web/learning-gateways.js`:

- `speechBinding` rejects registered `simulated=true`, `verified=false`, and
  `status=unverified` records before matching source, time, speaker and transcript
  can grant verification.
- Quote rendering accepts only the three known string kinds. Malformed objects
  are not coerced into property keys and degrade to the existing paraphrase
  presentation; valid kinds retain their behavior.

Root did not replace CC's business patch. A separate code-owner review found no
additional issue. **Directed CC rework this turn: 0.** The prior pilot's two
reworks are historical, not new calls in this continuation.

## Independent acceptance

The independent Codex tester received the user requirements, interface and
candidate location without CC's implementation conversation. It reused the
previously frozen originals outside CC's workspace. Their three SHA256 hashes
and the tracked development test bytes remained unchanged. Before CC, the same
four original nodes failed; after CC they passed.

| Actual check | Result |
|---|---|
| Original three registry-state nodes + malformed-object node | 4 failed before; **4 passed after** |
| Complete video evidence suite | **81 passed** |
| Frozen independent HTTP/Chromium acceptance | **5 passed** |
| Existing course UI regressions | **19 passed** |
| Course/backend gateway regressions | **12 passed** |
| Root combined core/collection/personal/course regression | **154 passed** |
| JS syntax and whitespace diff | exit 0 |

Root ran two pytest batches (81 and 154); Verifier separately ran the baseline
four-node batch and five post-repair batches. Publisher's required checks are a
separate delivery-stage record, not included in these counts. Existing pytest
warnings concern Starlette/httpx, not failed assertions.

Actual Chromium checked desktop 1440×1000 and mobile 390×844: all three bad
registry states stayed unverified; malformed B-layer content opened safely as
paraphrase, with no page error. Four-layer and legacy readers had no horizontal
overflow. Reading produced zero learning write requests and equal before/after
learning state. The legacy `course-distance` caption and original timed link
survived removal of optional evidence fields.

**Limit:** image pixel loading in the isolated environment remains unverified:
registered images had natural width zero or incomplete loading, and a final
hidden-image scroll experiment timed out. The Verifier did not read private
media or infer its cause. Its initial observation-script route-binding error
and later strengthening of malformed-layer capture were changes to a local
capture copy, not frozen tests or CC implementation rework. See the byte-identical
[independent report](VERIFIER_REPORT.md), including all failed capture attempts.

## B — independent AGY diagnosis

Root read the previous `RESULT.md` and actual browser tool error. AGY **1.3.3**
looked for `DevToolsActivePort` in Chrome's ordinary default data directory; no
historical AGY Chrome launch command was captured. The currently running normal
Chrome had no debugging or explicit profile flags. Chrome **154.0.8037.98** is
subject to the documented Chrome 136+ default-directory debugging restriction,
but that alone is not proven to explain the old missing file.

Two owned Chrome subprocesses used fresh empty profiles and loopback CDP without
cookies or disabled security. CDP connected in both. The second rendered a
public document with HTTP 200, title, nonempty body and an inspected screenshot.
Both diagnostic helper assertions failed because they assumed an `h1` or title
phrase in the changed document body; those failures remain recorded. Public
access is supported by the actual protocol/content evidence rather than a helper
exit or self-reported success.

The official CLI/settings references and installed flags did not establish a
supported selector for the built-in `/browser` profile/CDP endpoint. Root
therefore did **not** run AGY again. The remaining layer is **AGY integration /
target selection, before website login**. This is not proof that an undocumented
capability cannot exist. Prior YouTube bot/login challenge and B&H HTTP 403 are
separate, **not retested** outcomes. No wider authorization, real-profile debug,
cookie copying, proxy/config change or challenge bypass occurred. Details and
official source links: [AGY_BROWSER_DIAGNOSIS.md](AGY_BROWSER_DIAGNOSIS.md).

## C — experimental project Skill and real discovery

Created `.agents/skills/research-code-verifier-orchestration/SKILL.md`, reusing
the proven AGY CLI and CC Skill. It covers authorized separate worktrees,
actual overlapping subprocesses, pre-frozen independent acceptance, bounded
rework and parent-owned delivery. Browser connection and new video evidence
are conditional. No global install, new framework or blanket AGENTS rule.

Prior raw parallel logs and live observation were reviewed: PIDs 6344/61072
overlapped **85.993077 seconds**, and 60776/54000 overlapped **122.908961 seconds**.
Those are the previous pilot's real calls, not freshly repeated research. Its
77-pass/4-fail product acceptance and source limitations remain historical facts
in the candidate's limits; this continuation now repairs those four failures.

Four fresh, ephemeral Codex CLI **0.159.2** sessions used separate local working
directories and default skill discovery, read-only routing, no resume and no
external AGY/CC launches. They received neutral instructions to inspect relevant
Skills only; the implicit request contained no Skill name/path. Existing explicit
external-agent authorization was retained, but execution was prohibited in this
route-only check. Model/default reasoning were not overridden.

| Prompt | PID | Actual candidate read | Routing decision |
|---|---:|---|---|
| Explicit `$research-code-verifier-orchestration` | 40792 | completed command `item_4`, exit 0 | Selected |
| Natural-language video research + teaching display + independent acceptance | 45520 | `item_5`, exit 0 | Selected |
| CSS spacing fix | 43812 | `item_7`, exit 0 | Rejected orchestration |
| Large photography research without engineering | 31728 | `item_4`, exit 0 | Rejected orchestration |

All four sessions ended with exit 0 and `turn.completed`. Automatic CLI
reconnect/time-out messages occurred before completion; no controller restart
was used. The candidate SHA256 stayed
`f4737318dfd98eea4b0eb9d1760232285d51af12480c73630b6b0ea686f36627`.
The negative sessions **also read the body to evaluate its exclusions**; they
did not launch three-party work. Thus selection boundaries passed this sample,
but avoiding unnecessary reads remains unproven. One implicit case establishes
an actual discovery event, not a reliable probability across future tasks.
The skill-creator validator passed under the shared Python with UTF-8 mode.

## Resources, protection and next reuse

CC reported input/output/cache-read tokens of 1128/14/203 for readiness and
51722/4933/127232 for repair. SDK cost fields were USD 0.0060915 and 0.445551,
**estimates, not bills**. Invoice/actual quota consumption: **unknown**. No
unexpected provider switch was observed. Discovery input/output tokens were
145042/2019, 99989/1880, 100775/1437 and 99727/1427, with considerable cached
context; this is observable routing overhead, not a demonstrated efficiency
advantage. AGY model calls this turn: **0**; manual second-app handoffs: **0**.

Protected settings, frozen standards and main `web/app.js` hashes match the
before values. Main HEAD and prior dirty status were preserved. Tracked tests,
formal course JSON/CSS, private data and Publisher source/state were not manually
edited. Reports and local raw evidence are separated; profiles, screenshots,
credentials and test databases are not committed. Retain local evidence/worktree
for review; future cleanup must avoid following the ignored `.venv` junction.

Next real reuse should test implicit routing with varied wording and a smaller
skill catalog, supported AGY isolated-browser attachment if documented, and
genuine accessible video material. The present repair does not establish those
capabilities or a cost/speed benefit over Codex alone.

Machine records, exact commands, tool IDs, process times, hashes and route decisions:
[EXECUTION.json](EXECUTION.json). Formal publication is only this isolated task
branch; commit/push, remote SHA and Notion read-back are reported separately by
the canonical Publisher receipt after sealing. No main merge or deployment.

Replay from the isolated worktree with the existing shared environment:

```powershell
& '.\.venv\Scripts\python.exe' -X utf8 -m pytest -q tests/test_video_evidence_display.py
& '.\.venv\Scripts\python.exe' -X utf8 -m pytest -q tests/test_learning_course.py tests/test_learning_gateways.py tests/test_learning_gateways_ui.py tests/test_learning_course_ui.py
node --check web/learning-gateways.js
```

For frozen acceptance, use the external Verifier originals and
`VERIFIER_TARGET_ROOT` as recorded in `VERIFIER_REPORT.md`; do not edit them to
fit a new implementation. These checks create only isolated temporary fixtures.
