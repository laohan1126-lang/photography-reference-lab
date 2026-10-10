# Antigravity 独立摄影教学研究 Loop｜姿态、重心与角色动作

## 1. 任务背景与用户意图

你现在担任 photography-reference-lab 项目的**独立摄影教学研究员与课程设计者**。
Codex 正在另一条线上研究课程架构及「机位、焦段与透视」。你不需要等待 Codex，也不要与它重复开发同一部分。
你的任务是独立证明：Antigravity 能否从可靠的专业摄影资料出发，研究、组织并制作出真正有教学价值的摄影课程。

项目的最终使用者是一位已有一定实拍经验、以 Cosplay、漫展场照和人像为主要方向的摄影爱好者。他需要逐渐获得独立的摄影判断力，而不是继续积累摄影术语、知识卡片和待完成的技能清单。

**本轮成功标准是教学质量，而不是工程工作量。执行原则：先做专业摄影研究，再做课程，最后才考虑工程集成。**

## 2. 基线与隔离边界

- 基线分支：`codex/evidence-photography-atlas`
- 基线提交：`b8807fe02f23d75887f464fc53a5ebe9f346582d`
- 专属分支：`antigravity/posing-curriculum-pilot-20261010`
- 专属工作目录：`D:\AI PROJECTS\photography-reference-lab-antigravity`（独立 Git worktree）
- 禁止直接修改、重置或合并 Codex 分支及 main。禁止改动用户的原始图片、反馈、个人学习状态和其他日用数据。
- 原则上不修改现有 SKILL_TREE、LEARNING_CONTENT、GATEWAYS 及生产 UI。研究与课程原型使用独立目录 `docs/research/posing-curriculum-pilot-20261010/`。
- 不调整系统代理、全局网络配置或其他 Agent 的运行环境。

## 3. 六个阶段目标与可检验验收标准

1. **第一阶段：独立审查现有知识体系**
   - 审查现有技能树中的三个相邻领域：姿态、重心与身体线条；角色、表情与人物指导；服装、假发与仿制道具。
   - 回答专业摄影师如何组织姿态教学、连续讲解 vs 临场查阅、人体-画面-角色-指令连接、底层索引 vs 章节划分 4 个核心问题。
2. **第二阶段：真正研究专业教材与摄影师教程**
   - 重点研读 Roberto Valenzuela《Picture Perfect Posing》(拍出绝美姿态 / 完美姿态系统)、《Picture Perfect Practice》、官方专业人像/Cosplay 指南及实战教程。
   - 深入理解重心承重、身体朝向/肩线/头颈躯干、手臂与身体间隙（负空间）、前倾/倚靠/站姿、道具参与、姿态过渡和简洁指令。
   - 记录作者、原始链接、实际阅读范围与支持结论，绝不拿视频标题或搜索摘要冒充掌握。
3. **第三阶段：重新组织课程大纲**
   - 提出面向真实人像摄影的「人物姿态与角色动作」课程大纲。
   - 明确区分摄影原理、摄影师经验、项目教学、审美选择四种属性，映射现有能力地图。
4. **第四阶段：制作一章可以实际学习的试读课程**
   - 主题：《为什么人物摆姿势会显得拘谨、缩成一团或缺乏力量？》（真人 Cosplay、人像与持道具姿态）。
   - 全面覆盖 6 大问题：观察问题、局促成因、支撑/转向/四肢调整、符合角色表达、现场指导指令、副作用与现场验证。
   - 具备足够大且细节清晰的真实图片解析与前后对比，以独立 HTML 图文试读页呈现。
5. **第五阶段：检验实际教学价值**
   - 设计至少一个正文未直接讲解的盲测真人照片案例：读者先自主观察与判断，再揭示专业分层解析与改善代价。
   - 检查真实图片加载、专业事实与图文对应。
6. **第六阶段：交付与协作**
   - 提交推送到专属分支 `antigravity/posing-curriculum-pilot-20261010`。
   - 输出完整教学样板、专业资料清单、新大纲与技能映射、HANDOFF 报告、实际检查记录。

## 4. Outcomes

### 4.1 独立审查与文献研究完成
- 完成对现有能力地图中 `posing`（18 技能）、`character`（17 技能）、`costume`（11 技能）三大相邻领域的独立审查，完整解答了专业摄影师姿态教学组织结构、连续讲解 vs 临场查阅界限、人体-画面-角色-指令连接链条、以及底层知识索引的定位。
- 深入研读并提取了 Roberto Valenzuela《Picture Perfect Posing》的 15-Point Posing System (P3S) 解剖力学模型（脊柱、单腿承重、对立平衡 Contrapposto、大臂压紧肋骨的形变与负空间塌陷灾难、羽毛轻触与乌龟伸颈），以及 Nikon COSGENIC 系列、COSPLAY MODE 动作顾问专题、Peter Hurley 肖像眼神法等实战体系。形成独立记录 `docs/research/posing-curriculum-pilot-20261010/SOURCES.md`。

### 4.2 课程重构大纲与技能映射
- 确立面向真实人像与 Cosplay 摄影的 6 阶递进课程大纲《人物姿态、重心与角色动作：从生理力学到镜头剧力》，严格标示【原理】、【经验】、【教学】与【审美】四层属性，并与现有 46 项原子技能建立完整映射。形成大纲文档 `docs/research/posing-curriculum-pilot-20261010/CURRICULUM_OUTLINE.md`。

### 4.3 完整试读样板与独立交互阅读器
- 撰写并产出深度试读章节《为什么人物摆姿势会显得拘谨、缩成一团或缺乏力量？》（`docs/research/posing-curriculum-pilot-20261010/PILOT_CHAPTER.md`），全面解答了成片视觉诊断、解剖力学成因、三步动作重构工程（地基-负空间-末梢）、角色戏剧叙事对齐、现场口令工程（动词+解剖部位+方位+参照物）与副作用警示四大边界。
- 构建了面向用户的独立 HTML 交互式试读页（`docs/research/posing-curriculum-pilot-20261010/reader/index.html`），采用视觉暗房设计，真实加载 5 张 1080p 高清实拍 WebP 大图，支持盲测案例折叠揭晓互动。
- 产出了正文未解析的盲测案例深度实战训练《长柄重型武器与暗场低机位的姿态解剖》（`docs/research/posing-curriculum-pilot-20261010/BLIND_CASE_ANALYSIS.md`），提供读者自主判断引导、四维专业解构、以及下一张微调方案与 Trade-offs 权衡。

### 4.4 实际验证与回归结果
- **图片与路径真实性**：脚本验证试读页引用的 5 张实拍照片（`cos-0001`, `cos-0005`, `cos-0033`, `cos-0041`, `cos-0046`）全部物理存在、可读、无 404；
- **代码与回归测试**：`node --check web/app.js` 通过；核心库回归测试套件（`test_library.py`, `test_imports_jobs.py`, `test_workers.py`, `test_operations.py`, `test_personal_library.py`, `test_collection_runner.py`）**123 passed, 1 warning**，全部通过；
- 形成实际检验记录 `docs/research/posing-curriculum-pilot-20261010/VERIFICATION.md` 与交接报告 `docs/research/posing-curriculum-pilot-20261010/HANDOFF.md`。
