# 独立候选验收报告

**结论：PARTIAL / FAIL（不得据此准入）**。冻结的 5 条验收通过，旧案例兼容、桌面/手机布局和阅读不写入私人学习状态也有实际浏览器证据；但独立异常输入重现两项未通过：模拟语音证据被显示为已核验，畸形引文类型令阅读器渲染崩溃。另有候选新增测试 4 条失败。报告只验证，不修改候选业务代码。

验收对象：`D:\AI PROJECTS\photography-reference-lab-multi-pilot-20261010`。运行时通过候选 `create_app()` 启动回环地址服务，数据库 `Settings` 指向一次性临时目录；没有打开或访问正常 owner 数据库。截图、Playwright 脚本和浏览器观测 JSON 均在本验收工作树 `.local/multi-verifier/evidence/`。

## 冻结原件完整性

原件字节未改，哈希与 `freeze.json` 内登记值一致：

| 冻结原件 | SHA256 |
|---|---|
| `.local/multi-verifier/ACCEPTANCE.md` | `857b11c0014203c519130767ef14add01874d6ac576c0bbce882418671be08e7` |
| `.local/multi-verifier/test_video_evidence.py` | `6f6109a5d73db640b64d7533aeff702482854c3d0251df497cff7039e1bcad0e` |
| `.local/multi-verifier/freeze.json` | `4f284725687451be7fa935516e38db1ab68225018ef06fd57358e1aa3cfbd678` |

冻结时间：`2026-10-10T15:59:09Z`。本报告及补充浏览器脚本没有更改冻结标准、冻结断言或候选实现。

## 测试与运行结果

以下均为本轮实际运行/检查结果：

| 检查 | 命令或路径 | 结果 |
|---|---|---|
| 冻结浏览器验收 | `D:\AI PROJECTS\photography-reference-lab\.venv\Scripts\python.exe -X utf8 -m pytest -q .local\multi-verifier\test_video_evidence.py`，`VERIFIER_TARGET_ROOT` 指向候选 | **5 passed, exit 0, 28.70s** |
| 候选新增 UI 回归 | `D:\AI PROJECTS\photography-reference-lab\.venv\Scripts\python.exe -X utf8 -m pytest -q tests\test_video_evidence_display.py` | **77 passed, 4 failed, exit 1, 12.24s**；4 个失败均在 `test_untrusted_registry_status_cannot_verify_author_speech` 的恶意语音记录状态样本（见下文）或 `test_unreadable_layer_and_object_cannot_claim_verification` 畸形 `quote_kind` 样本 |
| 既有课程/入口 UI 回归 | `D:\AI PROJECTS\photography-reference-lab\.venv\Scripts\python.exe -X utf8 -m pytest -q tests\test_learning_gateways_ui.py tests\test_learning_course_ui.py` | **19 passed, 1 StarletteDeprecationWarning, exit 0, 77.37s** |
| 补充真实浏览器检查 | `D:\AI PROJECTS\photography-reference-lab\.venv\Scripts\python.exe -X utf8 .local\multi-verifier\capture_candidate_evidence.py` | **脚本 exit 0**，输出 `candidate-browser-observations.json`；服务收尾另有两条 Windows `WinError 10054` 异步关闭回调，截图与观测已完整写出。该收尾噪声不是产品通过证据。 |

四项新增 UI 回归失败的具体结果：对 registry 中 `simulated=True`、`verified=False`、`status='unverified'` 的原始 speech record，页面仍给出 `data-verdict="verified"`；畸形对象 `quote_kind={"toString": null}` 在 `evidenceQuoteHTML()` 查找显示名时报 `TypeError: Cannot convert object to primitive value`。这两类输入分别验证“信任状态不能凭匹配字段升级”和“不可读数据应安全降级”的冻结语义。

## 实际浏览器观察

补充检查以 Chromium 分别使用桌面 `1440×1000`、手机 `390×844` 打开真实课程案例 `jun-hand-direction`。两个视口均呈现 A/B/C/D：A 两个登记帧各自有时间码和对应 Bilibili 播放入口；B 明示未核实本人逐字原话，并标记“转述 · 非摄影者逐字原话”；C 有第三方来源链接并限定该来源支持理想投影关系、不证明本片摄影师动机；D 显示建议/推断。页面和阅读器横向溢出均为 `false`。两张已登记媒体图在浏览器中完整解码，均为 640px 宽。

案例索引中的五条旧视频案例为 `course-fixed-focal`、`course-distance`、`course-height`、`jun-hand-direction`、`jun-low-final`。独立检查候选数据里来源视频、起止与帧时间对应：

| 案例 | 来源及片段 | 登记 A 帧 |
|---|---|---|
| `course-fixed-focal` | Bilibili `BV1od4y1n7Ag`，55–78 秒 | 67 秒 |
| `course-distance` | 同一 Bilibili 视频，82–142 秒 | 140 秒 |
| `course-height` | YouTube `kHlzwHBCuaE`，108–132 秒 | 108、116 秒 |
| `jun-hand-direction` | Bilibili `BV1MD421L7VK`，132–150 秒 | 132、148 秒 |
| `jun-low-final` | 同一 Bilibili 视频，260–301 秒 | 275、300 秒 |

我逐张打开上述 8 张候选登记公开视频截图核对画面内容；所见与各自登记描述相符。媒体端点通过浏览器加载成功。链接时间参数指向案例播放片段起点。C 的 MIT《Foundations of Computer Vision》39.2 明确给出透视投影依赖相机坐标深度的公式，支持候选所述的理想针孔投影关系；本结论只限于该教材内容，不推及摄影师意图或此片焦距。B 没有经本轮完整视频音轨核对，页面保持未核实是合适呈现。

