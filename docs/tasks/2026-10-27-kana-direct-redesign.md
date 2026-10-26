# Kana / direct redesign

## Original intent and boundary, recorded before implementation
Baseline: `b805b2a8f7e4ba5e869b1d6595ca7cd727e88dc1`, `codex/ui-studio-15-preview-20261027`.
The owner rejected the candidate: supplied Kana art unused; curtains/hat unwanted; flat typography; ineffective motion; judgments on the left; card and sharing tools below the fold.

Presentation only. Preserve app.js, library-browser.js, API, K/I/M/X, expected_revision, unknown identity, image provenance, field-card gating, source bytes and main. No deployment, new collection, database migration or Golden Path. Public Git receives no private illustrations, photographs, screenshots, databases or font files.

Direction: Kana's Focus Diary. Cool white, sky blue and raspberry from the supplied summer scene. Compact scene opening; the real reference photo remains the primary canvas. Right-hand action rail; no theatrical curtain, improvised hat or nested decoration. Original scene art, not a character cutout.

Protected ergonomics: 1440×900 and 1366×768: photo, K/I/M/X and existing card/edit/source/share controls in the initial viewport. Secondary history can scroll. Mobile has a fixed four-choice toolbar, with remaining controls below the photo.

## What changed
- `web/index.html`: scoped Kana shell; retains original application/form/action IDs and original business scripts.
- `web/kana.css`, `web/kana.js`: isolated presentation layer. Existing controls are moved, never cloned or rebound to fake business handlers. Original `styles.css`, `studio.css`, `studio.js`, `app.js`, `library-browser.js` remain unchanged.
- Fixed-text SVG lettering avoids display-heading fallback; no font binaries distributed.
- Actual supplied art installed privately into `web/private/kana/`. Missing artwork is an explicit state, not a falsely completed theme. `summer.webp` is the initial scene; `rain.webp` belongs to global inspiration; portrait is an available asset, not forced into a carousel.
- Visible pointer hearts/stars, scene parallax, entrance lettering and successful-save cues. No save success emitted on click alone. Reduced-motion remains operable.
- Added targeted actual-renderer component regression and branch-scoped CI workflow.

## Evidence and honest limits
The container could not reach GitHub directly. Source was read through the GitHub connector. Baseline CSS/DOM were recovered from that exact commit's CI trace and CSS blob hashes verified. Local Chromium rendered the new presentation with the exact baseline DOM fixture plus supplied private art. Its 116 assertions cover seven widths, visible artwork/lettering, first-viewport right-hand controls, preserved fixture handlers, drawer focus, nonempty moving particles, failed-save presentation, reduced motion, missing assets and duplicate IDs. This is NOT real API, Windows, production or independent-model verification.

Actual app.js + TestClient + Chromium coverage is in `tests/test_kana_presentation.py`; the new branch workflow publishes synthetic-only screenshots and geometry. Consult its actual run status, not this document, for the result. The inherited baseline CI already failed five HTTP navigation tests at `b805b2a`; do not conceal them or call the whole suite green.

Astra review was denied in the prior attempt. No authorization bypass or independent review occurred in this attempt. External visual review remains UNVERIFIED; owner's aesthetic acceptance remains PENDING.

## Required deployment handoff
Use a worktree beneath `D:\AI PROJECTS\photography-reference-lab\.local\worktrees\kana-direct\root`. Install the separately supplied private assets with `python tools/install_kana_assets.py --source <unpacked-private-kana-directory>`; confirm images decode in the real application. Run `python -m pytest -q tests/test_kana_presentation.py` and relevant existing UI regression before deployment. Inspect actual photos, selected/unselected states, long titles and real card dialogs. Do not copy the offline fixture into production. Keep private images ignored. User authorization is still required for main merge/production replacement.

## Evidence-based postmortem for Codex
1. Skill discovery and benchmark file hashes proved installation, not quality. They did not prove reading the composition or matching its level of finish.
2. The rejected `selection-desk` / `kana-journal` structure put decisions on the left and moved card tools down. An exact viewport/control-coordinate contract was missing.
3. The supplied art was replaced with CSS props. A title saying stage plus a curtain is not evidence of character integration; neither is an unused image in a folder.
4. Display CSS depended on local font fallbacks; the old pointer node had no visible content. Presence of CSS/JS and effect counts did not prove rendered lettering or visible motion.
5. Required independent review was blocked. That gap must remain UNVERIFIED, not be washed away by a pending-user-review label or a large test count.
6. Corrective work must preserve original decisions and state semantics. Our adapter moves original nodes and uses the existing success callback; it does not generate observations or accept cards.

