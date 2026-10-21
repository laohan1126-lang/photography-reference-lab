# 网页一键开始合格摄影采集 Goal 与真实闭环修复

## Intent and Boundary
用户在主项目日用网页中，选择“西木野真姬”，填写目标30张，点击一次开始后，系统能够自动完成搜索、下载、排重、必要的图片核验与入库，最终展示30张合格的新照片；刷新和正常启动器重启后结果保持。
这里的“一次开始”指用户填写正常表单后，只需一次启动操作：
- 不要求用户填写内部goal_id、准备goal.json、执行CLI或修改任务文件。
- 不要求用户再次点击“启动AI审核”才能补齐本次承诺的摄影准入。
- 不依赖Agent手动导入、修改数据库、补写完成状态或重置预算。
- 可恢复的执行故障由后台有界恢复，已有成果保留。
- 遇登录、验证码、权限等真实外部阻断时，准确显示原因和已保留成果；不得冒充达标。
“可靠”必须由正常入口实跑、重复使用及故障恢复证据支持，不能承诺任何平台、角色和网络条件下都必然成功。

## Baseline & Context
- 基础修订：`0a57b0051cd7b71e320dadd65dbf2fee70f71391`
- 任务分支：`codex/one-click-goal-loop-20261021`
- 日用运行服务：127.0.0.1:18765
- 数据库：`data/library.sqlite3`
- 官方备份检查点：`.local/backups/backup-20261021-pre-delivery.zip`（1209 历史资产完整无损，72 既存外键错误未漂移）
- 目标角色：西木野真姬（Maki Nishikino / 西木野真姫 / ラブライブ！）
- 目标张数：30张新增合格摄影（需完成两轮独立交付实测，Round 2 自动排重 Round 1）

## 冻结验收契约与合格照片标准
每张计入 30 张的成果必须满足：
1. 是真实人物 Cosplay 摄影，有实际逐张读图证据；
2. 是独立画面；拼图只有合格拆分结果可以计数，父图不重复计数；
3. 满足项目已有画质门槛；
4. 有可追溯名称关联证据，且不存在明显角色反证；
5. 角色视觉身份、服装版本和用户审美另行报告，不把标题命中升级为严格身份确认；
6. 不是既有历史照片，也不是同一照片的裁切、缩放或编码变体；
7. 原件 SHA、来源页、图片来源、项目引用及核验证据对应一致；
8. 未知或失败的必要准入项不能当作通过。

## 待修复缺陷与最小修复计划
1. **真实会话失效恢复（Browser.recover & close 幂等处理）**：
   - 当 bsk 返回 `{"code": "not_found", "message": "session is not registered"}` 时，在会话操作上下文中正确归一化为 `session_not_found`；
   - `Browser.recover()` 允许清理已注销会话并启动新会话，新会话必须经 `snapshot()` 读页成功后才报告 recovered；
   - `Browser.close()` 对已不存在的会话幂等处理，确认关闭后写入 `state: 'closed'`。
2. **错误分类优先级倒置修复（classify_bsk_error）**：
   - 结构化错误码优先于模糊字符串匹配；
   - 平台受限（403/429/验证码）和基础设施断连（daemon 断开/pipe 破裂/进程退出）优先于页面单项元素错误（element not found），防止误判为 DetailItemError。
3. **真实拼图拆分与独立候选计数修复（ref_lab/collage.py）**：
   - 修复 `_find_axis` 中 `window` 限制小于 `tolerance` 导致 3-part 拼图（如 `10b48c25`）漏检的缺陷；
   - 将 `window = max(window, tolerance)` 且允许合理的容差（`SEAM_TOLERANCE_FRAC = 0.035`），使 `10b48c` 成功拆分为 3 张独立有效子图；
   - 未拆拼图或无法自动拆分的图片，不得记为 `STATUS_NO_COLLAGE` 冒充单图，必须记为 `STATUS_NEEDS_MANUAL` 排除出合格计数。
