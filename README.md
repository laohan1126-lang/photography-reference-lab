# Photography Reference Lab (漫展与Cosplay摄影实战参考系统)

基于真实 Cosplay 摄影出片实战、二次元角色特征以及漫展现场人流环境构建的高质量摄影参考、姿势看板与采集验证工具集。

---

## 📸 项目概览

本项目目前针对**《王者荣耀·王昭君·长夜焕生》**及同系国风二次元神女/法师角色进行深度姿势挖掘与参考建库。针对漫展现场拍摄的特殊限制（如人头背景嘈杂、Coser体力消耗、法杖道具摆放、发丝斗篷甩动等），提供经过人工审核与高分辨率校验的实战参考体系。

### 🌟 核心资产与交互看板

所有看板均为独立离线 HTML，支持浏览器双击直开、全屏高清 Lightbox 放大镜、单键筛选与 JSON 结果导出：

1. **小红书原生接管审核看板**：[`references/changye-huansheng/dist/review_xhs_batch.html`](references/changye-huansheng/dist/review_xhs_batch.html)
   * 包含 **75 张** 100% 小红书真实 Coser 漫展与正片出片参考（王者女角色、法杖交互、漫展防杂人出片）。
2. **动漫与王者荣耀专精审核看板**：[`references/changye-huansheng/dist/review_cosplay_batch.html`](references/changye-huansheng/dist/review_cosplay_batch.html)
   * 包含 **102 张** 纯正二次元 & 王者荣耀女角色高清单人参考（申鹤、芙宁娜手杖、镜流、Comiket 现场出片）。
3. **精选 47 张高清单人参考看板**：[`references/changye-huansheng/dist/curated_selection_board.html`](references/changye-huansheng/dist/curated_selection_board.html)
   * 用户人工过筛保留的 47 张单人高清实战卡，带详细动作拆解与角色实战价值分析。
4. **超大全景联排图（Master Contact Sheets）**：
   * `dist/cosplay_contact_sheets/cosplay_contact_MASTER_102.jpg`
   * `dist/xhs_contact_sheets/xhs_contact_MASTER_75.jpg`
   * `dist/curated_selection_MASTER_47.jpg`

---

## 🛠️ 工具链与采集架构

- **BrowserSkill (Edge 原生自动化接管)**：
  * `scripts/xhs_live_agent_collector.py`：通过 BrowserSkill 与本机 Edge 双向通信，以用户真实浏览器上下文在小红书站内进行深度 Cosplay 检索，提取原生高清无损大图。
- **无损下载与校验器**：
  * `scripts/download_candidates.py`：针对小红书 `currentSrc` 进行原子并发下载，校验 WebP 容器完整性与自然像素尺寸。
- **Pinterest 垂直爬取器**：
  * `scripts/live_cosplay_search.py`：针对二次元漫展与特定角色进行定向 736x/originals 大图无损抓取。
- **看板与联排图构建器**：
  * `scripts/build_xhs_board.py`
  * `scripts/build_cosplay_board.py`
  * `scripts/organize_selected_candidates.py`

---

## 📂 目录结构

```text
photography-reference-lab/
├── notes/
│   └── collection-workflow.md         # 采集流程规范与诊断手册
├── references/
│   └── changye-huansheng/             # 王昭君·长夜焕生 专案
│       ├── curated_candidates/        # 规范化归档的精选姿势库
│       ├── data/                      # 结构化 YAML/JSON 元数据
│       ├── dist/                      # 交互看板 HTML 与 Contact Sheets 大图
│       ├── scripts/                   # 专案脚本工具集
│       └── staging/                   # 采集暂存区与清单记录
├── scripts/
│   └── download_candidates.py         # 全局下载校验器
├── .gitignore
└── README.md
```

---

## 🚀 快速上手

### 1. 浏览审核看板
无需安装任何复杂环境，直接在文件浏览器中用任何浏览器打开：
* `references/changye-huansheng/dist/review_xhs_batch.html`
* `references/changye-huansheng/dist/review_cosplay_batch.html`

### 2. 运行小红书采集脚本
```bash
# 需确保本地 Edge 与 bsk daemon 已就绪
python references/changye-huansheng/scripts/xhs_live_agent_collector.py
```
