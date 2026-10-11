# Codex 多 Agent 编排：v1.0.0 命名整理

## 当前入口

旧名称`research-code-verifier-orchestration`改为`codex-multi-agent-orchestration`，用户包版本仍是`1.0.0`。这次不增加功能、不改description触发边界，不重跑真实AGY/CC工程实验。

| 用途 | 当前路径 |
| --- | --- |
| 用户级通用Skill | `C:/Users/Dell/.agents/skills/codex-multi-agent-orchestration/SKILL.md` |
| 项目级Skill/领域交接补充 | `.agents/skills/codex-multi-agent-orchestration/SKILL.md` |
| 用户包版本源 | `.forge/codex-multi-agent-orchestration/user-v1/` |
| 当前发现入口/评估集 | `.forge/codex-multi-agent-orchestration/run_discovery.py`、`evals.json` |

用户与项目仍各有各自的正文；没有把摄影浏览路径合并入通用Skill。名称/frontmatter与标题同步，项目既有`agents/openai.yaml`的display_name改为“Codex 多 Agent 编排”，default_prompt改用`$codex-multi-agent-orchestration`，其余属性保持。两个旧活动Skill目录均已移走，没有旧名alias。用户级与项目级同名包不自动合并，本项目继续遵从项目约束。

## 备份与保护

先验证三个绝对目标在授权父目录下、目标不存在且原包无链接；`migrate.py dry-run`实跑PASS。2026-10-11 06:52:55 UTC（北京时间14:52:55）复制原7文件并核对SHA，再迁移目录。原文件恢复副本与原路径/新路径/大小/mtime/hash清单在`.local/orchestration-rename/backup/20261011T065255Z/manifest.json`，执行记录在`.local/orchestration-rename/migration.json`。没有递归删除、覆盖其他Skill或改设置。

已有项目dirty按当前原字节保存在备份及新项目包中，仅授权名称/标签替换；无关dirty、配置与历史报告保持。`SKILL_VALIDATION.md`、`REAL_TASK_REPORT.md`、`VERIFIER_REPORT.md`、`USER_V1_INSTALLATION.md`以及旧任务/原始评估记录的旧名称是当时实际名称，不改写为新名称。旧`.forge/research-code-verifier-orchestration/`只保留此前实验脚本/evals作历史，新入口位于上表新目录；版本源已迁移。

## 验收记录

独立R1–R7标准于2026-10-11 06:50:13 UTC冻结，SHA256 `c9b814cd891d9409a827fec49a3523e47e178dd7ef491e2832104ec270ceaae7`。Verifier独立比对原包、版本源、历史与配置哈希，不读实现过程会话。静态79/79 PASS：原7份备份对应冻结基线，候选只有名称/标题/UI标签变更；description与功能等价，版本/安装源匹配，引用实际存在，旧活动目录不存在，受保护内容未漂移。

ROOT使用现有venv实跑skill-creator `quick_validate.py`，用户/项目/版本源三个目录均返回`Skill is valid!`；`git diff --check`PASS。发现评估实跑10个全新原生Codex会话：首轮7次、补充3次；全部退出0、无超时，但不以退出0或Agent自评代替实际Skill正文读取。

| 原始案例 | PID | 开始–结束 UTC（2026-10-11） | 实际证据与裁决 |
| --- | --- | --- | --- |
| user_explicit_new_name | 38876 | 06:55:54–06:56:52 | 无工具读取事件；完整读取UNVERIFIED，原false保留 |
| user_implicit_neutral_csv | 50040 | 06:55:54–06:56:51 | 完整用户正文读取；未清楚授权后续外部调用，不作为最终授权隐式正例 |
| negative_button_color | 36124 | 06:55:54–06:56:58 | 未读取用户/项目正文，PASS |
| negative_routine_bug | 34564 | 06:56:51–06:57:30 | 未读取用户/项目正文，PASS |
| negative_knowledge_question | 48448 | 06:56:52–06:57:19 | 未读取用户/项目正文，PASS |
| negative_explicit_no_external | 59096 | 06:56:59–06:57:48 | 未读取用户/项目正文，PASS |
| project_explicit_new_name | 51440 | 06:57:19–06:58:24 | 独立审计见项目全文和规则；在外目录启动，项目原生作用域UNVERIFIED；原评估器false保留 |
| user_explicit_actual_read_new_name | 47368 | 07:02:06–07:02:50 | 工具完整读取用户正文，PASS |
| user_implicit_authorized_csv | 35444 | 07:02:06–07:03:03 | 未点名Skill/AGY/CC、未注入正文/路径；自动选择并完整读取用户正文，PASS |
| project_explicit_native_scope | 42060 | 07:02:06–07:03:04 | 原生`-C`项目目录，工具完整读取项目正文和规则，未读用户正文，PASS |

