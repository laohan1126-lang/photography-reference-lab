# Codex → CC Switch / MiniMax 实际委派实验

状态：**FULL**。两项实际委派产出的修复通过独立验收，项目级 Skill 候选完成。两个子进程曾因轮数上限非零退出，以下如实保留其失败状态。

## 真实路由与工作区

原生 `claude.exe` 为 `2.1.220 (Claude Code)`，Get-Command/version/help 均实际检查。CC Switch 当前 Claude provider 为 MiniMax，活动数据库记录与用户 settings 的 endpoint、模型、凭据一致；凭据只私下比较，未输出。本地路由、接管、failover 均关闭。

有效 endpoint 为 `https://api.minimaxi.com/anthropic`，配置及服务报告的模型为 `MiniMax-M3.1-Flash-Preview`。父进程有另一地址及不同认证的 ANTHROPIC 覆盖；每次仅对子进程移除继承的 `ANTHROPIC_*`，复制既有选中供应商设置。全局代理、认证及 CC Switch 配置未改。调试日志显示上述 base URL 和 `/anthropic/v1/messages` 请求；四次均有真实响应，调用前后路由一致。SDK 的 `provider=firstParty` 标签不证明 Anthropic 官方路由；本实验确认 endpoint 和服务报告的模型，未独立鉴定底层权重身份。

通过 ls-remote 核对远端基线 `antigravity/research-evidence-gate-loop-20261010` 为 `e290b56499736498cc5999a95c23abe4d9ad1c5f`。开发只在独立 worktree 的 `codex/cc-minimax-delegation-pilot-20261010` 分支。主工作区分支及原有 dirty 列表保持一致，课程和原始摄影数据未触碰。

## 实际调用

| 调用 | PID | 退出码 / 终态 | 结果 |
| --- | --- | --- | --- |
| ready，新会话 | 23288 | 0 / completed | `CC_MINIMAX_READY`，无工具 |
| 媒体修复，新会话 | 39244 | 1 / error_max_turns，限 8 | 12 次成功 Edit；A/B/C 通过，golden 夹具未完成 |
| 定向返工，新会话 | 32240 | 1 / error_max_turns，限 8 | 6 次成功 Edit；完成夹具及边界回归，移除额外路径回退；18 项通过 |
| 空包修复，新会话 | 33128 | 0 / completed，限 12 | 5 次成功 Edit；一次文本替换失败由 CC 自行纠正；最终 24 项通过 |

stderr 均为空，无 permission_denials、超时或供应商切换。开发使用 stream-json/verbose、`dontAsk` 和精确 `Edit(./path)` 许可，仅提供 Read/Edit/Write/Glob/Grep。无 shell、网络、权限跳过、CC commit/push。首轮冗余 `Write(path)` 规则被 CLI 提示忽略；有效 Edit 规则覆盖全部文件编辑工具，后续移除了无效规则。

Codex 返工 **1 次**：交回真实 golden 失败证据，要求修复夹具并移除未要求的 media_root/cwd 路径回退。没有删除测试、放宽断言或降级 ERROR。第二任务未恢复上一会话。CC 完成主代码修改，Codex负责验收、审查及交付；CC 未运行测试。

## 修改与验证

CC 仅修改 `checker.py` 和 `tests/test_research_evidence_gate.py`，相对基线为 400 行新增、48 行删除。缺失文件、目录、读取失败和错误 SHA 产生 ERROR；哈希改为分块读取。零断言包产生 `EMPTY_RESEARCH_EVIDENCE / ERROR`，沿既有 loop 进入 REVISE/BLOCKED，不发凭证。`loop.py`、schemas 未改。

保留原有 11 项测试断言；把缺失路径及空文件 SHA 正向夹具改成真实非空临时字节和实算 SHA，新增 8 项回归。结构夹具不代表真实课程内容或摄影事实核验。

独立标准在 CC 开发前写入 worktree 外，未授予编辑权限，并拒绝 CC Read。每次调用后原脚本 SHA256 均一致：`ee6aef2735d6c13766d122bcf694805b9cdbcbf0d4a39325a78f1d4bc2f799e2`。本目录 [测试副本](test_gate_acceptance.py) 在全部 CC 调用后由 Codex 原样复制。

