# 正式交付收尾 Loop

## 原始目标与边界（编辑前记录）

用户已确认最新四张真实摄影参考质量达到要求。本轮冻结审美，目标是“一次真实搜图要求，系统自主使用多语言、多来源检索，自己进行可信参照调查和逐图质量核验，在资源预算内尽可能达到目标数量，正常生成结果并导入参考库；可恢复中断后接着完成，不重复已完成工作”。工程关卡通过后，最多启动一次新的冷启动20张正常网页委托，准确报告全部耗时。

原始任务文本SHA256：156a802655da0f176c24058af22d151d2d3bedcffe5884ca4a04bd6c349830ee。基线为codex/collection-supply-20261019的02162249a040e5ba86ee7f9757659e25be2f4d56；原工作树干净。日用目录仍有既有未提交工作，不改动。新实现仅在.local/worktrees/collection-finalization-20261019下，ROOT分支codex/collection-finalization-20261019。Publisher在首次编辑前已start并声明R1–R8、delivery.git=true / notion=false。

保留模型、摄影提示词、accepted、角色/服装核验、完整needs_supplement、schema3、两摄影worker/单浏览器/顺序提交/参照变化保护。保留私人原图、原始模型回执、失败记录与K/I/M/X。无新付费API、无云端浏览采集、无Root手工补图、无main合并、无日用服务切换、无Notion。

## 实现前简要设计

- Stack：Windows Python/FastAPI、SQLite、现有BrowserSkill/Edge与AGY CLI；复用原子写、进程锁、任务包、严格导入和内容SHA。
- ROOT：tools/collect_verified.py、ref_lab/verified_collection.py的规划/恢复边界、相关采集回归与协议/任务文档。新增小型恢复/覆盖模块仅在复用不足时采用。
- Job工作树：ref_lab/agent_collection.py、service.py、app.py及正常网页状态/恢复按钮；相关runner/UI/import测试。稳定任务目录、独占attempt与同Job重复导入。
- Checks工作树：历史指纹缓存及其等价/失效测试；核对原Actions并最小修复git_ops、Windows夹具与学习路由/样式测试。与Job测试文件如有交集先交接，不并发改同文件。
- 风险：临时目录使网页恢复丢失；received先于audit导致合法断点被拒；数量先达到会跳过覆盖；重新启动会清零时间、误排除本Job合格图；成功报告未绑定目标与覆盖。
- 验收：按下列独立标准，先合成故障与边界回归、25图回放和四图契约核对，再冻结代码并从正常网页发起唯一20图委托。

## 独立验收标准 COLL-AC-v1

由独立只读审查者在实现前提出；冻结后不得随结果放宽。

| ID | 可观察通过条件 |
|---|---|
| COLL-AC-01 | 模型、摄影提示词、accepted、角色/服装核验、完整needs_supplement和schema3契约保持冻结，提供基线对照。 |
| COLL-AC-02 | 数量达标但覆盖不足、数量不足、来源受阻、搜索耗尽、正常达标：报告、Job、API、UI状态一致；保留安全停止原因。 |
| COLL-AC-03 | 分别证明语言、平台、图片来源覆盖；可信中日英别名有界真实机会；数量提前达到不能跳过覆盖，超出现有能力的要求列缺口。 |
| COLL-AC-04 | 每图可追溯查询、平台、原帖与原字节；分别统计图片、帖子、可确认发布者及网站；未知不编造。 |
| COLL-AC-05 | 原图接收未登记审计、部分完成且模型在途、判断完成未导入、服务退出四个边界硬中断后合法恢复，保留原字节回执。 |
| COLL-AC-06 | 复用绑定原图SHA、完整项目条件、参照版本、模型与规则契约；逐项变化使相关旧判断失效。 |
| COLL-AC-07 | 服务重启识别遗留任务，正常UI继续同Job；不抢活跃任务，不在启动时自动调用模型。 |
| COLL-AC-08 | 同Job恢复搜索计划和访问进度；通过/拒绝完成项不重复调用，待核继续；旧通过图完整交付不被历史排重吞掉。 |
| COLL-AC-09 | 重试、调用和累计时间预算不重置；双击、并发继续、取消、迟到输出受attempt所有权约束；并发与参照保护不变。 |
| COLL-AC-10 | 判断完成后、ZIP生成后、部分导入后中断均幂等收尾；SHA/ZIP/manifest/数据库一致；重入0新模型、无重复且人工数据不变。 |
| COLL-AC-11 | 缓存仅在内容SHA/算法版本/完整性等价和同机收益成立时采用；无明确收益可暂缓，不改排重阈值。 |
| COLL-AC-12 | 核查0216224的Actions原始失败与候选结果，解释git_ops、Windows夹具、browser路由/样式契约归属；受影响回归通过，不删跳弱化用例。 |
| COLL-AC-13 | 25张原图原回执在候选重放：预测、准入、顺序25/25相同、18准入；四张认可基线保持，回放不冒充网络测速。 |
| COLL-AC-14 | 工程通过后最多一次完整20张：未用于本次调参的合法角色、无可复用参照缓存、隔离Windows正常启动/UI链路，提前冻结条件代码来源预算。 |
| COLL-AC-15 | 原始时间线覆盖网页点击、首张正式可见、最终入库/收尾；wall包含索引参照重试恢复导出；分解耗时/调用/错误/补证/重试/可得Token，超时如实。 |
| COLL-AC-16 | 重新打开正常网页仍可见本批全部入库图；独立打开首中末与代表拒绝/身份矛盾，检查错角色/非真人/拼图/损坏/错绑/重复/无参考价值，保留AGY判断。 |
| COLL-AC-17 | 父Agent交付候选SHA、原始证据、精确回归、保护对照和远端SHA；不写Notion/合并main/切日用，最终仅READY_FOR_OWNER_ACCEPTANCE、PARTIAL_WITH_EVIDENCE或BLOCKED_WITH_EVIDENCE。 |

