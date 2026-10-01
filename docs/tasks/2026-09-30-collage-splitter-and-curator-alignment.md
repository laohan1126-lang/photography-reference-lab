# Collage Splitting Integration & Curator Skill Alignment — 2026-09-30

## User intent
1. **多宫格拆分接入主采集流**：上次探讨过多宫格拼图拆分为独立动作参考，用户发现新采集到的托尔图片依然存在未拆分的 6 宫格拼图，要求将拆分机制加进主流程中。
2. **Skill 协同对齐机制优化**：针对用户提出的“人类反馈可能存在直觉误判、AI 视觉能力强但若盲从会过拟合带偏”的问题，确立“用户随心处理一批 -> 批量发起复盘 -> AI 视觉会诊并提出建设性讨论/纠偏 -> 双方确认后落地 Skill”的人机协同闭环，并落实“光影失调 vs 意境逆光”辨析准则。

## Acceptance criteria
1. `tools/collect_adapter.py` 集成 `CollageSplitter`：在下载小红书等平台候选图片时，自动识别多宫格拼图（2x2, 2x3, 3x3, 6x6, 异构拼架等），并将每个有效子动作切片超采样重构为独立候选图（带【动作#01】标签与原出处元数据）。
2. 单图候选正常保留原逻辑；非拼图不受影响。
3. `C:\Users\Dell\.gemini\config\skills\cosplay-reference-curator\SKILL.md` 完整补充：
   - 图像切分与动作子卡评估规范；
   - 光影失衡 vs 艺术逆光辨析准则（防误杀）；
   - 人机协同对齐复盘工作流（Human-in-the-Loop Socratic Alignment SOP）。
4. 运行现有回归测试，确保测试全部通过。

## Implementation outcome
- **Changed**:
  1. `tools/collect_adapter.py`:
     - 引入 `CollageSplitter`、`ImageFilter`、`ImageEnhance`。
     - 增加 `process_and_expand_image` 管道：遇到多宫格拼图时自动执行几何边缘探测、子图裁剪、Lanczos 超采样高清重构与微反差锐化，将多宫格拼图自动拆展为独立候选卡，标记 `obtained_as="collage_slice"` 与 `【动作#N】` 标题；非拼图保留单图原生逻辑。
     - 在小红书、Pinterest、Bing 三处采集候选保存逻辑中统一切入 `process_and_expand_image`。
     - 在 Windows 运行时严格限定浏览器为 Edge，禁止静默 fallback 到未认证的 Chrome。
  2. `tests/test_collection_runner.py`:
     - 增加 `test_collage_splitting_expands_candidates` 单元测试，分别验证纯单图不切分与 2x2 拼图自动切分展开为多个单图候选。
  3. `C:\Users\Dell\.gemini\config\skills\cosplay-reference-curator\SKILL.md`:
     - 增加 Section 9：多宫格自动切解与子图独立赋权（Multi-Grid Auto-Slicing & Sub-Action Independence）。
     - 增加 Section 10：光影失衡 vs 艺术逆光辨析准则（Lighting Flaw vs. Artistic Low-Key & Silhouette）。
     - 增加 Section 11：人机协同对齐复盘工作流（Human-in-the-Loop Socratic Alignment SOP）。

- **Verified**:
  - `pytest tests/test_collection_runner.py -k "test_collage_splitting"`: **1 passed** (0.36s)。
  - `pytest tests/test_collection_runner.py`: **27 passed** (11.77s)。
  - `node --check web/app.js`: exit code 0。
  - 实测对用户托尔 6 宫格真实 Asset（`1bf5df6d...`）运行 `CollageSplitter`，成功识别 `shelf_grid_heterogeneous` 并精准切出 5 组独立子动作 boxes。

- **Status**: **VERIFIED**

---

## Extension: 小红书图集所有内页图片自动翻页抓取 (2026-09-30)

### User intent
用户要求：“动翻页抓取图集里的所有内页图片”。当小红书笔记包含多张图片（图集/轮播）时，不再局限于抓取第一张封面图，而是自动提取并抓取图集里的全部内页图片。

### Acceptance criteria
1. 在 `tools/collect_adapter.py` 的小红书采集流水线中，针对通过初筛的笔记卡片，导航至笔记详情页，提取图集（imageList）中的所有内页高分辨率图片 URL（优先从 `window.__INITIAL_STATE__.note.noteDetailMap` 提取原图 URL，DOM 轮播作为 fallback）。
2. 在该页面会话中批量拉取该图集所有内页的图像字节流，逐张经过 `validate_downloaded_image` 与 `process_and_expand_image`（若内页本身有多宫格拼图同样自动拆解），保留单图与切片独立候选卡。
3. 候选卡标题与元数据准确标注内页序数（如 `【P1/3】`, `【P2/3】` 等），保留原始笔记 URL、文案及 Tag。
4. 若详情页打开失败或无图集状态，平稳降级为使用搜索卡片的封面图，绝不使采集流程崩溃。
5. 补充针对图集内页提取与解包的自动化单元测试，现有所有测试全部保持通过。

### Implementation outcome
- **Changed**:
  1. `tools/collect_adapter.py`:
     - 升级 `fetch_xhs_detail_metadata`：通过客户端 `window.__INITIAL_STATE__.note.noteDetailMap` 原生读取图集全量 `imageList`（提取 `urlDefault` 及各尺寸场景），并以 DOM 轮播元素作为无状态环境下的降级兜底，提取完整 `gallery_urls`。
     - 新增 `download_gallery_images`：在当前浏览器会话上下文中批量并发 `fetch()` 图集图片并转化为 base64 字节流，支持按需截断并自动容错。
     - 升级 `fetch_bsk_candidates` 小红书候选主循环：对通过初筛的笔记自动获取图集所有内页图片，逐张校验尺寸/格式并送入 `process_and_expand_image`（若图集内页包含多宫格拼图同样自动展开），为每张内页独立生成带 `(P1/N)` 编号的 `PackCandidate` 候选卡，并在图集提取失败时平稳降级为封面图抓取。
  2. `tests/test_collection_runner.py`:
     - 新增 `test_xhs_gallery_slides_extraction_and_packaging` 自动化测试，验证图集批量下载、多内页候选元数据生成与 `PackCandidate` 严格模型合规性。

- **Verified**:
  - 实测真实小红书笔记（如双一 cosplay 图集 3 张、14 张样本）批量抓取成功，提取全部内页超清 WebP 原图。
  - `pytest tests/test_collection_runner.py`: **28 passed** (12.25s)。
  - `pytest tests/test_library.py tests/test_imports_jobs.py tests/test_workers.py tests/test_operations.py tests/test_personal_library.py tests/test_collection_runner.py`: **115 passed** (36.76s)。
  - `node --check web/app.js`: exit code 0。

- **Status**: **VERIFIED**


