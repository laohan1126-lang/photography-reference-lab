# Source quality audit — PASS 2

**结论范围：**完成当前研究源与候选记录的元数据/资格审计，并对高风险来源和引用做了抽样重开。不是对所有页面或全部候选的逐条语义验证。

## 审计覆盖

检查了 8 个主 scope 及新增的 `cosplay_gap`、`perspective_gap`：**192 条 source 元数据、258 条 candidate**。必需 source 字段齐全，所有 candidate source ID 均能在这些 map 中解析；这些只是结构检查，不证明作者资格、来源独立性或 claim support。

访问状态包括 154 full text、26 partial、10 index-only、2 blocked。按 brief，Tier B 仅适用于实际观看的高质量专业视频；当前 B 标签还出现在文章、课程目录/大纲、未观看视频页，因此均需撤销 B，且 partial/index/blocked 应留在 discovery，不能支撑详细教学主张。

## 优先修正

1. `cosplay-nikon-cosgenic` URL 是 `about.html` 系列索引，不能支持 Lesson 3/5/11 locator。我分别重开 Lesson 3、5、11；须拆成 lesson-specific source IDs。Lesson 5 有多人布局/姿势变化的直接文本，但 source row 缺失。
2. `cosplay-c01/02/07/08/13/14` 修复上述错引后，原有置信度可按各自独立的 cosplay 全文来源重评；PPA适配证据不得额外计成直接共识来源。
3. `post-skin-frequency-separation` 的 PHLEARN 全文确实直接支持纹理/颜色频率分离和过度修饰限制；Fstoppers 重开没有返回正文，检索页指向未观看的 Joel Grimes 视频，不是独立直接来源。建议降为 Aaron Nace 的 medium photographer method。
4. note.com 作者的摄影身份有自述，但未独立核实教学资历。Kujira 付费内容不可读；Sutten 是完整第一人称摄影案例；hia0814 是单次委托拍摄记录。建议 discovery/unranked，或清楚标成单人方法，不用于高置信共识。`cosplay-c12-subject-set-overlap` 目前只有 hia0814 一条案例，应补专业全文来源或转缺口。
5. `perspective-gap-skill-intentional-roll` 的两篇人像资料对角度给出相反指导（Photofacts 30–45°；Nikon Europe 建议小倾斜）。保留分歧，训练“滚转是否读作有意”，不要设普适数字门槛，降为 medium。电影教材仅作 adapted 背景。
6. 动态影像候选已标 `动态影像`，保持与静态人像边界。mot-17/21/22/27/34 依赖 ACMI 教学材料、Canon 摄像机手册或单篇 ASC 文章，不足以标成专业摄影师共识；mot-18 只有一项直接证据，另一项是 adapted 电影指导。建议中置信并注明视频教学/项目迁移。`perspective-skill-shot-scale-vocabulary` 目前仅有两本电影教材，应作为 adapted 术语或补静态摄影来源。
7. 四组跨 scope 重复 URL/教师须去重：Fujiya/Mayuko Ukawa、Nikon Cosgenic about、Canon/Laura Tillinghast、Lindsay Adler 课程页。相同文章、老师或课程概览不能重复计为独立来源。

## 实际重开样本

实际打开了 Cosgenic about、Lesson 3/5/11；COSPLAY MODE 日本刀与小道具文章；PHLEARN 频率分离；Fstoppers Joel Grimes 二手文章（无可用正文）；note.com Kujira、Sutten、hia0814；ANIMEK 活动页；Photofacts 人像 Dutch angle；ASC camera-placement、script-analysis、camera-movement；ACMI cinematography；Canon camcorder PDF（正文未返回）。每项重读范围及限制已逐条写入 JSON。未打开嵌入图片像素。

Field 源/候选文件最后观察修改时间为本地 2026-10-07 23:56；本轮未变。Canonical tree 定稿后需再对照复核。

详细的 90 条 source corrections 和 28 条 candidate corrections 见同目录 `source_quality_pass2.json`。本审计只写这两份 PASS2 报告，没有修改源图谱、候选图谱、UI、共享数据或 Git 历史。
