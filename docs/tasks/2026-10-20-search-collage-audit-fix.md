# 六项缺陷修复、隔离验收与唯一真实搜索（2026-10-20 第二轮）

## 原始要求（用户本轮原文要点，代码改动前记录）

基线审计版本 `da25d715`。新建仓库内部工作树与 `codex/search-collage-audit-fix-20261020` 分支；
首次编辑前启动正式 Publisher 事务并记录六项修复要求和验收标准。保留原失败证据、人工决定及历史回执；
不合并 main、不切换日用服务、不写 Notion。实施顺序：**检测与完整性 → 恢复排重 → 统一计数 →
展示与计时 → 隔离验收 → 唯一真实搜索**。

### 六项缺陷（必须逐项关闭）

1. **拼图检测与记录完整性**：每轴最多自动拆 3 格与现有画质阈值不变；先检查更密网格与冲突分格，
   4/5 等分或互相冲突的边界返回 `needs_manual_crop`、有效数 0。派生记录增加 `algorithm_version`；
   旧版本不能直接复用为有效结果，只在明确的处理/恢复操作中先快照旧记录再重算；只读查询不迁移数据、
   不改写历史搜索回执。复用前验证原件/子图 SHA、路径边界与父子绑定；损坏文件保留、记录明确失败原因、
   排除计数，本轮不自动覆盖。轮询复用按“路径、预期 SHA、大小、修改时间”绑定完整性结果，文件变化后失效重验；
   打开图片仍校验完整 SHA，避免每秒重读全部原图。重算产生新 SHA 时不继承旧 SHA 的人工决定，旧决定与旧文件保留。
2. **恢复与历史排重**：恢复下载前把本 Job 已验证原件与有效子图共同恢复到排重索引（已处理记录可复用，
   但不跳过索引恢复）；历史未入库批次的有效子图也进入历史排重，沿用已有 SHA 与保守近似规则；
   本 Job 已有子图保持原状态，新出现的重复子图记录重复关系、不新增独立数量；计数与候选卡同时按 SHA 去重。
   Search、Review、人工选择仍分离，Review 只审原件。
3. **统一计数与网页表达**：Search 停止条件、队列 API、最终 summary 和 `counts.json` 共用同一计算逻辑，
   保留现有字段名；字段语义见下表。未处理、版本待更新或处理失败的记录不默认算作单图；处理中/失败显示明确状态；
   人工保留/淘汰不改写采集成果数量。
4. **展示与计时**：静态候选页生成时复制实际引用的有效子图，验证链接文件存在且 SHA 正确，复用已有文件、
   避免每次刷新重读全部原图；低清子图不进候选卡，文案改为“原拼图仍可查看”；删除 Pinterest 外层重复的
   `detail_navigate` 计时，保留实际导航计时、DOM 独立统计，总计与子阶段不得相加；旧报告追加更正
   （实际执行 5 条查询、其中 3 条产图；40.4 秒是首图保存时间；旧导航汇总存在重叠），原日志不改写。
5. **离线与网页验收**：审计复现转为“正确行为”回归并确认旧版本失败、新版本通过；执行本次审计的
   34 项定向回归及受影响的索引/恢复/计数测试；两批旧真实图片隔离副本复验原件 SHA、裁切坐标与像素，
   不改原始证据目录；用本机 Edge 与已有 `LAB_CHROMIUM` 配置完成网页检查（父图/子图打开、保留、淘汰、撤销、
   刷新、重启一致），保存截图、图片加载结果与日志；浏览器检查受阻须记未通过。
