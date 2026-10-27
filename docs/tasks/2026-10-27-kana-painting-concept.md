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

## Windows candidate deployment, 2026-10-27

Owner request: deploy this new branch for actual review, preserve the supplied composition and main. The real HTTP allowlist omitted kana-painting.css, reproduced by the expanded resource regression (404 instead of 200). Add only that exact stylesheet to the allowlist; preserve private-media authentication and path restrictions. Install the existing hash-verified local art and run the actual app against an independent backup with mutation requests blocked. Windows rendered checks and publication outcomes will be appended below; owner aesthetic acceptance remains PENDING.

### Verified outcome
- Exact candidate baseline: 60016a7. Preserve the supplied composition, fonts, original illustration bytes and all business handlers. No main merge or daily-data deployment.
- Static regression first reproduced HTTP 404; exact stylesheet allowlist fix passes public CSS and private-art auth/path checks.
- Initial focused run: 4 passed, 6 failed. Scene overflow was caused by the original image leaving its scene and the mobile scene extending beyond the viewport. Clip only that decorative scene, bound the existing blurred underlay, and reuse the existing compact-inspector state with reduced gaps/padding; no body overflow suppression, title/warning removal or photo resizing. Drawer regression now exercises the mobile drawer; desktop navigation is intentionally persistent.
- Intermediate run: 8 passed, 2 failed. After inspector spacing correction the three desktop cases passed. Actual backup long-title content exposed another short-screen boundary which synthetic content did not; corrected the same compact padding rule and reran those 3 cases: 3 passed. The other 7 cases reuse the unchanged relevant evidence from the 8-pass run. All 10 focused cases now have passing evidence; no claim of a fresh full-suite pass.
- Windows Edge actual HTTP: 1440x900, 1366x768, 1024x768, 390x844, 320x720; painting stylesheet loaded, original art decoded, font loading complete, zero page exceptions, no horizontal scroll. Applicable desktop controls and mobile K/I/M/X in viewport with hit tests. Real next-image change and source dialog passed. Three original media HTTP requests returned 200; write barrier returned 403.
- Local preview http://127.0.0.1:18778/ uses the separately restored official backup, automatic classification OFF, mutations blocked. It is opened in the system browser for owner review. Private assets, database and screenshots remain ignored/local. Existing daily checkout edits are preserved.
- Owner aesthetic approval, exact concept-image visual parity and full repository regression remain UNVERIFIED. Typography/spacing are a candidate for human review, not deemed accepted by technical checks. Notion disabled. Git publication SHA is recorded independently by the Publisher receipt for turn 01a17c57-78d5-70b3-aa4a-6eee8cc37a92.
