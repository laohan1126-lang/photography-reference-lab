# 采集查重项目边界修复：同项目防重复、全库复用原件

日期：2026-10-24
分支：`codex/dedup-project-scope-20261024`（基线：`69c57f6`，即 `codex/dedup-recovery-20261022` 当前 HEAD）
状态：**IN PROGRESS**

## 用户目标（原话保留，优先于实现叙述）

> 修复采集查重范围过大的问题，实现"同项目防重复、全库复用原件"。
> 完成实现、针对性验证和正式交付后停止，由 Astra 独立复审。
> 不要继续旧的"双轮各30张"采集目标。

### 必须实现的行为（用户原文）

1. 相似图片查重以 project_id 为边界。
   - 当前项目已有图片、本项目此前采集收到的图片、本轮新图，参与查重。
   - 同项目历史包含失败或未导入批次，但必须有可验证的项目归属。
   - 不因角色名称相同，就自动合并两个项目的查重范围。
   - 新项目不得默认加载其他项目的一千多张图片做相似比较。
   - 历史归属不明时，保留原记录并报告，不退回全库扫描。

2. 全库只保留轻量的完全相同文件查询。
   - 用文件指纹查找已有原件，避免重复存储。
   - 另一项目已有相同文件时，允许当前项目建立自己的参考关系。
   - 不继承另一项目的人工选择、角色认定、卡片验收。
   - 不得把"复用已有原件"汇报成"新下载了一张"。

3. 同项目的相同文件、缩放、转码和裁切重复，仍须按现有规则拦截。
   不得通过降低重复检测标准获得提速。

4. 测试、QA、探针和合成素材不得进入真实采集历史。
   当前已发现目录名称排除不完整。修复真实历史的来源边界，
   不要继续堆叠几个目录名称黑名单。
   不删除测试文件、历史原件或旧回执。

5. 项目范围必须贯穿任务创建、历史基线、查重缓存、采集、
   恢复和成果计数。不能只在最后显示结果时过滤。
   保留旧任务的原始证据，不改写旧回执来制造通过结果。

### 执行边界（用户原文摘录）

- 先读取 AGENTS.md、docs/tasks/CURRENT.md 和相关实现，核对真实数据目录、分支及已有改动，再记录本次目标。
- 遵循项目既有 Publisher 流程，在首次编辑前建立事务。
- 采用最小完整修复，优先修改共享边界。不扩展新功能，不改搜索平台、角色判断标准或用户审美规则。
- 沿用现有已授权的浏览器和模型接入方式。不新增付费 API、充值要求或外部服务依赖。
- 本轮默认使用本地现存真实图片验证，不启动新的30张采集轮次。

### 验收标准（用户原文）

- A. 范围正确：记录一次真姬项目和一次新项目的实际查重输入清单；能解释每张历史图片为何属于当前项目；其他项目、无归属测试图不得参与相似比较。
- B. 同项目防重复仍有效：真实图片验证原文件重复、缩放/转码版本、裁切版本能被拦截；真实不同图片能通过。沿用已有有效反例，不削弱测试。
- C. 跨项目复用正确：同一原件在两个项目中可以分别使用；只保存一份原件，各自的人工选择和验收状态独立。已有目标项目关系不得被覆盖。
- D. 新项目成本不随无关图库增长：增加其他项目图片后，新项目的相似比较数量不会随之增长。不得隐式建立或遍历全库视觉指纹作为前置步骤。
- E. 性能有实测：同一批现存真实图片、相同环境，比较旧全库范围与新项目范围的历史准备耗时、单候选比较耗时和实际比较数量。报告实际结果，不预设提速倍数。
- F. 恢复与数据安全：任务恢复或正常重启后，项目范围不丢失、不退回全库查重，图片、来源和人工选择不变。涉及真实库写入时遵循既有备份与恢复要求；优先在仓库 .local/ 内隔离验证。

### 停止条件

