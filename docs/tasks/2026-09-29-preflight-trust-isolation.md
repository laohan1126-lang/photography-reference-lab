# Preflight trust + project isolation convergence — 2026-09-29

## User intent
The owner reports that search recall improved after loosening social-card filtering, but new noise now reaches manual screening (example: a Xiaohongshu text/help post about how to manage a Wang Zhaojun / Changye Huansheng costume skirt edge). The owner wants the repository changed first, then a local Agent will pull and run it, and the owner will make the final visual acceptance decision.

This task is a narrow convergence pass, not a new feature expansion.

## Boundaries
- Preserve the current BrowserSkill + local adapter architecture.
- Do not add paid APIs, new providers, or a new ML vision dependency.
- Do not treat search query, title, URL, author, platform recommendation, or existing category as visual proof.
- Do not solve the problem by endlessly adding brand-name blacklists. A costume brand can appear in a valid cosplay post.
- Keep good “voice-line title” cosplay posts recoverable by using detail-page evidence when the search-card text is ambiguous.
- Preserve human K/I/M/X decisions and existing assets.
- No database migration unless unavoidable.
- Work only on this task branch; no main merge or deployment.

## Observable acceptance criteria
1. Xiaohongshu/Pinterest search-card membership alone must not make a candidate eligible.
2. Explicit non-reference help / dressmaking / sale / tutorial language must be rejected before import when visible in card/detail metadata.
3. A valid voice-line-titled cosplay note may still pass if the detail page supplies character/costume/cosplay evidence.
4. Costume brand names alone must not be a rejection reason.
5. Preflight must not claim real-person modality solely from title prefixes or known page URLs.
6. Project-scoped preflight lookup must never fall back to another project's record.
7. “Latest preflight” must use insertion chronology, not random UUID lexical order.
8. Add regressions for the exact failure classes above.
9. CI must pass before this branch is handed off as code-verified. Live hit-rate and visual usefulness remain for the local Agent + owner to verify.

## Planned implementation
- Tighten social metadata admission into three semantic outcomes: accepted, rejected, or needs-detail-evidence.
- For ambiguous Xiaohongshu cards, inspect the visible detail page metadata/tags through the existing BrowserSkill session, then re-evaluate.
- Remove blanket costume-brand rejection and replace it with explicit help/dressmaking/commerce intent markers.
- Remove positive real-person assertions based only on title prefix / known URL in deterministic preflight.
- Make project-scoped preflight lookup strict and order records by row insertion chronology.
- Add focused unit/integration regressions only.

## Verification boundary
Synthetic/unit/CI tests can verify routing, persistence, and deterministic rules. They cannot prove that real-world search results are aesthetically useful or visually correct. Final acceptance requires the owner to inspect a real local run.

## Outcome / implementation receipt

Code-verified checkpoint: `9f7a8ab59e0d0eb47114c5724e03e5c7ea890bd9`.

### Changes made
- Social search-card membership no longer bypasses character/costume/cosplay metadata requirements.
- Ambiguous Xiaohongshu cards return `needs_detail_evidence`; the BrowserSkill path may inspect an actual `/explore/` note page, merge its visible body/tags, and re-evaluate. Search-result pages are explicitly refused as detail evidence so aggregate page text cannot validate an unrelated card.
- A voice-line title remains recoverable when note detail supplies the requested evidence.
- Costume brand names are not blanket negative markers. Explicit help/dressmaking/commerce/tutorial intent remains rejectable.
- Deterministic preflight no longer asserts real-person modality from internal-looking title prefixes or known fashion URLs alone.
- Project-scoped preflight lookup no longer falls back across projects and now orders by SQLite insertion chronology (`rowid`) instead of random preflight UUID text.
- Xiaohongshu query logs now expose `detail_checked` for local verification.

### CI feedback incorporated
An intermediate run exposed two regressions rather than being accepted as “close enough”:
1. A valid card with the exact requested costume plus explicit cosplay/photo evidence but no character literal was over-rejected. Discovery admission now accepts that combination while preflight still remains visually unverified.
2. The isolation regression initially used a non-existent synthetic asset SHA and hit the foreign-key constraint. The test now creates a real persisted test asset before inserting preflight rows.

Both were corrected before the final code checkpoint.

### VERIFIED — automated scope
GitHub Actions run `36534160875` on code checkpoint `9f7a8ab59e0d0eb47114c5724e03e5c7ea890bd9`:
- Core / Python 3.11: **153 passed, 1 warning**, 27.19 s. Node syntax check and Python compile step also succeeded.
- Core / Python 3.13: **153 passed, 1 warning**, 25.42 s. Node syntax check and Python compile step also succeeded.
- Browser / Python 3.12 + Chromium: **23 passed, 1 warning**, 123.69 s.
- All three jobs concluded `success`.

These results verify deterministic rules, persistence semantics and the existing synthetic browser regression suite. They do not verify live Xiaohongshu DOM/selectors, session state, external ranking, image identity, or aesthetic usefulness.

