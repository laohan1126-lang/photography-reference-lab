# 摄影能力地图与专题研究页 · 2026-10-07

## 用户原意与本轮边界

用户纠正上一版方向：“首页不是普通图片流，而是我的摄影能力地图。”“第一版只实现两个页面。”“确认这套摄影学习产品的视觉语言和基础信息架构是否成立。”“第一轮完成后停止，不要继续扩展功能。”

首页的十个专题依次为：构图与画面组织；机位、焦段与透视；人物姿态与重心；人物与武器 / 道具空间；光线与人物塑形；景别与人物比例；角色表达与气势；现场执行与调度；后期与最终呈现；运镜与动态画面。

首页以摄影拼贴/封面为专题入口，比例不同、标题在图下；不做等高仪表盘卡、统计、进度或多层边框。顶部只有轻导航、搜索、最近学习，并保留用户上一轮要求的拍摄参考往返入口。详情用左侧约 42% 的连续研究笔记和右侧约 58% 的自然比例案例图墙；宽屏左侧可 sticky。先完善“机位、焦段与透视”，核心问题和四条关键规律采用用户给出的原文，其余九个专题用明确示例内容进入同一模板。图片 hover 显示示例成败/标签，点击打开 lightbox。

## 实施前检查与方案

- 栈：FastAPI + 原生 HTML/CSS/JS，无前端构建；复用已有原型只读素材接口、局部图标、17 张私有图片、独立 18767 预览和 18766 往返链接。
- 保留：R. 品牌、浅色背景、绿色细节、图片原字节与来源、现有鉴权边界；不改参考库界面或运行配置。
- 替换：旧学习 rail、发现/收藏/练习导航、普通图片瀑布流首页、单图学习详情。用户明确授权这次信息架构调整；旧原型 sessionStorage 保留不清除，但不作为新版功能继续暴露。
- 设计解读：私人摄影视觉研究工具，摄影主导、克制的 editorial 排版；原生 CSS aesthetic，不引入企业设计系统。DESIGN_VARIANCE=7（不同封面与图片比例）、MOTION_INTENSITY=2（仅 hover/切换反馈）、VISUAL_DENSITY=4（图片主导且文字紧凑）。
- 集中管理 CSS spacing、radius、typography、page max-width、gallery gap、muted text tokens。仅封面有轻裁切，案例与 lightbox 保留完整画幅。
- 触及：web/learning.html、learning.css、learning.js；对应隔离浏览器测试、真实双服务验证脚本和本任务记录。无数据库、复杂 CRUD、登录、设置、采集、依赖升级或正式发布。
- 素材与文案：使用已存在的真实图片作为 mock 视觉素材；UI 中的案例成功/失败、焦段及观察标签是示例，不把其写成已验证图片事实。详情提供来源与示例说明，不新增审美分类或摄影参数记录。用户给定专题是学习导航，不是正式库分类迁移。
- 当前工作树：codex/photography-learning-prototype @ 96b7a41，开始前干净。共享根目录与 convergence 不改。

## 可观察验收

1. 首页出现十个可点击专题封面，构图/比例有变化，搜索过滤专题，最近学习来自真实当前标签页访问。
2. “机位、焦段与透视”呈现用户的核心问题、四条规律及问题/结论/下次验证；其余专题复用模板并明确示例身份。
3. 详情左右宽度约 42/58，案例图片自然比例；hover/focus 显示次要信息，触屏可通过 overlay 获取。Lightbox 可关闭、前后切图、Esc 返回、焦点返回原图。
4. 首页/详情/浏览器后退/刷新/拍摄参考往返均有效；手机无横向溢出且不采用造成笔记截断的 sticky。
5. 无业务写请求、不改素材；保留私有素材鉴权与路径白名单回归。新增功能无死按钮、无虚假学习完成或图片事实。
6. 实际打开桌面和手机，查看截图并审查是否有等高卡、过度圆角、按钮堆积、badge 或框套框。技术验证不代表用户视觉验收。

## 本轮结果

- 已替换旧学习 UI：移除功能 rail、发现/收藏/练习页面与计数；首页仅十专题、搜索、最近学习、参考库往返。封面采用单图与拼贴、不同纵横比和自然错落，标题在图片下方，说明仅 hover/focus 显示。
- 详情沿用单模板；示例专题按用户原文呈现核心问题与四条关键规律，另有明确示例身份的问题、结论和下次实拍计划。其他九专题可点击且都有模板内容。左侧连续排版，42/58 栅格；宽屏在笔记能完整放入视口时 sticky，小屏或短视口不固定、不截断内容。
- 右侧最多九张精选 mock 图片保持自然比例；hover/键盘 focus 才显示成败与标签，触屏点击即可在大图中看到。原图弹层保留画幅、原始出处、署名和素材说明；支持关闭、Esc、前后切图与键盘焦点返回。
- 路由使用 `/learning#map`、`#topic=perspective`、`#q=...`、`&case=...`。最近学习只反映当前标签页真正访问过的专题，支持刷新与跨 18766 返回；新暂存使用 v2 命名空间，旧原型记录没有删除。没有表单写库或伪造完成状态。
- CSS 中集中定义 spacing、字号、颜色、圆角、最大宽度、图库间距和动效参数；保留现有技术栈与打包资源。原型只读接口和参考库未改。

