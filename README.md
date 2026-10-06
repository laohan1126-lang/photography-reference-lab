# Photography Reference Lab · 参考实验室

个人 Cosplay / 日常人像摄影参考库：**搜一批独立图片 → 快速挑选 → 留住审美 → 给少数真正想拍的图片制作现场卡**。不是企业素材后台，不以接单变现为前提。

## Dot 摄影参考待筛入口

侧栏的“待筛摄影参考”独立于角色项目和“我的审美库”。2026-10 的 Dot 批次有 238 幅主候选、240 份原始文件（其中 2 份为同作品兼容副本）；导入后全部保持“待筛”，不自动成为审美收藏或角色参考。编号、Dot 原文、来源、署名和使用限制可在单图页查看。按“动作 / 光线 / 构图 / 环境 / 道具”的筛选仅来自 Dot 文案关键词，**未经逐图视觉复核**，不是图片事实或用户审美决定。用户可逐图改为“优先 / 普通 / 跳过”并记下自己的判断。

私有批次原图、`index.json` 和经审计的 `manifest.jsonl` 留在 `.local`，不提交 Git。需重跑时先用 `python tools/import_dot_drive_batch.py --batch-dir <私有批次目录> --data-dir <资料目录>` 做校验与预演；核对 238/240 后再加 `--apply`。脚本先做 SQLite 备份，按编号和哈希幂等导入，不覆盖已经做出的人工决定。实际导入与验证见 [任务记录](docs/tasks/2026-10-06-dot-photography-review-import.md)。

## 启动与升级（Python 3.11+）

### Windows：日常主运行环境

当前推荐的日常路径是 **Windows Python + Windows BrowserSkill + Edge**。不要再让正式启动依赖仓库外的 WSL regression 目录或临时 worktree。

首次安装：

```powershell
.\install.ps1
```

已有资料库时，先把完整备份恢复到一个 **Windows 本地目录**，再显式配置：

```powershell
powershell -ExecutionPolicy Bypass -File scripts\configure-windows-runtime.ps1 -DataDir "D:\path\to\reference-lab-data"
powershell -ExecutionPolicy Bypass -File scripts\doctor-windows-runtime.ps1
.\start.bat
```

启动器会使用当前仓库自己的 `.venv\Scripts\python.exe` 和同一 checkout 下的 `tools\collect_adapter.py`，并拒绝连接一个不受本启动器管理的旧 WSL 服务。若没有配置数据目录，也没有已存在的本地数据库，会直接报错，**不会偷偷新建一个空库**。

只有明确要建立全新空库时才执行：

```powershell
powershell -ExecutionPolicy Bypass -File scripts\configure-windows-runtime.ps1 -DataDir ".local" -InitializeEmpty
```

默认本地端口为 `18765`；可在 gitignored 的 `.local/windows-runtime.json` 中配置，或用环境变量覆盖。停止服务使用 `stop.bat`，它只终止本启动器记录的 Windows 进程树，不会全局杀 Python/WSL。

### WSL / Linux：兼容与开发路径

应用代码仍保持跨平台，可在独立环境中：

```bash
python -m venv .venv
source .venv/bin/activate
python -m pip install -e ".[test]"
python -m ref_lab doctor
python -m ref_lab serve
```

WSL/Linux 兼容环境必须使用**自己的数据目录**。不要让 Windows 与 WSL 轮流打开同一个正在使用的 SQLite/WAL 目录。需要迁移时使用完整 backup/restore，而不是跨运行环境共用数据库。

首次导入仓库历史素材仍可显式运行 `python -m ref_lab migrate-legacy`。已有数据库启动时会按版本迁移；**沿用正确的 `LAB_DATA_DIR`，不要误建空库**。

v0.3 的数据库版本为 2。升级版本 1 前，自动通过 SQLite backup API 生成同数据目录下的 `library-before-v2-*.sqlite3`，然后事务迁移。图片原字节、旧选择、反馈、卡片和版本号保留；这份自动备份只有数据库，完整备份仍需：

```bash
python -m ref_lab backup --output ../reference-lab-backup.zip
```

恢复须停服务，在新的空目录解压完整备份，再用该目录启动并 `doctor`。不要把旧版本代码指向已升级数据库。

## 下一次打开应该怎么用

