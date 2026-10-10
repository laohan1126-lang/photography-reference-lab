# 独立修复验收报告

验收目标：候选 `D:\AI PROJECTS\photography-reference-lab-multi-repair-20261011`，HEAD `07e4ec1fc8d979a07423425b75840cced9a6f2fd`，仅对照冻结标准与最终实现。独立基线记录：`baseline.md`；本报告、捕获副本和日志均只写入旧 verifier worktree 的 `.local\repair-202611`。没有读取 owner 私人数据库、学习记录或私有原图，没有改候选、冻结断言、正式课程或测试。

冻结原件 `ACCEPTANCE.md`、`test_video_evidence.py`、`freeze.json` 的 SHA256 最终仍为冻结登记值：`857b11c0014203c519130767ef14add01874d6ac576c0bbce882418671be08e7`、`6f6109a5d73db640b64d7533aeff702482854c3d0251df497cff7039e1bcad0e`、`4f284725687451be7fa935516e38db1ab68225018ef06fd57358e1aa3cfbd678`。原四项失败节点见 baseline 记录；候选与原 baseline HEAD 相同。

## confirmed / 已确认

- 最终候选的原四节点均通过：`4 passed, 1 warning, exit 0`。完整 `tests/test_video_evidence_display.py`：`81 passed, 1 warning, exit 0`；冻结 HTTP/Chromium 验收：`5 passed, exit 0`；既有课程 UI：`tests/test_learning_gateways_ui.py tests/test_learning_course_ui.py` 为 `19 passed, 1 warning, exit 0`；课程后端/网关：`tests/test_learning_course.py tests/test_learning_gateways.py` 为 `12 passed, 1 warning, exit 0`。JS `node --check web/learning-gateways.js` 与 `git diff --check` 均为 exit 0。
- 前后对照：基线四节点 `4 failed / exit 1`——三条 speech registry 状态实际被归为 `verified`，`quote_kind={"toString":null}` 实际抛 `TypeError`；最终相同节点 `4 passed`。对应最终实现位置为 `web/learning-gateways.js:156`（speech registry trust-state gate）和 `:251-253`（`quoteKindOf` 与 quote renderer）。
- 独立 Chromium 用隔离临时数据目录实测三种坏状态（`simulated=True`、`verified=False`、`status="unverified"`）：三例 DOM `data-verdict=unverified`，页面异常 `[]`；每例读操作无 PUT/POST/DELETE 学习写请求，私人状态前后相等。畸形对象 `quote_kind={"toString":null}` 在手机 390×844 的真实 reader 中实际渲染 B 层，`dialog_open=true`、`data-verdict=unverified`、引文标签安全降级到“转述 · 非摄影者逐字原话”，无 page error。
- 桌面 1440×1000 和手机 390×844 实际 reader 的 A/B/C/D 文字与来源链接可见，无 dialog/document 横溢，学习状态不变，捕获到的学习写请求均为 0。旧案例 `course-distance` 删除新增字段后，旧 caption 可读、原播放链接及时码仍为 `https://www.bilibili.com/video/BV1od4y1n7Ag/?t=82`，没有 JS 错误/横溢/学习写入，私有状态前后相等。冻结五项还通过旧案例时间码、HTML 字面文本、安全链接和只读学习状态检查。

## reproduced / 已复现

- 两个基线 bug 均被原四节点直接复现，且相同节点在修复候选转绿；独立浏览器再次用逐条注入的 registry 状态与恶意对象输入验证了最终渲染行为。Browser script exit 0 仅作为运行状态，以上结论来自逐项 DOM verdict、page errors、链接/文本、请求记录和 API 状态比较。

## inferred / 推断

- 当前回归足以支持这两个指定输入及既有课程路径未回归；未覆盖其它浏览器引擎、所有可能的畸形 JS 对象或 registry 状态组合，因此不把结果外推到所有未知输入。

## not verified / 未验证

- 当前隔离 worktree 的课程图像尚未完成像素加载验收。初次桌面/手机捕获显示 `jun-hand-direction` 两张登记媒体 `naturalWidth=0`，页面仍显示“正在加载原案例照片…”；旧 `course-distance` 的图片 `complete=false,naturalWidth=0`。这是隔离环境下的观察，未读取/访问 owner 私有媒体，也未判定是环境缺少图像文件还是图片懒加载/服务路径问题，因而不能声称旧图或失败提示已验收通过。之后尝试强制滚入该隐藏图以触发加载时，验收副本遇到 `Locator.scroll_into_view_if_needed` 30 秒超时；这是脚本/元素可见性限制，没把它记作候选 bug，也没有覆盖早前成功捕获的 DOM 证据。
- 未重新观看远端视频或核对摄影师音轨/原话；未做用户教学效果或正式日用服务验收。现有主任务边界为合成输入 UI 修复，不从本次结果宣称这些通过。

## 命令与证据日志

以下命令均在候选根目录运行，Python 为 `D:\AI PROJECTS\photography-reference-lab\.venv\Scripts\python.exe -X utf8 -m pytest -q`；冻结脚本在旧 verifier 根目录运行并设置 `VERIFIER_TARGET_ROOT` 指向上述候选：

- `tests/test_video_evidence_display.py::<3 个原 speech 节点 + test_unreadable_layer_and_object_cannot_claim_verification>`：修复后 4 passed。
- `tests/test_video_evidence_display.py`：81 passed。
- `.local/multi-verifier/test_video_evidence.py`：5 passed。
- `tests/test_learning_gateways_ui.py tests/test_learning_course_ui.py`：19 passed。
- `tests/test_learning_course.py tests/test_learning_gateways.py`：12 passed；`node --check web/learning-gateways.js` 与 `git diff --check` exit 0。
- 原四节点 baseline：`baseline-original-failures.log`；修复后分别留在 `repair-original-four.log`、`repair-full-video-evidence.log`、`repair-frozen-five.log`、`repair-course-ui.log`、`repair-course-unit.log`。
- 浏览器完整成功运行输出：`repair-browser-legacy-final.log`；机器可读观测：`evidence/candidate-browser-observations.json`；实际桌面/手机截图及三种状态、畸形输入、旧案例截图：`evidence/`。捕获脚本为冻结脚本的本地副本 `capture_repair_evidence.py`，冻结原件未改。
- 首次本地副本运行 exit 1 是 route handler 参数误绑定（Playwright 的 Request 对象覆盖了 bundle）；改为闭包后重跑。随后为实际检查 malformed B 层补充 DOM 断言，完整成功运行。另一次最后的图像可见性实验因为隐藏图片不能滚入视窗而超时，单独记录在 `repair-browser-image-settled.log`，不覆盖成功运行的机器观测；图像加载因此仍未验证。

整体结论：两个指定代码缺陷及冻结回归均通过独立验收；课程阅读中不写学习状态也在本次隔离浏览器中确认。因隔离候选图像未加载/失败提示状态未能确认，此报告不对课程媒体验收作完整通过结论。
