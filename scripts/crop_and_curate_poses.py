from PIL import Image
from pathlib import Path
import yaml

ROOT = Path("references/changye-huansheng")
YAML_FILE = ROOT / "data" / "references.yaml"

# Load source sheets
eyra_12_path = Path("staging/downloads/eyra_poses/eyra_pose_12.webp")
eyra_07_path = Path("staging/downloads/eyra_poses/eyra_pose_07.webp")
expo_light_01_path = Path("staging/downloads/expo_light_diagram_01.webp")
expo_light_p3_path = Path("staging/downloads/expo_light_p3.webp")

im_12 = Image.open(eyra_12_path)
im_07 = Image.open(eyra_07_path)
W12, H12 = im_12.size
W7, H7 = im_07.size

# Eyra 12 is a 3x3 grid
col_w12 = W12 // 3
row_h12 = H12 // 3

# Eyra 07 is a 3x3 grid
col_w7 = W7 // 3
row_h7 = H7 // 3

# Define crops: (box, target_rel_path, ref_data)
new_items = []

# 1. 01_STANDING: Bottom-left of eyra_12
crop_01 = im_12.crop((0, row_h12 * 2, col_w12, H12))
p_01 = ROOT / "refs/03_POSE/01_STANDING/POSE_0101_standing_cross_feet_45deg.webp"
p_01.parent.mkdir(parents=True, exist_ok=True)
crop_01.save(p_01, "WEBP", quality=92)
print("Saved POSE_0101")

new_items.append({
    "id": "POSE_0101",
    "file": "refs/03_POSE/01_STANDING/POSE_0101_standing_cross_feet_45deg.webp",
    "category": "03_POSE",
    "priority": "CORE",
    "source": {
        "url": "https://www.xiaohongshu.com/explore/69f1e5a000000000350390c1",
        "page_title": "适合新手的简单好用场照姿势合集 - 无道具站姿",
        "author": "鬼城Eyra",
        "platform": "小红书",
        "source_type": "EXPO_FIELD_PHOTO",
        "verified": True
    },
    "target_relevance": 0.95,
    "aesthetic_value": 0.90,
    "technical_value": 0.96,
    "source_confidence": 0.95,
    "production_cost": "LOW",
    "expo_feasibility": "A",
    "reference_roles": ["STANDING_POSE", "DIRECTING_SCRIPT", "EXPO_FIELD_BENCHMARK"],
    "director_script": "身体往右侧转30度，重心放后腿，前腿稍微往前迈半步脚尖点地！双手自然在腰间展开，挺胸收腹，脸转回来找我的镜头，下巴稍微收一点点，眼神带一点高冷神圣！好，保持住，咔嚓！",
    "model_setup": "standing",
    "camera_position": "front-left 15°, chest height",
    "recommended_lens": "50mm f/1.8",
    "crop": "full body / 3/4",
    "micro_adjustments": [
        "双脚不要平行死板并拢，前后脚错开20cm拉长纵向线条",
        "双手不要握拳，指尖呈放松微曲态",
        "腰部主动向上提拔，切忌垮腰驼背"
    ],
    "common_failures": [
        "身体完全正面面对镜头显得呆板如证件照",
        "重心前倾导致小腹凸起"
    ],
    "observed": [
        "漫展展馆现场实景全身站姿，模特身体向右侧微侧30度，前后脚错位交叉站立。",
        "双手在身侧自然展开，身姿挺拔，眼神平视镜头，背景为漫展室内过道。"
    ],
    "inferred": [
        "侧身30度站位配合前后脚错位，能在不用任何道具的情况下，利用镜头对角线最快速地拉长女性身材比例。"
    ],
    "proposed": [
        "作为 Shot 01（标准安全全身照）和 Chain 01 的首发基础站姿。"
    ],
    "do_not_copy": [
        "不要弯腰驼背",
        "不要双腿僵直并拢"
    ],
    "use_for_shots": ["SHOT_01", "SHOT_02"]
})

# 2. 02_STOOL_SEATED: Middle-right of eyra_07 (seated holding staff, hand to chin)
crop_02 = im_07.crop((col_w7 * 2, row_h7, W7, row_h7 * 2))
p_02 = ROOT / "refs/03_POSE/02_STOOL_SEATED/POSE_0201_stool_staff_chin_gesture.webp"
p_02.parent.mkdir(parents=True, exist_ok=True)
crop_02.save(p_02, "WEBP", quality=92)
print("Saved POSE_0201")

