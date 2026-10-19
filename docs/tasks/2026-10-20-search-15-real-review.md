# 真姬15张真实搜图、人工同步修复与独立AI审核闭环

## 原始目标（本轮用户原文要点，编辑前记录）

仓库 `D:\AI PROJECTS\photography-reference-lab`；起始分支
`codex/search-relevance-fix-20261020`，起始提交
`0731cf5c1554cb73d7b3d0b24b4109b56a51cfe7`。先读 AGENTS、架构文档及最近两轮
search-review-decouple / search-relevance-fix 记录。创建新的隔离工作树和任务分支，不修改日用
main、正式数据库、私人原图或人工判断，不写 Notion，不擅自切换日用服务。

### A. 一次15张真实快速搜图

项目：西木野真姬 / Love Live! / 不限服装。从正常 Windows 网页入口运行，目标为 15 张具有
可信角色名称文本线索的候选原图。Search 阶段保持 0 视觉模型调用。未确认相关性的探索图可以
显示，但不计入 15 张目标。必须记录：首张/第5/第10/第15张名称命中候选的网页可见时间；名称
命中/探索/重复/跳过数；小红书与 Pinterest 各自查询、可见卡片、详情尝试、成功下载；完整中英
日查询词与实际排序模式；原帖 URL、SHA、尺寸、名称依据；各阶段耗时；模型调用与 Token；
停止原因与完整 wall time；停止后重开页面原图仍可查看。目标数只统计名称命中候选；名称命中
不等于视觉身份确认。若整轮 0 张或某来源 0 张，必须逐环节追查（搜索词→真实搜索结果→可见
卡片→详情→DOM→原图URL→下载→格式→排重→持久化），不得只报 `search_plan_exhausted` /
`source_blocked`；对失败的详情页保存可复查原因、导航状态、可见图片数和提取结果。不绕过
登录/验证码、不猜 CDN、不用隐藏 API。不得为凑数使用无关图、旧图或无限加预算。

### B. 人工审核和继续加搜可靠性（先做，不做完不启动 A）

修复两个已审查问题：

1. 继续加搜可能被旧的查询进度状态阻断。
2. 边搜索边人工保留/淘汰时，候选队列与项目图库可能不同步。

要求：用户点击人工保留/淘汰即持久记录；项目引用尚不存在时安全创建或后续可靠同步；搜索与
人工并发不覆盖；已有正式 K/I/M/X 决定不被静默覆盖；人工保留不等于 AI 通过；撤销人工决定
后项目与候选视图一致；重启和重复导入仍一致。回归必须覆盖：原任务全部查询完成、目标达到后再
加 10 张；重启后继续同一 Job；原候选 SHA/字节/人工决定保留；新查询实际执行，不被旧
`done=True` 跳过；不重复计数旧图；累计时间、查询、详情预算不得无理由清零；预算已用尽必须
明确报告，不得假装加搜成功。测试至少覆盖：搜索运行中选择、导入前选择、导入后选择、并发导入、
撤销、重启、已有人工决定冲突。缺陷复现测试先失败，再修复通过；不得删检查、放宽人工权限或
清空旧状态。

### C. 后台AI审核真实闭环

复用本轮已保存候选，不重新搜索。先确认已有本地 Review 执行器、当前模型、模型调用命令及额度
可用性；不擅自更换付费服务、模型或安装组件。默认复用正式审核契约：可信参照调查、
SourceAssessment、CollectionVision、完整 needs_supplement、严格 accepted、schema3。本轮以
3–5 张真实候选为有界样本；如现有审核器只支持整批，可做最小有界批次控制，已完成保留、其余
保持待审，不得把未审图自动判拒绝，不得新建审核架构。从网页操作“启动 AI 审核”，验证：
Search 完成后可独立启动；处理真实原图；参照可获取解码；至少一条真实视觉判断回执含原图
SHA 绑定与完成状态；通过/拒绝/不确定/受阻状态区分；逐图落盘且重启保持；已审图重试不重复
调用；人工选择不被 AI 覆盖；合格图按 schema3 导入、不合格/受阻保留候选；审核失败不影响
Search 候选。另验证 `search_review` 由两个独立阶段组成，Review 准备参照不阻塞 Search 下载
及展示。报告审核调用次数、总 Token、实际耗时；事先固定有界模型调用与运行预算。参照编码/
读取/可信度问题先定位根因再最小修复；不得取消角色验证或降低 accepted 制造成功。

### 验收与纪律

分别给出 A：SEARCH_15、B：HUMAN_AND_CONTINUE、C：REAL_REVIEW 三个 PASS/PARTIAL/BLOCKED
结论，附实际证据；合成测试 PASS 不能替代真实领域验收。只围绕 A/B/C 修复真实缺陷；禁止扩展
采集平台、重设计视觉审美、弱化身份核验、增加多 Agent 框架、因结果不好无限重跑、未授权修改
正式图库/main/Notion、伪造或缓存旧图凑数、合并 main 或切换日用环境。完整保留真实失败、模型
原始回执、候选图片与 SHA；提交测试与任务文档到独立分支并推送，核对远端 SHA。最后停止执行，
把三项实测结果和剩余缺陷交给用户决定下一步，不自动再开新开发 Loop。

