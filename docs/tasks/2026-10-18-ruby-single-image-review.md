# 2026-10-18 星野露比逐图人工评价闭环（评估方法修复）

## 用户目标与边界（实现前，保留原意）

上一轮露比盲评把同一批照片按不同排序重复展示，要求判断 A/B 哪组更好；这没有有效采集逐图审美真值，也把算法排序实验变成了重复看图。本轮必须修复：

- 正确流程：16 张独立图片 → 用户逐图评价一次 → 保存评价 → 对照冻结的三种排序 → 自动计算指标 → 展示结论。
- 本轮属于评估方法修复，不是新一轮模型训练。
- 不得修改训练数据、模型参数、特征权重、原始候选池或已冻结的预测结果；不得修改正式 K/I/M/X；不得重新联网搜索星野露比；不得改变上一轮 NOT_PROVEN 结论。
- 所有新评价写入独立的本地实验文件；不得上传私人图片或人工评价。
- 不得使用用户本轮评价调整排序后再计算同一批图片来证明成功；不得伪造、预填或替代用户审美评价。
- 先完成程序与空标签验收，等待用户实际完成逐图评价后才产生有人工真值的最终对照结论。

## 冻结现场（实现前已记录）

- 分支 `codex/learning-loop-v1-20261018`，HEAD `d3486efaf3f4079c0d7dfa65b553127c32a74c7d`。
- `python -B -X utf8 tools/learning_v1.py check-freeze` → PASS，20 个文件哈希一致。
- 保护清单 SHA256、16 张原图逐字节校验（16/16）与当时 Git 状态保存于私有文件 `.local/learning-v1/human-review-before.json`。
- `freeze.json` 的 `file_hashes` 同时覆盖 `tools/learning_v1.py`、`tools/learning_v1_report.py`、`tools/learning_v1_search.py` 与 `tools/collect_adapter.py`。因此本轮**不修改** `tools/learning_v1_report.py`；新增独立模块并复用其 `STYLE`、`document`、`escape` 等渲染函数。修改该文件会使冻结哈希检查失败，与“冻结输入/实现保持不变”的硬约束冲突。

## 实现方案

新增 `tools/learning_v1_human.py`（单文件、标准库为主）：

1. 读取冻结的 `ruby-pool.json`、`ruby-predictions.json`、`ruby-evaluation.json`、`model.json`、`freeze.json`，记录输入哈希并拒绝漂移。
2. 按 `asset_sha` 去重；以 SHA 升序作为稳定、中立、与模型无关的展示顺序，分配统一编号 `R01`–`R16`。
3. 生成真实可交互页面 `.local/learning-v1/ruby-human-review.html`；默认只监听 `127.0.0.1` 的最小 HTTP 服务提供页面、图片与保存接口。
4. 三个独立维度：角色准确性、摄影参考价值、个人审美；可选一句原因；支持跳过、上一张/下一张与键盘操作。
5. 草稿按 SHA 原子写入 `ruby-human-labels.json`，页面在刷新/重开后从服务恢复；提交后写独立只读快照 `ruby-human-labels-final.json`。
6. 只在用户提交后（或显式运行 report 时）用冻结排序计算指标，输出 `ruby-human-metrics.json` 与 `ruby-human-report.html`。
7. 缺失标签不按 0 计；覆盖不足显示 N/A；完全相同排序报告 `NO_RANKING_DIFFERENCE`；总结论保持 `NOT_PROVEN`。

## 可观察验收

- 每个独立 SHA 只展示一次、只计一次；跳过不计为不喜欢；三维度互不覆盖。
- 刷新后草稿恢复；最终快照只读；正式 K/I/M/X、冻结文件、预测 SHA 不变。
- 空标签报告不产生虚假准确率。
- 自动化测试使用合成数据；真实露比图片只做只读浏览器验收，不产生虚假评分。

## 检查点

