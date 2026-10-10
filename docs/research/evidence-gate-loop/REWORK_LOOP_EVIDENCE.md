# 研究事实自动验收与返工质量门禁（Quality Gate Loop）实证报告

> **项目名称**：Photography Reference Lab 研究事实质量门禁与返工闭环
> **分支**：`antigravity/research-evidence-gate-loop-20261010`
> **基线 Commit**：`beae2514e113ab6ede2c4fe6753d00d7ca248d9e`
> **执行日期**：2026-10-10
> **核心机制**：研究 Agent 结构化证据交付 $\rightarrow$ 两层独立检查（程序化事实核验 + 独立语义审查） $\rightarrow$ 机器可读返工包（`REWORK_PACKAGE.json`，上限 2 轮） $\rightarrow$ 准入凭证（`ADMISSION_RECEIPT.json`）

---

## 一、 系统架构与问题背景

### 1.1 核心痛点与解决策略

在上一轮研究中，Agent 容易出现以下关键问题：
1. **虚假自评通过**：研究 Agent 生成一篇长文后，自行声明 `verified=true` 即宣布成功，缺乏外部制衡。
2. **事实与推断混淆**：把摄影师从未说过的对白（如叹气说“像个小棍子”）、主观臆想的机械结构（如“下蹲是建立力学三角支架消除身体颤动”）冒充为一手客观事实。
3. **器材跨文档矛盾与时间穿越**：同一视频在不同文档中被写成不同相机型号（Canon R5 vs Sony A7R），或在 2024 年初的视频中声称使用了 2025 年末发布的器材。
4. **伪精确数字**：凭空捏造无测量依据的数字比例（如 90/10、60/40）和死板角度（30°-60°）。

本项目在 `ref_lab/evidence_gate/` 中构建了一套轻量、严密、可执行的**研究质量门禁引擎**，彻底改变工作机制：
$$\text{研究 Agent 交付证据} \longrightarrow \text{独立门禁审查} \longrightarrow \begin{cases} \text{合格 (PASS)} \longrightarrow \text{颁发准入凭证} \longrightarrow \text{准入正式课程} \\ \text{不合格 (REVISE)} \longrightarrow \text{生成返工包} \longrightarrow \text{限期返工 (最多2轮)} \\ \text{严重违规/超限 (BLOCKED)} \longrightarrow \text{彻底熔断阻断} \end{cases}$$

---

## 二、 模块设计与代码结构

代码严格遵循本地优先、无外部网络依赖、可测试原则，完全内置于 `ref_lab`：

```
ref_lab/evidence_gate/
├── __init__.py           # 模块导出与类型暴露
├── models.py             # Pydantic v2 严苛结构化 Schema (A/B/C/D 分级、证据包、返工包、凭证)
├── checker.py            # 第一层：程序化事实检查引擎 (时长溢出/哈希/器材矛盾/时间线/伪精确数字/链接黑名单)
├── semantic_audit.py     # 第二层：独立语义审查引擎 (ASR逐字稿比对/虚构对白拦截/意图僭越/伪科学过度假说)
├── loop.py               # 门禁循环调度器 (状态机控制/返工轮次限制/凭证发放)
└── cli.py                # 命令行交互与自动化集成接口
```

### 2.1 结构化证据输入 Schema (`models.py`)

- **四级认知台账体系**：
  - **A 级（直接观察）**：视频画面中明确出现的物体、操作、动作或画面变化。
  - **B 级（作者表达）**：摄影师音频原声、字幕或简介自述，必须附带时间码与真实引用。
  - **C 级（专业解释）**：经典物理光学、几何透视或人体解剖学学理解释，需指明理论依据与适用条件。
  - **D 级（项目推断）**：本项目提出的建议或待验证假设，严禁冒充前三者。
- **强制忽略自封验证**：`self_attested_verified: Optional[bool]` 字段即使被研究者标为 `true`，系统会触发 `SELF_ATTESTATION_IGNORED` 警告，严禁作为门禁通过依据。

### 2.2 第一层：程序化事实核验 (`checker.py`)

1. **链接真实性与黑名单匹配**：自动阻断已知无关旅行 Vlog（如 Manny Ortiz 加尔各答街头 Vlog `I6sdXDIjo50` 冒充姿态教程）。
2. **时间码边界检查**：比对 `source.duration_seconds`，时间码溢出（如 450s > 340s）直接拦截。
3. **截图与时间段吻合性**：检查截图时间戳是否落在 `[start - 5s, end + 5s]` 窗口内，防止张冠李戴。
4. **器材跨文档矛盾核验**：比对权威设备列表（Canon R5）与声称器材（Sony A7R），发生矛盾立即报错。
5. **硬件发布时间线核验**：维护硬件上市知识库，发现 2024 年视频声称使用 2025 年硬件时触发 `TIMELINE_ANACHRONISM`。
6. **伪精确数字拦截**：正则扫描无实测传感器依据的 `90/10`、`60/40`、`30°-60°` 等杜撰数字。
7. **本地媒体哈希与完整性**：核验本地视频/音频文件的存在性与 SHA256 指纹。