| 案例 | 基线 | 修复后 |
| --- | --- | --- |
| A：ACCESSIBLE、文件不存在 | 错误 PASS | 两个周期均拒绝，无凭证/准入文件 |
| B：真实非空文件、错误 SHA | 拒绝 | 保持拒绝 |
| C：真实非空文件、正确 SHA、合法来源与断言 | PASS | 保持 PASS，凭证绑定 fingerprint |
| D：全空包；仅来源无断言包 | 均错误 PASS | 均拒绝，无凭证/准入文件 |

实际 pytest：基线 **3 failed / 2 passed**；首轮 **1 failed / 13 passed**；返工后 **18 passed**；最终独立 5 例 + 门禁 19 例 **24 passed**；项目默认六文件回归 **123 passed**。Node syntax、Skill quick_validate、git diff --check 通过；独立代码审查无剩余阻断问题。测试只有既有 Starlette 弃用警告。

截至报告封存，Codex及审查子代理运行 pytest **7 次**，包括初次控制台基线、带独立进程退出码的日志复测及审查者一次 15 项验证。Publisher 的必需 core/node 检查在后续交付执行，其实际结果见终态回执。

## 资源与结论边界

四次 CC 墙钟合计约 133.54 秒；CLI 报告 input 70,165、output 19,572、cache-read 390,869 tokens。`total_cost_usd` 合计 1.0355595 为 CLI 估算；MiniMax 实际账单、额度扣减及意外费用 **未知**。没有 GUI、手工搬文件或供应商切换。

收益已证实：外部 CC 真实产出补丁、接受失败证据，并在新会话完成第二任务。额外成本为路由检查、隔离、证据记录、独立验收和返工；没有同题 Codex 单独开发对照，速度、价格和质量优势未证明。轮数上限仍是可靠性限制。

候选位于 `.agents/skills/codex-cc-minimax-dispatch/SKILL.md`，通过格式与只读场景审查，未全局安装、未声称另一真实任务复用通过。下一次应验证不同任务上的精确许可与轮数预算、本地路由开启时的上游辨认。本轮不涵盖历史摄影事实复核、SIMULATED_TEST 等其他门禁规则或生产/UI 发布。

## 复测与证据

```text
python -m pytest -q docs/research/cc-minimax-delegation-pilot-20261010/test_gate_acceptance.py tests/test_research_evidence_gate.py
python -m pytest -q tests/test_library.py tests/test_imports_jobs.py tests/test_workers.py tests/test_operations.py tests/test_personal_library.py tests/test_collection_runner.py
node --check web/app.js
```

[EVIDENCE.json](EVIDENCE.json) 保存脱敏命令、原始任务 prompt、路由日志片段、工具 ID/结果及 usage；[CC_PATCH.diff](CC_PATCH.diff) 保存真实补丁。本目录保存各阶段测试日志。完整脱敏 stream/stderr/debug 和逐调用 diff 留在 ignored `.local/cc-minimax-pilot/`；不含认证正文。worktree 保留复核，未清理其他会话或数据。

Root 在报告封存后按现有 finish-task-publisher 流程提交精确实验路径、推送上述独立分支并核对远端 SHA；实际提交/推送与 Notion 状态以终态回执和最终回复为准，各状态分别验证。

参考：[MiniMax CC 接入](https://platform.minimax.io/docs/m-plan/claude-code)、[CC Switch 路由](https://github.com/farion1231/cc-switch/blob/main/docs/user-manual/en/4-proxy/4.1-service.md)、[CC 权限](https://code.claude.com/docs/en/permissions)。参数行为以当前安装的 help 与真实执行为准。

## 发布检查点恢复

Publisher 必需 core/node 检查通过后，暂存的原始 diff 空上下文行及 pytest 错误日志行尾空白触发 cached diff --check，提交前终止，未产生 commit。其 FAILED 回执与 pending Notion 记录原样保留。自动恢复要求已持久化 prepared_tree；本次在该阶段之前失败，不能用 retry 安全恢复，也未手改发布器状态或重建基线。

根主控按项目允许的等价审查命令继续 Git 交付：只规范化共享日志显示副本的行尾空白，diff 改用真实 --unified=0 输出；原始日志/逐调用 diff 和验收原件保持原样。业务代码、Skill、测试断言及独立验收 SHA 不变。重新核对完整暂存检查、基线 parent、精确13路径及远端 SHA；实际提交/推送结果另存本地恢复回执并在最终回复报告。Publisher/Notion 状态仍为待恢复，不能将手工 Git 成功写成发布器成功。

pytest 实际总次数为 **8**（含 Publisher 额外一次 core 检查），Node 共 **2** 次，Skill 格式校验 **2** 次；本次文档格式恢复未重跑行为测试。
