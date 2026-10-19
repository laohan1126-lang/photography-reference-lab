# 搜图相关性失败复盘与定向修复

## 原始目标（本轮用户原文要点，编辑前记录）

审查基线 `5aec401de8d782e290ac6f13420cf3b000d526d3`，真实任务
`549b320fa82343e9911d5f1c4a919c42`（西木野真姬 / Love Live! / 不限服装）。
用户已审查代码：Search 与 Review 已解耦，但真实交付 4 张图与目标角色严重不相关，
这不是成功的角色搜图验收。要求先解释失败并给出本机证据，再做定向修复；**不要直接开始
另一轮大规模工程重构**。

修复边界：

- 保留 Search 阶段 0 视觉模型调用。
- 建立低成本、多语言的可信名称来源：项目已有名称/人工别名 → 已有可信缓存 → 用户额外填写；
  不得把“角色中文名 + 英文作品名”当成英文角色名，不得臆造别名。
- `discovery_rank()` 不能只排序；实现轻量相关性分层：目标名称/作品线索优先，明确其他角色
  不冒充目标，无文字帖子保留探索但标记“角色相关性未确认”，并设置探索预算，不得提前耗尽目标。
- 小红书优先综合相关性，有界尝试最新；必须用可见网页行为确认排序。
- 快速搜图代表人工审核，不是固定 4 张。默认建议 30，允许自定义；明确实际上限；支持继续加搜、
  主动停止保留图片；已有候选不重复下载/计数；区分部分完成、预算耗尽、真正达标。
- 打通候选图库人工保留/淘汰与项目正式选择，不覆盖既有人工决定；人工保留 ≠ AI 核验通过。
- 检查 `search_review` 双阶段是否真正并行；记录审核执行器和模型配置；真实 AI 审核仍 UNVERIFIED。

本轮不做：20 张完整搜图、昂贵 AI 审核、不改 main/正式库、不合并 main、不写 Notion。

## 基线

- 审查基线：`5aec401`（`codex/search-review-decouple-20261020`）。
- 本轮独立工作树：`.local/worktrees/search-relevance-fix-20261020/root`；分支
  `codex/search-relevance-fix-20261020`。
- 真实任务证据：`.local/worktrees/search-review-decouple-20261020/root/.local/collection-runs/549b320f.../current/`
  的 `name-plan.json`、`collector-state.json`、`received.json`、`search-summary.json`、
  `search-1-window-1.json`（小红书）、`search-2-window-1.json`（Pinterest）、`duplicates.json`；
  验收汇总 `.local/acceptance-20261020/acceptance.json`；数据库
  `.local/ui-data-quicksearch-20261020/library.sqlite3` 的 job/project/refs/discoveries。

## 可观察验收标准

| ID | 通过条件 |
|---|---|
| SR-R1 | 离线复现原查询顺序：XHS 仅 `西木野真姬 cos 摄影`，Pinterest 仅 `西木野真姬 cosplay photography`，无 `Maki Nishikino` / `西木野真姫`。 |
| SR-R2 | 可信名称来源可生成中日英查询并记录实际名称与来源；不得把“中文名 + 英文作品名”写成英文名。 |
| SR-R3 | 保存的四张 Pinterest 卡片只有 `其中包含以下圖片：`，无角色文本；新逻辑不把它们计入目标，不返回 `target_reached`。 |
| SR-R4 | 无标题/无文字但可能相关的卡片仍可在有界探索预算内下载并明确标记“角色相关性未确认”；明确其他角色不直接充当目标。 |
| SR-R5 | 小红书默认优先综合；只有有界、有理由时才尝试最新，并通过可见 DOM 确认。 |
| SR-R6 | UI 默认 30，可自定义；前后端上限一致并提示；继续加搜/停止保留已下载候选；已有 SHA 不重复下载、不重复计数。 |
| SR-R7 | 候选图库人工保留/淘汰同步到项目 refs；既有人工正式决定不被覆盖；`human_keep` 与 `accepted` 分离。 |
| SR-R8 | `search_review` 确实同时启动 Search 与 Review；Search 不等待 Review；记录执行器/模型来源为 UNVERIFIED。 |
| SR-R9 | 快速模式仍是 0 视觉模型调用；本轮不跑真实 AI 审核、不跑 20 张、不改 main/正式库。 |

