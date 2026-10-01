# Mobile View Optimization, Rejection Reason Extension, and Collector Hardening — 2026-10-01

## User Intent and Boundaries

1. **Mobile Experience & Pose Card Usability**:
   - User requested: "能不能改成比如图片三分之二大 左边留出来 给那个制作过卡的就放制作卡那些指示 没做卡的就只显示图片 这样能边看图边看怎么拍"
   - Requirement: On mobile viewports (< 768px), display a split view where images with pose field cards take up 2/3 width on the right, and the left 1/3 panel cleanly presents verbal cues (🗣️ 现场口令, 📸 摄影动作, 🛡️ 降级方案). Uncarded references expand to full width (100%).
2. **Rejection Reason Extension**:
   - User requested: "淘汰原因加上无关角色选项"
   - Requirement: Include "无关角色" in the rejection modal and ensure the quick rejection options reflect this common failure mode.
3. **Elimination of Commercial & Recruitment Post Noise**:
   - User reported: "最近两次都是 好几张广告图 我排除理由也给了 怎么又这么高频出现这些问题了 还好几个这种和场照正片没关系的东西" (Reference: `想出云瑶拍正片求一个擅长左位质量高的搭子`, containing mannequin costume on white background, recruitment chat text screenshot, green prop wings on floor).
   - Requirement: Eliminate non-photoshoot posts (team recruitment "求搭子/组队/招募", props/wings "道具/翅膀", white-background mannequins/e-commerce product listings, note/chat screenshots).

## Implemented Changes

1. **Mobile Split View Layout (`web/app.js`, `web/styles.css`)**:
   - Added responsive mobile split container `.mobile-split-card-view` and `.mobile-card-summary`.
   - Displays cue highlights with distinct badges for quick field directing.
   - For references without a card, displays the reference photo edge-to-edge without cramped padding.
2. **Rejection Modal Options (`web/app.js`)**:
   - Added "无关角色" to standard rejection reason categories.
3. **Collector Anti-Noise Hardening (`tools/collect_adapter.py`)**:
   - Added noise keywords to `NEGATIVE_TYPE_MARKERS`: `搭子`, `求搭子`, `找搭子`, `求一个`, `蹲搭子`, `组队`, `扩列`, `招募`, `约拍搭子`, `求队友`, `道具展示`, `道具制作`, `自制道具`, `道具自制`, `翅膀`, `聊天记录`, `求问`, `问问`, `求返图`, `捞返图`, `求图`, `有没有人拍到`, `捞捞`, `对镜自拍`, `对镜拍`, `试衣间`, `各家`, `出格裙`, `山正`, `好价`, `急抛`, `拼单`.
   - Made `require_cosplay` default to `True` in `build_policy(job)` unless explicitly opted out with non-cosplay hints.
   - Implemented fast pure-white pixel ratio filter in `validate_downloaded_image`: downsizes image to 64x64 and calculates `white_ratio` (RGB > 240, 240, 240). Images with `white_ratio > 0.60` (such as mannequins on pure white e-commerce backgrounds and note screenshots) are rejected immediately.
   - Added secondary slide deduplication: checks perceptual hash distance against previously ingested slides of the same post (`hamming_distance < 6`).
4. **Data Cleanup**:
   - Cleaned up lingering bad references from the recruitment post in project `瑶` (`44e0be71`, `a5bccfd7`, `5babbb1c`) in `data/library.sqlite3` with `decision='reject'`, `rejection_reason='人台道具/组队招募贴/非正片'`.

## Verification Evidence

1. **Python Core Regression**:
   - `python -m pytest -q tests/test_library.py tests/test_imports_jobs.py tests/test_workers.py tests/test_operations.py tests/test_personal_library.py tests/test_collection_runner.py tests/test_collect_adapter.py tests/test_confirmed_archive.py`: **141 passed, 0 failed**.
2. **UI & Browser Regression**:
   - `python -m pytest -q tests/test_ui_components.py tests/test_collection_ui.py`: **18 passed, 0 failed**.
3. **JavaScript Syntax Verification**:
   - `node --check web/app.js`: exit 0.
4. **Collector Test Suite**:
   - `pytest -q tests/test_collect_adapter.py`: **21 passed, 0 failed** (verifying metadata filtering, synthetic images, perceptual hash deduplication, aspect ratios).
