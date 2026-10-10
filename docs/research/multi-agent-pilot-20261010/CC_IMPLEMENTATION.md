# Claude Code / MiniMax implementation — PARTIAL

Root actually started **four** native Claude Code 2.1.220 subprocesses. Root
did not substitute its own business-code repair. Final JS/CSS bytes match the
CC worktree exactly. Actual process/tool records are in [EXECUTION.json](EXECUTION.json).

## Supplier proof and protected configuration

Read-only CC Switch/user-settings audit established selected provider **MiniMax**,
direct endpoint `https://api.minimaxi.com/anthropic`, configured model
`MiniMax-M3.1-Flash-Preview`, local routing/failover disabled, and matching provider
environment. Every child's debug log confirms the non-Anthropic endpoint and
`/anthropic/v1/messages` request route; JSON reports that same model.
This proves the selected/requested route, not private backend implementation.
The SDK's generic `provider: firstParty` label is not treated as Anthropic proof.

The parent had an unrelated ANTHROPIC_BASE_URL override and a present auth token.
Each child's environment removed inherited ANTHROPIC_* overrides and supplied
only the already selected user-provider settings. No key/token or authentication
file body was printed. No global provider/proxy/auth/settings change occurred;
before/after settings and protected test hashes match.

Minimal real readiness response: `CC_MINIMAX_READY`, exit **0**, `is_error:false`.
Each development call exited **1**, `error_max_turns`, 20-turn budget (JSON counts
21). Edits genuinely occurred before the terminal error; none is called a
successful completed CLI session merely because files changed. Stderr was empty.

## Actual bounded invocation

Reused the baseline project's `codex-cc-minimax-dispatch` Skill and route audit.
Each fresh development session ran in the **CC-only worktree**:

```powershell
claude -p '<bounded task or observed rework failures>' `
  --output-format stream-json --verbose --max-turns 20 `
  --permission-mode dontAsk --safe-mode --setting-sources user `
  --tools Read,Edit,Write,Glob,Grep `
  --allowedTools 'Edit(./web/learning-gateways.js)' `
    'Edit(./web/learning-gateways.css)' `
    'Edit(./tests/test_video_evidence_display.py)' `
  --no-session-persistence --debug-file '<private local log>'
```

Exact disallow rules additionally excluded credentials/global settings, owner
data, the AGY worktree and protected Verifier originals (see EXECUTION.json).
No shell/Bash/MCP/Agent tool, arbitrary commands, commit, push, Publisher mutation
or skip-permissions access was granted. Development uses explicitly simulated
fixtures with legal sample video IDs and actual UTF-8 fixture hashes.

## Actual product changes by CC

- `web/learning-gateways.js`: optional `video_evidence.layers` renderer, separate
  A/B/C/D labels and statuses, source/time/media binding, explicit uncertainty,
  supported quote kinds, registered speech-record checks and safe text/links.
  Existing case/playback renderer and no-new-field legacy path remain usable.
- `web/learning-gateways.css`: small wrapping evidence cards for desktop/mobile.
- `tests/test_video_evidence_display.py`: CC wrote the first development harness.
  Its probe was unreachable after `return`, and several fixtures were miswired.

Root integrated CC's final JS/CSS byte-for-byte, added evidence metadata to five
existing cases, appended a narrowly scoped primary source and regenerated the
existing atlas with its standard builder. No backend/private-state code changed.

## Two actual controller-directed rework rounds

1. First implementation could equate different YouTube `v` identities, overclaim
   author speech and independently verified explanations, and crash on malformed
   fields. Root supplied observable failures to a **new real CC call**. CC added
   identity checking, conservative status rules and a development test file.
2. Review of the changed candidate found insufficient registered-speech binding,
   missing method/interval validation and malformed field handling. Root supplied
   those failures to another **new real CC call**. CC changed JS eleven times but
   did not repair its test harness before hitting the turn budget.

After the two-round limit, a separate Codex tester corrected **test wiring only**:
probe placement, payload routing, legal IDs, interval URL assembly, array indices,
multi-entry inputs, fixed-footer assertions and actual HTML-vs-escaped-text checks.
It preserved negative requirements; no frozen Verifier original or business JS
was edited. An unsupported transcript-SHA business requirement was not invented.
This is real extra controller cost, not a CC-authored passing test claim.

Actual final development suite: **77 passed, 4 failed**. The four failures cover
two unresolved **ERROR** defects:

- Registered B speech records marked `simulated:true`, `verified:false` or
  `status:unverified` still produce `verified` (three independent negative cases).
- `quote_kind:{toString:null}` throws TypeError in `evidenceQuoteHTML`, preventing
  subsequent D entries from rendering (one malformed-input negative case).

These tests remain failing without skips or weakened assertions. No third
automatic rework, local business-code workaround or production acceptance is
claimed. This branch is a **PARTIAL experiment checkpoint**, not a release.

## Resource record

| Call | PID | Exit | Input / output / cache-read tokens | CLI USD estimate |
|---|---:|---:|---|---:|
| readiness | 49712 | 0 | 1110 / 14 / 203 | 0.0060015 |
| initial implementation | 61072 | 1 | 43633 / 10804 / 576964 | 0.776747 |
| rework 1 | 54000 | 1 | 48210 / 26126 / 556785 | 1.1725925 |
| rework 2 | 18056 | 1 | 29477 / 10688 / 413634 | 0.621402 |

Amounts are SDK estimates, **not verified MiniMax invoices**. Actual billing,
remaining quota and unexpected fees are **UNKNOWN**. There was no observed
provider switch. No user opened CC/CC Switch or moved files manually.
