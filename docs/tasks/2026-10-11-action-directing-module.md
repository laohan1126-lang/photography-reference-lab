# 《动作导演》完整模块与真实协作试点

## 原始意图（实施前记录，2026-10-11）

用户要求：“作为摄影师，我怎样把脑海中的角色画面，变成模特听得懂、做得出来、拍出来有效果的动作？”正式生成一门完整模块接入现有 `/learning`，不能停在教程样板、平行技能树或三个 Agent 的 SUCCESS。

必须真实调用 AGY Headless CLI 研究专业摄影师一手材料；Codex 独立形成事实底稿；真实 CC 完成有边界的网站接入；fresh-context Verifier 实施前冻结目标、完成后独立验收。完整课程最后必须由 AGY CLI 口语化教学润色，再由 Codex 逐差异审核。保留润色前后及实际 diff。不修改通用 Skill/Hook，不替换供应商或增加付费 API。

主要关联既有 `character-4`、`posing-6`、`character-1`，依内容关联 `character-3`、`posing-5` 与 costume 技能。至少有一个非武器场景。问题与折叠解析即可；无填写框、自评表单、保存答案按钮；阅读不改变技能状态。用户亲自试学/实拍效果保持未验证。

## 当前基线与边界

- 实时 `git ls-remote origin refs/heads/codex/evidence-photography-atlas`：`fc6290cc4978529fdd9f58ed6cea02bab736de8a`；本地 HEAD 相同；远端目标分支原先不存在。
- ROOT：`codex/action-directing-module-pilot-20261011`。AGY、CC、Verifier 分别使用 `.local/action-directing-{agy,cc,verifier}` 的独立工作树与任务分支。
- 本地存在其他任务 staged/unstaged 内容。immutable Publisher baseline 已于首次编辑前建立，事务 `01a129cf-ebf9-7202-8aea-f8a5e1843991`，合同七项；不得把 prior dirty 纳入本轮提交。
- 指定旧 Skill 路径不存在；实际已改名，读取 `.agents/skills/codex-multi-agent-orchestration/SKILL.md` 及 external-handoffs、AGY_BROWSER_RUNBOOK。沿用实际接口，不修改 Skill。
- 已阅读前轮协作与权限/手机滚动失败记录、Publisher 历史。保留原失败；本轮是新课程，不继续堆浏览器权限例外。全局配置、私人图库、原图、数据库、浏览器 profile、个人状态均不修改/提交。

## Blueprint 与依赖

现有 Python/FastAPI + 静态 JavaScript 学习平台；复用 course 阅读器、数据生成和来源/媒体结构。先独立冻结验收 → 接口代表操作 → AGY 研究与兼容实现（独立部分可并行）→ Codex 原始证据审核/底稿 → 连续课程 → AGY 全文润色与差异复核 → CC 数据集成 → Verifier 浏览器/事实/回归验收 → scoped Publisher。事实或实现失败定向返工最多两轮。

本轮所有权：ROOT 新建 `docs/research/photography-atlas/action-directing/` 教材/事实/协作/验收记录、此任务文档及最终集成；CC 仅经检查后列出的课程与生成器兼容文件；Verifier 仅独立证据/测试；AGY 仅其 worktree 私有研究与润色输出。关键文件不并发写。精确 CC 范围与冻结标准在后续记录追加。

## 可观察验收

合同覆盖：独立标准事先冻结；真实进程及失败保留；一手案例实际阅读与可见证据边界；观察—指导—复拍—代价完整教学；新情境问题/折叠解析/现场练习；真实 AGY 全文润色及最终事实差异审核；真实 CC 接入、桌面手机可读与旧课程/状态兼容；实际相关回归；五项指定交付与可运行入口。独立标准将在 Verifier 产出后记录 hash，不因实现结果修改。

优先至少两位独立摄影师、争取真实可见调整过程视频。受阻材料注明实际取证人，Codex 取证不冒充 AGY 自主研究；原话、作者解释、可见观察、项目推论、未知条件分层。未转载原始视频/商业图片或私照进 Git。

