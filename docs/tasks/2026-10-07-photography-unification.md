# 摄影项目合并与副本清理 — 2026-10-07

## 用户意图与边界（实施前）

用户已认可摄影学习 UI 与另一对话的 Drive 导入工作，要求：“现在把这个项目合并一下……两边我已经比较满意了……我看到那个文档里面有五个，把它们合并了，然后把多的给我删掉。”

- 将摄影学习、拍摄参考与 Dot 待筛入口合到一个正式本地项目及启动入口；保持已验收的视觉和人工筛选语义。
- 检查五个并列的 `photography-reference-lab*` 目录、它们的 Git 历史、未提交内容、数据与运行依赖。先合并验证，再备份并清理已确认冗余的目录。
- 保存原图、来源、人工选择/笔记、数据库与各分支独有工作。学习页 mock 内容仍为 UI 示例，不迁入真实图片的事实或分类。
- 不重构数据库，不重新下载 Drive 图片，不重新判定审美，不删除历史分支或无关项目，不推送/发布/改域名。
- 首次扫描发现主仓库有 `pyproject.toml`、`web/styles.css` 的行尾变化及未跟踪 `%SystemDrive%/`；备份并保留，不把它们当成待删副本。

## 工程简报

- 技术栈：Python / FastAPI、SQLite、本地原生 HTML/CSS/JavaScript、Windows PowerShell 启动器，继续使用现有环境。
- 合并主目录：`D:\AI PROJECTS\photography-reference-lab`；基线 `e4aa915`。学习分支 `ffb0bca`，收敛分支 `8c50426`；三个辅助分支需核对已收敛范围。
- 预计改动：冲突处的 API/static 入口、前端导航、文档与针对性回归；复用原有运行和备份工具。
- 私有文件：原图、数据库、运行配置、清理备份和截图均留在 Git 之外。
- 风险：不同库可能有独有人工操作；外部启动器可能仍依赖旧目录；合并期间不能让旧代码打开更新后的数据库。遇到冲突保存两边证据后再选择。

## 可观察验收

1. 单个本地主入口同时提供拍摄参考、238 条 Dot 待筛候选及摄影学习；两个摄影分支可以往返，刷新仍可返回。
2. 10 个学习专题、透视详情、灯箱与最近学习继续可用；人工筛选理由继续持久化并保留 revision 检查。
3. 合并前后原图哈希、真实资料库的用户业务行和来源不丢失；完整性与历史问题单独记录。
4. 核心、合并相关 API/UI、真实 HTTP/浏览器检查实际执行；桌面和手机尺寸截图检查，无假成功声明。
5. 待清理目录有逐文件备份清单及校验；精确路径确认后才删除，正式入口不再依赖这些目录。

## 结果与限制（实施后追加）

### 已完成的合并

- `26dd24b` 合入参考库收敛主线，`2ae33a3` 合入已验收学习 UI，均保留双亲历史。collector/runtime/state 三条辅助分支的七个补丁经 `git cherry` 核对，均在收敛主线已有等价实现；不重复合入。
- 解决 service 初始化、前端视图集合/入口、静态资源打包的冲突，保留独立 Dot 待筛与图库、学习页面。学习入口统一为 `/learning`，不再依赖 18766/18767 服务。
- `d05595d` 补充同源导航和 study-only 不进入自动分类的回归。`e61603b` 接入只读预演、冲突阻断、只生成新文件的 SQLite 三方合并工具。
- 保留主目录现有 Python、原图、运行配置与未跟踪 `%SystemDrive%/`。两份既有行尾修改原字节保存于私有备份；规范化索引后确认无实际代码差异，未作为独立功能改动提交。

### 真实数据与保全

共同基线可追溯到 2026-10-06 复制库前的快照，三处旧备份 SHA 相同。主库相对基线只新增 Dot 240 assets / 238 candidates / 239 events；收敛库保有后来的人工作业与 AI 搜索注释。

停掉三个已核实归属的摄影进程后，完整备份日用 data 与四个候选旧目录，逐文件 SHA 校验，并保存 Git bundle。私有证据位于 `backups/unification-20261007/`，含 `archive-summary.json`、每目录 manifest、base/current/incoming SQLite 快照、原启动记录及 `all-branches.bundle`。不跟随 `.venv` junction，链接指向的主目录环境保留。

