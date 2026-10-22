# C项裁切排重修复与新增两轮验收

最终状态：**NOT PASSED / 新增2个正式Job名额已用完**。同一冻结实施8bf51ba下两轮普通网页单次开始，系统准入13/30、1/30，分别因总时间预算和返回搜索页命令超时停止；未人工接力。已复现窄裁切漏重的修复及135相关回归通过，14张准入成果技术复核、正常冷重启和实际网页decode通过；不能替代两轮各30张验收。详细结果、失败证据、计时、用量和保全检查见下文。

## 原意与授权（不覆盖旧失败）

用户答复：**“授权修复并新增2轮验收”**。
原始完整Goal仍以附件`138a584d-8689-44b0-8b1a-68ec9b020b6d/pasted-text-1.txt`及`2026-10-22-one-click-audit-fix.md`为准：最终同一实现，两轮正常网页单次开始，西木野真姬/30张，每轮至少30张合格、对全历史及跨轮排重的新真人Cosplay照片；无人工继续/加预算/CLI补采集/手动导入/补状态；正常启动器持久化通过，A–H与数据/证据/人工决定保全。

新增边界：最多2个正式Job，每个2700秒/60次真实模型尝试，合计最多5400秒/120尝试；0诊断Job。保持画质、原生读图、来源与重复排除门槛，不以凑数调整；不合并main、不改审美、不新增付费服务。不把上轮34/31当新版本已通过。

## 恢复基线及方案边界

- 日用checkout与隔离源码均以497a88c为编辑前版本；日用运行仍83f7790，旧失败/成果/备份均保留。工作树位于`.local/worktrees/narrow-crop-goal-20261022/root`，分支`codex/narrow-crop-goal-20261022`。
- Publisher新事务`01a1629b-3e07-7003-8579-cdea1f9ce6ff`在首次编辑前start/contract，原事务DEFERRED不覆盖。
- 已知失败：横图1619×1080保留40%宽/100%高并等比例重编码成竖图，match返回None；对应合成box3失败。证据仍在`.local/one-click-audit-20261022/final-crop-boundary-counterexample.json`及`final-crop-regression.*`。
- 根因：共享匹配的粗窗口和细拟合各自截断较窄ROI，几何范围不足被错误当“无重复”。保留现有像素差/相关性/局部冲突阈值，不靠放宽相似度制造排重；扩大合法几何搜索，匹配语义升级并失效旧准入证明。
- 影响调用方：ImageHistory.match/consider、collector原图/封面/恢复/Review、拼图子图、Goal全历史冻结、PhotoTypeWorker历史绑定、共享counts。复用现有缓存、基线、原子判定及needs_review；不另建排重/计数实现。

## 验证与正式实跑次序

1. 保存修前失败，增加横/竖不同方向、不同长宽比及连拍反例；共享匹配修后重验。
2. 实际原图裁切变体与不同实际连拍检查；相关缓存/Goal/子图/队列/Review/旧读取调用方回归及耗时测量。未知关系不计目标。
3. 写正式库或切运行前核对真实数据目录/活动任务，官方备份并隔离恢复校验；不动旧人工选择。
4. 冻结代码提交、实现文件SHA、配置/来源/别名/历史基线与新增2轮资源安排。每轮只能正常网页开始一次；失败保留，不人工补数。
5. 正常stop/start冷启动及重启后核对两轮计数/原件/来源/引用/模型流与浏览器实际解码。
6. 完整Goal PASS或真实外部阻断/冻结资源边界停止；Git/运行/Notion分别报告。

## 检查点

IN PROGRESS。新增正式Job尚未使用，未进行新模型调用。共享匹配修复已完成本地验证，等待历史索引测量、官方备份隔离恢复及运行冻结。

### 修复及修补循环审查

