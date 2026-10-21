# Photo15 独立验收与有限优化

## 原始目标与边界

用户要求：不直接相信 Sol 的完成声明，独立核对原 Goal、真实应用流程、代码和测试；先测量瓶颈，修复范围明确且安全的缺陷，完成相关回归，分别报告功能、工程和交付结果。保留数据与既有修改，不扩展功能。

起点 `77216b498c7556df87b3371be6919ba7303916b1`，日用工作树干净；修复在 `.local/worktrees/goal-photo15-independent-audit-20261021/root` 的任务分支进行。不合并 main、不重启或切换日用、不写 Notion，不新增模型调用或采集预算。编辑前 Publisher 事务已建立，合同明确 Git-only；首次 host-cwd 不一致被拒绝，修正为实际工作树后使用同一身份成功，未重建已有基线。

## 修改前独立证据

- 原 15 张逐张打开，11 个原件及 4 个有效子图均为不同真人摄影。逐项重算原件 SHA、严格解析原生 view_file 流、复现预览 SHA、重裁像素及项目引用通过；统一计数 15；SQLite integrity=ok，旧外键错误 72。私有脚本第一次错误使用 asset_id 字段而非 asset_sha，纠正脚本后核对通过，未改产品数据。
- 日用成果页真实浏览器显示 15/15，15 图片全部加载，15 个证据详情存在。
- 普通非 Goal 搜图反例：目标 1，下载 4 个名称命中候选，因没有分类 worker 却使用 usable_named 作为停止目标，最终 relevance_unconfirmed。原测试通过预置 synthetic_type 掩盖了此路径。
- 历史发现 cProfile：1584 条路径、46.786 秒；11423 次 resolve，21442 次 stat；遍历不跟随链接，反复解析已验证树中的目录占主要时间。
- 主环境测试受沙箱 socketpair 阻塞，保存栈后停止本轮测试进程，正常本地权限重跑隔离测试。不是业务失败。

## Blueprint 与反补丁判断

Python/FastAPI 服务、文件检查点、现有 Antigravity 分类器、普通 JS 网页。复用 shared compute 和历史扫描函数：普通模式以名称命中独立候选停止，Goal 仍以严格摄影证据停止；原照片计数不降级。分类器在失败/中断时也保留原始流和真实已报告用量。历史扫描只减少重复目录解析，保持文件边界、链接拒绝和逐文件 SHA 验证。新增回归覆盖普通模式无分类回执、失败流留存和历史完整性；不改库结构、审美、身份审核或平台控制。

## 已完成修复

1. `collection_counts.compute` 明确返回 target_metric/target_progress。普通搜索使用 named_candidates；有基线的 Goal 继续使用 usable_named。采集器停止、收尾、summary、counts 和队列共用同一集合；不把候选数写成合格摄影数。新回归不注入 synthetic_type，旧实现目标1实收4仍未达标；修复后正常结束且合格摄影保持0、模型调用0。创建任务→采集回执→导入→API候选→原件SHA链路在隔离库通过，平台仅使用明示测试替身。
2. `AntigravityClassifier` 在非零退出、超时和中断的 finally 中先停止自己的进程树，再保留原生输出流和实际报告用量；缺失用量仍未知。成功准入继续执行原严格 view_file/parser/asset_sha。退出和取消两项回归在旧版均缺 stream_path，修复后流、SHA、ERROR用量17均保留且不准入。
3. `PhotoTypeWorker` 接收本轮 agent.model。此前用户选定模型未传到类型分类器而静默落到默认型号，新增分发回归先失败、后通过。未换模型、未追加真实调用。

## 性能实测

`historical_paths` 不再对已解析根目录、已拒绝链接的 os.walk 内部目录反复 resolve；将 local_root 的解析提到循环外。每个实际图片路径仍 resolve、检查所属边界、存在性并读取 SHA；没有移除历史来源或旧诊断批次。

同进程对真实历史按 before→after→after→before 运行，路径集合四次均为同一1584条：

| 实现 | 第一次秒数 | 第二次秒数 |
|---|---:|---:|
| 原实现 | 97.103 | 56.742 |
| 优化后 | 31.537 | 27.378 |