Codex must compare the deployed result against these six concrete failure modes and actual screenshots. Do not write a generic apology or silently relax the goal to pass the gate. A technically valid theme can still be rejected by the owner.

## 2026-10-27 local HTTP failure and owner authorization
The actual isolated-backup application returned 404 for the Kana CSS, JS, two SVGs and private artwork; the existing component test injects presentation files and did not check HTTP. The owner explicitly authorized expanding only the static resource route and adding regressions. Preserve business APIs, existing access policy, daily data and the provided visual design. Public files must use fixed allowlists; private art must require an authenticated session when auth is enabled, with no general directory exposure. Validate actual HTTP, authentication, mobile/desktop rendering, existing workflows and report failures; no production deployment before owner acceptance.

### Evidence-based review and checkpoint
1. The previous iteration validated installation and hashes and inspected the benchmark, but its stated gate did not measure the actual image/text/action relationship against the real application; it did not catch the redesign's loss of the supplied theme. File integrity proved only the files. The new 1.6 fixture also manually injected CSS and JS and did not test the actual static routes; local real HTTP revealed 404s despite green CI.
2. The rejected 1.5 version used CSS stage props instead of the supplied artwork. Now the real isolated preview decodes `summer.webp` (1179×1600) in project view and `rain.webp` (899×1221) in inspiration view. The three private files remain ignored and separate from library data. `portrait.webp` is installed but not displayed.
3. Previous 1440×900 real capture placed the decision region at x58, y405 and the photo at x350. With 1.6 HTTP fixed, the photo occupies x36–1062 and the decisions start x1092, y531; the card button is x1092, y675, and source and share start y761. At 1366×768 the final two right-side controls end at y759 but the 1.6 probe measured only 76.2% visible because an ancestor clips them: **FAIL**, despite their screen coordinates. At 390×844 and 320×720 four decisions are fixed in the viewport. Screenshots and measurements are local private evidence under `.local/kana-ui16-handoff/evidence/`, never public Git.
4. The rejected title's measured glyphs used installed STKaiti, STZhongsong and Adobe Garamond, not bundled cross-environment lettering. The old pointer element did not prove visible pixels. New fixed-label SVGs are served by explicit routes and were visible in actual captures; actual pointer hover produced three distinct transforms with visible SVG children and reduced-motion hid the effect. This does not certify typography or aesthetics.
5. Required Astra review was denied previously. The earlier delivery should have made this independent-review gap prominent rather than calling the entire candidate ready. Current independent review remains UNVERIFIED and owner acceptance PENDING; no alternate channel was used.
6. The API fix adds only fixed static resource routes, authenticated private-art access and private/no-store caching; the presentation adapter retries artwork after login. Existing app.js, library-browser.js, database, rules and source assets are untouched. Synthetic route/auth/login checks passed. The preview uses an isolated official-backup restore with GET/HEAD only and POST 403; it cannot establish that all historical K/I/M/X, cross-role choices or card gates were exhaustively revalidated. Real collection and owner data writes were not performed.

Local route check: `python -m pytest -q tests/test_kana_static.py` with the project virtualenv and isolated temp directory: 2 passed, 1 dependency warning. Before the route fix the first check failed at the real 404. The first login check failed because its fixture omitted the rain image; adding all three synthetic images made the unchanged real login scenario pass. An earlier UI/HTTP suite yielded 20 passed/12 failed while the source changed during its run; it is not valid as a final-version regression. Some failures reference old UI selectors, but no blanket cause is asserted. Follow-up 1.6 component regression and full rendering gates are recorded separately when finished.

Follow-up: `python -m pytest -q tests/test_kana_presentation.py` on the updated source produced **7 passed, 1 failed**, with the 1024×768 first-viewport controls check still failing. The test was retained and no layout redesign was made under this route-only authorization. In the real read-only backup preview, opening the source dialog and moving to the next photo succeeded; a decision attempt was rejected with HTTP 403 as intended. These do not prove a real save, revision conflict, or card acceptance; production and user aesthetic acceptance remain pending.

The 1.6 rendered gate used actual application screenshots at 1440×900, 1366×768, 390×844 and 320×720, original 1.6 read-only probe, local screenshot hashes, and three real hover frames. It returned FAIL for `#toggle-selection` and `#reveal-file-btn` being clipped at 1366×768; the independent-review gate returned UNVERIFIED (DENIED). Overall visual acceptance is not complete. The user's aesthetic decision and authorization for day-to-day deployment remain outstanding.