- 根因是共享排重几何搜索没有覆盖正常窄裁切，64像素指纹也丢失头部裁切细节。保留原像素差、相关性、局部冲突和覆盖冲突待核验规则；指纹/缓存升级为4，使用128像素指纹及本机多尺度模板定位，再按原像素门槛拟合，不改画质或照片准入。
- 已删除仅扩大窗口、全尺度PIL逐一细拟合、向量插值及mesh粗排序的失败方案；证据在`renewal-crop-vector.xml`、`renewal-crop-fixedscale.xml`、`renewal-crop-mesh.xml`、`renewal-crop-fp128.xml`等。它们分别暴露旋转方向、覆盖冲突或水平窄裁切漏重，不作为通过证据。
- 复用现有ImageHistory和拼图analyze；候选确为可拆拼图时，对旧单个面板的包含关系留给子图逐一排重，不整张丢弃新面板；子图仅排除自己刚登记的父图，保留其它历史父图/子图。新增局部依赖opencv-python-headless 4.14.0.94，仅处理本机像素；缺失时历史未就绪并拒绝准入。`pip check`通过，原numpy/Pillow未更换。
- 最终粗定位改用本机面积采样减去PIL重复缩放开销，最终判定仍使用原像素门槛；`renewal-crop-fastproposal.xml`12通过。随后`renewal-crop-freeze.xml`121通过（61.54秒）；`renewal-crop-adjacent.xml`14通过（5.53秒），覆盖共享缓存、Goal、模型账本、关闭恢复、原图/子图、加搜拒绝一致性、旧读取、自身原件排除和自动采集。Starlette现有httpx弃用警告保留，不影响断言。
- 真实原图5个裁切/重编码变体全部识别为重复，实际不同连拍未拒绝；绑定SHA和结果在`renewal-real-final.json`。合成反例保护纵横裁切、可见姿势变化、覆盖冲突、混合拼图与父子身份，不能据此宣称所有照片已审美验收。
- 两次TestClient被Windows沙箱socketpair阻塞的原输出保留；核实是本机套接字权限后在正常权限下重跑，未把挂起算PASS。官方备份首次同样被沙箱临时目录拒绝，确认未产生输出后使用正常权限执行。
- 日用checkout仍干净497a88c，服务与适配器仍旧冻结83f7790。数据库1531 assets/1291 refs/82 jobs；唯一running状态b8070657为10月21日旧初始化残留，无对应活动采集进程，保持旧状态与记录，不补写。
- 官方新备份`.local/backups/backup-20261022-renewal.zip` SHA256 `0f73b18051ae99111eb84d3de08e75ad51a716b5a8bcf13eec4e8e90d9bd367e`，隔离恢复到新目录`.local/backups/20261022-renewal/restored-library`。原库/恢复库各表计数、integrity和72条既有外键错误一致，doctor核验1531原件及派生无缺损；不迁移、不覆盖原库。
- 全历史真实路径2800条、按SHA唯一1694组，新FP4索引ready/errors=[]；发现18.235秒、冷建241.015秒。100实际指纹匹配样本1.453秒，推算1694组24.614秒，仅为抽样估计，不当作正式Job时间。测量缓存独立保存，不预填正常应用缓存；正式网页冷建时间如实计入点击时间线。结果`renewal-history-final.json`。
- 工程冻结检查：`git diff --check`、修改模块compileall、`pip check`通过。正式前先保存限定路径工程检查点；完整Goal仍PENDING，不能用工程提交或135回归通过封为COMPLETED。正常启动器部署同一工程版本后两轮标签formal5/formal6，资源仍2×2700秒/60尝试、0诊断。

### 新授权第一轮开始

