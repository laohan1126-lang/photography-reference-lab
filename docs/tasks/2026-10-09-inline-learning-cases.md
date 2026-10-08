# Inline professional learning cases · 2026-10-09

## Owner intent and acceptance

“直接把原网站图片、文字什么的直接给我摘录下来……省得我打开网站看。” Make the existing three learning paths self-contained for observation: seven external-only cases become nine inline source photographs, with concise Chinese source paraphrases, attribution and traceable reading locations. Keep full original teaching and delayed exercise analysis. Do not copy entire articles, infer redistribution permission, download source photographs into Git, bypass access restrictions, add courses, change private state or migrate reference assets.

## Baseline and blueprint before edits

- Branch `codex/evidence-photography-atlas`, baseline `46b236486fc784c58a9c9d70d346b5eae2c39124`. The injected task identity is `01a11caa-c304-7f42-aa99-7a702f360445`, session `01a111c0-c935-7770-a2ee-f4ce03ce4d9a`; the immutable publisher baseline and contract are outside the repository.
- Existing FastAPI, plain JavaScript/CSS and pytest/Playwright; no dependency changes. Reuse the reader, source catalogue, spacing/type tokens, loading/error handling and existing drafts/navigation.
- Touch the case catalogue, reader media rendering, a shared narrow image policy, catalogue validation, affected tests, generated learning bundle and current documentation. Avoid `web/app.js` (already dirty), unrelated untracked work, original skill/source/companion catalogues, SQLite, private records and runtime configuration.
- Main risk: confusing original-source reference with redistribution permission, or source claims with our own observations. Preserve `rights.allowed=false` for unlicensed original cases; `source_remote` names the display mechanism only. Permit exact observed media locations only on `/learning`; scripts, API connections and the reference library stay same-origin. No image proxy/cache.
- Acceptance: all seven cases/nine source photos visible at natural proportions; Chinese source paraphrases directly below each case; correct attribution/reading location; actual desktop/mobile original-photo checks, failure fallback and existing draft/return/state regressions. Test fixtures are not evidence of real photographs or learning outcomes. Publish exact files and verify remote SHA.

## Semantic review before implementation

Reviewed successful receipts `01a11c4f-3f5c-72e1-a708-c095c840a8a9` and `migration-photography-reference-lab-717d3fd6` and their recorded root causes. The first established separate teaching/state ownership; the second concerns publication recovery and remains unchanged.

PATCH-LOOP DETECTED: copyright status and display mechanism were conflated. Absence of redistribution permission made real cases external links, breaking the observation activity. Keep source provenance, rights truth, original teaching and state ownership. Delete the assumption that a remote reference must assert a reuse license. Redesign around explicit `source_remote` media references and `licensed_remote` material, with one shared precise image allowlist and independently traceable source paraphrases.

## Source/pixel audit before implementation

All original media URLs were obtained from the actual public source pages, not reconstructed CDN variants. Root opened all nine exact images in Edge and inspected their pixels and natural dimensions. Agents independently checked source text and existing rendering/validation.

- Nikon / Diane Berkenfeld: `distraction-1-before.jpg` and `distraction-1-after-fixed.jpg`, both **650×981**, vertical photographs. The old catalogue incorrectly said horizontal/wide format; that claim is withdrawn. In the second image arcing grass overlaps a greener, textured blurred background, not a uniformly dark/empty one. Viewpoint, framing and exposure are not a controlled single-variable experiment.
- Nikon / Tamara Lackey: `Tamara-Lackey-laughing-girl-portrait.jpg`, **650×792**. Green top, blue jeans, cross-legged on a white bench/bleacher, horizontal railing and orange foliage. The old claim about warm-coloured clothing is withdrawn. Centering is one part of this portrait, not an isolated causal experiment.
- Ed Gregory / Photos in Color via PetaPixel: `portraittest_1.jpg`, **1600×867**. Sixteen portraits in a four-by-five layout with crossed-out corners; no precise per-frame angle labels. Embedded video was not watched.
- Andrew Faulds via Professional Photographer: `201711-8vh_1901_header.jpg`, **1200×675**. Side-facing woman, sunglasses, bent arms and warm/cool light; insufficient geometry to recover camera height.
- Jane Allan / The Lens Lounge: `butterfly-light-portraits.jpg`, **800×565**. Two outdoor portraits with sunglasses hiding the eyes; head direction/nose shadows can be compared, but pose and expression vary.
- David Hobby / Strobist: exact original-page links `Shade.jpg` **800×534**, `Dark.jpg` **800×534**, `Final.jpg` **800×555**. The final framing and pose differ, in addition to exposure and flash changes. Normal Edge access succeeded; no challenge or paywall bypass. The article is a working sequence, not a pure single-variable test.

