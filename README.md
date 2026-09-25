# Photography Reference Lab · 参考实验室

私人 cosplay / 日常人像审美库、独立大图筛选工作台和现场摄影资料卡。

**v0.2 是可运行的应用重构，不是旧看板的换皮。** FastAPI + SQLite + 原始图片文件存储 + 无构建步骤的 Web 界面。角色项目、人工选择、图片核验、资料卡、任务、笔记和变更事件分别持久保存。旧 `references/`、`images/`、`staging/` 及历史 HTML 保留，不作为新系统的事实来源直接发布。

## 启动（Python 3.11+）

```bash
python -m venv .venv
# Windows: .venv\Scripts\Activate.ps1
# macOS / Linux: source .venv/bin/activate
python -m pip install -e ".[test]"
python -m ref_lab migrate-legacy
python -m ref_lab doctor
python -m ref_lab serve
```

访问 `http://127.0.0.1:8765`。另开终端执行 `python -m ref_lab token` 取得本机口令。默认数据目录 `.local/`，不会提交数据库、登录口令、浏览器档案或新收集的私人图片。Windows 可先运行 `./install.ps1`。

旧素材迁移可重复执行，按导入标识和实际文件 SHA-256 去重；真实人工 KEEP / MAYBE / REJECT 记录被保留。**历史动作说明、标题和搜索分类只保存为未验证旧信息；缺图如实记录，不伪造图片或核验结果。** 原仓库有公开素材，新的私人访问控制不会撤回已经公开过的 Git 历史。

## 已实现的主流程

1. 建立多个角色项目：仅角色名必填，作品、服装版本和自由要求选填，器材条件可修改。
2. 上传独立图片或导入候选 ZIP；保留接收到的文件原始字节，另生成展示图和缩略图。精确重复按哈希合并，近似重复仅提示。
3. 单图大图筛选、原尺寸查看、保留 / 待定 / 淘汰、审美反馈、借鉴维度、灵感收藏、搜索与分页。选择写入数据库，不依赖 localStorage。
4. 人工逐图核验，或将已保留参考交给外部 Agent / 可选 API 执行器。图片事实、布光推测与可执行拍摄方案分开；AI 结果只能成为草稿。
5. 来源、图片、角色适配和资料卡门槛满足后，由用户单独确认现场卡。改图会撤销旧核验和选择；改要求会使旧卡待复核。并发编辑使用版本冲突检查。
6. 导出带独立图片的离线拍摄 ZIP：解压后打开 `index.html`，现场口令优先，布光、后期和来源可继续阅读。灵感包明确不是现场指令。
7. 导入 Notion **Markdown & CSV ZIP**，保留本地图片和源路径、提示未解析引用；笔记可编辑，重复导入不会覆盖已经编辑的笔记。
8. 采集 / 分析任务有实际状态、检查点、候选数量和失败记录。备份、完整性检查、数据库迁移入口和可选 Notion 意图记录同步已提供。

## 采集与 AI 分析不是假按钮

网站建立任务后，默认显示“等待执行／受阻”，不会自动宣称搜索完成。

- **不使用付费 API**：下载任务 ZIP，让本地 Codex / Antigravity 读取独立图片，按 `docs/WORKER_PROTOCOL.md` 返回候选包或分析 JSON，网站导入并逐项校验。
- **本地浏览器采集**：安装 Playwright，在自己明确授权的本机 Chromium / Edge CDP 会话运行 `python -m ref_lab collect --job JOB_ID --cdp http://127.0.0.1:9222 --search`。不提供验证码绕过、隐藏 API、Cookie 导出或 CDN 地址猜测。仅尝试正常可见页面，受阻就停止并保留进展。网站不能接管另一台电脑的浏览器。
- **可选 OpenAI API**：显式配置 `OPENAI_API_KEY` 与 `LAB_ANALYSIS_MODEL` 后，运行 `python -m ref_lab analyze --job JOB_ID --confirm-external-images`。这个命令向 API 发送所选参考展示图，需要相应权限和独立 API 费用；不是使用 ChatGPT 网页 Pro 次数。启动网站不会自动调用它。
- 复杂合成卡可以保存背景生成提示词；本版不自动生成背景、不重绘实拍人物、不自动操作 PS。

采集器的默认搜索词只是起点。项目自由要求完整进入任务包和 AI 分析上下文；本地简单采集器**没有声称已经通过 LLM 理解所有自由要求或保证素材语义正确**。需要 Agent 按任务要求扩展检索、查看实际图片。

## 回归与维护

```bash
python -m pytest -q tests/test_library.py tests/test_imports_jobs.py tests/test_workers.py tests/test_operations.py
node --check web/app.js
python -m playwright install chromium
python -m pytest -q tests/test_ui_components.py
python -m pytest -q tests/test_browser.py
python -m ref_lab backup --output ../reference-lab-backup.zip
```

测试中的人物类型标注来自明确标记的**合成测试数据**，只验证流程门槛，不证明模型的真实图像识别准确率。组件测试用无网络 API 桥接；完整浏览器测试另测实际 HTTP、Cookie 和离线文件。见 [Codex 回归清单](docs/CODEX_REGRESSION.md)。

每个有意义的开发任务先写 `docs/tasks/` 意图与验收，再改代码。`tools/finish_task.py` 提供显式路径提交、回归、可选推送及远端 SHA 核对；不会强推 main。Notion 是可选同步视图，不是唯一事实源。共同规则见 [AGENTS.md](AGENTS.md)。

## 部署边界

这是**单所有者私人工作台**，不是多租户公共图片平台。默认只监听回环地址。部署到域名前，需要 HTTPS 反向代理、随机 `LAB_ACCESS_TOKEN`、准确的 `LAB_PUBLIC_ORIGIN`、持久化数据卷和备份。配置示例见 `.env.example`；Python 不会自动加载 `.env`，需由终端或部署工具提供环境变量。

```bash
docker build -t photography-reference-lab .
# 在 --env-file 指定的文件中配置随机口令与实际 HTTPS origin。
docker run --env-file .env -p 127.0.0.1:8765:8765 -v photography-data:/data photography-reference-lab
```

Docker 镜像不复制旧参考素材；先在本地迁移，或由管理员单独挂载指定旧目录执行迁移。代码仓库可公开，私人数据和未授权参考图不能因网站上线而自动公开。原始图片可能保留 EXIF，离线 ZIP 是私人数据副本，下载后不能远程撤回。

详细设计：[架构](docs/ARCHITECTURE.md) · [执行器协议](docs/WORKER_PROTOCOL.md) · [部署与安全](docs/DEPLOYMENT.md) · [本轮任务记录](docs/tasks/2026-09-25-library-rebuild.md)。