## 进展

- 2026-10-20：已读取 549b 全部保存快照与数据库记录，确认原查询/排序/计数/人工同步缺陷；
  建立独立工作树，开始最小修复。

## 根因与证据（本轮实测记录）

- **实际查询**：549b `name-plan.json` 的 steps 为小红书 `西木野真姬 cos 摄影`、Pinterest
  `西木野真姬 cosplay photography`；`search-summary.json` 的 `queries` 与之一致。第三条
  `西木野真姬 cos 场照` 从未执行（`observed=false`）。项目/Identity Context 的 en/ja 别名为空；
  `deterministic_plan` 只产生 `西木野真姬` 与 `西木野真姬 Love Live!`，从未读取此前保存的
  `Maki Nishikino`/`西木野真姫` 名称计划，也没有用户别名入口。
- **小红书**：`search-1-window-1.json` 有 18 张可见卡片、`sort_latest=true`、
  `sort_state=latest`。`collector-state.json` 记录 8 个 XHS 详情页尝试、`details=12`（含 4 个
  Pinterest）、`received` 中 0 张 XHS、`duplicates` 中 0 个 XHS、`search-errors=[]`。
  未尝试的 10 张是 `SAMPLE_PER_QUERY=8` 上限；8 张详情页没有留下逐页“未打开/无可用图”原因，
  因此不能把 0 张说成“0 次下载失败”，只能确认 0 行被追加/计数。
- **小红书排序**：`Browser.search()` 在拿到任何卡片后无条件点击“最新”，没有“综合”分支；
  `XHS_SORT_JS` 当时也只返回最新状态。这不是平台强制，而是代码默认。
- **Pinterest 四张**：`search-2-window-1.json` 中对应四张卡片的可见文字都是
  `其中包含以下圖片：`；`received.json` 的 `source_text="\n"`，`refs` 的 `source.title=""`。
  四张的运行时 `discovery_rank` 未落盘；按同代码与卡片文字重建均为 3（未命中名称、无摄影
  意图词、无负类词），且没有任何原帖标题/描述/角色文字证据。项目里显示的
  `西木野真姬 · 快速搜图候选` 是导入器生成的标题，不是来源证据。
- **assess_search 未拦阻**：它以 `character_aliases` 做文字命中，但调用方只传 `character`，
  且只处理 `STOP_STALE_QUERY/REVIEW_QUERY_REWRITE/CHANGE_QUERY_OR_SOURCE` 三种 action；
  无命中返回的 `SAMPLE_THEN_CHANGE_SOURCE` 被忽略。`discovery_rank` 只参与排序，不参与准入。
- **4 张即完成**：UI 默认目标 4；`limit_reason()` 只比较 `len(received)` 与 target；
  `write_search_summary()` 只要有收到图片就写 `completed`。`target_reached` 表示“下载数到了”，
  不是“角色相关数到了”。数据库 job 的 `search_state=completed`，但 job row `status=blocked`，
  因为 `update_search_stage()` 在审核未运行时把总状态改为 blocked；这会让“搜索完成”和
  “任务待恢复”同时出现，属于状态展示缺口。

## 最小修复（本轮）

- 新增 `ref_lab/search_relevance.py`：文字分级 `target_named/target_context/unconfirmed/
  other_character/non_photo`；只有 `target_named` 计入目标；无文字/缺标题保留为探索候选并标记
  “角色相关性未确认”；同角色名称但无摄影意图也保留。探索预算
  `max(1,min(8,target//4))`，不会提前耗尽目标。明确其他角色/非摄影内容不下载并计数跳过。