6. **唯一一次真实搜索**：渡边曜 / Love Live! Sunshine!!、服装不限、15 张名称命中的可用独立照片、
   小红书 + Pinterest、正常 BrowserSkill 路径、独立数据目录与端口、正常启动器、`LAB_AUTO_CLASSIFY=0`、
   不启动 AI Review、单 Job、15 分钟；冻结代码 SHA、查询计划、历史范围、目标、阈值与预算；
   点击前启动网页观察，记录首图保存、首图加载可见、第 5/10/15 张可用、总时长、停止原因；
   结束后重启隔离服务核对保持。不足 15 张如实记录；本轮未出现合格拼图时明确记录“真实搜索未覆盖有效子图路径”。
   保留历史排重，运行时长只作观察，不作严格性能 A/B。

### 统一计数语义（保留现有字段名）

| 字段含义 | 统一规则 |
|---|---|
| 已下载原图 `found` | 已收到的唯一原件数 |
| 原件名称命中 `target_confirmed` | 只统计原件，不加子图 |
| 原始独立单图 `original_singles` | 当前规则确认非拼图且文件完整的原件 |
| 拼图有效子图 `derived_valid` | 完整、合格、按 SHA 去重后的子图 |
| 实际可用独立照片 `usable_independent` | 合格单图与有效子图的唯一 SHA 并集 |
| 其中名称命中 `usable_named` | 上述可用照片中有名称命中关联的子集；搜索按此达标 |
| 待人工裁切／未确认 `awaiting_manual` | 按原件去重统计未解决的裁切、画质或相关性问题；正常拆分成功不计入 |

## 基线与事务

- 基线提交：`da25d7156465925e343e8611a0e6de6663f9cc8a`。
- 工作树：`.local/worktrees/search-collage-audit-fix-20261020/root`；分支
  `codex/search-collage-audit-fix-20261020`。
- Publisher：task `search-collage-audit-fix-20261020`（host `manual`，session `dsh-turn2-auditfix`），
  `start` 于 2026-10-20T11:19:25Z，contract digest
  `ea544f27fa9fd36b97313528558f3371e5efa33b1d6d17dc2d7b7089b228cfd1`，六项 requirement：
  `R1-collage-detection-integrity`、`R2-restore-history-dedupe`、`R3-unified-counts`、
  `R4-display-timing`、`R5-isolated-web-acceptance`、`R6-single-real-search`。
- 隔离验收环境：独立数据目录、独立端口、正常启动器；`LAB_CHROMIUM` 指向本机
  `C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe`（155.0.4283.62）。
- 原始证据只读：上一轮 `.local/worktrees/search-perf-collage-20261020/root/.local/` 与旧运行目录
  不在此分支改写；复验只用隔离副本。

## 验收矩阵（先写成“正确行为”回归）

| 场景 | 必须达到的结果 |
|---|---|
| 4×1、1×4、4×4、2×4、5 行网格 | 待人工裁切，不产生可计数的拼图大块 |
| A/B 拆分后中断，恢复再收到 A/C | 只有 3 张独立子图；旧人工决定不变 |
| 未入库历史子图再次出现 | 按既有规则判重 |
| 子图缺失、损坏，或原件 SHA 改变 | 不沿用有效状态，不计入目标，异常可见 |
| 一张名称命中拼图拆出两张 | 原件 1、原件名称命中 1、有效子图 2、可用 2、待人工 0 |
| 静态页与候选网页 | 所有有效图片实际加载成功 |
| 四次 Pinterest 导航 | 四条实际导航记录，无同名嵌套重复汇总 |

## 修复对应表

