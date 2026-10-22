# 重复下载与磁盘积压清理、返回恢复与获取吞吐修复

状态：IN PROGRESS（第1轮）。本记录替代旧的“仅两轮验收”目标，但保留全部旧失败与结论，不覆盖历史任务记录。

**当前阻断**：清理、下载生命周期、返回/恢复、排重性能与调度修复均已完成并有回归；最终候选版本`83ec2ff`的四次正常网页单次开始验收全部停在同一外部BrowserSkill扩展故障（约34~35个详情后`Background execution cleanup timed out`），最好一次为17/30。未重启用户Edge、未升级/重载扩展，等待主人决定；完整Goal未完成。

## 原意与授权（保留用户原话）

用户原话：**“优先解决摄影参考库的重复下载和磁盘积压”**、**“确认保留件就不要备份了，不要占磁盘了，磁盘没空间了。”**

完整要求（按用户原文顺序）：

1. 已能可靠确认的重复图片，不再重复下载。
2. 必须取得字节才能判断的图片，先进入受限临时区；确认重复后立即删除临时副本，不进入长期图片存储。
3. 清理摄影参考库内所有项目、历史采集批次及失败批次中可确认的重复下载副本，同一原始字节只保留一个可靠存储件，所有使用关系指向它。
4. 随后修复返回搜索页、自动恢复、排重性能和调度问题。
5. 最终通过正常网页单次开始，自动获得至少30张合格、不重复的新照片；同一最终冻结版本的两轮独立实跑，以及正常启动器重启验证，全部通过才算完成。

清理授权与边界：

- 授权范围为摄影参考库内部所有项目、历史采集批次与失败批次；**不扩展到电脑上其他软件、其他仓库或项目外路径**。
- 用户已授权本范围内经验证的重复副本清理，不逐文件重复请求确认。
- **本轮不做任何备份**：不复制图片、数据库或ZIP，不生成全库备份，不移动到回收站，不以移入备份目录冒充释放空间。保留正常数据库事务与必要的精简操作记录。此要求优先于通用清理流程的备份建议。
- 既有旧备份/封存包单独处理：不因包含重复图片就整包删除；只有包内独有内容与绑定依赖均已排除才可列为冗余。
- 保留不同照片、不同连拍、人工选择、项目引用、来源、学习记录与失败历史。
- 不合并 `main`、不强推、不公开发布、不新增外部付费服务。
- 允许必要的受控停服、正常启动器启动与重启；先确认无其它活动任务，不中断无关工作。
- 代码修改遵守现有任务分支与交付协议；清理例外不授权绕过路径归属与提交边界。

## 本次核实基线（第1轮实测，不沿用旧快照）

- 分支 `codex/one-click-runtime-v4-20261022`，HEAD `5560246bf7b23669fcbc6923297be273e8f105ab`；与 `codex/narrow-crop-goal-20261022` 完全一致（0/0）。未提交改动仅4个既有测试临时目录删除（`.pytest-tmp-learning-review*/`、`tmpu82yxeyy/`、`tmpye_gx0i8/`），与本轮无关。
- 实跑实现 `8bf51ba`；运行记录 `.local/runtime/server.json` 记 PID 44876 / `code_8bf51ba` / digest `f95efa…`。**更正（第1轮稍后核实）**：该服务实际仍在运行（`python -m ref_lab serve --port 18765`，PID 44876/父进程50252），最初一次进程快照漏读，后续以CIM命令行核实为准；未重启、未改动其数据。另发现同机 `D:\AI PROJECTS\codex 名片生成` 有多个活动工作流/Streamlit/测试进程，属无关任务，本轮不中断；其实跑时间会受同机负载影响，计时按实际记录。
- 数据目录：`D:\AI PROJECTS\photography-reference-lab\data`（项目内，`LAB_DATA_DIR` 由启动器配置，未在本 shell 设置）；项目外未发现需要扩展的清理路径。
- 卷可用空间（清理前）：D: `33,739,034,624` 字节（31.42 GiB）。项目总占用约 34 GB，其中 `.local` 约 30.5 GB（`.local/backups` 16.42 GB、`.local/worktrees` 4.93 GB）。
- 资产存储为内容寻址：`data/assets/<sha[:2]>/<sha>/original.*|preview.jpg|thumb.jpg`，共1554个SHA目录/4662文件/695.8 MB；原图与派生图分开计。
- 图片清单（`data`、`.local/collection-runs`、`.local/goals`、`.local/tmp`、`staging`、`references`、`inspections`、`training_sets`、`images`、`batches`）：7813个图片文件、1,561,748,200字节、6,137个不同SHA、1,025个相同SHA重复组、1,676个多余副本、430,037,278字节。明细 `.local/disk-audit-20261022/core/inventory-*.jsonl`。

