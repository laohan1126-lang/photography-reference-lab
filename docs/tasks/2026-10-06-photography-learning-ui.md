# 摄影学习可点击视觉原型 · 2026-10-06

## 用户意图（实施前）

原话：“先做一个高完成度、可点击的视觉原型，我先验收 UI，再决定后续数据结构与完整功能。”两张 Pinterest 截图只作为视觉和布局参考，不复制品牌、Logo、功能或文案。

补充：“这个项目和 D:\AI PROJECTS\photography-reference-lab-convergence-20261004 是一起的，打算是摄影这块下面的两个分支。”本轮将摄影工作区呈现为拍摄参考与摄影学习两个并列入口。只读对照 convergence 的新版图库导航，不合并或修改该目录。

## Blueprint / 范围

- 延续 FastAPI + 无构建原生 HTML/CSS/JS；独立学习页面、样式和脚本。保留 R. 品牌和绿色强调色，白色画布、窄导航、瀑布流、完整大图与笔记面板。设计参数 variance 6 / motion 3 / density 5。
- 改动：web 学习页与现有侧栏入口、静态白名单和打包清单；只读原型素材接口；隔离预览工具、针对性浏览器检查。
- 不修改：SQLite、领域模型、采集器、K/I/M/X、审美分类、原图、现有用户数据；不整合 convergence 分支，不发布网站。
- 示例来自本地已有图片。来源标题保留 discovery 身份，演示主题不写入正式分类；不作新审美判断。素材原字节与来源元数据只放 gitignored .local。无示例时明确空态，不伪造已导入。
- 收藏、笔记、学习清单仅原型浏览器状态，显式标注。用户 UI 验收与技术验证分开。
- 当前起点 ffe9ecb；保留无关未跟踪 docs/tasks/2026-10-06-dot-photography-review-import.md。

## 可观察验收

1. 摄影下两个并列模块，参考入口可返回原站；学习页桌面瀑布流和手机双列无横溢。
2. 搜索、主题筛选、收藏、详情大图、相关图、笔记与练习清单真实响应；无死按钮或伪网络成功。
3. 详情保留图片完整构图；返回恢复浏览位置；键盘与关闭可操作。
4. 明确 UI 原型和示例来源；不改正式数据库、不调用付费服务，不把演示分类当事实。
5. JS 语法、所需核心回归、真实浏览器点击与桌面/手机截图检查。记录实际失败与未验证项。

## 实施结果与证据

### 交付形态

- **可点击 UI 原型 / 待用户视觉验收，非正式功能发布。** 本轮以白色画布、原有 R. 标识与绿色强调色呈现摄影下的「拍摄参考」「摄影学习」兄弟模块；窄侧栏、五列桌面/两列手机瀑布流、专题页、完整大图详情、来源页、观察笔记、收藏与练习清单可操作。
- `/learning` 为独立页面。新增只读原型素材路由沿用原应用 `/api` 鉴权，静态文件采用明确白名单；没有新数据库模型、迁移或写入接口。独立预览工具完全不实例化 Library，不打开资料库。
- 17 张本地已有示例的原字节复制到私有 `.local/learning-preview`，逐文件 SHA-256 一致；逐张打开核对显示内容，仅用于原型展示，未宣称审美筛选/分类/身份已获验收。既有出处、署名、使用限制随私有 manifest 保留，原素材不改动。新图片、manifest 与截图均不进入 Git。
- 收藏/练习/笔记仅 namespaced sessionStorage，UI 说明和提示标注当前标签页范围；收藏初始为空，无伪造的用户偏好。输入实时暂存，详情切换和刷新保留，浏览器不支持暂存时明确提示。搜索、主题、收藏和练习支持空态；详情可放大、上下张、浏览器后退，返回按钮恢复浏览位置。
- 图标来自 Tabler Icons v3.34.1 官方仓库，15 个 SVG 本地化并附 MIT 许可，无新软件、框架、模型或付费服务安装。

### 并行工作保护

初期只发现未跟踪的 Dot 任务记录；实施中发现另一任务开始在原目录修改导入/数据库代码。随即把本任务迁至独立工作树 `D:\AI PROJECTS\photography-reference-lab\.local\learning-ui-worktree`，分支 `codex/photography-learning-prototype`，基于 ffe9ecb。8 个独立新增文件逐个校验复制哈希后移出共享目录；对四个共用文件仅反向移除本轮具体增量，保留对方 API、导航、模型、服务与测试修改。共享目录已恢复 `codex/dot-photo-review-import`，未对其提交。迁移清单保存在原目录 `.local/learning-preview/isolation-manifest.json`。