| # | 缺陷 | 修复位置 | 状态 |
|---|---|---|---|
| 1 | 密网格/冲突、版本、完整性、轮询缓存、新 SHA 不继承决定 | `ref_lab/collage.py`（`ALGORITHM_VERSION=2`、`_axis_decision`、`verify_record`、快照迁移）、`ref_lab/integrity.py`（按路径/大小/mtime 缓存，文件变化失效） | 已完成 |
| 2 | 恢复索引、历史子图、本 Job 子图去重 | `ref_lab/collection_history.py`（历史 `derived.json` 的有效子图入索引）、`tools/collect_verified.py::restore_history_index`（下载前恢复原件+有效子图）、`ref_lab/collage.py`（known_shas/重复关系）、`collection_queue._derived_rows`（卡片按 SHA 去重） | 已完成 |
| 3 | 统一计数 | 新 `ref_lab/collection_counts.py::compute`；Search 停止条件、队列 API、`search-summary.json`、`counts.json` 全部调用同一函数（`counts_source` 字段可核） | 已完成 |
| 4 | 静态页子图、文案、计时去重、旧报告更正 | `tools/collect_verified.py::render_search_gallery`（复制并校验子图/复用/失败可见）、`web/app.js`（低清与旧版本文案、待处理/待更新/完整性异常状态）、`receive()` 删除外层 `detail_navigate`、上一轮任务文档追加更正 | 已完成 |
| 5 | 34 项定向回归、两批旧图、Edge 网页验收 | `tests/test_collage_audit.py`（25 项）、`tests/test_collection_audit.py`（10 项）、`tools/verify_collage_batches.py`、`.local/acceptance-web-20261020/` | 见下 |
| 6 | 唯一真实搜索 | 独立数据目录 `.local/ui-data-search-20261020`、端口 18792、`.local/run-30-20261020/` | 见下 |

## 回归与验收证据

### 定向回归（35 项审计用例）

```powershell
.venv\Scripts\python.exe -X utf8 -m pytest -q --basetemp D:\prl-audit-tests\e ^
  tests\test_collage_audit.py tests\test_collection_audit.py
# 35 passed
```

覆盖：4×1/1×4/4×4/2×4/5 行 → `needs_manual_crop` 且 0 可用；支持的 1×2/2×1/2×2/3×1/3×3 仍正常；
更密网格不回退成 2 大块；旧版本记录只读视图报“待更新”且不迁移、显式处理先快照再重算；
损坏/缺失子图与改动原件保留现场、不覆盖、排除计数；路径越界/父子绑定错误整条记录失败；
完整性缓存随文件变化失效；重算新 SHA 不继承旧决定且旧文件/旧决定保留；重复处理复用；
一图两格 = 原件 1/名称命中 1/子图 2/可用 2/待人工 0；重复子图跨父图只计一次；
队列、compute、summary 数字一致；人工保留不改变采集数量；历史有效子图入索引、旧版本与损坏子图不入；
恢复同时登记原件与有效子图；静态页复制并校验每个子图、低清页承诺“原拼图仍可查看”；
Pinterest 每次导航只记录一个 `detail_navigate`。

相关历史回归（不重复跑与本轮无关的套件）：

```powershell
.venv\Scripts\python.exe -X utf8 -m pytest -q --basetemp D:\prl-audit-tests\e ^
  tests\test_search_relevance_regression.py tests\test_search_relevance_interaction.py ^
  tests\test_collection_stages.py tests\test_collection_job_recovery.py tests\test_collection_runner.py ^
  tests\test_collection_contract.py tests\test_collection_resume.py tests\test_collection_history_cache.py ^
  tests\test_verified_collection.py tests\test_review_baseline_consistency.py tests\test_imports_jobs.py ^
  tests\test_personal_library.py tests\test_search_continue_recovery.py tests\test_candidate_decision_sync.py ^
  tests\test_review_sample_limit.py tests\test_review_self_duplicate.py ^
  tests\test_collage_split.py tests\test_search_detail_timing.py tests\test_collage_project_sync.py ^
  tests\test_collage_audit.py tests\test_collection_audit.py
# 248 passed, 1 warning（含 35 项审计用例；
#  注意 --basetemp 必须用短路径，放在 .local/worktrees 深处会触发 Windows 路径长度问题）
```

### 旧版本失败 / 新版本通过（同一探针，`.local/audit-behavior-probe.py`）