**拍摄项目 → 挑参考**：角色名必填，作品、服装版本和自由要求选填。独立大图旁只有四个主要选择：本角色参考 **K**、通用灵感 **I**、待定 **M**、淘汰 **X**。左右键切图，可关闭“选择后下一张”。审美笔记、来源纠错、手动编辑藏在次级折叠区。选为本角色参考表示“值得用于这个项目”，并不宣称图中就是目标角色。采集 Agent 的视觉预检会把游戏/动画截图、插画、假人/服装/商品展示、拼图、空场景及高可信错角色从默认真人候选流降到“已过滤候选”；过滤不等于 X，也不删除资产，用户可以恢复。

**我的审美库**与项目平级，即使没有任何项目也能上传收藏。可以长期保存动作、表情、构图、光线、色彩、电影画面等，再引用到多个角色。同一个文件按 SHA-256 只存一份。已有项目选择（包括淘汰）不会因再次引用而被静默改变；一个项目淘汰图片不会删除全局收藏或其他项目的使用关系。

**跨项目复用**不搬图片文件，只改变项目使用关系。单张或临时多选后可以“复制到其他项目”或“转移到其他项目”；新目标项目默认是未选择，不继承原项目的角色判断、preflight、资料卡或人工确认。目标项目已经有同一图片时保留它自己的旧选择。转移/“从当前项目移出”也不是 X 淘汰：原项目关系进入可恢复状态，资产、来源、我的审美库和其他项目引用都保留。

**模特沟通板**使用同一个项目内的临时选择篮。按选择顺序可给每张图写一句“想让模特看什么”，每页最多 4 张并用 contain 方式完整放入画面，不强裁切。1–4 张直接下载 PNG；更多图片自动按 4 张一页生成多张 PNG 并打包 ZIP。沟通板只是拍摄前交流材料，不是现场卡，也不会改变 K/I/M/X。

**角色精选 → 制作现场卡**：只给真正想拍的几张制卡。建立任务 → 交给 Agent → 导入分析草稿 → 检查口令、图像判断与来源 → 单独确认。AI 判断错时修正，不需要先手填所有事实。不是所有保留图都适合现场卡；`card:null` 是允许的有效分析结论。图片、来源、选择或要求改变会撤销受影响的确认。

**现场卡**仍是一图一卡：可说出口的引导、静态和情境动作、摄影师动作、安全降级、可见光线证据、布光推测、现有器材方案、PS 路线和必要的背景需求。项目设置中的“离线拍摄包”包含独立图片和完整静态页面；不依赖现场网络。摄影笔记独立保存，也兼容旧项目笔记与 Notion Markdown/CSV ZIP 导入。

## 默认采集：BrowserSkill + Codex / Antigravity

点“找一批参考”，保存完整角色、作品、版本、项目要求、器材和本轮自由要求，再下载任务包或复制执行提示词。**默认不会自动唤醒本机 Agent，也不会把等待状态写成已搜完**。可选的 `LAB_COLLECTION_COMMAND` 适配器仅在明确配置、点击启动后运行；没有适配器就保留任务包 / CLI 交接，不偷偷换抓图方式。

本地采集有两种能力边界，必须区分。BrowserSkill / 真实视觉 Agent 可以逐张看图并返回 schema 3 preflight；而当前 `tools/collect_adapter.py` 只是严格搜索适配器，没有视觉模型，因此只返回 schema 2 候选包，绝不伪造“真人实拍 / identity match”。日常主路径通过 Windows BrowserSkill 驱动已登录 Edge，优先小红书、再 Pinterest；只有调用方明确传入 `--allow-bing-fallback` 时才允许 Bing 备用检索，绝不静默换来源。适配器会把角色、皮肤/版本和本轮自由要求当作发现约束，并对明确的游戏/插画/商品/求助/教程等文本噪声做确定性过滤；看图才能判断的人台、广告、错角色或构图价值仍交给人工最终审核。搜索 query、标题、URL 和平台召回都只是 discovery context，不能升级成视觉事实。A 角色精准 / B 可迁移动作 / C 审美拓展是**发现意图**，不是图片事实。详见 [执行器协议](docs/WORKER_PROTOCOL.md) 与 [来源评估](docs/SOURCE_ASSESSMENT.md)。

同一数据目录下也可以直接交接：

```bash
python -m ref_lab export-job --job JOB_ID --output job.zip
# Agent 读取包、正常浏览并返回 result.zip，或分析图片返回 analysis.json。
python -m ref_lab import-job --job JOB_ID --input result.zip
python -m ref_lab import-job --job ANALYSIS_JOB_ID --input analysis.json
```