## 基线

- 起始提交：`0731cf5c1554cb73d7b3d0b24b4109b56a51cfe7`（`codex/search-relevance-fix-20261020`）。
- 本轮独立工作树：`.local/worktrees/search-15-review-20261020/root`；分支
  `codex/search-15-review-20261020`。
- 只读历史证据：`.local/worktrees/search-review-decouple-20261020/root/.local/collection-runs/549b320f.../current/`
  与 `.local/acceptance-20261020/`；`.local/worktrees/search-relevance-fix-20261020/root` 的任务记录。
- 运行环境：Windows Python 3.12 + 本仓库依赖；隔离数据目录；正常 `scripts/launch.ps1` 启动；
  Windows Edge/BrowserSkill（需实测连接，不以可执行文件存在代替）。

## 可观察验收标准

| ID | 通过条件 |
|---|---|
| B1-R1 | 原任务所有查询已完成、目标已达后再加目标并重启，新查询实际执行（浏览器真实搜索次数 > 0），不是被旧 `done=True` 全部跳过。 |
| B1-R2 | 继续加搜保留原候选 SHA、原图字节与人工决定；旧图不重复计数；`received` 按 SHA 唯一。 |
| B1-R3 | 继续加搜不清零累计 `details`、`windows`、`elapsed`；预算已用尽时明确返回 `*_budget_exhausted` 且不宣称成功。 |
| B1-R4 | `--search-only` CLI 不会因旧 terminal `search-summary.json` 直接退出而漏掉继续加搜；同一 Job 的任务包拿到当前 `search_extra_target`。 |
| B2-R1 | 搜索运行中/导入前点击人工保留或淘汰，导入后项目 ref 与候选视图一致，且 `decision_origin=human_candidate_queue`。 |
| B2-R2 | 导入后点击、撤销、重启后重复导入仍一致；人工保留不产生 `accepted`/AI 通过。 |
| B2-R3 | 已有正式 `human_curation`/`human` K/I/M/X 决定冲突时返回 409，不静默覆盖。 |
| B2-R4 | 并发导入与人工决定不丢失：最终要么 ref 带该决定，要么队列可重放，不能存在“队列有决定、项目 pending”的永久分叉。 |
| A-R1 | 仅建立一次新的 15 张真实搜索 Job（西木野真姬/Love Live!/不限服装/快速搜图+人工审核/小红书+Pinterest），Search 视觉模型调用 0。 |
| A-R2 | 交付 15 张名称命中候选并保留原帖 URL、SHA、尺寸、名称依据；网页可重开查看原图；记录首张与第 5/10/15 张耗时、来源分布、停止原因与 wall time。 |
| A-R3 | 若任一来源 0 张，给出逐环节数量与原始错误；不得以无关图补数。 |
| C-R1 | Search 完成后可独立启动 Review；处理真实已下载原图与真实参照。 |
| C-R2 | 至少一条真实模型视觉回执，含原图 SHA 绑定、完成状态、通过/拒绝/不确定/受阻区分；逐图落盘、重启保持、已审不重复。 |
| C-R3 | 人工决定不被 AI 覆盖；accepted 按 schema3 导入，拒绝/受阻保留候选；审核失败不回滚 Search 候选。 |
| C-R4 | 报告实际调用次数、Token、耗时；预算固定且有限。 |

## 进展

- 2026-10-20：已读取 AGENTS、两份任务记录、collector/stage/service/queue/API 代码与保存的 549b
  证据；创建独立工作树和任务分支。开始 B 阶段失败回归。

## B 阶段：根因、修复与验证

### B1 继续加搜被旧状态阻断（共同根因共三处）

1. `tools/collect_verified.py`：`collect()` 在继续加搜时把 `state['searches']`/`state['pages']`
   重绑为新对象，但主循环继续使用 `searches=state['searches']` 的旧局部对象；下一次
   `checkpoint()` 又把旧对象写回 `collector-state.json`，旧 `done=True` 与旧页面立即复活。
   同时旧代码清空 `state['queries']`，丢失累计查询记录。
2. `tools/collect_verified.py` 的 `--search-only` CLI：只要 `search-summary.json` 是 terminal
   状态就直接退出（`Search already finished; no new acquisition`），继续加搜的进程根本不会
   进入采集器；被杀死的继续轮次还会被旧 summary 误判为已完成。
3. `ref_lab/agent_collection.py` 的 `_prepare_task()`：任务包首次生成后不再更新，`job.json`
   冻结了旧的 `target_count`/缺失的 `search_extra_target`，采集器读不到新的累计目标。

修复（最小、不重置真实预算）：

