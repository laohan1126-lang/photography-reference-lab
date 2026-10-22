# 一键两轮采集审计修复与重新验收（2026-10-22）

状态：IN PROGRESS；原 Goal 未通过。不得把工程修复或旧36/31成果改称一键验收通过。

## 编辑前检查点

- 日用目录：`D:\AI PROJECTS\photography-reference-lab`；分支 `codex/one-click-goal-loop-20261021`，HEAD `0ce25875989eff8aaee2e045b39a7f2e159d8fc8`。
- 日用312个已跟踪差异逐文件与HEAD比较：全部仅CRLF/LF差异，未覆盖/暂存这些文件。
- 修复工作树：`.local/worktrees/one-click-audit-20261022/root`，分支 `codex/one-click-audit-20261022`；同HEAD，开始时干净。
- 正式Publisher基线：本会话 `01a16007-a3c1-7262-9664-fe2329d1449a`，真实turn `01a16008-3a4d-77e0-a386-dc23338400ee`；首次实现编辑前已建立真实基线并声明契约，fingerprint `758fefcf1225941f6c83d895e1ad02569c7e3bc8db464039f9abbac06470fbd6`。
- Publisher状态在日用`.local/one-click-audit-20261022/publisher/`。首次跨工作树host绑定失败（HOST_WORKSPACE_MISMATCH），bind-existing不适用（TERMINAL_TASK_EVIDENCE_MISSING）；在实际工具执行工作树重用原始基线start成功，没有重造基线或借用身份。
- Windows PID15924→46388 正常服务存在，监听127.0.0.1:18765，health=ok；运行记录仍标旧修订0a57b005。
- 旧Job b8070657…标running，owner45448已不存在；只读核验，不手工修状态。当前未发现采集子进程；受控停止前需再次检查。
- WSL普通Windows调用失败 `UtilBindVsockAnyPort socket failed 1`，授权单次提权只读检查成功；此为宿主权限边界，不能据此归因为产品启动失败。
- 旧探针results.json确认 D/E/F/G/C反例；旧会话失效恢复证据仍保留，不当本轮重新实测。
- 尚未写正式用户数据，尚未执行本轮官方备份/隔离恢复；任何正式写入前必须完成。

## 实现范围与影响

- A：Browser.command/recover、采集控制器、阶段/外层预算、PhotoTypeWorker及界面预算；防止时间耗尽误恢复。
- B：start/stop脚本及runtime-common的进程所有权、路径与冻结版本检查；先分离宿主生命周期与产品缺陷。
- C：自动基线、历史发现/缓存、准入计数、原图/子图调用方；不可在索引未知时放行，不删除历史或误拒真实连拍。
- D/E：create_job、extend_search、API、任务包/Goal/数据库一致性；拒绝请求零副作用，文件失败须上报。
- F/G/H：逐次模型账本、完整回执复用、关闭重试、拼图版本与显式重算/快照；保留旧图与用户选择。
- 先合成失败回归，再最小修复，再相关回归。模型视觉准确性、真实网页/启动器证据单列。
- 不新增功能或依赖、不改审美、不降低准入、不合main、不部署公网、不提交私有资产。

## 原始用户 Goal 与完整冻结验收标准（原文保留）

1. Goal
在摄影参考库主项目中，用户通过正常网页选择“西木野真姬”、填写目标 30 张，点击一次开始，系统自动完成搜索、下载、历史排重、拼图处理、必要的逐张视觉核验、入库和成果展示。
完成必须同时满足：
- 最终同一代码版本下，完成两轮独立实跑。
- 每轮单独获得至少 30 张合格、不重复的新照片。
- 第二轮自动排除第一轮及所有既有历史成果。
- 两轮都不依赖人工继续、临时增加预算、CLI 补跑、手动导入、修改 JSON/数据库或补写完成状态。
- 通过项目正常启动器停止、冷启动和重启验证，成果、证据、引用及计数保持。
- 修复本轮审计确认的问题，纠正上一轮不符合证据的完成报告。
完成子任务、测试通过、提交成功、候选数量达到 30，都不代表 Goal 完成。
2. Current State：已知真实状态
项目唯一日用目录：
D:\AI PROJECTS\photography-reference-lab
上一轮独立审计时：
分支：codex/one-click-goal-loop-20261021
HEAD及远端：0ce25875989eff8aaee2e045b39a7f2e159d8fc8
这些是审计快照。开始时自行核对当前分支、HEAD、未提交修改、服务进程、实际数据目录和相关任务记录，不覆盖其他人的工作。
已实现并有证据支持：
- 普通网页创建任务会自动绑定 Goal。
- 已接入 PhotoTypeWorker、逐张原生 view_file 回执及合格数量计算。
- 两轮最终保存的准入数量为 36、31。
- 67 张文件、正式库原件 SHA、项目引用及模型原始流均通过独立技术核验。
- 两个成果页实际解码 36/36、31/31。
- 已注销会话的真实恢复及正常关闭通过独立测试。
- 105 项相关回归通过，但本次新增逻辑缺少针对性的新增回归。
原始 Goal 仍未通过：
事实	Round 1	Round 2
Job	72f7014e9ea94dfca29626ffd02d650b	be4078a1197e423689ea326ecc8d8536
首次停止时合格数	29	9
首次问题	browser_unavailable，日志含负剩余时间超时	文件替换 PermissionError，采集退出
人工干预	点击继续补足	点击继续补足
追加预算	900 秒	900 秒
最终累计预算	2700 秒	2700 秒
最终准入数	36	31


