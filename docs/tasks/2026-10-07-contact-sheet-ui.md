# 印样式界面重设计 · 2026-10-07

## 用户意图

“幫我這個倉庫重新設計一下ui 符合這個攝影參考項目也最好有點高級感 codex設計的太醜了。”

同日另有 Codex 的“暗房式”未提交改动（`codex/ui-darkroom-20261007` 工作区，见 `2026-10-07-darkroom-ui.md`）。它基本是原版换深色，版式、方块面板与统计卡结构未变。本任务在独立 worktree / 分支 `cursor/ui-redesign-20261007` 上从 HEAD 重做，不覆盖、不合并那份改动，方便用户对照取舍。

## 边界

- 只改视觉语言：`web/styles.css` 整份重写，`web/learning.css` 换同一套 token；HTML/JS 只动文案装饰（去 emoji）、主题色与样式版本号。
- 保留全部 ID、类名、导航文案、按钮可访问名称、K/I/M/X 语义与交互流程；不改数据库、原图、人工选择、采集器、路由。
- 截图验证只读：Playwright 把 `/static/*` 换成本 worktree 的文件，接口仍走本机服务，并拦截所有非 GET 请求，保证不写入所有者资料库。
- 不提交到 main、不推送、不合并。

## 风格

摄影画册 / 底片印样（contact sheet）：暖黑画布让照片跳出来；标题用思源宋体（Noto Serif SC）营造画册感；编号、计数与英文眉题用等宽字体，像底片边缘的印字；单一黄铜强调色只用于当前项、焦点和主要选择。圆角 0–4px，几乎不用阴影，不用渐变与玻璃拟态。

## 可观察验收

1. 拍摄参考、图库、待筛、审美库、摄影学习共用一套暖黑画布、宋体标题和黄铜强调色。
2. 照片是画面中最亮的东西；面板退后为细线分隔，不再是一块块卡片。
3. 筛选主按钮（K/I/M/X）清楚可辨，已选状态一眼可见；淘汰仍为红色语义。
4. 1440px 桌面与 390px 手机宽度下没有横向溢出；手机底部选择条仍固定。
5. `node --check` 三个前端脚本通过；UI 组件测试与学习页测试通过（或如实记录失败）。

## 结果

- `web/styles.css` 从约 1800 行叠加覆盖的旧样式整份重写为一套 token：暖黑画布 `#0f0e0d`、骨色文字 `#ece6da`、黄铜强调 `#c9a46b`；思源宋体（本机已装 Noto Serif SC）做标题，Cascadia Mono 做编号、计数和英文眉题；圆角 2px（对话框 4px），只有对话框和浮层有阴影。
- 版式变化：统计改为一条细线分隔的计数条；详情列去掉卡片框，用左侧细线与大图分开；K/I/M/X 改为 2×2 细线网格，已选为骨色实底；缩略条做成带齿孔与帧号的胶片条，未选帧半透明；现场口令改成宋体引文样式；“项目设置与导出”改为下拉浮层，点菜单项或点外面即收起（`app.js` 新增一个全局点击监听）。
- 学习页 `learning.css` 换同一套 token 与字体。
- 去掉 `app.js` 28 处、`index.html` 7 处装饰 emoji，按钮文字其余不变；`app.js` 一处写死的 `#f9f9f9` 内联底色改用 `--soft`。
- `tests/test_library_browser_ui.py` 中项目目录文字颜色断言从旧浅色主题的 `rgb(24, 48, 57)` 改为新主题文字色 `rgb(236, 230, 218)`；该断言原本防的是对话框里文字不可读，深色对话框里仍是同一个检查。

### 实际验证

- `node --check web/app.js`、`web/learning.js`、`web/library-browser.js`：退出码均为 0。
- `python -m pytest -q tests/test_ui_components.py tests/test_library_browser_ui.py tests/test_learning_ui.py tests/test_collection_ui.py`：37 passed（需把 `PLAYWRIGHT_BROWSERS_PATH` 指到 `%LOCALAPPDATA%\ms-playwright`）。
- `python -m pytest -q tests/test_browser.py`：9 passed。
- 未运行 `tests/test_live_system_regression.py`：它连真实服务，本任务不碰所有者资料库。
- 只读截图（Edge / Playwright，接口走本机 18765，非 GET 一律拦截）：1440×900 下看过挑参考、图库、待筛、审美库、摄影学习、项目设置菜单、编辑对话框、淘汰理由对话框、项目目录、灯箱；390×844 下看过挑参考与学习页。各页 `scrollWidth - innerWidth = 0`，页面无 JS 报错。

### 限制与下一步

- 这是 AI 截图自检，不等于你的审美验收；请在真机上看过再决定用这版、Codex 暗房版，还是继续调整。
- 缩略条改为 `object-fit: cover` 裁切显示（大图与灯箱仍完整显示）；若希望缩略图也看到完整构图，改回 `contain` 即可。
- 手机端侧栏仍占首屏约四分之一，照片从首屏中下部开始；若要更激进，可把项目列表收进抽屉，但需要改交互。
- 回归：在本 worktree 运行上面两条 pytest 和三条 `node --check`；视觉对照可用只读截图脚本把 `/static/*` 指向本 worktree 的 `web/`。