首轮与隔离回归并行，负载明显波动；原始 cProfile 另测46.786秒。可确认局部目录发现开销下降，不将本测量包装为整轮搜索或模型调用提速。未知调用的 Token 未推测；没有新模型调用，也未声称降低每次模型的 Token。

## 验证与证据

私有证据目录：主目录 `.local/test-goal-independent-20261021/`，不入Git。`artifacts-before.json` / `artifacts-after.json` 独立验证前后全部旧计数字段、15张SHA与读图证据相同；4张子图按父图重裁像素一致。`history-comparison.json` 保存完整时间与集合相同断言。

- 修改前相关既有回归：73 passed（existing-tests.txt）。新增4项初次受沙箱临时 `.agents` 目录限制；正常权限后4 failed，其中普通目标1项与失败证据2项是旧实现缺陷，Goal指标项是新增契约检查。模型配置分发另1 failed，已修复。
- 首轮修复相关58 passed（green.txt）。最终受影响11个文件123项：122 passed / 1 failed（final-tests.txt）；唯一失败是新API测试错把创建契约201写成200，修正测试后该完整链路1 passed（api-check.txt）。产品源码在这两次之间未变，复用其余122项证据，不称单次全量全绿。
- 执行命令（工作目录为本修复工作树；解释器是主目录 `.venv/Scripts/python.exe -X utf8`）：`-m pytest -q -p no:cacheprovider --basetemp=<主目录>/.local/test-goal-independent-20261021/final-tests tests/test_goal_independent_audit.py tests/test_goal_photo_admission.py tests/test_collection_upgrade_counts.py tests/test_collection_stages.py tests/test_search_continue_recovery.py tests/test_search_relevance_regression.py tests/test_search_detail_timing.py tests/test_classification.py tests/test_collection_history_cache.py tests/test_collection_audit.py tests/test_collection_autonomy.py --tb=short`。单项复测为 `tests/test_goal_independent_audit.py::test_plain_search_receipt_import_and_api_agree`，独立 basetemp 为 api-check。
- 用新代码只读重算真实当前目录，仍15；统一计数新增指标没有改变任何旧字段。主库 integrity=ok；从原 Goal SQLite 基线独立逐行比较13类业务表，全部旧行保留，旧942引用与26项目均无变化，1182旧原件SHA全部复核一致；72外键错误与基线完全相同（preservation-independent.json）。初次审计脚本假设每表都有id失败，改为完整行集合对比后通过，未修改表或数据。
- 本轮真实日用浏览器：任务卡15/15→候选图库27张、合格摄影18/其中名称15→Goal成果页15图/15证据详情全部加载，刷新后标题15/15保持；学习页能力地图与个人记录读取。未点击采集/AI审核/人工选择，也未对日用执行重启。
- 已独立核对当前运行/日用HEAD/原任务分支远端为77216b498c7556df87b3371be6919ba7303916b1。main仍1c0aadfdacd9579d38b79e45dfbf6d2a8d1d55e1；主目录运行任务分支不表示已合入main。

## 验收与剩余边界

A 原冻结15张成果：PASS（证据、原件、引用、数量、可见页面）；日常重复搜图能力：PARTIAL，已确认普通路径回归且在独立分支修复。原冷启动记录只核对留存证据，本轮没有重新重启日用。

B 已修3处边界缺陷；保留两项既存全量失败及72外键孤行，不做无关清理。Goal仍需预先建立本地基线，单个角色实跑不证明新角色泛化或无需Agent准备的完整产品流程。

C 已实施3处小范围目录解析优化，实测见上；未引入缓存、依赖、跨语言重写或放松SHA。模型开销优化仅改善失败证据与配置遵循，不宣称Token下降。

D 修改范围为5个产品Python文件、1个回归文件和3个文档文件。发布仅任务分支Git-only；主库、现有图片、旧失败回执和日用进程不变。回退可在获得部署授权后对本修复提交使用普通git revert；当前尚未部署，因此日用无需回退。严禁用旧数据库覆盖新增成果。

E CONDITIONAL：本轮修复可供集成审查，尚未在日用部署或执行修改后的新一轮联网搜图/真实模型调用；严格角色身份、服装、用户审美和现场卡仍未验收。不得用回归通过将这些项目改写为PASS。Git交付状态由最终Publisher回执单独报告。