旧报告却宣称两轮零人工介入、单次预算 900 秒、一键完成，必须纠正。
标准启动器验收也不成立：执行者最终手动启动服务、补写 server.json，再检查启动器能否识别已运行进程。这不能证明冷启动成功。
相关证据：
docs/tasks/2026-10-21-one-click-goal-loop.md
docs/tasks/CURRENT.md
.local/audit-one-click-20261022/probes/results.json
.local/audit-one-click-20261022/browser-recovery/probe-result.json
.local/audit-one-click-20261022/browser-debug.json
.local/audit-one-click-20261022/asset-verification.json
.local/collection-runs/<上述Job>/current/
原始执行记录：
C:\Users\Dell\.codex\attachments\6b61b187-608f-48d6-9c78-c7aafc4e6673\已粘贴的文本.txt
3. Scope：必须修复的问题
先检查所有相关调用方，再选择最小完整修复。优先复用现有 Goal、历史索引、快照、计数与进程管理机制，不新增平行实现。
A. 真正完成一键流程，并正确区分超时原因
涉及：
tools/collect_verified.py
ref_lab/agent_collection.py
ref_lab/collection_stages.py
ref_lab/photo_types.py
已确认：Browser.command() 将任务剩余时间不足转为浏览器基础设施超时，最终可能显示 browser_unavailable。
要求：
- 区分总预算耗尽、单命令超时、浏览器断连、模型不可用和平台限制。
- 总预算耗尽不得触发无意义的浏览器恢复或平台轮换。
- 下载、裁切、核验、收尾和入库的时间及状态必须协调，不能留下需要用户再点一次才能完成的正常流程缺口。
- 可恢复故障在同一 Job、同一冻结预算内有界处理。
- 根据实测核验耗时确定合理的正常默认预算，并在正式验收前冻结、在界面清楚展示。
- 不允许针对某次验收临时使用特别高的隐藏预算；不得无限提高时间或调用上限掩盖故障。
B. 修复正常启动器链路
检查：
start.bat
stop.bat
scripts/launch.ps1
scripts/terminate.ps1
scripts/runtime-common.ps1
先定位之前启动失败发生在哪里，区分产品启动逻辑与执行宿主进程生命周期问题。
要求：
- 正常启动器真正创建并管理服务。
- 服务和采集适配器来自同一 checkout、同一冻结代码版本。
- 运行记录由正常启动流程生成。
- 禁止手动运行 serve、手写 PID 或 server.json，再将其包装成启动器通过。
- 本 Goal 范围内可进行必要的受控本地启动与重启；执行前完成数据保护，并确认没有其他活动任务。
- 不因此扩大为 main 合并、公共发布或基础设施改造。
C. 补齐历史排重与裁切变体检查
涉及：
ref_lab/service.py::_create_auto_goal
tools/collect_verified.py::_history_for_search
ref_lab/collection_history.py::ImageHistory
ref_lab/collection_counts.py
已确认：
- 自动基线只有 SHA，没有冻结图片指纹。
- 历史索引未就绪时，同照片重新编码可能漏过。
- 当前匹配跳过长宽比相差超过 3% 的图片，裁切变体可以漏过。
- SHA 交集为零只能证明字节不同，不能证明照片不同。
要求：
- 合格准入前，确保必要历史排重信息已经可靠就绪；允许先下载展示，但未完成排重不得计为新成果。
- 复用已有历史发现范围，包含正式库、历史批次、失败或诊断批次及有效子图。
- 同一照片的缩放、重编码、合理裁切变体不得重复计数。
- 用反例保护不同姿势、不同画面的真实连拍，不能简单放宽阈值大量误拒。
- 无法确认的重复关系保持待核验，不凑数量。
- 基线绑定与缓存损坏必须可检测，不静默降低排重标准。
D. 修复 Goal 编号冲突
位置：
ref_lab/service.py::_create_auto_goal
当前“项目前缀＋整数秒”可使同秒创建的两个任务覆盖同一个 Goal。
要求：
- 使用项目已有唯一 ID 机制。
- 已存在的目标和历史基线不得被另一任务覆盖。
- 补同项目同秒创建、不同目标数量的回归。
E. 修复加搜请求的数据一致性
位置：
ref_lab/service.py::extend_search
已复现：40 张任务追加 70 张，返回 422 后数据库仍为 40，goal.json 已变成 110。
要求：
- 所有输入、状态及上限校验先完成。
- 被拒绝的请求不得改变任何目标文件或数据库状态。
- 文件更新失败不得吞掉异常后继续报告成功。
- 保持数据库、Goal 文件与运行任务包一致。
- 保留用户主动加搜功能，但正式一键验收不得使用它补数。
F. 修复模型重试记账和预算
位置：
ref_lab/photo_types.py::PhotoTypeWorker._process
已复现：上限为 1 时实际调用两次，账本只记一次，第一次失败消耗被最后一次覆盖。
要求：
- 每次真实模型尝试独立记录，执行前检查调用预算。
- 保存每次原始回执、结果、耗时、已知用量和未知用量。
- 重试不得覆盖第一次失败证据。
- 明确区分图片数、尝试次数和成功次数。
- 已有完整有效回执应复用，不能无故重复调用模型。
G. 修复关闭失败后的会话身份丢失
位置：
tools/collect_verified.py::Browser.close
当前停止超时后仍清空 session；再次关闭可能不发送停止命令就写出 closed。
要求：
- 仅确认停止成功或会话确实不存在后清空身份。
- 失败时保留任务拥有的会话 ID 和“清理未确认”状态。
- 后续清理必须针对原有会话，不影响用户标签或其他任务。
- 保留已经通过的失效会话恢复行为。
H. 让拼图算法升级作用于旧记录
位置：
ref_lab/collage.py
真实旧图 10b48c25… 新算法已能识别三格拼图，但旧 no_collage 记录仍因版本相同被复用。
要求：
- 正确更新算法版本。
- 使用已有快照、完整性校验和显式重算流程。
- 保留原件、旧记录、旧子图及人工决定。
- 原件和子图身份处理遵守已有迁移规则，不能把自己的旧子图误判成历史重复。
- 未可靠确认的拼图不得冒充独立单图计入目标。
4. 不应触碰的范围
- 不扩展新功能、美化界面或进行无证据的大规模重构。
- 不改用户审美，不把名称命中升级为严格角色或服装身份确认。
- 不降低现有画质、实际看图、来源、原件完整性和重复排除门槛。
- 不删除旧成果、失败记录、模型流、人工选择或备份。
- 不绕过登录、验证码、访问限制，不导出浏览器凭据或猜测高清 URL。
- 不增加未经授权的付费服务。
- 不自动合并 main、强推或公共发布。
- 私有图片、数据库、浏览器配置及凭据不得提交 Git。
- 所有新验证目录、备份和工作树位于项目 .local/ 下。
5. Execution：持续工作循环
阶段一：恢复状态与建立可复现证据
1. 阅读适用的 AGENTS.md、README、架构、采集协议和相关任务记录。
2. 核对实际运行进程、数据目录、代码版本和未提交修改。
3. 保留原始 Goal 与本提示词验收标准，建立本轮任务记录。
4. 按执行端适用的正式交付协议，在首次编辑前建立真实基线。不得借用其他会话身份或事后补造编辑前基线。
5. 对上述缺陷建立最小失败回归，区分合成测试、真实应用证据和视觉判断。
6. 在任何正式用户数据写入前，执行官方备份并验证隔离恢复。
阶段二：修复、测量与针对性回归
循环执行：
复现 → 定位共享根因 → 最小完整修复 → 相关调用方回归 → 检查真实失败路径
重复失败且没有新信息时停止原样重试，重新分析根因。不得靠叠加特殊例外或削弱测试获得通过。
代码修改后先完成适用的本地验证，再进入正式实跑。测量模型等待、下载、历史索引和收尾耗时，避免凭感觉调整预算。
阶段三：冻结正式验收配置
开始两轮正式验收前，保存：
- 最终提交、工作树状态和实现文件摘要。
- 服务与适配器路径、运行版本。
- 项目、角色、可信别名、来源、目标 30。
- 正常默认时间预算、模型调用预算、模型配置和并发。
- 画质、照片准入、排重规则与历史基线。
- 两轮验收安排及有限的总实跑资源预算。
两轮使用相同最终实现和配置。修复阶段的测试批次不能冒充正式验收。
阶段四：两轮正常网页实跑
每轮均由正常网页表单创建任务并点击一次开始。
- 不填写内部 Goal ID，不准备任务文件。
- 点击前开始记录时间和正常应用事件。
- 后续只观察，不点击继续、加搜或额外审核来补足。
- 不直接调用采集 CLI、导入函数或状态更新 API。
- 第二轮必须以包含第一轮成果及全部既有历史的基线启动。
- 两轮不能合并数量，每轮均须独立达标。
若某轮失败：
- 保留该轮 Job、成果、预算、日志及失败原因。
- 不人工接力后把它改称一键通过。
- 定位并修复后，在最终冻结版本重新取得完整两轮通过证据。
- 失败与诊断成果继续进入后续历史排重。
- 不允许无分析地反复新建任务碰运气；总授权资源预算耗尽时如实报告未完成。
阶段五：正常启动器与持久化验证
完成成果后，使用正常 stop.bat / start.bat 或其正式脚本链路进行验证。
检查停止确实完成、冷启动确实由启动器执行，随后：
- 两轮合格数量仍各自不少于 30。
- 所有成果原件 SHA、来源、项目引用和核验证据保持。
- 浏览器实际解码所有计入成果的图片。
- 状态与停止原因正确，没有自动新增采集或重复导入。
- 服务和采集适配器仍来自冻结版本。
- 不要求用户或 Agent 手工修复运行记录。
6. Acceptance Criteria
每张计入目标的照片必须满足：
1. 真人 Cosplay 摄影，有绑定该图片的原生实际读图证据；普通人像不能仅凭标题当作 Cosplay 凑数。
2. 独立画面；拼图仅合格子图可计数，父图不能重复计入。
3. 满足现有画质要求。
4. 有可追溯名称关联，且没有已确认的明显反证；不宣称未经验证的严格角色身份。
5. 不属于历史照片及其缩放、重编码、裁切变体，也不与本轮其他成果重复。
6. 原件 SHA、来源页、图片来源、项目引用和核验证据一致。
7. 必要准入项未知、失败或证据损坏时，不计为通过。
8. 不覆盖用户已有人工选择。
整体通过还必须满足：
- 两轮均为正常网页单次启动，各自自动完成不少于 30 张。
- 无人工继续、临时加预算、手动补状态或事后改口径。
- 所有可恢复故障处理均在冻结预算内完成。
- 正常启动器冷启动及重启后持久化通过。
- 八项审计缺陷有针对性回归与对应证据。
- 修复没有破坏已有人工筛选、主动加搜、图片保留及旧成果读取。
- 最终验收所用代码与交付代码一致；之后若修改相关实现，重验受影响路径，不能沿用失效证据。
7. Evidence 与报告纠正
完成时提交可复核的：
- 两轮 Job ID、冻结输入、历史基线及代码版本。
- 每轮从点击开始至结束的完整时间线，包含所有中断与后台恢复。
- 首个原件、首张合格照片、第 30 张合格照片的时间；区分落盘、入账和浏览器实际可见。
- 全部合格成果清单：SHA、文件、来源、引用、类型证据、画质与排重依据。
- 两轮内部、跨轮及对历史库的重复检查结果；不能只给 SHA 交集。
- 全部模型尝试次数、耗时、已知 Token、未知用量和失败回执。
- 正常启动器停止、冷启动、重启及运行版本证据。
- 测试命令、实际结果、失败与未验证范围。
- 修改文件、影响范围、必要回退步骤；回退不得覆盖本轮新增用户数据。
- Git、运行部署与 Notion 各自的实际状态，不用一个 SUCCESS 混在一起。
纠正旧报告时：
- 保留旧报告与原失败证据，追加明确更正并标注旧完成结论失效。
- 承认旧两轮使用了人工继续及追加预算。
- 纠正启动器冷启动声明。
- 将“SHA 零交集”与“照片内容完全不重复”分开。
- 更正遗漏的调用次数、消耗和计时。
- 不把本轮修复后的结果倒写成上一轮已经通过。
8. Stop Conditions
只有以下情况可以停止：
1. **PASS：**上述全部验收标准通过，证据完整。
2. **BLOCKED：**存在已核实的登录、验证码、权限、外部服务或其他不可自行解决的阻断。
3. **风险或资源边界：**继续执行会危及用户数据、影响不属于本任务的活动工作，或超出冻结资源预算。
阻断时报告：已保存成果、缺口、准确原因、尝试证据及最小必要人工动作。不得降低目标或把部分完成标为 Goal 完成。
上下文压缩后，先恢复原始 Goal、冻结标准、已失败尝试和当前检查点，继续同一工作循环。不要每完成一小步就等待指令，也不要在结束时把本轮必须完成的工作写成“建议下一步实现”。

