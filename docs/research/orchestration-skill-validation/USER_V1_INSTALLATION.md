# 用户级编排 Skill v1 安装与验证

## 已安装内容

用户目标是让 Codex 面对复杂项目自动判断并调用现有 CC/AGY，最后审核结果。本轮通用包版本 `1.0.0`，安装于 `C:/Users/Dell/.agents/skills/research-code-verifier-orchestration/`；原名称保持，自动发现沿用默认设置。无需每次点名代理，已有有效授权继续有效。

| 文件 | SHA256 |
| --- | --- |
| SKILL.md | b2cbe177b37961b8beea4201bb9a26fe4c427a3d4f6dffead8abbdedf57efb6e |
| references/external-handoffs.md | b61392c90b7c093c4a97bd9e0e9d0d9f1de44b2fdb5c7f8f5676e2d215b7f1be |

两个安装文件与版本源 `.forge/research-code-verifier-orchestration/user-v1/` 逐字节一致；安装前目标目录不存在，采用新文件独占创建，无覆盖。安装于2026-10-11 06:16:20 UTC（北京时间14:16）。原项目Skill保持；同名项目与用户Skill不会自动合并，本项目继续服从项目约束，其他项目使用自包含用户包。

## 工作方式与领域边界

Codex根据任务选择实际有用的角色。研究交AGY，实现交CC，独立Verifier冻结标准并验收，Codex最终检查真实diff、证据、目标覆盖及未解决问题，再整合交付。只有独立任务并行；内容接入等待研究结果；每任务最多两轮定向返工。只返回CLI SUCCESS、自述、标题或未核验资料都不算完成。

通用包没有摄影仓库、Chrome实例、具体来源URL、私有策略、配置或浏览脚本路径。当前项目的领域Skill/指引承担浏览器、视频、摄影、架构及权限配置。任务不需研究就不派AGY，普通修改、问答或未授权外部执行不强制进入编排。安装不会改变代理、凭据、供应商、权限、hooks或日用服务；实际复用仍先探测当前工具和能力。

可直接给复杂项目目标，例如：“研究公开规范，为导入工具实现一个兼容功能，独立验收后交付；沿用我已授权的外部协作工具。”也可显式说：“使用 `$research-code-verifier-orchestration` 组织这个任务。”已有授权不需要每次重复声明；缺少新能力或超出授权仍如实处理。

## 当前验证

- `skill-creator/scripts/quick_validate.py` 用项目现有 `.venv` 实跑PASS；首次使用另一现有Python因缺PyYAML未能运行，保留为环境失败，未安装依赖。
- ROOT相对链接检查PASS：资源都在包内，无绝对机器路径或摄影仓库依赖。独立静态审查计算两文件hash一致、版本/引用可用，32项既有dirty与3份配置hash均保持。
- 独立验收于2026-10-11 06:12:57 UTC冻结，标准SHA256 `8d42689c344ef603945af1331a7a9e13b87a38c3f088ff61acafcb9b86afa883`；未读取实现会话，不改候选或发布。
- 原生fresh Codex会话在摄影仓库外实际进行发现测试，结果完成后追加；正例要求完整读取安装正文，负例包括按钮色、普通bug、知识问答与未授权外部任务。所有测试为提示词约束的只读规划，宿主policy不是只读OS沙箱。
- 初始两个正例确实读取用户级正文，但任务措辞仍指向摄影项目，随后读取该项目。它们只证明仓库外发现，不满足领域脱离；原记录保留，追加两次中性CSV规范/导入工具目标的新会话。此为测试设计修正，未改Skill候选或冻结标准。

### 原生发现结果

Codex CLI `0.159.2`，8个独立ephemeral thread，最多3个并发。表内时间均为2026-10-11 UTC；全部exit 0、无timeout。正例以成功工具事件返回安装文件完整正文为证据，四个负例没有读取目标Skill、没有派AGY/CC。原生进程退出本身不是判定标准。