### UNVERIFIED — required local acceptance
The local Agent should pull this task branch into an isolated worktree and run one real BrowserSkill collection using the owner’s normal environment. Preserve evidence for:
- the exact “求助：三分妄想家的王昭君长夜焕生c服裙边怎么整理” class being excluded;
- the “长风万里，生生不息” class remaining recoverable when its detail page really contains the requested tags/body;
- legitimate cosplay not being rejected merely because a costume brand is mentioned;
- imported candidates staying `unreviewed/uncertain` unless real visual evidence exists;
- query logs including `detail_checked`, imported IDs and actual source URLs.

The owner remains the final judge of whether the resulting photographs are actually useful references.

## Local acceptance run (2026-09-29) — four further defects found and fixed

The owner's live environment (BrowserSkill daemon + Edge 154.0.0.0, extension
0.3.1, logged-in Xiaohongshu) exposed three defects that the synthetic suite
and the CI checkpoint could not see, plus the original one. All four are fixed
on this branch; the owner's normal data directory was never modified beyond
additive test projects.

### `aa27497` — the detail-evidence path never worked at all
The search page links each note twice. The extractor preferred the tokenless
`/explore/<id>` anchor, which renders Xiaohongshu's 404 “当前笔记暂时无法浏览”
(error_code 300031) instead of the note, so every detail fetch returned empty
and every voice-line-titled cosplay card was dropped. Measured: 2 cards at
3.5 s, 22 cards at 9.5 s after the same navigation.

Fixed by preferring the `xsec_token` anchor, and by letting the detail guard
accept either note link form while still refusing the aggregate keyword search
page. Live result: 4 → 11 candidates; 长风万里，生生不息 and 愿得昭君王，携手共长生
are recovered from their visible detail body/tags.

### `fc1a3ef` — the deployed setup was silently searching Bing
`shutil.which("bsk")` resolved to a WSL-native `bsk` whose daemon home is
`/home/dell/.bsk`, with no daemon and no extension connected. `browser_id` was
therefore `None` and `main()` degraded to Bing, so the owner was reviewing Bing
results while believing they were Xiaohongshu. Existence was treated as
availability.

Fixed: enumerate real candidates, probe each with `browsers --json`, keep the
first that actually reports a connected browser, and continue past dead or
crashing binaries. When none can, the run reports a blocked manifest and Bing
requires an explicit `--allow-bing-fallback`. This restores the “never revive
the silent headless fallback” invariant.

### `34f2655` — a fixed sleep sampled the page before it loaded
A first live E2E selected BrowserSkill correctly but returned zero candidates
across all 16 queries (`metadata_filtered=0`: nothing was even read). A fixed
`sleep(3.5)` beat the lazy rendering. Replaced with a bounded poll that keeps
the best sample and only gives up early once cards have actually appeared, so
an empty first sample still gets its retries. Applied to both platforms.

### `53e4687` — the default timeout killed real runs
A real pass took 601 s and was killed by the 600 s default with
“本地 Agent 执行超时”. Default is now 1800 s; `LAB_COLLECTION_TIMEOUT_SECONDS`
still overrides.

### End-to-end evidence (VERIFIED)
Run through the owner's own `start.bat` → `launch.ps1` → WSL `run_server.sh`
entry, on `http://127.0.0.1:18765`, via the same HTTP API the UI uses:

- `LAB_DATA_DIR` unchanged: `/home/dell/projects/photography-reference-lab-regression/.local/regression-real-fixed` (222M), read from the live process environment.
- `producer: local_browserskill_adapter`; selected `/mnt/c/Users/Dell/.local/bin/bsk.exe`; browser id `9d3f232a`.
- No Bing source check present.
- Job `2d826239fa9544edbb62b9708d2d027b`, 608 s, 8 candidates imported, `detail_checked` 14–19 per query.
- Recovered voice-line titles: 长风万里，生生不息, 聆听 深眠的潮音, 「长夜焕生」, 捞捞这个王昭君呀吼.
- Junk still rejected: 求助/c服/做裙/裙撑/建模/店铺, including 喵屋/三分妄想 shop comparisons newly caught via detail text.
- All imported candidates `preflight=null`, `preflight_status=unreviewed`, `decision=pending`.

Tests: 46 passed across the adapter and collection-runner files; full CI core
set 158 passed with the same 4 pre-existing Windows-only failures that the
base branch `c3b65d7` produces in this environment (path-separator and
SQLite `WinError 32` behaviour).

### Known limitations (owner decides)
- A mannequin/服装展示 shot (“杭州cos馆长夜焕生到啦”) passes the text filter because
  人台/假人 exist only in the image, not in the post text. Reachable only through
  manual rejection; no new blacklist was added by design.
- A 后期服务 advertisement (“素材会 可做天幕 cos后期”) likewise passes on text alone.
- Whether a candidate is genuinely 王昭君·长夜焕生, and whether the cover is a
  usable single pose frame rather than a multi-panel collage, remains the
  owner's per-image judgement. The collector never claims otherwise.

### Temporary state to undo after merge
`run_server.sh` was repointed at the acceptance worktree to exercise the fix
(backup `run_server.sh.bak.20260929-164701`). Once this branch is merged the
adapter path must be restored to
`/mnt/d/AI PROJECTS/photography-reference-lab/tools/collect_adapter.py` so a
normal start does not depend on a worktree.

## Handoff
Draft PR: #3, head `codex/preflight-trust-isolation-20260929`, base `codex/reference-library-rebuild`. Do not merge before local BrowserSkill and owner acceptance.