旧案例兼容通过：在浏览器响应中移除案例全部新增字段后，`course-distance` 原 caption 仍可读，播放链接仍为 `https://www.bilibili.com/video/BV1od4y1n7Ag/?t=82`，没有渲染空证据区，也未崩溃。

课程打开、阅读和切换带来的浏览器写请求列表为空（无 PUT/POST/DELETE）；隔离临时库读取的私人学习状态前后相等。此结果只证明本次隔离实例中的读取路径未改变记录；不声称访问或检查过用户私人数据库。

冻结脚本对 HTML/事件注入、危险协议链接、来源/时间链接和读取写状态边界的 5 条检查均通过。浏览器运行中也未观察到这些检查所捕获的页面错误。候选语义层的两项异常失败仍独立保留，不能由冻结套件绿色抵消。

## 明确失败证据

**confirmed / 已确认：模拟原话可以伪装成已核验。** 浏览器路由注入 `simulated=True` 的合成 speech record，文字明确标为模拟攻击样本，另将证据条目伪装成作者逐字原话。页面无 JS 异常，但把 B 显示为“已核验（仅限所列片段与核验方式）”，DOM verdict 是 `verified`。这是候选误把未可信记录升级成验证结果的直接证据，不是单测推断。截图：`evidence/failure-simulated-speech-marked-verified.png`，SHA256 `ae43199869f6a0bd324da0824ec6b807cb95a512b63ce13ac75a86c5e56c543c`。

**confirmed / 已确认：畸形 quote kind 会中断弹窗。** 在 `course-fixed-focal` 的 B 层注入 `quote_kind={"toString": null}` 后，浏览器报 `Cannot convert object to primitive value`，案例阅读弹窗未打开。截图：`evidence/failure-malformed-quote-render.png`，SHA256 `f9864aaa7179af0ae011ae80969679c8f3170ab009cf291cb290fa09824f110b`。

截图保存了失败现场，单靠截图不能替代异常来源；对应触发输入、`page_errors`、DOM 状态和 verdict 均保存在 `evidence/candidate-browser-observations.json`。

## 截图与辅助证据

以下 8 张均为 Playwright Chromium 的实际浏览器视口截图；每张画面只展开对应证据层，桌面和手机各四张。SHA256 见表：

| 视口/层 | 文件 | SHA256 |
|---|---|---|
| 1440×1000 A | `evidence/success-desktop-layer-A.png` | `1627b89963a3932f71b76aa851f567adf4114152c178dc8d3a5c97e144eb624d` |
| 1440×1000 B | `evidence/success-desktop-layer-B.png` | `f7c447884306159e737221d0bb4ee4fb70ac1ed80fcd914660bb10a0d476948b` |
| 1440×1000 C | `evidence/success-desktop-layer-C.png` | `349fb23e89aa1e086e1f8136f812fc1ee7204c688883b1e6fd57b66aa36a521f` |
| 1440×1000 D | `evidence/success-desktop-layer-D.png` | `78568126ed6b05b25fa1b1fcbcd76d06ef5fc28cc8e7ac5cd40a571b4ec84816` |
| 390×844 A | `evidence/success-mobile-layer-A.png` | `8f33c1f6c75729f08fd4bb438d9d0c26aa122ebde946526d39888a8f407e7b38` |
| 390×844 B | `evidence/success-mobile-layer-B.png` | `d06cbf73ea6baef222707fc09fe4c9703ba281c8bbd43b1faec903cb368519bf` |
| 390×844 C | `evidence/success-mobile-layer-C.png` | `7fac2426627d82b39efa9b2f4e83994c273b2b0ef11a75640e6180da3932f20a` |
| 390×844 D | `evidence/success-mobile-layer-D.png` | `bf684a35a66e21261e2fd108a9ee02bffd82e11f5c48d321744e6560efadb3de` |

完整机器可读结果和两个失败现场观测：`evidence/candidate-browser-observations.json`。该文件 SHA256：`639ffc44f1f2dc4254ec308a1a11ce934125ef906af363f2002bd3431a373d2f`。补充浏览器脚本 `capture_candidate_evidence.py` SHA256：`c4b43206976ac26a0dc532b6a4b78bb5e13152a769bb324a4700a1bc40df9baa`；只需设置 `VERIFIER_TARGET_ROOT` 指向候选根目录，并使用既有 Python/Playwright 环境即可复跑。

## 证据标签与限制

- **confirmed / 已确认**：冻结测试 5/5；既有 UI 19/19；五条视频案例、A/B/C/D 的实际文本与状态、来源及截图时间映射、桌面/手机无横向溢出、旧案例退化、阅读写入边界；模拟语音错误升级；畸形引文对象导致弹窗渲染失败。证据为本轮运行结果、浏览器 JSON、截图及冻结件哈希。
- **reproduced / 已复现**：两项语义缺陷通过独立合成异常输入在浏览器和新增回归中重现；新增回归整体为 77/4，未通过。
- **inferred / 推断**：未覆盖每条数据组合及所有浏览器引擎；其余同类畸形对象或 registry 状态可能有类似影响，但没有据此宣称全部都失败。
- **not verified / 未验证**：摄影师完整音轨/逐字原话；8 张截图以外的源视频连续画面；主人对课程教学解释的接受度；运行时其他浏览器；MIT 来源之外的解释主张；候选是否已修复上述失败。所有视觉事实限定于已登记并实际查看的截图，不等同于观看完整片段。

报告生成后未做任何候选业务代码修改，未提交、发布或合并。该报告只提供独立验收证据，最终准入决定由父主控作出。
