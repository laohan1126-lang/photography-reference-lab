from PIL import Image
from pathlib import Path
import yaml

ROOT = Path("references/changye-huansheng")
YAML_FILE = ROOT / "data" / "references.yaml"

p05 = Path("staging/downloads/eyra_poses/eyra_pose_05.webp")
p04 = Path("staging/downloads/eyra_poses/eyra_pose_04.webp")
p11 = Path("staging/downloads/eyra_poses/eyra_pose_11.webp")
expo_p1 = Path("staging/downloads/expo_light_p1.webp")
expo_p4 = Path("staging/downloads/expo_light_p4.webp")

im05 = Image.open(p05)
im04 = Image.open(p04)
im11 = Image.open(p11)

def get_grid_cell(im, row, col):
    w, h = im.size
    cw = w // 3
    ch = h // 3
    return im.crop((col * cw, row * ch, (col + 1) * cw, (row + 1) * ch))

new_refs = []

def add_crop(cell, rel_path, meta):
    target = ROOT / rel_path
    target.parent.mkdir(parents=True, exist_ok=True)
    cell.save(target, "WEBP", quality=92)
    meta["file"] = rel_path
    new_refs.append(meta)
    print(f"Saved {meta['id']} -> {rel_path}")

# 1. 06_PROP_WEAPON: Top-left of im04 - staff two handed front guard
add_crop(
    get_grid_cell(im04, 0, 0),
    "refs/03_POSE/06_PROP_WEAPON/POSE_0602_staff_two_handed_front_guard.webp",
    {
        "id": "POSE_0602",
        "category": "03_POSE",
        "priority": "CORE",
        "source": {"url": "https://www.xiaohongshu.com/explore/69f1e5a000000000350390c1", "page_title": "适合新手的简单好用场照姿势合集 - 武器持握", "author": "鬼城Eyra", "platform": "小红书", "source_type": "EXPO_FIELD_PHOTO", "verified": True},
        "target_relevance": 0.95, "aesthetic_value": 0.92, "technical_value": 0.96, "source_confidence": 0.95,
        "production_cost": "LOW", "expo_feasibility": "B",
        "reference_roles": ["WEAPON_PROP_POSE", "DIRECTING_SCRIPT", "TWO_HANDED_GUARD"],
        "director_script": "双手抱住竖琴法杖立在胸前，右手在上左手在下，身体微向下沉呈防守警戒态！眼神透过法杖看我的镜头，表情凝重坚定，好，稳住，啪！",
        "model_setup": "prop", "camera_position": "front eye level", "recommended_lens": "50mm f/1.8", "crop": "3/4 / half body",
        "micro_adjustments": ["法杖竖直不偏不倚，双手呈上下错位握持", "双膝微屈，重心降低体现战斗张力"],
        "common_failures": ["双手握太紧导致双肩高耸僵硬", "法杖直接挡住半边脸"],
        "observed": ["双手握持长柄武器立于体前，微屈膝蓄力，眼神专注威严。"],
        "inferred": ["适合表现王昭君在深海面临敌人时凝聚冰晶护盾的施法前摇。"],
        "proposed": ["用于 Shot 10（法杖竖琴威严共鸣）防守变体。"],
        "do_not_copy": ["法杖不可遮挡眼部视线"],
        "use_for_shots": ["SHOT_05", "SHOT_10"]
    }
)