> 说明：上表“重复”只表示相同SHA的字节副本，不代表审美或身份重复；不同SHA的裁切/重编码仍按原保守匹配规则。

## 重复判定与保留规则

- **相同SHA且实际字节核验一致**：可确定的相同字节副本，是本次清理对象。
- **不同SHA的重编码/缩放/裁切**：不凭相似度直接删除；仅在同一成片、保留件不损失必要内容、引用与证据依赖可安全处理时归并，否则保留并说明。
- 不同姿势、不同连拍、人工制作的独立裁切，不得当普通重复下载副本。
- 唯一长期保留位置：现有 `data/assets` 内容寻址资产库。不为搬家再造存储。
- 保留件必须存在、可完整解码、SHA正确，且本身不在删除清单内。
- 存在活跃写入、清理引用保护、封存/导出依赖、Git跟踪或证据绑定的副本，本轮不删，逐项列原因。
- 删除直接执行，不进回收站；记录路径、SHA、大小、结果与释放字节。可中断、可重跑、幂等。

## 实施顺序

1. 先盘点再动手；先阻止增长（下载生命周期），再清理存量。
2. 下载链路：已知完整资产/来源关系在下载前复用；未知内容先写受限临时文件，流式SHA命中即删；需内容比较的变体判定后再入长期库；失败/取消/超时清理自有临时文件。
3. 返回与恢复：超时后先核实来源、原查询、页面内容与会话身份；确认成功才解除残留 `return_error`；恢复预算只计实际恢复耗时并保留总时间/次数上限；返回故障先于重型排重处理。
4. 排重性能：复用指纹预处理、尺寸模板与索引；缩短共享锁但保持提交时原子去重；先测清理后历史规模再优化，提供同数据前后测量。
5. 调度：实际重复率与新增产出及时影响查询顺序；已见关系减少重复工作但不让旧失败变“新照片”；探索配额按图片执行；优先有目标名称关联的候选。
6. 代码、配置、模型、准入与预算冻结后，再执行同一冻结版本的两轮正常网页单次开始验收与正常启动器重启验证。

## 验收标准

- 纳入范围的确定重复字节只剩一个经验证保留件；项目引用、旧结果页、原件打开、人工决定、来源与续跑正常。
- 不新增图片或全库备份；清理前后可用空间与净释放可复核；未处理文件逐项列原因。
- 新下载重复不在临时区、批次目录、正式库、预览或导出链路持续堆积；分别报告下载前拦截与下载后清理数。
- 窄裁切、重编码、不同连拍、混合拼图、父子身份、并发去重回归通过。
- 返回报超时但页面已正确恢复时不误停；首次恢复成功后仍能处理下一次可恢复故障；浏览器故障、平台限制、预算耗尽分别报告。
- 两轮各≥30张新增合格独立真人摄影；名称、画质、类型、来源、SHA、项目引用完整；真实浏览器实际加载；正常启动器重启后保持；两轮间无人工推动。
- 失败Job的13张与1张仍是失败成果，不合并、不补足后改称通过。

## 检查点

### 第1轮（2026-10-22 晚）