Publisher 事务 `adcc1167-e0bb-431f-b8ca-9c9cf1894d90` 已在编辑前 start 并声明合同；冻结现场已记录。实现、测试、浏览器验收与最终发布结果追加在下方。

## 实现与实际结果（追加）

已新增 `tools/learning_v1_human.py`（标准库 HTTP + JSON，未编辑冻结的 `tools/learning_v1_report.py`）：

- 从冻结文件读取 16 张露比候选，按 SHA 去重并以 SHA 升序生成稳定中立顺序 `R01`–`R16`；未发现重复 SHA、近似重复或训练集重合，16 张均可计分。
- 单图页面含三个独立维度、可选一句原因、上一张/下一张/跳过/键盘操作、原图大图与来源链接；不显示模型分数、策略名或排序建议。
- 草稿按 SHA 原子写入 `.local/learning-v1/ruby-human-labels.json`，刷新后从服务恢复；提交写只读快照 `.local/learning-v1/ruby-human-labels-final.json`，并生成 `.local/learning-v1/ruby-human-metrics.json` 与 `ruby-human-report.html`。
- 指标只读冻结的 baseline0 / baseline1 / candidate2：Top-5 喜欢数、分级 NDCG@5、摄影可用数、角色确认/错误/未确定、覆盖与缺失；缺失标签不按 0，Top-5 不完整时 NDCG 为 N/A；完整排序相同报告 `NO_RANKING_DIFFERENCE`；候选2未同时超过两个基线时明确写明没有改善；结论始终保留 `NOT_PROVEN`。
- 服务只监听 `127.0.0.1`；页面与报告不发起外部请求。

实际验收：

- `python -B -X utf8 tools/learning_v1.py check-freeze` → PASS（20 个冻结文件哈希一致）。
- `python -B -X utf8 -m tools.learning_v1_human verify --baseline .local/learning-v1/human-review-before.json` → PASS，33 项（17 个受保护文件 + 16 张原图）全部一致。
- 自动化：`pytest -q tests/test_learning_v1_human.py` → 18 passed。合并回归 `pytest -q tests/test_learning_v1.py tests/test_learning_v1_human.py tests/test_learning_query_plan.py tests/test_search_quality_loop.py -k "not detail_dom"` → 46 passed, 2 deselected（本机 `python -m pytest` 不可用，实际用 PATH 中的 pytest 并设置 `PYTHONPATH`；仓库 `.venv` 的 pytest 缺 `iniconfig`，未修环境）。
- 空标签真实报告：16 张独立 SHA、0 人评价、所有指标 N/A、`NOT_PROVEN` 不变；未创建真实 `ruby-human-labels.json`。
- 真实浏览器（Playwright/Chromium）：合成数据完成保存、刷新恢复、关闭标签页后重开恢复、跳过、提交、只读快照、报告生成、桌面与 390px 窄屏；真实露比页只读浏览 16 张，全部图片实际加载、R01–R16 唯一、无策略/分数泄漏、无标签写入。证据见 `.local/learning-v1/browser-human-review-verification.json`、`e2e-review-mobile.png`、`real-review-mobile.png`。
- 验收中发现并修复一个回归：离开页面时 `visibilitychange` 会 POST 空草稿，生成全空标签文件。现客户端只刷新有内容的条目，服务端对空草稿返回 `noop` 且不写文件；已补回归测试，并确认重新打开/翻页/返回总览后真实标签文件仍不存在。该全空文件已核验无任何用户选择后删除。

尚未验证 / 仍缺少：

- 用户本人的逐图评价尚未发生；因此没有有人工真值的最终对照结论。
- 本轮浏览器验收走 HTTP；未重新用 `file://` 打开新页面（工具阻止 file 协议），静态相对路径与旧入口保持一致。
- 来源作者为空、16 张集中在 Pinterest；报告标记 `UNVERIFIED_PLATFORM_ONLY`，不能宣称独立拍摄组或外推。
- Git/Notion 最终状态见 Publisher 实际回执；不得由测试通过推定发布成功。