### 2.3 第二层：独立语义审查 (`semantic_audit.py`)

1. **对白音频逐字稿核验**：
   - 提取声称的摄影师对白，在对应时间码段落与 Whisper 逐字稿进行文本和语义比对。
   - 精准捕获并拦截历史虚构词（如“像个小棍子”），指出真实原话为“因为这样一只手，你把那只手完全挡完了！”。
2. **意图与推断僭越检测**：
   - 拦截将主观力学推测（如“力学三角支架消除身体颤动”）归为摄影师本意或直接观察的僭越行为（真实动机为摄影师自述“硬一点的姿势没那么会，后面全拍蹲着的”）。
3. **伪科学过度假说套用**：
   - 拦截将肌肉疲劳等简单力学问题过度引申为“胎儿期防御性惊跳反射”等无医学证据支持的生物学假说。

### 2.4 自动返工状态机与轮次控制 (`loop.py`)

- **决策分支**：
  - 无错误：输出 `PASS`，生成包含确定性哈希的 `ADMISSION_RECEIPT.json`。
  - 存在事实错误且 `cycle < 2`：输出 `REVISE`，生成结构化 `REWORK_PACKAGE.json`。
  - 媒体不可访问或 `cycle >= 2`：输出 `BLOCKED`，永久停止该轮自动推进。
- **自动化边界清晰度**：
  - **完全自动化层**：门禁评测、规则检查、哈希校验、返工包生成、结果导出均由代码全自动执行。
  - **人机协同接力层**：返工包以机器可读 JSON 输出，Agent 针对返工包中的 `remediation_guidance` 修正断言，修正后重新提交。最多允许两轮返工，避免无限死循环。

---

## 三、 红队自动化测试结果

在 `tests/test_research_evidence_gate.py` 中编写了 11 项全覆盖红队测试，覆盖所有已知历史失败案例和正确样本：

| 测试用例函数 | 测试目标 / 历史失败场景 | 拦截结果 | 状态 |
| :--- | :--- | :--- | :---: |
| `test_redteam_sony_a7r_contradiction` | Canon R5 被错误写成 Sony A7R IV | 拦截：`EQUIPMENT_CONTRADICTION` | **PASSED** |
| `test_redteam_hallucinated_little_stick_dialogue` | 虚构摄影师叹气说“剑像小棍子” | 拦截：`VERBATIM_HALLUCINATION` | **PASSED** |
| `test_redteam_manny_vlog_url_mismatch` | Manny Ortiz 加尔各答旅行 Vlog 冒充教程 | 拦截：`URL_MISMATCH_VLOG` | **PASSED** |
| `test_redteam_screenshot_timestamp_mismatch` | 截图时间（04:30）与引用段落（01:45）错配 | 拦截：`SCREENSHOT_TIMESTAMP_MISMATCH` | **PASSED** |
| `test_redteam_timeline_anachronism` | 2024年3月视频声称使用了 2025年末发布的机型 | 拦截：`TIMELINE_ANACHRONISM` | **PASSED** |
| `test_redteam_pseudoscience_and_pseudo_precision` | 胎儿期惊跳反射假说与 90/10 虚构承重比 | 拦截：`PSEUDOSCIENCE_OVERGENERALIZATION`<br>+ `UNVERIFIED_PSEUDO_PRECISION` | **PASSED** |
| `test_redteam_timestamp_out_of_bounds` | 时间戳（450s）超出视频总时长（340s） | 拦截：`TIMESTAMP_OUT_OF_BOUNDS` | **PASSED** |
| `test_redteam_unaccessible_media_blocks` | 媒体文件未下载或无法访问 | 拦截：`MEDIA_UNACCESSIBLE` $\rightarrow$ `BLOCKED` | **PASSED** |
| `test_rework_loop_cycle_limit` | 返工轮次达到上限（第 2 轮仍失败） | 熔断：从 `REVISE` 转为 `BLOCKED` | **PASSED** |
| `test_self_attested_verified_neutralized` | 研究者自填 `verified=true` 试图绕过门禁 | 报警：`SELF_ATTESTATION_IGNORED` 并拦截真实错误 | **PASSED** |
| `test_golden_sample_passes_and_issues_receipt` | 校准后的真实正向样本（小言Jun + 林海音） | 验收：`PASS` 并生成 `ADMISSION_RECEIPT.json` | **PASSED** |

**执行命令与输出**：
```bash
pytest tests/test_research_evidence_gate.py -v
```
```
======================== 11 passed, 1 warning in 0.64s ========================
```

---

## 四、 小言Jun 视频真实端到端试验复盘

我们选取小言Jun漫展走廊教学视频（`BV1MD421L7VK`），在磁盘上进行了真实两轮端到端闭环试验：

### 4.1 第一轮：输入错误包并触发自动门禁