## 结果（待追加）

此处尚未宣称实施、验收或发布成功。日用服务不重启；预览使用独立学习数据。最终 Git/Notion 以真实 Publisher 收据分别报告。

## 实际实施与验证追加（2026-10-11）

- 独立 Verifier 于实施前冻结 AD-01 至 AD-15。原始 JSON SHA256：`a762419dfd97e1754b6a10a84dc7ff095d6c976c4a33b2f751498e4e0a2aacfe`；MD：`bd9e02617861cbaf3907edcdfecfb9071f3e80fda455cd24114da64295ec5e69`。冻结未因失败修改。
- 真实任务进程 AGY 四次、CC 三次；研究权限拒绝、CC 首轮 turn 上限、AGY 首次润色的 provider ERROR 与事实问题均保留。Codex 自行通过合法浏览器核对 Lindsay Adler 的五个主要调整帧及额外定位、Jerry Ghionis / Westcott 两幅原图与教程原文，Verifier 另开浏览器独立重查。没有把 Codex 取证计为 AGY 自主研究。
- 最终课程八节、三来源、三案例、十六个既有技能关联；非武器情境为宽袖持信、图书馆持书及受限座位/手套等迁移练习。问题和折叠解析沿用只读阅读器；没有新增填写/保存/自动掌握。保留完整润色前稿、实际 AGY 最终响应、润色后稿、最终教材及两段真实 diff；ROOT 另审核三处条件/归属措辞。
- CC 八文件接入经 ROOT 检查后整合：`web/learning.js`、`web/learning-gateways.js`、`ref_lab/learning_preview.py`、`ref_lab/api.py`、`ref_lab/action_directing_media.py`、`tools/validate_learning_gateways.py`、`tools/build_action_directing.py`、`tests/test_action_directing.py`。附加包缺失、合法 JSON 但结构无效、引用/ID 冲突均在合并前拒绝，旧课程继续可读；图片 CSP 仅增加两条核验原图精确 URL。
- 两轮定向返工分别修 CC 与 AGY。独立相关回归发现旧 CSP 断言 48 passed / 1 failed；用户随后明确“允许这一次单点修正”。ROOT 只修 `tests/test_learning_gateways_ui.py` 的旧断言为精确 token 集合，并保护私人首页 CSP；ROOT 1 passed，Verifier 独立复跑 1 passed（1.45s）。不隐藏失败或算作原两轮以内。
- ROOT 实际执行：新课程与旧课程两组共 23 passed（45.90s）；默认六文件回归 123 passed（73.97s）；技能/状态/UI 兼容 28 passed（77.69s）；三个 JavaScript syntax 检查、基础 atlas --check、新增课程 --check、来源结构校验和 `git diff --check` 均通过。此前 IndentationError、basetemp setup errors 与 CSP 失败另在协作/验收报告保留，不计为通过。
- 实际课程入口：`http://127.0.0.1:18772/learning?course=action-directing-module`，ROOT preview 真实 HTTP 200；独立浏览器检查桌面、390px 手机、原图及展开解析，隔离数据回归验证零状态写请求/原学习记录不变。日用 18765 服务未重启。需重新打开时运行 `.venv/Scripts/python.exe -X utf8 tools/preview_learning.py --port 18772 --reference-url http://127.0.0.1:18765/`。
- 最终独立逐项结论见 `docs/research/photography-atlas/action-directing/ACCEPTANCE.md`。用户亲自试学、现场复拍效果、他人审美接受与流程推广仍未验证；不新增 Golden Path，不批量生产其他课程。
- Git/Notion 将由本事务 canonical seal/finish 生成真实收据。Publisher 的空暂存区硬门禁发现六项其他任务 staged 内容；需要单独授权临时保留其 staging、发布后逐 blob 恢复，不能从既有 task-branch push 授权推断可改其他任务暂存区。不以换 index 或修改 Publisher 绕过门禁。

## 独立终验与发布准备追加

