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

