# Drive recovery and owner-photo teaching cases

## Owner intent and boundaries

The owner asked to use their Google Drive photographs as memorable counterexamples and explain how to change the next shot. They then prioritized “优先检查为什么drive不能下载 优先保证插件稳定性” and asked to continue checking Drive after reopening the client. Preserve their earlier preference: self-study questions, without answer-entry or assessment controls.

Inspect real files before photographic claims. Preserve received bytes, original image library, private records, credentials and network/proxy settings. Do not infer role names, capture height/distance/focal length or a controlled improvement pair from unrelated frames. No paid services, bulk rewriting or new learning-state system.

## Blueprint, ownership and acceptance

Reuse the existing course in `GATEWAYS.json`, source/hash records in `LEARNING_CONTENT.json`, the canonical generated bundle and the hash-checked private media route. Add two explained diagnostic-boundary cases inside the existing boundary section, leaving the three unseen transfer photographs and three thinking activities intact. Selected private original JPG bytes remain under ignored `.local`; no image bytes enter Git.

ROOT started and declared transaction `01a12499-f8c2-7f93-9345-1e9be2e9dfd6` before this edit. Reviewed the supplied prior receipts `01a12461-924a-7630-a321-bb77bbc4eb39` and `01a11caa-c304-7f42-aa99-7a702f360445`: keep the course/map/state separation and existing source/media boundary; add actual observations rather than another acquisition or assessment system.

Owned paths: this record, `docs/research/photography-atlas/GATEWAYS.json`, `docs/research/photography-atlas/LEARNING_CONTENT.json`, `web/learning-atlas.json`. GATEWAYS and the generated bundle overlap the previous uncommitted reader checkpoint. That exact prior transaction was retried after a successful remote connectivity probe, but again failed before commit with `Recv failure: Connection was reset`. No further blind retry or new baseline for those earlier changes. Preserve pre-integration bytes privately so the failed sealed checkpoint can be recovered separately; do not commit pre-existing changes under this new transaction. Unrelated `web/app.js`, other dirty/untracked files and all images remain excluded.

Acceptance: actual Drive reads and complete readable original JPGs with sizes/local hashes; meaningful intent-dependent observations, next adjustment, cost and falsifying check; canonical validation and real browser photo display without forms or personal writes. These checks do not certify long-term plugin reliability or the owner's learning gain.

## Drive evidence

After the client was reopened, the plugin actually listed the owner's folder, returned file metadata and search results, then listed the folder again. Both stored JPGs report download permission. The first DSC02268 fetch returned MCP `-32603 Internal error` after about 31 seconds; current logs expose no provider HTTP/TLS/root-cause detail. A small binary probe and DSC02260 succeeded; the canonical DSC02268 URL subsequently succeeded and a further same-file raw fetch succeeded in 5.329 seconds. These observations do not establish a file-size limit or prove the URL query caused the initial error.

Use ordinary plugin-returned file URLs with `download_raw_file=true, include_base64=false`; consume the returned file reference without exposing its temporary signed URL. Python urllib encountered `SSL: UNEXPECTED_EOF_WHILE_READING` when consuming the returned reference. The existing Windows .NET download client then saved both originals successfully using existing system settings. No proxy, network, TLS trust, credentials or plugin installation was changed. Earlier local quoting/stdin attempts failed before a request and were corrected; they are not evidence of Drive permissions.

| File | Original bytes | Decoded dimensions | Local SHA-256 |
| --- | ---: | --- | --- |
| DSC02260.JPG | 17932314 | 7008×4672 | `1c02c12aeca9f7ab84c8c5148c2ed5396665c345b1ad4e7e813679e97cc6a49a` |
| DSC02268.JPG | 18621715 | 7008×4672 | `6f359f0b2fb2a3fe127d246222eb9a683edf1a412f1edbf3315047fd5e4c044c` |

Byte counts match the plugin metadata. JPEG magic and full pixel decode pass; the image library reports MPF/MPO-compatible JPEGs. The metadata adapter did not return the requested Drive checksum, so local hashes are identity checks, not an independently matched provider checksum. ROOT and an independent reviewer opened both actual local originals; earlier browser screenshots are not substitutes for those bytes.

Current folder/file read and original-file acquisition are verified. The shared transport failure is no longer reproduced in these calls; its exact cause and sustained future stability remain unproven. No vendor plugin code was modified or claimed repaired.

## Photographic review and planned teaching

DSC02260: the tall helmet decoration has actual volume; feet and the left lower prop are cut by the frame, while substantial ceiling remains. This cannot prove low-camera head enlargement. Under a costume-recording goal, test framing boundaries before changing posture; a vertical frame can sacrifice the horizontal prop or convention context, so check those edges. Under a companion-memory goal, closeness and the venue can remain useful.

DSC02268: the near cyan figure occupies the right side and overlaps background, not clearly the main subjects' helmet faces or chests. The lower-left prop end is now inside the frame; feet remain cut. For a clear two-person photograph, first wait for the passerby while keeping the main setup; for crowded-venue documentary intent, the foreground can be intentional. A lateral move changes overlap and background and needs a new check. The two photographs differ in pose/prop projection/framing and are not a controlled before/after pair. Do not diagnose softness from the resized inspection or assert unknown exposure settings.

## Verification and delivery outcomes

Both owner cases are now inside the existing course's boundary section, with actual original bytes served through registered media IDs. The original three gateways and all seven other course sections are byte-equivalent as parsed objects to the preserved reader checkpoint; the three unseen transfer photographs remain unseen before their exercise. No renderer/backend/state change was necessary.