## 后续结果（追加，不改写上方意图）

待复现与修复；正式两轮预算尚未冻结，正式实跑未开始。

### 首批失败回归与修复检查点

- `pytest -q tests/test_one_click_audit_regressions.py --basetemp=.local/audit-baseline --junitxml=.local/evidence/audit-baseline.xml`（Windows现有venv）：7 failed / 4.43s；D/E(2)/F/G/A/H各自命中真实缺陷。合成输入，无实际模型或视觉准确性声明。
- 初步修复后加入Goal/加搜/拼图/恢复关联集：81 passed / 6 failed / 42.15s；新增7项全部通过。4项旧测试因未使用规定的`-X utf8`读UTF8失败，2项长工作树测试路径超过Windows路径限制。先修正执行命令并在项目.local下用短basetemp重跑，不修改产品以掩盖宿主条件。
- 新增实际改动：UUID Goal且目录禁止覆盖；加搜预校验+文件失败回滚；逐次模型尝试独立账本；预算耗尽AgentCallFailed；关闭失败保留session cleanup_pending；拼图版本3。尚未完成A/B/C以及正式数据备份和验收。
- 旧测试临时目录重命名为`test-audit-baseline/test-audit-fix1`，防止合成received.json被历史发现误收，证据原样保留。

### 历史排重与数据保护检查点