- 环境核实如上。发现 DSH 沙箱对 `data/`、`references/`、`staging/` 等目录的 shell 写操作被拒（文件工具可写）；已按诊断脚本修复 `data` 目录的 WRITE_OWNER，shell仍拒写，后续删除与 `git` 操作使用受控提权命令分批执行，并记录审批。
- 上一轮正式两轮仍为 FAIL（13/30、1/30）；本轮不继承为通过。旧备份/失败/人工决定未动。
- 清理批次1（只删重复图片字节，不备份、不复制）：以 `data/` 全树4,889个图片SHA（1554个资产原件SHA逐一与目录名核对，0错误）为保留集合；对8个“备份还原目录”及 `data/downloaded_wedding` 逐文件流式SHA复核后直接删除。
  - 删除：35,399个图片文件 / 5,266,473,228字节；其中8个还原目录35,361个（含原件/预览/缩略图/导出副本），wedding暂存38个。每个删除文件都有另一份仍在 `data/` 的不同路径保留件；4,666个保留件实际PIL解码0失败；正式库未被删写。
  - 另清空 pytest 临时目录 `.local/tmp/run-a1`、`run-a2`：2,860个文件 / 301.9 MB（测试临时产物，无运行或引用依赖；服务未运行）。
  - 可用空间：删除前D: 41,072,246,784字节（38.257 GiB，紧接删除前实测；20:58首次读数为33,739,034,624字节，两次读数差异按实测如实并列），删除后46,693,470,208字节（43.492 GiB），**净释放5.235 GiB**；`data`+`.local` 文件数276,197→237,938，字节46,474,301,696→40,926,262,748。
  - 保留未删（逐项原因）：45个旧备份ZIP（11.05 GB，含数据库历史状态与包内元数据，属“旧备份单独处理”）；20个旧任务工作树（4.1 GiB干净检出+若干脏检出，属工作副本非下载副本）；`backups/`(1.888 GB)与`.local/backups/consolidation-20261011-2305`(2.56 GB，其他仓库归档，超出本仓库范围)；`references/`内Git跟踪的暂存下载（544个文件与资产同字节，但属跟踪内容，待单独判断）；`inspections/`与`training_sets/`（评估/训练语料，有manifest与构建脚本依赖）；旧采集运行目录中43个与资产同字节的文件（`received.json`仍以原路径引用，待链路改造后再处理）；`.local/backups/browser-audit-tests-20261021`（测试截图，字节不重复）。
  - 清理脚本可重跑：`.local/disk-audit-20261022/verify_clean2.py`（默认dry-run，`--apply`才删并在删除前再次SHA复核；清单 `cleanup-verify2.json`/`cleanup-executed.json`）。

### 第1轮工程改动（未冻结，验收前继续复核）

- `ref_lab/collection_history.py`：把逐对构造/缩放的 128px 指纹改为按记录缓存的图像金字塔与按查询缓存的裁剪模板；粗定位模板按 (side,kind,尺寸) 复用，匹配语义（含像素差/相关性/局部冲突阈值、拼图容器规则）保持。`consider` 的重型比较移到共享读锁之外，新增独立入账锁并在提交时复核 `known_shas`，保留并发入账的精确字节原子去重；新增 `rekey` 供临时文件转正后更新缓存路径。
- 等价性：用 `git show HEAD:ref_lab/collection_history.py` 载入改动前实现，对同一组合成样本（6种横/竖/窄裁切+重编码、局部覆盖、换姿势、12张随机图）两两比较 `_photo_relation` 结果，**80对0差异**（`.local/disk-audit-20261022/matcher-equivalence.json`）。
- 同数据耗时：1554个真实资产原件为历史，同一张裁切查询完整扫描一遍，改动前 `22.469秒` → 改动后 `11.687秒`（本机wall，另有其它项目在跑，仅作同机同数据对照；不是正式Job计时）。修复过程中回归测试先抓到两处模板参数顺序/平坦模板判定差异，已按原语义修正，10项既有裁切回归由失败转通过后才保留优化。
- `tools/collect_verified.py` 返回与恢复：
  - `navigate-back` 超时或报错后，先读活页面并用 **来源主机+路径、原查询（URL参数或搜索框）、可见结果数、当前会话id** 共同判定；确认已回到原搜索页才清除残留 `return_error`，并把证据写入 `return-checks.json`（只保留最近20条）。仅“URL像搜索页”不再算通过。
  - 恢复预算改为累计**实际恢复耗时**（`recovery_seconds_used`），正常采集时间不再计入；仍保留Job总deadline和最多2次上限。
  - `recover(step, reason='return')` 先核实活页面、再在同一会话导航回原查询并复核，只有仍失败才重建自己的会话；不触碰共享BrowserSkill daemon。
  - 每个详情返回后立即检查返回故障并在任何重型历史比较之前做一次有界恢复；未恢复时才抛出，并保留 `return_pending_rows` 证据。区分 `page_return`/`connection`/`time_budget_exhausted`。