| 场景 | 旧 `da25d715` | 新代码 |
|---|---|---|
| 4×1 网格 | `split_partial / grid_2x1`，2 块 800×1199/1200 | `needs_manual_crop`，0 子图，`dense_grid_4_part` |
| 无版本记录 | `reused=true`，无快照 | 重算 v2，快照 1 份 |
| 损坏子图 | `reused=true`，损坏文件仍 `valid` | `split_partial`，该子图 `corrupt`，文件保留，兄弟子图仍有效 |
| 历史未入库子图 | 未入索引 | 入索引 |
| 静态候选页 | 引用子图但**不复制**（链接 404） | 引用并复制，SHA 校验 |
| Pinterest 导航 span | 2 个同名嵌套 | 1 个 |

原始输出：`.local/acceptance-web-20261020/old-behavior.json`、`new-behavior.json`。

### 两批旧真实图片隔离副本复验（不改原始证据）

```powershell
.venv\Scripts\python.exe -X utf8 -m tools.verify_collage_batches ^
  --batch .local\verify-batches\run-15 --batch .local\verify-batches\run-20
```

- run-15（上一轮 18 张）：5 张拼图（4 拆分成功、1 低画质）、11 张有效子图；原图 SHA 全部未变；
  每个子图的裁切矩形/尺寸/文件 SHA 与**重新裁切的像素逐点一致**，0 problems。
- run-20（上一轮渡边曜 20 张）：1 张 3×3 白缝九宫格 → 9 张低画质拒绝、0 有效；原图 SHA 未变；0 problems。
- 报告：`.local/verify-batches/verification.json`。

### Edge 网页验收（`LAB_CHROMIUM` = 本机 msedge.exe 155.0.4283.62）

`.local/acceptance-web-20261020/web_check.py` → **22/22 PASS**，截图 4 张与 `web-acceptance.json`：

- 候选图库 5 张卡片（1 单图、1 个 2×1 父图 + 2 张有效子图、1 个低画质 3×3 父图）；
- 页面所有图片 `complete && naturalWidth>0`，逐个 `fetch→createImageBitmap` 解码成功（200，字节数一致）；
- 点击“打开原图/打开子图”新标签页 URL 正确并解码成功；
- 低画质父图显示“原拼图仍可查看”，没有子图卡片；
- 人工保留写穿到项目引用（`decision=keep`、`decision_origin=human_candidate_queue`），不是 AI 通过；
- 人工淘汰 → 撤销 → 刷新 → 重启隔离服务，队列与项目决定一致；可用/名称命中/子图计数重启后不变；
- 无页面脚本错误。

## 唯一真实搜索（阶段 6，结果见下）


## 进展

- 2026-10-20：创建独立工作树与分支；Publisher 事务与六项 contract 已声明；读取基线代码与本机
  Edge/`LAB_CHROMIUM` 环境；开始按顺序实现，先做检测与完整性。

## 唯一真实搜索的执行记录（Job 4a81ff48…）

- 网页入口（Edge + `LAB_CHROMIUM`）填写表单并点击“开始搜图”创建 Job；
  冻结输入：`.local/run-30-20261020/frozen-inputs.json`（代码 SHA `f985ce9f1490…`、8 条查询、15 张、900 秒、
  历史 1400 张、算法 v2 与画质/接缝阈值）。
- 第一次尝试（22:44）：`process_failed`，2 秒内退出、0 下载。保存了回执
  `search-summary-attempt1-process_failed.json`。**根因不是产品搜索逻辑**：本轮审计探针在 `.local` 下留下了
  一个带**相对路径**子图的私有 run 目录，历史索引按“无法证明不重复”拒绝启动（
  `Historical derived tile is missing`）。删除探针残留后历史索引恢复 1400 张。
- 诊断期间手工执行的一次采集已下载 8 张真实图片；它们没有经过网站阶段导入，也没有计入本 Job。
  为避免把诊断数据混入验收，整个 run 目录已归档到 `.local/backups/run-30-diagnostic-1-<ts>/`
  （历史扫描不包含 `backups`），没有删除原图字节。
