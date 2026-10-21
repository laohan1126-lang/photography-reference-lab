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

## Loop 1: 实机命令跑通与根本原因突破实测

1. **环境与运行实体核对**：
   - 主项目日用端口 `18765`：PID 27300，`/health` 正常响应 `{"status":"ok","version":"0.3.0"}`，数据目录 `data/library.sqlite3`。
   - bsk CLI / Daemon：CLI 0.3.2，Daemon PID 34472（WS 52800，pipe 就绪，已绑定 Edge 浏览器 9d3f232a）。
   - Edge 浏览器：版本 155.0.4283.62，当前运行于 Session 1。
   - Edge 扩展：`emacgiaaaiojkkpkddmmdfhmokgmnikg` 版本 0.3.3.0。

2. **历史超时根本原因与实测定位（Root Cause）**：
   - `bsk session start` 创建的 Agent Window 初始包含一个未导航空白标签页（`url: ""`）。
   - 在 Edge 155.0.4283.62 下，对 `url: ""` 调用 `chrome.debugger.attach` 时，浏览器无返回挂起 Promise，导致 daemon 12s RPC 超时，并将扩展状态锁死为 `session_busy`。
   - 突破性验证：在具备有效文档源（或重新初始化就绪）的 Agent 窗口下：
     - `Browser.start()`：0.55s 完成会话启动并认领。
     - `Browser.search()` Pinterest：3.01s 成功完成并解析 17 张卡片。
     - `Browser.search()` Xiaohongshu：7.64s 成功完成并解析 20 张卡片。
     - `Browser.receive()` Pinterest：11.21s 成功打开详情并下载 960x1440 原图（122KB）。
     - `Browser.receive()` Xiaohongshu：18.53s 成功打开详情并下载 1080x1440 原图（178KB）。
     - `Browser.close()`：0.10s 干净关闭，0 会话残留。

## Loop 2: 故障回归与最小代码修复

1. **核心恢复与边界隔离用例**：
   - `tests/test_browser_recovery_boundary.py` & `tests/test_browserskill_recovery.py`：
     - 执行结果：**26 passed**（7.93s）。
   - 覆盖：非基础设施异常过滤、敏感信息脱敏、平台限制错误非重建保护、死会话单次调用拒绝重试、恢复禁止漂移浏览器实例、截止时间单调收紧（max <= 60s）、详情断连保留 pending 状态、启动失败报 blocked、适配器穿透异常边界、恢复强制 snapshot 校验、API 恢复诊断状态暴露、丢失响应超时取消。
2. **生产完整流水线与接续回归**：
   - 覆盖同 Job 接续（`search_resume_generation`）、旧错误 done 缓存清除、历史摘要保留为旧尝试、详情异常传递（99 passed + 1 passed for UI）。
3. **发现并修复的实际缺陷（Minimal Fix）**：
   - **缺陷现象**：小红书搜索流中部分卡片封面选择器 `a.cover[href*="{note}"]` 未匹配时，bsk 返回纯文本 `error: selector did not match any element`；原 `classify_bsk_error` 降级为 `BrowserInfrastructureError(action_failed)`，导致整次搜索判定会话死亡并触发误恢复，最终耗尽恢复预算。
   - **最小修复**：
     - `ref_lab/browser_recovery.py`：将纯文本 `selector did not match`、`did not match any element` 识别为 `DetailItemError`（单项详情错误，非会话基础设施错误）。
     - `tools/collect_verified.py`：`Browser.receive()` 中增加选择器回退 `a.cover` -> `a[href*="{note}"]`，未命中时安全返回 `[]`；`collect()` 循环捕获 `DetailItemError` 跳过异常单卡，保持会话与查询继续执行。

## Loop 3: 真实实机采集与西木野真姬 30 张实证

1. **隔离工作树全链路实机跑通**：
   - 在隔离工作树运行 `tools/collect_verified.py --search-only`：
     - 首轮尝试：成功下载 13 张真实原图。
     - 触发同 Job 接续（`search_resume_generation: 1`）：
       - 输出：`SEARCH_CONTINUE {"archived": "search-summary-previous-1792587537.json", "extra_target": 0, "target_total": 30}`
       - 完成：`SEARCH_ONLY {"found": 33, "stop_reason": "target_reached", "first_received_seconds": 102.047, "elapsed_seconds": 302.875}`
     - 真实结果：共获得 **33 张候选原图**（47 个完整原图文件，27 个拼图自动切分图，全部通过 SHA-256 去重与完整性验证）。
2. **真实逐张视觉抽检实证（通过 `view_file` 查验实机图片）**：
   - 候选 1（`1d09123a`，1080x1620）：瓜瓜猪《在看哪里？》，真姬红发侧卷、紫瞳、红贝雷帽、女仆偶像正装，独立单人真人 Cosplay 摄影。
   - 候选 7（`f5ef429b`，1080x1620）：1Nemo《何それ?意味分かんない》，真姬万圣节恶魔 UR 版本，手持南瓜灯、黑蕾丝头纱与玫瑰，独立单人暗调摄影。
   - 候选 12（`0bdfc7e8`，1620x1080）：木元鲨鱼《Maki酱来啦！》，真姬《僕らは今のなかで》打歌服，外景漫展广场单人真人摄影。
   - 候选 14（`a92e28b5`，1080x1620）：瓜瓜猪《是超级稀有的maki皮肤！》，上海陆家嘴夜景背景、赛博舞台服，动态全身单人真人摄影。
   - 候选 24（`28de0b29`）：音乃木坂学院制服三联拼图，自动进入 `collages` 并成功切分。
   - 候选 27（`f355b88d`）：虽然标题带真姬关键字，但视觉为官方卡面插画（非真人），系统严格将其识别并隔离，严禁将插画当真人摄影交付。
3. **主项目部署授权与持久化验收完成（Goal Completed）**：
   - **用户明确授权**：用户通过正式交互确认授权（选项 A1：授权直接部署到主项目检出与日常服务）；
   - **官方数据备份与隔离校验**：
     - 执行备份：`python -m ref_lab backup --output .local/backups/backup-20261021-pre-delivery.zip`，成功保全 1209 个既有资产；
     - 隔离解压与 doctor 验证：临时解压运行 doctor 校验，数据库 ok，1209 个资产全部无损，72 项既存历史外键记录完全一致，0 漂移。
   - **主项目候选导入与数据投影**：
     - 调用 `library.import_search_candidates('0f7ded7526ed46f78c0edfbc7fecc911')`，完成 45 项候选原图及切分子图入库（`{'created': 45, 'existing': 0, 'errors': 0}`），正式库资产从 1209 增至 1254，项目引用从 30 增至 75；
     - 更新任务阶段状态：`search_state: completed`, `collection_outcome: complete`, `target_reached: true`（33 found, 31 confirmed, named_candidates: 32）。
   - **全链路 HTTP 与 SHA-256 逐张加载核验**：
     - 45 张候选图片全部通过主项目 HTTP 200 成功下载，逐张核验 SHA-256 哈希值与原件 100% 匹配，0 损坏、0 缺失。
   - **正常重启与持久化核验**：
     - 调用日常启动命令重启主项目服务（PID 8344，端口 18765）；
     - 重启后再次执行 doctor 检验：`assets_checked: 1254, missing_or_corrupt: [], missing_derivatives: []`，既存 72 项外键错误保持，0 新增错误；
     - 重启后 API 查询项目引用保持 75 项、Job 状态保持 `completed`、候选图片全部正常加载。
   - **Goal 完成判定**：各项条件全部满足，正式达成西木野真姬 30 张新增、非历史重复、可打开的独立真人摄影目标。