# 2. 01_STANDING: Bottom-right of im04 - standing, staff planted, other arm behind back
add_crop(
    get_grid_cell(im04, 2, 2),
    "refs/03_POSE/01_STANDING/POSE_0104_staff_ground_stance_noble.webp",
    {
        "id": "POSE_0104",
        "category": "03_POSE",
        "priority": "CORE",
        "source": {"url": "https://www.xiaohongshu.com/explore/69f1e5a000000000350390c1", "page_title": "适合新手的简单好用场照姿势合集 - 挺拔立姿", "author": "鬼城Eyra", "platform": "小红书", "source_type": "EXPO_FIELD_PHOTO", "verified": True},
        "target_relevance": 0.96, "aesthetic_value": 0.93, "technical_value": 0.97, "source_confidence": 0.95,
        "production_cost": "LOW", "expo_feasibility": "B",
        "reference_roles": ["STANDING_POSE", "DIRECTING_SCRIPT", "NOBLE_STANCE"],
        "director_script": "右手单手握法杖直直插在右侧地面上，左手背到后腰处！身体挺拔笔直，下巴扬起15度，眼神冷傲看向斜上方，像深海神殿的女王审视大地，好，稳住，啪！",
        "model_setup": "prop", "camera_position": "front-left 20°, slightly low angle", "recommended_lens": "24-240 @ 35–50mm", "crop": "full body",
        "micro_adjustments": ["挺胸拔背拉长脊柱线条", "左手背在身后露出腰侧镂空珊瑚细节"],
        "common_failures": ["身体前倾导致显矮", "法杖离身体过远不协调"],
        "observed": ["全身站姿，单手柱杖立地，另一手背于身后，体态修长高贵。"],
        "inferred": ["极度彰显王昭君 FMVP 尊荣贵气。"],
        "proposed": ["用于 Shot 01 全景霸气立姿。"],
        "do_not_copy": ["切忌驼背塌肩"],
        "use_for_shots": ["SHOT_01"]
    }
)

# 3. 07_TURNING_DYNAMIC: Top-left of im05 - turning back 45deg, weapon over shoulder
add_crop(
    get_grid_cell(im05, 0, 0),
    "refs/03_POSE/07_TURNING_DYNAMIC/POSE_0703_turn_weapon_over_shoulder.webp",
    {
        "id": "POSE_0703",
        "category": "03_POSE",
        "priority": "CORE",
        "source": {"url": "https://www.xiaohongshu.com/explore/69f1e5a000000000350390c1", "page_title": "适合新手的简单好用场照姿势合集 - 回身动势", "author": "鬼城Eyra", "platform": "小红书", "source_type": "EXPO_FIELD_PHOTO", "verified": True},
        "target_relevance": 0.95, "aesthetic_value": 0.92, "technical_value": 0.96, "source_confidence": 0.95,
        "production_cost": "LOW", "expo_feasibility": "B",
        "reference_roles": ["TURNING_DYNAMIC", "DIRECTING_SCRIPT", "OVER_SHOULDER_WEAPON"],
        "director_script": "背对着我向右走一步，猛然回头看我！法杖斜扛在后肩上，身体形成S形扭转！下巴微收，眼神锐利锁定镜头，好，漂亮，啪！",
        "model_setup": "prop", "camera_position": "back-left 30°, eye level", "recommended_lens": "50mm f/1.8", "crop": "3/4 / half body",
        "micro_adjustments": ["法杖斜背在肩头形成视觉斜对角线", "头部回望锁住镜头，露出清晰下颌线"],
        "common_failures": ["法杖滑落砸到后背", "转头过猛假发飞乱"],
        "observed": ["背身回望，法杖斜负肩头，身体扭动线条流畅充满动感。"],
        "inferred": ["兼具动态张力与背部细节展示。"],
        "proposed": ["用于 Shot 05 回眸与 Shot 12 动态组合。"],
        "do_not_copy": ["法杖尖端注意安全避开周围路人"],
        "use_for_shots": ["SHOT_05", "SHOT_12"]
    }
)

