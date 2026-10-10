# Antigravity Loop｜摄影真实视频研究与专业决策补全

## 1. 任务背景与核心意图

继续 photography-reference-lab 的独立摄影教学研究。
针对上轮存在的核心缺口：**理论解释较丰富，但缺少对职业摄影师真实拍摄过程的充分研究。**

本轮目标是弄清楚：
**专业摄影师面对人物姿态、机位和动作表现问题时，实际上怎样观察、判断、调整与完成照片？**
重点研究共同问题：
**持剑人物前倾时，摄影师怎样同时处理人物气势、姿态张力、身体比例、道具和现场空间？**

允许寻找相邻的人像姿态、运动人物及其他道具摄影案例，但必须说明为什么能迁移。不能将短匕首、长剑、大剑的动作直接视为等价。

## 2. 隔离边界与执行原则

- 基线分支：`antigravity/posing-curriculum-pilot-20261010`
- 基线提交：`5d2e6d760408ff078953981bdb8dd94f55a24c60`
- 专属分支：`antigravity/posing-video-evidence-20261010`
- 专属工作目录：`D:\AI PROJECTS\photography-reference-lab-antigravity`
- 禁止直接修改 Codex 分支或 main。
- 坚持教学质量与事实求是：严格区分实际操作（A）、作者解释（B）、原理解释推断（C）与未知盲区（D）；严禁脑补心理活动，严禁伪装单变量实验。
- 审查并纠偏上轮存在的理论绝对化（90/10承重、手臂视觉宽度精确百分比、两指宽、严格15度折角、防御反射术语）。

## 3. 验收标准与交付清单

1. `VIDEO_SOURCE_LOG.md`：深入检查 3-5 个真正有价值的专业实拍与姿态指导视频，记录作者、链接、实际观看范围及关键时间码；
2. `SHOOTING_DECISIONS.md`：深入分析持剑前倾、身体比例、气势与空间决策过程，严格区分四层事实；
3. `LESSON_PATCH.md`：完成专题教学《职业摄影师怎样把局促、无力的持剑姿态调整为有明确角色表达的动作？》，集成真实前后对照画面与决策链条；
4. 全面审查并纠偏现有课程（`PILOT_CHAPTER.md`, `SOURCES.md`, `CURRICULUM_OUTLINE.md`, `reader/index.html`）；
5. `HANDOFF.md`：供 Codex 独立审查和整合的交接说明。

## 4. Outcomes & Verification

### 4.1 核心交付成果
1. **真实视频研读与日志归档**：
   - 完成 `docs/research/posing-curriculum-pilot-20261010/VIDEO_SOURCE_LOG.md`；
   - 深入审查并解帧 5 部专业视频，核心为小言Jun B站实录 `BV1MD421L7VK`（302s 全片分析，01:45-05:01 女侠持剑斗笠姿势四阶段实录），横向对照松田理奈（杀阵动作重心）、Roberto Valenzuela（B&H 实战负空间）、Manny Ortiz（腰平机位透视中和）、Yume（短视频持剑反例局限）。
2. **现场多变量决策深度解剖**：
   - 完成 `docs/research/posing-curriculum-pilot-20261010/SHOOTING_DECISIONS.md`；
   - 严格依照 **[A 实际操作]**、**[B 摄影师自述]**、**[C 原理推断]**、**[D 未知/未验证]** 四级标准，全景解构“前倾持剑”中的气势、比例、道具轴向短缩与空间避让冲突。
3. **原有理论绝对化断言校准**：
   - 彻底校准 `PILOT_CHAPTER.md`、`SOURCES.md`、`CURRICULUM_OUTLINE.md` 与 `reader/index.html`；
   - 将 90/10 承重法则降级为站姿非对称承重启发法，与 60/40 战斗弓步明确区分；
   - 消除伪精确 20%~30% 增粗百分比，改为 2D 投影黏连与腰线遮蔽机理；
   - 将两指宽间隙校准为依袖型而定的负空间窗口；
   - 将 15° 关节折角校准为防范无意识肌肉锁死超伸，允许刚性直线；
   - 剔除胎儿防御反射进化心理学假说，改为被动常态习惯与 2D 空间失察。
4. **专题教学增补完整成稿**：
   - 完成 `docs/research/posing-curriculum-pilot-20261010/LESSON_PATCH.md`：《职业摄影师怎样把局促、无力的持剑姿态调整为有明确角色表达的动作？》；
   - 输出完整的摄影师现场口令指挥卡与学习者自检表。
5. **交互试读页升级与交接报告**：
   - 升级 `docs/research/posing-curriculum-pilot-20261010/reader/index.html`，集成现场决策特辑与全新导航；
   - 更新 `docs/research/posing-curriculum-pilot-20261010/HANDOFF.md`，提供供 Codex 深度整合的理论交接接口。

### 4.2 实际执行验证证据
- **测试套件运行**：
  `python -m pytest -q tests/test_library.py tests/test_imports_jobs.py tests/test_workers.py tests/test_operations.py tests/test_personal_library.py tests/test_collection_runner.py`
  - 结果：`123 passed in 1.49s`。
- **前端语法校验**：
  `node --check web/app.js`
  - 结果：退出码 0，无语法错误。
- **静态试读页验证**：
  `file:///D:/AI%20PROJECTS/photography-reference-lab-antigravity/docs/research/posing-curriculum-pilot-20261010/reader/index.html`
  - 结果：布局整洁，锚点跳转正常，盲测折叠正常，图片引用正常。