- 工程冻结`8bf51babf37e0a499b0a9c8758459c75028bc140`，任务分支已推送origin且远端SHA一致；日用任务分支快进至同一版本，未触及main。正常terminate确认旧PID11976消失、server.json消失、health拒绝连接；随后launch正式创建PID53624及运行记录。冻结摘要`f95efa277289a8e9658047a6c83f454edc80781e7e25565cdc4661722c9c83f5`，141实现/依赖文件摘要复核无变化，配置保持2700秒/60模型尝试。
- 冻结证据`frozen-renewal-v5.json`。原Edge实例9d3f232a已实际探测连接且无其它会话；ROOT后台会话zgkj在导航前启动debug记录。正常页面选择西木野真姬、目标30、别名/Goal ID/要求留空；10:02:03 UTC单次点击开始，标签formal5，新增额度已占用1/2。没有模型预采集、手动导入或缓存预热。首次FP4冷基线在正常应用内建立，等待时间保留在点击时间线，Job绑定出现后只读观察。
- 备份中的1291条完整refs另存私有只读基线，最终逐条比较人工决定及原记录；旧失败状态b8070657未改写。
- formal5自动建立Job`62654f815b084ce3b69acfb830015b7c`，10:06:36 UTC开始唯一2700秒尝试；冷基线准备约273秒，与Job执行时间分开保存，不缩去点击等待。冻结基线1694组FP4/SHA绑定通过，与独立全历史集合完全相等；旧4正式和1诊断全部原件覆盖无缺漏。约10:22 UTC已取得5原件/4合格，5次模型尝试（第5次当时执行中），ROOT实际分别打开前4个合格原图，姿势/画面不同，记录`formal5-root-visual.json`。旧模型/源码/准入规则未修改，无继续或加搜；本轮尚未通过。
- 10:35 UTC约29分钟：16原件、8名称关联合格，15次模型尝试；新增探索页缺少目标名称证据，真人摄影也未冒充本目标成果，拼图待处理不计数。ROOT已实际分别打开8个合格原图；浏览器按120秒间隔实际decode。实跑尚未完成，不以下载数或CLI成功判断达标。只读观察器按实际Job起点覆盖尾段；这是证据采样窗口，不修改Job的2700秒预算或采集状态。
- formal5最终于10:46:32 UTC自动结束：**13/30，FAIL**，`time_budget_exhausted`，22原件、172重复、8查询/17窗口/71详情，21真实模型尝试、739059已知Token、未知用量0。应用累计计时2657.493秒；collector自身2355.922秒，冷基线及应用初始化计时不得遗漏，点击到最后引用的精确时间以事件导出为准。没有人工继续、加预算、CLI补采集或手动导入。正常采集浏览器回执closed；ROOT最终13/13实际解码，debug原始导出3971774字节、49操作、丢失请求/操作均0（页面上下文/performance记录有容量边界，保留原coverage），随后正常stop自身会话。ROOT已分别打开全部13个计入照片，其中一张画面明显偏软如实记录，未宣称细节清晰或用户审美接受。
- 已启动本轮只读全历史内容/原件/来源/原生回执/引用/用量复核。新增正式额度已使用1/2，准备按同一冻结版本、同一普通表单执行第2轮；不把第一轮13张改称达标。
- formal5技术复核完成（368.297秒）：13个计入成果逐一对1694组冻结历史内容比较、轮内比较，未检出重复；原件/正式库SHA、来源、唯一项目引用、照片类型/质量现有门槛、原生读图流与FP4基线绑定全部通过。21/21尝试成功，已知Token739059、未知用量0，模型wall合计724.972秒（含工具/等待，不是端到端总耗时）。本轮真实网页目标仍FAIL 13/30，技术复核PASS不能替代数量验收；证据`formal5-technical-audit.json`及时间线。

### 新授权第二轮开始

