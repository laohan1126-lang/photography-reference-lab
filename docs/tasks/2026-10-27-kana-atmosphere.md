# Kana / continuous illustration atmosphere — 2026-10-27

Owner feedback: the prior UI still felt generic. MEGU.FM worked because the whole illustrated scene, its opacity, and gradients formed the *environment*. Kana instead shrank the painting to a 142px banner with a 355px image and two masks. The reviewer explicitly rejects presenting isolated decoration as character integration.

## Implemented in isolated branch
- Keep the existing right-hand K/I/M/X, edit, source, make-card, and export controls; keep genuine frontend event handlers and API semantics.
- Use the original complete summer illustration as a broad, faded visual atmosphere behind the title and into the workspace; retain recognizable face/pose at the top without hard-edged thumbnails or an isolated character cutout.
- Add a dimmed/blurred ambient echo of the currently viewed *actual* reference only behind its view stage. It follows real image load and selection; do not alter original pixels, inference, or data.
- For inspiration mode, use the rain illustration only if the owner's private art is installed. When art is missing, continue a legible, usable neutral layout; do not claim art loaded.
- Mobile keeps visible sticky K/I/M/X and fixes previously exposed horizontal overflow from the project menu and image-kind filter.
- Motion is subtle environment breathing and source-photo glow plus existing contextual pointer effect, with reduced-motion alternatives.

## Scope, rights, and status
Changes are limited to web/index.html, web/kana-atmosphere.css, web/kana.js and UI test loading. The repository is public; NO image, private library, DB, username or font binary is committed. Private images must be installed via existing local tools/install_kana_assets.py. No main merge, deployment, or Golden Path.
Local isolated Chromium screenshots and responsive probes exist in the conversation artifact; cannot be taken as live Windows HTTP verification. User approval PENDING. The delivered visuals are a candidate, not final aesthetic acceptance.