Verifier 已交付原冻结十五项 PASS（仅可观察工程、来源事实与协作证据）；独立默认 123 passed，相关首次 48 passed / 1 failed 后获授权的该例 1 passed，桌面/390px 只读回归 2 passed，目录/教材/来源 30 passed / 1 Windows symlink 环境 skipped。原报告、结构化结论、五份 XML、二十八份原始回执哈希审核和原始进程审核已逐字节复制进入正式课程目录，未纳入任何图片或原始事件日志。

独立测试 `tests/test_action_directing_acceptance.py` 原样集成（SHA256 `a347c4c3e52198741dc274bac2c3b1d018661bb5798774f52593e016ffc5a625`）；ROOT 实际复跑 2 passed（14.57s），无业务改动或新增返工。重复执行先创建 ignored `.local/verifier`；准备和入口说明见 `ROOT_INTEGRATION.md`。

用户对暂存区追加明确授权：“允许，发布后原样恢复暂存内容”。该授权覆盖保存在项目 ignored 目录的原 index 备份、仅六项其他任务的精确临时 unstage、在核对本事务提交身份/范围后恢复原 blob/mode/stage 和重命名状态；不覆盖改动其他工作文件、丢弃部分暂存、替换 Publisher 或全局权限。Git/Notion 最终结果以事务保存收据为准，此段不预称推送或同步成功。

ROOT 首次暂存保护预检在 seal 前停止：`git reset HEAD -- <精确其他任务路径>` 重新将两个工作区已缺失的旧重命名源列入 tracked snapshot，导致“缺失 key”与“值为 None 的缺失文件”字典比较误报。finally 已恢复全部原 blob/mode，cached raw 与全部工作文件哈希完全一致，HEAD 不变、事务仍 STARTED、无 sealed manifest 或外部提交。根因是混淆索引成员与实际文件内容；恢复前只读复核后，比较改为按全部路径 `.get` 检查同一缺失/哈希状态（与 canonical snapshot delta 同义）。原备份/失败证据保留，下一次前置恢复只允许这个已确认的 pre-seal 状态；不新增 baseline，不修改 Publisher，不视为课程第三轮返工。

## 最终发布阻塞

第二次明确 pre-seal 恢复后，canonical seal 实际返回 `WORKSPACE_BRANCH_CHANGED`（exit2）。ROOT 在原研发分支先 start，再切本轮任务分支，导致不可变事务的分支绑定与当前分支不同；这是 ROOT 初始化顺序错误。标准 recover/未完成事务 bind 不提供分支迁移，不能重采晚基线或修改既有 state/baseline，不能借原分支完成错误目的地发布。当前 HEAD 未变，没有本轮 commit/push/Notion 写入。六项其他任务原 staged blob/mode/stage、cached raw 与工作文件哈希已再次完整核对恢复，详见 PUBLISHER_STATUS.md。本轮工程已验收，R7 正式发布仍阻塞，最终不宣称完整任务或正式发布完成。


## 干净工作树恢复交付意图（2026-10-11）

用户明确授权“允许新建执行聊天并完成发布”。本聊天 ROOT 只恢复已经验收的《动作导演》交付，不生成或润色课程，不增加业务返工。