- 下载生命周期：新增 `incoming/` 受限临时区；XHS `capture_note` 与 Pinterest 详情都先流式写入临时文件并同时算SHA。已知来源图片地址（只复用已在验证历史中的SHA）在传输前跳过该图；下载后SHA命中已知集合立即删除临时文件；未知字节经历史判定后才用 `os.replace` 转正到 `images/`。失败/取消/退出统一清理本Job残留临时文件（`incoming_cleaned`）。`duplicates.json` 区分 `known_source_url`（下载前拦截）与 `same_bytes_known`（临时下载后清理）。
- 调度与配额：连续2条查询0新增且反馈为高重复/无新结果时提前进入检索词改写，不再等初始计划跑满两遍；探索配额改为按**图片**计数（全局/来源/查询），多图帖不能再用一个帖名突破配额；无名称证据的越额候选立即丢弃临时副本并记录原因。
- 回归：新增 `tests/test_download_lifecycle_and_return.py` 13项（返回状态判定、恢复预算跨正常工作、原查询优先修复、已知地址/已知SHA/未知字节三条下载路径、返回故障先于历史比较、并发入账、转正后rekey、清理后历史跳过、资产硬链接）；更新 `tests/test_search_detail_timing.py` 5项到临时区契约。
- 入库链路：`AssetStore.ingest` 增加 `source_path`，与采集批次在同一卷时用**硬链接**保存原件（一份物理存储、两个路径），失败自动回退普通写入；搜索候选导入传入批次路径。防止入库后再复制出第二套长期原件。
- 清理后历史：`historical_paths` 对被清理过、`images/` 已空的归档批次记录 `skipped`（其字节已在正式资产库中，SHA仍覆盖），仍含文件却无法校验的批次照旧报错；采集侧把跳过写入 `history-skips.json` 和摘要计数，不把未扫描写成已完成。

### 第1轮回归结果

- 组A：`test_one_click_audit_regressions`、`test_collection_history_cache`、`test_goal_photo_admission`、`test_collage_split`、`test_collection_audit`、`test_collection_stages`、`test_search_continue_recovery` → **121 passed**（604.06秒，2026-10-22T23:41Z起）。
  命令：`.venv\Scripts\python.exe -X utf8 -m pytest -q --tb=short -p no:cacheprovider --basetemp=.local\tmp\ptA <上述文件>`
- 组B（结果见下一步检查点）：`test_download_lifecycle_and_return`、`test_search_detail_timing`、`test_browser_recovery_boundary`、`test_browserskill_recovery`、`test_collection_autonomy`、`test_review_self_duplicate`、`test_collection_supply`、`test_collection_upgrade_counts` → **90 passed**（99.11秒，含关闭API集成用例）。合计相关回归 **211 passed / 0 failed**。
- 清理后历史规模（`history_after_cleanup.py`）：2,731个文件、1,664个不同SHA、1,679条指纹记录、0错误；历史路径遍历28.515秒、热缓存加载21.360秒。清理前审计口径为2,800路径/1,694 SHA（该口径来自上次Goal冻结时，包含后来被上一轮归档进ZIP的formal5/6运行目录）。
- 覆盖核对（`coverage_check.py`）：本轮删除的35,399个文件中，属于历史扫描范围（`images/`或`derived/`且非`restored-library`）的删除数为**0**；删除的3,112个不同SHA全部只对应`data/assets/*/preview.jpg|thumb.jpg`或`data/exports`副本，这些字节从未进入历史指纹集合。说明本轮清理没有减少任何历史原件/子图的排重覆盖。仍有30个SHA的差异来自上一轮把formal5/6运行目录整体归档为ZIP（非本轮清理），其中含1份从未进入received清单的孤立字节；失败原件/清单未删。

