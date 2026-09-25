# 王昭君·长夜焕生 漫展实战摄影视觉参考系统 V2.1 (Expo Field Edition)

> **Visual Reference System V2.1 · 大型漫展现场快速 COS 摄影实战参考系统**  
> **适用场景**：人流密集、空间狭窄、时间有限、无助手的真实漫展出街/出片拍摄  
> **硬件基准**：Sony A7M4 + Godox V100 单灯（单灯架+圆形柔光罩）+ 50mm f/1.8 + 24-240mm + 折叠小马扎

---

## 1. 系统核心理念与重大重构 (V2.1 Expo Pivot)

本项目历经从 **V2.0 影棚概念版** 向 **V2.1 漫展实战版** 的彻底重构。

### 为什么必须重构？
1. **真实物理边界不可逆**：漫展现场没有 2000W 镝灯、没有水纹投影灯、没有吸光黑丝绒幕布、没有鼓风机、不能吊威亚、不能让 Coser 在脏地面趴地或长时间下蹲。
2. **单兵作战极限**：摄影师单兵作业，一只手持机，另一只手或单灯架固定 Godox V100；镜头仅有 50mm f/1.8 定焦与 24-240mm 变焦。
3. **现场沟通效率定生死**：漫展嘈杂混乱，必须有极简、直白、无需 Coser 思考的**口头指令台词（Director Scripts）**，以及连贯微调的**动作流（Pose Chains）**，杜绝冷场与僵硬。

### 核心坚守原则
- 🎯 **出片率绝对优先**：将镜头与姿势严密划分为【MUST GET 必保保底】、【NICE TO HAVE 锦上添花】与【ONLY IF 极限探索】三级。
- 🎯 **口令化现场指导**：每一个姿势均配置摄影师口头直白台词、体态摆位、微调变体与常见翻车点。
- 🎯 **单灯极限物理压榨**：系统总结 Godox V100 在漫展环境中的 4 大实战模式，坚决破除“盲目高速同步（HSS）”的电池与过热陷阱。
- 🎯 **后期真实还原边界**：确立 POST_A（精修去杂）、POST_B（半写实漫展背景替换）、POST_C（全环境深海合成）三级管线，严禁破坏 Coser 真实面部与服饰轮廓。
- 🎯 **100% 离线手机支持**：生成零网络依赖的竖版手机相册卡片（`field_pack/phone_album/`）与单文件离线网页（`field_pack/index_offline.html`）。

---

## 2. 目录架构

```text
references/changye-huansheng/
├── README.md                          # 系统总览与漫展实战操作手册
├── project.yaml                       # 项目元配置与分类定义
│
├── refs/                              # 分类存储的本地高清实战参考图 (62项)
│   ├── 00_OFFICIAL/                   # 官方高清原画、3D模型全景/细节、技能特写 (13项)
│   ├── 01_COSTUME/                    # 水母薄纱、发冠刺绣、裙摆材质实拍 (5项)
│   ├── 02_STYLE/                      # 海洋神性氛围、冷暖高调质感 (4项)
│   ├── 03_POSE/                       # 漫展站立、坐姿、半身、特写动作实战库 (28项)
│   ├── 04_LIGHTING/                   # V100单灯离机、立体阴影、色温实测 (4项)
│   ├── 05_SET_PROP/                   # 晶体竖琴法杖握持与道具细节 (2项)
│   ├── 06_POST/                       # 水下微光、粒子特效与合成后期参考 (2项)
│   ├── 07_BTS_TECHNICAL/              # 漫展真实单灯架位、机位部署花絮 (4项)
│   └── 90_REJECTED/                   # 审计废弃/不符合漫展规范图库 (保留原因)
│
├── data/
│   └── references.yaml                # Single Source of Truth 唯一事实数据库 (62项)
│
├── docs/
│   ├── POSE_CHAINS.md                 # 8套漫展连续动作流与口头指令台词指南
│   ├── SHOT_PLAN.md                   # 12套漫展实战分镜执行方案 (MUST/NICE/ONLY)
│   ├── POST_WORKFLOW.md               # 漫展后期管线标准 (POST_A/B/C 三级制作规范)
│   ├── AI_BACKGROUND_RECIPES.md       # AI 背景生成与光学透视匹配配方手册
│   ├── OFFICIAL_EVIDENCE.md           # 官方一手证据全解与采样
│   ├── VISUAL_DNA.md                  # 基于官方证据提炼的7维视觉基因
│   ├── REFERENCE_GAPS.md              # 漫展实战技术攻坚缺口与替代方案
│   └── REFERENCE_ANALYSIS.md          # 视觉挑战与制作深度剖析
│
├── field_pack/                        # 漫展现场 100% 离线物料包
│   ├── index_offline.html             # 无需外网的单文件离线画板
│   └── phone_album/                   # 竖版手机相册指导卡片 (JPG)
│
├── dist/                              # 自动生成的本地大板与联系图
│   ├── index.html                     # 交互式全功能参考看板 (支持分类过滤)
│   ├── contact_sheet_all.jpg          # 62项全量参考高清排版图
│   └── contact_sheet_core.jpg         # 39项 CORE 核心排版图
│
└── scripts/
    ├── validate_refs.py               # 数据完整性与规范自动验证脚本 (0 error / 0 warning)
    ├── check_sources.py               # 来源链接有效性巡检工具
    ├── build_board.py                 # HTML 交互看板生成器
    ├── build_contact_sheet.py         # 高清联系图排版生成器
    └── build_offline_pack.py          # 离线手机相册卡片与离线板打包工具
```