- 校正执行条件后的关联回归：`run-tests.py r2`（前述6文件）87 passed / 41.89s；日志与XML在日用`.local/one-click-audit-20261022/r2.*`。
- C修前新增3裁切+基线反例：4 failed / 2.11s（cbase.*）；修后`run-tests.py cfix tests/test_one_click_audit_regressions.py tests/test_collection_history_cache.py tests/test_goal_photo_admission.py`：46 passed / 17.00s。
- C当前实现：冻结SHA绑定的64x64像素指纹；保留原3%规则之外的裁切注册比较和局部差异反例；新Goal在准入前同步完成全历史索引；基线SHA/算法/集合/回执排重绑定验证；Cosplay Goal不以普通portrait_photo计数。未知或疑似重复不放行。真实照片准确性与耗时仍待验证，不能以合成用例代替。
- 本轮官方备份命令（Windows主运行环境）：`.venv/Scripts/python.exe -X utf8 -m ref_lab backup --output .local/backups/backup-20261022-one-click-audit.zip`，1364资产。
- 已恢复到全新`.local/backups/20261022-one-click/restored-library`；`verify-backup.py`核验正式/备份表计数及既有外键错误一致，doctor实读1364原件及派生，0缺失/损坏，72既有外键错误未新增。ZIP SHA256 `6a507801fe37b8239230488c19fd73f2f2d347ecb6a1e6d76a2388d6f2744102`；详细证据`backup-restore.json`。
- 当前Windows BrowserSkill现有daemon0.3.2/协议1.3、Edge实例9d3f232a连接，0会话，未启动或替换daemon。尚未打开平台页验证登录。
- 旧实跑账本计时：R1记录44次、46原流，已记录耗时1617.62s、median33.12s、max97.99s，2次Token未知；R2记录39次、39原流，耗时1360.27s、median33.14s、max63.64s。旧累计墙时2102.39s/2046.067s。R1多出的原流需逐次重建，不能沿用旧汇总。
- 正常默认30张拟定2700s（按目标量`min(3600,max(900,target*60+900))`，依据旧真实墙时约2100s及索引/收尾余量），尚未冻结或用于正式验收；旧runtime固定900s需经正式配置链路明确修改并界面显示。模型尝试上限仍目标两倍，含失败。
- 广回归broad1期间修改了启动版本核验源码；其结果仅诊断，不作为内容冻结验收证据。最终需在稳定内容下重新验证受影响集。

### 原流、真实图与启动器检查点

- 旧原流重建：R1 46份真实原流，旧账本44次，已知Token1,275,605、3份原流用量未知；R2 39份原流/39次，已知Token1,203,564、0未知。逐次SHA/文件/结果/已知起止时刻与未知字段保存在`.local/one-click-audit-20261022/old-usage-rebuilt.json`。无账本时不能从文件mtime伪造模型起止时间。
- 历史发现新增暴露旧复制批次绝对路径指回原位置的问题；不删除历史、不跳过错误，复用项目既有按SHA找回同批次原图的规则扩展到历史子图。只有项目内预期命名空间中同SHA字节能恢复，缺失/变更/越界仍阻断。原记录不回写。
- Windows真实历史测量：1934路径/1510唯一指纹、发现4.922s、冷构建139.828s、无错误。旧真实原图298fb305…三种合理裁切重编码均匹配回同原图（0.328/0.312/0.266s，像素差1.504/1.435/1.370）；详细`history-measure.json`。不以这3例宣称所有裁切都已证明。
- Codex分别用原生view_image打开真实568eabd9…和7fb6adc6…，头/眼、杯和背景人物位置不同，属于不同画面；共享排重返回None保留连拍（real-burst-result.json），不宣称严格角色身份。
- 真实10b48c25…已打开，确为三格拼图。正确旧v2 no_collage记录在Job0f7ded75…；首次诊断错误误找72f7014e记录KeyError已保留。复制到隔离test-a22-real-collage后用既有verify_batch显式重算：v2完整快照、v3 grid_3x1生成3子图、全部裁切像素验证0问题、源记录/原件与人工文件不变（old-collage-result.json）。未把这3子图补入任一正式验收任务。
- Windows工作树.git指针原为WSL绝对路径导致原生Git无法识别；仅把本任务自己的指针改为等价相对路径，原生Git和WSL都确认同HEAD。此为执行环境放置问题，不冒称产品启动缺陷。
- runtime2：86 passed / 1 failed，Windows真实启动器的两个PowerShell生命周期用例已通过；剩余计时断言暴露collection_elapsed初始化未包含Goal准备，已对齐两个计数，待freezechecks重验。测试helper补与正常bat同样的-ExecutionPolicy Bypass，仅进程作用域，未改全局策略。
- focused3：149 passed / 1 failed，UI用例仍假定旧“快速搜图”文字和旧数量标签。已修成当前语义及2700秒/60次与动态15张预算断言。
- 新增证据损坏反例：修前2 failed（integritybase.*）；损坏账本曾静默重置预算、存储kind改变仍能借原流准入。修后严格原流解析与结果绑定，账本损坏保留并停止；integrityfix相关集58 passed / 55.87s。当前新增模型临时目录限定在本Job证据目录旁，并加入真实Windows轮询读句柄释放后的原子替换回归，freezechecks待完成。
- 正常网页已用本任务BrowserSkill会话xbho打开主项目（非正式实跑、未创建任务）。当前版本尚未切换日用服务。所有正式成果仍为0轮通过。

### 冻结前工程结果（仍非Goal完成）