new_items.append({
    "id": "POSE_0201",
    "file": "refs/03_POSE/02_STOOL_SEATED/POSE_0201_stool_staff_chin_gesture.webp",
    "category": "03_POSE",
    "priority": "CORE",
    "source": {
        "url": "https://www.xiaohongshu.com/explore/69f1e5a000000000350390c1",
        "page_title": "适合新手的简单好用场照姿势合集 - 小马扎/梯凳坐姿",
        "author": "鬼城Eyra",
        "platform": "小红书",
        "source_type": "EXPO_FIELD_PHOTO",
        "verified": True
    },
    "target_relevance": 0.96,
    "aesthetic_value": 0.92,
    "technical_value": 0.98,
    "source_confidence": 0.95,
    "production_cost": "LOW",
    "expo_feasibility": "B",
    "reference_roles": ["STOOL_SEATED_POSE", "DIRECTING_SCRIPT", "STAFF_INTERACTION"],
    "director_script": "坐马扎前边三分之一，左手握住竖琴法杖立在身边，右手食指轻轻抬起来碰在嘴唇和下巴边上！右腿往前伸直点地，身子坐直，眼神看向斜上方，表情温柔一点，好，保持，啪！",
    "model_setup": "stool",
    "camera_position": "front-right 30°, eye level",
    "recommended_lens": "50mm f/1.8 或 24-240 @ 50–70mm",
    "crop": "full body / 3/4",
    "micro_adjustments": [
        "手指接触下唇要极轻微，绝不可用力挤压嘴唇导致唇妆变形",
        "靠近镜头的腿必须向前斜伸，脚背下绷拉长腿部线条",
        "法杖保持笔直立地，充当侧向几何稳定参考线"
    ],
    "common_failures": [
        "坐姿完全瘫软导致腹部挤压出衣服折痕",
        "双腿垂直90度坐立显得腿粗短"
    ],
    "observed": [
        "漫展展馆现场实景坐姿，模特侧坐于折叠凳前沿，手持长柄法杖立在身侧，另一只手轻触唇颊，前腿斜伸拉长。",
        "背景为漫展玻璃幕墙与大理石地面。"
    ],
    "inferred": [
        "结合小马扎与长柄法杖的坐姿，不仅能瞬间解决 Coser 穿高跟鞋站立疲惫的问题，更具有古代神女深海安歇的沉静气场。"
    ],
    "proposed": [
        "作为 Shot 09（小马扎端坐）与 Chain 02 的核心参考。"
    ],
    "do_not_copy": [
        "不要全身瘫坐在椅子上",
        "不可用力按压面部"
    ],
    "use_for_shots": ["SHOT_09", "SHOT_10"]
})

# 3. 04_CLOSEUP: Top-left of eyra_12 (Closeup, pulling collar/glove, sharp eyes)
crop_04 = im_12.crop((0, 0, col_w12, row_h12))
p_04 = ROOT / "refs/03_POSE/04_CLOSEUP/POSE_0401_face_glove_closeup_glance.webp"
p_04.parent.mkdir(parents=True, exist_ok=True)
crop_04.save(p_04, "WEBP", quality=92)
print("Saved POSE_0401")

new_items.append({
    "id": "POSE_0401",
    "file": "refs/03_POSE/04_CLOSEUP/POSE_0401_face_glove_closeup_glance.webp",
    "category": "03_POSE",
    "priority": "CORE",
    "source": {
        "url": "https://www.xiaohongshu.com/explore/69f1e5a000000000350390c1",
        "page_title": "适合新手的简单好用场照姿势合集 - 面部特写与手势",
        "author": "鬼城Eyra",
        "platform": "小红书",
        "source_type": "EXPO_FIELD_PHOTO",
        "verified": True
    },
    "target_relevance": 0.94,
    "aesthetic_value": 0.93,
    "technical_value": 0.96,
    "source_confidence": 0.95,
    "production_cost": "LOW",
    "expo_feasibility": "A",
    "reference_roles": ["FACE_CLOSEUP", "EXPRESSION_DIRECTING", "EYE_CONTACT"],
    "director_script": "脸稍微朝左偏15度，双手抬起来轻轻捏住耳边的头纱边缘。眼神直视穿进我的镜头里！嘴唇微张带一点呼吸感，别笑，保持高冷清澈的眼神，一秒钟别眨眼，啪！",
    "model_setup": "standing",
    "camera_position": "front, eye level, close range 1m",
    "recommended_lens": "50mm f/1.8 (收至 f/2.5~f/2.8)",
    "crop": "closeup / bust",
    "micro_adjustments": [
        "眼睛聚焦在镜头中心螺纹处，瞳孔产生微小高光点",
        "下巴微敛，露出优美下颌线",
        "头顶触角呆毛与两鬓波波头内扣弧度完整入画"
    ],
    "common_failures": [
        "特写时模特下意识挤眉弄眼或表情不自然僵硬",
        "光圈开得过大（如 f/1.4）导致睫毛清楚但鼻尖模糊"
    ],
    "observed": [
        "胸像大特写，眼神清澈而带有威严感，直击镜头，双手抬至颈侧做轻微捏拉手势，虚化背景杂乱。"
    ],
    "inferred": [
        "大特写是漫展人潮最密集时最保险的救命镜头，无需大空间，50mm 在 1 米距离内即可彻底隔绝周围路人。"
    ],
    "proposed": [
        "作为 Shot 04（面部神性特写）的动作标准。"
    ],
    "do_not_copy": [
        "不可过分挤压面部",
        "严禁眼神漂移无焦"
    ],
    "use_for_shots": ["SHOT_04"]
})