convergence 目录只读，现有本地参考工作区 `http://127.0.0.1:18766/` 返回 HTTP 200 且包含新版 library-browser.js。原型独立运行于 `http://127.0.0.1:18767/learning`，切换入口指向该现有参考工作区；未合并、重启或改写 convergence。正式工作区里的学习入口需后续采用本分支后才出现，本轮独立预览不等于已部署。

### 本轮实际验证

工作目录均为独立工作树；Python 复用已安装的 `D:\AI PROJECTS\photography-reference-lab\.venv\Scripts\python.exe`，已验证 `ref_lab.__file__` 指向本独立工作树。

| 检查 | 实际结果 |
| --- | --- |
| `python -X utf8 -m pytest -q tests/test_library.py tests/test_imports_jobs.py tests/test_workers.py tests/test_operations.py tests/test_personal_library.py tests/test_collection_runner.py --basetemp=.local/learning-preview/core-local-tmp --junitxml=.local/learning-preview/core-local.xml --tb=short` | **116 passed**, 45.82s |
| `python -X utf8 -m pytest -q tests/test_learning_ui.py tests/test_ui_components.py tests/test_collection_ui.py tests/test_browser.py --basetemp=.local/learning-preview/browser-final-tmp --junitxml=.local/learning-preview/browser-final.xml --tb=short` | **27 passed**, 174.66s；包含真实 HTTP/Chromium、Cookie、离线流程与4项新增测试 |
| `python -X utf8 -m pytest -q tests/test_collect_adapter.py tests/test_candidate_pipeline.py --basetemp=.local/learning-preview/collector-tmp --junitxml=.local/learning-preview/collector.xml --tb=short` | **30 passed / 3 failed**, 8.49s；未声称全绿 |
| `git diff --exit-code ffe9ecb -- tools/collect_adapter.py tests/test_collect_adapter.py` | exit 0，三个失败涉及的适配器和测试与起点一致 |
| `node --check web/app.js`、`node --check web/learning.js`、`git diff --check` | exit 0 |
| 本机独立预览实际私有图片截图与浏览 | 17/17 图片成功解码，无页面脚本错误；1512×1000 桌面和390×844手机无横溢；完整原图详情已打开检查 |

新增回归验证：素材鉴权/路径白名单/缺样本空态；收藏、笔记、练习刷新保留；笔记文本转义；浏览器后退/键盘切图；清除筛选保留收藏或练习视图；跳到内容保持当前路由；手机专题与详情；原型交互不发业务写请求，不产生项目或全局收藏。

初次尝试如实保留：沙箱 pytest 临时目录权限导致103 setup errors，3个既有采集断言失败、43 passed；指定项目内临时目录后遇共享目录另一任务尚在编辑的 storage.py 缩进错误，未修改对方文件。移入独立工作树后沙箱测试进程挂起，终止本任务进程后通过正常本机权限运行上述隔离测试。首次新增接口测试使用不匹配 TrustedHost 的默认 testserver 得到400；修正测试客户端 base_url，既有安全策略未放宽。Codex 内嵌自动化内核启动失败，改用已安装 Chromium 进行真实浏览器测试，无安装/安全策略变更。

### 未验证与已知限制

- 用户视觉验收、完整学习数据结构、跨设备持久化、正式导入/课程管理与双分支统一部署未做，依用户本轮边界延后。
- 3个既有采集测试为 `test_wait_for_cards_*`：断言旧 list 返回值，但当前函数返回 `(cards, blocked)`。未扩大范围修复；不把这轮计为全项目测试全绿。
- Python TestClient 有既有 Starlette/httpx 弃用警告；不安装新依赖处理。
- UI 主题分组、标题是原型展示，不写正式分类；来源信息沿用旧记录，未重新外网核验。

### 下次打开 / 回归

在本独立工作树运行：

```powershell
& 'D:\AI PROJECTS\photography-reference-lab\.venv\Scripts\python.exe' tools/preview_learning.py
```

浏览 `http://127.0.0.1:18767/learning`；仅回环监听。`--port` 和 `--reference-url` 可显式指定；默认参考入口为已核对的 convergence 18766。不要运行整站启动器把本工作树当日常运行环境。

最小复查：`python -m pytest -q tests/test_learning_ui.py --basetemp=.local/learning-preview/next-ui-tmp` 与 `node --check web/learning.js`。测试媒体为隔离合成图；视觉截图在私有 `.local/learning-preview/desktop.png`、`detail.png`、`mobile.png`、`mobile-detail.png`，与合成测试证据分开。

本地保存 UI 检查点；用户 UI 验收前不作正式发布/合并声明，不把后续学习功能完成与本轮原型混为一谈。
