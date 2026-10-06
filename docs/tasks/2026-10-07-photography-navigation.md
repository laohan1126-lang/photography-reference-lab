# 摄影双分支往返导航 · 2026-10-07

## 用户意图

“我点拍摄参考就回不来了，这也不对吧。”摄影学习与 convergence 的拍摄参考是摄影下的两个并列模块；应通过界面直接往返，不能依赖浏览器后退。

## 实施前简报

- 当前：学习原型在 18767，根路径重定向到 convergence 的 18766；后者的实际侧栏没有学习入口。此前浏览器检查用了后退，未覆盖用户所需的页面入口返回。
- 技术：沿用 FastAPI 静态页面与原生 HTML/CSS/JS；不增加依赖。
- 修改：两份参考页的模块导航保持同标签页；convergence 增加指向本机学习原型的明确入口；学习页在当前标签页暂存当前视图/筛选/详情，返回时恢复。新增对应浏览器回归和可重跑的实际双服务检查。
- 不修改：数据库、原图、人工选择、采集器、认证、生产启动配置；不合并两个项目分支，不改共享根目录的 Dot 导入工作。
- 分支与起点：学习 codex/photography-learning-prototype @ ee57619；convergence codex/patch-convergence-20261004 @ 2de6b8c。实施前两处 Git 状态均干净；后者在正常本机权限下确认。
- 范围说明：本轮用户反馈授权修复 convergence 的可见导航；这更新了原型初始任务中“convergence 只读”的实施范围。仍仅本机原型，没有统一部署/完整学习功能发布。

## 可观察验收

1. 桌面和 390px 手机上，直接点击“拍摄参考 → 摄影学习”往返，无新增标签页、无浏览器后退。
2. 返回保留学习筛选/详情、收藏与已输入笔记；显式带 hash 的链接优先于暂存位置。
3. 拍摄参考页刷新仍有入口，导航不引起横向溢出。
4. 实际双服务检查不向真实库发送业务写请求；记录修复前失败与修复后结果，截图单独保存在 .local。

## 结果

- 已在 convergence 参考页 Logo 下方增加“拍摄参考 / 摄影学习”并列切换，桌面和手机均在首屏可见。入口指向当前本机原型 18767，保留 UI 原型标识；学习分支自己的参考页也改为同标签页打开。
- 学习页面在原有 sessionStorage 中保存路由，返回恢复视图、主题、搜索、当前图片；笔记/收藏继续沿用原型暂存。明确 hash 的深链接优先，不改变浏览器后退行为。
- 实施前，新增两项隔离浏览器回归均失败于旧入口 target=_blank；实际双服务脚本失败于 convergence 中找不到“摄影学习”链接，复现用户的真正故障。该失败以断言为准；最初合并命令末尾的环境探测返回 0，未将其当成检查通过。
- 学习工作树运行 `python -X utf8 -m pytest -q tests/test_learning_ui.py tests/test_library.py tests/test_imports_jobs.py tests/test_workers.py tests/test_operations.py tests/test_personal_library.py tests/test_collection_runner.py --basetemp=.local/learning-preview/nav-green-tmp --junitxml=.local/learning-preview/nav-green.xml --tb=short`：**122 passed**，82.19s。
- convergence 运行 `python -X utf8 -m pytest -q tests/test_browser.py tests/test_library.py tests/test_imports_jobs.py tests/test_workers.py tests/test_operations.py tests/test_personal_library.py tests/test_collection_runner.py --basetemp=.local/navigation-test-tmp --junitxml=.local/navigation-regression.xml --tb=short`：**132 passed**，127.24s。上述 Python 均为现有 Windows .venv，测试数据隔离；各有一个既有 Starlette/httpx 弃用警告。
- 实际运行 `python -X utf8 tools/verify_learning_navigation.py`：1440px / 390px 两种宽度各通过两次“摄影学习 → 拍摄参考 → 摄影学习”点击，含参考页刷新；同一标签页，筛选/详情/收藏/笔记保留，无横溢、页面脚本错误或业务写请求。没有调用 browser.go_back 来替代返回入口。
- 检查了真实页面截图 `.local/learning-preview/navigation/reference-nav-1440.png` 和 `reference-nav-390.png`；左上返回入口可见，手机两列切换正常。结构化证据在同目录 `navigation.json`，返回后的学习截图为 `learning-return-*.png`。这些私有页面截图未入 Git。
- 两个工作树的 `node --check web/app.js`、学习分支的 `node --check web/learning.js` 及 `git diff --check` 通过。
- 未改接口、启动器、原图或数据库；静态资源即时生效，未重启已有服务。共享原始工作区的 Dot 工作未编辑。

## 范围与重跑

此处验证的是本机两个正在运行的原型服务；跨设备入口、统一正式部署、完整学习数据结构及用户整体视觉验收仍独立于本次导航修复。学习位置和笔记仍只在当前标签页暂存。

启动两个现有本机服务后，在学习工作树执行 `python -X utf8 tools/verify_learning_navigation.py` 可重跑真实往返检查；隔离回归分别为学习 `tests/test_learning_ui.py -k workspace_switch`、convergence `tests/test_browser.py -k photography_workspace_entrance`。用户验收步骤：刷新拍摄参考页面，点击左上 Logo 下方“摄影学习”，再用学习页顶部“拍摄参考”返回。

本轮仅提交各任务分支的导航、回归与记录，作为本地检查点；整体 UI 仍待用户验收，未推送、合并或同步外部工作记录。