- 继续加搜时原地 `clear()` 局部 `searches`/`pages`（不再重绑），保留 `page_attempts` 以便详情
  预算不重复计数；`received`/`audit`/`duplicates`/`collisions`/`search_errors`/人工决定文件
  原样保留，按 SHA 去重旧图。
- 新增 `continue` 元数据与 `elapsed_seconds_total`：累计 wall time 跨轮次保存；summary 写
  `cumulative_elapsed_seconds` 与 `continue{attempt_index,extra_target,previous_target,target,
  confirmed_at_start,blocked_by}`；预算已在开始时耗尽则 `blocked_by` 明确记录，不伪装加搜。
- 每轮完成查询追加 `query_history`（上限 120），`queries` 不再被清空。
- CLI：terminal summary 只有在没有新增目标（或新目标 ≤ 上轮 effective target）时才退出；
  继续加搜时把旧 summary 归档为 `search-summary-previous-<ts>.json` 再运行新轮次，进程被
  杀时不会把旧成功当成新成功。
- `_prepare_task()` 在任务包已存在时仅原子刷新 `job.json`（项目快照、规则、图片不变），
  使采集器拿到当前 `search_extra_target`。
- `Library.update_search_stage()` 使用 `cumulative_elapsed_seconds`，且累计时间只增不减。

回归：`tests/test_search_continue_recovery.py`（4 项）。真实失败形状为“原任务全部计划查询已
完成、`search_complete=true`、目标已达到，同 Job 再加 4 张并重启”：

- `test_continue_after_every_query_finished_executes_new_queries_and_keeps_old_originals`：
  继续轮必须重新执行全部计划查询、新增 4 张、旧 4 张 SHA/字节与 `human-decisions.json` 不变、
  `details` 累计递增、`continue.confirmed_at_start=4`。
- `test_continue_reports_exhausted_detail_budget_instead_of_claiming_success`：
  `details=MAX_DETAIL_PAGES` 时 0 次浏览器查询、`status=partial`、
  `stop_reason=detail_budget_exhausted`、`continue.blocked_by=detail_budget_exhausted`。
- `test_search_only_cli_continues_instead_of_exiting_on_the_old_summary`：CLI 不再打印
  `Search already finished` 直接退出，执行新查询、found 1→2、旧 summary 归档。
- `test_task_package_is_refreshed_with_the_pending_extra_target`：任务包 `job.json` 刷新到
  `search_extra_target=6` 且 `target_count`/项目快照不变。

### B2 边搜边人工保留/淘汰与项目图库不同步

根因：`Library.decide_candidate_human()` 在项目 ref 尚不存在时只写
`human-decisions.json`；Search 结束后的 `_import_search()` 用
`add_candidate(decision="pending")` 创建 ref，从不回放已保存的人工决定。搜索运行中点击保留，
项目仍是“未选择”，且后续重复导入无法修复。

修复：

- 新增 `Library.import_search_candidates()` 作为 Search/Review/候选决定的唯一导入路径；创建或
  复用 ref 时读取 `human-decisions.json`，把 `keep`/`reject` 直接作为初始决定并写入
  `decision_origin=human_candidate_queue`；重复导入幂等，不覆盖正式 `human_curation/human`
  决定（记录 `conflicts`，项目保持权威）。
- `decide_candidate_human()` 先做正式决定冲突检查，写 durable JSON 后立即 `import` 该 SHA：
  Search 运行中（带当前 `attempt_id`）或导入前点击都会立即创建项目 ref；撤销 `clear` 把项目
  ref 恢复 `pending`。并发创建同 `(project, asset)` 时捕获 SQLite 唯一键冲突并复用已存在 ref。
- `_import_search()` 改为委托该服务方法。人工保留仍只是 `human_keep`，`review` 保持空，不会
  变成 AI `accepted`。
- 搜索运行中的创建仍经过原 `add_candidate` 的 attempt 归属校验，不绕过轮次边界。

回归：`tests/test_candidate_decision_sync.py`（7 项）：运行中保留立即建 ref；导入前淘汰；
导入后保留→撤销→再导入仍 pending；重复导入不回退决定；已有正式项目决定冲突时导入不覆盖；
并发（导入线程在 `add_candidate` 前暂停、主线程同时点保留）最终一致；新 Library 进程重启后
候选视图与项目 ref 都保持。1 项（导入后撤销）在修复前已通过，其余 6 项修复前失败。

### B 阶段验证

- 修复前证据：同一组新回归在 stash 掉源码修改后 **10 failed / 1 passed**；修复后
  **11 passed**。
- 相关既有回归（主仓库依赖环境）：`tests/test_search_relevance_regression.py
  tests/test_search_relevance_interaction.py tests/test_collection_stages.py
  tests/test_collection_ui.py tests/test_collection_job_recovery.py
  tests/test_collection_runner.py tests/test_collection_contract.py
  tests/test_collection_resume.py tests/test_collection_history_cache.py
  tests/test_verified_collection.py tests/test_review_baseline_consistency.py
  tests/test_imports_jobs.py tests/test_personal_library.py`
  → **189 passed, 1 warning**（146.85 秒）。
