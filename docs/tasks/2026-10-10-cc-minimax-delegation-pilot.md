# Codex 主控 CC Switch + MiniMax 真实开发实验

## 原始意图与边界

用户要求“不要只写方案，必须实际运行”，由 Codex 唯一主控，在当前会话真实调用 Claude Code CLI，通过 CC Switch 已配置的 MiniMax 完成两个事实门禁修复，再由 Codex 独立测试、审查与最多两轮返工。两个任务都实际完成且独立验收通过后，才创建项目级候选 Skill；失败只交付真实分析，不安装全局 Skill。

实验基线远端 SHA 已核对为 `e290b56499736498cc5999a95c23abe4d9ad1c5f`，来源分支 `antigravity/research-evidence-gate-loop-20261010`。新 worktree `D:/AI PROJECTS/photography-reference-lab-cc-minimax-20261010`，新分支 `codex/cc-minimax-delegation-pilot-20261010`。主工作区、正式课程、原始摄影数据和全局配置不修改；CC 不提交、推送或改配置，不开放任意命令权限。

## 供应商与执行前检查

- 实际 CLI：`C:/Users/Dell/.local/bin/claude.exe`，版本 2.1.220。
- CC Switch 当前 Claude provider 为 MiniMax；数据库、用户 settings 的 endpoint/model/auth 一致。本地 Claude 路由及 failover 均禁用，配置直接请求 `api.minimaxi.com/anthropic`，模型 `MiniMax-M3.1-Flash-Preview`。
- 当前 Codex 进程存在不同的 ANTHROPIC_BASE_URL 与认证覆盖；仅对子进程排除覆盖并使用已配置的 MiniMax 值，不改父进程、认证文件或 CC Switch。不得请求未知路由；真实响应和路由证据不足时停止开发。
- CC 调用采用此版本支持的 session 参数与工具边界；不使用 dangerously-skip-permissions。单次就绪响应、工具事件、文件 diff、退出码、错误和使用量分别记录。

## Blueprint 与独立验收

- Stack：Python/FastAPI、Pydantic v2、pytest；事实门禁自身无外部模型依赖。
- 入口：QualityGateLoop.evaluate → ProgrammaticChecker.audit / SemanticAuditor.audit；CLI 导出准入/返工文件。
- CC 可改：`ref_lab/evidence_gate/checker.py`、`ref_lab/evidence_gate/loop.py`、`tests/test_research_evidence_gate.py`；必要的最小回归测试。Codex 不代替 CC 编写主要修复。
- 禁止改：Codex 独立验收、配置、其他产品代码、课程和历史凭证/摄影资料。
- A/B/C/D 标准使用真实临时非空文件及实际 SHA256；在开发前写入 worktree 外的 Codex 区域并绑定哈希。A 缺失文件拒绝、B 错哈希拒绝、C 正确文件保持 PASS、D 空来源/空断言不得 PASS 或发凭证。
- 已发现基线测试依赖不存在的 scratch 媒体路径及空文件 SHA；修复可能暴露这个冲突，必须改用真实临时文件保留原断言，不能删除失败测试或降级 ERROR。
- 第一项通过后第二项使用新 CC 会话。独立用例、相关门禁回归和配置必需 checks 由 Codex 执行；结构测试不证明摄影事实或媒体视觉真实性。

## 执行结果

待执行，不预填成功。原始调用和 private 日志留在 `.local/cc-minimax-pilot/`；正式报告为 `docs/research/cc-minimax-delegation-pilot-20261010/REPORT.md`。仅由 Codex root 按 explicit owned paths 交付请求的独立分支。

## 实际结果（执行后追加）

- MiniMax 活动配置、direct endpoint、真实响应一致；仅隔离子进程继承覆盖。四次原生 CC 调用，ready/task2 退出 0，task1/rework1 达轮数上限退出 1；配置、路由、独立验收原件均未变。
- CC 独立修改 checker 与门禁测试；缺失、目录、读取失败、错哈希均拒绝。一次主控返工补完 golden 夹具，移除未要求的路径解析；随后第一任务 18 项通过。
- 第二任务使用新 CC 会话：零断言 ERROR，loop/schema 未改。旧断言保留，新增 8 项回归；临时文件明确为结构夹具，不代表摄影事实。
- Codex 独立 5 例 + 门禁 19 例为 24 passed；默认六文件回归 123 passed；Node/Skill 校验与独立审查通过。主工作区、课程、原始数据和供应商配置未被本轮修改。
- 受控外部验收原件 SHA256 始终为 ee6aef2735d6c13766d122bcf694805b9cdbcbf0d4a39325a78f1d4bc2f799e2；所有 CC 调用后原样复制入报告。
- 两项行为修复通过后生成项目级 Skill 候选，无全局安装。MiniMax 实际账单/额度未知，无速度或成本优势、真实跨任务 Skill 复用声明。脱敏原始进程日志保留本地。
- FULL 实验证据和可运行命令见研究报告；根主控随后 seal/finish 独立分支，工程验收与外部交付状态分开记录。