- `run-tests.py freezechecks`：305 passed / 226.12s。范围：本轮新增回归、Goal准入/原流、历史缓存、拼图拆分/快照/项目同步、采集阶段/继续/预算/runner/UI、两个真实Windows PowerShell启动器生命周期、Windows实际轮询句柄冲突、分类、导入与人工库选择保全。日志/XML在日用`.local/one-click-audit-20261022/freezechecks.*`。
- 此后独立API坏证据投影反例apibase：1 failed / 1.54s，当前证据不可读时竟回退旧30张成功数。已修成实时投影优先、异常时可用数0及evidence_unavailable；在finalaffected重验。启动前历史索引错误也写正式blocked阶段回执，不再丢为无原因进程退出。
- 本轮原始Publisher基线与完整Goal契约保留。为满足用户“正式两轮之前有最终代码提交”的要求，后续代码冻结检查点将按AGENTS允许的等效受控Git命令创建，明确为工程检查点而非Goal完成；不得为了提前提交而给two-rounds伪造PASS、改写契约或重造基线。最终Git推送/Publisher事务/运行版本分别报告。
- 正式实跑尚未开始；正常网页预检小红书首页可读取真实内容，无登录/验证码门槛。Pinterest首页已正常到达，待可见页面检查。xbho旧自有会话已注销，正常stop返回not_found；新自有会话mlxu绑定同Edge9d3f232a。

### 进入主项目前的最后保全与调用方结果

- API新鲜投影修改后的finalaffected：130 passed / 1 failed / 145.66s。失败旧测试只写“found=2”摘要而无原件，却要求继续审核；改为提供两张实际落盘合成原件/received记录，保留继续审核功能断言，不恢复陈旧成功数。
- 失败下载未登记历史、SHA重复别名掩盖正式原件损坏两个反例：historyedgebase 2 failed / 1.85s；修后lastscope（本轮新回归/历史/Goal/阶段/UI）85 passed / 77.77s。每个正式原件独立校验SHA，不再依赖按SHA去重后单一别名路径；失败批次images中已收到但未登记的原图也进入既有历史范围。
- 最终范围实测：2163路径/1521唯一指纹、发现10.531s、复用缓存后构建28.031s、无错误，三裁切仍正确（history-measure-final.json）；较前测量补入11种未登记历史字节。
- 日用源码312处原有差异仍全部仅换行，HEAD仍0ce2587；已原样ZIP归档到`.local/backups/20261022-pre-code-switch/prior-dirty-bytes.zip`并保存每文件SHA清单，无暂存改动、无覆盖。
- 切换前运行读数：PID46388、正常库data/library.sqlite3；26项目/1364资产/1124引用/23灵感/238待筛/3756事件。唯一旧running Job b8070657…的owner45448不存在，无活动采集进程；不手工补状态。
- Windows已正常读取小红书与Pinterest首页内容，未遇登录/验证码门槛；不把首页可读当作新照片采集通过。
- `node --check web/app.js`、`python -m compileall -q ref_lab tools tests`、`git diff --check`均退出0。当前完整隔离suite fullfinal仍运行（已出现失败，必须待最终日志定位，不能宣称全套通过）。正式网页新实跑仍0轮。

### 全量与最后调用方回归

- `run-tests.py fullfinal tests`：1163 passed、3 failed、6 skipped /1087.09s；完整日志/XML保留。6跳过分别是未带入私有审美manifest、Windows无符号链接权限(3项)、无私有冻结实验与基线(2项)，不宣称通过。
- 3失败定位：旧断言要求完整旧子图不进历史（违反本轮全历史要求），旧错误文案限定，0ce已移除但测试仍要求命令内部重放导航。核对旧HEAD实现后更新测试，保留控制器有界恢复及click不重放验证。没有添加无证据的命令重试。
- 新反例uncertainbase：2 failed /1.43s；修复子图疑似重复/历史出错被记为确定重复。子图保持history_pending、完整原件留存，审核保持REVIEW_BLOCKED，均不凑数。`run-tests.py finalcallers`相关10文件108 passed /56.20s。
- 命令uncertaintyfix因误填不存在的test_collection_stage_continue.py而exit4、未执行测试，保留日志；已用实际存在的文件集重跑。
- historyrecordbase：1 failed、1 passed /1.20s；损坏derived.json曾静默缩小基线，已改为拒绝建Goal；未完整解码历史图片的Goal也拒绝建立，防止只冻结成功的部分。prefrozen关联集正在运行。
- 旧原生成功项兼容性：R1 42/42、R2 38/38完整回执通过新原流结果绑定验证；这不是新两轮准入，也不证明名称严格身份。
- 切换前再次核实仅日用server父子15924/46388，无collect_verified/collect_adapter运行；BrowserSkill会话列表空，未接管其他标签。

### 本轮有限实跑资源边界（正式冻结清单仍待部署版本核实）

- 本任务最多1次网页诊断任务、4次正式30张任务；正式每任务固定2700秒/60次图片类型尝试（含失败），单线程；总正式采集预算10800秒/240尝试。诊断不计正式成果，最多2700秒/20尝试。不得越界继续、追加预算或偷偷提高调用数。
- 任何正式失败保留原Job和证据；如需修复重验，剩余资源只允许重取完整同版本两轮，不把失败后的人工补足算通过。所有诊断与失败字节进入后续历史。
- 工程检查点、Git推送、Publisher事务与运行验收分别记录；此处未宣称PASS、尚未开始正式轮次。

- prefrozen：85 passed/1 failed /42.51s。未解码历史的同步构建本就抛异常、不是静默跳过；失败是新增用例期望服务Problem409却收到PIL原始OSError。已在既有建Goal边界转换为明确409，避免API无说明500。此前关于该同步路径静默跳过的推测撤回；损坏derived.json静默跳过仍有独立失败证据。freeze2仅重验受影响集。
- 严格真实历史复核（history-measure-prefreeze.json）：2163路径/1521指纹，ready=true/无错误，发现13.985s、warm构建3.953s；三实际裁切仍匹配原件。

- freeze2：86 passed /38.79s，Goal创建服务409/历史缓存/历史损坏/Goal准入/审核/阶段相关路径通过。legacybase：1 failed /1.46s，严格新准入会让旧成果页不展示旧照片；修后legacyfix（新反例+Goal+个人库）77 passed /37.61s。补保留已入库旧子图的只读展示：当前合格数保持新规则结果，单列“历史准入记录·当前待复核”，不补写旧视觉结论或新基线。oldread最终小集待结果。

- oldread最终小集4 passed /3.66s，旧原件/旧已入库子图只读展示与当前Goal成果页一致性通过。准备工程冻结提交；本提交明确为IN PROGRESS检查点，正式两轮0/2。

### 日用正常链路初次冷启动（工程检查点4fe203f）