# 4. 03_HALF_BODY: Bottom-right of im05 - half body staff horizontal point
add_crop(
    get_grid_cell(im05, 2, 2),
    "refs/03_POSE/03_HALF_BODY/POSE_0303_half_body_staff_horizontal_point.webp",
    {
        "id": "POSE_0303",
        "category": "03_POSE",
        "priority": "CORE",
        "source": {"url": "https://www.xiaohongshu.com/explore/69f1e5a000000000350390c1", "page_title": "适合新手的简单好用场照姿势合集 - 半身特写", "author": "鬼城Eyra", "platform": "小红书", "source_type": "EXPO_FIELD_PHOTO", "verified": True},
        "target_relevance": 0.94, "aesthetic_value": 0.91, "technical_value": 0.95, "source_confidence": 0.95,
        "production_cost": "LOW", "expo_feasibility": "B",
        "reference_roles": ["HALF_BODY", "DIRECTING_SCRIPT", "POINTING_GESTURE"],
        "director_script": "半身站稳，右手握住法杖下垂，左手抬起到胸前食指指向镜头！眼神清冷带一点审讯感，看镜头！好，一秒钟，啪！",
        "model_setup": "prop", "camera_position": "front eye level", "recommended_lens": "50mm f/1.8", "crop": "half body",
        "micro_adjustments": ["手指指向镜头形成强烈近大远小纵深透视", "面部保持半侧受光"],
        "common_failures": ["手指挡住自己的鼻子", "神态发呆"],
        "observed": ["中景半身，单手指向镜头，透视感强烈，主体气场逼人。"],
        "inferred": ["非常适合打破死板站姿，制造与观众的直接交互感。"],
        "proposed": ["用于 Shot 03 半身英雄像。"],
        "do_not_copy": ["不可手指完全对死镜头遮挡五官"],
        "use_for_shots": ["SHOT_03"]
    }
)

# 5. 09_BACK_VIEW: Top-center of im11 - back view umbrella/veil lift
add_crop(
    get_grid_cell(im11, 0, 1),
    "refs/03_POSE/09_BACK_VIEW/POSE_0902_back_view_umbrella_fan_lift.webp",
    {
        "id": "POSE_0902",
        "category": "03_POSE",
        "priority": "CORE",
        "source": {"url": "https://www.xiaohongshu.com/explore/69f1e5a000000000350390c1", "page_title": "适合新手的简单好用场照姿势合集 - 绝美背影", "author": "鬼城Eyra", "platform": "小红书", "source_type": "EXPO_FIELD_PHOTO", "verified": True},
        "target_relevance": 0.96, "aesthetic_value": 0.95, "technical_value": 0.98, "source_confidence": 0.95,
        "production_cost": "LOW", "expo_feasibility": "A",
        "reference_roles": ["BACK_VIEW", "DIRECTING_SCRIPT", "SPINE_LINE"],
        "director_script": "背对我站好，单臂举过头顶撑开薄纱，右腿微曲足尖点地！身体呈现优美S弯弧线，不用回头，就给一个纯粹高贵的背影！好，深呼吸，啪！",
        "model_setup": "standing", "camera_position": "back eye level", "recommended_lens": "50mm f/1.8", "crop": "full body",
        "micro_adjustments": ["展示大露背蝴蝶骨与深V线条", "长拖尾垂直铺展在地面"],
        "common_failures": ["身体站得过于板正像木桩", "双脚没有重心区分"],
        "observed": ["纯背身艺术构图，单腿屈伸打破对称，背部线条舒展优雅，织物拖尾华丽倾泻。"],
        "inferred": ["王昭君长夜焕生背面大露背（OFFICIAL_004/007）最佳艺术背影方案。"],
        "proposed": ["用于 Shot 05 露背专属成片。"],
        "do_not_copy": ["检查背后安全别走光"],
        "use_for_shots": ["SHOT_05"]
    }
)

# 6. 04_CLOSEUP: Top-right of im11 - closeup mask/fan side glance
add_crop(
    get_grid_cell(im11, 0, 0),
    "refs/03_POSE/04_CLOSEUP/POSE_0403_closeup_fan_mask_side_glance.webp",
    {
        "id": "POSE_0403",
        "category": "03_POSE",
        "priority": "CORE",
        "source": {"url": "https://www.xiaohongshu.com/explore/69f1e5a000000000350390c1", "page_title": "适合新手的简单好用场照姿势合集 - 侧颜特写", "author": "鬼城Eyra", "platform": "小红书", "source_type": "EXPO_FIELD_PHOTO", "verified": True},
        "target_relevance": 0.95, "aesthetic_value": 0.94, "technical_value": 0.97, "source_confidence": 0.95,
        "production_cost": "LOW", "expo_feasibility": "A",
        "reference_roles": ["FACE_CLOSEUP", "DIRECTING_SCRIPT", "PEEPING_EYE"],
        "director_script": "侧脸对准我，右手两指拉起面纱一角挡住嘴唇，下巴稍微往上扬10度，眼睛斜看镜头！眼神要带一点神圣与距离感，别眨眼，啪！",
        "model_setup": "standing", "camera_position": "front-right 45°, close 1m", "recommended_lens": "50mm f/1.8", "crop": "closeup",
        "micro_adjustments": ["光圈收至 f/2.5 确保瞳孔与面纱纹理清晰", "下颌线保持清晰投影"],
        "common_failures": ["遮挡面积过大看不出是谁", "眼神无神"],
        "observed": ["面部微距特写，薄纱半遮面庞，眼神清冷而深邃。"],
        "inferred": ["水母面纱半透质感与东方含蓄神性完美融合。"],
        "proposed": ["用于 Shot 04 与 Shot 07。"],
        "do_not_copy": ["不可完全遮挡面部"],
        "use_for_shots": ["SHOT_04", "SHOT_07"]
    }
)

