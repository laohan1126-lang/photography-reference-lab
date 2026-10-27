# Kana painting-based UI — approved concept implementation candidate

User approved the generated single-canvas visual concept, **not** a generic anime themed admin skin. The design target is a warm, bright and expressive editorial photo-review workspace with prominent original Kana illustration, large artistic ARIMA/Kana lettering, film-strip gestures and open layout rather than repeated boxes.

## Architectural choice
- Preserve the real K/I/M/X business handlers, classification, stage image source, revision semantics, make-card, original viewing, export and project search.
- The existing review image is ALWAYS the actual reference, never filled with concept mockup pixels or fabricated photographs.
- Recompose with persistent left project-navigation rail on desktop, original full illustration painted across header and workspace, review image in center, right-hand real decision controls, filmstrip below the review image.
- Use genuine owner-provided Kana scene assets already managed at `web/private/kana` (summer.webp/rain.webp). Do **not** regenerate a new main character or commit those private/copyright images to public Git.
- Rebuild artistic hierarchy using an ARIMA display lettering layer and original kana-wordmark.svg, protect body/action legibility, bring photographic material and atmospheric color together through soft gradients and scene masking.
- On mobile, navigation collapses to existing drawer and four decision controls stay in reach, with motion reductions respected.

## Honest boundary
This is a code and design candidate, not a proven pixel-perfect translation of the generative image. The source concept contains synthetic copy and fake thumbnails: those must NOT replace real app data. Evaluate the actual authenticated Windows runtime, screenshot it at 1440x900, 1366x768, 390x844, and exercise save, card, modal, export, image navigation, viewport sizing. Record every deviation from the approved concept. If missing fonts or images, FAIL/UNVERIFIED; never call visual parity complete until the real browser screenshot is reviewed. No main merge or production deployment until owner approves.

## Files
`web/kana-painting.css`, `web/index.html` only. New CSS is isolated and reversible. No new API, database, Python service, or altered saved records.
