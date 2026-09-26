# 2026-09-27：个人审美库与轻量筛图工作流

## 用户意图（实现前记录）

> 图片首先是独立资产；搜索角色只是发现上下文。第一轮只负责审美筛选，不当数据库管理员。
> 独立的“我的审美库”；本角色参考 / 通用灵感 / 待定 / 淘汰；一张精选图对应一张现场卡，不强迫所有保留图制卡。
> BrowserSkill + Codex / Antigravity 为默认采集路径；不配置独立 OpenAI API；不编造图像事实、平台实测或人工确认。

交付分支 `codex/reference-library-rebuild`，起点 `b95f37540ada1bae18de949873bdbbcce021e621`。已读 AGENTS、README、ARCHITECTURE、WORKER_PROTOCOL、CODEX_REGRESSION、最近任务和 PR 记录。

## 实际改动

- 保留原有 SHA-256 图片存储与项目引用；新增独立 discoveries、asset_observations、inspirations。发现意图、图像观察、角色使用关系与审美反馈分离。角色匹配不是可向其他角色继承的图片事实。
- SQLite schema 1 → 2 事务迁移，升级前通过 SQLite backup API 备份包含 WAL 的数据库；旧选择、版本号、卡片、反馈、笔记、别名和图片原字节保留。旧 inspiration 收藏进入全局审美库；重复导入不重置选择。
- 大图浏览器保留缩略图节点，局部更新选择与详情；可见项不乱滚动，变更列表时维护锚点。72 张样本测试点击、前后图、K/I/M/X、两种自动下一张设置；65 张样本测试跨页和刷新定位。
- 首层四个审美动作，来源、人工纠错和手动制卡折叠。全局审美库无项目也能上传，同一图可被多个角色引用；重复引用不覆盖已有选择、不继承角色判断或现场卡确认。
- 淘汰立即退出默认流；恢复回到原选择但不复活旧确认。清理默认 dry-run，须显式 apply，至少等待 7 天；保护其他项目、全局收藏、笔记和未结束分析任务，保留审计元数据，不删除仓库历史素材。
- 制作现场卡 → Agent 任务 → 分析 / 草稿 → 用户单独确认。分析允许 card:null；图片不合适时不强行制卡。一图一卡，只有用户明确确认才能进入现场卡；改变相关要求会撤销旧确认。
- 默认 BrowserSkill 任务包包含冻结的完整角色、作品、版本、自由要求、器材、本轮要求、三类发现意图、来源计划、搜索策略、结果 schema 和 AGENT_TASK.md。支持网页和 CLI 导入结果、部分分析结果续传、过期快照拒绝、来源阻断与缺口回执。网页不自动启动本机 Agent。
- README、ARCHITECTURE、WORKER_PROTOCOL、CODEX_REGRESSION 与真实实现同步；旧 collector / API analyzer 只留在兼容说明，正常工作流无需 API 密钥。

## 回归结果

完整命令：`python -m pytest -q --junitxml=test-results/results.xml`。

GitHub Ubuntu / Python 3.13 / Chromium 实跑：**101 passed，0 failed，0 errors，0 skipped，124.12 秒**。有 1 条第三方 Starlette TestClient 的弃用提示，不是跳过或失败。JUnit 与日志已下载核对，不以传输脚本退出码代替测试结果。

| 测试范围 | 通过数 |
| --- | ---: |
| 原有后端四组测试 | 64 |
| 新增个人审美库 / 迁移 / 任务 / 回收回归 | 20 |
| 真实 Chromium 组件测试（显式 TestClient 桥接） | 10 |
| 实际 Uvicorn HTTP / Cookie / 上传下载 / 离线流程 | 5 |
| 真实历史素材迁移及 HTTP 页面流程 | 2 |
| 合计 | 101 |

