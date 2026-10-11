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