- 第二次尝试（22:57，同一 Job、同一冻结目标/查询/规则）：通过网页“开始搜图”调用的同一个
  `/api/jobs/{id}/start` 端点重启；这是重试同一任务，不是第二个 Job。

### 真实搜索结果（第二次尝试；唯一 Job，15 分钟预算内）

| 指标 | 实测 |
|---|---|
| 停止状态 / 原因 | `completed` / `target_reached`（名称命中可用 16 ≥ 15） |
| 首张原图保存 | **68.23 秒**（服务端 `acquired_at`） |
| 首张原图网页可见 | **69.3 秒**（观察器首个 found=3 事件；页面轮询 ≤1 秒） |
| 首张可用独立照片 | **68.23 秒**（与首图同批） |
| 第 5 / 10 / 15 张可用 | **95.87 / 374.01 / 403.47 秒**（页面 96.8 / 375.8 / 404.3 秒） |
| 搜索总 wall time | **406.98 秒**（attempt start→finished；采集器 `elapsed_seconds` 395.75） |
| 已下载原图 | **19**（小红书 16 / Pinterest 3；唯一 SHA 19） |
| 名称命中 / 探索未确认 | **16 / 3** |
| 原始独立单图 | **17** |
| 拼图 | **2**：`2×1` 拆分成功 → 2 张有效子图；`dense_grid_5_part` → 待人工裁切、0 子图 |
| 拼图有效子图 | **2** |
| 实际可用独立照片 | **19**（其中名称命中 **16**） |
| 待人工裁切 / 未确认 | **4**（3 张探索 + 1 张待人工裁切拼图） |
| 去重 / 无效 | **0 / 0** |
| 模型调用 / Token | **0 / 0**（无 attempt/calls 目录，未启动 Review） |
| 历史排重 | 启动前已知 1400 张；本轮 0 重复、0 错误 |

执行查询（8 条计划中实际产生候选的 4 条；达到目标即停）：

| 来源 | 查询 | 下载 | 名称命中 |
|---|---|---|---|
| 小红书 | `渡辺曜 Love Live! Sunshine!! cos 摄影` | 7 | 7 |
| 小红书 | `渡辺 曜 cos 棚拍` | 8 | 8 |
| 小红书 | `You Watanabe cos 场照` | 1 | 1 |
| Pinterest | `You Watanabe Love Live! Sunshine!! cosplay photography` | 3 | 0（3 张探索） |

阶段耗时（本轮 `timings.jsonl`，新增计时）：

| 阶段 | 次数 | 合计 | 均值 |
|---|---|---|---|
| `browser_receive` | 19 | 275.95 秒 | 14.52 秒 |
| └ `detail_download` | 30 | **143.94 秒** | 4.80 秒 |
| └ `detail_return` | 17 | **85.33 秒** | 5.02 秒 |
| └ `detail_click` | 15 | 17.77 秒 | 1.18 秒 |
| └ `detail_dom_wait` | 19 | 10.62 秒 | 0.56 秒 |
| └ `detail_navigate`（Pinterest，每次导航仅 1 条） | 4 | 7.47 秒 | 1.87 秒 |
| └ `detail_locate` | 13 | 6.09 秒 | 0.47 秒 |
| └ `detail_store` | 26 | 2.41 秒 | 0.09 秒 |
| `browser_search` / `browser_more` | 5 / 4 | 48.00 / 12.50 秒 | 9.60 / 3.12 秒 |
| `discovery_preview` | 22 | 45.28 秒 | 2.06 秒 |
| `history_consider` | 30 | 3.35 秒 | 0.11 秒 |

结论：数量达标（16 张名称命中可用独立照片），**且真实搜索覆盖了有效子图路径**（2×1 拼图贡献 2 张），
同时正确拒绝了一个 6 格证件照排版（`needs_manual_crop`，没有切出可计数的“大块”）。
本机时间只作观察：与上一轮不是同角色/同查询/同网络结果，不能当严格性能 A/B。