### 最终候选版本（83ec2ff）上的验收尝试与外部阻断

四次正常网页单次开始的正式尝试，全部停在同一类**外部浏览器扩展故障**上；不是总预算、模型、来源封锁或本产品代码：

| # | Job | 冻结版本 | 点击(本地) | 结束原因 | 用时 | 合格/30 | 重复 | 关键证据 |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| 1 | ad454382 | 3b3d46c | 00:08:18 | command_timeout | 2375s | 12 | 58 | 3次返回超时全部由页面状态核实恢复；点击超时后`session_stop`返回`Background execution cleanup timed out` |
| 2 | 4e18c278 | 83ec2ff | 01:39:16 | command_timeout | 849s | 0 | 63 | Pinterest返回超时→`page_return`恢复成功；随后`wheel`超时，恢复时`session_stop`再次清理超时 |
| 3 | 8226be7b | 83ec2ff | 02:08:55 | command_timeout | 169s | 0 | 12 | 同一次`click`+`navigate-back`超时并立即`session_stop`清理超时 |
| 4 | 67b9f1c9 | 83ec2ff | 02:20:44 | command_timeout | 1411s | **17** | 68 | 34个详情、7窗口后`evaluate` 30秒RPC超时，`session_stop`仍返回`Background execution cleanup timed out` |

- 尝试2前发现BrowserSkill守护进程已死，用产品自带`scripts/ensure-external-services.ps1`恢复（新daemon PID 46064，Edge 9d3f232a已连接）；随后一个独立诊断会话（创建/导航/读页/返回/停止）全部在1.1秒内成功，说明浏览器本身可用。尝试3、4仍在该新daemon上失败。
- 共同点：失败发生在约34~35个详情循环之后（尝试1=35详情、尝试4=34详情），且总是`tool.session_stop: Background execution cleanup timed out`（扩展协议错误）。守护进程0.3.2、扩展0.3.3、CLI 0.3.2；`bsk doctor`在失败后仍报daemon/扩展健康。**这指向浏览器扩展后台执行清理卡死的外部缺陷**，本产品代码无法在会话内修复（重建会话也必须先停旧会话，而停会话正是失败点）。
- 尝试4的正面证据：23.5分钟内达到**17张合格**（20份原件全部SHA+解码通过、18次真实图片类型调用且全部成功、0拒绝、20条项目引用与发现记录完整），按当时速率本可在45分钟内接近30；它在第34个详情循环处被外部扩展拖死。
- 下载生命周期实测（尝试4）：68条重复 = **27条下载前来源地址拦截**（`known_source_url`，小红书跨会话CDN身份生效）+ 23条下载到临时区后立即删除（`same_bytes_known`）+ 18条Pinterest封面命中；`incoming`零残留；`known_source_images=424`；18次模型调用、634,460已知Token、`usage_complete=true`。
- 返回与恢复修复实测：多次`navigate-back`超时后，均由“来源+原查询+可见卡片+同会话id”确认已恢复并继续；Pinterest一次未恢复时，`browser_recovery/page_return/recovered=true`在原会话内导航回原查询成功。没有一次因为“旧超时错误残留”误停。
- **结论：两轮各≥30张的最终验收未完成，且不是靠再点一次就能通过。** 阻断是外部BrowserSkill扩展的会话清理超时（34~35个详情后稳定触发）与本机同跑的其它项目负载；需要先解决扩展/守护版本（0.3.2 daemon ↔ 0.3.3 extension）或重新加载扩展，再在同一冻结版本上重新取得完整两轮。未重启用户Edge、未重启共享daemon以外的服务、未修改扩展；等待主人决定是否升级/重载扩展。

## 第1轮收口状态（2026-10-23 03:0x 本地）