三方预演零冲突，生成新库后独立核对，再通过 SQLite backup API 恢复到已停止的正式库，未直接复制覆盖 WAL 文件。完整保留 23 projects / 1,131 assets / 891 refs / 238 study candidates；纳入收敛分支的 3 条较新人工选择、1 条筛选会话更新、54 条 AI observations、57 条 annotations、354 条分类队列记录、2 条导航状态及 98 条事件。新增事件重编号，旧事件原样保留；AI 注释仍为 AI 来源，学习 mock 标签未写入业务数据。

1,131 个原图及衍生图均完整。原有 72 条外键错误原样存在、没有增加。`doctor` 会写状态，故在独立 DB 副本上运行：完整性 ok、丢失/损坏原图和衍生图均 0，发现并重建 47 个旧派生状态；这次合并没有把其派生重建覆盖到用户原始行，也没有宣称 doctor 全绿或顺带修复历史外键。

### 本轮实际验证

- 核心六组 + Dot/runtime/state/classification/library-browser/collection-contract/adapter/candidate/boundary：`287 passed`，156.56s，1 条既有 Starlette 弃用警告。命令和 XML 位于 `.local/unification-tests/backend.xml`。
- UI/component/gallery/HTTP/history 全组初次 `45 passed, 4 failed, 2 teardown errors`。失败为学习 fixture 漏复制新图库脚本，以及旧测试仍期望 18767；补齐 fixture、改为验证同源往返。随后 learning + Dot + entrance 聚焦检查 `13 passed, 2 failed`，仅新 URL 断言漏写原有 `#map`；修正后入口两种尺寸 `2 passed`。最终受影响的学习/待筛/入口用例全通过，未改产品行为凑测试。
- 三方合并合成回归 `11 passed`；独立复审补足重复内容事件按出现次数保留、两侧删除基线事件的冲突报告。真实输入没有内容重复事件，98 条均保留。
- `node --check web/app.js`、`node --check web/learning.js`、Python compile 检查通过。整个合并范围的 whitespace 检查同时修正一份收敛文档原有多余末尾空行。
- 正式主目录启动器实跑 `scripts/launch.ps1 -NoOpen -NoWait -SkipExternalServices`；runtime 返回的代码与 data 均为主目录。验收时临时关闭自动分类，未改变持久配置。
- 在实际 `http://127.0.0.1:18765` 服务用 Chromium 检查 1440/390 两种宽度：10 专题、研究笔记、灯箱、最近学习、双向往返各两轮、238 待筛、三项筛选理由和图库图片加载均通过；0 脚本错误、0 横向溢出、0 业务写请求。已查看实际截图，保留已验收视觉。
- 实际证据：`.local/unification-tests/{data-merge.json,adoption.json,doctor.json,live/navigation.json,live/unified.json}` 及 `live/` 下截图。截图检查首次对图库屏幕外懒加载图等待未结束，修正检查脚本为显式 eager 后通过，产品懒加载未改变。

### 清理范围（已备份，待精确路径确认）

保留正式目录 `D:\AI PROJECTS\photography-reference-lab`。四个可移除副本已经过全量备份、逐文件比对与 Git 干净检查：

1. `D:\AI PROJECTS\photography-reference-lab-convergence-20261004`
2. `D:\AI PROJECTS\photography-reference-lab-convergence-collector-20261005`
3. `D:\AI PROJECTS\photography-reference-lab-convergence-runtime-20261005`
4. `D:\AI PROJECTS\photography-reference-lab-convergence-state-20261005`

清理预演记录为 `backups/unification-20261007/cleanup-plan.json`。保留 Git 分支和备份；不清理 C 盘独立 Git stub、其他摄影/Notion 项目、用户未指名的历史资料或工具配置。隐藏开发工作树不属于此次五个并列目录的清理范围。

实际删除结果将在用户确认这些精确路径后追加。本地集成不等于外部发布；未推送、未同步 Notion、未改域名，手机公网连通与真实平台采集不在本次验证范围。