# 7. 05_HANDS_EXPRESSION: Bottom-right of im11 - holding umbrella/staff shaft hands
add_crop(
    get_grid_cell(im11, 2, 2),
    "refs/03_POSE/05_HANDS_EXPRESSION/POSE_0502_hands_umbrella_shaft_interact.webp",
    {
        "id": "POSE_0502",
        "category": "03_POSE",
        "priority": "CORE",
        "source": {"url": "https://www.xiaohongshu.com/explore/69f1e5a000000000350390c1", "page_title": "适合新手的简单好用场照姿势合集 - 手部持物细节", "author": "鬼城Eyra", "platform": "小红书", "source_type": "EXPO_FIELD_PHOTO", "verified": True},
        "target_relevance": 0.94, "aesthetic_value": 0.91, "technical_value": 0.95, "source_confidence": 0.95,
        "production_cost": "LOW", "expo_feasibility": "B",
        "reference_roles": ["HANDS_EXPRESSION", "DIRECTING_SCRIPT", "GRIP_DETAIL"],
        "director_script": "双手上下交叠握在法杖杆身处，十指微曲放松，低头看着双手握持的地方。表情放柔和，像在默默为武器祈祷，好，啪！",
        "model_setup": "prop", "camera_position": "front-high 15°", "recommended_lens": "50mm f/1.8", "crop": "half body / bust",
        "micro_adjustments": ["手指关节放松，不要发白用力", "胸前红色晶核在双臂环抱中保持可见"],
        "common_failures": ["双手用力过猛手背青筋凸显", "法杖歪斜"],
        "observed": ["手部持物特写，双手柔和交叠握持杆身，具有祈祷与宁静的仪式感。"],
        "inferred": ["极好的情感沉淀镜头，丰富成片情绪维度。"],
        "proposed": ["用于 Shot 08 与 Chain 04。"],
        "do_not_copy": ["不可手指僵直"],
        "use_for_shots": ["SHOT_08"]
    }
)

# 8. 08_LOW_ANGLE: expo dynamic low angle stride from expo_p1
if expo_p1.exists():
    im_p1 = Image.open(expo_p1)
    target_p1 = ROOT / "refs/03_POSE/08_LOW_ANGLE/POSE_0803_expo_dynamic_low_angle_stride.webp"
    im_p1.save(target_p1, "WEBP", quality=92)
    print("Saved POSE_0803")

    new_refs.append({
        "id": "POSE_0803",
        "file": "refs/03_POSE/08_LOW_ANGLE/POSE_0803_expo_dynamic_low_angle_stride.webp",
        "category": "03_POSE",
        "priority": "CORE",
        "source": {"url": "https://www.xiaohongshu.com/explore/6a2fd1fb000000000702df85", "page_title": "漫展万能场照实拍示范 - 低机位大跨步动态", "author": "秋桑桑桑.📷", "platform": "小红书", "source_type": "EXPO_FIELD_PHOTO", "verified": True},
        "target_relevance": 0.95, "aesthetic_value": 0.94, "technical_value": 0.98, "source_confidence": 0.98,
        "production_cost": "LOW", "expo_feasibility": "A",
        "reference_roles": ["LOW_ANGLE", "DIRECTING_SCRIPT", "EXPO_FLOOR_DYNAMIC"],
        "director_script": "摄影师单膝下跪贴地！Coser 单膝微屈，右腿向镜头正前方斜跨迈出，脚尖下压点地！一手持杖一手握拳，身体前倾昂首，眼神居高临下看镜头！好，稳住，啪！",
        "model_setup": "standing", "camera_position": "low angle ground level (20cm off floor)", "recommended_lens": "24-240 @ 28–35mm", "crop": "full body dynamic",
        "micro_adjustments": ["极低机位避开漫展过道路人", "腿部向前伸展获得极致广角拉长"],
        "common_failures": ["摄影师机位不够低无法避开人群", "模特向前跨步重心不稳晃动"],
        "observed": ["大型展馆地面实地极低视角大跨步动作，背景完全为场馆高层钢结构，人群完全被挡在身体后方，动势惊人。"],
        "inferred": ["漫展现场避开人群杂乱的最有效构图方式。"],
        "proposed": ["用于 Shot 11（低机位仰角威严长腿）。"],
        "do_not_copy": ["注意裙摆防走光安全检查"],
        "use_for_shots": ["SHOT_11"]
    }
)

