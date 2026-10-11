# 《动作导演》真实协作报告

本轮只生成这一门课程。教学效果等待用户试学/复拍，未据 pytest 或 Agent SUCCESS 宣布用户掌握。

## 实际任务调用

有完整 PID、argv、UTC、工作树、终结与哈希回执的 Headless 任务共七次：AGY 四次，CC 三次。环境探针（CLI help/version、AGY models）另记，不计为研究/实现任务；其中 AGY models 超时，未据它推断模型可用。实际代表操作读取 README 后，才派发正式任务。

| 调用 | PID | UTC 起止 | 实际结果 |
| --- | --- | --- | --- |
| cc-ready | 59316 | 07:31:49.179501—07:31:57.016758 | exit 0；实际 Read README 并回报标题。 |
| agy-ready | 22864 | 07:31:49.182441—07:32:15.802739 | exit 0；实际 view_file README。 |
| cc-implementation | 18260 | 07:32:13.298220—07:38:15.735517 | exit 1，48-turn 上限；留下八文件候选，不能称完整实现。 |
| agy-research | 53696 | 07:32:40.563451—07:33:31.654192 | exit 0/terminal SUCCESS，但 response 为空；Rangefinder read_url 权限拒绝中止研究。 |
| agy-full-polish | 52428 | 07:46:41.891844—07:52:50.861911 | exit 0/terminal ERROR，provider 内容过滤错误；有完整 response，但事实新增不合格，未进入网站。 |
| cc-revision1 | 33188 | 07:49:46.428184—07:53:38.383778 | exit 0/terminal success；修复路径、原子拒绝和测试问题，测试由 ROOT 实际执行。 |
| agy-polish-revision2 | 6372 | 07:54:41.228764—07:58:17.457665 | exit 0/terminal SUCCESS；返回完整八节；Codex 逐差异审核后采用，并记录三处事实措辞修正。 |

完整元数据、工具计数、permission denial、terminal usage 与原始事件文件 SHA256 见 PROCESS_RECEIPTS.json；原始脱敏事件/终结日志在 ignored `.local/action-directing/<label>/`。CC 沿用既有 MiniMax-M3.1-Flash-Preview 路线；AGY 沿用已装 CLI 的用户路线。全部七次回执的 protected/provider unchanged 为真，正式任务的冻结标准不变。未修改全局 Skill/Hook、供应商或权限配置，未使用 skip-permissions。

JSON 中 `tool_counts` 是原始 stream 工具事件计数；AGY 的 ACTIVE、DONE 可能分别出现，不能直接当作去重后的调用次数。七次任务进程的计数以独立 PID/起止回执为准，具体工具调用可按原事件的 step_index 或工具调用 ID 复查。

## AGY 与 Codex 各自实际做了什么

首次 AGY 研究确实读取了官方 YouTube 页面和工具生成的页面文件，随后在第二站点受阻；没有产出研究稿、播放画面或可认证的研究结论。因此没有“AGY 首次虚构对白被抓”的可报告事实，也没有将 Codex 独立取证算到 AGY 名下。

Codex 通过既有合法浏览器读取原作者说明、定位视频帧和打开原站照片，形成 FACTS.md。二手页面只用于找实际官方视频链接。独立 Verifier 又重新打开五个视频帧和两幅原图，读取官方/署名原文。原始读取范围与失败见 SOURCES.md 和 SOURCE_AUDIT.md。

Codex 审查 AGY 第一版完整润色时，发现它将条件性调整变成必然因果、从全身照片断言左右受力、加入无根据的精确距离，把假设 A/B 练习写成已实拍，并将慢动作改为迅速转头、承诺读后掌握。这些是实际 response 中的缺陷，不是为了展示协作制造的问题。第二轮回到核验底稿，恢复假设/慢动作/未知与限制。最终另明确镜像方法的作者、不预认证仿制道具安全、把机位副作用恢复为“可能”。完整前后稿、真实 diff 和事实复核在 AGY_POLISH_DIFF.md、ROOT_FACT_AUDIT.json。

## CC 的实际代码贡献与返工

CC 在独立工作树修改五个已有文件并新增三个文件：