- 隔离 venv（`install.ps1` 同流程 `pip install -e ".[test]"`）中：
  `test_search_continue_recovery.py test_candidate_decision_sync.py
  test_search_relevance_regression.py test_search_relevance_interaction.py`
  → **23 passed**。
- `python -m compileall -q ref_lab tools tests` 通过；`node --check web/app.js` 通过。
- 未验证：真实外网继续加搜、真实网页“综合/最新”翻页和搜索结果轮换；本轮继续加搜回归只用
  确定性浏览器替身，不代表平台召回率。B 阶段未启动真实 15 张任务（符合退出条件）。

## A 阶段：唯一一次真实 15 张搜索

### 冻结输入（运行前）

- 代码 SHA：`0e0fd33e837510654481e441cc8db083ff4f7609`（B 修复提交；运行期间未改源码）。
- 工作树：`.local/worktrees/search-15-review-20261020/root`；正常启动器
  `scripts/launch.ps1`（`-SkipExternalServices`，未接触 Cloudflare 隧道）；隔离数据目录
  `.local/ui-data-15-20261020`；端口 18789；BrowserSkill daemon 已连接 Windows Edge
  （`bsk status`：edge 155.0.0.0 / extension 0.3.3 / 无 skew）。
- 项目 `a3ba6fc091d5402285618dbea4891688`：西木野真姬 / Love Live! / 服装空 / 要求
  “真人 cosplay 摄影参考；快速搜图 15 张，人工审核”。
- Job `bedd28c47ee5483caba160057673fbd8`：`collection_mode=search`，`target_count=15`，
  来源 `[xiaohongshu, pinterest]`，无额外别名（使用本轮可信 preset + 项目名）。
- 计划查询 8 条（`queries`）：`西木野真姬 Love Live! cos 摄影`、
  `Maki Nishikino Love Live! cosplay photography`、`西木野真姫 cos 场照`、
  `西木野真姫 cosplay photoshoot`、`Maki Nishikino cos 棚拍`、
  `西木野真姬 cosplay convention`、`西野木真姫 cos 正片`、
  `Nishikino Maki cosplay portrait`。
- 实际预算：Search 阶段默认 1530 秒；detail 96 页；每查询最多 3 窗口；每查询最多 8 张卡；
  vision 预算 30（Search 不使用）；Search 视觉模型调用预期 0。
- 冻结文件：`.local/run-15-20261020/frozen-inputs.json`。

### 实际结果

正常网页入口：点击“开始搜图”→ `/start` → 独立 Search 子进程。`t0` 由页面点击监听记录
（2026-10-20 04:09:34.493 +09）；网页候选图库每秒轮询。**只建立这一次 15 张 Job，没有第二次。**

| 指标 | 实测 |
|---|---|
| 停止状态 / 原因 | `completed` / `target_reached` |
| 点击→首张候选原图落盘 | **101.145 秒**；网页轮询最多 +1 秒（服务端 page→queue） |
| 点击→第 1 张**名称命中**在网页可见 | **151.469 秒** |
| 点击→第 5 张名称命中 | **257.479 秒** |
| 点击→第 10 张名称命中 | **383.487 秒** |
| 点击→第 15 张名称命中 | **431.511 秒** |
| 点击→Search 完成（服务端 `search_finished_at`） | **432.36 秒** |
| Collector `elapsed_seconds` | 414.922 秒 |
| 找到候选 / 名称命中 / 探索未确认 | **18 / 15 / 3** |
| 重复 / 下载错误 | 9 / 0 |
| 模型调用 / Token | **0 / 0** |
| 历史排重已知 SHA | 1255；0 errors |
| 实际执行查询数 | 3 / 8（达到目标即停止） |

来源分布：

| 来源 | 执行查询 | 可见卡片（窗口合计） | 详情尝试 | 成功下载 | 名称命中 | 探索 | 重复 |
|---|---|---|---|---|---|---|---|
| 小红书 | 2 条（中文 1、日文 1），5 个窗口 | 84 张（20+20+18+26） | 19 | 15 | 12 | 3 | 7（same_bytes） |
| Pinterest | 1 条（英文），1 个窗口 | 16 张 | 3 | 3 | 3 | 0 | 2（可见封面命中历史） |

- 排序：5 个窗口全部 `sort_latest=false`、`sort_mode=relevance`；小红书没有触发“最新”回退。
- 跳过：`skipped_exploration_budget=54`、`skipped_other_character=0`、`skipped_non_photo=0`
  （探索预算 `max(1,min(8,target//4))`；名称命中未用完前不会把探索图算作目标）。
- 阶段耗时（`timings.jsonl` 的 wall_seconds 汇总）：`browser_receive` 319.53 秒（22 次，含详情
  导航/原图下载）、`browser_search` 43.56 秒（3 次）、`discovery_preview` 24.94 秒（24 次）、
  `browser_more` 14.53 秒（2 次）、`history_consider` 2.89 秒（25 次）、`browser_start` 2.20 秒；
  其余约 21 秒为规划/检查点开销。