Actual commands and results:

- `tools/build_photography_atlas.py --write` and `--check`: PASS; 14/71/247 unchanged, research version `19b735848812e291040621750932c518445a0d05650d6dc4c5c05e1529602909`.
- `.venv/Scripts/python.exe -X utf8 -m pytest -q tests/test_learning_course.py tests/test_learning_course_ui.py tests/test_learning_gateways.py tests/test_learning_gateways_ui.py tests/test_learning_content.py --basetemp=.local/owner-photo-regression`: 33 passed, 1 skipped (Windows symlink capability), 1 existing Starlette/httpx deprecation warning; 122.96s. Real HTTP/Chromium course regressions retain questions only, old records and no reading writes on desktop/mobile.
- Two real preview HTTP GETs returned 200, `image/jpeg`, `private, no-store`, exact original byte counts and matching registered SHA-256 hashes.
- In-app browser actually loaded both photos at intrinsic 7008×4672; after loading, `complete && naturalWidth > 0` is true for each. Both were inspected fully in the reader, with captions and explanations. The course has 0 input/assessment/save widgets and no document overflow. Screenshot: ignored `.local/owner-photo-recovery/course-owner-case.jpg`.
- Independent reviewer reread the integrated cases and source mappings, checked original and served-copy hashes, and found no major factual/provenance issue. They explicitly retained the not-a-controlled-pair and no-face-occlusion boundaries.
- `git diff --check`: PASS. The aggregate diff includes the preserved prior reader changes and unrelated work; it is not the current owned scope.

The prior preview was no longer listening after reopening. The attempted PowerShell background launch was blocked by tool policy before execution; the ordinary managed terminal launch of `tools/preview_learning.py --port 18771 --reference-url http://127.0.0.1:18765/` succeeded. The initial browser connection-refused/error-page attempts were not counted as successful UI verification. No daily database/service restart or network setting change was made.

Learning effect and the proposed reshoots remain for the owner to test. The plugin's current read/download path is verified, but the first intermittent internal error and earlier shared transport error have no proven vendor root cause. Publication is a separate requirement: preserve both the old sealed reader bytes and these new changes; no pre-existing changes may be silently staged under the new transaction.

## Authorized delivery recovery (2026-10-10)

The owner asked why the connection was reset and explicitly requested repair and submission. A current direct GitHub probe could not connect on port 443; the same read using the already enabled Windows proxy returned the expected branch SHA. This identifies a usable route for this attempt, not the component that caused the earlier reset. Each publishing subprocess uses the existing Windows proxy through temporary process configuration. Persistent Git configuration, system proxy, credentials, TLS verification and network settings remain unchanged.

The original question-only transaction `01a12461-924a-7630-a321-bb77bbc4eb39` was recovered using its exact sealed bytes and original identity. Its canonical retry succeeded: commit and verified remote SHA are both `027d3ad00b6fd3a34dbc3cdddeb277e11dd8304e`; the configured Notion record also succeeded. The previous photo transaction `01a12499-f8c2-7f93-9345-1e9be2e9dfd6` remains a historical failed receipt with `UNRESOLVED_PATH_OWNERSHIP`: two declared paths were already dirty in its immutable baseline. It was not retried, rebound or rewritten.

ROOT then started and declared the current actual turn transaction `01a124bd-4373-7472-b682-97df16cec64a` at the committed reader HEAD above, while all four photo target paths were clean or absent. Before replay, ROOT reviewed both receipts supplied by this new start and an independent review of the canonical recovery guards. This transaction replays the four previously verified owner-photo snapshots from ignored `.local/owner-photo-recovery/current-case-snapshot/`; it does not recapture a baseline for earlier edits. The three catalogue/bundle paths exactly match their saved SHA256 values. This task record preserves its original contents and appends this recovery evidence.

Keep the existing reader and media boundaries. The correction is delivery ordering and explicit replay ownership, without Publisher patches, relaxed checks, new acquisition code, photo-byte commits or unrelated cleanup. Fresh canonical, course/media/browser checks and final publication are pending below; previous successful UI and Drive evidence is historical evidence, not a new connection or learning-effect claim.

### Fresh replay verification

- `tools/build_photography_atlas.py --check`: PASS; research version remains `19b735848812e291040621750932c518445a0d05650d6dc4c5c05e1529602909`, with 14 domains, 71 modules and 247 skills.
- `.venv/Scripts/python.exe -X utf8 -m pytest -q tests/test_learning_course.py tests/test_learning_gateways.py tests/test_learning_content.py tests/test_learning_course_ui.py --basetemp=.local/owner-photo-publication-regression`: exit 0, 17 passed, 1 skipped (Windows symlink capability), 1 existing Starlette deprecation warning, 26.33s. Actual HTTP/Chromium regressions cover question-only reading, desktop/mobile, preserved records and media validation. HEAD stayed at the reader commit throughout this run.
- Fresh requests to both private media endpoints returned 200, `image/jpeg`, `private, no-store`; bytes and SHA256 matched the unchanged originals and served copies (17932314 and 18621715 bytes). No new Drive download or plugin repair is implied.
- Parsed scope comparison preserved all three other gateways and seven other course sections. The three replayed JSON files match their audited photo snapshots exactly. Unrelated `web/app.js` hash and unrelated untracked-file set are unchanged; Git index is empty. `git diff --check` passed.

These are fresh engineering checks for the replay. Final Git/Notion publication is reported separately by the canonical receipt; original images remain ignored and excluded from the four-path commit. User reading gains, reshoots and sustained plugin/network reliability remain unverified.