## 进展

2026-10-19：已完成基线调查、独立验收条件及编辑前Publisher事务；工程实现开始。真实20图任务尚未启动。

接续检查点：Job worker 的9个目标文件及checks的6个文件已按独占路径集成到ROOT，原工作树/日用库未改。Job worker原55项PASS为synthetic executor/隔离数据与Chromium UI；ROOT首次组合57PASS/1FAIL，foreign ZIP测试在较深临时目录得到adapter_or_result_error，正在使用canonical根内短路径定位，未把它标为通过。

独立审查第1次REVISE：旧resume漏语言、partial结果被永久封存、缓存命中重复计数/额度末次成功不能复用、第二轮翻页错查询、旧无binding断点被拒，共5项P1。按原标准修共享恢复边界，不降低摄影准入。ROOT新增4项预算/成功回执证据回归先4FAIL；修后这4项通过，扩测34PASS/3FAIL（2个毫秒sleep并发夹具已改事件同步、1个无效ZIP预检由控制器修复负责）。验收未通过，20图尚未启动。

25原图/原回执只读回放已运行：25/25预测、顺序与原回执相同，18准入；单/双worker为3.746/2.181秒，0真实模型/浏览器调用，仅本地定时回放。BrowserSkill沙箱named-pipe拒绝访问，授权只读检查确认原daemon和Edge 9d3f232a可连接、无现有session；未重启daemon、未改设置。

第2次定向审查：原5项中4项关闭，发现参照查询把model_blocked标记finished、普通已有ZIP仅核manifest未核图片字节。两项回归先2FAIL；修复参照执行状态与ZIP复用边界后，参照/控制器组合30PASS（review-round2-fixed.xml）。部分包继续的真实控制器路径用合成PNG验证：保留旧包SHA副本、仅新增1次待核、旧准入字节不变，旧receipt SHA及同manifest换图片均拒绝。缓存重建成功attempt证据的子进程夹具已按真实写入顺序补全，2/2恢复PASS。

真实旧格式25图兼容复核：无新job binding、旧attempt也无binding，仍通过原prompt/schema/model/图像输入SHA及成功终值严格对应；独立审查者另行复核25/25、18准入、0新CLI、原JSON未变。四张认可基线逐份原图、ZIP、画廊、回执与当前accepted复核4/4相同；不进行新的审美调参。

CI原失败已核实：本机Publisher git_ops依赖改为工具委托契约测试；Windows夹具复制当前collect_verified，并复用测试解释器已安装依赖（system_site_packages），不联网安装；学习页实际为/learning及14个domain，不再断言旧10个topic；图库颜色与当前CSS一致。隔离原生Windows pwsh/Windows PowerShell启动与终止、桌面/移动学习入口合并4PASS（runtime-ci-fixed.xml）。远端Actions尚未复跑。日用保护基线为1541文件、1177原图、937条Reference，只读保存在.local/finalization/daily-protection.json。