- 新工作树：`C:/Users/Dell/.codex/worktrees/cf7c/photography-reference-lab`；先从干净 detached HEAD 正常切换至 `codex/action-directing-module-upload-20261011`，再 start。
- 当前真实 session：`01a12a53-9264-7253-b14a-fece913af68a`；turn/任务：`01a12a53-9aa7-7e73-b42b-f97b89d70546`。canonical start 已在任何复制/编辑前完成，基线 HEAD `fc6290cc4978529fdd9f58ed6cea02bab736de8a`，dirty/index 为空；不可变 fingerprint `d95fa80b7d47f2803cb3eaa0b9de8f972fe807b98f36b37272100899470c1016`。
- 新合同 R1–R5：精确复制并核验 41 项；在当前 clean baseline 实跑相关回归；验证旧课与桌面/390px只读状态；保护源索引/文件与日用服务；准备精确 scoped Git/Notion 交付并分别记录真实结果。delivery Git/Notion 均明确授权，外部写文件清单为空。
- 源仓库仅只读，复制清单为源 manifest 的40项加 PUBLISHER_STATUS.md；原字节/hash清单保存在 ignored `.local/action-directing-upload/source-sha256.json`。仅本任务文档及已有发布报告允许追加恢复记录，其余文件必须与源逐字节相同。
- 保留旧 WORKSPACE_BRANCH_CHANGED、tracked-missing 索引预检误判及两次完整恢复历史；不修改旧事务、baseline、Publisher、全局配置或授权注册，不使用另一 Notion 目的地。
- 验收以本工作树实际运行结果为准；旧 AGY/CC/Verifier 来源与进程证据仅原样保留，不声称本次重新执行。真人学习、审美与实拍迁移继续未验证。
- 目标远端初检：GitHub gh API 对上传分支返回明确 HTTP404；原 evidence-photography-atlas 仍为基线 SHA。标准 Publisher seal/finish 后再核对 commit父SHA、精确路径/hash和实时远端SHA。


## 新工作树恢复验证与封存前状态（2026-10-11）

本次仅恢复正式交付；旧失败历史及来源/Agent/润色/独立验收证据原样保留，不声称重新执行 AGY/CC 或重新观看来源。新事务位于正确的任务分支，并在首次复制前建立。

- 41 项复制时全部逐字节相同；除任务文档和本发布报告仅追加记录外，其余39项保持源SHA256。冻结标准 SHA `a762419dfd97e1754b6a10a84dc7ff095d6c976c4a33b2f751498e4e0a2aacfe`、独立阅读测试 SHA `a347c4c3e52198741dc274bac2c3b1d018661bb5798774f52593e016ffc5a625` 均未变。独立只读审计确认精确delta为41项，16个既有skill引用齐全，无需源仓库其他dirty依赖。
- 当前实际回归：默认六文件最终 `123 passed`（79.99s）；`test_action_directing.py`、`test_action_directing_acceptance.py`、`test_learning_course.py`、`test_learning_course_ui.py` 共 `25 passed`（91.02s）；`test_learning_state.py`、`test_learning_ui.py`、`test_learning_gateways_state.py`、`test_learning_gateways_ui.py` 共 `43 passed`（174.52s）。三组最终191项通过，XML/完整命令/日志存于 ignored `.local/action-directing-upload/`。
- 首次并行默认回归真实 `122 passed / 1 failed`，失败为 `test_real_process_is_stopped_on_cancel` 期望 `attempt_superseded`、实际 `adapter_or_result_error`。隔离DB收据记录 `PermissionError`；该路径代码与测试均为HEAD原样，异常具体发生位置未证实，不称已修复或直接认定为flaky。所有并行UI结束后该例独跑 `1 passed`（2.94s），再串行复跑完整默认六文件得到上述123通过；首次失败XML/log保留。已有9月30日、10月5日Windows取消风险历史已复核。
- 三项 `node --check web/learning.js`、`web/learning-gateways.js`、`web/app.js` 通过；`tools/build_action_directing.py --check` 与 `tools/build_photography_atlas.py --check` 通过，基础地图14/71/247保持；`git diff --check` 通过。import路径实测为本新工作树。现有D盘venv以ignored junction复用，没有安装软件或新依赖。
- 新桌面1440px/手机390px实际阅读回归通过：八节、三折叠问题、无填写/保存控件，旧课程可读，阅读期间零写请求及已有学习文件字节不变，过期写409、课程写404仍有效；图片主动中断只验证失败回退，不能作为来源图像准确性证明。ROOT另查看本次390px截图；不计为用户审美验收。
- 源仓库1493个tracked/untracked文件hash、HEAD、branch、index与cached raw/status哈希在复制前后及测试后均一致；源staged内容不操作。日用18765服务/数据及原18772预览不重启、不改动。
- 默认 `git ls-remote` 本次20秒超时，结果未知，失败checkpoint保留。采用现有授权 `gh auth git-credential` 仅对子进程的Git配置后，查询1.26秒exit0，上传分支无ref；与明确gh API HTTP404相符。不会改全局认证设置或绕过Publisher push guard。Notion保持有效配置指定的数据源与HKCU用户环境凭据，不选择其他目标。
- 本次先review旧 `DEFERRED/BLOCKED` 原事务（无manifest/commit/push/Notion），保留其fingerprint及收据，不改绑/重采。清洁工作树使本轮无需暂存区保护脚本或临时unstage。未修改Publisher/Skill/Hook/权限/provider，未增加业务返工。
- 封存前实际状态：Git/Notion尚未执行；将在相同事务canonical seal/finish中提交精确41项并运行配置mandatory checks。此报告此后不修改，以saved receipt和额外实时commit/远端SHA核验为最终外部结果。真实收据路径：`C:/Users/Dell/.codex/task-finalization-data/tasks/6a2d6ed857c942e5509d45322f6a9946/receipt.json`。
- 未验证：真人学习、审美、实拍迁移；Windows首次PermissionError精确异常来源；旧Hook的实时兼容及WSL。未部署、未合并main。