所有标准满足后停止，不自动追加联网采集或优化。出现相同失败且没有新证据时，先查根因。
最后明确写"待 Astra 独立复审"，不自行宣布用户最终验收通过。不合并 main，不删除用户图片，不把技术通过写成用户审美认可。

## 现状核对（实现前证据）

- 分支 `codex/dedup-recovery-20261022`，HEAD `69c57f6`，工作树干净。
- 真实数据目录 `D:\AI PROJECTS\photography-reference-lab\data`（`.local/windows-runtime.json` 指定），库 `data/library.sqlite3` 约 19.8MB，26 项目、1774 资产、84 个采集 Job、595 条真姬（`1ed24eed…`）refs。
- `.local/collection-runs/` 共 36 个目录：29 个可通过 jobs 表归属到项目（真姬 24、渡辺曜 2、南小鸟 1、跨项目复用测试等）；**7 个无归属**：4 个 UUID 目录（`0fe3d506…`、`8ffed561…`、`99588662…`、`d503705f…`）+ 3 个测试/诊断目录（`agy-autonomous-maki-20261019`、`agy-flowfix-maki-20261018`、`agy-online-maki-20261018`）。
- 现行排重基线是**全库**：`ref_lab/collection_history.py::historical_paths` 扫描 `data/assets` 全部原件（逐个重哈希）+ `.local` 下所有 `received.json` 运行目录（仅靠目录名前缀黑名单排除 test*/pytest*/browser*/fixture*），`ImageHistory` 无 project 概念；`ref_lab/service.py::_create_auto_goal` 建基线时再全表扫 `assets` 并全部重哈希；指纹缓存 `.local/history-fingerprints.json` 全局共享（按路径键，本身无害）。`tools/collect_verified.py` 与 project_id 完全无接触。
- 测试素材混入通道即上列 7 个无归属目录 + 任意新目录都可能被 os.walk 扫到（例如 `agy-browser-evidence`、`path-contract-probe` 这类名字不命中现有前缀黑名单）。
- 跨项目同名角色不会合并查重范围的新边界须显式按 project_id 归属；真姬（1ed24eed）与历史王昭君多项目并存是现实验证场景。

## 实现设计（最小完整修复，改共享边界）

1. `ref_lab/collection_history.py`：
   - 新增 `collect_history_scope(root, current, project_id, history_roots, skipped, unattributed)`：以只读 SQLite 连接查询真实库 `jobs`（kind='collection'）与 `refs`，把运行目录按 job_id→project_id 归属；相似查重路径集只含本项目 refs 的资产 + 本项目运行目录（含失败/未导入批次）的 images/received/derived，全部沿用现有逐字节校验与 keeper 规则；同时产出全库"轻量精确索引"（SHA→keeper 路径，仅取自资产库与运行目录的 SHA 目录名/文件名，不解码不预哈希）与"无归属运行"报告清单。
   - 无归属运行：不进入相似比较范围，也不退回全库扫描；保留原记录并报告。
   - 运行目录发现从"递归 os.walk + 目录名黑名单"改为"按 jobs 表归属直接构造路径"，测试/探针/合成目录（无 DB 归属）结构上不可能进入真实历史。
   - `ImageHistory` 增加全局精确索引 `library_shas`（SHA→keeper）：精确命中本项目 `known_shas` 仍按 `same_bytes` 拦截；精确命中全库（他项目）返回 `same_bytes_library` 复用结果（不拦截），由调用方建立本项目参考并复用原件；感知比较只在本项目记录上进行。算法版本不变（FP5），同项目拦截标准不降低。