### 实际验证

在本任务工作树复用现有 Windows Python `D:\AI PROJECTS\photography-reference-lab\.venv\Scripts\python.exe`：

| 命令 / 检查 | 结果 |
| --- | --- |
| `python -X utf8 -m pytest -q tests/test_library.py tests/test_imports_jobs.py tests/test_workers.py tests/test_operations.py tests/test_personal_library.py tests/test_collection_runner.py --basetemp=.local/learning-preview/map-core-tmp --junitxml=.local/learning-preview/map-core.xml --tb=short` | **116 passed**, 48.47s |
| `python -X utf8 -m pytest -q tests/test_learning_ui.py --basetemp=.local/learning-preview/map-browser-final-tmp --junitxml=.local/learning-preview/map-browser-final.xml --tb=short` | **8 passed**, 23.67s |
| `python -X utf8 tools/verify_learning_navigation.py --output .local/learning-preview/map-final` | 1440 / 390px 各两次实际专题→拍摄参考→专题点击；单标签、路由和最近学习保留；0页面脚本错误、0业务写请求 |
| 1920×1080 本机浏览器检查 | 研究笔记 computed position=sticky，滚动400px仍位于页头下方，页面无横向溢出 |
| `node --check web/learning.js`、`node --check web/app.js`、`git diff --check` | 通过 |
| 17张原始示例 SHA-256 与原 manifest 比对 | 全部一致，图片未修改 |

新增浏览器覆盖：十专题入口与其他九模板；搜索/空态；无素材仍可看专题；核心问题与规则原文；案例自然比例；hover 与真实 Tab/Shift+Tab 焦点显示；lightbox前后/关闭/后退/焦点返回；最近学习空态、刷新、显式深链优先；1440/390下专题与参考库往返；私有素材鉴权和路径白名单保持原测试。

真实截图已打开检查，目录 `.local/learning-preview/map-final/`：`map-1440.png`、`map-390.png`、`topic-1440.png`、`topic-full-390.png`、`topic-wide-1920.png`、`case-1440.png`、`case-390.png`，结构化往返结果为 `navigation.json`。没有等高 dashboard 卡、数值 badge、统计条、按钮堆积或多层信息框；案例区只给图片本身轻圆角。截图为私有现有图片，不进入 Git。

审查与修正：独立只读审查发现 lightbox 打开覆写首页焦点目标，已拆开保存专题 ID 和案例按钮，新增回归通过。首次主树浏览器回归为 7 passed / 1 failed：新增测试把程序 `.focus()` 当成键盘 `:focus-visible`；改为真正的 Tab/Shift+Tab 后8项通过。初次临时截图脚本使用过宽的 `[data-topic]` 选择器，在首页入口和隐藏详情 section 间出现 strict-mode 冲突，现有版本脚本改为限定 `#topic-grid a` 后完整跑通。隔离测试代理的首次运行因不存在的临时父目录失败，创建任务临时目录后通过；一次进程有Windows WMI诊断但pytest退出0，主树最终测试没有该诊断。测试中既有 Starlette/httpx 弃用警告未扩大范围处理。

### 交付边界与复查

本轮完成的是**待用户视觉验收的两页可点击原型**。案例标签、焦段与成败仅示意，未核验为真实作品事实；其他专题文案是 mock。未实现完整学习持久化、CRUD、登录、数据库变更、真实成败判定、动态视频或跨设备统一部署；用户要求本轮到此停止。无远端推送、Notion记录、主分支合并或公开发布。

当前预览继续运行于 `http://127.0.0.1:18767/learning#map`；示例详情直达 `http://127.0.0.1:18767/learning#topic=perspective`。无需重启只读预览服务，静态更新已通过真实页面验证。若服务停止，在本工作树运行 `python tools/preview_learning.py`；参考库沿用自己的 18766 服务。

最小复查：运行 `python -m pytest -q tests/test_learning_ui.py --basetemp=.local/learning-preview/map-next-tmp`，并在两服务运行时执行上述真实导航脚本。分支 `codex/photography-learning-prototype`；本地提交可用 `git log -1` 查询。并行测试仅在 `.local/learning-map-tests` 隔离树进行，最终测试文件已纳入本树，未改共享根目录或 convergence。
