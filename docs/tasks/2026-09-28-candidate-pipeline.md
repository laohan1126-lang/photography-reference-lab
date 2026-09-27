# 2026-09-28 Candidate pipeline development loop

## Intent recorded before implementation

User: SEARCH -> IDENTITY PREFLIGHT -> QUALITY PREFLIGHT -> CURATION/RANKING -> HUMAN K/I/M/X -> SESSION SUMMARY -> VERSIONED AESTHETIC PROFILE. AI analyzes and ranks; the owner decides. Preserve implementation autonomy within the existing independent Asset / Discovery / Project-use / Inspiration design.

Authorized product branch: `codex/reference-library-rebuild`.
Observed starting remote HEAD: `18b2f308ecdbcb9da6608279bf13c65a80e29235`.
Compared `a947cddbc795a24f7482bc049d6ab92a13e7fbf6` to that HEAD: five commits ahead, including one-click collection and analysis additions.

## Initial observations (not completion claims)

- README and architecture describe an Agent-owned adaptive BrowserSkill task-package workflow. The new `run_browser_collection_job` instead runs a fixed Xiaohongshu-then-Pinterest DOM image collector and falls back silently to headless Pinterest.
- `find_bsk_cli` contains a specific Windows user name and WSL path. Browser startup assumes PowerShell, an Edge extension ID and a daemon port.
- Browser subprocesses generally lack process deadlines and return-code validation. Multiple broad exception handlers discard failures; navigation failure may still lead to evaluating stale page content.
- Exact-character discovery is inferred from the presence of `cos` in query text; Pinterest candidates are unconditionally transferable. Neither is visual identity evidence.
- Completion uses accumulated `imported_ids`, not verified completion of this execution or candidate quality. No candidate-level identity/quality preflight is performed in this new collector.
- The container has no existing checkout or user database. Attempted `git fetch origin` failed: `Could not resolve host: github.com`. Authorized GitHub read/write API is available. The owner’s local working tree and uncommitted changes are therefore UNVERIFIED and must not be touched.

## Planned scope

1. Restore source-independent, adaptive Agent acquisition with explicit capability checks, execution evidence and honest blocked/partial status; no silent browser fallback or hard-coded user paths.
2. Add versioned identity context and candidate-level prediction/quality evidence distinct from human choices and field-card VisualReview. Keep filtered/uncertain/transferable candidates recoverable, never delete their assets.
3. Provide explainable ranking across task relevance, photographic usefulness, personal preference and exploration, without an overall aesthetic score or automatic choices.
4. Record append-only screening actions and natural screening sessions. Finish a session, inspect a grounded hypothesis, accept/edit/decline it, and optionally publish a global versioned aesthetic profile. I is strong global positive; K is task-first/weaker; M is neutral; X is not aesthetic-negative without explicit supporting evidence.
5. Preserve old asset SHA identities, choices, inspirations, discoveries, cards, reviews and notes using atomic, backed-up, repeatable migrations. No destructive tests on ordinary LAB_DATA_DIR.
6. Add failure-mechanism regressions; update README, ARCHITECTURE, WORKER_PROTOCOL and regression instructions to match actual behavior.

## Explicit non-goals and prohibitions

No paid standalone model API, mandatory new ML infrastructure, automatic K/I/M/X, aesthetic hard-delete, nine-site crawl quota, access-control bypass, cookie export, guessed CDN URLs, user data reset, main merge, force push, public deployment or Notion write. Do not establish a Golden Path now. Arima Kana and Kamen Rider Durendal are live acceptance cases only, not approved Golden Paths. Do not claim either character identity from its search context.

## Verification plan

- First run unchanged-code baseline and preserve failures before implementing. Historical CI success is not a fresh baseline.
- UNIT: identity/quality gates; ranking/exploration; feedback semantics; profile provenance and rollback; process failure classification.
- INTEGRATION: candidate import/restore, session lifecycle and idempotence/conflicts; schema 2 upgrade/rollback/backup; old library invariants.
- BROWSER/E2E: existing real HTTP/Chromium workflows plus visible new screening-session/profile flows with clearly labelled synthetic fixtures.
- LIVE EXTERNAL VALIDATION: Arima Kana / Oshi no Ko and the owner’s real Kamen Rider Durendal context, using authorized local BrowserSkill, actual independent downloaded images and visual inspection. Do not fabricate aliases, canonical visual facts, model evidence or source availability.
- Existing and new regressions, JavaScript syntax, Python compile and diff whitespace checks. Preserve evidence and report failures, skips and external blocks separately.

## External dependencies and current checkpoint

Real Windows/WSL environment, BrowserSkill installation/skill loading, authorized browser/login state, Antigravity/Codex execution and the private Durendal project/database are not present in this container. Both live cases currently UNVERIFIED. A read-only Git bundle via isolated CI infrastructure may be used to obtain a verifiable checkout; temporary transport infrastructure must not be merged into the product branch.

Status at creation: investigation; implementation NOT STARTED; baseline NOT RUN. Append actual commands, results, failures, changed scope and remaining checkpoints below rather than rewriting intent to match outcomes.