2. `tools/collect_verified.py`：三处历史构建点传入 job 的 project_id；下载路径把"全库精确命中"处理为复用原件（硬链接 keeper、received 行标注 `original_reuse`、计入 `reused_originals`，不汇报为新下载）；封面/审核/拼图子图只按本项目范围拦截；`_known_image_sources` 只读取本项目归属运行。
3. `ref_lab/service.py::_create_auto_goal`：冻结基线只含本项目范围（refs + 本项目运行），不再全表扫 assets、不再全库感知指纹。
4. `ref_lab/collection_counts.py`：报告 `reused_originals`（复用原件数），其余语义不变；成果计数继续经由项目级 goal 基线。
5. `ref_lab/collage.py`：子图精确命中他项目原件按复用处理，不再标记 DUPLICATE_HISTORY；同项目拦截不变。
6. 恢复路径（`restore_history_index`、`resume_collection_attempt`、`continue_imported_partial`）重建同一项目范围历史，不退回全库。

## 测试计划

- 更新 `tests/test_collection_history_cache.py` 等历史范围测试到新契约：项目归属、他项目排除、无归属报告、合成目录结构性排除、跨项目精确复用、同项目缩放/转码/裁切仍拦截。
- 保留全部感知匹配（dHash/裁切模板）反例与完整性测试，不削弱。
- 验收 A–F 用真实库在 `.local/` 隔离脚本内只读+隔离写验证；不启动真实采集轮次。

## 检查点

- （实现前）现状核对完成，见上。
- （实现完成）改动文件：`ref_lab/collection_history.py`（核心：`collect_history_scope` + `ImageHistory.library_keepers` + `_verified_keeper`）、`ref_lab/service.py`（`_create_auto_goal` 项目级冻结基线）、`tools/collect_verified.py`（三处历史构建点带 project_id、下载路径复用原件硬链接、`_known_image_sources` 项目范围、`history-index.json` 范围证据）、`ref_lab/collage.py`（子图跨项目精确命中按复用处理）、`ref_lab/collection_counts.py`（`reused_originals` 计数）；测试更新 12 个文件 + `conftest.py` 新增 `library_db` 归属夹具。旧 `historical_paths` 已移除，不存在备用全库路径。

## 验收结果（A–F）

证据目录 `.local/dedup-scope-20261024/`（A-scope-evidence.json、BC-dedup-reuse.json、D-cost-isolation.json、E-perf-old/new.json、F-restart-run1/2.json）。

- **A 范围正确 — PASS**。真姬项目 `1ed24eed…`：感知比较集 1751 路径（619 唯一 SHA），来源两类——(1) 本项目 refs 引用的资产（jobs/refs 表归属），(2) jobs 表中 project_id 一致的 22 个 collection 运行目录（含 blocked/失败批次），每个运行都可由库表解释归属；全库精确索引 1812 项仅含 SHA→保留件路径。新项目（澜 `af3ebe10…`）：感知比较集仅 30 张，其他项目 1781 张图与 5 个无归属运行目录均不参与。5 个无归属运行（4 个 UUID 目录 + 3 个 `agy-*` 测试/诊断目录）逐项报告于 `A-scope-evidence.json`，原记录保留未动。
- **B 同项目防重复 — PASS**。真姬真实原图（SHA `1b7b5905…`）字节副本→`same_bytes`；缩放 3/4 + JPEG q88 转码→`near_duplicate`（pixel_difference 0.394）；60% 中心裁切→`crop_duplicate`（correlation 0.998）；库外全新真实尺寸合成图→None（通过）。FP5 算法版本与阈值未改动。
- **C 跨项目复用 — PASS**。以渡辺曜项目真实原件（SHA `6e3674b2…`）对新建项目查询：`same_bytes_library`+`reuse=True`+已验证 keeper 路径；入库采用硬链接（同 inode、nlink≥2，物理只一份）；同项目第二次相同字节→`same_bytes`（重复）。复用结果只含 SHA 与 keeper 路径，不携带任何人工选择/角色认定/验收状态。隔离库演示：同一真实字节两项目各建 reference，assets 1 行、refs 2 行，甲 keep / 乙 pending 互不影响，既有目标项目关系不被覆盖。
- **D 成本隔离 — PASS**。澜项目感知比较集在其他项目沙盒新增 120 张图后保持 30→30，仅全库精确索引 1812→1932（纯文件名级，不解码）。无全库视觉指纹前置遍历。
- **E 性能实测（同库同环境，冷指纹缓存）— PASS**。旧全库范围（基线 69c57f6 代码，`.local/worktrees/dedup-scope-20261024/baseline`）：历史准备 188.734 秒、感知记录 2026、单个全新候选完整比较 11.157 秒。新项目范围（真姬）：准备 76.360 秒（暖缓存 16.8 秒）、感知记录 619、单候选 3.234 秒。澜级小项目准备 2.0–2.6 秒。另注：旧范围把本轮沙盒合成图也扫入"历史"，实测证实旧范围过宽。未预设倍数，实际约 2.5×/3.5×，随项目规模变化。
- **F 恢复与数据安全 — PASS**。两个独立进程重建真姬范围：路径集合 SHA256 完全一致（`95f9de1e…`），计数一致（1751/1812/22/5），不退回全库。恢复链路回归通过（`test_collection_controller_recovery` 13 项含 `continue_imported_partial`、`test_collection_local_finalization`、`restore_history_index` 相关用例）。真实库全程只读；所有写操作在 `.local/dedup-scope-20261024/` 与 pytest 隔离目录内。旧回执、失败 Job、测试文件一律未删除。