**正常流程不需要独立 OpenAI API。** 不会启动付费调用；旧 `collect` / `analyze` 命令仅为兼容保留，见 [兼容边界](docs/COMPATIBILITY.md)。Pro / Codex / Antigravity 的实际可用能力和额度仍以用户自己的 Agent 环境为准。未连接、登录受阻、结果不全必须如实报告。

## 当前未发布检查点的边界

[2026-09-28 collector 检查点](docs/tasks/2026-09-28-collector-checkpoint.md) 修复固定/静默采集回退、旧导入数量冒充新成功、HTTP 200 被界面误报完成的问题。候选包原始回执与服务端本包导入证据分开，重试和取消保留历史图片。配置接口与明确限制见 [适配器协议](docs/WORKER_PROTOCOL.md#2026-09-28-未发布检查点本地采集适配器)。

**这不是完整候选生产线发布。** 当前增加了可审计的候选 modality + identity preflight 协议、过滤/恢复路径和安全项目回收，但真实图片分类准确率仍必须由本机 Agent 逐图实测，不能由协议测试证明。更完整的 quality preflight、摄影/偏好排序、结束筛选会话、版本化审美画像仍未完成。供应商 CLI 适配器尚需本机实现/接通；未证明真实 BrowserSkill 搜图质量或原生 Windows 进程生命周期。现有分析提供器的固定路径/参数也没有在此 collector 检查点中解决。不要把本检查点直接当成日常库的已验收升级。

## 淘汰、恢复与磁盘空间

淘汰立即从默认候选流消失；“已淘汰 / 恢复”回收视图同时承担本项目的 X 回收与项目引用恢复：X 会恢复淘汰前选择，而跨项目转移/移出只恢复当前项目关系，两者语义不会混为一谈。视觉预检过滤与 X 分开，“已过滤候选”可以人工恢复为普通候选。移出审美库也有独立恢复入口。项目设置中的“删除项目”采用可恢复的软删除：项目从正常列表隐藏，但共享图片、全局审美收藏、其他项目引用和历史记录不物理删除；侧栏回收入口可恢复项目。

默认**不自动删除文件**。需要释放磁盘时先检查清单，再显式执行：

```bash
python -m ref_lab cleanup --days 30
python -m ref_lab cleanup --days 30 --apply
```

最短保留 7 天。只清理明确回收、足够旧、没有有效使用关系的内容寻址文件；保护其他项目、全局收藏、笔记和未结束分析任务引用。元数据、来源与事件保留，不删除仓库历史素材。文件已清理的条目须重新导入相同字节才能恢复；误删恢复还可依赖完整备份。没有明确回收依据的孤儿文件不凭猜测删除。

## 回归与维护

```bash
python -m pytest -q tests/test_library.py tests/test_imports_jobs.py tests/test_workers.py tests/test_operations.py tests/test_personal_library.py tests/test_collection_runner.py tests/test_modality_archive.py tests/test_reference_transfer_board.py tests/test_collect_adapter.py
node --check web/app.js
python -m playwright install chromium
python -m pytest -q tests/test_ui_components.py tests/test_collection_ui.py
python -m pytest -q tests/test_browser.py tests/test_live_system_regression.py
```

组件测试是真实 Chromium DOM，但用 TestClient 显式桥接网络；HTTP、Cookie 和 `file://` 离线测试单列。历史图片测试不填造角色、灯光或授权事实。最新结果和限制见 [本轮记录](docs/tasks/2026-09-27-personal-library.md)、[回归说明](docs/CODEX_REGRESSION.md)。代码任务先记意图、后记实际证据；[AGENTS.md](AGENTS.md) 与 Git 任务记录为协作约定，Notion 仅是显式授权的可选同步视图。

## 私人部署边界

FastAPI + SQLite WAL + 原始图片文件 + 无构建步骤的 Web。默认仅监听回环地址，单所有者使用。数据库、登录口令、浏览器档案和新增私人图片不提交 Git。已有公开 Git 历史无法通过私人页面撤回。公网部署前配置 HTTPS、随机 `LAB_ACCESS_TOKEN`、准确 `LAB_PUBLIC_ORIGIN`、持久卷和备份，参见 [部署说明](docs/DEPLOYMENT.md)。本版本不自动部署、不合并 main、不自动操作 PS、不重绘人物。

详细设计：[架构](docs/ARCHITECTURE.md) · [执行器协议](docs/WORKER_PROTOCOL.md)。
