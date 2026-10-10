# 实际检验记录（Verification Record）

本文档真实记录 Antigravity 在「姿态、重心与角色动作」研究与试读章节建设中的各项验证事实、执行命令与输出结果。

---

## 1. 验证事实与客观证据（Verified Facts & Evidence）

### 1.1 文献与专业知识审查
- **Roberto Valenzuela P3S 系统完整性核实**：
  - 确认并提取了《Picture Perfect Posing》的 15-Point Posing System（脊柱、重心分配、90度关节折角、三点检查法、肘部腰侧间隙负空间、HCS 手臂语境系统、手部造型、手发源可见性等）；
  - 确认其对“大臂压紧躯干导致肌肉横向膨胀、腰线遮蔽”的解剖物理规律；
  - 提取了其“羽毛轻触（Feather Touch）”与“乌龟伸颈（The Turtle）”的具体解剖执行机制。
- **Cosplay 与现场动作实战规范核实**：
  - 提取并对照了 Nikon Imaging Japan COSGENIC 教程（Lesson 1, 3, 4, 11）关于角色气质与动作幅度、日本刀剑剧站姿重心的规范；
  - 提取了 COSPLAY MODE 关于现场口令工程（动词+解剖部位+方位+参照物）与大型道具杠杆平衡的原则。

### 1.2 教学资源与图片显示实际验证
- **HTML 试读页图片路径与物理存在验证**：
  - 执行 `verify_html_images_accurate.py`，对 `docs/research/posing-curriculum-pilot-20261010/reader/index.html` 中引用的全部 5 张实拍照片进行物理路径解析：
    - `images/cos-0001.webp`：存在，107,486 bytes，1080 × 1440
    - `images/cos-0005.webp`：存在，165,024 bytes，1080 × 1402
    - `images/cos-0033.webp`：存在，55,678 bytes，1080 × 1621
    - `images/cos-0041.webp`：存在，67,154 bytes，1080 × 1620
    - `images/cos-0046.webp`：存在，112,674 bytes，1080 × 1620
  - 结果：**全部通过（PASS）**，无任何断链或 404 图片。
- **HTML 语法与交互脚本验证**：
  - 试读页采用纯原生 HTML5/CSS/JavaScript，无任何第三方外网 CDN 依赖，在离线环境下亦可完整渲染暗房样式；
  - 盲测训练区的“展开/收起专业解析”交互逻辑经静态代码检查与 DOM 结构核对，符合标准。

### 1.3 现有仓库与核心测试套件回归验证
在独立分支与独立 worktree `D:\AI PROJECTS\photography-reference-lab-antigravity` 中运行现有回归测试，验证未对现有系统产生任何破坏：
1. **Node 语法检查**：
   - 命令：`node --check web/app.js`
   - 结果：**退出码 0，检查通过**。
2. **核心库回归套件（Core Library Regression Suite）**：
   - 命令：`& "d:\AI PROJECTS\photography-reference-lab\.venv\Scripts\python.exe" -m pytest -q tests/test_library.py tests/test_imports_jobs.py tests/test_workers.py tests/test_operations.py tests/test_personal_library.py tests/test_collection_runner.py`
   - 结果：**123 passed, 1 warning in 72.29s，全部通过**。

---

## 2. 诚实区分：未验证项与主观审美边界（Unverified Scope & Limitations）

1. **真实使用者的审美与教学效果接受度（PENDING）**：
   - 本次通过严密力学分析、图文对照与独立盲测构建了教学样板，但**真实摄影爱好者在实际外拍或漫展中的吸收效率、顿悟体验与实拍改善率**，必须由人类使用者试读并现场实测后给出反馈；
   - 绝不通过自动化脚本模拟“学生测试答题 100 分”来虚构教学有效性。
2. **不同身材与极端服装造型的物理容差（Conditional）**：
   - 试读正文中总结的“手肘离开肋骨两指宽”与“45度躯干侧转”，在常服与轻铠甲上效果显著；但在极端厚重的全覆式重甲、宽大和服振袖或拖地长裙造型中，侧转可能导致布料严重堆叠褶皱或遮挡重要图案，需现场根据服饰具体结构协商调整。
3. **盲测案例的多变量环境限制（Not a Controlled Single-Variable Experiment）**：
   - 盲测案例（COS-031 镰刀低机位）拍摄于特定的多灯暗场环境，具备逆光轮廓光的加持。学习者在杂乱自然光大平光漫展现场复刻时，不可将光影氛围的差异归咎于站姿本身。