Job候选已在完整ROOT依赖上收敛：`python -X utf8 -m pytest -q --basetemp D:\AI PROJECTS\photography-reference-lab\.local\jb2 tests/test_collection_job_recovery.py tests/test_collection_runner.py tests/test_imports_jobs.py tests/test_collection_ui.py --junitxml=.local/finalization/job-final.xml` 为70PASS/55.54秒。此前68PASS/1FAIL是硬退出夹具只配置子进程、未给显式partial继续的父进程配置适配器；补父环境后通过。新增预算耗尽反例先FAIL，再修为复用已导入SHA的原ZIP，0新executor、不清预算。已验证真实ROOT API→runner→worker.main→真正job_binding/collector-state→ZIP→导入（视觉/Browser仍是明确替身），返回complete；连同跨轮旧包/换字节拒绝回归2PASS。未将合成判断称为真实视觉验收。

工程冻结：独立审查J01/02/04关闭；J03另复现“新manifest B封存、ZIP仍A、预算耗尽”，修共享本地finalize_only与write_result，复用原audit/参照/原图检查、SHA归档和原子写入，禁止Agent构造、Browser或执行队列。local-finalization.xml 9PASS，独立复核关闭J03且无剩余P0/P1。最终组合final-integrated.xml为141PASS/1FAIL（120.85秒）；唯一失败是子进程启动任务包阶段0.1秒的瞬时PermissionError，未调用适配器、正确受阻，单项final-hard-exit-recheck.xml 1PASS/2.28秒。共享调用方原176PASS/3FAIL中的三项原断言已按冻结目标修正：90目标1图不算完成、换角色后旧preflight不得套用、schema2无覆盖不算成功；原数据与来源保护断言保留，最终组合均通过。没有删除或跳过失败检查。

运行源码冻结SHA256：387d9ddc8a65dc88c7e74c75139b9992aac3c1a7357f139e4a8a951af905baee，128个运行文件逐项哈希在.local/finalization/source-freeze.json；Git基线仍0216224，尚未提交。唯一实跑拟用已有西施项目条件（王者荣耀、不限服装、原brief及默认器材）、目标20、原gemini-3.8-flash-medium、XHS/Pinterest、2视觉worker、2100秒外层/2040秒内部预算。正常scripts/launch.ps1启动ROOT自有18783/ui-data，跳过已确认在运行的共享服务引导；不改日用18765。参考冷缓存将在实际Job完整快照上点击前核验。

## 最终工程回执：BLOCKED_WITH_EVIDENCE

本轮真实目标未达成，不能作为日用切换验收通过。工程修复与安全收尾已独立复核；唯一冷启动委托为Job `3b8fdfd235964008bc636b6eeba0aaf1`，完整快照已确认没有可复用参照缓存，未建立第二个20图任务。实际从Edge正常网页建立并点击执行，随后两次继续仍是同Job，最后一次仅本地受阻收尾，18份原始模型attempt文件名称与SHA全部不变，新增模型调用0。

| 验收维度 | 实际结果 |
|---|---|
| 正常搜图 | Windows启动器→正常Edge网页→同Job执行/恢复→schema3受阻包→服务接收；没有从内部脚本替代正式UI验收。 |
| 质量 | 主人认可四图的原图、ZIP、画廊、原回执及当前准入4/4保持；新批没有准入图，不能宣称新质量或审美通过。 |
| 数量 | 收到5份不同原图，完成3份核验、2份待核；正式准入0/20，入库0。 |
| 多来源/语言 | 实际观察小红书`西施 cos 摄影`与Pinterest`Xi Shi cosplay photography`，分别zh/en；正式图片/帖子/发布者/网站分布均为0，未虚构日文检索或作者。完整交付覆盖未成立。 |
| 中断恢复 | 首轮历史索引缺陷在摄影搜索前停止，修后从正常UI继续同Job，成功计划/发现未重跑，原截止不延长；最终输入解释变化守卫拒绝复用受损参照，0新增调用收尾。 |
| 性能 | 执行按钮点击1792419011684至最终网页API回执1792421553464，共**2541.780秒（42:21.780）**；无正式首图。该数包含修复、中断、页面重开和本地收尾，不能当作无中断性能基准；Job累计执行1397.624秒。 |
| 正式包/重开 | blocked空ZIP与manifest一致，数据库引用0；ZIP SHA256 `f4ce0fe308a14029be9f99b4fe3fc204ef3c50fa75cfac675dfa60b6bbf893f8`。全新Edge会话重开后仍显示0/20受阻；没有新入库图片可供重开浏览。 |
| 回归/CI | 141项组合PASS、1次瞬时PermissionError单项复测PASS；编码及相邻恢复/缓存76PASS；历史环境42PASS/1个测试尾部NameError，修正尾部后2项PASS；原生Windows/学习入口4PASS。全部原始失败记录保留。远端Actions以发布后实际状态为准。 |
| 数据保护 | 1541受保护文件、1177原图、937条Reference完整记录SHA均未变，日用HEAD和原dirty状态未变；无main合并、日用切换、Notion写入。 |