重复验证：先确保 `.local/verifier` 存在，再运行 `.venv/Scripts/python.exe -X utf8 -m pytest -q tests/test_library.py tests/test_imports_jobs.py tests/test_workers.py tests/test_operations.py tests/test_personal_library.py tests/test_collection_runner.py`；课程/状态/UI按上列文件复跑。原试读入口仍为 `http://127.0.0.1:18772/learning?course=action-directing-module`；本次未重启或改动此服务。


## 第三次干净事务恢复意图（2026-10-11，实施前）

用户明确回答：“允许这项范围变更并继续发布”。本次将交付范围由41项增为42项，仅新增根目录 `.gitattributes` 的单文件空白属性；41项原文件逐字节复制，只有本任务文档和 PUBLISHER_STATUS.md 允许追加。

新ROOT工作树 `C:/Users/Dell/.codex/worktrees/8f1b/photography-reference-lab`；session `01a12a66-b17c-7571-bd9f-77b4850d35f9`，真实turn `01a12a66-b82d-7543-8f43-09905edc120f`。先正常切换 `codex/action-directing-module-upload-20261011`，再在首次复制/编辑前canonical start并声明R1–R6与Git/Notion授权，外部写文件清单为空；HEAD基线 `fc6290cc4978529fdd9f58ed6cea02bab736de8a`，dirty/index均为空。事务目录 `C:/Users/Dell/.codex/task-finalization-data/tasks/bae650ad053038acb6d57c1464486db6`。

范围保留完整八节/三来源/三案例/十六个既有技能与三折叠问题，不重新生成润色、不再调用或冒充AGY/CC重执行、不新增业务返工。源cf7c、原D盘、两旧事务和其index/baseline只读。默认六文件回归先串行执行；所有命令与新树日志保存在ignored `.local/action-directing-upload/`，真人学习/审美/实拍、旧Hook实时兼容、WSL继续未验证。

语义修复前已检查原DEFERRED/BLOCKED分支绑定失败、tracked-missing索引成员误判与两次恢复、cf7c seal后标准finish的55个单空格diff上下文行空白失败。旧事务COMMIT_INTENT没有prepared_tree，不能改旧state补tree。保持全部原diff证据字节，只为该精确路径声明 `whitespace=-blank-at-eol`，其余默认空白检查继续执行。依据：https://git-scm.com/docs/gitattributes#_checking_whitespace_errors 。不修改Publisher/Skill/Hook/全局配置/授权注册，不force push/main merge/部署或重启18765/18772。


## 42项恢复的本工作树验证与封存前状态（2026-10-11）