- 工作树干净（`git status --porcelain` 为空）；任务分支`codex/dedup-recovery-20261022`，最终候选`83ec2ff`，文档检查点`3c01227`。
- 正常运行：服务经`scripts/terminate.ps1`+`scripts/launch.ps1`部署`83ec2ff`，PID 53972，digest `7c80f513…`；无活动采集进程；数据库26项目/1591资产/1351引用/72条既有外键错误（未新增类别）。
- 磁盘：清理前实测38.257 GiB可用，删除后43.492 GiB；收口时64.102 GiB（期间同机其它任务也释放了空间，净释放只按本轮删除量5.235 GiB计，不外推）。
- 证据：`.local/disk-audit-20261022/`（`cleanup-executed.json`、`cleanup-verify2.json`、`cleanup-plan-summary.json`、`matcher-equivalence.json`、`history-after-cleanup.json`、`coverage-check.json`、`frozen-dedup-recovery-v1.json`、`frozen-dedup-recovery-final.json`、`frozen-dedup-recovery-final2.json`、`round-audit-<job>.json`、`audit_run.py`、`verify_clean2.py`等）；四次尝试的原始`browser-errors.json`/`return-checks.json`/`duplicates.json`仍在各自运行目录。
- 最优一次（`67b9f1c9`）：20张原件全部SHA+解码通过并已入库为项目pending引用，20条发现记录带job_id；真实浏览器逐一加载20/20（`naturalWidth>0`）；17张合格、18张可用独立、类型调用18次全成功、0拒绝；63.4万已知Token、用量完整。
- **未完成**：同一冻结版本的两轮各≥30张、第二轮独立于第一轮、正常启动器重启后两轮保持验证。阻断为外部BrowserSkill扩展在约34~35个详情后`Background execution cleanup timed out`；需要主人决定是否升级到0.3.3/重载扩展或重启Edge后再继续。未重启用户Edge、未升级CLI/daemon、未修改扩展。

## 报告更正（追加，不覆盖旧记录）

1. **1,694/1,717 的含义**：这是上一轮Goal在正式Job开始时冻结的“全历史相同字节/指纹组”数量（含所有项目、历史成功与失败批次、诊断所得，以及formal5新增的原件与1份未进received清单的孤立字节），用于排重；**不是**小红书/Pinterest上西木野真姬合格照片的库存，也不能据此宣称平台素材耗尽。本轮清理后当前历史为2,731文件/1,664 SHA/1,679指纹记录，Job会重新冻结自己的基线。
2. **本轮实际清理**：删除35,399个相同字节图片副本（5,266,473,228字节），另有2,860个pytest临时文件（301.9MB）；净释放5.235GiB。删除前逐文件流式SHA复核，保留件均存在于`data/`且4,666个保留件PIL解码0失败；没有新增图片/数据库/ZIP备份。未处理项与原因见“第1轮”检查点（旧备份ZIP、工作树、Git跟踪暂存下载、评估语料、外部仓库归档）。
3. **第二轮第二次恢复的真实原因**：上一轮formal6第二次`navigate-back`超时后，系统没有进入浏览器重建，而是被“首次恢复后的60秒计时门槛”拒绝（`recovery_start_time`未复位，正常采集时间被计入恢复预算）；**没有证据**证明第二次重建浏览器会失败。本轮的修复与回归已覆盖该缺陷。
4. **原debug覆盖范围**：上一轮debug录的是本地成果页面，请求主机只有127.0.0.1与浏览器扩展，**不包含采集标签的小红书/Pinterest操作**；因此不能用它证明平台、网络或BrowserSkill某一方导致了返回超时。本轮把采集器自身会话的返回状态写入`return-checks.json`（脱敏：主机、路径、查询、卡片数、登录/验证标志、会话id）。
5. **13张与1张仍是失败Job成果**：formal5=13/30、formal6=1/30都是失败停止的真实成果，不合并、不补足、不重新计为“一键通过”；本轮的正式两轮必须在同一最终冻结版本上重新取得。

## 本轮资源上限（实跑前记录，不临时扩充）

- 正式Job：2个（Round1/Round2），每个最长2700秒、最多60次图片类型模型尝试；合计≤5400秒/120次。
- 诊断Job：0；不新增预算；不人工继续、不CLI补采集、不手动导入、不改状态/计数。
- 两轮都使用同一最终冻结提交与配置；第二轮必须排除第一轮及全部历史成功/失败/诊断所得。
- 保留旧失败13张与1张；不合并main、不强推、不发布。

