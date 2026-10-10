# Codex → AGY Headless 实际运行报告

日期：2026-10-10。结果：**PARTIAL**。

真实搜索、事实底稿交接、AGY 写作、Codex 核验和两轮定点返工均在 Codex 主控下执行；没有启动 Antigravity IDE，没有要求用户复制文件。AGY 未观看视频，原片离线获取及关键原音听校尚有缺口，所以不标 FULL。临时脚本只捕获本次进程/截图，没有建设多 Agent 平台或继续开发旧门禁。

## 环境与官方接口

- 工作树：`D:/AI PROJECTS/photography-reference-lab-agy-headless-20261010`。
- 分支：`codex/agy-headless-video-pilot-20261010`；起点经 ls-remote 核实为远端 `codex/evidence-photography-atlas` 的 `b3b28868cf4b1f8a2956a293313fe969daaf5381`。
- `Get-Command agy` 返回 `C:/Users/Dell/AppData/Local/agy/bin/agy.EXE`；实际 `agy --version` 为 1.3.2，`agy --help` 列出 print、JSON/stream-json、conversation、print-timeout。
- [官方 Headless 文档](https://www.antigravity.google/docs/cli/headless/)由 Codex 独立读取。AGY 对该页的读取被权限系统拒绝，不能混称 AGY 已读取。
- PowerShell 7.6.6；复用已安装 Python、FFmpeg、yt-dlp、faster-whisper GPU 环境、BrowserSkill 0.3.2 和 Edge。没有安装大型依赖。
- 直连 Git/AGY 有连接问题；后续子进程复用 Windows 已启用的 `127.0.0.1:12002` 代理，不改注册表、全局代理、凭据或权限。首次静默的根因未确定，不将其断言为鉴权或网络故障。

## 七次真实 Headless 调度

版本/help 不计入本表。“SUCCESS”是 CLI 终态，不表示正文可靠或工具成功。

| 次序 / 私人记录名 | 实际调用与交接 | 退出 / status / 正文 | 实测进程墙钟 |
|---|---|---|---|
| 1，初始直连 probe | 用户指定 `agy -p "回复 AGY_CLI_READY，并说明你当前能否访问公开网页。" --output-format json --print-timeout 60s` | 持续静默，Codex 终止自己启动的进程；exit -1，无 JSON、无 conversation_id | 约 357 秒；内部 60s 未形成可见终态 |
| 2，research | stream-json、180s，先读官方网页证明工具能力 | exit 0 / SUCCESS / response 空；read_url 被拒绝 | 28.22 秒 |
| 3，ready | 原指令 JSON、60s，子进程使用现有代理 | exit 0 / SUCCESS / response 空；再次自动尝试官方页并被拒绝，未返回 AGY_CLI_READY | 21.79 秒 |
| 4，search | `--conversation` 接续 research，要求自主找 2–3 个候选，只交候选，不写课程 | exit 0 / SUCCESS / 返回三候选和权限说明 | 142.75 秒 |
| 5，lesson | 原 conversation，完整提供 Codex 核实底稿，要求仅据此写中文教学 | exit 0 / SUCCESS / 返回完整初稿 | 68.76 秒 |
| 6，repair | 原 conversation，9 个具体问题的局部替换 | exit 0 / SUCCESS / 返回 9 段 JSON | 63.37 秒 |
| 7，repair2 | 原 conversation，仅收紧 4 个剩余片段 | exit 0 / SUCCESS / 返回 4 段 JSON | 116.82 秒 |

共 7 次实际调用；6 次 exit 0 / SUCCESS，其中 4 次有实质文本、2 次空正文。主研究会话 `d19f7663-816d-43ef-9f0b-ba4f5fd2ec3a`；独立 ready 会话 `4a10ffd9-9a4e-4b79-946d-07acafef5b2d`。恢复会话在搜索、写作和两次修订中均实际成功，不要求用户转抄内容。

运行参数：`agy -p <UTF-8 prompt> --output-format stream-json --print-timeout 180s [--conversation <ID>]`。由 subprocess 捕获二进制 stdout/stderr，保存 JSONL 事件和独立实际退出码；研究后的调用有 240 秒外层截止，但没有触发。未使用 `--dangerously-skip-permissions`。

## 工具证据、stderr 与 usage

- **search_web**：主研究实际记录 11 个 DONE 调用，有查询参数和工具结果。证明 AGY 能使用公开搜索工具，不证明它读过视频或完整网页。
- **read_url_content**：实际调用过，对 `antigravity.google` 返回 `permission check failed ... user denied permission for read_url(antigravity.google)`。两个独立探测均有 denied_actions；stderr 提示 print 模式 soft-deny。保留错误，没有用绕行脚本继续读取被拒绝资源，也没有开启跳过权限。
- AGY 的工具清单虽列出 browser 工具，本次没有 AGY 的视频播放、画面、音轨或 browser 工具执行证据；候选报告明确承认未播放。不能因 init 中列出工具而称其可用。
- search、lesson、repair、repair2 的捕获 stderr 为空；不能由此推断所有底层 hook 正常。
- 最终主会话 CLI 自报累计 usage：input 270134、output 24055、thinking 17471、cache_read 312323、total 294189。ready 独立会话：input 20210、output 821、thinking 781、cache_read 0、total 21031。首次静默 probe 无 usage。主会话累计值仅取最后一次，不将各轮累计 token/duration 相加。没有账单或价格证据，不换算费用。
- 主会话最后 result 的 `duration_seconds=1882.271313`、`num_turns=5` 是会话字段，不是本次 repair2 的实际进程耗时；上表墙钟由 Codex subprocess 计时。
- 未观察到明确的额度耗尽提示；现有返回无法证明剩余额度多少。

## Codex 的独立取证与纠错

AGY 三候选中：Martin Wong 身份核实但媒体提取遇机器人验证；Jerry Ghionis 的标题真实但 URL 绑定错；Manny Ortiz 的地址不可用且确切身份未证实。Codex 修正 Ghionis 原候选、获得完整媒体并执行本地 ASR，但发现它偏讲解者自我示范，未选作最终课程。

最终片是 Codex 在同一 B&H 官方系列中找到的 [Jerry Ghionis 影棚实拍示范](https://www.youtube.com/watch?v=vQK0V3nqK94)，不能记成 AGY 发现。离线视频下载 403；原始自动字幕成功取得。正常可见 Edge 播放成功；Codex 通过 BrowserSkill 定位并打开 23 份真实截图，采用 06:22–06:35 落肩/转头、14:24–15:30 坐姿/开肘两个节点，正文嵌入四张本机私人截图。

BrowserSkill 首次后台 daemon 启动遇 Windows JobObject breakaway 错误，改用 skill 支持的 managed foreground daemon 后实际 status 确认 Edge 已连接。只用新建研究 session，结束时停止自己的 session。14:58 首次 screenshot 失败，复查播放器时间后再截图成功；失败记录保留。没有 Cookie 导出、隐藏接口、挑战绕过或激进重试。

**明确事实错误 3 项**：1 个错误来源绑定，2 个初稿画面误读（垂直手臂、黑色长袖）。另有未确认的候选身份、夸大轮廓变化、虚构距离精度、情绪/单动作因果等问题，逐项见 EVIDENCE。Codex 将证据与原句退回 AGY；两轮只换受影响片段。第二轮后 Codex 再次对照四张实际图，删除残余普遍化和未经核实的科学候选，保留 AGY 主体教学叙事。未让 AGY 自己审批初稿。

最终没有发现仍保留的重大画面事实错误；仍未人工听校自动字幕、未归档完整原片、未真人复拍或获得主人审美/学习效果验收。中文口令是转述，未伪装成逐字对白；相机参数、精确器材和心理机制没有进入课程事实。

## 三个问题的实际回答

1. **能否只操作 Codex 完成两个 Agent 接力？** 本次实际做到了 AGY 搜索、恢复上下文、据底稿写作、两轮修订与 Codex 验收，无 IDE 和人工文件搬运。媒体/原音核验仍有边界，因此完整流程结论保守为 PARTIAL。
2. **表达是否自然且无重大事实错误？** AGY 提供了“给画面留一口气”的教学叙事、图像读法、现场口令转述与可执行练习；Codex 处理已发现的明确错误。自动字幕尚未听校，不作无条件准确保证。
3. **是否减少重复操作？** 用户无需在两软件间复制提示词、底稿和修订意见，确实少了搬运步骤；本次仍花了能力探测、来源纠错和取证时间。不能据一次实验断言比人工更快、成本更低或质量一定更好。可复用的是少量提示词和三份研究文档，没有新增需长期维护的平台。

## 版本化、检查与发布边界

唯一发布者为 Codex root；一个只读子任务仅检查 Publisher 既有接口，未搜索视频、未写课、未冒充 AGY。第一次编辑前已执行 canonical start/contract；未修改 Publisher 内部状态文件，未添加陌生项目授权。

仅提交三份研究文档和 `docs/tasks/2026-10-10-agy-headless-video-pilot.md`。私人媒体/截图/签名 URL/日志、临时脚本、venv junction 均被 Git ignore；图片链接仅在此本机 worktree 可用，远端文档不会包含图片字节。用户正常工作区原有修改保持不动。没有合并日用分支、生产部署或修改 UI/课程。

实际检查：配置要求的四个 pytest 文件 **70 passed、1 deprecation warning、30.04s**；`node --check web/app.js` exit 0。这些是项目兼容回归，不是图像/对白准确性的证据。seal/finish 会另外执行配置的 required checks；真实 commit/push/remote SHA 与 Notion 状态由 canonical 回执和最终 Codex 消息报告，本文件不在提交前预填成功。

AGY 私人 cli.log 曾出现 `task-finalization_PreInvocation` 自定义 hook 的 Windows 路径引号错误，提示命令无法识别；AGY Headless 主任务仍继续。故 AGY hook 的现场兼容性是 **FAIL**，没有通过修改全局 hook 或内部 Publisher 文件掩盖。Codex 正常显式调用 canonical Publisher 的结果单独报告；WSL_NOT_COVERED。

私人证据位于 worktree `.local/agy-pilot/`：每轮 `.prompt.txt`、`.stdout.jsonl`/JSON、`.stderr.txt`、`.meta.json`，初稿 `lesson-draft.md`、最终替换片段，以及媒体/字幕/截图。原始接收字节与派生截图分开保留，没有删除研究证据。
