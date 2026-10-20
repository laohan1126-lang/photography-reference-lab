# 第二轮审计修复、主项目整合与主项目真实搜图验收（2026-10-21）

## 原始要求（用户本轮原文要点，代码改动前记录）

基线 `7c0773c5a85c51defd082fb86d787953462d74b6`。先读第二轮独立审计报告
`.local/audit-dsh2-20261020/audit.md` 及其复现结果，再分两阶段：

- **阶段 A 修复与隔离验收**：禁止合并 main、切换日用服务或写正式资料库。
- **阶段 B**：阶段 A 全部达标后，授权把修复整合进主项目、合并 main，并受控切换日用服务；
  最终在主项目完成真实搜图验收。

本轮“完整结果”= 从主项目正常网页发起快速搜图，获得目标数量的新增独立照片，原件、合格子图、来源、
计数和项目引用完整保存，能够打开、刷新并在重启后继续使用。不包含 AI 身份审核或替用户作审美决定。

所有工作树、测试目录、备份和证据都放在 `D:\AI PROJECTS\photography-reference-lab\.local\` 内。

### 阶段 A 必须关闭的缺陷

1. **旧记录升级后的自身重复**：旧版本子图已入库时，新版本重算不能把本 Job 自己的子图判为外部历史重复
   （可用数从 2 变 0）。要求：用本 Job 的旧记录、父子绑定及发现关系确认来源身份；旧记录仍须重新验证、
   按当前算法重算；重算得到相同 SHA 时保留本 Job 成果身份及原人工决定；重算产生新 SHA 时不继承旧 SHA
   的人工决定；外部历史重复继续排除；原件、旧子图、旧决定与迁移快照保留。
2. **名称关联计数**：照片唯一性与名称命中关联分别聚合。未确认父图 A/B、名称命中父图 A/C → 独立 3、
   名称命中 2；调换顺序结果相同；第二个 A 记为本轮重复时名称关联仍保留；外部历史重复不增加可用数量；
   队列卡片名称标签、搜索停止条件和最终计数一致，名称命中仍只是发现信息。
3. **部分画质失败的待处理计数**：一张拼图一个合格子图、一个模糊子图 → 可用 1、待人工处理原件 1、
   合格兄弟子图保留；按原件去重统计；纯重复排除不算画质或裁切问题。
4. **文案与验收记录**：顶部说明和单卡说明统一（低清子图不进入候选卡，原拼图仍可查看）；
   “实际可用独立照片”与“其中名称命中”按真实口径解释；旧报告追加更正（不覆盖原日志）：
   排重记录是 14 条；诊断批次 8 张原图全部再次出现在正式结果中，其中 5 张名称命中，扣除后该次新增名称
   命中独立照片为 11 张；69.3 秒改称 API 首次观察时间；406.98 秒仅第二次尝试，首次点击到最终结束约
   19 分 44 秒；诊断下载也必须进入历史登记（允许归档文件，但不能退出排重范围）。

### 阶段 A 通过门槛

先让新增回归在旧版本失败，再验证修复后通过；不能只检查 mock 调用。必须覆盖：

| 场景 | 预期 |
|---|---|
| 旧版本记录＋已入库子图＋新算法迁移 | 相同两张子图仍计 2，人工决定不变 |
| 相同内容来自外部历史 | 正确排重，不新增数量 |
| A/B → 中断 → 恢复 → A/C | 唯一子图 3，不重复计数 |
| 未确认 A/B＋名称命中 A/C | 独立 3、名称命中 2，与顺序无关 |
| 一个合格、一个模糊子图 | 可用 1、待处理原件 1 |
| 刷新、重启、重复迁移 | 数量、文件与人工决定保持一致 |

同时执行已有 69 项相关回归及受影响的相邻检查；隔离数据验证父子图打开、保留、淘汰、撤销、刷新和重启；
检查队列、summary、持久化计数与项目引用语义一致。阶段 A 不再单独做真实平台搜索。

### 阶段 B 与最终验收

- 主项目 `D:\AI PROJECTS\photography-reference-lab`，本轮开始时实际在
  `codex/learning-loop-v1-20261018`、HEAD `3284cf1`（并非 main，且含修复分支没有的后续改动）；
  执行时重新核对，不能直接切到旧 main 造成功能倒退。
- 记录分支/HEAD/未提交改动/实际 `LAB_DATA_DIR`/入口/进程；用项目正式备份方式备份并隔离验证恢复；
  在仓库内部集成工作树以当前主目录完整版本为基础合入修复；检查冲突涉及的调用方、共享网页组件与既有
  学习入口；通过后合并 main、受控切换主目录代码与日用服务；服务端与采集适配器同一版本；保留回退入口。
- 最终验收：主项目日用网页发起，渡边曜／Love Live! Sunshine!!、服装不限、快速搜图、小红书＋Pinterest、
  目标 15 张新增名称命中可用独立照片、单 Job 主动采集累计预算 15 分钟；冻结版本/输入/查询/历史范围/
  目标/预算；历史含正式库、既有真实批次与前轮诊断下载；不另跑隐藏诊断采集、不清空 run、不重置预算、
  不降低阈值、不用旧图凑数；需要恢复时沿用同一 Job 成果与累计预算；不启动 AI Review；浏览器观察在
  点击前开始，分别记录原件保存、图片实际加载可见、目标达成与总耗时。
- 不足 15 张时保留全部成果，报告实际数量和阻塞，最终验收标为未通过；不换 Job、不改口径。

## 本工作树

- 分支 `codex/search-integration-20261021`，基线 `7c0773c5a85c51defd082fb86d787953462d74b6`，
  工作树 `.local/worktrees/search-integration-20261021/root`。
- 阶段 A 只在此工作树与 `.local/` 隔离数据内改动；主目录与 18765 不触碰。

## 进展记录

### 2026-10-21 阶段 A 开始

- 已读审计报告、复现脚本与 `probe-results.json`；复现三项缺陷：`upgrade_own_crops` 从 2 变 0、
  `named_association` 顺序 1/2 不一致、`partial_quality` 为 `awaiting_manual=0`。
- 先写新回归 `tests/test_collection_upgrade_counts.py` 与历史归档排重回归，确认它们在 `7c0773c` 上失败，
  再改实现。

### 2026-10-21 阶段 A 结果

**先失败、后通过（同一命令、同一 venv）**

- 基线 `7c0773c`：`tests/test_collection_upgrade_counts.py` **5 failed / 3 passed**，
  `tests/test_collection_history_cache.py` **1 failed / 8 passed**。失败点正是审计三项缺陷与
  “归档诊断不入排重”。
- 修复后同一组测试 **17 passed**。

**修复内容**

1. `ref_lab/collage.py::process_original`：旧版本记录重算前，按“本 Job 旧记录 + 父子绑定 +
   文件 SHA”确认本 Job 自己的旧子图身份，先从外部历史索引中排除这些 SHA，再让当前算法重新判定状态；
   相同 SHA 记 `own_previous_result`（保留成果身份，人工决定仍按 SHA 保存在原文件），新 SHA 不继承旧决定；
   外部历史重复照旧排除；旧记录快照、旧子图文件、旧决定全部保留。
2. `ref_lab/collection_counts.py`：照片唯一性与名称命中关联分开聚合，最后求
   `usable & named_associations` 交集；名称关联可由任一父图（含本轮重复子图）提供，但只对 `usable`
   里的照片生效。待处理按原件去重：一个合格子图加一个模糊/损坏子图仍记 1 个原件待处理；纯重复排除不算
   画质或裁切问题。
3. `ref_lab/collection_history.py`：历史扫描不再跳过 `.local/backups`，归档的诊断批次仍进入排重范围。
4. `web/app.js`：顶部说明与单卡说明统一为“低清/不合格子图不进入候选卡、原拼图仍可查看”，
   “实际可用独立照片”“其中名称命中”按唯一照片交集解释。
5. 旧报告 `docs/tasks/2026-10-20-search-collage-audit-fix.md` 追加更正（不改原文）：排重 14 条、
   诊断 8 张全部重现（5 张名称命中，扣除后新增 11 张）、69.3 秒改称 API 首次观察、
   406.98 秒仅第二次尝试（首次点击到结束 1183.92 秒）、诊断下载须留在历史登记。
6. 两个陈旧测试期望（此前因缺 Chromium 被 skip，在 `7c0773c` 上同样失败）：
   `test_candidate_queue_shows_acquired_originals_and_keeps_human_decision` 改用当前标签
   `已下载原图`；`test_failed_note_open_does_not_navigate_back_out_of_valid_search` 允许只读 DOM 探测的
   `evaluate`，仍断言不发生导航返回。

**独立复现（`.local/verify-round3-20261021/probe.py` → `probe-round3-results.json`）**

| 审计复现 | 修复前 | 修复后 |
|---|---|---|
| 旧记录＋已入库子图＋新算法重算 | 可用 2→**0**，两子图 `duplicate_history` | 可用 **2**，两子图 `valid`，同 SHA，决定 keep、快照与旧文件都在 |
| 未确认 A/B＋名称 A/C | 顺序 1 / 2 不一致 | 两种顺序均 独立 **3**、名称 **2**；第二个 A 为 `duplicate_run` |
| 一个合格＋一个模糊子图 | 可用 1、待处理 **0** | 可用 **1**、待处理 **1**、合格兄弟保留 |
| 队列 / summary / 持久化计数 | — | 7 个关键字段三者完全一致 |

**隔离网页验收（`.local/verify-round3-20261021/web_verify.py`，Edge headless，18766）**

- 独立 `LAB_DATA_DIR`，通过正常 HTTP API 建项目与快速搜图 Job，再写入该 Job 的 run 目录：
  2×1 名称命中拼图（2 合格子图）、部分画质拼图（1 合格 + 1 模糊）、1 张探索单图。
- 队列显示 6 张卡（3 原件 + 3 合格子图），**模糊子图没有候选卡**；6 张图片全部解码成功
  （`img.decode()` + naturalWidth）；计数：已下载 3、名称命中 2、可用 **4**、其中名称命中 **3**、
  待人工 **2**。
- 子图“人工保留”：可用数不变、`已通过` 1、`human-decisions.json` 写入 keep；单图“人工淘汰”后
  `审核拒绝` 1、可用仍 4；“撤销人工决定”后回到待审；刷新后决定与图片仍在；重启服务后
  API 计数（4/3）与 6 张图片解码保持。截图 `web-01-queue.png`…`web-04-after-restart.png`。

**相关回归**：`collage/collection/search/verified/candidate/review_sample` 全部 29 个文件
**337 passed, 1 warning, 303.25 s**（安装 Playwright Chromium 后包含 22 项组件/浏览器检查；
先前 69 项为其中子集）。同日还验证：长临时路径（>260 字符）会让 Windows `os.replace` 报
`ERROR_PATH_NOT_FOUND`，4 项测试因此误失败；换成短临时目录后 **10 passed**，属测试环境路径长度问题，
不是产品回归。

## 阶段 B：备份、集成与日用切换

### 切换前主目录事实

- 分支 `codex/learning-loop-v1-20261018`，HEAD `3284cf1c88a131ba14de6657f7ee408e8e95bf71`（**不是 main**）。
  未提交改动只有 4 个被删除的旧测试临时文件（`.pytest-tmp-learning-review/…`、`tmpu82yxeyy/…`、
  `tmpye_gx0i8/…`），与本任务无关，未暂存、未提交。
- 实际数据目录：`.local/windows-runtime.json` 的 `d:\AI PROJECTS\photography-reference-lab\data`
  （255 个 asset 目录、`library.sqlite3` 12.7 MB、整目录 830 MB）。`LAB_DATA_DIR` 环境变量为空。
- 服务入口：`python -m ref_lab serve --host 127.0.0.1 --port 18765`，PID 10140/48188；
  正式入口为 `start.bat` → `scripts/launch.ps1`（受管 PID 记录在 `.local/runtime/server.json`）。
- `main` 当时在 `db4bcb0`，是 `3284cf1` 与修复分支的祖先，不能直接切过去。

### 备份与隔离恢复

- `python -m ref_lab backup --output .local/backups/library-before-integration-20261021-1.zip`：
  **1177 个原图、483.4 MB**，不含密钥。
- 解压到 `.local/verify-round3-20261021/restore-library`（3533 个文件，23.6 s）后比较：
  全部表计数与正式库**完全一致**（assets 1177、refs 937、preflights 1153、aliases 1103、
  discoveries 1147、jobs 70、projects 25、study_candidates 238，`user_version=4`）；
  1177 张原件逐一 SHA 与 asset id 相符，0 失败。
- `doctor` 返回 `ok:false`：原因是正式库本身已有 **72 条外键孤行**（`preflights/aliases/discoveries`
  指向不存在的 refs）。只读比较确认正式库与恢复副本的 `PRAGMA foreign_key_check` **完全相同**，
  因此这是既有数据状况，不是备份/恢复缺陷；未擅自清理正式库。

### 集成工作树与合并

- 工作树 `.local/worktrees/search-integration-20261021/integration`，分支
  `codex/search-integration-merge-20261021`，以主目录完整版本 `3284cf1` 为基础。
- 合并修复分支（`7c0773c` + 阶段 A 两个提交）出现 15 个冲突：`README.md`、`docs/WORKER_PROTOCOL.md`、
  两个任务文档、`ref_lab/{agent_collection,automatic_references,collection_history,verified_collection}.py`、
  4 个测试、`tools/{collect_verified,exact_recall}.py`、`web/app.js`。
- 冲突判定依据：修复分支的文件是同一产品线的**更新版本**——逐文件比较函数/类集合，对方版本没有任何
  我们缺失的符号（`agent_collection.timeout_seconds(target_count)` 自适应超时与
  `LAB_COLLECTION_HISTORY_DIR` 等对方小改动已在我们的版本中）。因此冲突按修复分支解决，
  学习线独有的文件、内容与文档全部保留。
- 合并结果相对主目录：**新增 49、修改 35、删除 0**；相对修复分支：删除 0。
  `python -m compileall` 与 `node --check web/app.js` 通过。
- 合并提交：`8046964`（第一版），`a2c7fdb`（加入 fixtures 隔离）。随后未在集成树上重跑全量（见下）。
- **全量回归**（集成树，1080 项）：**1082 passed、1 failed、6 skipped、1264 s**。唯一失败
  `test_runtime_convergence.py::test_windows_launcher_checks_actual_runtime_and_stops_its_instance`：
  PowerShell 执行策略拒绝运行测试自己生成的 `terminate.ps1`；在 **未改动的 `3284cf1`** 上同样失败
  （pwsh 与 powershell 两项都失败），属环境限制，不是合并回归。

### main 与日用切换

- `main` 快进到 `a2c7fdb`（后又到 `2c85c07`）；日用分支 `codex/learning-loop-v1-20261018` 同样快进，
  两者树完全一致（`git diff HEAD main` 为空）。
- 切换前停止旧服务（PID 10140/48188），切换到集成提交后使用**正式入口**启动：
  `scripts/launch.ps1 -NoOpen -NoWait -SkipExternalServices`，环境
  `LAB_AUTO_CLASSIFY=0`、`LAB_SEARCH_TIMEOUT_SECONDS=900`、
  `LAB_COLLECTION_HISTORY_ROOTS` 指向 4 个历史工作树。`.local/runtime/server.json` 记录
  `code_revision=a2c7fdb`、`adapter=tools/collect_verified.py`（同一 checkout）、data_dir 不变。
  启动脚本副本在 `.local/start-daily-18765.ps1`（未纳入 Git）。
- 回退入口：旧提交 `3284cf1`、备份 ZIP 与恢复验证记录；回退方式为 `stop.bat` →
  `git checkout 3284cf1`（或 `git switch` 回旧提交）→ 重新 `start.bat`。**不得**用旧数据库覆盖运行中
  新产生的数据；新结果在 `.local/collection-runs/<job>/` 与 `data/`，先另存再回退。

## 最终验收：主项目真实搜图（未通过）

- 冻结输入：`.local/verify-round3-20261021/acceptance-frozen-inputs.json`；代码 `a2c7fdb`，
  服务 PID 50180，数据目录正式库，目标 15 张名称命中可用独立照片，预算 900 秒，快速搜图，
  小红书＋Pinterest，历史范围 1544 条（含 `4a81ff48` 的 19 张与前轮诊断 8 张，合成 fixtures 已排除）。
- 发起方式：主项目网页（Edge + Playwright）在“采集任务 → 建立搜图任务”表单填写目标 15、快速搜图、
  服装不限与 3 个别名后点击“开始搜图”；观察器在点击**之前**启动。项目
  `cde6b9b863c34e7e8f9834527b102031`（渡辺曜／Love Live! Sunshine!!），Job
  `927b54a75d784349aeb5149dd2ee5e3d`。
- 实测（`.local/verify-round3-20261021/acceptance-observation.json`）：
  - 点击 → 首张原件服务端保存 **150.94 s**，首张图片在浏览器实际解码可见 **154.49 s**；
  - 运行 **422.28 s** 后结束，**未达到目标**：5 张原件、7 条排重、**2 张名称命中可用独立照片**；
  - 停止原因 `target_partial`（8 条查询、19 个可见窗口、两个来源均可用，计划耗尽），
    不是预算耗尽，也不是登录/验证受阻；
  - 5 张中 3 张为“角色相关性未确认”，因此 `usable_independent=5`、`usable_named=2`。
- 期间发现并修复一个真实产品缺陷：适配器在未达目标时写 `status=partial` 的完整回执，但
  `run_search_stage` 只接受 completed/blocked/failed/cancelled，于是把真实回执替换成
  `stop_reason=summary_missing`（“搜索进程没有留下阶段回执”）。修复提交 `2c85c07`（两处状态集合）
  并新增回归 `test_partial_search_summary_is_accepted_as_the_stage_receipt`；该缺陷先用回归在旧代码上
  复现（state=blocked），修复后 13 项阶段测试、72 项相关测试通过。
- 缺陷修复后按正式入口重启（`server.json` 记录 `code_revision=2c85c07`），本轮成果仍在：
  5 张候选、5 条项目引用（pending）、计数 5/2/5/3，5 张图片 API 200 且 SHA 与文件名一致、
  Edge 中全部解码可见；项目页与候选图库刷新后保持。截图
  `acceptance-01-form.png` … `acceptance-05-project-view.png`。
- **本轮 Job 的已存回执仍是旧缺陷写下的 `blocked/summary_missing`**（不篡改历史）；真实数字保存在
  `collector-state.json`（`search_summary`：found 5 / duplicates 7 / usable_named 2 / stop_reason
  target_partial，`history_known=1332`）与本记录中。
- **判定：主项目完整结果验收 未通过（FAILED）**：目标 15 张，实际新增名称命中可用独立照片 2 张；
  未达目标的原因是搜索计划耗尽、平台可见文本以简体“渡边曜”为主而冻结别名只有日文“渡辺曜/
  渡辺 曜/You Watanabe”，名称命中偏少。保留全部成果，不换 Job、不改口径、不重置预算。

## 发布、最终状态与保护核对

- 远端（`origin` = github.com/laohan1126-lang/photography-reference-lab）核对：
  `main = faf6696c98ac1e31f8832a0275c62bfe50e0bb60`；
  `codex/learning-loop-v1-20261018 = faf6696…`；
  `codex/search-integration-merge-20261021 = faf6696…`；
  `codex/search-integration-20261021 = 0c87a68788f7d9b1f7ff425a6f5d47c4dc2fab83`
  （修复分支内容：`7c0773c` + 阶段 A 两个提交 + fixtures 隔离）。
- 运行中的服务由 `scripts/launch.ps1` 记录 `code_revision = 2c85c07…`（partial 回执修复），
  与 `main` HEAD 的差异**只有** `docs/tasks/` 两个文件；`git diff --quiet <running> main -- ref_lab tools web`
  为 0，服务端与采集适配器均来自主目录同一 checkout（`tools/collect_verified.py`）。
- 本轮未使用 Publisher：这是 DSH 的 manual host 会话，没有“编辑前”的宿主生命周期基线；在实现完成后
  补建基线正是上一轮审计判定不合规的做法，因此按用户“不补建晚基线”的要求改为经复核的 Git 提交，
  并核对远端 SHA。旧失败事务回执与归档原样保留，未改写成成功历史；Notion 未写入。
  `delivery: {git: true, notion: false}`。
- 资料库保护（相对切换前备份快照的表计数）：只增不删——assets 1177→1182、refs 937→942、
  preflights 1153→1158、discoveries 1147→1152、projects 25→26、jobs 70→71、events 3257→3273；
  其余 12 张表完全不变（含 aliases 1103、inspirations 23、study_candidates 238、
  library_annotations 57、screening_sessions 8）。`/learning` 入口 200。
- 回退：见上节（旧提交 `3284cf1` + 备份 ZIP + `stop.bat`/`start.bat`）。运行中新产生的 5 张结果
  在 `.local/collection-runs/927b54a7…/` 与 `data/`，回退前先另存。



