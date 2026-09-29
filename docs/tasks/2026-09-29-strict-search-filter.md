# 2026-09-29 Strict request-driven search + truthful filtering

## User-reported failure

The owner explicitly asked the local collector to find only real cosplay photographs for a specific skin, but the resulting candidate stream still contained many official/game images and illustrations. A live example titled roughly “王昭君FMVP皮肤长夜焕生特效设计介绍” was displayed as:

- candidate preflight: passed
- content type: real_person_cosplay
- identity: match
- producer: local_collection_adapter

This is a correctness failure, not an aesthetic preference issue.

## Root cause found in current repository

1. `tools/collect_adapter.py` accepts an image as cosplay when the concatenation of title + description + **the search query itself** contains terms such as `cos`, `cosplay`, `正片`, etc. Because generated queries already contain those terms, unrelated search results can be labeled cosplay.
2. The adapter emits Schema 3 “visual preflight” fields even though it does not run an image-understanding model. It can therefore claim “真人实拍 / identity match” based on search metadata.
3. The owner’s free-text collection notes are not materially enforced by query construction or result acceptance.
4. The existing `ref_lab/preflight.py` also allows metadata/query text to become positive evidence and defaults unknown modality to real-person cosplay, so a later scan can repeat the same false-positive pattern.
5. The new collector test verifies transport/package validity, not the semantic requirement “game/illustration results must not pass as cosplay”, and it is not currently included in the core CI command.

## Scope: deliberately minimal

Do **not** add a larger ML/vision stack, paid API, template system, or more product modes.

The current requirement is only:

> Search according to the user’s explicit request, aggressively exclude obvious non-cosplay results, and never fabricate a visual pass when no visual classifier actually ran.

### Search adapter rules

For the local Bing-based adapter:

- Treat project character/costume/work and the user’s collection notes as hard search context.
- For an exact cosplay request, use photo-only image search filters and explicit negative query terms for game screenshots, CG, illustrations, wallpapers, concept art, model/render, merchandise and costume-display results.
- Result acceptance must **not** use the search query itself as positive evidence.
- Require positive cosplay/photo evidence from the result metadata itself (title/description/page context), and require character + requested costume/skin terms when they are available.
- Reject result metadata containing strong negative-type markers such as game screenshot, skin effects/demo, illustration, wallpaper, concept art, CG/render/model, merchandise/mannequin/costume display.
- Prefer fewer candidates over filling `target_count` with weak results.
- Do not fall back to Bing thumbnails when the original image URL cannot be downloaded.
- Keep exact SHA de-duplication and add within-run perceptual dHash suppression for re-encoded near-duplicates.
- Return Schema 2 from this search-only adapter. It is intentionally **not** a visual preflight producer.

### Server preflight rules

The built-in deterministic preflight may still filter obvious negative modalities, but it must be conservative:

- search query / title / aliases can be used to detect contradiction or suspicious source type;
- they must not by themselves produce a positive visual identity match;
- unknown modality defaults to `unknown`, not `real_person_cosplay`;
- metadata saying “cos” without actual visual evidence is not enough to mark content_type as real_person_cosplay;
- if no image-grounded rule can establish a positive identity, return `uncertain`.

The owner would rather see fewer results / uncertain labels than a false “passed”.

## Duplicate boundary

Existing exact SHA de-duplication across the library remains valid. This task only adds within-run perceptual suppression to the local adapter. Historical near-duplicate consolidation across old library assets remains a separate optional improvement and must not be silently expanded in this task.

## Acceptance criteria

1. A search query containing “cos” cannot make an unrelated result pass the adapter.
2. A result titled like “王昭君…皮肤…特效设计介绍” is rejected from a cosplay-only search even if the search query says “cos 正片”.
3. Illustration/game/CG/wallpaper/model/product markers are rejected before download/import.
4. A result explicitly describing the requested character + skin + cosplay/photo is eligible.
5. Explicit free-text request terms materially alter generated queries and filtering policy.
6. Adapter output is Schema 2 and does not contain fabricated visual preflight.
7. A later deterministic preflight scan does not turn query/title alias matches alone into visual identity `match`.
8. Unknown modality stays unknown/uncertain.
9. Within one run, byte-identical and dHash-near-identical images are not duplicated.
10. Core CI includes the collector semantic tests.
11. Existing project/reference/board functionality remains green.

## Verification boundary

These deterministic filters can prove that obvious wrong categories are not accepted and that metadata cannot impersonate vision. They do not prove perfect photo-vs-CG recognition for every unlabeled image. Final local acceptance should run the real Wang Zhaojun / 长夜焕生 request again and manually inspect the returned candidates. The result should be reported as a real hit-rate sample, not merely “30 candidates imported”.

## BrowserSkill (Xiaohongshu + Pinterest) Priority Restoration (2026-09-29)

### Issue
The local collection adapter had previously regressed to only calling `fetch_bing_candidates`, ignoring the user's primary source preference (Xiaohongshu + Pinterest) and causing real character searches (e.g. 达妮娅) to find zero candidates due to Bing's lack of real cosplay scene photography.

### Resolution
1. **Source priority restored in `tools/collect_adapter.py`**:
   - `find_bsk_bin()` auto-detects `bsk.exe` across native Windows and WSL paths.
   - `get_connected_browser_id()` verifies connected Edge instances.
   - `fetch_bsk_candidates()` prioritizes Xiaohongshu (`xiaohongshu.com/search_result?keyword=...`), strictly filters post titles and context with `result_metadata_allowed`, and retrieves full-resolution WebP image bytes directly within the page execution context to circumvent CDN anti-hotlinking 403 blocks.
   - If `target_count` is not yet met, it queries Pinterest (`pinterest.com/search/pins/?q=...`) to complement.
   - Strict `bsk session stop` in `finally` to ensure clean resource disposal.
   - Bing is kept strictly as an offline fallback when no BrowserSkill daemon/instance is active.
2. **Verification & Evidence**:
   - Live project "达妮娅" (ID: `a0cccc22dfef436aa7df08db8964f01e`, notes: "只找cos场照", job ID: `0e9c1faaaf734d95b25ff95e72e907ca`) dispatched via `POST /api/jobs/{id}/run-antigravity`.
   - BrowserSkill opened Edge, searched Xiaohongshu for `鸣潮 达妮娅 cosplay 正片`, scanned 18 posts, strictly rejected 13 non-cosplay posts, and successfully acquired 5 real coser stage/convention photos (`bd5e4a32...`, `b1a8f5ed...`, `b56d0201...`, `b80a70f3...`, `019d5438...`).
   - Regressions: all 9 adapter tests, 111 core library tests, 29 extended workflow tests, and `node --check web/app.js` passed.