# 4. 06_PROP_WEAPON: Center of eyra_07 (half-body holding vertical staff, head tilted)
crop_06 = im_07.crop((col_w7, row_h7, col_w7 * 2, row_h7 * 2))
p_06 = ROOT / "refs/03_POSE/06_PROP_WEAPON/POSE_0601_staff_vertical_standing_grip.webp"
p_06.parent.mkdir(parents=True, exist_ok=True)
crop_06.save(p_06, "WEBP", quality=92)
print("Saved POSE_0601")

new_items.append({
    "id": "POSE_0601",
    "file": "refs/03_POSE/06_PROP_WEAPON/POSE_0601_staff_vertical_standing_grip.webp",
    "category": "03_POSE",
    "priority": "CORE",
    "source": {
        "url": "https://www.xiaohongshu.com/explore/69f1e5a000000000350390c1",
        "page_title": "适合新手的简单好用场照姿势合集 - 长柄道具持握",
        "author": "鬼城Eyra",
        "platform": "小红书",
        "source_type": "EXPO_FIELD_PHOTO",
        "verified": True
    },
    "target_relevance": 0.95,
    "aesthetic_value": 0.91,
    "technical_value": 0.95,
    "source_confidence": 0.95,
    "production_cost": "LOW",
    "expo_feasibility": "B",
    "reference_roles": ["WEAPON_PROP_POSE", "DIRECTING_SCRIPT", "HALF_BODY"],
    "director_script": "法杖竖直立在胸前偏右位置，右手虎口握住杆身中段。身体稍微往前微倾，脸向左边偏10度，左手抬起到头顶上方作施法兰花指！看我镜头，下巴稍微扬一点，啪！",
    "model_setup": "prop",
    "camera_position": "front-left 20°, eye level",
    "recommended_lens": "50mm f/1.8",
    "crop": "half body / 3/4",
    "micro_adjustments": [
        "单手持杖时手肘贴近躯干，避免长时间平举手腕发酸颤抖",
        "法杖顶部晶体琴弓朝向正面，展现半透明琴身细节"
    ],
    "common_failures": [
        "法杖歪斜挡住面部",
        "握持过于吃力导致手背青筋暴起"
    ],
    "observed": [
        "中景半身，双手协同持握长柄武器，一手握杆一手于头顶舒展，头部微倾，体态极具动感与张力。"
    ],
    "inferred": [
        "法杖立在身前不仅确立了角色战斗法师的身份，更能作为天然的前景纵深引导线。"
    ],
    "proposed": [
        "作为 Shot 10（法杖竖琴威严共鸣）与 Chain 05 的执行参考。"
    ],
    "do_not_copy": [
        "不要让法杖横切面部"
    ],
    "use_for_shots": ["SHOT_05", "SHOT_10"]
})