- 工程提交4fe203f3fde49211e4dd2cc77b289ad104710312已推送codex/one-click-audit-20261022，ls-remote实查同SHA；非Goal完成、非main合并。日用独立任务分支codex/one-click-runtime-20261022同SHA，292个无关原脏文件逐字节SHA仍与归档一致。
- 通过正式terminate.ps1停止46388；随后的独立命令确认PID/运行记录/health均不存在。正式configure-windows-runtime.ps1设置2700秒并保留原历史roots/auto_classify。正式launch.ps1创建服务及server.json，执行宿主退出后独立runtime读数仍PID5444、源码/adapter同日用checkout、code_revision=4fe203f、code_digest=15e399a857048e202a20a4b67f4b3148211f2ceb4981b67bf723010347bf056c。26项目/1364资产/1124引用/3756事件未变。日志initial-stop/cold-start/after-cold-host-exit.*。
- 本次证明该执行宿主中初次正常冷启动确实工作，不倒写旧次失败原因。旧审计未保留足以定位当时具体失败点的完整进程证据，仍不能宣称旧启动链路通过。
- 实际旧0f7ded75批次10b48c25通过既有split_run_collages显式重算（非新任务补跑）：v2完整快照/v3三合格子图、原件不变、人工文件不变、重复复用；旧报告另行备份。原始27个派生文件均保留，新增3文件；未入库、未补写Goal计数。后续冻结历史包含这些字节。
- 一个Linux urllib读取Windows端口尝试被sandbox网络拒绝，未写API快照；改用Windows同一read-only helper成功。原runtime/config在此前已经复制保全。

### 续跑与正式第一轮开始（未通过）

- 上一条BrowserSkill fill帮助命令因自动审批账户用量不足未执行（审批未能完成，不是操作安全拒绝）；用户continue后同一审批路径恢复，未绕过审批。
- 间隔约6小时后重核：PID5444仍健康，同4fe203f/digest，全部冻结实现文件与runtime配置SHA未变，库计数仍1364/1124/3756，无其他采集进程。旧自有会话已注销，创建新自有omlp/Edge9d3f232a，debug d0089cdcd525f在正常导航前开始。
- 正式R1：正常网页选西木野真姬、search、目标字段填30，notes/Goal ID/额外别名为空；可见2700秒/60次尝试。2026-10-22T03:14:58.038754Z发起唯一开始点击，03:14:58.336Z记录正常POST /api/projects/1ed24eedebc54813b8472dca8cb9faa5/jobs。此后仅观察，未继续/加搜/额外审核。03:16:28Z创建请求仍pending，03:17:03Z尚未观测到新Job，开始按钮disabled。日志round1-*保存在日用.local/one-click-audit-20261022。
- 正式新轮次通过仍0/2；有限资源4个正式Job、每个2700秒/60尝试的边界不变。历史/失败/诊断字节不移除。

- R1已由应用创建Job c3e42762bc76463db1ca04e2d05fa7fb、Goal auto-353d7ddd22a4463d987919211bbfbd03；基线1524份/指纹算法2/SHA38ccc79ede29ba6e0054b675a5fe557bdb3010256221290f7805742bc0b0e24d（含旧H显式重算3子图）。准备229.282秒，写入search_elapsed与collection_elapsed，同预算2700秒，attempt_count=1。
- run-info实查adapter SHA0c9ca7adeb836bade660f26d190667e2d7be4712f1f8882535583b83faefce84、模型gemini-3.8-flash-medium、模型上限60、worker1、queries8/windows3/details96，与冻结一致。自有采集会话bwex保持active，独立网页观察会话omlp；无人工接力。03:20附近9个same_bytes历史重复已排除，尚无合格准入。

- 已回看用户给定旧原始执行记录（文件SHA 775e59fc89fe42487bc3df4e1b48306f5871006d77065cc600fb1ad598b7f8a1）：307–339行记录launcher调用后检查PID2344及health，再改为手动serve；3170–3287行再次launcher/health/日志检查后手动serve，并两种方式补写server.json，最后仅验证launcher识别现有进程。原记录主要是命令列表，缺少对应exit/健康结果与进程退出原因；可以定位旧验收断裂在launcher之后的进程持续/健康阶段，不能证明是产品创建失败还是原执行器生命周期回收。当前正常launcher在独立宿主退出后持续约6小时的PID5444/源码版本证据，与旧手动路径明确区分，不伪造旧根因。
- R1首个新received：ce629da0…，timings first_received=1792639361.6709802；03:23:10.288Z正常候选页实际decode800x1200。该图原生实际读图成功确认cosplay但名称关联unconfirmed，未纳入Goal。首张名称合格照片24989a09…的第2次模型尝试1792639504.7386858–1792639539.7676716、35369已知Token；03:25:52.767651Z首次轮询观察到Goal1张。浏览器可见时间按首次实际DOM/decode观察记录，不把模型结束时刻伪称浏览器paint时刻。

### 正式R1发现准入反例：本轮不能通过

- 根Agent实际逐个打开24989a09…、71e4d333…、ceab4de6…三个子图和bb86fb59…原图。24989a09与bb86fb59是同一画面（手、表情、背景物件一致），分别为带角落水印的小尺寸子图和大尺寸原图；系统却把二者计入Goal。不是仅SHA不同的推断，有实际图片观察及原始文件。
- 因此无论该Job后续达到多少，都不能认作正式PASS；保留全部数据/日志/模型回执，不删计数、不手写photo-audit、不人工补状态。继续只观察原冻结4fe203f Job自动结束，修复只在隔离工作树进行；后续必须新冻结版本取完整两轮，已失败字节继续进历史。
- 一对一复现：ImageHistory([24989a09]).match(bb86fb59)==None；注册拟合score2.510742/correlation0.995389，但local_error25.291667，超过当前局部阈值，被误当“无重复关系”。这是强整体相似与局部冲突应保持unknown却被清空的漏洞。duplicate-pair-probe.json / duplicate-pair-fit.json保存文件绑定、时序和数值。
- 同时复核consider：匹配快照和插入记录分离、原图与拼图线程可同时放行近重复；已新增并发反例验证，不靠放宽确定重复阈值修补真实案例。新增修前测试dedupsecondbase运行中。

