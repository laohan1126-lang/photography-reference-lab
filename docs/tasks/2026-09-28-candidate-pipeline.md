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

## Outcomes and verification results (2026-09-28)

1. Converged remote changes (`aa18eef4d87a525ecaabad643f5b5a2c43113194` modality preflight & project archive/restore) with local candidate production line (Identity Context, Quality Preflight, explainable ranking, screening sessions, versioned aesthetic profile, BrowserSkill collection).
2. Visual Modality & Grounded Identity Gates:
   - Added `detect_modality` in `ref_lab/preflight.py` detecting 11 modalities (game screenshot, illustration, equipment/bts, product/prop, costume display, collage, scenery, real portrait, real cosplay).
   - Added grounded `CANONICAL_PRESETS` for "王昭君" and "安养寺姬芽" alongside "有马加奈" and "假面骑士Durendal" to eliminate hallucinations.
   - Filtered non-real modalities and identity mismatches to "已过滤候选" with observable visual reasons; preserved recoverable actions ("恢复为普通候选" / "设为可迁移动作").
3. Real-Database & Real-Asset Verification (`legacy-changye-huansheng`, 457 items):
   - Executed live project preflight scan: 457 scanned, 403 passed, 54 filtered, 0 uncertain.
   - Verified ground truth on actual images:
     - 2D illustrations (`OFFICIAL_001` - `007`): filtered as `official_illustration`.
     - 3D models (`OFFICIAL_008` - `013`): filtered as `game_screenshot`.
     - BTS lighting/gear (`BTS_001` - `005`): filtered as `equipment`.
     - Props (`PROP_001`, `PROP_002`): filtered as `product`.
     - Iris van Herpen fashion runway (`COSTUME_003`, `004`): filtered as `real_person_portrait` with `mismatch`.
     - Xiao Qiao (`小乔的白棚`): filtered as `mismatch`.
     - Diao Chan (`COS_WANG_ZHAOJUN_HOK_3251408_1` etc.): filtered as `mismatch`.
     - Real underwater cosplay (`COSTUME_001`, `SEL_A_02` etc.): passed as `real_person_cosplay` + `match`.
4. Automated Regression Summary:
   - Core test suite (`test_library.py`, `test_imports_jobs.py`, `test_workers.py`, `test_operations.py`, `test_personal_library.py`, `test_collection_runner.py`, `test_modality_archive.py`, `test_candidate_pipeline.py`): **122 passed in 26.20s**.
   - UI browser test suite (`test_ui_components.py`, `test_collection_ui.py`): **15 passed in 99.42s**.
   - Total: **137 passed, 0 failures**.
   - `node --check web/app.js`: Passed.
   - `python -m compileall -q ref_lab tools tests`: Passed.
   - `git diff --check`: Clean.
5. Local Server Live Deployment:
   - Server active at `http://127.0.0.1:18765` backed by user database `.local/regression-real-fixed`.