- `web/learning.js`：读取独立附加包，验证引用及渲染前条件后原子合并，失败保留旧站并解释无法打开课程的原因。
- `web/learning-gateways.js`：复用现有阅读器，支持有边界的完整课程标签；问题/折叠解析继续只读。
- `ref_lab/learning_preview.py`、`ref_lab/api.py`：新增静态文件白名单，仅 /learning 允许两条精确来源图片 URL。
- `ref_lab/action_directing_media.py`：独立媒体登记；`tools/validate_learning_gateways.py`：可传入额外登记，基库不变。
- `tools/build_action_directing.py`：从真实 COURSE.json 读取并验证，分离课程与基础资料目录，冲突/缺失失败，支持确定性写入及 --check。
- `tests/test_action_directing.py`：真实 HTTP/Chromium 下的只读追加、坏包拒绝、旧站兼容与媒体/建包边界回归；合成夹具明确不作为摄影真实性证据。

ROOT 提供已审核课程数据、整合 CC 八文件并实际建包；未把教材写作归功于 CC。独立 tester 在首次候选复现 pytest 收集 IndentationError。ROOT 代码检查补充默认路径错误、缺少 main 导入、错误 CSP 子串判定、缺失文件夹具和合法 JSON 的空 chapters 可破坏旧站等具体问题，合为第一轮 CC 定向返工。返工后 ROOT 实测 18 pass / 1 fail，残留问题为测试把裸 URL 列表当完整 img-src 指令。ROOT 改正测试输入并增加实际 HTTP CSP token 断言；没有删除测试或降低标准。最终相关 23 项通过。

ROOT 曾把 pytest basetemp 指向尚不存在的 worktree/.local，导致 17 setup errors；改用既有 ROOT/.local 后才得到上述真实结果。这是执行路径错误，不算 CC 业务缺陷。私有底稿脚本一次多行字串语法错误也已在生成前修正，没有伪造成功产物。

定向返工共两轮：第一轮 CC 实现/测试问题，第二轮 AGY 全文事实问题；未修改验收标准。最终 Verifier 的实际结果另见 ACCEPTANCE.md，不预先填“发现缺陷”或“通过”。

独立最终验收随后实际发现一条旧 CSP 兼容断言失败（48 passed / 1 failed）：它假设 img-src 只能到旧列表立即结束。本课新增两条精确已核验地址后，这个旧预期需要更新。两轮上限已用，ROOT 先请求追加一个单点修正；用户明确回复“允许这一次单点修正”。ROOT 只更新这条测试，精确比较旧与新 URL 的 token 集合，并保留认证/CSRF、追加私人首页不含 Westcott 的限制检查。ROOT 1 passed，Verifier 独立复跑 1 passed（1.45s），不删除测试或扩大来源白名单。它是获授权的额外单点修正，不隐藏在原两轮内。

Verifier 也发现协作报告曾声称 PROCESS_RECEIPTS 已包含原始事件 SHA256，但初版 JSON 没有这些字段。ROOT 随后实际测量七次调用各四个原始回执文件的 SHA256/字节数，补入 original_artifacts。此前的缺漏作为真实报告错误保留；没有追造旧时间或替换日志。

独立终验现已完成：十五项原冻结标准 PASS，范围为可观察工程、来源事实与过程证据；二十八份原始回执的 SHA256/字节全核相等，重要来源在独立浏览器重查，真实 AGY 八节响应与两段 diff 精确一致。默认 123 passed、独立桌面/390px 只读兼容 2 passed、目录 30 passed / 1 环境 skipped。ACCEPTANCE.md / JSON 和原始测试 XML 已保留；ROOT 又原样集成独立回归并实际复跑 2 passed（14.57s）。真人试学/复拍和 Git/Notion 发布各自另验，不由这些结果推断。

## 能保留什么，尚不能推断什么

可观察的贡献是：CC 写出了可执行的追加包接入与失败隔离；AGY 第二版把部分报告语气改成面对面的指令、衔接观察和复拍，并为不能换位的新情境保留视线选项；独立核验重新读取重要原始材料，没有只评价文字印象。第一版同时显示表达编辑会引入事实与条件错误，需要主控逐差异审核。

CC 实现与 AGY 研究的 UTC 区间实际重叠，但没有相同任务由 Codex 单独完成的可比基线，不对速度、成本或质量作因果收益结论。CLI 的 token/美元数字只是原始报告值，不代表实际账单或经验证的节省。流程是否推广到其他领域，等待用户亲自试学反馈。