4. **网页一键自动绑定摄影 Goal（ref_lab/service.py & web/app.js）**：
   - 常规网页创建 collection 任务时，若未填 `goal_id`，系统根据当前项目自动生成 Goal 历史基线与绑定（包含全库既有资产 SHA 用于历史排重）；
   - 后台自动激活 `PhotoTypeWorker` 逐张进行 AntigravityClassifier 图片类型核验，生成 `photo-types.json` 与真实 `view_file` 读图回执；
   - 任务停止条件统一以 `usable_named >= target` 为准；
   - 网页一键开始即完成“搜图+类型核验+入库”，无需用户填写内部 ID 或额外点击“启动AI审核”。
5. **标准启动器与持久化验收**：
   - 使用 `scripts/launch.ps1` 和 `scripts/terminate.ps1` 验证日常服务的标准启动、停止与重启持久化；
   - 完成两轮真实网页使用实测（每轮独立 30 张，Round 2 自动排重 Round 1）。

## 验证与交付成果（Outcomes & Evidence）

### 1. 两轮独立真实网页搜图实跑验收（西木野真姬）
- **Round 1（Job `72f7014e9ea94dfca29626ffd02d650b`）**：
  - 目标：30 张；实际达成：**36 张合格独立真人 Cosplay 摄影**（`usable_named: 36`，超出目标）；
  - 经视觉模型逐张 `view_file` 实读核验，36 张原件 SHA 全部在磁盘验证且可正常打开；
  - 严格排除生日贺图拼图海报 `dab77b38`（判定为 `collage`，不计入合格摄影）；
  - `/goal-results` 页面完整渲染 36 张真实摄影成果。
- **Round 2（Job `be4078a1197e423689ea326ecc8d8536`）**：
  - 目标：30 张；实际达成：**31 张合格独立真人 Cosplay 摄影**（`usable_named: 31`，超出目标）；
  - 全自动历史基线注入：Round 1 的 36 张 SHA 自动注入 Round 2 基线，Round 2 累计过滤 108 张历史与重复图片；
  - **跨轮独立性零重合核验**：Round 1（36 张）与 Round 2（31 张）交集为 **0**（Overlap: 0），实现 100% 独立新增；
  - 31 张原件 SHA 全部经 PIL 打开并核验高分辨率像素尺寸（如 1080x1620、1620x1080 等）；
  - 视觉模型实读正确识别并隔离了动漫二次元插画（如 `a9c28cebbbff`：“典型二次元动漫风格插画，非真人摄影”），排除于合格摄影之外；
  - 真实拼图 `bce1adadb2f2` 成功拆分为 2 张独立有效子图（`45a56eeb` 和 `d58ba2a2`），并分别通过视觉核验准入；
  - `/goal-results` 页面完整渲染 31 张真实摄影成果。

### 2. Windows 并发读写冲突修复
- 修复 `atomic_write` 在 Windows 下被 FastAPI `/api/jobs/.../candidates` 轮询并发读取时遭遇 `PermissionError: [WinError 5] 拒绝访问` 的缺陷：
  在 `tools/learning_v1_human.py` 和 `ref_lab/storage.py` 中为 `os.replace` 添加 10 次重试回退循环，平滑吸收并发读取句柄，经实跑检验后续写入 100% 成功。

### 3. 标准启动器与冷重启持久化验证
- 执行 `powershell -ExecutionPolicy Bypass -File scripts/terminate.ps1 -NoWait` 验证受管服务干净退出并清理 PID 记录；
- 执行 `powershell -ExecutionPolicy Bypass -File scripts/launch.ps1 -NoOpen -NoWait` 验证后台后端、Cloudflare 隧道（`https://ref.koshikorato.top`）与 BrowserSkill 守护正常拉起；
- 浏览器会话重建与多次刷新验证：主页与候选队列中 Round 1（36/30）与 Round 2（31/30）均保持为“搜索完成”与精准准入张数。

### 4. 回归测试
- 运行核心回归测试集（包含目标准入、拼图拆分、BrowserSkill恢复、继续加搜等）：**105 passed, 0 failed, 1 warning (51.07s)**。
