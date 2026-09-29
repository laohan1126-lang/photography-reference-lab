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