- 失败R1自动结束：21原图/28独立候选/界面准入15（含已证实重复），28次真实模型尝试；stop=target_partial、未达30、首次单次attempt，无加预算。search-summary elapsed1705.032秒，加Goal准备229.282秒约1934.314秒，未用满2700；最终时间线/账本原样保留，后续不据此宣称完成。
- dedupsecondbase：2 failed /2.99s；隔离修复后dedupsecondfix63 passed /23.89s，真实漏重对变needs_review且不同真实连拍仍None。匹配语义版本升3，旧版本准入不得当新规则已校验；当前日用仍FP2/4fe，未偷偷改变运行代码。
- dedupcallers127 passed/1 failed /130.18s；失败实际Windows读句柄测试的150ms等待在高负载时早于replace结束、未产生冲突（attempts=[]）。改为真实读句柄持有至首次replace PermissionError后释放，未改产品；winwriterstable2 passed /0.67s。
- 网页观察失败源已实证：lazy图片在屏幕外complete=false，await decode等待未请求图片；仅终止自有observe-browser.py子进程50596并更换为不等待未加载图的观察器，未停采集。失败结果页完整15/15实际decode。浏览器导出failed-round1-browser.json 7,065,695字节；capture上限2000请求导致781 dropped，未丢操作记录；不宣称完整网络原流。未来通过轮的观察转普通成果页定期只读刷新，减少无关轮询记录，并保留本次缺口说明。
- 一对一probe helper第一次复测覆盖了duplicate-pair-probe.json为修后结果；原失败duplicate-pair-fit.json仍完整保留match=null及拟合前证据，原tool输出/修前FF日志也保留；后续输出改为duplicate-pair-fixed.json，不倒写旧证据。

### 原因闭环与下一工程检查点（仍0/2通过）

- R1最终精确账本：28次模型尝试，991,493已知Token、0未知用量；模型耗时合计1000.944461秒。summary cumulative_elapsed_seconds=1957.739，点击至finished_at约1959.585秒；前述1934.314仅相加两个阶段、漏了传输准备约23.425秒，现明确纠正，不冒称完整计时。
- R1发生8个计划耗尽时尚未用满时间/模型预算的正常流程缺口。新增controller回归autorefinementbase修前failed；首版修复82 passed/1 failed，因为新fixture未提供真实查询框的search字段，被STOP_STALE_QUERY拦住，不能当作修复无效或降低校验。修正fixture后，使用Git4fe原代码做明确标记的事后受控回归（不是编辑前基线），仍found0/search_plan_exhausted；新实现成功在同一个attempt取新query并保留900固定预算。
- 复用query_steps的可信别名/摄影意图轮换，只在自动Goal初始计划耗尽且时间、模型、候选与详情预算仍有余量时追加；最多24个不同检索词（初始8加两批），优先已有文字名称关联成果的来源，不把名称当视觉事实。单Job/同attempt、不增加2700秒、不增加60模型尝试、不重置历史与已访问页，不重跑同一查询碰运气。真实终止原因另存termination_reason，partial是结果状态。
- 不确定封面匹配不能将另一图片的名称命中升级到当前原图；新增正反例。refinementscope101 passed /55.38s；finalrefinebounds82 passed /37.47s（包含预算耗尽禁止自动改写/恢复）。编译、JS语法、diff检查待最终检查点重查。
- 单帖3张上限是否漏掉该真实帖其它可见原件尚未实证：源canonical链接在普通浏览器返回“当前笔记暂时无法浏览/扫码查看”，未重试挑战、未隐藏API或凭据；不据推测提高单帖下载上限。生产check_duplicate已限制单主图Pinterest Pin，未把小红书封面重复当整帖重复。
- 新匹配语义版本3，强整体一致但局部冲突只标待核验；确定重复阈值未放宽，既有不同手势合成反例及已实际打开的不同真实连拍保持None。匹配+登记使用原RLock形成一次原子判定，原件/子图线程不能同时漏过快照。旧准入回执不能自动冒充新规则已验证；旧照片仍可历史只读。
- 新库计数26项目/1396资产/1156引用/3825事件，72既有FK问题不增，无活动采集进程。官方backup-20261022-post-failed-formal.zip=1396资产，失败批次209文件另保全到.local/backups/20261022-pre-refinement/failed-run-c3e42762.zip；正在隔离恢复验证。
- 全局实跑资源授权不变：已用1个失败正式Job；至多3个正式Job余量、每个2700秒/60尝试；另保留最初冻结的1个正常网页诊断Job/2700秒/20尝试。下一代码检查点后先做诊断实测，再冻结新的完整正式两轮；旧失败不混算。

- 新官方备份隔离恢复通过：1396原件及派生实际doctor校验，0缺失/损坏，72既有FK错误一致；ZIP SHA700e70cd992b0bdf9aa9987014c47575b35faa84c28eacfeafaed68297f0a315。证据backup-restore-post-failed.json。最终JS/compileall/diff检查退出0，预算耗尽反例与相关82项通过；准备第二工程检查点，非Goal完成。

### 第二工程版本已正常部署（正式未重新开始）

- 新代码56bba676ab3e0847fd8a2e4f7d6fb1983f03d394已推送任务分支，ls-remote实查同SHA。日用新独立任务分支codex/one-click-runtime-v2-20261022；292个无关原文件字节仍与原归档一致。未main合并、未公开发布。
- 正式terminate.ps1停止5444并确认PID/record/health均不存在；正常launch.ps1自行创建服务及运行记录。宿主退出后独立读数PID12128、code_digest72377cc73a19b809f58a6a61cdaedfade5a560aedcab6ae121ceb1d7a2f0d168、revision56bba67，服务/适配器同日用checkout；1396资产/1156引用/3825事件保持。配置仍2700秒，模型预算60（诊断目标1按正常规则20）、worker1，Goal query最大24。
- 新工程快照helper首次错误沿用了原frozen-acceptance.json输出名，被assert not exists拒绝，原冻结清单未被覆盖；改成engineering-v2-snapshot.json独立存储诊断输入，非正式验收。
- 浏览器旧自有omlp会话在诊断准备时已注销，未接管其他会话；将正常新建自有会话，采集Job均无活动进程。此前直接canonical源帖404仅单帖阻断，未据此称整体来源不可用，未绕过。

### 诊断结果及采样盲区证据（正式仍0/2）

