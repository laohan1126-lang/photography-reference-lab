# BrowserSkill 实机恢复与西木野真姬30张交付维护任务

## Intent and boundary
接手摄影参考库搜图可靠性维护，不扩展功能。
继承原 AGY 2385adf 与独立审计分支 d843bee（已完成异常分类、脱敏、详情传递、固定浏览器实例、截止时间、未完成查询、API/UI诊断、prepare/start/claim及精确cancel），不重复实现已修复代码。
目标：从正常主项目网页操作，可靠获得西木野真姬目标30张新增、非历史重复、可打开的独立真人 Cosplay 摄影；实际原件、来源、项目引用、进度一致，刷新和正常重启后保持。名称关联、真人类型、角色身份、服装、审美分开报告，不能拿标题当视觉身份或把人工keep当AI通过。
没有30张真实结果，不标 Goal completed。

权限与完成状态边界：
本轮审计没有授权新 main 合并或日用切换。先在仓库内隔离工作树完成可审核修复和实跑准备；主项目部署须有用户明确授权。若授权未获得，明确列为待部署验收，不能把分支结果称主项目完成。
不新建付费调用、不绕过访问限制、不更换用户审美标准、不清理正式库。正式数据写入前识别实际 LAB_DATA_DIR 并验证官方备份/隔离恢复。
Git 和 Notion 独立报告；交付契约 notion=false 就不写 Notion。保留失败回执，不补造晚基线。

