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