- 唯一诊断Job97deea5f302b4acab2a8d1d0a687800d，正常网页目标1/同56bba67，自动完成3/1，4次模型尝试，无继续/加预算/人工导入。点击2026-10-22T04:28:12.468137Z；正常创建POST201耗时202.91723秒。基线1556份/FP3，包含失败轮新增32资产。正常成果页实解码3/3。
- 根Agent分别用view_image打开10c28be2…、50451088…、a49a2746…三实际原件：真人Cosplay，有不同背景/构图/手持物与动作；不宣称严格角色身份。三图不是相同画面；后续仍需独立对冻结历史核对。诊断不算正式两轮，不追加第二个诊断Job。
- 更正此前“真实单帖3张盲区未实证”：旧失败批次source_text（普通可见DOM）明确含1/8及作者正文，capturenote只[:3]，后续五个图库项未尝试。新合成controller反例notequotabase failed /3.48s：前三张均历史、第四张新图，found0。计划复用既有DOM读取函数，把自动Goal单帖上限有界调到12并同时约束接收端/剩余候选预算；不是把未知图库项自动计数，仍逐张排重/画质/实际看图。时间2700、模型60、候选90、详情96不变。
- 单帖较多下载须共享Browser截止时间；将在真实capture_note调用链补“第一次已收到、时间耗尽后不得第二次HTTP下载”的最小反例。修改只在隔离树，日用56bba67诊断已结束后仍保持其原代码/产物。

- 诊断最终账本4次/144,014已知Token/0未知，累计609.034秒，session state=closed；目标1自动达3。3/3真实原件已逐个打开，3/3浏览器解码，仍非正式通过。
- 新单帖预算反例notequotabase修前failed /3.48s；HTTP截止反例notedlbase修前failed /0.70s（两次HTTP均timeout20，第二次在总截止后仍派发）。修后notecapfix115 passed /55.26s（controller/采集DOM/计时/恢复边界/Goal/继续/阶段调用方）。自动Goal最多12个当前已呈现图库原件项，受剩余候选上限限制；旧非Goal/独立采样默认3保持。每次HTTP timeout=min(20,remaining)，截止不再发下一张；已有字节保留。仅观察到DOM的原URL，不猜高清、不绕过访问。
- 此采集修改不改FP3匹配语义或原生分类协议；诊断证明的对应未变路径可复用，但新采样范围须由后续最终版本正式两轮实跑覆盖，不能倒写56bba67已经通过完整Goal。

- 第三检查点compileall、node --check web/app.js、git diff --check均退出0。诊断browser export因自有会话lgpc已失效返回not_found，未能保存完整debug录制；既有点击/POST/逐15秒状态/模型原始回执/成果解码日志保留，不声称完整浏览器流。重新部署前官方backup首次错误带了全局--data-dir参数，argparse拒绝且无写入；改回此前验证的官方backup命令执行，原失败日志保留。

### 最终版本aa3c904冻结与新正式R1

- aa3c9044737e8ca5d437aa674be5120e294300ee已推送任务分支，远端同SHA。官方1401资产备份/隔离恢复通过，ZIP SHA cef9dbe8169f99c2cbf99b7bde8e9df4ebdf523b8a08a6e3f88a3cc17a14a085；0缺失/损坏、72既有FK保持。正常脚本停止12128，独立确认PID/record/health消失，再正常脚本冷启动PID42200，源码/adapter同checkout/revision/digest7e39b0ea370b0da748ce4753d37f3bf377719f3d06f19f4d2c0ec597e6a18977；1401资产/1161引用/3840事件保持。新日用分支codex/one-click-runtime-v3-20261022，291个当前无关原文件字节保全（较前292少1是本次明确更新README）。
- frozen-final-v3.json于2026-10-22T04:55:34.839254Z保存实际实现SHA、配置、项目/可信别名与所有预算。2700秒/60尝试/worker1/candidate90/query24/detail96/note12/FP3/collage3。全局最多4正式Job，已有1失败、诊断1已用；不增加资源。
- 自有新观察会话yxxo，debug d82b16677176b在导航前启动；正常网页西木野/目标30/search、其它字段空、可见2700/60；唯一点击记录formal2-click.json。新版本正式R1在等待自动创建，不混入旧失败或诊断成果，Goal仍未通过。

### 新正式R1准入疑点（不得通过）

- formal2 Job e992f833c92945bc851af5f54e9f65fa，正常点击2026-10-22T04:56:43附近，网页POST201耗22.277秒、自动start POST200，同attempt。基线1561份/FP3，实核包含旧失败21原件和诊断5原件，所有字节未排除。
- 根Agent实际打开2859d9ad…，可见圆形底座上的棚拍式人物；source_text首行明确“可能含AI生成内容”。原生模型给cosplay_photo，但未解释此来源警示。associate_detail只选作者正文，未传递平台可见警示到准入。不能据此断言已证实AI生成，也不能将来源未决的图片当已验证真人摄影。formal2-ai-warning-finding.json保存原行/来源/原始模型分类；此轮即使自动达到30亦不接受为正式PASS，后续只观察自行结束，不修改计数/状态。
- 将先补最小反例，再在隔离树复用现有来源/计数与worker机制：平台完整独立行的AI警示保持待核验，保留名称元数据/原件，不把评论或普通AI话题统统当AI图。不追加诊断Job。正式总上限4轮不变，当前第二个正式Job已用，剩余至多两轮，必须最终同版本两轮均过；不提高2700秒/60尝试上限。

- aiwarningbase：原件与子图两项确实错误计1；第三项fixture缺producer_name，已纠正并单独aiworkerbase确认旧代码仍生成错误模型尝试账本（failed）。修复新增source_warnings读取完整独立警示行、保留在关联/发现轨迹；名称命中保持元数据，counts单列source_pending且排除父子图准入，worker不为未决来源派发type-only模型。canonical缓存同时绑定警示状态，后续同SHA的警示不得被只更新名称遮掉。
- 首次关联验证命令误写不存在的test_photo_classification.py，pytest collection退出4未跑测试；第二条helper标签含连字符被assert拒绝未运行；已分别纠正文件名及标签重跑，不将这两条当测试通过。

- aiwarningfix2关联99 passed /57.96s；新增共享子图边界首次44 passed/1 failed /42.97s，fixture默认parent.png导致第二张合成原件覆盖第一张，完整性保护正确报original_sha_changed。改用a.png/b.png独立文件，正重跑包含全部审计反例/Goal/收尾/继续的相关集。产品不降低原件完整性校验；此前99项结果不冒充后来新边界已经通过。

- aiwarningshared2：83 passed /57.72s，包含所有审计反例、原件/子图、后出现的共享子图来源警示、Goal、收尾与主动继续。此前名称/分类99项通过。compileall与git diff --check退出0。警示只匹配完整独立平台提示行，普通AI话题与否定句不一律拒绝；不声称有完整AI图像检测能力。新语义独立于FP3，因此不修改图像指纹算法版本。
- 当前日用aa3c904 formal2仍自动运行，05:15观察36原件/28旧准入；新修复未部署，不能倒写正在执行的版本已获修复。准备第四工程提交，明确Goal仍未完成。