### 结束后网页证据（Edge + LAB_CHROMIUM，`search_run_check.py` → 9/9 PASS）

- 候选图库 21 张卡片（19 原件 + 2 子图），全部 `fetch → createImageBitmap` 解码成功、HTTP 200；
- 项目导入 21 条 pending 引用（19 原件 + 2 子图），没有 AI 通过、没有人工决定被自动写入；
- 待人工裁切卡片明确显示 `dense_grid_5_part` 与“原拼图仍可查看”；
- 静态候选页引用的 21 个文件全部存在且文件名 SHA 与内容一致；
- 重启隔离服务后：计数（19/16/2）、项目引用和图片加载保持；页面无脚本错误。
- 证据：`.local/acceptance-web-20261020/search-run-web.json`、`search-01-gallery.png`、`search-02-after-restart.png`。

### 本轮未覆盖 / 限制

- 真实搜索是**全新尝试**（attempt 2 的 run 目录为空），因此没有实际触发“恢复下载前重建索引”的运行时路径；
  该路径由 `test_restore_registers_originals_and_verified_tiles` 等回归覆盖，并在旧版本探针中显示缺失。
- 历史排重使上一轮同图（若出现）被排除；本轮未出现同图，重复计数为 0。
- 没有运行 AI Review、没有人工审美评价；3 张 Pinterest 探索图分辨率偏低，由用户自行取舍。
- 若后续要验证“真实搜索 + 中断恢复”的组合，需要另建任务；本轮按“不再建第二个 Job”停止。

## 发布事务与失败恢复（Git-only）

- 首次事务（同一 task id，session `dsh-turn2-auditfix`，基线指纹 `18df9192…`）在提交前通过 Publisher 的
  暂存差异检查时失败：`tests/test_collage_audit.py:306: new blank line at EOF.`。失败发生在 `git add` 之后、
  `git commit` 之前，Publisher 记 `commit_sha = null`、receipt = FAILED：没有产生提交，也没有推送。
  状态导出保存在 `.local/publisher-status.json`；原任务目录逐字节归档到
  `C:\Users\Dell\.codex\task-finalization-data\archive\`，仓库内副本在
  `.local/backups/publisher-attempt1-20261020-<时间戳>/`。
- 恢复方式：Publisher 的 retry 只对“已持久化 prepared tree 的提交意图”做人工对账，而本失败点在 prepared tree
  记录之前，原事务无法继续；因此归档失败事务后，在同一 task id 上重建事务：baseline 记录当时已完成的
  15 个改动路径，contract 用 `preexisting_path_authorization` 精确声明这 15 条及证据，seal 按当前内容重新计算哈希。
  这是发布事务的重建，不是代码改动；失败回执、旧 manifest 与事件日志都保留。
- 已删除测试文件末尾多余的空行；提交前手动复核 `git diff --cached --check` 为 CLEAN（Publisher 提交时还会再查一次）。
- Notion：本轮按用户边界不写入。运行 Publisher 时用临时 `TF_GLOBAL_CONFIG`
  （`.local/publisher-global-no-notion.json`）把 notion 凭据来源改为进程环境且不提供 token；`notion_ops.publish`
  在 preflight 即返回 `NOTION_TOKEN_MISSING`，**不发起任何 Notion API 请求**，Publisher 记 `FAILED_PENDING`
  （待授权补写，不是成功写入）。本轮授权只覆盖 Git 推送。
- 本次提交的 commit SHA 记录在 Publisher `receipt.json`
  （`C:\Users\Dell\.codex\task-finalization-data\tasks\bee3f2a78204f0e34c1a193ff010ef8b\receipt.json`）
  与最终交接消息中；本文件本身属于提交内容，无法在提交前写入该 SHA。