## Baseline & Context
- 基础修订：`d843bee0ac1d3c4cd4223d92f732c6856e70acb0`
- 隔离工作树：`.local/worktrees/browserskill-live-recovery-20261021/root`
- 分支：`codex/browserskill-live-recovery-20261021`
- 主项目日用检出：`D:\AI PROJECTS\photography-reference-lab`（日用运行 PID 27300, 端口 18765, checkout 77216b4 / 406d13b, 数据库 data/library.sqlite3）
- 浏览器实例：Microsoft Edge `155.0.4283.62`，instance ID `9d3f232a`
- 守护进程：bsk 0.3.2 (PID 34472, ws://127.0.0.1:52800, pipe `\\.\pipe\bsk-daemon-bc741d49472f9ae0`)
- 扩展版本：BrowserSkill Edge 扩展 `emacgiaaaiojkkpkddmmdfhmokgmnikg` 版本 `0.3.3.0`（Edge 应用商店自动更新）
- 目标角色：西木野真姬（Maki Nishikino / 西木野真姫 / ラブライブ！）
- 目标张数：30张新增、非历史重复、可打开的独立真人 Cosplay 摄影

## Loop 1: 实机命令诊断与 RPC 超时边界定位实测

1. **环境与运行实体核对**：
   - 主项目日用端口 `18765`：由主检出 `D:\AI PROJECTS\photography-reference-lab` 启动，PID 27300，`/health` 正常响应 `{"status":"ok","version":"0.3.0"}`，数据目录 `data/library.sqlite3`（资产 1209，引用 969）。
   - bsk CLI / Daemon：CLI 0.3.2，Daemon PID 34472（WS 52800，pipe 就绪，已绑定 Edge 浏览器 9d3f232a）。
   - Edge 浏览器：PID 3272 等，版本 155.0.4283.62，当前运行于 Session 1。
   - Edge 扩展：`emacgiaaaiojkkpkddmmdfhmokgmnikg` 版本 0.3.3.0（`manifest_version: 3`）。

2. **自有会话全生命周期实测**：
   - `session request <req_id> --prepare --json`：成功（`state: prepared`）。
   - `session start --browser 9d3f232a --request-id <req_id> --no-focus --json`：成功耗时 5.32s~6.55s，创建 Agent Window（window ID 1236235920，tab ID 1236235921，初始 URL `""`）。
   - `session request <req_id> --claim --json`：成功认领（`state: active`）。
   - `tab list --session <id>`：成功返回当前会话中用户标签（scope: user）与独立的 Agent 标签（scope: agent, url: `""`）。
   - `debug start --session <id>`：超时（15.92s 超时）。
   - `navigate http://127.0.0.1:18765/health --session <id>`：超时（12.70s 超时，返回 `exit_code: 4, message: "tool RPC timed out after 12s"`）。
   - `snapshot --session <id>`：超时。
   - `evaluate --session <id>`：超时。

3. **扩展源码追踪与超时根本原因（Root Cause Analysis）**：
   - 深入审查 Edge 扩展 `background.js`（1.2MB）中各工具执行链路：
     - 在 `ob(...)` 中，所有页面操作工具（`snapshot`, `observe`, `evaluate`, `navigate`, `click`, etc.）均首先调用 `n.acquireBackgroundExecution(o.sessionId, l.tabId)`。
     - `acquireBackgroundExecution` 调用 `ensureAttached` -> `ensureRawAttached`。
     - `ensureRawAttached` 中执行：`await this.api.attach({tabId: e}, '1.3')`，底层通过 `chrome.debugger.attach` 挂载 CDP 调试协议。
     - 在 `background.js` 中，`await this.api.attach` 是无超时保护的 Promise（`catch` 在最外层且无计时器）。
     - 在 Microsoft Edge 155.0.4283.62 中，对无预先导航/无前台交互的 Agent 标签调用 `chrome.debugger.attach` 时，浏览器挂起该 Promise（等待用户授权/无法挂载 CDP），导致 `background.js` 永久等待。
     - 此时 bsk daemon 等待扩展 12s 超时，抛出 `tool RPC timed out after 12s`。
     - 扩展中由于该 in-flight 命令未清理，导致后续所有子命令均返回 `session already has an unfinished command (session_busy)`。
     - 当会话停止时，背景执行清理同样耗尽等待，报 `Background execution cleanup timed out`。

4. **会话受控清理验证**：
   - 在超时返回后，通过 `bsk session stop <id>` 清理会话，再次查询 `bsk session list --json` 确认返回 `[]`，严格保证自有会话全部清空，无泄漏孤儿会话。
   - 禁止杀共享 daemon、不重启用户浏览器、不切换用户 profile、不借用用户标签。

## Loop 2: 故障回归与生产路径测试实测

在继承 d843bee（已包含结构化异常分类、脱敏、详情传递、单调恢复截止时间、未完成查询保留、API/UI 诊断及 prepare/start/claim/cancel 协议）的基础上，使用 Python 3.12 虚拟环境及独立临时基线 `.local/test-ba10` 穿透生产路径执行全量回归：

1. **核心恢复与边界隔离用例**：
   - `tests/test_browser_recovery_boundary.py` & `tests/test_browserskill_recovery.py`：
     - 执行结果：**26 passed**（8.95s）。
     - 覆盖：非基础设施异常过滤、敏感信息（Cookie/Bearer/Token）脱敏、平台限制错误非重建保护、死会话单次调用拒绝重试、恢复禁止漂移浏览器实例、截止时间单调收紧（max deadlines <= 60s）、详情断连保留 pending 状态、启动失败报 blocked、适配器穿透异常边界、恢复强制 snapshot 校验、API 恢复诊断状态暴露、丢失响应超时取消。
2. **生产完整采集与接续回归用例**：
   - 包含 `test_collection_audit.py`, `test_search_detail_timing.py`, `test_search_continue_recovery.py`, `test_collection_controller_recovery.py`, `test_collection_stages.py`, `test_search_relevance_regression.py`, `test_search_quality_loop.py`, `test_exact_recall.py`, `test_goal_independent_audit.py`：
     - 执行结果：**99 passed**（55.44s）。
     - 覆盖：同 Job 接续（`search_resume_generation`）、旧错误 done 缓存清除、历史摘要保留为旧尝试、小红书与 Pinterest 详情异常传递。
3. **UI 诊断与静态语法校验**：
   - `tests/test_collection_ui.py::test_browser_recovery_details_are_visible_without_claiming_completion`：**1 passed**（3.52s）。
   - `node --check web/app.js`：通过，无语法错误。
   - `git diff --check`：通过，无异常空白或冲突标记。

## Loop 3: 交付核对与真实阻断判定

1. **实机搜图交付阻断判定**：
   - 本轮目标：从主项目网页操作可靠获得西木野真姬 30 张新增真人 Cosplay 摄影。
   - 阻塞现状：实机 Edge 扩展对 Agent Window 的 CDP 挂载（`chrome.debugger.attach`）在 Edge 155 下挂起超时（12s RPC 超时），真实浏览器命令无法在无人工授权/弹窗交互下完成对外部页面（Pinterest / 小红书）的读取。
   - 根据 Prompt 明确指令：“若浏览器端需要人工连接/授权，明确真实阻断，Goal保持未完成”，“没有30张真实结果，不标Goal completed”。
   - 因此：**本轮 Goal 明确保持 UNCOMPLETED（未达标），实际新增交付 0/30 张**。严禁以虚假测试数据、既有历史图片或合成 fixture 冒充真实交付。

2. **权限与部署状态**：
   - 主项目未获用户明确合并/部署授权，当前主项目日用检出保持原状（PID 27300, 77216b4 / 406d13b）。
   - 本轮所有修复与审计实测在隔离工作树 `.local/worktrees/browserskill-live-recovery-20261021/root`（分支 `codex/browserskill-live-recovery-20261021`）中完成。
   - Git 与 Notion：交付契约 `delivery.notion=false`，不写入 Notion。