Historical V2 review documents remain historical. These corrections replace inaccurate current catalogue descriptions without pretending the previous audit was accurate.

## Outcomes

Implemented seven `source_remote` cases with nine original media references, optional per-image phase labels, intrinsic dimensions and independently traceable Chinese source paraphrases. Source paraphrases expand in the same reader, remaining folded before the observation activity. All three existing Commons transfer cases remain byte-for-byte equivalent as catalogue objects. Original-photo clicks no longer unexpectedly navigate away. A failed image retains its text/attribution and does not hide sibling images. Cached load/error state is handled when reopening the reader.

Independent read-only review found no blocking correctness or state issues, and caught one leftover “打开网格” prompt; changed it to “观察上方网格”. Main photography/source corrections are recorded above. No new course, dependency, database/state model or reference-app change.

### Actual verification

- `python -m pytest -q --basetemp .local/inline-case-test-qa-final tests/test_learning_gateways.py tests/test_learning_gateways_ui.py`: **21 passed**. Seven source cases/nine exact media URLs and accurate rights/source mapping; real HTTP/Chromium inline rendering; source paraphrase expansion; single-photo failure, siblings and returning draft; existing auth/CSRF, response ownership, conflict and navigation checks. Synthetic image fixtures test rendering/policy only.
- `python -m pytest -q tests/test_library.py tests/test_imports_jobs.py tests/test_workers.py tests/test_operations.py tests/test_personal_library.py tests/test_collection_runner.py --basetemp=.local/inline-case-core-tests`: **123 passed**.
- `python -m pytest -q tests/test_learning_state.py tests/test_learning_gateways_state.py tests/test_learning_ui.py tests/test_photography_tutorials.py --basetemp=.local/inline-case-learning-tests`: **31 passed**. Tests use isolated data, not the normal library.
- **175 tests total** in the current work; each run reported one existing Starlette/httpx deprecation warning. Early red checks exposed the missing source-media model. Initial browser fixture attempts were blocked by sandbox setup, then succeeded with the same isolated tests outside that restriction; intermediate new-test failures were test assumptions/API usage, corrected before the final passing run.
- `python tools/build_photography_atlas.py --check`, `node --check web/learning-gateways.js`, `node --check web/app.js`, `git diff --check`: **PASS**. Final bundle digest `14701727c23cf24e1f0949bb022e25a84a7f2251083117a3c63da03c342883b0`.
- Compared old/new bundle objects: domains/modules/skills/sources/tutorials/conflicts/gaps/problem index/checklists unchanged. Protected dirty `web/app.js` SHA-256 remains `b8d255950fdff188716c7c325357f4fd7dccf1fa7fea039701dd52a8dc6ea019`.
- Restarted only the verified managed Windows server through existing scripts with automatic classification disabled; actual Edge reader at `http://127.0.0.1:18765/learning` loaded all nine exact source photos. Inspected real displayed photographs and source paraphrases without external navigation. Mobile 390×844 checks retained natural photo proportions and no document/reader horizontal overflow; reset the viewport afterward. No normal-library learning writes were performed.
- Captured real, unsubstituted source photos in a separate Chromium session at 1440×1000 and 390×844, then opened both screenshots: `.local/inline-case-qa/desktop-original-cases.png`, `.local/inline-case-qa/mobile-original-case.png`. These private QA artifacts and source-photo bytes are excluded from Git.

### Limits and publication

Photo rendering currently works with the observed original hosts; this is not an offline archive or a guarantee of future availability. No redistribution license or creator endorsement is claimed. Human aesthetic acceptance and learning transfer remain unverified.

Safe cleanup was limited to this task's two newly created `.pytest-tmp-inline-cases*` directories: 104 files were copied to `.local/inline-case-qa/test-setup-backup` and moved to `.local/inline-case-qa/test-setup-archive`, with preimage metadata/hash manifest and post-move/backup SHA-256 checks. No files were deleted; unrelated temporary directories remain untouched. Manifest: `.local/inline-case-qa/test-setup-archive/manifest.json`.

Publish only the explicit twelve changed/new task files through the canonical publisher. Actual Git/Notion outcome and remote SHA live in this task's external receipt; this document does not predict publication success. Unrelated dirty/untracked work remains outside the commit.