执行证据：[正式代码常规 CI run 36263974310](https://github.com/laohan1126-lang/photography-reference-lab/actions/runs/36263974310)，三个 job 全部成功，代码 checkpoint 为 `28f63d639d8c1697ad88fcb0199c3f02f893b420`。本验收记录是之后的纯文档更新。

单次 101 项测试的隔离快照为 `23a34588b4de599b56ad2f9b9c92e67608ced739`，文件树 `56daee6955a4870fe79dedf80e34437920a63c94`。其测试通过，但临时验证分支回推遇非 fast-forward 拒绝，未强推；随后按顺序提交到上述正式 checkpoint，整个文件树完全一致，并再次通过常规 CI。

本地另跑：后端 84 passed；组件 10 passed；`node --check web/app.js`、`python -m compileall -q ref_lab tools tests`、`git diff --check` 通过。常规 CI 的 Python 3.11 / 3.13 后端矩阵与 Python 3.12 的组件、HTTP、历史素材测试均通过。

### 历史数据核验

第一次实际迁移：435 created / 53 existing / 0 missing / errors=[]；第二次 0 created / 488 existing，幂等成立。共有 435 独立 Asset、435 Reference、488 导入别名。原选择 keep 47 / pending 255 / reject 133 全部保留；正常候选流为 302，不含淘汰项。

实际构造 schema 1 历史数据库后升级到 2，逐项核对旧记录选择、revision、来源、旧反馈、别名，以及全部 435 张原图 SHA。doctor：数据库正常、外键错误 0、损坏或缺失原图 0、缺失缩略图 0。未添加任何虚构图像观察或现场卡，未修改历史图片。

### 实际 UI 与离线核验

真实历史图通过 Uvicorn HTTP 与 Chromium 会话登录显示：缩略图节点 / 已可见项位置保持 → 通用灵感 → 全局审美库 → 第二角色引用 → 淘汰 / 恢复 → 建立等待 Agent 的制卡任务 → 刷新保留选择及任务。没有复制图片文件；390px 视口无横向溢出。

明确合成样本通过真实网页下载分析任务包、校验独立原图 SHA、上传分析 JSON；用户确认前 ready=0，确认后 ready=1。下载离线包后，断网 Chromium 以 file:// 打开，图片可见，口令、现有器材方案与 PS 路线完整。改变要求撤销旧确认。**这些是流程和门槛验证，不是 AI 看图准确率证据。**

### Loop 中发现并修复

基线实际复现缩略图 scrollLeft 从 3100 回到 0，节点整体被替换；改为稳定节点局部渲染。随后修复淘汰时中间状态短暂选回首图、图像加载错误后恢复仍被隐藏、旧执行器重复提交任务完成等问题。

第一轮完整 HTTP 测试为 95 passed / 5 failed：Playwright 的页内等待循环被严格 CSP 阻止。改用有截止时间的测试侧轮询，并新增 CSP 回归；没有放宽网站 CSP。下一轮 100 passed / 1 failed，发现测试仍断言旧任务包文件名；改为验证实际 AGENT_TASK.md、任务 ID 与禁止代替用户确认的指令。最终完整 101 项通过，没有删掉失败用例或改成 skip。

## 环境与未验证边界

本机 Codex 连接失败；隔离容器的 git fetch origin 因 GitHub DNS 失败，无法检查用户电脑未提交工作。使用授权 GitHub 接口读取分支和历史，再以可校验 git bundle 在隔离副本工作；没有访问或覆盖用户日用数据库。容器浏览器被管理策略阻止访问本机 HTTP，因此组件桥接与 GitHub runner 的真实 HTTP 测试分开记录，没有绕过策略。临时传输文件不进入产品分支。

来源匿名探测记录在 SOURCE_ASSESSMENT：小红书登录入口、Pinterest / X 403、Instagram 429 后停止、Curecos 与微博受限；Cosplayers Archive、FilmGrab、ShotDeck 仅验证可见入口。**未完成用户登录态 BrowserSkill 多平台搜索和下载验收；不能称这些网站全部接通。**

未验证：用户 Windows 实机、实体手机离线使用、用户本地最新私有数据、真实 Agent 对照片的分析质量、实际登录态搜索质量、PS 自动操作和公网部署。本轮没有独立 OpenAI API 调用、付费订阅、自动部署或 Notion 写入，也没有把真实历史图硬标为已核验 / 已确认现场卡。

## 用户验收入口

沿用原 LAB_DATA_DIR，升级前做完整备份。进入项目“挑参考”，把缩略图滑到后段，点图和 K/I/M/X，切换自动下一张；淘汰后观察立即消失，再从“已淘汰 / 恢复”找回。点“通用灵感”后到左侧“我的审美库”，引用至另一个角色，检查两个项目选择互不覆盖。

在“角色精选”只挑一张“制作现场卡”，将任务包交给已配置 BrowserSkill 的 Codex / Antigravity；没有返回结果时应明确等待，导入真实草稿后再单独确认。以这一次真实登录态搜图及逐图分析，补上本轮尚未验证的外部执行质量。
