# 项目级编排 Skill 发现与边界验证

日期：2026-10-11，Windows。状态：**PARTIALLY VERIFIED**。项目级 Skill 已验证基础发现；单次成功不证明长期稳定，不全局安装。

## 沉淀范围与来源

部署位置：[SKILL.md](../../../.agents/skills/research-code-verifier-orchestration/SKILL.md)。核心只含角色、隔离、依赖调度、冻结独立验收、进程证据和两轮定向返工；领域操作位于领域 Skill 或任务材料。没有 Agent 平台、权限修复、摄影方法或代码架构设计。

先只读核对已有 `codex/research-code-verifier-pilot-20261010`、`codex/cc-minimax-delegation-pilot-20261010`、`codex/agy-headless-video-pilot-20261010` 与后续 repair 分支的实际报告/调用脚本。继承真实外部进程、独立 worktree、Verifier 先冻结、CC 实改、失败返工与 SUCCESS 不等于验收的边界；保留旧实验 PARTIAL、403、未观看视频及未证明浏览器自动选档案的局限。

## 可复现评估

评估包：[evals.json](../../../.forge/research-code-verifier-orchestration/evals.json)，含 3 个正向、3 个近负向、3 个执行边界；本轮实际运行下表三类发现测试，其余评估案例未独立实跑。新会话通过本机 `codex exec --ephemeral --json` 与原生祖先项目目录发现，不向隐式/负向提示词注入目标 Skill 名称、角色或工具名称。只读规划前缀和 exact 用户请求保存于私人原始记录。

判定依据是成功的 Skill 正文读取工具事件及实际返回内容；口头“选择了”不足。支持 shell 读取与真实 Node MCP 文件读取；负向要求既无目标正文读取，也无外部 Agent 调度。

| 最终请求 | PID | 实际观察 | 结果 |
| --- | ---: | --- | --- |
| 使用 research-code-verifier-orchestration 完成一个研究和代码任务。 | 57540 | 实际读取目标正文，提出冻结独立验收与隔离分工 | VERIFIED |
| 为摄影课程增加真实教程研究能力，需要找资料、改代码，并且独立验证。 | 29372 | 自选 Skill 并实际读取；自行提出 AGY、CC、Verifier 分工 | VERIFIED |
| 调整一个按钮颜色。 | 22912 | 未读取目标正文，未调度外部 Agent，按简单本地编辑规划 | VERIFIED |

三个最终进程均 exit 0，独立 session/thread ID、UTC 起止、正文哈希、实际工具事件留在 `.local/orchestration-validation/discovery/*-final-routing/`。每种只观察一次，不作概率/统计稳定性断言。执行采用与宿主一致的 danger-full-access policy，**只读由明确提示词约束，而非 OS 沙箱强制**；没有改配置或权限。

三类发现会话均禁止实际派发；负向测试的有效判断是**未读取目标正文**。未派发也受这个通用前缀约束，不能单独证明实施态绝不调用外部 Agent。新会话负责自动选择和规划，真实外部执行由当前 ROOT 接续，并非宣称一个无干预的新 CLI 会话完成了全程。

## 保留的失败与修正

1. 初轮模型连接超时，尚未发生工具读取；保留 PID/非正常退出，不记为触发失败。恢复仅向子进程提供 Windows 已配置的回环代理，未改全局代理。
2. read-only CLI 原生 Windows 沙箱报 `helper_sandbox_lock_failed`，不能读取文件。保留阻断，改用宿主已授权执行 policy；没有修改安全规则或绕过被拒网页。
3. v1 的按钮颜色会话实际读取 Skill，虽未调度 Agent仍按严格标准 FAIL。收窄 description 中“目标需要协作”的条件，明确不要加载按钮颜色/普通 bug/问答，并移除测试包装中的协作关键词；未新增 AGENTS 强制规则。两项同时修正，无法单独归因于 description。
4. 中间包装“禁止启动进程”误伤 shell 只读，隐式会话仅选元数据；另一个显式会话通过 Node MCP 真正读取但首版解析器只统计 shell。修复评估器与只读约束后，在新会话重跑全部三类；保留中间记录，不把自述当读取。