---

## 3. 漫展实战动作流与口头指令速查

系统在 [`docs/POSE_CHAINS.md`](docs/POSE_CHAINS.md) 中完整定义了 8 组连贯流转动作链。摄影师可在 1–2 分钟内引导 Coser 自然产出 3–5 张不同情绪构图：

| 动作链编号 | 动作链主题 | 包含姿势编号 | 摄影师核心口令（Director Script） | 现场耗时 |
| :---: | :--- | :--- | :--- | :---: |
| **Chain 01** | 经典站姿微调流 | `POSE_0101` → `0102` → `0103` → `0104` | “侧身站，重心放后脚，法杖斜抱胸前，头转看我，眼神带点清冷怜悯” | 90 秒 |
| **Chain 02** | 小马扎优雅坐姿流 | `POSE_0201` → `0202` → `0203` | “马扎坐一半，外侧腿伸直脚尖点地，裙摆往前铺，双手轻叠膝头” | 120 秒 |
| **Chain 03** | 回眸神性流动流 | `POSE_0701` → `0401` | “背对我，肩线压低，慢慢转头找我镜头，下巴收一点，眼神放空” | 90 秒 |
| **Chain 04** | 法杖互动与召唤流 | `POSE_0601` → `0602` | “双手握住琴颈，指尖在琴弦上虚拨，深呼吸抬头看斜上方光亮” | 90 秒 |
| **Chain 05** | 水母薄纱情绪半身流 | `POSE_0301` → `0302` | “单手虚抚脸颊发丝，手指放松别贴死，眼神看我镜头上方” | 60 秒 |
| **Chain 06** | 纯净面部神女特写流 | `POSE_0401` → `0501` | “微侧 15 度，吸一口气嘴唇自然微张，眼神透过我看向远方” | 60 秒 |
| **Chain 07** | 低机位女王气场流 | `POSE_0801` → `0802` | “下巴微抬，眼神自上而下俯视，法杖竖直立地，身姿挺拔” | 90 秒 |
| **Chain 08** | 漫展人流避险救急流 | `POSE_0104` → `0702` | “找个白墙/柱子，靠拢收窄四肢，双手交叠胸前护宝石，看镜头” | 60 秒 |

---

## 4. 漫展 12 套分镜拍摄执行优先级

详见 [`docs/SHOT_PLAN.md`](docs/SHOT_PLAN.md)：