- 停止后重开：服务重启一次后 `http://127.0.0.1:18789/#view=jobs` 的候选图库仍显示 18 张原图、
  15 名称命中、3 未确认、18 待审；原图 URL 返回原字节。

### 15 张名称命中候选（全部已逐张打开原图检查）

| # | 来源 | SHA-256（前 16） | 尺寸 | 备注 |
|---|---|---|---|---|
| 4 | Pinterest | `b44d25cf55499eef` | 1200×1800 | 单张，真人 Maki 偶像服，Luu Danh Photography |
| 5 | Pinterest | `d055f1b5ecebf0aa` | 641×960 | 单张，真人 Maki 旗袍造型 |
| 6 | Pinterest | `dfa6b0b95554730d` | 560×840 | 单张，真人 Maki 女仆造型 |
| 7 | 小红书 | `a92e28b53d647ca2` | 1080×1620 | 单张，上海夜景 Maki |
| 8 | 小红书 | `93c88b356e49ff23` | 1080×1440 | **上下 2 格拼图**（同一帖） |
| 9 | 小红书 | `b8e9ff2ef1b5167b` | 1080×1620 | 单张（同一帖） |
| 10 | 小红书 | `2d5493b3461ca5ad` | 1080×1440 | **3×3 九宫格拼图**；帖子带“可能含AI生成内容”平台标签 |
| 11 | 小红书 | `01e8e7673bf099eb` | 1080×1440 | 单张，真人 Maki 花丛肖像 |
| 12 | 小红书 | `47f02060f97f667c` | 1080×1440 | **2×2 四格拼图**（校服） |
| 13 | 小红书 | `28de0b2933b9840e` | 1080×1920 | **上下 3 格拼图**（校服） |
| 14 | 小红书 | `4a1670a075e1af0f` | 1620×1080 | 单张（同帖） |
| 15 | 小红书 | `52e75a5e39310aa2` | 1620×1080 | 单张（同帖） |
| 16 | 小红书 | `a54bf56edd5ea898` | 1439×1080 | 单张，真人 Maki 粉色肖像 |
| 17 | 小红书 | `5c3e360680e617d7` | 1080×1439 | 单张，舞台造型 |
| 18 | 小红书 | `45fed820710a2f1f` | 1080×1439 | 单张（同帖） |

探索候选（不计入 15）：#1 `1d09123a…`、#2 `e41a99b2…`、#3 `aedefc60…`，同一小红书帖
`6ad5a11a…`（“在看哪里？在flo外场快速的出了一套图”）；#2 是 2 格拼图。完整来源、图片 URL、
查询词、尺寸、名称依据见 `.local/run-15-20261020/candidates.json` 与
`candidates-contact-sheet.jpg`（18 张缩略图与序号/SHA/耗时，私有文件）。

### A 的质量结论（不能只看数量）

- 15 张名称命中均能在原帖标题/描述找到“西木野真姬 / 真姫 / Maki”之一；都是真人 cosplay
  原图，没有插画、游戏截图或无关图。
- **但 15 张里有 4 张是拼图**（#8 2 格、#10 9 格、#12 4 格、#13 3 格），不是单张摄影参考；
  #10 的帖子另带“可能含AI生成内容”平台标签。可用的单张名称命中候选为 **11 张**。
- 独立视觉抽查（同一批真实图）进一步证明：探索帖 #1 被判为《我推的孩子》有马加奈
  B 小町造型（红贝雷帽、B 字盾徽），**不是**西木野真姬；#2 拼图；#3 与 #1 同帖同服装但
  无盾徽视角，AI 判为真姬并 `CONFIRMED`——这是本轮最明显的疑似误收风险，不能把 #3 当成
  已确认的角色真值。
- 因此 A 的数量目标达到，但“15 张都适合作为角色摄影参考”**不成立**；名称命中≠视觉确认。

## C 阶段：真实后台 AI 审核闭环

### 执行器、模型与可用性（运行前检查）

- 执行器：`tools/collect_verified.py --review-only` + `ref_lab.verified_collection.AntigravityCollectionAgent`；
  完整契约：NamePlan → 可信参照调查（ReferenceDiscovery / SourceAssessment / 参照图解码）→
  逐图 `CollectionVision` → `needs_supplement` → 严格 `accepted` → schema3。
- 模型：`LAB_CLASSIFICATION_MODEL` 默认 `gemini-3.8-flash-medium`；CLI
  `C:\Users\Dell\AppData\Local\agy\bin\agy.exe`，命令
  `agy -p <prompt> --model ... --mode plan --sandbox --output-format stream-json --json-schema ...`。