本段是新ROOT的实际恢复结果，完整保留此前两次发布失败及课程历史，不将旧报告中的191项当作本次执行。源cf7c的41项全部匹配旧sealed manifest expected_hashes；独立只读审计确认39固定项同时与原D盘字节相同，两报告只保留完整源prefix后追加。新增 `.gitattributes` 精确两行，SHA256 `4881d784a0f455dc0054db330fde570e44777c24367877b027e933917d943550`；55条单空格均在真实unified diff hunk中，无其他尾空白，原diff SHA `d73066a2d9650edd0673808c018255b7f12777adc7c0306c2c4469fb46229efd` 不变。规则仅匹配该证据文件的blank-at-eol，其余路径属性为unspecified；该文件以后所有行尾空白也受该语义规则，不能宣称只豁免55个行号。官方依据：https://git-scm.com/docs/gitattributes#_checking_whitespace_errors 。

- 本树串行默认六文件：123 passed（pytest XML 59.643s）；新课程/冻结桌面手机验收/旧课程四文件：25 passed（103.458s）；学习state/UI/gateway四文件：43 passed（154.220s）。合计191 passed，本次无失败/跳过；三个node语法检查、两个构建器--check与tracked diff --check通过。原cf7c首次并行122pass/1fail的取消PermissionError历史仍保留，未定位或修复根因。
- 当前真实命令/PID/UTC开始结束/退出码、JUnit/XML和日志在ignored `.local/action-directing-upload/` 的default、course、state-ui及static result文件中；运行import来自本8f1b树，ignored .venv junction复用现有D盘环境，没有安装依赖。
- 实际1440px与390px只读验收：八节、三折叠问题、无填写/保存控件，旧课程及原笔记保留；阅读写请求0、页面错误0、隔离学习状态字节不变，过期写409/课程写404。ROOT已查看本次390px展开截图；中断媒体只证明失败回退，不证明图片事实或本人学习效果。
- frozen标准JSON SHA `a762419dfd97e1754b6a10a84dc7ff095d6c976c4a33b2f751498e4e0a2aacfe` 与test SHA `a347c4c3e52198741dc274bac2c3b1d018661bb5798774f52593e016ffc5a625` 未变；没有第三轮业务修复。
- 本轮source 1465项文件hash、HEAD/branch/index/cached raw/status及两旧事务baseline/state/manifest/receipt与Publisher/core/config hash前后相同。日用18765与原18772未改动/重启。历史failure-checkpoint的index hash与本轮起点不同；本轮起点与当前源index同为 `f8bc37946110f40e2861d3674e53f5c74421056096983c76572e71b8b715a742`，不以跨历史元数据差异推定本次写入。
- 当前process-only gh credential helper的实时ls-remote exit0，用时1.55s，授权上传分支无ref；旧默认GCM超时历史不抹除。有效Notion仍为既有verified data_source与Windows HKCU用户环境凭据，目标/配置不改动。
- 独立只读no-index空白对照：源exit3/55条错误，目标exit1/0条错误；exit1只是内容差异。完整42项尚将在本ROOT自己的标准index进行精确stage/check/blob dry-run，并只unstage本42项、保持工作字节；标准canonical finish仍自行执行全部配置mandatory checks与空白guard。
- 封存前Git/Notion尚未执行；本报告封存后不再追加外部结果。当前新事务目录 `C:/Users/Dell/.codex/task-finalization-data/tasks/bae650ad053038acb6d57c1464486db6`，savedreceipt `C:/Users/Dell/.codex/task-finalization-data/tasks/bae650ad053038acb6d57c1464486db6/receipt.json` 与ignored后验检查将给出实际commit/push/远端SHA和Notion身份/内容读回结果，分别报告；不预称发布成功。
- 验收状态PARTIALLY_VERIFIED：真人学习、审美/实拍迁移、旧Hook实时兼容、WSL、旧PermissionError具体异常点未验证。本次无新的AGY/CC或来源视觉重执行，不部署、不合并main。

重复回归：先创建ignored `.local/verifier`，以本树 `.venv/Scripts/python.exe -X utf8 -m pytest -q` 按上列default6、course4、state/UI4顺序串行执行；再node3/builders2，完整42项空白检查参看ignored preseal-check。旧试读服务入口仍为 `http://127.0.0.1:18772/learning?course=action-directing-module`。
