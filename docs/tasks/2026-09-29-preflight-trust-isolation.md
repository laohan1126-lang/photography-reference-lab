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

## Handoff
Draft PR: #3, head `codex/preflight-trust-isolation-20260929`, base `codex/reference-library-rebuild`. Do not merge before local BrowserSkill and owner acceptance.