`personal-skill-forge` 静态检查和 eval lint 均实际 **PASS，0 errors / 0 warnings**。独立只读审查发现基础 transport 参考曾比历史试验多写 Bash 默认权限；已收回到历史无 shell 权限边界，本轮 CC 测试由 Codex/Verifier 实跑。

## 全局安装判断

暂不值得全局安装。基础触发成立，但经历真实负向误读与评估器边界修正，尚缺多轮随机复测和第二个不同领域的成功复用。下一步先在本项目增加授权/未授权及近负向复测，确认独立来源/UI验收稳定后再由用户决定安装。当前会话启动时并无这个新 Skill；自动选择证据来自创建后的新 CLI 会话，不能倒推原会话启动即自动发现。

发现机制参考已实际打开的 [OpenAI 官方 Skill 文档](https://learn.chatgpt.com/docs/build-skills)；以上触发结论来自本机运行，不从文档推断。

## AGY 通路修复后的当前 Skill 复测

本次宿主技能目录已列出项目 Skill，ROOT 按真实研究、实现和独立验证目标自动读取使用；新增的是代表性运输前检、依赖修复与实际工具证据门槛。浏览器具体权限与操作保留在领域 [运行说明](AGY_BROWSER_RUNBOOK.md)，未写入基础技能，也未增加 AGENTS 强制调度规则。

更新后另开三个原生 Codex 临时会话，正文 SHA256 均为 `5860238f763d488062e98624b828e94ddb9927a28e7f2f942ecc6eaec06c78a2`，与实际当前文件一致：

| 请求 | PID | UTC 起止 | 正文读取证据 |
| --- | ---: | --- | --- |
| 显式使用同名 Skill | 47820 | 05:04:17–05:06:01 | 实际完整 Get-Content 正文返回；其后 rg 无结果导致复合命令 exit 1 |
| 只给摄影课程研究、代码与独立验证目标 | 54912 | 05:04:17–05:06:51 | 实际自动读取完整正文 |
| 调整按钮颜色 | 52328 | 05:04:17–05:05:34 | 未读取目标正文，未调度外部 Agent |

三个进程本身均 exit 0。显式原 `result.json` 因读取后的 rg 返回 1 而记 false；这是评估器假阴性，不是 Skill 未读。保留原 events/results，单独在 `.local/orchestration-validation/discovery/reassessed.json` 审计：显式 false→true、隐式 true→true、负向 false→false。评估器仅在目标 Get-Content 输出包含与本次完整正文逐字匹配的内容时接受非零复合命令；partial/filename-only 两个负例均拒绝。没有用 Agent 自述补通过，没有编辑 Verifier、提示词或原失败记录。

当前 `quick_validate.py` 与 `eval_lint.py` 实跑 PASS（0 errors / 0 warnings），评估器 AST 和原事件正负断言 PASS。仍是提示词约束的只读规划测试，真实执行由 ROOT 接续；三类各一轮不证明长期稳定或无人值守。继续只在本项目使用，未全局安装。

最终只读审计进一步发现旧“exit 0 + 标题”规则会接受仅标题输出。ROOT 用内存负例真实复现后，移除这个不足的成功信号；shell 与结构化 MCP 均要求返回完整当前正文，完整 Get-Content 后的其他命令失败仍可按已返回正文认定读取。独立发现测试审计实际通过14项断言：header-only/partial/path-only 在零与非零退出下均拒绝，完整 CRLF 正文与非零复合读取接受，MCP 的完整正文/目标路径边界正确。当前评估器 SHA256 `00f3bc4938134e2044049730b06c41014895d5275bb4718c6952d3ec8af98402`。

按收紧后的评估器直接重审三份原始 events 仍为 **true/true/false**；原 result 的 **false/true/false** 与早期 `reassessed.json` 保持，另存 `.local/agy-flow/discovery-strict-final.json` 和 `discovery-final-review.json`。未重跑新外部会话、未改 Skill 正文/描述或冻结 Verifier。独立 V01–V10 本轮不包含发现评估器源码；本段来自单独的只读审计，不混用验收范围。