### 必保底镜头 (MUST GET - 6组)
1. **Shot 01: 【经典立绘 · 海渊神女】(Hero Full Body)** - 50mm f/1.8 / 24-240mm (35mm), 站姿30°法杖斜抱，V100 45°高位主光。
2. **Shot 02: 【长夜低语 · 抚心微光】(Chest & Hand Intimacy)** - 50mm f/1.8 (f/2.0), 3/4半身抚胸前水母宝石，大光圈虚化背景。
3. **Shot 03: 【静谧潮汐 · 礁石侧坐】(Seated Elegance)** - 50mm f/1.8, 小马扎斜坐，长腿延伸，避开漫展脏地面。
4. **Shot 04: 【神性回眸 · 霜发流云】(Back Turning Gaze)** - 50mm f/1.8, 露背转身，V100 打透水母帽半透明纱。
5. **Shot 05: 【冰肌冷眸 · 纯净神女】(Face Closeup)** - 50mm f/1.8 (f/2.2), 面部大特写，眼神光雕刻，后期换背景安全核心。
6. **Shot 06: 【长夜独奏 · 潮涌鸣琴】(Harp Interaction)** - 50mm f/1.8, 拨弦特写，双手舒展，法杖发光细节捕捉。

### 锦上添花镜头 (NICE TO HAVE - 4组)
7. **Shot 07: 【海渊破晓 · 逆光生辉】(Backlight Halo)** - V100 置于 Coser 侧后方打发丝轮廓光。
8. **Shot 08: 【拂晓掠影 · 纱幔微扬】(Veil Motion Dynamics)** - 慢门抓拍或助手抖动裙摆瞬间。
9. **Shot 09: 【极寒王权 · 俯视众生】(Low Angle Authority)** - 离地20cm极低机位仰拍，拉长身形。
10. **Shot 10: 【掌心微芒 · 召唤灵体】(Hands Macro Cupping)** - 双手托起虚空小水母，为后期合成预留空间。

### 严苛极限镜头 (ONLY IF CONDITIONS ALLOW - 2组)
11. **Shot 11: 【海渊沉眠 · 拟态失重】(Simulated Underwater Float)** - 需小马扎+暗色背景，后期擦除凳子。
12. **Shot 12: 【万千游弋 · 群母升腾】(Summoning Wide Scene)** - 需场馆大纵深通道与无杂人窗口。

---

## 5. Godox V100 单灯实战指南

1. **拒绝盲目 HSS**：快门锁定在最高同步速度 **1/250s**。强光下通过收缩光圈（f/4~f/5.6）控制环境曝光，V100 保持在 1/8~1/16 功率，保证回电极速且单块电池撑满全场。
2. **单灯角度黄金法则**：灯头比 Coser 头部高 30~50cm，斜向下 45°，距人物 1.2~1.5m，配合便携圆形柔光罩，在鼻侧打出柔和伦勃朗三角光，坚决避免机顶直闪油光。
3. **退避方案（LIGHT_MODE_04）**：若遇安保驱离或空间极端逼仄，立刻收起灯架，挂 50mm f/1.8 光圈全开（f/1.8），利用漫展天井或大灯箱漫射光纯环境光出片。

---

## 6. 后期与 AI 背景扩展管线

- **POST_A (基础出片，100%必做)**：液化、分频磨皮保留冷白肌理、消除展厅插座与杂乱脚标、强化眼神光与胸前发光晶体。
- **POST_B (半写实合成，漫展精修首选)**：将展馆杂乱天花板与背景压暗，局部置换为深蓝粒子光斑与焦散虚化水光，保留 Coser 边缘自然光晕。
- **POST_C (重度场景置换，挑选 2–3 张底片)**：
  - 严格遵守 5 大物理匹配原则（机位高度、透视焦段、主光角度 45°、色温匹配 5600K、景深衰减）。
  - 参考 [`docs/AI_BACKGROUND_RECIPES.md`](docs/AI_BACKGROUND_RECIPES.md) 进行 Midjourney / SD 提示词渲染背景，严禁使用 AI 重绘 Coser 脸部与服饰！

---

## 7. 离线工具与自动化构建

```bash
# 1. 验证整个数据库与文件物理关联 (0 error / 0 warning)
python scripts/validate_refs.py

# 2. 编译交互式本地网页 (dist/index.html)
python scripts/build_board.py

# 3. 渲染高清排版联系图 (dist/contact_sheet_all.jpg)
python scripts/build_contact_sheet.py

# 4. 生成手机离线指导包 (field_pack/phone_album/*.jpg & index_offline.html)
python scripts/build_offline_pack.py
```