### 实跑发现与修复

1. 隔离runner把`LAB_COLLECTION_HISTORY_DIR`固定为当前隔离库，旧history_roots只扫received，首次只得到165个指纹。保存失败后停自有监督器，泛化为各显式历史root读取自身UTF-8 BOM runtime配置及assets。1177/1177正式原图全部纳入，总路径1365、修后实际唯一指纹1303；不扫描未声明工作树，不改算法/阈值。修后运行源码SHA256为13481264947f887fa80c7533c27b56a3d4572492557a8e4e7c0f8cde7bd085c2。
2. 独立审查实际打开6份参照图并核对回执，三份SourceAssessment均为insufficient。直接原因之一已证实：原HTML声明GBK，却被强制UTF-8替换解码，前三页分别产生1891/3605/758个替换字符；不能据此说原站不是官方或这些CG没有识别价值。停止继续消耗坏输入后，修共享字节解码边界，BOM优先、HTTP/meta声明、GBK/GB2312归一GB18030，非法输入严格拒绝；参照恢复和缓存重新解析对比，解释改变时保留原判断并拒绝静默复用。5项反例先FAIL、修后76项PASS。四份实际原字节重读均无替换字符，research原文件账本不变。没有在修后重新发起整批或把旧insufficient改成可信。

最终交付运行源码SHA256：**e32a67228c8b3be787c2e9037637043e84618949a81c2c25f23fde1baf357565**。模型、摄影视觉提示词、accepted、角色/服装核验、完整needs_supplement及schema3的冻结AST均保持。编码修复后的新参照模型重评、完整20图成功闭环与正常无中断性能仍未验证；本轮停止，不自动展开下一轮。

### 实际资源与独立样本

18次模型尝试：NamePlan 1、ReferenceDiscovery 6、SourceAssessment 5、CollectionVision 6；14份SUCCESS、2次临时网络ERROR、2次中断无终值。摄影为5个逻辑调用、6次CLI尝试；3个补证请求，参照检索6、来源页4、参照图片获取7。可观测Token合计369585，另2次中断无usage，不能报告完整Token总额。记录的history_index累计103.188秒、reference_prepare 674.781秒、browser_search 20.484秒、browser_receive 144.548秒；包含并行重叠及被硬中断而缺终值的span，不能简单相加为总wall。

独立审查者打开全部5张摄影原图：3份原预测均为身份uncertain且未准入，另2份仍未完整核验，造型差异/身份疑点保留；没有通过图可作首/中/末抽查。原AGY判断、失败、原图及K/I/M/X未被改写。最终独立结论同为BLOCKED_WITH_EVIDENCE。

### 复核入口与命令

工作目录为本ROOT worktree。验证解释器为`C:\Users\Dell\AppData\Local\Programs\Python\Python312\python.exe`，仓库`.venv`复用相同已安装依赖。重跑以下是离线/合成边界，不启动新20图：

```powershell
python -X utf8 -m pytest -q --basetemp "D:\AI PROJECTS\photography-reference-lab\.local\review-encoding" tests/test_automatic_references.py tests/test_reference_cache.py tests/test_collection_finalization.py tests/test_collection_controller_recovery.py tests/test_collection_receipt_budget.py
python -X utf8 -m pytest -q --basetemp "D:\AI PROJECTS\photography-reference-lab\.local\review-job" tests/test_collection_job_recovery.py tests/test_collection_runner.py tests/test_imports_jobs.py tests/test_collection_ui.py tests/test_collection_local_finalization.py
python tools/benchmark_collection.py replay --baseline "D:\AI PROJECTS\photography-reference-lab\.local\agy-autonomous-20261019" --output .local/new-readonly-replay
node --check web/app.js
git diff --check
```

编码修复后再次只读回放25份原图/原回执：25/25预测及顺序一致、18准入，0新模型/浏览器；4份一手参照缓存验证仍可复用。计时为本地paced replay，不能冒充真实网络提速。

私有证据在`.local/finalization/`：trial-freeze.json、trial-repair1.json、trial-history-defect.json、html-encoding-original-bytes-proof.json、trial-run-summary.json、trial-closure-proof.json、ui-final-metrics.json、ui-final-debug.json、ui-final-blocked.png、daily-protection-final.json及各原始JUnit。隔离页面`http://127.0.0.1:18783/#view=jobs&project=231166a98a5a4c1d8517b717e5d69407`可看受阻状态；原日用18765未切换。Git-only目标为`codex/collection-finalization-20261019`，确切commit/远端SHA及禁用Notion的结果以原始Publisher回执与主对话为准。