- 普通 shell 直接探测 agy 会报“未登录/日志目录拒绝访问”（token 缓存 expiry 2026-10-20 02:14、
  shell 无法写 `~/.gemini`）；但**正常启动器启动的服务进程内真实调用成功**，回执
  `status=SUCCESS`、含 usage/structured_output（见下）。本轮没有更换模型、没有安装新组件、
  没有调用付费 API。
- 固定预算：Review 阶段 2400 秒；`LAB_REVIEW_MAX_IMAGES=5`（本轮新增的最小有界批次控制）；
  原 vision 调用上限 30。

### 三次真实 Review 尝试（保留失败）

1. **04:28 第一次**：从网页启动 Review；NamePlan 成功（35,816 tokens，50.2s）；参照调查
   取得 1 个可信页面/2 张图；为执行 3–5 张有界样本，在参照准备阶段主动取消（保存
   `review-state`；未产生视觉判断）。
2. **04:39 第二次**：NamePlan/参照成功（最终 4 张可信参照，2 个官方/授权页面）；逐图阶段
   **18/18 全被标为 duplicate（same_bytes），0 次视觉调用**。根因：Search 已把候选原图导入
   项目 asset store，Review 的历史排重从 `LAB_COLLECTION_HISTORY_DIR` 看到同字节文件，把
   “本 Job 自己的候选”当成历史重复；这是真实执行缺陷，不是用户数据。
   失败证据保留：`review-audit-selfduplicate-20261020-044928.json`、
   `review-summary-selfduplicate-20261020-044928.json`。
3. **04:51 第三次**：修复后重启隔离服务并重新从网页启动；参照缓存命中（0 次新参照查询），
   5 张视觉判断后按 `review_sample_limit` 正常收尾。

### 第二次失败的修复（最小）

- `ref_lab/collection_history.py` 新增 `ImageHistory.exclude(shas)`，从本轮历史比较中移除
  “本 Job 已取得”的 SHA/记录。
- `tools/collect_verified.py` 的 `review_candidates()` 在开始及每轮刷新后对本 Job
  `received` 的 SHA 调用 `exclude()`；不会隐藏真正的历史重复（对照 SHA 不同仍会命中）。
- 回归：`tests/test_review_self_duplicate.py`。该测试在修复前 `review_calls=0`（两图全
  duplicate），修复后 2 次真实视觉调用、2 张 accepted；同时保留“未修复前 self match”断言。

### 有界批次控制

- `LAB_REVIEW_MAX_IMAGES=N`（0=不限，默认 0）：只限制“本轮新发起的逐图判断数”；达到上限后
  `stop_reason=review_sample_limit`，已完成判断逐图保留，其余保持 **pending**，不自动判拒绝，
  仍会生成包含已通过项的 schema3 ZIP 并导入。
- 回归：`tests/test_review_sample_limit.py`（2 项）：4 张、上限 2 → 2 次调用、2 accepted、
  2 pending、`partial`；随后无上限续审只消费剩余 2 张，不重复已完成项；上限 0 表示不限。

### 第三次（成功）真实审核结果

- 点击“启动 AI 审核”到 Review 收尾：**约 361 秒 wall**；`review_elapsed_seconds=354.282`。
- 有界样本 5 张（13 张保持 pending）；**5 次真实 CollectionVision 调用**，
  140,748 tokens，模型 wall 353.4 秒。参照：**4 张可信参照图**（2 页：
  Good Smile figma 官方分销页 2 张；Good Smile Nendoroid 制造商页 2 张；
  Hobby Wave 页被 SourceAssessment 判 untrusted，未使用）。每次视觉调用的
  `binding.inputs` 都包含 4 个参照文件 SHA + 当前原图 SHA。
- 三次尝试合计（含被取消/失败轮）：**13 次模型调用 / 383,837 tokens / 894.7 秒模型 wall**。
  当前 `review-summary.model_calls=5` 只统计 CollectionVision；`tokens` 是该 Job 目录全部
  attempt 的累计值，不是单轮值；单轮真实审核成本以上面的 5 次/140,748 tokens 为准。

| 候选 | 结果 | 模型判断 |
|---|---|---|
| `1d09123a…`（探索） | rejected / NEEDS_EVIDENCE | `cosplay_photo`，identity **mismatch**；红贝雷帽+B 字盾徽 → 有马加奈 B 小町，非真姬 |
| `e41a99b2…`（探索） | rejected / MISMATCH | `collage`（上下拼图）；身份特征像真姬，但拼图不能作为单张摄影参考 |
| `aedefc60…`（探索） | **accepted / CONFIRMED** | `cosplay_photo`，identity match，high；红发紫眸+捻发动作；**与 #1 同帖同服装，疑似同角色误收，需人工看** |
| `b44d25cf…`（Pinterest 名称命中） | **accepted / CONFIRMED** | `cosplay_photo`，identity match，high；单人全身、花束、背身回眸，摄影参考价值明确 |
| `d055f1b5…`（Pinterest 名称命中） | blocked / REVIEW_BLOCKED | “Agent输出未通过结构校验，未交付未核验图片。”——执行受阻，不是拒绝 |