# 9. 04_LIGHTING: expo off-camera flash shadow carving from expo_p4
if expo_p4.exists():
    im_p4 = Image.open(expo_p4)
    target_p4 = ROOT / "refs/04_LIGHTING/LIGHTING_004_expo_off_camera_flash_shadow_carving.webp"
    im_p4.save(target_p4, "WEBP", quality=92)
    print("Saved LIGHTING_004")

    new_refs.append({
        "id": "LIGHTING_004",
        "file": "refs/04_LIGHTING/LIGHTING_004_expo_off_camera_flash_shadow_carving.webp",
        "category": "04_LIGHTING",
        "priority": "CORE",
        "source": {"url": "https://www.xiaohongshu.com/explore/6a2fd1fb000000000702df85", "page_title": "漫展万能场照实拍示范 - 离机闪光灯立体阴影雕刻", "author": "秋桑桑桑.📷", "platform": "小红书", "source_type": "EXPO_FIELD_PHOTO", "verified": True},
        "target_relevance": 0.97, "aesthetic_value": 0.94, "technical_value": 0.99, "source_confidence": 0.98,
        "production_cost": "LOW", "expo_feasibility": "A",
        "reference_roles": ["ONE_LIGHT_SETUP", "LIGHTING_CARVING", "EXPO_ATMOSPHERE"],
        "director_script": "（单灯实战指导：V100 45度高位前侧光，精确照亮模特面容与衣服暗部，背景自然暗下 1 档，彻底杜绝大平脸）",
        "model_setup": "standing", "camera_position": "front-right 30°", "recommended_lens": "50mm f/1.8", "crop": "3/4 portrait",
        "micro_adjustments": ["灯具距离 Coser 严格控制在 1.5 米内", "柔光附件避免漏光进入相机镜头"],
        "common_failures": ["闪光灯直射产生油光", "背景全黑失去现场感"],
        "observed": ["漫展暗调环境中单灯精准塑形，高光与阴影过渡柔和细腻，人物质感高级脱俗。"],
        "inferred": ["充分证明 Godox V100 单灯离机配合柔光罩的极致成片品质。"],
        "proposed": ["作为 LIGHT_MODE_01 的核心布光参考。"],
        "do_not_copy": ["不要机顶直闪"],
        "use_for_shots": ["SHOT_01", "SHOT_02", "SHOT_03", "SHOT_04"]
    }
)

# Append to references.yaml
with open(YAML_FILE, "r", encoding="utf-8") as f:
    current_data = yaml.safe_load(f)

existing_ids = {x["id"] for x in current_data}
added = 0
for r in new_refs:
    if r["id"] not in existing_ids:
        current_data.append(r)
        added += 1

with open(YAML_FILE, "w", encoding="utf-8") as f:
    yaml.dump(current_data, f, allow_unicode=True, sort_keys=False, indent=2)

print(f"Phase 2 complete! Added {added} high-value references!")
