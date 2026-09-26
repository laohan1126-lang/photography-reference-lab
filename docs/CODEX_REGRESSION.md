# v0.3 回归与接手

目标分支 `codex/reference-library-rebuild`，本轮起点 `b95f37540ada1bae18de949873bdbbcce021e621`。旧 v0.2 验收记录保留在日期任务文档中，**不是当前测试结果**。最新实跑命令、统计和限制见 [2026-09-27 任务记录](tasks/2026-09-27-personal-library.md)。

## 保全与安装

```bash
git fetch origin
git status --short
git log --oneline -5
git switch codex/reference-library-rebuild
# 有其他未完成工作时不要切换/覆盖，改用独立 worktree。
python -m pip install -e '.[test]'
python -m playwright install chromium
```

先读 AGENTS、README、ARCHITECTURE、WORKER_PROTOCOL 和最近 tasks。已有库备份后再升级；使用新的空 LAB_DATA_DIR 试迁移，不覆盖用户日用数据。数据库 v2 不可由旧代码继续写入。

## 自动回归

```bash
python -m pytest -q tests/test_library.py tests/test_imports_jobs.py tests/test_workers.py tests/test_operations.py tests/test_personal_library.py
node --check web/app.js
python -m compileall -q ref_lab tools tests
python -m pytest -q tests/test_ui_components.py
python -m pytest -q tests/test_browser.py tests/test_live_system_regression.py
```

个人库测试覆盖全局无项目收藏、多项目同字节引用、发现意图不变图像事实、淘汰/恢复、schema1升级、旧选择/确认/笔记保留、任务包/回执/分析部分完成、旧快照拒绝和磁盘清理保护。

组件测试使用真实 Chromium + 明示 TestClient 桥接，不覆盖实际 HTTP、Cookie、跨域或离线文件打开。检查 72 张样本中的 DOM 节点身份、已可见缩略图精确滚动位置、K/M/I/X 和两种自动下一张设置、跨页、刷新定位、无项目收藏上传、多角色引用、草稿检查和 409。只通过这些不能声称完整浏览器闭环。

HTTP 测试真实启动 Uvicorn、登录取得 Cookie、上传/下载候选 ZIP 与分析 JSON，明确确认后下载离线包，在断网浏览器打开真实 `file://` 文件，并验证图片 SHA、口令与 PS 路线。合成样本不是图像识别准确率证据。

历史回归改为从仓库实际清单自建隔离数据，不再依赖固定 `/tmp` 目录。第一次 435 created / 53 existing，第二次 0 / 488；选择 keep47 / pending255 / reject133，正常候选302。实际 schema1表升级与哈希、别名、revision核对。真实图片用于显示、选择、收藏、跨角色引用和恢复；**不再对历史图硬填角色、器材、灯光或自有授权来凑“已验收”**。现场卡正反门槛在明确合成样本中验证。

## 人工看页面时重点

进入“挑参考”，把缩略图滑到后段，点击当前可见图、左右键、K/I/M/X；开关自动下一张都不应突然回首图。淘汰立即消失，“已淘汰 / 恢复”能找回原选择。筛选和刷新保存当前位置与服务器选择；大图临时加载失败后恢复也不能一直隐藏。

点通用灵感进入独立审美库；引用到第二角色后核对同一图片、旧项目选择不变、新项目没有继承角色事实或卡片。没有项目时仍可直接收藏或写笔记。390px 宽度不横向溢出。

角色精选中只挑几张“制作现场卡”。未交给 Agent 的任务应保持等待；真实导入后才显示草稿/分析结论。检查用户不确认时 ready=0；图片/来源/要求改变后旧确认失效。图中真有可执行人物姿势、来源与授权范围是否准确，必须人工或实际逐图分析；不要以测试通过代替。

## BrowserSkill 与来源实测

用用户实际安装的 BrowserSkill 读取技能、doctor、授权 Chrome/Edge 会话；按任务包先小批验证小红书/Pinterest 与适合当前角色的来源。记实际原发布页、作者、下载字节、访问状态及检索缺口。遇验证码、付费/访问限制就停。不导出 Cookie、猜 CDN、使用隐藏接口或强行重试。

本轮匿名页面探测见 SOURCE_ASSESSMENT，不等于登录态自动搜图测试。不得把静态列表或 Agent 自述当成所有平台已接通。没有 API 密钥是默认可用条件，不是受阻原因。

## 备份、清理和证据

`backup` 解压到新的空目录后 doctor；比较原图、项目、收藏、选择、笔记。`cleanup --days 30` 先 dry-run；仅在隔离测试库执行 apply，核对其他项目/全局/笔记/未结束任务保护。不要把正式库当破坏性测试样本。

真实素材截图只放私有 `.local`；CI 仅上传合成截图和不含原图的 JSON 计数/回执。记录失败、跳过、被策略阻止的实际范围；修后复测。最终核对 diff、未跟踪文件、远端 SHA；不 force-push、不合并 main、不自动发布或 Notion 同步。