| 任务 | PID | 开始–结束 UTC | 用户级正文读取 | 已观察摄影仓库访问 | 结论 |
| --- | ---: | --- | --- | --- | --- |
| 初始显式摄影目标 | 51900 | 06:19:59.772865–06:23:39.833296 | 是 | 是 | 发现PASS；不用于领域脱离 |
| 初始隐式摄影目标 | 51860 | 06:19:59.771158–06:23:40.348974 | 是 | 是 | 发现PASS；不用于领域脱离 |
| 按钮颜色 | 60320 | 06:19:59.772865–06:21:38.956795 | 否 | 是 | 未误触发PASS |
| 普通bug | 48824 | 06:21:39.125277–06:22:49.918503 | 否 | 否 | 未误触发PASS |
| 知识问答 | 60856 | 06:22:50.061684–06:23:34.253855 | 否 | 否 | 未误触发PASS |
| 复杂但禁止外部执行 | 37576 | 06:23:34.341487–06:27:28.957138 | 否 | 是 | 授权边界PASS |
| 中性CSV显式目标 | 53264 | 06:28:53.784057–06:29:59.762266 | 是 | 否 | 跨领域发现PASS |
| 中性CSV隐式目标 | 46384 | 06:28:53.784057–06:29:45.886474 | 是 | 否 | 跨领域自动选择PASS |

CSV隐式prompt没有Skill、AGY或CC名称；两条CSV目标均明确源码尚未提供，禁止搜索其他仓库。两会话只读取用户级Skill，自动提出AGY研究、CC实现、独立Verifier和Codex最终审核；没有编造解析库、接口或规范阅读结果。此检查证明其他工作目录下的发现与跨领域选择，尚未证明在另一真实代码项目中完整实施。四个负例保持各自原prompt，不用CSV正例覆盖其结果。

每例`started.json/events.jsonl/stderr.txt/final.txt/result.json`原文件位于`D:/AI PROJECTS/orchestration-user-v1-validation-20261011/<case>/`。汇总在`.local/user-orchestration-v1/discovery/all_8_sessions_summary.json`；候选hash前后保持，不向会话注入Skill正文或实现结果。

### 独立最终验收

Verifier于2026-10-11 06:34:10 UTC给出冻结V1-01至V1-10 **PASS**，限用户级安装、通用边界与跨目录/跨领域发现；不是任意项目稳定性证明。裁决SHA256 `8bc70f06c79beb4457815130cd7fc852147af33ab23fb76479f1397b07795f28`，完整报告/裁决/8例独立审计在`.local/user-orchestration-v1/verifier/FINAL_REPORT.md`、`FINAL_VERDICT.json`、`DISCOVERY_AUDIT.json`。原冻结标准hash保持；Skill无确认缺陷，0轮返工，没有为满足流程制造问题。

独立审查逐条核对成功工具输出，四正例正文与安装字节精确匹配（PowerShell仅额外增加CRLF）；CSV两例各只执行一条安装Skill读取命令。32项既有dirty、3份配置、旧失败事务4份文件的hash全部匹配。历史真实AGY capture/view/write、CC Read/Edit和四份研究源/副本hash另行复核；CC内容接入exit 1/error_max_turns及工具失败仍保留，只作已验证项目流程的历史支持。Verifier未读实现对话/prompt文件、未改候选、未调用外部工具或发布。

ROOT最终审核确认安装包与接受版本相同、角色与授权边界符合用户目标、独立结论没有未解决候选缺陷、发现结果与真实执行没有混称。复用从当前项目的实际工具/权限探测开始；领域适配仍由该项目负责。

## 证据与交付边界

原始安装、保护、发现事件与独立审查保留在Git忽略的 `.local/user-orchestration-v1/`，中性测试工作区在D盘。只提交本轮新的通用包、任务与安装报告；旧dirty、原图、私人配置、代理/令牌、数据库不提交。

本轮不是新的跨领域AGY/CC真实执行实验；已验证摄影项目中的真实链路记录见既有REAL_TASK_REPORT/VERIFIER_REPORT，用户级包的跨项目发现和领域脱离在本轮另验。其他项目外部权限、网站/视频能力、长期无人值守、主人审美与旧手机媒体竞态没有因安装而变为已验证。

旧failed Publisher canonical state/receipt与原始保存的finish结果JSON完全相等，原baseline/manifest/收据保留，不用本轮baseline恢复旧工作；当前任务有自己的先于编辑的immutable transaction和两个精确外部安装路径。Git/Notion交付独立以本轮实际Publisher收据及最终消息报告，工程验收不能预判发布成功。