- 通过/拒绝/不确定/受阻区分：`accepted=2`、`rejected=2`（含 `NEEDS_EVIDENCE`、`MISMATCH`）、
  `blocked=1`、`pending=13`；`human_keep=0/human_reject=0`。
- 人工决定：本轮真实运行没有替用户做任何 K/I/M/X 或候选保留/淘汰；AI 结果没有修改
  `human-decisions.json`。人工保留仍只是 `human_keep`，不会变成 `accepted`。
- 逐图落盘：`review-audit.json` 逐项含 `asset_sha`、`status`、`decision`、完整
  `CollectionVision`（asset_sha/context_sha 绑定）、参照 SHA、耗时；重启服务后 5 条判断、
  2 条导入 ID 和 18 张候选全部保持。
- 已审核重试：离线回归证明 `accepted/rejected/duplicate` 会被跳过；本轮真实运行未再启动
  第二轮审核以免重复模型调用。受阻的 `d055f1b5` 属于“未完成项”，按设计可在后续轮次重试。
- schema3 导入：`review-result.zip` 通过校验，包含 2 张 accepted，`job.review_imported_ids`
  记录 2 个 ref；`review-result.zip` SHA-256 = `47501c07cd60d03fa69cbd42614b146239edbfc54b5c82f3cb4e00d96399b27b`。
- 导入后发现并修复第二个真实缺陷：Search 先创建的 pending ref 已有“uncertain”本地 preflight，
  旧 `import_candidates()` 只在新 ref 上应用 schema3 preflight，导致真实审核的
  `preflight=match/passed` 没有落到项目 ref。修复为“unreviewed/uncertain 且无人工 override 时
  允许 schema3 preflight 升级”；回归
  `test_schema3_review_preflight_reaches_a_preexisting_search_candidate`。随后用**同一真实 ZIP**
  重走导入函数（0 次模型调用，未改决定）：2 个 ref 现为 `preflight_status=passed`、
  `identity_prediction=match`、`decision=pending`。这是导入修复验证，不是重新审核。
- 审核失败/受阻不回滚 Search：18 张候选、15 名称命中、全部原图 SHA 与字节不变；审核只把
  5 张置为 accepted/rejected/blocked，其余 13 pending。
- `search_review` 两阶段独立：沿用并重跑
  `tests/test_collection_stages.py::test_stage_endpoints_keep_search_complete_while_review_is_blocked`
  （Review 停在 reference_prepare 时 Search 已完成、18 张候选可见；释放后才审核）；
  以及 `test_cancelling_review_does_not_stop_search_or_delete_candidates` 等 4 项，
  本轮 **4 passed**。未再启动第二轮外网 15 张。

### C 的结论与风险

- 执行器、真实模型、真实原图、真实可信参照、逐图 SHA 绑定、结果落盘、重启保持、bounded
  sample、schema3 导入和失败隔离均已实测成立。
- **但真实审核只有 5 张样本，且至少有 1 张疑似误收（#3 与已被判为有马加奈的 #1 同帖同服装）**；
  #5 是模型输出结构校验失败（受阻，不是拒绝）；13 张仍待审。不能把本轮 2 张 accepted 当成
  “2 张真姬身份已被可靠确认”。这属于模型/视觉证据限制与执行受阻，不是 Search 失败。
- 本轮没有用户人工真值，因此不计算通过率/误收率，也不以 AI 自己的标签替代人工判断。

## 最终验收（本任务结论，不是主人审美确认）

| 维度 | 结论 | 证据 / 限制 |
|---|---|---|
| A：SEARCH_15 | **PASS（数量）/ PARTIAL（可用性）** | 唯一一次真实 Job 达到 15 张名称命中、18 下载、0 模型调用；首张 101.1s、第 15 张 431.5s；小红书 12 名称命中（此前 0 的问题已消失）+3 探索，Pinterest 3；但 4/15 是拼图、1 帖带 AI 标签，可用单张为 11；探索帖 #1 被真实视觉判为其他角色。 |
| B：HUMAN_AND_CONTINUE | **PASS（工程回归）** | 修复前 10 failed/1 passed；修复后 11 passed；继续加搜会重跑全部计划查询、保留原 SHA/字节/人工决定、累计预算不清零；边搜边决定/导入前/导入后/撤销/重复导入/并发/重启/正式决定冲突均通过。真实外网 continue 未跑（遵守只建一个 15 张 Job）。 |
| C：REAL_REVIEW | **PARTIAL** | 真实模型 5 次逐图判断、4 张可信参照、SHA 绑定、逐图落盘、重启保持、schema3 导入 2 张；有界 5 张、13 待审；1 张疑似误收、1 张受阻。执行器与闭环成立，身份真值/全量审核不成立。 |

## 本轮新增/修改文件

- `tools/collect_verified.py`：继续加搜状态/预算/CLI 修复；`LAB_REVIEW_MAX_IMAGES` 有界批次；
  Review 排除本 Job 自身 SHA。