# 5. 04_LIGHTING: Single speedlight expo field shot (green dress lady in expo hall)
p_light = ROOT / "refs/04_LIGHTING/LIGHTING_003_expo_single_light_sculpting.webp"
if expo_light_01_path.exists():
    im_light = Image.open(expo_light_01_path)
    im_light.save(p_light, "WEBP", quality=92)
    print("Saved LIGHTING_003")

    new_items.append({
        "id": "LIGHTING_003",
        "file": "refs/04_LIGHTING/LIGHTING_003_expo_single_light_sculpting.webp",
        "category": "04_LIGHTING",
        "priority": "CORE",
        "source": {
            "url": "https://www.xiaohongshu.com/explore/6a2fd1fb000000000702df85",
            "page_title": "一个万能漫展场照灯位 - 离机单灯漫展实战",
            "author": "秋桑桑桑.📷 / 一点都不容易的易",
            "platform": "小红书",
            "source_type": "EXPO_FIELD_PHOTO",
            "verified": True
        },
        "target_relevance": 0.98,
        "aesthetic_value": 0.95,
        "technical_value": 0.99,
        "source_confidence": 0.98,
        "production_cost": "LOW",
        "expo_feasibility": "A",
        "reference_roles": ["ONE_LIGHT_SETUP", "OFF_CAMERA_FLASH", "EXPO_BACKGROUND_SEPARATION"],
        "director_script": "（灯光设置参考图：单灯前侧45度斜上方1.5米，柔光罩照亮面部与服饰，背景自然暗沉，漫展顶灯化作梦幻光斑）",
        "model_setup": "standing",
        "camera_position": "front-left 30°, slightly low angle",
        "recommended_lens": "50mm f/1.8",
        "crop": "3/4 / half body",
        "micro_adjustments": [
            "单灯距离模特面部严格控制在 1.2~1.5 米以内",
            "环境光先欠曝 0.7~1 档，单灯输出补足面部曝光"
        ],
        "common_failures": [
            "机顶直接直闪导致面部死白油光",
            "灯架距离太远导致光衰严重面部发暗"
        ],
        "observed": [
            "大型漫展场馆暗调背景实景场照，模特身穿华丽长裙、戴宽檐帽手持权杖。",
            "单只离机闪光灯从前侧方高位打入，柔和雕刻面部五官轮廓与裙面褶皱金线。",
            "背景为漫展天花板与虚化圆形光斑，人物立体感极强地从深暗背景中跃出。"
        ],
        "inferred": [
            "实证了单个便携闪光灯（如 Godox V100 + 圆形柔光罩）完全可以在漫展场馆内完成商业级质感人像，无需多灯复杂布光。"
        ],
        "proposed": [
            "作为全项目漫展单灯布光（LIGHT_MODE_01）的最高实操标杆！"
        ],
        "do_not_copy": [
            "不要机顶直闪",
            "不要盲目追求全黑死背景"
        ],
        "use_for_shots": ["SHOT_01", "SHOT_02", "SHOT_03", "SHOT_04"]
    })

# 6. 07_BTS_TECHNICAL: Expo light stands setup in hall
p_bts = ROOT / "refs/07_BTS_TECHNICAL/BTS_004_expo_hall_light_stands_setup.webp"
if expo_light_p3_path.exists():
    im_bts = Image.open(expo_light_p3_path)
    im_bts.save(p_bts, "WEBP", quality=92)
    print("Saved BTS_004")

    new_items.append({
        "id": "BTS_004",
        "file": "refs/07_BTS_TECHNICAL/BTS_004_expo_hall_light_stands_setup.webp",
        "category": "07_BTS_TECHNICAL",
        "priority": "CORE",
        "source": {
            "url": "https://www.xiaohongshu.com/explore/6a2fd1fb000000000702df85",
            "page_title": "一个万能漫展场照灯位 - 漫展场馆实地布光位示意",
            "author": "秋桑桑桑.📷",
            "platform": "小红书",
            "source_type": "EXPO_FIELD_BTS",
            "verified": True
        },
        "target_relevance": 0.95,
        "aesthetic_value": 0.82,
        "technical_value": 0.98,
        "source_confidence": 0.98,
        "production_cost": "LOW",
        "expo_feasibility": "A",
        "reference_roles": ["LIGHT_STAND_PLACEMENT", "EXPO_SPACE_STRATEGY", "SAFETY_STAND"],
        "director_script": "（现场部署指导：摄影师左脚踩住单灯架底座，灯架位于右前侧45度，高度2.1米俯倾照亮Coser）",
        "model_setup": "none",
        "camera_position": "observer view",
        "recommended_lens": "24-240mm",
        "crop": "bts wide",
        "micro_adjustments": [
            "单灯单架部署，紧凑收拢脚管防止路人踩绊",
            "轻量反折灯架便于3秒内提灯快速转移阵地"
        ],
        "common_failures": [
            "灯架腿张开过大占用主通道被保安驱赶",
            "无人扶持被大裙摆刮倒"
        ],
        "observed": [
            "漫展空旷展厅内的实地灯架布置实拍，清晰标注了各灯位与相机的空间几何距离与地面反折结构。"
        ],
        "inferred": [
            "在漫展有限空间内，轻装快速机动是单兵摄影师生存的第一准则。"
        ],
        "proposed": [
            "指导摄影师现场单灯单架的安全立足点与走位。"
        ],
        "do_not_copy": [
            "漫展高峰期切勿在主通道摊开4支大型灯架"
        ],
        "use_for_shots": ["SHOT_01", "SHOT_02", "SHOT_03"]
    })

# Append new items to references.yaml
with open(YAML_FILE, "r", encoding="utf-8") as f:
    current_data = yaml.safe_load(f)

existing_ids = {x["id"] for x in current_data}
added_count = 0
for it in new_items:
    if it["id"] not in existing_ids:
        current_data.append(it)
        added_count += 1
        print(f"Added to yaml: {it['id']}")

with open(YAML_FILE, "w", encoding="utf-8") as f:
    yaml.dump(current_data, f, allow_unicode=True, sort_keys=False, indent=2)

print(f"Curated and added {added_count} new high-value references cleanly!")