首轮显式可能受原生显式加载影响，但没有可观察的完整工具读取，不能据计划文本补写PASS。首轮项目原评估器未识别完整读取；独立审计确认读取，但其启动目录仍不能证明项目原生发现。保留原prompt/result/events，不删除失败测试，也不改变Skill或冻结标准。补充显式仅增加实际工具读取要求；补充隐式明确后续授权，仍不点名Skill或Agent；补充项目仅纠正实际启动作用域。这是证据补充，Skill返工0轮。

原始每例`started.json`、`events.jsonl`、`result.json`、`final.txt`在`D:/AI PROJECTS/orchestration-rename-validation-20261011/<case>/`，记录PID、完整argv、实际cwd和精确UTC。首轮汇总`.local/orchestration-rename/discovery/summary.json`保持；补充汇总`.local/orchestration-rename/discovery/corrected-01/summary.json`为3/3匹配。实际补充命令：`.venv/Scripts/python.exe -X utf8 .forge/codex-multi-agent-orchestration/run_discovery.py --batch corrected-01 --case user_explicit_actual_read_new_name --case user_implicit_authorized_csv --case project_explicit_native_scope`。脚本拒绝覆盖已有会话证据；本轮不重复成功案例。

独立Verifier审阅全部10次原始尝试后，于2026-10-11 07:05:16 UTC给出R1–R7 **PASS**，范围限命名整理、本地安装、保护及发现。报告`.local/orchestration-rename/verifier/final-report.json`，SHA256 `27c641235c1633e2ea5d3f3588c375b844f6c370c40db8b7b310b7a7f1ab6f22`；冻结标准hash未变。当前用户/版本源正文SHA256 `37521310623eb9da569a166cdfef2a97900d3f18ac532c1785e4e9788c90fe22`，项目正文SHA256 `d4e7d15f66eaabbec4d61ee702faefc116ff60981059a3ba1921d0f1ef73d1eb`，会话前后相同。

可重复的本地格式回归：`.venv/Scripts/python.exe -X utf8 C:/Users/Dell/.codex/skills/.system/skill-creator/scripts/quick_validate.py C:/Users/Dell/.agents/skills/codex-multi-agent-orchestration`；项目包和版本源使用上表对应路径。新会话发现已验证，当前已打开聊天的catalog刷新及任意任务的确定性自动匹配未验证。

## 发布边界

本地用户/项目入口迁移与正式Git交付分开报告。旧项目Skill两文件在本轮immutable baseline中已有前轮dirty；按照Publisher既有dirty保护门禁，项目迁移旧/新六条路径不在本轮提交，保留原内容及本地迁移，不宣称远端项目入口已改名。正式提交限定已提交通用版本源的名称迁移、当前新发现入口/evals及本轮任务/报告。排除路径及归属理由进入清单，不能改baseline或强行包含此前工作。

新事务`01a129b5-9769-7b80-b4c9-a9a7dae0730a`先START/contract再实施；旧成功/失败事务保持，旧失败恢复不在本轮。实际Git/Notion结果以当前Publisher收据和最终消息报告。仍未验证新项目完整工程执行、任意站点及长期无人值守；此次只证明命名整理后的静态等价与发现行为。
