# Photography Reference Lab · 参考实验室

个人 Cosplay / 日常人像摄影参考库：**搜一批独立图片 → 快速挑选 → 留住审美 → 给少数真正想拍的图片制作现场卡**。不是企业素材后台，不以接单变现为前提。

## 启动与升级（Python 3.11+）

```bash
python -m venv .venv
# Windows: .venv\Scripts\Activate.ps1
# macOS / Linux: source .venv/bin/activate
python -m pip install -e ".[test]"
# 首次导入仓库历史素材；可重复执行，不重置原选择：
python -m ref_lab migrate-legacy
python -m ref_lab doctor
python -m ref_lab serve
```

打开 `http://127.0.0.1:8765`，另一个终端执行 `python -m ref_lab token` 取得本机口令。默认数据目录 `.local/`；Windows 可先运行 `./install.ps1`。已有数据库直接启动会迁移；**沿用原来的 `LAB_DATA_DIR`，不要误建一个空库**。

v0.3 的数据库版本为 2。升级版本 1 前，自动通过 SQLite backup API 生成同数据目录下的 `library-before-v2-*.sqlite3`，然后事务迁移。图片原字节、旧选择、反馈、卡片和版本号保留；这份自动备份只有数据库，完整备份仍需：

```bash
python -m ref_lab backup --output ../reference-lab-backup.zip
```

恢复须停服务，在新的空目录解压完整备份，再用该目录启动并 `doctor`。不要把旧版本代码指向已升级数据库。

## 下一次打开应该怎么用

**拍摄项目 → 挑参考**：角色名必填，作品、服装版本和自由要求选填。独立大图旁只有四个主要选择：本角色参考 **K**、通用灵感 **I**、待定 **M**、淘汰 **X**。左右键切图，可关闭“选择后下一张”。审美笔记、来源纠错、手动编辑藏在次级折叠区。选为本角色参考表示“值得用于这个项目”，并不宣称图中就是目标角色。

**我的审美库**与项目平级，即使没有任何项目也能上传收藏。可以长期保存动作、表情、构图、光线、色彩、电影画面等，再引用到多个角色。同一个文件按 SHA-256 只存一份。已有项目选择（包括淘汰）不会因再次引用而被静默改变；一个项目淘汰图片不会删除全局收藏或其他项目的使用关系。

**角色精选 → 制作现场卡**：只给真正想拍的几张制卡。建立任务 → 交给 Agent → 导入分析草稿 → 检查口令、图像判断与来源 → 单独确认。AI 判断错时修正，不需要先手填所有事实。不是所有保留图都适合现场卡；`card:null` 是允许的有效分析结论。图片、来源、选择或要求改变会撤销受影响的确认。

**现场卡**仍是一图一卡：可说出口的引导、静态和情境动作、摄影师动作、安全降级、可见光线证据、布光推测、现有器材方案、PS 路线和必要的背景需求。项目设置中的“离线拍摄包”包含独立图片和完整静态页面；不依赖现场网络。摄影笔记独立保存，也兼容旧项目笔记与 Notion Markdown/CSV ZIP 导入。

## 默认采集：BrowserSkill + Codex / Antigravity

点“找一批参考”，保存完整角色、作品、版本、项目要求、器材和本轮自由要求，再下载任务包或复制执行提示词。**网页不会自动唤醒本机 Agent，也不会把等待状态写成已搜完**；这是实际任务包 / CLI 交接，不是云端自动调度器。

本地 Agent 使用已安装的腾讯 BrowserSkill，在用户授权的真实浏览器里制定检索计划、扩展中日英关键词、评估多个来源、逐张下载并记录出处，返回候选包。小红书和 Pinterest 优先，其他来源按任务质量选择，不机械维护九个网站的专用爬虫。A 角色精准 / B 可迁移动作 / C 审美拓展是**发现意图**，不是图片事实。来源检查、低产停止原因和数量缺口进入回执。详见 [执行器协议](docs/WORKER_PROTOCOL.md) 与 [来源评估](docs/SOURCE_ASSESSMENT.md)。

同一数据目录下也可以直接交接：

```bash
python -m ref_lab export-job --job JOB_ID --output job.zip
# Agent 读取包、正常浏览并返回 result.zip，或分析图片返回 analysis.json。
python -m ref_lab import-job --job JOB_ID --input result.zip
python -m ref_lab import-job --job ANALYSIS_JOB_ID --input analysis.json
```

**正常流程不需要独立 OpenAI API。** 不会启动付费调用；旧 `collect` / `analyze` 命令仅为兼容保留，见 [兼容边界](docs/COMPATIBILITY.md)。Pro / Codex / Antigravity 的实际可用能力和额度仍以用户自己的 Agent 环境为准。未连接、登录受阻、结果不全必须如实报告。

## 淘汰、恢复与磁盘空间

淘汰立即从默认候选流消失；“已淘汰 / 恢复”可以恢复原选择，但不恢复旧现场卡确认。移出审美库也有独立恢复入口。

默认**不自动删除文件**。需要释放磁盘时先检查清单，再显式执行：

```bash
python -m ref_lab cleanup --days 30
python -m ref_lab cleanup --days 30 --apply
```

最短保留 7 天。只清理明确回收、足够旧、没有有效使用关系的内容寻址文件；保护其他项目、全局收藏、笔记和未结束分析任务引用。元数据、来源与事件保留，不删除仓库历史素材。文件已清理的条目须重新导入相同字节才能恢复；误删恢复还可依赖完整备份。没有明确回收依据的孤儿文件不凭猜测删除。

## 回归与维护

```bash
python -m pytest -q tests/test_library.py tests/test_imports_jobs.py tests/test_workers.py tests/test_operations.py tests/test_personal_library.py
node --check web/app.js
python -m playwright install chromium
python -m pytest -q tests/test_ui_components.py
python -m pytest -q tests/test_browser.py tests/test_live_system_regression.py
```

组件测试是真实 Chromium DOM，但用 TestClient 显式桥接网络；HTTP、Cookie 和 `file://` 离线测试单列。历史图片测试不填造角色、灯光或授权事实。最新结果和限制见 [本轮记录](docs/tasks/2026-09-27-personal-library.md)、[回归说明](docs/CODEX_REGRESSION.md)。代码任务先记意图、后记实际证据；[AGENTS.md](AGENTS.md) 与 Git 任务记录为协作约定，Notion 仅是显式授权的可选同步视图。

## 私人部署边界

FastAPI + SQLite WAL + 原始图片文件 + 无构建步骤的 Web。默认仅监听回环地址，单所有者使用。数据库、登录口令、浏览器档案和新增私人图片不提交 Git。已有公开 Git 历史无法通过私人页面撤回。公网部署前配置 HTTPS、随机 `LAB_ACCESS_TOKEN`、准确 `LAB_PUBLIC_ORIGIN`、持久卷和备份，参见 [部署说明](docs/DEPLOYMENT.md)。本版本不自动部署、不合并 main、不自动操作 PS、不重绘人物。

详细设计：[架构](docs/ARCHITECTURE.md) · [执行器协议](docs/WORKER_PROTOCOL.md)。