- **输入文件**：[`docs/research/evidence-gate-loop/EVIDENCE_PACKAGE_INITIAL.json`](file:///D:/AI%20PROJECTS/photography-reference-lab-gate-20261010/docs/research/evidence-gate-loop/EVIDENCE_PACKAGE_INITIAL.json)
- **故意植入的缺陷**：
  1. `claim-1.1`：声称器材为 `Sony A7R IV + 35mm 定焦`；
  2. `claim-1.2`：虚构对白 `你看剑根本看不出来，像个小棍子`；截图时间设为 `270.0s`（与 `105-134s` 错配）；
  3. `claim-1.3`：套用 `胎儿期防御性惊跳反射` 并断言 `90/10 变成 60/40`；
  4. 全体断言附带 `self_attested_verified: true` 试图自封通过。

**门禁执行命令**：
```bash
python -m ref_lab.evidence_gate.cli --input docs/research/evidence-gate-loop/EVIDENCE_PACKAGE_INITIAL.json --cycle 1 --output-dir docs/research/evidence-gate-loop
```

**门禁反馈（Exit Code: 1）**：
```json
{
  "decision": "REVISE",
  "cycle": 1,
  "max_cycles": 2,
  "saved_artifacts": {
    "rework_package": "docs/research/evidence-gate-loop/REWORK_PACKAGE.json"
  },
  "summary": "Gate evaluation REVISE at cycle 1/2: Found 9 fact/semantic error(s) across 3 claim(s).",
  "affected_claims": [
    "claim-1.1",
    "claim-1.2",
    "claim-1.3"
  ],
  "issue_count": 12
}
```

门禁成功阻止了不合格内容，并在 [`docs/research/evidence-gate-loop/REWORK_PACKAGE.json`](file:///D:/AI%20PROJECTS/photography-reference-lab-gate-20261010/docs/research/evidence-gate-loop/REWORK_PACKAGE.json) 中生成了精准修复指引：
- 指令 1：校准设备为作者自述 Canon R5 + RF 50mm f/1.8；
- 指令 2：将虚构对白替换为 02:08 真实录音“因为这样一只手，你把那只手完全挡完了！”；将截图时间修正至 115.0s；
- 指令 3：剔除胎儿期惊跳反射与 90/10 假数字，替换为等长肌肉疲劳力学与仰角视点透视原理；
- 指令 4：警告并忽略一切 `self_attested_verified` 标记。

---

### 4.2 第二轮：根据返工包修复并最终通过准入

- **修复输入文件**：[`docs/research/evidence-gate-loop/EVIDENCE_PACKAGE_REVISED.json`](file:///D:/AI%20PROJECTS/photography-reference-lab-gate-20261010/docs/research/evidence-gate-loop/EVIDENCE_PACKAGE_REVISED.json)
  - 针对返工包的每项要求完成真实纠正；
  - 引用与事实全部对齐校准账本。

**二次门禁执行命令**：
```bash
python -m ref_lab.evidence_gate.cli --input docs/research/evidence-gate-loop/EVIDENCE_PACKAGE_REVISED.json --cycle 2 --output-dir docs/research/evidence-gate-loop
```

**门禁反馈（Exit Code: 0）**：
```json
{
  "decision": "PASS",
  "cycle": 2,
  "max_cycles": 2,
  "saved_artifacts": {
    "receipt": "docs/research/evidence-gate-loop/ADMISSION_RECEIPT.json"
  },
  "receipt_id": "rcpt_pkg_xiaoyanjun_posing_study_20261010_5d5e766421",
  "total_claims_verified": 3,
  "manifest_hash": "5d5e766421d52898d9ed9549ee7a548f7820021b6979cac38dd7e2a51a629da3"
}
```

系统正式颁发了准入凭证 [`docs/research/evidence-gate-loop/ADMISSION_RECEIPT.json`](file:///D:/AI%20PROJECTS/photography-reference-lab-gate-20261010/docs/research/evidence-gate-loop/ADMISSION_RECEIPT.json)：
```json
{
  "receipt_id": "rcpt_pkg_xiaoyanjun_posing_study_20261010_5d5e766421",
  "package_id": "pkg_xiaoyanjun_posing_study_20261010",
  "verified_at": "2026-10-10T10:43:57.834847+00:00",
  "decision": "PASS",
  "total_claims_verified": 3,
  "approved_manifest_hash": "5d5e766421d52898d9ed9549ee7a548f7820021b6979cac38dd7e2a51a629da3",
  "scope": "photography_course_curriculum"
}
```

---

## 五、 与现有任务发布流程（finish-task-publisher）的协同关系

1. **环境与分支边界隔离**：
   - 本次工作在全新独立 worktree `D:\AI PROJECTS\photography-reference-lab-gate-20261010` 和独立分支 `antigravity/research-evidence-gate-loop-20261010` 下展开；
   - 绝不改动主项目运行环境、主干分支及现有摄影师日用服务。
2. **正式课程研究准入契约**：
   - 现有的 `finish-task-publisher` 负责代码与工程维度的提交与推送；
   - 本套 Quality Gate 作为**摄影知识内容正式准入的专业事实门禁**：未来任何研究成果必须持有有效的 `ADMISSION_RECEIPT.json`，且其 `approved_manifest_hash` 与研究清单内容指纹匹配，才能被正式课程构建器引入。
3. **真实性与不可伪造性**：
   - 凭证哈希强绑定清单全文；若研究者擅自修改任何断言或结论，哈希校验将立即失效。
