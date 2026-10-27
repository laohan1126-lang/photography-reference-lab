# Kana accepted-concept fidelity rebuild, 2026-10-27

## User request and rejected baseline

The user rejected the preceding layout as unrelated to the accepted mockup, explicitly noted overlapping typography, and asked for a deeper implementation, honest capability boundaries and a reusable Skill update. The previous branch a753080 is NOT aesthetically accepted. This candidate uses a new task branch and does not merge or deploy main.

## Active design contract

Accepted mockup: 1672 x 941, SHA256 `5b53aef8021f687910ad22ab9e01c94720f853fe53ee90e197a53bb4a814425c`. Mode: FAITHFUL_IMPLEMENTATION, not fresh random exploration. Title around x.13/y.055/w.273, photo frame around x.24/y.375/w.465/h.465, actions to its right. Title must not touch the tabs. Core actions stay visible at 1440x900 and 1366x768; mobile preserves K/I/M/X and accessible navigation.

The canonical appearance comes from public business styles.css plus a single rewritten kana-editorial.css. No studio/kana/atmosphere/painting theme overlays are loaded. The existing canonical kana.js is now a rewritten presentation adapter. Original app.js, library-browser.js, database, imports, policy, original bytes and endpoints are not changed.

## Implemented

- Full original uniform illustration as the environment, not the cyan summer banner. Other supplied illustrations enter only decorative scene prints. None are committed publicly.
- Fixed combined ARIMA/Kana/Chinese lettering and handwritten note exported as individual accessible SVG assets from the approved mockup; no system-font imitation, no font files, no flattened screenshot UI.
- Rebuilt navigation/local project index/current photograph/right decisions composition. Main photograph retains `object-fit:contain` and `filter:none`; soft echo is a separate decorative image.
- Real K/I/M/X, source/card/edit/share controls retain their DOM nodes and handlers. Search/filter moved to the left index, no API rewrite or fake saving.
- Actual pointer orbits, environment motion, thumbnail feedback and distinct post-save cues; reduced motion preserves state without duplicated photo.
- Broader regression found and fixed: open global menu intercepting content; mobile global navigation inaccessible; evidence details double-nested; original post-save cue removed. Old business assertions retained.

## Local verification scope

Actual product JS runs in Chromium with explicit TestClient request bridge and isolated fixture DB, not the owner's library. Local browser navigation to HTTP was administratively blocked; it was NOT bypassed and the component method is NOT represented as a deployed HTTP environment. Static route/auth tests run via TestClient. CI runs the separate actual-HTTP login test.

Before publication: presentation/fidelity/static tests 16 passed, 1 local HTTP browser test deselected due to environment restriction; all 22 existing business component cases passed after fixing the regressions above. Final CI attached to this branch is the authority for the pushed bytes. Six viewport real-art screenshots are conversation artifacts, not public Git; stage pictures in that demonstration are isolated fixtures, including a crop from the owner's screenshot. No claim that synthetic tests establish visual authenticity or aesthetics.

## Remaining fidelity ledger (do not hide)

1. Original character pose vs generated leaning pose: CONSTRAINT_CONFLICT. Keeping the supplied artwork cannot also reproduce a newly drawn pose without another matching image or authorized editing. No character regeneration was done.
2. Portrait reference vs landscape concept photo: CONSTRAINT_CONFLICT. Full portrait pixels plus landscape fill cannot both be kept without crop/stretch/new pixels. The true photo remains intact, with neutral ambient gutters.
3. Rich painted silk/light/stage texture: OPEN visual difference. Current vector ribbons and highlights approximate it, but are not equally detailed. This is unfinished asset art direction, not an inherent HTML/AI impossibility.
4. Windows Edge production and independent Astra critique: UNVERIFIED. Do not infer from isolated Linux component or CI tests.
5. Overall aesthetic acceptance remains PENDING and full concept fidelity is PARTIAL. No percentage or 10/10 self-score.

## Reproduction and boundaries

Use original `tools/install_kana_assets.py` and the separately supplied private assets; verify the hashes and authenticated decode. Run `node --check web/kana.js`; `python -m pytest -q tests/test_ui_components.py tests/test_kana_presentation.py tests/test_kana_static.py tests/test_kana_fidelity.py`. Render the actual app at the accepted 1672x941 viewport and small laptop/mobile sizes. Keep reference and screenshot unretouched and record differing regions. No Golden Path added, no private data committed, no main merge or production deployment.
