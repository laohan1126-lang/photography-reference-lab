#!/usr/bin/env python3
"""Build and maintain references.yaml as the Single Source of Truth for Changye Huansheng V2."""

import yaml
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OUTPUT_YAML = ROOT / "data" / "references.yaml"

# Full meticulously curated dataset adhering strictly to Rule 5, 6, 7, 18
REFS_DATA = [
    # ==================== 00_OFFICIAL ====================
    {
        "id": "OFFICIAL_001",
        "file": "refs/00_OFFICIAL/OFFICIAL_001_key_visual.webp",
        "category": "00_OFFICIAL",
        "priority": "CORE",
        "source": {
            "url": "https://pvp.qq.com/web201605/herodetail/152.shtml",
            "page_title": "王者荣耀官方英雄与皮肤爆料站 - 王昭君·长夜焕生",
            "author": "王者荣耀官方 / 天美工作室群",
            "platform": "pvp.qq.com / 小红书官方",
            "source_type": "OFFICIAL",
            "verified": True
        },
        "target_relevance": 1.00,
        "aesthetic_value": 0.98,
        "technical_value": 0.95,
        "source_confidence": 1.00,
        "production_cost": "HIGH",
        "reference_roles": ["COLOR_PALETTE", "KEY_VISUAL", "LIGHTING_DIRECTION", "CHARACTER_SILHOUETTE"],
        "observed": [
            "官方2121x1080高清横版美宣海报原画。",
            "画面以深蓝暗调海洋为大底（约70%面积），右上角有强烈斜射暖金日光（约10%面积），人物及水母周身泛出高饱和冷青色生物荧光（约20%面积）。",
            "人物右手持水母竖琴法杖向左上方延展，身周环绕多只大小不一的半透明发光小水母。",
            "水母帽与披肩呈现高半透明透光感，边缘被右上角暖金与身周青蓝两道轮廓光同时切割。"
        ],
        "inferred": [
            "画面构图可能具有相当于35mm焦段在微仰视角下的透视拉伸感。",
            "右上方暖光可能用于烘托'破晓长夜'的叙事主题，与水底冰冷形成极强冷暖冲突。",
            "水母帽材质在原画设定中推测为次表面散射（SSS）半透明硅胶或特级透光欧根纱。"
        ],
        "proposed": [
            "现场作为 Shot 01（Hero Shot 全景）的唯一构图与光比色彩基准。",
            "建议执行时在右上方架设 3200K 暖光束（模拟晨曦穿透），左侧及背景铺设深蓝泛光与冷青边缘光，复刻冷暖双轮廓。"
        ],
        "do_not_copy": [
            "原画中夸张的非人类肢体拉伸比例（如过长的小腿）不可生硬强求真人模特复刻，需通过镜头广角畸变合理转译。",
            "不可将背景调成毫无暖色渗入的死黑死蓝。"
        ],
        "use_for_shots": ["SHOT_01", "SHOT_08", "SHOT_10"],
        "search_keyword": "王昭君 长夜焕生 原画 官方",
        "notes": "全项目视觉基准图，所有色彩与情绪的最高仲裁依据。"
    },
    {
        "id": "OFFICIAL_002",
        "file": "refs/00_OFFICIAL/OFFICIAL_002_character_detail.webp",
        "category": "00_OFFICIAL",
        "priority": "CORE",
        "source": {
            "url": "https://pvp.qq.com/web201605/herodetail/152.shtml",
            "page_title": "王者荣耀官方英雄海报角色特写裁剪",
            "author": "王者荣耀官方 / 天美工作室群",
            "platform": "pvp.qq.com / 小红书官方",
            "source_type": "OFFICIAL",
            "verified": True
        },
        "target_relevance": 1.00,
        "aesthetic_value": 0.96,
        "technical_value": 0.90,
        "source_confidence": 1.00,
        "production_cost": "LOW",
        "reference_roles": ["HAIR_STRUCTURE", "FACIAL_EXPRESSION", "MAKEUP_COLOR", "CHEST_CORE"],
        "observed": [
            "官方原画上半身微距特写（1080x1080）。",
            "面部为通透冷白肤色，眼影为微弱粉紫色系，睫毛修长，瞳孔为深邃蓝紫色并带有高光星点。",
            "发型为浅蓝至浅紫渐变微卷波波头（Bob cut），头顶有一根向上自然翘起并分叉的发光呆毛（象征水母触角与长生选手聪明草）。",
            "胸前佩戴一枚深红色菱形能量晶核（AG超玩会战队应援色彩蛋），周围环绕白色半透明珊瑚状颈饰。"
        ],
        "inferred": [
            "面部神态呈现空灵、恬静、微带悲悯的神圣感，视线并非对准正前方，而是向右下方微垂后轻扬。",
            "胸前红宝石是全身唯一的暖红点缀，推测在视觉上承担打破蓝冷单调的视觉锚点功能。"
        ],
        "proposed": [
            "妆造团队以此图作为假发修剪（波波头内扣弧度+发光触角呆毛）与眼影唇釉选色的硬性基准。",
            "近景肖像拍摄（Shot 04）时，需确保胸前红色吊坠反光清晰可见。"
        ],
        "do_not_copy": [
            "不可将假发做成普通直长发或凌乱披肩发，波波头内卷轮廓是本皮肤专属特征。",
            "不可遗漏胸前的红宝石核心。"
        ],
        "use_for_shots": ["SHOT_02", "SHOT_04", "SHOT_06"],
        "search_keyword": "王昭君 长夜焕生 面部特写 官方",
        "notes": "妆面与发型修剪的一手依据。"
    },
    {
        "id": "OFFICIAL_003",
        "file": "refs/00_OFFICIAL/OFFICIAL_003_model_turnaround_front.webp",
        "category": "00_OFFICIAL",
        "priority": "CORE",
        "source": {
            "url": "https://www.xiaohongshu.com/explore/69723231000000000903aa59",
            "page_title": "王者荣耀王昭君长夜焕生模型三视图 - 正面",
            "author": "王者荣耀官方 (提取: 舟楫不避狂澜)",
            "platform": "游戏内3D模型提取 / 小红书",
            "source_type": "OFFICIAL",
            "verified": True
        },
        "target_relevance": 1.00,
        "aesthetic_value": 0.88,
        "technical_value": 0.98,
        "source_confidence": 0.98,
        "production_cost": "LOW",
        "reference_roles": ["COSTUME_SILHOUETTE", "3D_MODEL", "HEMLINE_GEOMETRY", "PROPORTIONS"],
        "observed": [
            "游戏内正视角A-Pose 3D模型全身立绘（1080x1472）。",
            "上身为贴身银白抹胸与深海蓝斜向拼接，腰腹部有镂空流光材质。",
            "裙摆为多层花瓣状重叠结构：最外层为弧形波浪边缘短裙摆，后方下垂半透明渐变水母拖尾。",
            "左臂为裸露手臂佩戴透明水母腕带，右臂带有半透明长袖手套。"
        ],
        "inferred": [
            "裙摆剪裁模拟水母伞盖在水中收缩舒张的波浪花边，静态站立时依然保持弧形伞状张力。"
        ],
        "proposed": [
            "COS服装版型核验基准：裙摆支撑必须有内衬鱼骨或双层压褶以维持波浪弧度，不可软榻下垂。"
        ],
        "do_not_copy": [
            "游戏内为了性能简化的低多边形直边细节不可直接照搬，实物服装应采用更细腻的高定面料工艺。"
        ],
        "use_for_shots": ["SHOT_01", "SHOT_03", "SHOT_07"],
        "search_keyword": "王昭君 长夜焕生 3D模型 正面",
        "notes": "官方3D资产正面标准站姿，服装版型结构最权威图谱。"
    },
    {
        "id": "OFFICIAL_004",
        "file": "refs/00_OFFICIAL/OFFICIAL_004_model_turnaround_back.webp",
        "category": "00_OFFICIAL",
        "priority": "CORE",
        "source": {
            "url": "https://www.xiaohongshu.com/explore/69723231000000000903aa59",
            "page_title": "王者荣耀王昭君长夜焕生模型三视图 - 背面",
            "author": "王者荣耀官方 (提取: 舟楫不避狂澜)",
            "platform": "游戏内3D模型提取 / 小红书",
            "source_type": "OFFICIAL",
            "verified": True
        },
        "target_relevance": 1.00,
        "aesthetic_value": 0.88,
        "technical_value": 0.98,
        "source_confidence": 0.98,
        "production_cost": "LOW",
        "reference_roles": ["BACK_STRUCTURE", "TRAIN_DRAPING", "SHOULDER_STRAPS"],
        "observed": [
            "游戏内后视角3D模型全身立绘（1080x1472）。",
            "背部为深V形露背设计，两根交叉的透明纤细肩带固定于肩胛骨处。",
            "水母拖尾自腰部正后方垂下，呈双层燕尾分叉状，中央带有青色渐变发光线。",
            "后脑勺发型为极为整齐的弧形内扣，两束较细的发辫自后颈下方延伸。"
        ],
        "inferred": [
            "背部结构高度强调女性背部线条的轻盈通透感，拍摄背面或回眸视角时具有极高美感价值。"
        ],
        "proposed": [
            "指导 Shot 06（美背与回眸视角）的服装背部穿戴检验与肩带隐形固定。"
        ],
        "do_not_copy": [
            "避免背后拉链或绑带穿帮露在露背区域外。"
        ],
        "use_for_shots": ["SHOT_06", "SHOT_08"],
        "search_keyword": "王昭君 长夜焕生 3D模型 背面",
        "notes": "官方3D资产背面标准图，背面运镜与拖尾结构的绝对参照。"
    },
    {
        "id": "OFFICIAL_005",
        "file": "refs/00_OFFICIAL/OFFICIAL_005_weapon_harp_staff_detail.webp",
        "category": "00_OFFICIAL",
        "priority": "CORE",
        "source": {
            "url": "https://www.xiaohongshu.com/explore/69723231000000000903aa59",
            "page_title": "王者荣耀王昭君长夜焕生武器竖琴特写",
            "author": "王者荣耀官方 (提取: 舟楫不避狂澜)",
            "platform": "游戏内3D模型提取 / 小红书",
            "source_type": "OFFICIAL",
            "verified": True
        },
        "target_relevance": 1.00,
        "aesthetic_value": 0.92,
        "technical_value": 0.98,
        "source_confidence": 0.98,
        "production_cost": "MEDIUM",
        "reference_roles": ["WEAPON_PROP", "CRYSTAL_MATERIAL", "HARP_STRUCTURE"],
        "observed": [
            "法杖顶端为半透明水母钟形伞盖与弧形晶体竖琴融合构型（1080x1472）。",
            "琴身为冰晶/树脂质感，内部包裹青蓝色渐变发光核心，琴弦为5根笔直的荧光光丝。",
            "法杖握杆为银蓝金属渐变，下端带有海螺与晶体锥形配重。"
        ],
        "inferred": [
            "武器既是法杖也是乐器，手持方式应允许手指自然搭在琴弦上作拨弦状。"
        ],
        "proposed": [
            "实体道具制作验收：琴弓必须使用高透光环氧树脂或亚克力，并在琴框内槽预埋超细 5V 青色 LED 柔性灯带提供物理内发光。"
        ],
        "do_not_copy": [
            "禁止使用不透光的廉价 EVA 泡沫喷漆制作琴框，否则逆光下无法产生水晶折射。"
        ],
        "use_for_shots": ["SHOT_01", "SHOT_05", "SHOT_09"],
        "search_keyword": "王昭君 长夜焕生 武器 竖琴 细节",
        "notes": "核心道具实体化最高级别蓝图。"
    },
    {
        "id": "OFFICIAL_006",
        "file": "refs/00_OFFICIAL/OFFICIAL_006_headpiece_jellyfish_veil.webp",
        "category": "00_OFFICIAL",
        "priority": "CORE",
        "source": {
            "url": "https://www.xiaohongshu.com/explore/69723231000000000903aa59",
            "page_title": "王者荣耀王昭君长夜焕生水母头冠面纱细节",
            "author": "王者荣耀官方 (提取: 舟楫不避狂澜)",
            "platform": "游戏内3D模型提取 / 小红书",
            "source_type": "OFFICIAL",
            "verified": True
        },
        "target_relevance": 1.00,
        "aesthetic_value": 0.94,
        "technical_value": 0.96,
        "source_confidence": 0.98,
        "production_cost": "MEDIUM",
        "reference_roles": ["HEADPIECE", "VEIL_CONSTRUCTION", "TRANSLUCENT_SHEER"],
        "observed": [
            "水母头冠特写（1080x1472）。",
            "帽顶为扁平椭圆水母伞盖骨架，边缘延伸出向下垂落的压褶半透明纱裙与数根细丝触须飘带。",
            "帽檐内侧微透出额头与发丝，未完全遮盖面容。"
        ],
        "inferred": [
            "头饰具有一定重量，若固定不稳容易在模特抬头或低头时滑落，且易在正面主光下形成重度下眼窝阴影。"
        ],
        "proposed": [
            "拍摄现场必须配置前下方反光板消除帽檐阴影，且帽胚内侧应缝制暗夹紧固在发网骨架上。"
        ],
        "do_not_copy": [
            "切勿使用厚实白布，必须选用透光率在 60% 以上的玻璃欧根纱。"
        ],
        "use_for_shots": ["SHOT_02", "SHOT_04", "SHOT_06"],
        "search_keyword": "王昭君 长夜焕生 水母帽 头饰",
        "notes": "全套造型标志性头饰结构基准。"
    },
    {
        "id": "OFFICIAL_007",
        "file": "refs/00_OFFICIAL/OFFICIAL_007_costume_tail_structure.webp",
        "category": "00_OFFICIAL",
        "priority": "SUPPORT",
        "source": {
            "url": "https://www.xiaohongshu.com/explore/69723231000000000903aa59",
            "page_title": "王者荣耀王昭君长夜焕生裙摆下摆结构",
            "author": "王者荣耀官方 (提取: 舟楫不避狂澜)",
            "platform": "游戏内3D模型提取 / 小红书",
            "source_type": "OFFICIAL",
            "verified": True
        },
        "target_relevance": 0.95,
        "aesthetic_value": 0.86,
        "technical_value": 0.92,
        "source_confidence": 0.98,
        "production_cost": "LOW",
        "reference_roles": ["COSTUME_HEM", "FABRIC_GRADIENT"],
        "observed": [
            "裙身下摆与拖尾局部放大视图（1080x1472）。",
            "从腰部蓝紫渐变至下摆纯白，波浪花边多达三层叠压，边沿有亮银色滚边细线。"
        ],
        "inferred": [
            "多层叠压产生水波层层荡漾的立体感，走动时裙摆会自然摆动。"
        ],
        "proposed": [
            "指导下半身特写与走动抓拍动作设计。"
        ],
        "do_not_copy": ["不可将下摆做成单层平面布料剪裁。"],
        "use_for_shots": ["SHOT_01", "SHOT_08"],
        "search_keyword": "王昭君 长夜焕生 裙摆细节",
        "notes": "裙摆层次裁剪工程依据。"
    },
    {
        "id": "OFFICIAL_008",
        "file": "refs/00_OFFICIAL/OFFICIAL_008_chest_core_coral_accessory.webp",
        "category": "00_OFFICIAL",
        "priority": "SUPPORT",
        "source": {
            "url": "https://www.xiaohongshu.com/explore/69723231000000000903aa59",
            "page_title": "王者荣耀王昭君长夜焕生胸前核心饰品",
            "author": "王者荣耀官方 (提取: 舟楫不避狂澜)",
            "platform": "游戏内3D模型提取 / 小红书",
            "source_type": "OFFICIAL",
            "verified": True
        },
        "target_relevance": 0.98,
        "aesthetic_value": 0.90,
        "technical_value": 0.90,
        "source_confidence": 0.98,
        "production_cost": "LOW",
        "reference_roles": ["ACCESSORY_PROP", "CHEST_CORE"],
        "observed": [
            "胸前红宝石与领口珊瑚饰品正方特写（1080x1080）。",
            "深红多面切割宝石镶嵌在淡金爪托内，下垂一束微细珍珠流苏。"
        ],
        "inferred": [
            "宝石材质为高折射率透明红色树脂，受光时会有清脆的单点高光。"
        ],
        "proposed": ["服化团队必须精准还原红宝石棱角切割面。"],
        "do_not_copy": ["不可使用扁平印刷贴纸替代。"],
        "use_for_shots": ["SHOT_02", "SHOT_04", "SHOT_10"],
        "search_keyword": "王昭君 长夜焕生 胸口宝石 细节",
        "notes": "战队彩蛋与视觉对比色核心物件。"
    },
    {
        "id": "OFFICIAL_009",
        "file": "refs/00_OFFICIAL/OFFICIAL_009_model_turnaround_side.webp",
        "category": "00_OFFICIAL",
        "priority": "CORE",
        "source": {
            "url": "https://www.xiaohongshu.com/explore/69723231000000000903aa59",
            "page_title": "王者荣耀王昭君长夜焕生模型三视图 - 侧面",
            "author": "王者荣耀官方 (提取: 舟楫不避狂澜)",
            "platform": "游戏内3D模型提取 / 小红书",
            "source_type": "OFFICIAL",
            "verified": True
        },
        "target_relevance": 1.00,
        "aesthetic_value": 0.88,
        "technical_value": 0.96,
        "source_confidence": 0.98,
        "production_cost": "LOW",
        "reference_roles": ["SIDE_PROFILE", "SPINE_ALIGNMENT", "POSTURE_CURVE"],
        "observed": [
            "3D模型正侧位全身视图（1080x1472）。",
            "脊柱呈现挺拔中微带含胸的内敛体态，臀部微翘，裙摆呈前短后长倾斜斜切线。",
            "水母帽前沿略高后沿略低，呈 15° 俯冲角。"
        ],
        "inferred": [
            "侧面剪影呈流畅的微 S 形，前短后长的裙摆为腿部留出前伸空间，避免臃肿。"
        ],
        "proposed": ["摄影师指导模特侧身站位与佩戴水母帽的角度校准基准。"],
        "do_not_copy": ["避免帽子向后仰翻导致面容全露失去神性神秘感。"],
        "use_for_shots": ["SHOT_03", "SHOT_05"],
        "search_keyword": "王昭君 长夜焕生 3D模型 侧面",
        "notes": "侧身站姿与帽子佩戴俯仰角唯一官方依据。"
    },
    {
        "id": "OFFICIAL_010",
        "file": "refs/00_OFFICIAL/OFFICIAL_010_hair_bobcut_back_structure.webp",
        "category": "00_OFFICIAL",
        "priority": "SUPPORT",
        "source": {
            "url": "https://www.xiaohongshu.com/explore/69723231000000000903aa59",
            "page_title": "王者荣耀王昭君长夜焕生发型后颈细节",
            "author": "王者荣耀官方 (提取: 舟楫不避狂澜)",
            "platform": "游戏内3D模型提取 / 小红书",
            "source_type": "OFFICIAL",
            "verified": True
        },
        "target_relevance": 0.95,
        "aesthetic_value": 0.86,
        "technical_value": 0.92,
        "source_confidence": 0.98,
        "production_cost": "LOW",
        "reference_roles": ["WIG_STYLING", "HAIR_BACK"],
        "observed": [
            "后脑勺及发丝层级特写（1080x1472）。",
            "内层短发收于颈窝，外层发尾大弧度包裹，发尾微翘形成羽毛般的分簇。"
        ],
        "inferred": ["假发需分层内扣打毛定型才能在走动或微风中保持结构不散。"],
        "proposed": ["假发师修剪发尾分簇与颈部内收层次对照。"],
        "do_not_copy": ["不可修剪成一刀切的死板平头波波头。"],
        "use_for_shots": ["SHOT_06"],
        "search_keyword": "王昭君 长夜焕生 假发结构 后部",
        "notes": "发网后脑贴合度与发尾分簇指导。"
    },
    {
        "id": "OFFICIAL_011",
        "file": "refs/00_OFFICIAL/OFFICIAL_011_harp_crystal_translucency.webp",
        "category": "00_OFFICIAL",
        "priority": "SUPPORT",
        "source": {
            "url": "https://www.xiaohongshu.com/explore/69723231000000000903aa59",
            "page_title": "王者荣耀王昭君长夜焕生竖琴晶体透光特写",
            "author": "王者荣耀官方 (提取: 舟楫不避狂澜)",
            "platform": "游戏内3D模型提取 / 小红书",
            "source_type": "OFFICIAL",
            "verified": True
        },
        "target_relevance": 0.98,
        "aesthetic_value": 0.92,
        "technical_value": 0.92,
        "source_confidence": 0.98,
        "production_cost": "MEDIUM",
        "reference_roles": ["WEAPON_PROP", "CRYSTAL_REFRACTION"],
        "observed": [
            "竖琴弓形梁柱晶体折射放大（1080x1472）。",
            "柱体表面有菱形棱面刻线，边缘呈现亮白高光与青蓝内折射。"
        ],
        "inferred": ["高折射率物理质感在实拍逆光下能够自发产生棱镜光散。"],
        "proposed": ["道具表面建议抛光并涂刷微量透明清漆以增强镜面高光。"],
        "do_not_copy": ["避免哑光磨砂质感导致失真。"],
        "use_for_shots": ["SHOT_05"],
        "search_keyword": "王昭君 长夜焕生 竖琴 晶体质感",
        "notes": "竖琴光学质感与涂装标准。"
    },
    {
        "id": "OFFICIAL_012",
        "file": "refs/00_OFFICIAL/OFFICIAL_012_jellyfish_veil_top_angle.webp",
        "category": "00_OFFICIAL",
        "priority": "SUPPORT",
        "source": {
            "url": "https://www.xiaohongshu.com/explore/69723231000000000903aa59",
            "page_title": "王者荣耀王昭君长夜焕生帽盖顶视几何图",
            "author": "王者荣耀官方 (提取: 舟楫不避狂澜)",
            "platform": "游戏内3D模型提取 / 小红书",
            "source_type": "OFFICIAL",
            "verified": True
        },
        "target_relevance": 0.96,
        "aesthetic_value": 0.88,
        "technical_value": 0.94,
        "source_confidence": 0.98,
        "production_cost": "LOW",
        "reference_roles": ["HEADPIECE_GEOMETRY", "CONCENTRIC_RINGS"],
        "observed": [
            "水母帽俯视鸟瞰角度（1080x1472）。",
            "帽盖顶部呈现同心圆环纹路，八根放射状骨线由中心向外发散，仿造真实钵水母伞状骨架。"
        ],
        "inferred": ["水母帽有清晰的仿生骨架支撑体系，并非随意堆叠的软纱。"],
        "proposed": ["帽胚内部建议采用 1mm 细软钢丝或透明定型骨条做出 8 根肋骨支撑。"],
        "do_not_copy": ["不可做成塌陷无骨的浴帽状。"],
        "use_for_shots": ["SHOT_06"],
        "search_keyword": "王昭君 长夜焕生 水母帽 俯视",
        "notes": "水母帽内部骨架支撑工程图解。"
    },
    {
        "id": "OFFICIAL_013",
        "file": "refs/00_OFFICIAL/OFFICIAL_013_shoes_ankle_shell_ornament.webp",
        "category": "00_OFFICIAL",
        "priority": "OPTIONAL",
        "source": {
            "url": "https://www.xiaohongshu.com/explore/69723231000000000903aa59",
            "page_title": "王者荣耀王昭君长夜焕生足部鞋履细节",
            "author": "王者荣耀官方 (提取: 舟楫不避狂澜)",
            "platform": "游戏内3D模型提取 / 小红书",
            "source_type": "OFFICIAL",
            "verified": True
        },
        "target_relevance": 0.90,
        "aesthetic_value": 0.84,
        "technical_value": 0.88,
        "source_confidence": 0.98,
        "production_cost": "LOW",
        "reference_roles": ["FOOTWEAR", "ANKLE_ACCESSORY"],
        "observed": [
            "足部鞋履特写（1080x1080）。",
            "透明高跟凉鞋设计，踝关节缠绕半透明贝壳螺旋饰品与银色脚链。"
        ],
        "inferred": ["脚背全露配合透明高跟，视觉上拉长小腿线条并突显水生精灵的赤足感。"],
        "proposed": ["全身立姿及仰角拍摄时（Shot 01、07）核验鞋履穿戴。"],
        "do_not_copy": ["严禁穿着普通白色厚底皮鞋或长靴。"],
        "use_for_shots": ["SHOT_01", "SHOT_07"],
        "search_keyword": "王昭君 长夜焕生 鞋子 细节",
        "notes": "脚部配件与腿长拉伸指导。"
    },

    # ==================== 01_COSTUME ====================
    {
        "id": "COSTUME_001",
        "file": "refs/01_COSTUME/COSTUME_001_full_physical_dress.webp",
        "category": "01_COSTUME",
        "priority": "CORE",
        "source": {
            "url": "https://www.xiaohongshu.com/explore/6a4ce71d0000000007022652",
            "page_title": "王昭君长夜焕生实拍样衣全景",
            "author": "久七",
            "platform": "小红书",
            "source_type": "COSPLAY",
            "verified": True
        },
        "target_relevance": 0.92,
        "aesthetic_value": 0.85,
        "technical_value": 0.90,
        "source_confidence": 0.90,
        "production_cost": "MEDIUM",
        "reference_roles": ["PHYSICAL_COSTUME", "FABRIC_DRAPING", "EMBROIDERY_REFLECTIVITY"],
        "observed": [
            "国内制衣工坊实做物理COS样衣上身实拍全景（1080x1620）。",
            "缎面在摄影室内硬光照射下产生高光斑块，下摆双层欧根纱具有真实悬垂与自然微透光。",
            "水母帽配有垂坠珍珠链与半透明渐变飘带。"
        ],
        "inferred": [
            "实物面料的高光反光率较高，若现场主光未经柔化可能在胸前与肩部产生死白过曝。",
            "下摆欧根纱需风机辅助吹动才能展开，静止状态下多自然下垂贴合腿部。"
        ],
        "proposed": [
            "拍摄现场主光必须加装大面积双层柔光箱/柔光伞，压制缎面过硬的镜面高光；侧方配备风机低档微吹保持下摆舒展。"
        ],
        "do_not_copy": [
            "样衣胸口拼接若有明显缝合针脚需后期修平。",
            "不可任由假发刘海塌陷，需加强发根蓬松度。"
        ],
        "use_for_shots": ["SHOT_01", "SHOT_05"],
        "search_keyword": "王昭君 长夜焕生 cos 全身",
        "notes": "现有三方COS服装实物落地的现实参考。"
    },
    {
        "id": "COSTUME_002",
        "file": "refs/01_COSTUME/COSTUME_002_hat_drape_detail.webp",
        "category": "01_COSTUME",
        "priority": "SUPPORT",
        "source": {
            "url": "https://www.xiaohongshu.com/explore/6a4ce71d0000000007022652",
            "page_title": "王昭君长夜焕生水母帽檐垂感细节",
            "author": "久七",
            "platform": "小红书",
            "source_type": "COSPLAY",
            "verified": True
        },
        "target_relevance": 0.90,
        "aesthetic_value": 0.82,
        "technical_value": 0.88,
        "source_confidence": 0.90,
        "production_cost": "LOW",
        "reference_roles": ["HEADPIECE_PHYSICAL", "SHADOW_OCCLUSION"],
        "observed": [
            "半身近景展示实物水母帽佩戴状态（1080x1620）。",
            "帽檐压褶透光纱向前方倾斜，飘带下垂至锁骨下方，刺绣在侧光下呈现立体凹凸纹理。"
        ],
        "inferred": [
            "当光线从斜上方打下时，帽檐下沿会在鼻梁与眼窝投下明显锯齿状阴影。"
        ],
        "proposed": [
            "明确要求前下方 30° 放置补光板或补光灯棒，强制填平帽檐阴影。"
        ],
        "do_not_copy": ["切勿让下垂飘带遮挡模特嘴唇与眼神光。"],
        "use_for_shots": ["SHOT_02", "SHOT_04"],
        "search_keyword": "王昭君 长夜焕生 cos 半身 水母帽",
        "notes": "证明帽檐阴影遮挡问题的关键物理证据。"
    },
    {
        "id": "COSTUME_003",
        "file": "refs/01_COSTUME/COSTUME_003_ivh_hydrozoa_dress.webp",
        "category": "01_COSTUME",
        "priority": "CORE",
        "source": {
            "url": "https://www.irisvanherpen.com/haute-couture/sensory-seas",
            "page_title": "Iris van Herpen Haute Couture SS20 'Sensory Seas' - Hydrozoa",
            "author": "Iris van Herpen",
            "platform": "irisvanherpen.com / 巴黎高定时装周",
            "source_type": "EDITORIAL",
            "verified": True
        },
        "target_relevance": 0.88,
        "aesthetic_value": 0.98,
        "technical_value": 0.96,
        "source_confidence": 0.98,
        "production_cost": "HIGH",
        "reference_roles": ["BIOMIMETIC_COUTURE", "TRANSLUCENT_MESH", "JELLYFISH_FINS"],
        "observed": [
            "顶级高定时装秀场走秀图（1080x1440）。",
            "激光切割透明 PETG 材质与极薄玻璃欧根纱（Glass Organza）层叠拼接，形成如同水母触手和伞缘呼吸脉动的流动轮廓。",
            "材质在秀场顶逆光照射下呈现近乎悬浮的半透明发光体视觉。"
        ],
        "inferred": [
            "高级通透感的来源不是一层简单的死白纱，而是多层微小弧形切片在逆光下的次表面重叠衍射。"
        ],
        "proposed": [
            "服化团队若需升级服装档次，可在水母帽与拖尾边缘叠加手工激光裁切的透明热定型欧根纱波浪片，提升生动海洋仿生感。"
        ],
        "do_not_copy": [
            "严禁照搬其先锋暗黑复杂的解构轮廓，王昭君长夜焕生本尊属于优雅端庄神女定位，应保持整体造型的纯净感。"
        ],
        "use_for_shots": ["SHOT_01", "SHOT_06"],
        "search_keyword": "Iris van Herpen Sensory Seas Hydrozoa",
        "notes": "跨界高定时装水母生物仿生材料的最高标准。"
    },
    {
        "id": "COSTUME_004",
        "file": "refs/01_COSTUME/COSTUME_004_ivh_pleated_translucent_fin.webp",
        "category": "01_COSTUME",
        "priority": "SUPPORT",
        "source": {
            "url": "https://www.irisvanherpen.com/haute-couture/sensory-seas",
            "page_title": "Iris van Herpen Haute Couture SS20 压褶半透明翼状细节",
            "author": "Iris van Herpen",
            "platform": "irisvanherpen.com / 巴黎高定时装周",
            "source_type": "EDITORIAL",
            "verified": True
        },
        "target_relevance": 0.85,
        "aesthetic_value": 0.95,
        "technical_value": 0.94,
        "source_confidence": 0.98,
        "production_cost": "HIGH",
        "reference_roles": ["PLEATED_ORGANZA", "LIGHT_TRANSMISSION"],
        "observed": [
            "压褶高定面料特写（1080x1439）。",
            "极细密的手工风琴褶在微弱侧光下呈现极为细腻的明暗渐变排线，通透而不单薄。"
        ],
        "inferred": ["细密压褶能够捕获逆光形成光晕，极大增强轮廓边缘的光感厚度。"],
        "proposed": ["用于水母帽边缘纱幔的压褶工艺选型参考。"],
        "do_not_copy": ["不可采用粗大塑料褶皱。"],
        "use_for_shots": ["SHOT_04", "SHOT_06"],
        "search_keyword": "Iris van Herpen Sensory Seas pleats",
        "notes": "半透明压褶光影质感极佳示范。"
    },
    {
        "id": "COSTUME_005",
        "file": "refs/01_COSTUME/COSTUME_005_underwater_fabric_waterproofing.webp",
        "category": "01_COSTUME",
        "priority": "SUPPORT",
        "source": {
            "url": "https://www.xiaohongshu.com/explore/6922dec0000000001e00bb1a",
            "page_title": "水下COS教程 - 面料与妆容防水加固指南",
            "author": "在贵阳摄影师七哥 / 桥南",
            "platform": "小红书",
            "source_type": "TUTORIAL",
            "verified": True
        },
        "target_relevance": 0.86,
        "aesthetic_value": 0.80,
        "technical_value": 0.92,
        "source_confidence": 0.90,
        "production_cost": "LOW",
        "reference_roles": ["WATERPROOF_MAKEUP", "FABRIC_PREPARATION"],
        "observed": [
            "水下/仿水下妆造与服装预处理对比（1080x1620）。",
            "轻薄雪纺与薄纱在空气中具有良好飘逸性，金属配件涂刷防护甲油胶，妆容采用'妆前乳+持妆粉底+定妆喷雾+散粉+定妆喷雾'的三明治定妆法。"
        ],
        "inferred": ["若现场伴随水气喷雾或湿发拍摄，常规二次元浓妆会在 15 分钟内花妆晕染。"],
        "proposed": ["妆造师必须严格采用高防水防汗三明治定妆体系，并在假发根部喷涂高强度定型胶。"],
        "do_not_copy": ["不要选用容易吸水变重下沉的厚重棉麻或厚缎。"],
        "use_for_shots": ["SHOT_03", "SHOT_04"],
        "search_keyword": "水下 cos 妆容 防水分层 准备",
        "notes": "湿水与仿水实战妆造防崩塌指南。"
    },

    # ==================== 02_STYLE ====================
    {
        "id": "STYLE_001",
        "file": "refs/02_STYLE/STYLE_001_hanging_jellyfish_portrait.webp",
        "category": "02_STYLE",
        "priority": "CORE",
        "source": {
            "url": "https://www.xiaohongshu.com/explore/6a37bcbf000000002003a270",
            "page_title": "白棚置景透明水母人像创作成片",
            "author": "暮影_MUYING / 白川川",
            "platform": "小红书",
            "source_type": "EDITORIAL",
            "verified": True
        },
        "target_relevance": 0.88,
        "aesthetic_value": 0.92,
        "technical_value": 0.92,
        "source_confidence": 0.92,
        "production_cost": "MEDIUM",
        "reference_roles": ["SET_INSTALLATION", "STUDIO_CREATIVE", "DEPTH_OF_FIELD"],
        "observed": [
            "摄影棚内利用吊顶鱼线悬挂多顶实体手工半透明水母道具（1080x1440）。",
            "顶光照射在水母伞盖上，在人物周围形成错落的前景虚焦与背景浮游层次，产生轻盈流动的高级艺术感。"
        ],
        "inferred": [
            "实物水母道具相比纯后期贴图，能提供完全符合现场主光物理方向的高光反光与漫反射阴影，代入感极大增强。"
        ],
        "proposed": [
            "现场建议在天花板横梁架设 3-5 个用透明欧根纱与气泡球自制的手工水母作为前景遮挡物，拉开景深（Shot 01、06）。"
        ],
        "do_not_copy": ["避免水母悬挂过低直接撞头，鱼线需选用直径 0.2mm 以下的透明钓鱼线。"],
        "use_for_shots": ["SHOT_01", "SHOT_06", "SHOT_09"],
        "search_keyword": "水母 置景 拍摄 人像 艺术",
        "notes": "证明物理置景水母在摄影棚内可行性的核心案例。"
    },
    {
        "id": "STYLE_002",
        "file": "refs/02_STYLE/STYLE_002_dreamy_blue_jellyfish_lake.webp",
        "category": "02_STYLE",
        "priority": "OPTIONAL",
        "source": {
            "url": "https://www.xiaohongshu.com/explore/6a8abc650000000028022929",
            "page_title": "坠入梦境之湖 - 水母主题幽蓝人像",
            "author": "mmelody5📷 / 一口忆酱",
            "platform": "小红书",
            "source_type": "COSPLAY",
            "verified": True
        },
        "target_relevance": 0.75,
        "aesthetic_value": 0.90,
        "technical_value": 0.78,
        "source_confidence": 0.85,
        "production_cost": "LOW",
        "reference_roles": ["COLOR_MOOD", "DREAMY_BLUE", "DEEP_SHADOWS"],
        "observed": [
            "高对比深幽蓝冷色调人像成片（1080x1855）。",
            "整体背景深暗偏黛蓝，人物身披白色半透明纱在冷青色环境中形成强烈的明暗反差。"
        ],
        "inferred": [
            "原片为《胜利女神：妮姬》角色莉贝雷利奥（Liberelio）的同人COS，并非王昭君。",
            "其调色风格与长夜焕生的冷调夜色氛围有一定相似度。"
        ],
        "proposed": ["仅作为深暗蓝冷色调氛围与白色半透明纱明度分离度的参考。"],
        "do_not_copy": [
            "【红线】严禁抄袭其角色本身的护士服/异端者颈饰与黑色机械配件，该角色并非王昭君！",
            "不可将色调做成纯死灰蓝。"
        ],
        "use_for_shots": ["SHOT_07"],
        "search_keyword": "坠入梦境之湖 水母 摄影",
        "notes": "非目标角色！仅参考冷色反差，严防角色元素污染。"
    },
    {
        "id": "STYLE_003",
        "file": "refs/02_STYLE/STYLE_003_simulated_underwater_dry_set.webp",
        "category": "02_STYLE",
        "priority": "CORE",
        "source": {
            "url": "https://www.xiaohongshu.com/explore/69edef1a000000001f000433",
            "page_title": "仿水下拍摄 - 悬停入深海",
            "author": "熊猫小涯",
            "platform": "小红书",
            "source_type": "EDITORIAL",
            "verified": True
        },
        "target_relevance": 0.92,
        "aesthetic_value": 0.94,
        "technical_value": 0.96,
        "source_confidence": 0.94,
        "production_cost": "MEDIUM",
        "reference_roles": ["DRY_UNDERWATER", "WEIGHTLESS_SUSPENSION", "CAUSTICS_SURFACE"],
        "observed": [
            "陆地暗棚仿水下拍摄全身照（1080x1620）。",
            "背景为纯黑色吸光布，顶置水波焦散灯投射在白色蓬松裙摆上，模特呈漂浮悬停姿态，假发干燥完整，无泡水塌陷痕迹。"
        ],
        "inferred": [
            "通过侧向低速风机吹拂轻纱与地面支撑木箱抠除技术，在陆地上实现了超越真水下的纯净漂浮感，彻底规避了真水棚毁假发、花妆、模特憋气面部狰狞的致命缺陷。"
        ],
        "proposed": [
            "作为 Shot 03（失重悬浮）与 Shot 08（动态飞扬）的唯一技术路线范本：坚决采用陆地暗棚仿水下！"
        ],
        "do_not_copy": [
            "原片模特身着 Lolita 裙摆，不可照搬其服装剪裁，需替换为王昭君长夜焕生水母下摆。"
        ],
        "use_for_shots": ["SHOT_03", "SHOT_08"],
        "search_keyword": "仿水下拍摄 悬停入深海",
        "notes": "全案最重要的技术突破点：以陆地仿水下代替真水棚。"
    },
    {
        "id": "STYLE_004",
        "file": "refs/02_STYLE/STYLE_004_ivh_sensory_seas_silhouette.webp",
        "category": "02_STYLE",
        "priority": "SUPPORT",
        "source": {
            "url": "https://www.irisvanherpen.com/haute-couture/sensory-seas",
            "page_title": "Iris van Herpen Sensory Seas 极简高定秀场剪影",
            "author": "Iris van Herpen",
            "platform": "irisvanherpen.com / 巴黎高定时装周",
            "source_type": "EDITORIAL",
            "verified": True
        },
        "target_relevance": 0.85,
        "aesthetic_value": 0.96,
        "technical_value": 0.90,
        "source_confidence": 0.98,
        "production_cost": "HIGH",
        "reference_roles": ["FASHION_EDITORIAL", "CLEAN_BACKGROUND", "NEGATIVE_SPACE"],
        "observed": [
            "纯黑极简背景下走秀全身摄影（1080x1439）。",
            "大面积暗黑负空间包裹中央发光水母轮廓裙，视觉极为高级洗练，无杂乱背景干扰。"
        ],
        "inferred": [
            "高级感来源于对背景信息的极度克制，使观众全部注意力集中于人物发光边缘与材质流动。"
        ],
        "proposed": ["指导摄影师在全景镜头（Shot 07）中保持画面留白率在 50% 以上，拒绝廉价花哨的贴纸背景。"],
        "do_not_copy": ["避免模特表情过于冷酷厌世，王昭君角色应保有一丝悲悯与救赎温情。"],
        "use_for_shots": ["SHOT_07"],
        "search_keyword": "Iris van Herpen Sensory Seas silhouette runway",
        "notes": "高级时装剪影与负空间掌控标杆。"
    },

    # ==================== 03_POSE ====================
    {
        "id": "POSE_001",
        "file": "refs/03_POSE/POSE_001_jellyfish_body_curve.webp",
        "category": "03_POSE",
        "priority": "SUPPORT",
        "source": {
            "url": "https://www.xiaohongshu.com/explore/68c4ec9b000000001b0323c8",
            "page_title": "水母主题拍照姿势全攻略 - 躯干S形曲线",
            "author": "大道寺cheese【图文版】",
            "platform": "小红书",
            "source_type": "TUTORIAL",
            "verified": True
        },
        "target_relevance": 0.82,
        "aesthetic_value": 0.84,
        "technical_value": 0.90,
        "source_confidence": 0.90,
        "production_cost": "LOW",
        "reference_roles": ["BODY_CURVE", "S_SHAPE_POSTURE", "FINGER_TENSION"],
        "observed": [
            "人像站姿分解示范（1080x1620）。",
            "躯干微侧倾 15°，两肩一高一低，手腕微曲下垂，手指呈现错落无骨感，打破僵硬对称站姿。"
        ],
        "inferred": ["水母属于无脊椎无骨骼流体生物，拟人体态应尽量消除硬角折线，多呈现圆弧过渡。"],
        "proposed": ["拍摄现场作为模特站姿引导公式：提胸、收腹、微侧肩、手指轻柔悬垂。"],
        "do_not_copy": ["图中的日常 JK 制服与浴缸场景属于无关元素，严禁抄入。"],
        "use_for_shots": ["SHOT_01", "SHOT_05"],
        "search_keyword": "水母 拍照 姿势 教程",
        "notes": "S形躯干流线与手指松弛感示范。"
    },
    {
        "id": "POSE_002",
        "file": "refs/03_POSE/POSE_002_holding_jellyfish.webp",
        "category": "03_POSE",
        "priority": "SUPPORT",
        "source": {
            "url": "https://www.xiaohongshu.com/explore/68c4ec9b000000001b0323c8",
            "page_title": "水母主题拍照姿势 - 手势轻捧微光",
            "author": "大道寺cheese【图文版】",
            "platform": "小红书",
            "source_type": "TUTORIAL",
            "verified": True
        },
        "target_relevance": 0.85,
        "aesthetic_value": 0.86,
        "technical_value": 0.92,
        "source_confidence": 0.90,
        "production_cost": "LOW",
        "reference_roles": ["HAND_GESTURE", "HOLDING_OBJECT", "GAZE_DIRECTION"],
        "observed": [
            "双手轻微合拢托举手势示范（1080x1620）。",
            "掌心留有空隙，视线柔和注视掌心正上方，下巴微收，眼神带专注倾诉感。"
        ],
        "inferred": ["在没有实体道具时模特容易手势僵硬，若掌心放置真实小发光物能自然形成合抱受光姿态。"],
        "proposed": ["直接对应 Shot 02（双手轻捧记忆水母）的动作动作指引。"],
        "do_not_copy": ["避免手指握得过死破坏空灵悬浮感。"],
        "use_for_shots": ["SHOT_02"],
        "search_keyword": "水母 捧水母 拍照 姿势",
        "notes": "双手托捧动作与视线聚焦示范。"
    },
    {
        "id": "POSE_003",
        "file": "refs/03_POSE/POSE_003_cool_expression_upward.webp",
        "category": "03_POSE",
        "priority": "SUPPORT",
        "source": {
            "url": "https://www.xiaohongshu.com/explore/6a7db3f70000000028000ce9",
            "page_title": "水母拟人清冷感面部仰角特写",
            "author": "诗译📷",
            "platform": "小红书",
            "source_type": "COSPLAY",
            "verified": True
        },
        "target_relevance": 0.78,
        "aesthetic_value": 0.88,
        "technical_value": 0.86,
        "source_confidence": 0.88,
        "production_cost": "LOW",
        "reference_roles": ["FACIAL_ANGLE", "COOL_EXPRESSION", "HEAD_TILT"],
        "observed": [
            "面部微仰视角特写（1080x1620）。",
            "头部微向上仰 10°~15°，下颌线紧致清晰，双目微垂望向斜前方，神情清冷疏离、毫无讨好谄媚感。"
        ],
        "inferred": [
            "模特出镜为《胜利女神：妮姬》莉贝雷利奥COS，非王昭君。",
            "此神态极符合昭君'长夜漫漫、独守深渊'的冷傲神女气质。"
        ],
        "proposed": ["用于 Shot 04（微距肖像特写）的神情与下颌仰角指导。"],
        "do_not_copy": [
            "【红线】严禁将妮姬角色的护士装、十字徽章与白色眼罩类元素带入长夜焕生！",
            "眼神切勿过于呆滞死板。"
        ],
        "use_for_shots": ["SHOT_04"],
        "search_keyword": "水母 清冷感 姿势 拍照公式",
        "notes": "非目标角色！仅借用清冷微仰神态，禁止元素混淆。"
    },
    {
        "id": "POSE_004",
        "file": "refs/03_POSE/POSE_004_weightless_floating_arch.webp",
        "category": "03_POSE",
        "priority": "CORE",
        "source": {
            "url": "https://www.xiaohongshu.com/explore/69edef1a000000001f000433",
            "page_title": "仿水下失重漂浮弓背姿态",
            "author": "熊猫小涯",
            "platform": "小红书",
            "source_type": "EDITORIAL",
            "verified": True
        },
        "target_relevance": 0.95,
        "aesthetic_value": 0.94,
        "technical_value": 0.98,
        "source_confidence": 0.94,
        "production_cost": "MEDIUM",
        "reference_roles": ["WEIGHTLESS_ARCH", "BODY_SUSPENSION", "FALLING_DYNAMICS"],
        "observed": [
            "失重悬浮侧卧屈膝全身姿态（1080x1620）。",
            "双腿一前一后自然屈膝，脚尖全力下绷延展小腿线条，双臂如羽翼在体侧展开，腰部弓起成优美弧线。"
        ],
        "inferred": [
            "这是在陆地暗棚利用隐藏支撑凳横向侧卧拍摄并旋转相机的产物，实现了真实水中自由落体或沉睡浮起的完美动态。"
        ],
        "proposed": [
            "Shot 03（失重悬浮·潮汐沉眠）的硬性动作模版，现场模特按此形态进行支撑躺卧测试。"
        ],
        "do_not_copy": [
            "避免脚尖勾起或双腿死板并拢（会变成平躺直挺挺的僵硬状态）。"
        ],
        "use_for_shots": ["SHOT_03"],
        "search_keyword": "仿水下 悬浮 姿势 侧卧",
        "notes": "深海沉睡悬浮动作的教科书级实操范本。"
    },

    # ==================== 04_LIGHTING ====================
    {
        "id": "LIGHTING_001",
        "file": "refs/04_LIGHTING/LIGHTING_001_ocean_caustic_sample.webp",
        "category": "04_LIGHTING",
        "priority": "CORE",
        "source": {
            "url": "https://www.xiaohongshu.com/explore/671aed0e0000000021002e6b",
            "page_title": "水纹灯人像摄影成片效果",
            "author": "摄影师贾超（灯光版）",
            "platform": "小红书",
            "source_type": "BTS",
            "verified": True
        },
        "target_relevance": 0.92,
        "aesthetic_value": 0.90,
        "technical_value": 0.94,
        "source_confidence": 0.95,
        "production_cost": "MEDIUM",
        "reference_roles": ["WATER_CAUSTICS", "SKIN_PROJECTION", "LIGHT_CONTRAST"],
        "observed": [
            "模特面部及锁骨清晰映射出动态水波纹光束（1080x1621）。",
            "高光焦散线锐利明亮（RGB约220~240），暗部阴影保持深蓝通透，无明显夜店霓虹脏色。"
        ],
        "inferred": [
            "水波焦散由带旋转水波纹镜片的聚光灯打出，灯头距模特距离适中（约 2~3 米），使光纹聚集成网状高反差。"
        ],
        "proposed": [
            "Shot 04（水光抚颊）的实拍布光基准，水纹灯焦点调至模特眼部与锁骨，营造真实深海水波映射感。"
        ],
        "do_not_copy": [
            "切勿让最粗的水纹阴影线直接横切模特鼻梁正中央，需微调灯位避开五官关键中轴线。"
        ],
        "use_for_shots": ["SHOT_03", "SHOT_04"],
        "search_keyword": "水纹灯 人像 摄影 效果",
        "notes": "真实水波纹投影在皮肤上的高水准实操范式。"
    },
    {
        "id": "LIGHTING_002",
        "file": "refs/04_LIGHTING/LIGHTING_002_cyan_amber_portrait_sample.webp",
        "category": "04_LIGHTING",
        "priority": "CORE",
        "source": {
            "url": "https://www.xiaohongshu.com/explore/67a33b56000000001800fff2",
            "page_title": "全彩灯光肖像创作 - 冷青与暖橙双色温对比",
            "author": "南光摄影 / Luciana Abella",
            "platform": "Nanlite 官方发布 / 小红书",
            "source_type": "BTS",
            "verified": True
        },
        "target_relevance": 0.90,
        "aesthetic_value": 0.96,
        "technical_value": 0.95,
        "source_confidence": 0.98,
        "production_cost": "MEDIUM",
        "reference_roles": ["DUAL_COLOR_TEMPERATURE", "CYAN_AMBER_SPLIT", "RIM_LIGHTING"],
        "observed": [
            "专业棚拍时尚肖像（1080x1350）。",
            "面部左侧为主冷青色（Peacock Blue）深邃雕刻，右后侧为高色温差的暖琥珀橙金轮廓逆光，背景极暗，冷暖对冲极其高级。"
        ],
        "inferred": [
            "左右两侧光源色温跨度极大（一侧约 8000K+Cyan，另一侧约 3000K+Amber），通过色彩互补将人物立体感彻底剥离背景。"
        ],
        "proposed": [
            "Shot 01（Hero Shot）与 Shot 10（长夜尽头）的双色温布光标准：深海蓝底+暖金破晓轮廓。"
        ],
        "do_not_copy": [
            "原片为欧美浓颜肖像，本案王昭君为东方古典面孔，冷暖光过渡需更加柔和，切勿打出过于粗暴的阴阳脸。"
        ],
        "use_for_shots": ["SHOT_01", "SHOT_10"],
        "search_keyword": "全彩灯光 人像创作 肖像照 南光",
        "notes": "冷青与暖金双色温对撞的商业摄影标杆。"
    },

    # ==================== 05_SET_PROP ====================
    {
        "id": "PROP_001",
        "file": "refs/05_SET_PROP/PROP_001_luminous_orb_handheld.webp",
        "category": "05_SET_PROP",
        "priority": "CORE",
        "source": {
            "url": "https://www.xiaohongshu.com/explore/67ce4b10000000002903b0eb",
            "page_title": "手持发光晶球道具实拍与环境光溢出",
            "author": "，bzn",
            "platform": "小红书",
            "source_type": "COSPLAY",
            "verified": True
        },
        "target_relevance": 0.90,
        "aesthetic_value": 0.92,
        "technical_value": 0.94,
        "source_confidence": 0.92,
        "production_cost": "LOW",
        "reference_roles": ["PRACTICAL_LIGHT", "LIGHT_SPILL", "ORGANIC_INTERACTION"],
        "observed": [
            "模特掌心握有一枚高亮自发光晶球（1080x1439）。",
            "晶球发出的光线真实照亮了模特手指内侧的半透明血肉质感、下巴底面与胸前衣领，产生无与伦比的物理真实环境光溢出（Light Spill）。"
        ],
        "inferred": [
            "如果空手纯靠后期贴发光水母，手指之间绝不可能出现如此符合物理光学的接触阴影与透光反差。"
        ],
        "proposed": [
            "拍摄 Shot 02（掌心水母）时，强烈建议模特手中握持一枚小型内置青白 LED 发光球（道具成本极低），实拍下物理光晕后再由后期覆盖合成水母触须。"
        ],
        "do_not_copy": ["切勿让发光球的电线或电池仓外露穿帮。"],
        "use_for_shots": ["SHOT_02"],
        "search_keyword": "海洋 水母装 水晶球道具 实拍",
        "notes": "实拍自发光道具解决后期贴图塑料感的最强方案。"
    },
    {
        "id": "PROP_002",
        "file": "refs/05_SET_PROP/PROP_002_jellyfish_prop_rigging.webp",
        "category": "05_SET_PROP",
        "priority": "CORE",
        "source": {
            "url": "https://www.xiaohongshu.com/explore/6a37bcbf000000002003a270",
            "page_title": "摄影棚手搓悬吊透明水母装置花絮",
            "author": "暮影_MUYING / 白川川",
            "platform": "小红书",
            "source_type": "BTS",
            "verified": True
        },
        "target_relevance": 0.92,
        "aesthetic_value": 0.85,
        "technical_value": 0.98,
        "source_confidence": 0.95,
        "production_cost": "MEDIUM",
        "reference_roles": ["PROP_MAKING", "RIGGING_BTS", "ORGANZA_BALL"],
        "observed": [
            "影棚置景制作幕后花絮（1440x1080）。",
            "水母伞盖主体由透明亚克力空心半球配合压褶欧根纱包裹而成，下方悬挂细透明蕾丝、亚克力珠链与反光光纤丝带，通过魔术腿和鱼线悬吊在顶棚 C-Stand 上。"
        ],
        "inferred": [
            "单只手工水母材料成本低廉（约 30-50 元），但在影棚逆光照射下呈现极其高级的半透明光感。"
        ],
        "proposed": [
            "美术置景团队据此制作 3-5 顶直径 30~50cm 的悬吊水母道具，吊挂于人物上方与前景不同深度。"
        ],
        "do_not_copy": ["避免使用过于厚重的胶水产生发黄发黑胶痕。"],
        "use_for_shots": ["SHOT_01", "SHOT_06", "SHOT_09"],
        "search_keyword": "水母 置景 手搓 制作花絮",
        "notes": "物理水母道具制作与悬吊工程指南。"
    },

    # ==================== 06_POST ====================
    {
        "id": "POST_001",
        "file": "refs/06_POST/POST_001_caustic_skin_retouch_cleanup.webp",
        "category": "06_POST",
        "priority": "CORE",
        "source": {
            "url": "https://www.xiaohongshu.com/explore/67ce4b10000000002903b0eb",
            "page_title": "水光星芒与冷色调皮肤质感精修范式",
            "author": "，bzn",
            "platform": "小红书",
            "source_type": "BTS",
            "verified": True
        },
        "target_relevance": 0.90,
        "aesthetic_value": 0.94,
        "technical_value": 0.94,
        "source_confidence": 0.92,
        "production_cost": "LOW",
        "reference_roles": ["FREQUENCY_SEPARATION", "SKIN_CLEANUP", "EYE_CATCHLIGHT"],
        "observed": [
            "精修特写人像（1080x1439）。",
            "面部皮肤白皙通透，水纹投影在阴影处过渡极其柔和，无发青发脏杂斑，眼球带有晶莹明亮的高光点（Catchlight）。"
        ],
        "inferred": [
            "后期修图师使用了高低频磨皮（Frequency Separation）：低频层压暗/抹平了水纹投影在阴影区造成的黄绿杂色与色阶断层，高频层完整保留了皮肤纹理与锐利水波线条。"
        ],
        "proposed": [
            "制定后期修图规范：严禁使用整体一键平滑磨皮（会将水波纹洗掉），必须采用高低频分离精修皮肤，并在眼眸叠加微弱青光。"
        ],
        "do_not_copy": ["切勿过度磨皮导致皮肤失去真实毛孔质感变成塑料充气娃娃。"],
        "use_for_shots": ["SHOT_02", "SHOT_04"],
        "search_keyword": "海洋星光梦境 修图 精修 教程",
        "notes": "解决实拍水波纹容易让面部变脏的最重要后期技术准则。"
    },

    # ==================== 07_BTS_TECHNICAL ====================
    {
        "id": "BTS_001",
        "file": "refs/07_BTS_TECHNICAL/BTS_001_caustic_lighting_diagram.webp",
        "category": "07_BTS_TECHNICAL",
        "priority": "CORE",
        "source": {
            "url": "https://www.xiaohongshu.com/explore/671aed0e0000000021002e6b",
            "page_title": "实战水波纹布光四灯阵列图解",
            "author": "摄影师贾超（灯光版）",
            "platform": "小红书",
            "source_type": "BTS",
            "verified": True
        },
        "target_relevance": 0.94,
        "aesthetic_value": 0.85,
        "technical_value": 0.98,
        "source_confidence": 0.95,
        "production_cost": "LOW",
        "reference_roles": ["LIGHTING_DIAGRAM", "LAMP_POSITIONS", "SETUP_GUIDE"],
        "observed": [
            "真实影棚现场灯位图解手绘图（1080x1621）。",
            "标注：主光为常亮水纹灯置于模特斜上方高位；背景打大面积深蓝 LED 染色；侧后方 135° 架设闪光灯加色纸做轮廓切光；正面有白色反光板补阴影。"
        ],
        "inferred": [
            "水波焦散必须由常亮灯产生，因常亮灯旋转水波镜片具有连续运动特性，快门速度在 1/125s~1/160s 可精准凝固水纹切线。"
        ],
        "proposed": [
            "灯光组进场布光 1:1 复刻此四灯阵列作为基础光底。"
        ],
        "do_not_copy": ["避免背景灯功率过大冲淡前景焦散反差。"],
        "use_for_shots": ["SHOT_01", "SHOT_03", "SHOT_04", "SHOT_07"],
        "search_keyword": "水纹灯 布光 图解 教程",
        "notes": "全案灯光组现场落地的实操布光宝典。"
    },
    {
        "id": "BTS_002",
        "file": "refs/07_BTS_TECHNICAL/BTS_002_nanlite_color_diagram.webp",
        "category": "07_BTS_TECHNICAL",
        "priority": "CORE",
        "source": {
            "url": "https://www.xiaohongshu.com/explore/67a33b56000000001800fff2",
            "page_title": "Nanlite 全彩影视多灯系统 3D 渲染灯位图",
            "author": "南光摄影 / Luciana Abella",
            "platform": "Nanlite 官方发布 / 小红书",
            "source_type": "BTS",
            "verified": True
        },
        "target_relevance": 0.90,
        "aesthetic_value": 0.88,
        "technical_value": 0.98,
        "source_confidence": 0.98,
        "production_cost": "MEDIUM",
        "reference_roles": ["COMMERCIAL_LIGHTING", "EQUIPMENT_SETUP", "3D_DIAGRAM"],
        "observed": [
            "官方工业级灯位图（1080x1350）。",
            "清晰标明灯具型号：主光 Alien 300C、侧轮廓 Forza 500B II + 19° 聚光成像筒投光、侧夹光 PavoSlim 120C × 2。"
        ],
        "inferred": [
            "成像筒的加入能够精准控制逆光光束只打在发丝和肩胛，完全不漏光到正面镜头造成眩光。"
        ],
        "proposed": [
            "高规格拍摄方案：右上方破晓暖光建议使用带保荣口聚焦筒（Snoot/Spotlight）的 COB 灯具，确保光束锐利如利剑切入水底。"
        ],
        "do_not_copy": ["无需照搬一模一样的昂贵品牌型号，同类型 COB 与平板灯均可替代。"],
        "use_for_shots": ["SHOT_01", "SHOT_10"],
        "search_keyword": "南光 全彩 人像创作 灯位图",
        "notes": "专业商业人像双色温控光设备配比方案。"
    },
    {
        "id": "BTS_003",
        "file": "refs/07_BTS_TECHNICAL/BTS_003_underwater_cosplay_prep_guide.webp",
        "category": "07_BTS_TECHNICAL",
        "priority": "SUPPORT",
        "source": {
            "url": "https://www.xiaohongshu.com/explore/6922dec0000000001e00bb1a",
            "page_title": "水下 COS 准备清单与保暖固定实操指南",
            "author": "在贵阳摄影师七哥 / 桥南",
            "platform": "小红书",
            "source_type": "TUTORIAL",
            "verified": True
        },
        "target_relevance": 0.88,
        "aesthetic_value": 0.82,
        "technical_value": 0.94,
        "source_confidence": 0.90,
        "production_cost": "LOW",
        "reference_roles": ["CHECKLIST", "ON_SET_SAFETY", "ACCESSORY_FIXING"],
        "observed": [
            "实战物料清单文字图（1080x1620）。",
            "列明发胶、别针、一字夹、防水暗扣、大浴巾保暖设备与隐形安全防护建议。"
        ],
        "inferred": ["水系拍摄模特极易发生失温、饰品滑脱和配件翻卷，准备工作直接决定现场拍摄效率。"],
        "proposed": ["直接转译为现场执行清单（On-Set Checklist）的防护物资核验标准。"],
        "do_not_copy": ["无。"],
        "use_for_shots": ["SHOT_01", "SHOT_03", "SHOT_08"],
        "search_keyword": "水下 cos 教程 准备 清单",
        "notes": "现场保障与防护核验清单的一手来源。"
    },

    # ==================== 90_REJECTED ====================
    {
        "id": "REJECT_001",
        "file": "refs/90_REJECTED/REJECT_001_post_tutorial_cover_text_clutter.webp",
        "category": "90_REJECTED",
        "priority": "REJECT",
        "source": {
            "url": "https://www.xiaohongshu.com/explore/685917ec000000001d00e14a",
            "page_title": "绝美发光水母剪映教程封面",
            "author": "爱学习顶呱呱",
            "platform": "小红书",
            "source_type": "TUTORIAL",
            "verified": False
        },
        "target_relevance": 0.30,
        "aesthetic_value": 0.20,
        "technical_value": 0.15,
        "source_confidence": 0.30,
        "production_cost": "LOW",
        "reference_roles": [],
        "observed": [
            "小红书社交媒体营销教程封面（1080x1439）。",
            "画面被巨大黄色和红色卡通大字严重遮挡（'第三步 剪映合成大片'、'宝子们快冲！'），仅有几行简短手机软件操作文案。"
        ],
        "inferred": ["属于低质社交媒体引流营销图，无任何专业分层通道或可复现的摄影/后期合成技术信息。"],
        "proposed": ["坚决移入废弃库（refs/90_REJECTED/），禁止进入正式摄影参考板。"],
        "do_not_copy": ["禁止将营销封面当作后期技术参考。"],
        "use_for_shots": [],
        "search_keyword": "水母 特效 教程",
        "notes": "【审计废弃】违反规则12F（禁止收教程封面）与规则2（错图标注、大字污染、信息贫乏）。"
    },
    {
        "id": "REJECT_002",
        "file": "refs/90_REJECTED/REJECT_002_ai_tutorial_promo_card.webp",
        "category": "90_REJECTED",
        "priority": "REJECT",
        "source": {
            "url": "https://www.xiaohongshu.com/explore/685917ec000000001d00e14a",
            "page_title": "用AI解锁绝美发光水母全流程拆解卡",
            "author": "爱学习顶呱呱",
            "platform": "小红书",
            "source_type": "TUTORIAL",
            "verified": False
        },
        "target_relevance": 0.35,
        "aesthetic_value": 0.25,
        "technical_value": 0.20,
        "source_confidence": 0.30,
        "production_cost": "LOW",
        "reference_roles": [],
        "observed": [
            "AI生图营销宣传图（1080x1440）。",
            "顶部占满大号渐变艺术字（'用AI解锁绝美发光水母 全流程拆解'），底部为 AI 生成的发光水母插画。"
        ],
        "inferred": ["AI概念图无法证明物理结构可靠性，且营销排版破坏了视觉参考的纯净度。"],
        "proposed": ["移入废弃库保留审计记录。"],
        "do_not_copy": ["禁止采纳其卡通化AI发光色调。"],
        "use_for_shots": [],
        "search_keyword": "发光水母 AI 教程",
        "notes": "【审计废弃】违反规则12F与规则2（AI营销排版、信息密度过低）。"
    }
]

def save_yaml():
    OUTPUT_YAML.parent.mkdir(parents=True, exist_ok=True)
    with open(OUTPUT_YAML, "w", encoding="utf-8") as f:
        yaml.dump(REFS_DATA, f, allow_unicode=True, sort_keys=False, indent=2)
    print(f"Successfully generated {OUTPUT_YAML} with {len(REFS_DATA)} references.")

if __name__ == "__main__":
    save_yaml()
