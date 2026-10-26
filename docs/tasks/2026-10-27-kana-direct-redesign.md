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