- `ref_lab/identity.py` 增加人工维护的 `西木野真姬` preset（`西木野真姫`、`Maki Nishikino`、
  `Nishikino Maki` 等，含来源说明）及 `trusted_alias_records()`。名称来源顺序：
  project → identity context → 人工 preset → 用户 `search_aliases`；不读取旧模型 name-plan。
- `deterministic_plan/query_steps` 改为语言感知：XHS 优先中/日/英，Pinterest 优先英/日/中；
  作品只作为独立上下文词，不拼成假英文名；每个 step 记录 `used_name/name_source/language/
  work_term/intent`。不再把中文名+英文作品名当英文名。
- 小红书：默认优先“综合”；用可见 `.tags` 的 active 状态确认；仅当相关性查询没有名称命中时，
  对后续查询有界尝试一次“最新”，不使用隐藏 API。
- 额度：表单/模型默认 30、上限 100，帮助文字明确；API `JobInput` 同步 100。新增
  `/api/jobs/{id}/search/continue`，同一 job 增加 `search_extra_target`，保留已下载候选并
  重置本轮查询/页面扫描；`received` 按 SHA 去重，不重复计数。停止搜索保留已下载候选。
- 人工审核：`Library.decide_candidate_human()` 在写 `human-decisions.json` 的同时把决定写入
  项目 ref（`decision_origin=human_candidate_queue`）；已有 `human_curation/human` 正式决定
  冲突时返回 409，不静默覆盖。`human_keep` 仍不等于 AI `accepted`。
- `search_review`：代码核对 `start_job()` 先 `launch_search()` 再 `launch_review()`；
  Review 以 `--review-only --wait-search` 独立线程/进程/锁运行，Search 不读取 Review 状态。
  Review 执行器为 `AntigravityCollectionAgent`，`LAB_COLLECTION_COMMAND` 配置本地适配命令，
  `LAB_CLASSIFICATION_MODEL` 默认 `gemini-3.8-flash-medium`，CLI 由 `ANTIGRAVITY_CLI`/
  `find_antigravity_cli()` 发现。真实视觉审核本轮未运行，状态 UNVERIFIED。
- 新增/更新回归：`tests/test_search_relevance_regression.py`（旧 549b 查询、可信别名、
  四张 Pinterest 不达标、XHS 缺标题保留、其他角色排除、继续加搜、综合优先）、
  `tests/test_search_relevance_interaction.py`（默认 30/上限 100、人工同步/冲突）、
  以及原有 stage/UI/collection 测试中的旧断言更新。

## 验证结果

- 定向回归（本机 Windows Python 3.12 + 仓库 `.venv` 依赖）：
  `tests/test_search_relevance_regression.py tests/test_search_relevance_interaction.py
  tests/test_collection_stages.py tests/test_collection_ui.py tests/test_verified_collection.py
  tests/test_review_baseline_consistency.py tests/test_collection_contract.py
  tests/test_collection_runner.py tests/test_collection_job_recovery.py
  tests/test_personal_library.py tests/test_imports_jobs.py tests/test_collection_supply.py`
  → **190 passed, 1 warning**。
- 四张原图基线回归 `test_review_baseline_consistency.py` 通过；真实 4 图 SHA/accepted 未改。
- 快速 Search 新集成测试断言 `model_calls=0,tokens=0`，没有调用 NamePlan/Reference/Vision。

## 未验证 / 限制

- 没有重新访问小红书/Pinterest，也没有跑真实 4 张以上搜索；综合/最新的真实网页结果、新的
  中日英查询词召回率均未在线验证。测试只使用保存的页面文字和合成替身。
- 小红书 8 个详情页 0 行的逐页原因缺少原始逐页记录（快照只保存窗口，不保存每页失败原因），
  不能断言是登录、DOM 变化还是无可用图。
- 没有运行真实 AI Review，因此审核通过率、真实身份判断和模型耗时仍 UNVERIFIED。
- 人工同步使用现有 SQLite ref + 原子 JSON；未做法务/多用户并发压力测试。
- 没有改 main、正式库、Notion；没有合并或部署。