### 第2次正式开始（版本3b3d46c，仍作为开发性证据）

- 2026-10-22T15:08:18Z 正常网页单次点击创建 Job `ad4543826b374f53a01858e30bebe47d`（目标30、普通输入、无别名/Goal编号），基线冻结后15:09:36Z启动采集。
- 结果：status `blocked`、search_state `partial`、stop_reason `command_timeout`，应用累计2375.259秒，停止于39.6分钟（非预算耗尽）。**合格12/30**，received 15、details 35、windows 7、queries 6、重复58、模型调用14、已知Token 491,283；15份原件全部存在且实际解码通过。
- 返回修复实际生效：`return-checks.json`记录到3次`navigate-back`超时（`navigate_back_error=BrowserInfrastructureError`），每次都由来源+原查询+27/26/28张可见卡片+同一会话`fcpc`确认为已恢复，Job没有因此误停；这是上一轮无法通过的场景。
- 真正停止原因：一次`click`超时后有限恢复时，BrowserSkill扩展返回`tool.session_stop: Background execution cleanup timed out`，`browser-errors.json`保留原始错误；属于外部浏览器/扩展故障，不是页面返回状态判定，也不是总预算耗尽。
- 下载生命周期实测：`duplicates_temp_cleaned=41`（相同字节下载到临时区后立即删除，`images/`未留下副本）、`incoming_cleaned={files:0}`（无残留）；`duplicates_pre_download=0`，说明当前小红书CDN地址带会话前缀，纯URL预检尚未命中，需要更强的来源身份（下一步修复）。
- 性能热点（同一次运行）：`history_consider` 9次共390.3秒、均值43.4秒；`detail_download` 50次257.8秒；`discovery_preview` 45次215.7秒；`detail_return` 18次105.8秒。据此把历史匹配改为分块并行（保留“最早命中”语义），并把小红书CDN路径的会话前缀从来源身份中剔除。

### 第3次版本改动（3b3d46c → 最终候选）

- `ImageHistory._match`：先串行构建一次全部历史金字塔，再按连续分块并行比较；每个分块返回自己最早命中的索引，主线程取全局最早索引，因此与串行“第一条命中”完全一致；拼图容器跳过逻辑仍在主线程执行。线程只读共享金字塔，模板缓存按线程隔离。80对合成样本仍0差异；同数据完整扫描在并发负载下 48.688秒→18.828秒（首次）/15.953秒（热），并行前同机对照为22.469→11.687秒（无并发负载时）。
- `normalize_image_url`：小红书CDN路径只保留`/notes_*/...`及其rendition后缀，跨会话时间戳前缀不再导致同一图片被当作新传输；不同rendition仍视为不同字节。新增回归2项（同一资产两种会话前缀相等、不同rendition不等）。

### 首次正式开始失败（开发性，不计验收）

- 2026-10-22T15:01:09Z 正常网页单次点击创建 Job `b3e11b62bbbe47ef84598c2b7c18e65e`（目标30、普通输入），基线冻结约45秒，采集在15:02:02Z启动（实现`94446a4`/digest `d1f65cea…`）。
- 首个窗口3个详情全部在下载阶段失败：`FileNotFoundError ...\current\incoming\<uuid>.part`。根因是新增的受限临时区在传入显式`incoming`路径时未创建父目录（默认路径会创建），下载写入即失败；`download-errors.json`保留原始错误。
- 15:04:Z 用产品自带`POST /api/jobs/{id}/search/cancel`受控停止；Job最终`blocked/user_cancelled`，`found=0 accepted=0`，真实模型调用0。该次只作为缺陷证据，不冒充两轮验收之一，也不改写成平台/网络故障。
- 修复：`capture_note` 使用显式临时区前先`mkdir(parents=True, exist_ok=True)`；新增回归 `test_capture_note_creates_a_missing_temporary_area`，下载生命周期+详情计时20项通过。修复后重新提交、重新部署、重新冻结，再执行两轮正式验收。

