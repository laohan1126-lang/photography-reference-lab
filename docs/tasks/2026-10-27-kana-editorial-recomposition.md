# Kana fully recomposed illustrated UI — 2026-10-27

The user explicitly accepted the generated 1672×941 full-page concept and rejected the earlier additive "painting" CSS skin as unrelated to the design. This change replaces the HTML spatial structure, not only colors.

- Desktop: persistent project navigation on the left; ARIMA/Kana typographic hero with original full illustration, a handmade film ribbon, subtle light/star layers; open local project index; actual reference photograph in the center; real decision and make-card controls on the right; real filmstrip beneath.
- Mobile: original navigation drawer, project label near photo, real K/I/M/X sticky review bar.
- Underlying business state remains owned by existing app.js and library-browser.js. Dynamic contents mount through unchanged #view, and kana.js continues to move real controls rather than clone callbacks.
- Original private summer.webp/rain.webp are mounted by existing private installer, not shipped to the public repository. They are not AI recreated. No replacement of actual reference photos by the approved mockup's fake pixels.
- The accepted generated mockup remains design specification; implementer must compare Chromium screenshot against it, especially character scale, drawing/typing integration and main photo/right toolbar geometry. Any visible drift is a defect, not artistic liberty.
- No backend, schema, session, user library, or export changes. Main and production remain untouched.
- User aesthetic review PENDING. CI business tests are not a claim of visual parity.


## 2026-10-27 editorial v2 implementation and verification

Owner rejected the earlier cosmetic overlay; the approved generated design is the fixed visual target. Actual changes go beyond CSS:
- Replace workspace DOM hierarchy: persistent desktop project rail; real headline and ARIMA + fixed-path Kana artist lettering; large real private original illustration; open project context rail; actual #view renderer with real filters/current-reference photograph, thumbnails and right-hand decisions. The dynamic #view and IDs still connect to existing app.js, original API, review state and revision handling.
- New web/kana-editorial.css owns page architecture, not just colors. New web/ui-art/kana-display-logo.svg is a self-contained wordmark shape (no distributable font).
- Fix ref_lab/api.py CSS/SVG static allowlist (old code returned 404 for the new layer!). Add HTTP checks in tests/test_kana_static.py; component test harness loads the correct CSS and SVG. Keep user's summer/rain/portrait images in ignored private folder, with existing verified installer hashes.
- Round circular K/M/X buttons, separate genuine I decision, compact make-card and six live secondary actions in the real inspector; phone uses original sticky decision controls and drawer, honoring reduced-motion.

**Actual CI evidence:** workflow Kana presentation regression run 40476375311 for code commit 9296ceffc685862fabf463faaf6f46baa3d5942d; Chromium/TestClient test summary 10 passed, 1 warning. This checks business component behavior and static serving but uses synthetic photo fixtures.
**Local art visual evidence:** compared owner's approved 1672x941 concept with genuine owner-provided summer.webp plus real-world reference cropped from a user-supplied screenshot inside an isolated local visual QA page. 1672/1440/1366/1024/390/320 renders inspected; desktop/right operations and mobile sticky judgments visually evident; no horizontal overflow in those static captures. These screenshots are **NOT** the authenticated production Windows browser and do not prove full HTTP app parity. Full-repo regression still not accepted as green; independent Astra critique still UNVERIFIED. User aesthetic acceptance PENDING.

**Remaining:** compare real Windows Edge authenticated read-only snapshot against accepted concept at 1672x941, 1440x900, 1366x768, 390x844; ensure private art all decodes, correct current project name/data, real card/save/source/export flows and hover/mid-motion. Fix mismatches before asking for signoff. Don't overwrite main/deploy/commit private art until owner explicitly approves.