## 回归

- 定向（本轮更新+新增）：`test_collection_history_cache` 21、`test_history_missing_keeper` 10、`test_collection_audit` 10、`test_collection_autonomy` 13、`test_collection_stages` 13、`test_collage_split/audit`、`test_goal_photo_admission`、`test_verified_collection` 31、`test_collection_controller_recovery` 13、`test_one_click_audit_regressions`、`test_download_lifecycle_and_return`、`test_duplicate_payload_lifecycle`、`test_collect_repeat_association`、`test_review_self_duplicate`、`test_pinterest_repeat_metadata`、`test_collection_efficiency` 等：合计约 370 项全部通过（分批执行，无失败）。
- 扩大（共享 service/库影响）：`test_library`、`test_workers`、`test_operations`、`test_personal_library`、`test_modality_archive`、`test_reference_transfer_board`、`test_collect_adapter` 共 113 passed；`python -m compileall ref_lab tools tests` 通过。
- **既有失败（与本轮无关，已用 git stash 在基线 `69c57f6` 复现同因）**：`test_collection_runner` 8 项失败（"本 Job 已用累计执行时间预算"——这些用例未隔离 service 根目录，create_job 会在真实库上建 Goal，叠加用例内 3 秒 `LAB_COLLECTION_TIMEOUT_SECONDS` 后必然超支；本轮改动使 Goal 建立更快而非更慢）。如实保留，未修改该用例语义。
- 本轮验证期间发现并移除一个由失败测试写入真实 `.local/collection-runs/cli-job/` 的杂散目录（仅含测试 blocked 汇总，系本次失败用例 `_summary_blocked` 未隔离所致；删除的是本轮测试自己刚产生的文件，非历史数据）。

## 未验证/限制

- 未启动真实浏览器采集轮次（按本轮边界）。真实下载路径上的复用硬链接由单元级验证与 `_promote_temporary` 逻辑覆盖，未做端到端联网实跑。
- 旧 Goal（冻结于全库基线）的续跑仍用其原基线——按要求不改写历史冻结证据；新 Goal 一律项目级。
- `test_collection_runner` 既有失败如上，属测试隔离问题，留待独立任务处理。

## 交付

- 分支 `codex/dedup-project-scope-20261024`；Git 状态与远端 SHA 见 Publisher 回执；Notion 状态另行如实报告。
- 本轮所有技术验收为 AI 自测；**待 Astra 独立复审**，不自行宣布用户最终验收通过。