- 新ROOT独立浏览器会话wclt在导航前开始debug，普通页面再次选择西木野真姬，目标30、其它输入留空，10:50 UTC单次点击，标签formal6。新增正式额度2/2已启用，0诊断，禁止自动再开第3个。
- Job`a27337cfda984eb69124bd6ade172bb7`，同一冻结8bf51ba/摘要f95efa…，141个实现/依赖文件SHA复核无变化。自动FP4基线1717组，完整包含先前1694组、formal5登记22份新原件和另一份未进入received清单的新字节。formal5的164个落盘文件（含历史重复）全部保留；新增孤立字节faef290f…也进入后续排重，不因未入清单被忽略。
- formal6最终**1/30，FAIL**，停止原因`command_timeout`，不是总预算耗尽或模型不可用。`navigate-back`先超时，系统在同一Job内自动恢复一次并确认recovered；再次返回搜索页超时后恢复未完成，保留1份新原件并正常关闭采集会话。应用累计353.940秒、collector271.609秒；1次真实模型尝试成功，34815已知Token，未知用量0。完整浏览器debug1160147字节已导出，无丢失请求/操作，ROOT会话正常stop。
- 唯一计入成果已由ROOT打开实际原图，网页1/1实际解码；对1717组冻结历史内容及正式库/来源/唯一引用/原生读图回执/既有质量门槛/FP4绑定的37.562秒只读技术复核通过，没有借人工继续或加预算改为达标。

## 两轮结果与资源边界

| 项目 | formal5 | formal6 |
| --- | --- | --- |
| 正常网页独立Job | 62654f815b084ce3b69acfb830015b7c | a27337cfda984eb69124bd6ade172bb7 |
| 同一实现 | 8bf51ba / FP4 | 8bf51ba / FP4 |
| 目标 / 系统准入 | 30 / 13 | 30 / 1 |
| 登记新原件 | 22 | 1 |
| 应用累计秒数 / 上限 | 2657.493 / 2700 | 353.940 / 2700 |
| 点击至最后项目引用秒数 | 2665.305 | 357.286 |
| 首原件落盘距点击秒数 | 965.775 | 312.268 |
| 首合格API首次观察距点击秒数 | 1002.653 | 363.485 |
| 首合格网页首次decode距点击秒数 | 1090.522 | 445.411 |
| 第30张 | 未达到 | 未达到 |
| 模型尝试 / 成功 / 失败 | 21 / 21 / 0 | 1 / 1 / 0 |
| 已知Token / 未知用量尝试 | 739059 / 0 | 34815 / 0 |
| 停止原因 | time_budget_exhausted | command_timeout |
| 目标验收 | FAIL | FAIL |

两个Job均仅一次正常网页开始、一次应用attempt_started事件，无extend/replenish事件，无CLI补采集、人工继续、手动导入或状态补写。模型wall合计760.137秒，包括工具/等待，不与其它并行stage直接相加。API采样15秒、网页decode采样120秒，表内可见时间是首次实际观察，不冒充精确首次渲染。搜索路径没有`collection.attempt_finished`事件，因此该事件时间为null；末次search_stage及import事件如实保留。

新增正式名额2/2已用；应用累计约3011.434/5400秒，真实尝试22/120次，0诊断。未用时间或模型次数不能兑换第3个正式Job，不能改变完整Goal或复用旧34/31。**完整Goal NOT PASSED，资源名额边界停止实现/采集。** C的已复现窄裁切缺陷及对应回归已修复；正常一键的吞吐与导航恢复仍未达到目标，不能将技术复核PASS或Git检查点写成整体完成。

## 保全与正常启动器复核