- `ref_lab/agent_collection.py`：任务包 `job.json` 原子刷新。
- `ref_lab/service.py`：继续加搜累计时间；`import_search_candidates()` 统一导入/人工决定回放；
  `decide_candidate_human()` 立即创建/同步。
- `ref_lab/collection_stages.py`：`_import_search()` 委托统一路径。
- `ref_lab/collection_history.py`：`ImageHistory.exclude()`。
- `ref_lab/imports.py`：schema3 preflight 升级已存在 pending ref。
- `tests/`：`test_search_continue_recovery.py`（4）、`test_candidate_decision_sync.py`（8）、
  `test_review_sample_limit.py`（2）、`test_review_self_duplicate.py`（1）。
- 本文档与 `docs/tasks/CURRENT.md`。

## 验证命令与结果（最终）

```powershell
# 隔离 venv（本工作树 .venv，install.ps1 同流程）
$env:PYTEST_DISABLE_PLUGIN_AUTOLOAD="1"
.venv\Scripts\python.exe -X utf8 -m pytest -q --basetemp D:\prl-tests-20261020g `
  tests\test_search_continue_recovery.py tests\test_candidate_decision_sync.py `
  tests\test_review_sample_limit.py tests\test_review_self_duplicate.py `
  tests\test_search_relevance_regression.py tests\test_search_relevance_interaction.py `
  tests\test_collection_stages.py tests\test_collection_ui.py `
  tests\test_collection_job_recovery.py tests\test_collection_runner.py `
  tests\test_collection_contract.py tests\test_collection_resume.py `
  tests\test_collection_history_cache.py tests\test_verified_collection.py `
  tests\test_review_baseline_consistency.py tests\test_imports_jobs.py tests\test_personal_library.py
# → 196 passed, 8 skipped（隔离 venv 的 Playwright 版本与已装 Chromium revision 不匹配）

# 真实 Chromium UI（主仓库依赖环境，ref_lab 来自本工作树）
python -m pytest -q --basetemp D:\prl-tests-20261020h tests\test_collection_ui.py tests\test_ui_components.py
# → 23 passed

.venv\Scripts\python.exe -m compileall -q ref_lab tools tests   # OK
node --check web/app.js                                         # OK
```

## 未验证 / 剩余缺陷

- A：没有做第二轮真实搜索；小红书/Pinterest 只执行了 3/8 计划查询（达到目标即停），未覆盖
  “最新”排序和全部语言查询；拼图/重修图较多，15 张不是 15 张干净单图；平台排序与召回
  不可复现为严格 A/B。
- B：真实外网 continue 未执行；真实平台“结果轮换”未知；嵌套并发压力只做了 1 组确定性竞态。
- C：只有 5 张有界样本；13 张待审；1 张疑似误收、1 张模型结构校验受阻；参照来源仅 2 个
  官方/授权页面且未做人工真值；项目 ref 只升级了 schema3 preflight，完整 CollectionVision
  仍只在 review-audit/候选队列，不冒充人工 K/I/M。旧历史隐私导致的 Git/Notion 暂停沿用；
  本轮不写 Notion、不合并 main、不切换日用服务。

## Git 发布

- 任务分支：`codex/search-15-review-20261020`（从 `0731cf5c1554cb73d7b3d0b24b4109b56a51cfe7`
  创建）。
- 提交：`0e0fd33e837510654481e441cc8db083ff4f7609`（B 修复 + 回归）；
  `0d0c1fb77a779d8b508b7e0589dac8e21f3afe3a`（C 修复 + 回归 + 真实 A/C 结果文档）。
- 已推送 `origin/codex/search-15-review-20261020`；远端 SHA 与本地一致（见收尾核对）。
- 私有真实证据（不提交 Git）：`.local/run-15-20261020/`、`.local/collection-runs/bedd28c4.../`、
  `.local/ui-data-15-20261020/`。未写 Notion（本轮用户明确禁止）、未合并 main、未切换日用服务。

## 停止状态与查看入口

- 隔离服务仍在运行：`http://127.0.0.1:18789/`（仓库内启动器、独立数据目录，
  与日用 `18765` 服务无关）。
- 候选图库：`http://127.0.0.1:18789/#view=jobs&project=a3ba6fc091d5402285618dbea4891688`
  → “候选图库”（18 原图、15 名称命中、3 未确认、2 AI 通过、2 AI 拒绝、1 受阻、13 待审）。
- 项目候选：`http://127.0.0.1:18789/#view=references&project=a3ba6fc091d5402285618dbea4891688&job=bedd28c47ee5483caba160057673fbd8`。
- 停止隔离服务（不改日用）：在 `.local/worktrees/search-15-review-20261020/root` 运行
  `powershell -ExecutionPolicy Bypass -File scripts\terminate.ps1`。
- 本轮到此停止：不自动开新开发 Loop、不重跑 15 张、不补审剩余 13 张、不合并 main、不写 Notion。