- 最终官方备份`.local/backups/backup-20261022-renewal-final.zip` SHA256 `108230cff453195b1d49a19b4a4cb5a57c44392e13902b19a65188db8ac47533`，隔离恢复核验1554原件/派生、integrity和72条既有外键错误，未新增错误。正式库新增23条引用及23份Asset，全部成果与未计入候选均保留。
- 旧引用首次比对使用了doctor处理后的恢复库，出现42条差异，失败证据`renewal-pre-existing-refs-final.json`保留。改用同一个编辑前官方备份原始SQLite字节、不运行Library/doctor后核对：1291条旧refs全部字段与原库一致；42条仅是隔离doctor改变的revision/updated_at，不是生产库改写。纠正证据`renewal-raw-pre-existing-refs-final.json`。
- 原有1531条Asset元数据及189个已冻结旧关键文件（原件/模型流/记录）逐一核验未变；原件/历史批次继续按全历史SHA与指纹绑定保留，未删除旧失败或改变人工选择。
- 两轮结束后先固定61个关键文件、23条新引用、模型流、完整Job及计数。正式terminate确认旧PID53624消失、server.json消失且health拒绝；正式launch创建PID44876与新记录。冷启动后61文件/23引用/13与1计数及同一实现/配置精确比较PASS，没有新采集或重复导入。随后独立只读浏览器会话实际decode 13/13及1/1，返回SHA与审计选中集合完全一致；观察会话正常关闭。证据`renewal-before-restart.json`、`renewal-after-restart.json`及`renewal-cold-browser-decode.json`。
- 跨轮比较复用已完成的第二轮1717组FP4全历史内容核验，其中完整包含第一轮13个计入成果，13个跨轮配对均已覆盖且未检出重复；不是用SHA零交集代替内容比较。轮内及对历史复核结果、原生读图与每次尝试均在两份technical-audit中保存，`renewal-cross-round-content.json`绑定第二轮基线和完整审计文件SHA。

## 最终保留的缺口

- 正常网页两轮各30张：FAIL（13、1），不得表述为COMPLETED。
- 第一轮历史匹配/搜索获取吞吐占用预算，第二轮返回搜索页连续超时且自动恢复一次后失败。现有原始错误、模型流、计时与输入均保存；本轮不再修改冻结实现或增加实跑。
- 用户个人审美接受、严格角色/服装身份、其它平台安装/运行：UNVERIFIED。ROOT对14张实际原图的观察不代替用户审美；其中d856fc4…明显偏软，现有技术质量门槛通过不等于清晰度或审美认可。

## 交付与继续边界

- 实施及两轮冻结提交均8bf51ba，运行仍该实施摘要和同一日用checkout/adapter；后续收口只改本任务及CURRENT文档，不更换实现以追认实跑。Git保存任务分支未完成检查点，Notion未启用；canonical Publisher保留完整Goal要求，不能为封COMPLETED而降为仅执行两轮。
- 恢复数据必须使用新空目录及doctor，不覆盖1554原件/1314引用；回退代码需先停止服务、备份新增库，并保留本轮原件/回执/错误。FP3旧Goal不能被当成新FP4准入证明。本次没有main合并、强推、公开部署或私有图片/数据库提交。
- 如后续获准继续，先从formal6的navigate-back两次超时和一次恢复原始证据定位，再验证同Job有界恢复；formal5的635.441秒原件历史判定、349.530秒封面排重/获取、513.769秒详情下载按并行stage分别分析，不能简单相加成总时长。保留当前失败作为反例，后续代码变更必须重新取得同一最终实现的完整两轮，现有13/1不算通过。

## 可复跑的本地验证

在冻结工程源码目录使用日用`.venv/Scripts/python.exe -X utf8`，测试数据必须指向仓库`.local/test-*`隔离目录：

```powershell
python -X utf8 -m pytest -q --tb=short tests/test_one_click_audit_regressions.py tests/test_collection_history_cache.py tests/test_goal_photo_admission.py tests/test_collage_split.py tests/test_collection_audit.py tests/test_collection_stages.py tests/test_search_continue_recovery.py --basetemp=<repo>/.local/test-crop-renewal-freeze
python -X utf8 -m pytest -q --tb=short tests/test_collection_autonomy.py tests/test_review_self_duplicate.py --basetemp=<repo>/.local/test-crop-renewal-adjacent
python -X utf8 -m pip check
```

实际结果分别121通过、14通过、依赖无冲突；JUnit及输出保存在`.local/one-click-audit-20261022/renewal-crop-freeze.*`和`renewal-crop-adjacent.xml`。Windows TestClient需要正常本机套接字权限，沙箱挂起的两份原始日志保留为失败环境证据。未运行与本次共享排重无关的课程/UI美化/全仓套件，不影响既有135项证据；最终真实两轮及重启验收另列，不用测试代替。
