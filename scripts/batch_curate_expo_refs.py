from PIL import Image
from pathlib import Path
import yaml

ROOT = Path("references/changye-huansheng")
YAML_FILE = ROOT / "data" / "references.yaml"

# Load source sheets
p12 = Path("staging/downloads/eyra_poses/eyra_pose_12.webp") # 无道具类
p07 = Path("staging/downloads/eyra_poses/eyra_pose_07.webp") # 棍棒
p05 = Path("staging/downloads/eyra_poses/eyra_pose_05.webp") # 长柄武器
p04 = Path("staging/downloads/eyra_poses/eyra_pose_04.webp") # 长刀/长道具
p11 = Path("staging/downloads/eyra_poses/eyra_pose_11.webp") # 花魁/伞/回眸背影

im12 = Image.open(p12)
im07 = Image.open(p07)
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

# ==========================================
# 01_STANDING (无道具极速站姿)
# ==========================================
# 1. POSE_0102: Bottom-right of im12 - standing relaxed, hand near tie/chest
add_crop(
    get_grid_cell(im12, 2, 1), # bottom-center
    "refs/03_POSE/01_STANDING/POSE_0102_standing_hand_to_neck_cape_flow.webp",
    {
        "id": "POSE_0102",
        "category": "03_POSE",
        "priority": "CORE",
        "source": {"url": "https://www.xiaohongshu.com/explore/69f1e5a000000000350390c1", "page_title": "适合新手的简单好用场照姿势合集", "author": "鬼城Eyra", "platform": "小红书", "source_type": "EXPO_FIELD_PHOTO", "verified": True},
        "target_relevance": 0.94, "aesthetic_value": 0.90, "technical_value": 0.95, "source_confidence": 0.95,
        "production_cost": "LOW", "expo_feasibility": "A",
        "reference_roles": ["STANDING_POSE", "DIRECTING_SCRIPT", "CAPE_DRAPING"],
        "director_script": "身体正对偏左15度，右手抬起来轻轻搭在后颈头发上，左手自然垂下。挺胸收腹，眼神看着我头顶偏右，表现出深海神女微风拂发的气质！好，保持，啪！",
        "model_setup": "standing", "camera_position": "front-right 15°, eye level", "recommended_lens": "50mm f/1.8", "crop": "full body / 3/4",
        "micro_adjustments": ["手搭后颈要轻，手指自然微曲", "重心放在前脚，后脚脚跟微抬"],
        "common_failures": ["手肘过于向外显得粗笨", "耸肩导致脖子变短"],
        "observed": ["全身站姿，单手扶颈后发丝，披风/长纱随风微扬，体态挺拔舒展。"],
        "inferred": ["适合表现王昭君水母帽垂纱与肩部流线型。"],
        "proposed": ["用于 Shot 01 站姿备选。"],
        "do_not_copy": ["不要耸肩"],
        "use_for_shots": ["SHOT_01", "SHOT_02"]
    }
)

# 2. POSE_0103: Top-right of im05 - standing with staff vertical beside, hand on hip
add_crop(
    get_grid_cell(im05, 0, 2),
    "refs/03_POSE/01_STANDING/POSE_0103_standing_scepter_hand_on_hip.webp",
    {
        "id": "POSE_0103",
        "category": "03_POSE",
        "priority": "CORE",
        "source": {"url": "https://www.xiaohongshu.com/explore/69f1e5a000000000350390c1", "page_title": "适合新手的简单好用场照姿势合集", "author": "鬼城Eyra", "platform": "小红书", "source_type": "EXPO_FIELD_PHOTO", "verified": True},
        "target_relevance": 0.95, "aesthetic_value": 0.92, "technical_value": 0.96, "source_confidence": 0.95,
        "production_cost": "LOW", "expo_feasibility": "B",
        "reference_roles": ["STANDING_POSE", "DIRECTING_SCRIPT", "STAFF_HIP_STANCE"],
        "director_script": "左手扶在腰间，右手握紧竖琴法杖立在右侧地面！右脚稍微往后退半步，身体重心放后脚，脸转过来找镜头，下巴稍微扬起20度，俯视镜头的女王神性！好，啪！",
        "model_setup": "prop", "camera_position": "front-left 20°, slightly low angle", "recommended_lens": "24-240 @ 35–50mm", "crop": "full body",
        "micro_adjustments": ["下巴抬高20度展现傲然神性", "法杖保持垂直，不要歪倒"],
        "common_failures": ["手叉腰变成茶壶状", "法杖离身体太远显得松散"],
        "observed": ["全身站姿，单手叉腰，一手持长柄武器立地，双腿修长交叉。"],
        "inferred": ["极度契合王昭君王者归来的气场。"],
        "proposed": ["用于 Shot 01 全身霸气站姿。"],
        "do_not_copy": ["不可过于叉腰显得粗俗"],
        "use_for_shots": ["SHOT_01", "SHOT_10"]
    }
)

# ==========================================
# 02_STOOL_SEATED (小马扎/坐姿出片)
# ==========================================
# 3. POSE_0202: Top-right of im12 - seated on stool, legs crossed, chin resting
add_crop(
    get_grid_cell(im12, 0, 2),
    "refs/03_POSE/02_STOOL_SEATED/POSE_0202_stool_crossed_legs_forward_lean.webp",
    {
        "id": "POSE_0202",
        "category": "03_POSE",
        "priority": "CORE",
        "source": {"url": "https://www.xiaohongshu.com/explore/69f1e5a000000000350390c1", "page_title": "适合新手的简单好用场照姿势合集", "author": "鬼城Eyra", "platform": "小红书", "source_type": "EXPO_FIELD_PHOTO", "verified": True},
        "target_relevance": 0.95, "aesthetic_value": 0.91, "technical_value": 0.96, "source_confidence": 0.95,
        "production_cost": "LOW", "expo_feasibility": "B",
        "reference_roles": ["STOOL_SEATED", "DIRECTING_SCRIPT", "LEG_EXTENSION"],
        "director_script": "坐马扎前边，双腿交叉叠起来，上面这条腿的脚尖死死绷直往前探！双手交叉放在膝盖上，身体稍微往前探一点，眼神看镜头，保持优雅神态，好，啪！",
        "model_setup": "stool", "camera_position": "front-right 20°, eye level", "recommended_lens": "50mm f/1.8", "crop": "3/4 / full body",
        "micro_adjustments": ["二郎腿交叉时上腿脚尖必须下压绷直", "脊椎挺直微前倾，杜绝驼背"],
        "common_failures": ["二郎腿脚尖勾起像大叔坐姿", "重心过于靠后导致衣服堆褶"],
        "observed": ["侧坐于凳上，双腿优雅交叠，前脚尖斜向下绷直，上身挺拔前倾。"],
        "inferred": ["二郎腿斜前延伸能在视觉上创造极致长腿线条。"],
        "proposed": ["用于 Shot 09 小马扎坐姿进阶。"],
        "do_not_copy": ["脚尖不可勾起"],
        "use_for_shots": ["SHOT_09"]
    }
)

# 4. POSE_0203: Bottom-left of im04 - seated on stool, weapon resting across knee
add_crop(
    get_grid_cell(im04, 2, 0),
    "refs/03_POSE/02_STOOL_SEATED/POSE_0203_stool_staff_horizontal_cross.webp",
    {
        "id": "POSE_0203",
        "category": "03_POSE",
        "priority": "CORE",
        "source": {"url": "https://www.xiaohongshu.com/explore/69f1e5a000000000350390c1", "page_title": "适合新手的简单好用场照姿势合集", "author": "鬼城Eyra", "platform": "小红书", "source_type": "EXPO_FIELD_PHOTO", "verified": True},
        "target_relevance": 0.94, "aesthetic_value": 0.90, "technical_value": 0.95, "source_confidence": 0.95,
        "production_cost": "LOW", "expo_feasibility": "B",
        "reference_roles": ["STOOL_SEATED", "DIRECTING_SCRIPT", "STAFF_HORIZONTAL"],
        "director_script": "坐马扎上，法杖横着搭在膝盖前，右手扶着法杖一端，左手轻搭在耳侧头纱上。双腿稍微错开，眼神看镜头右侧虚空，像在沉思！好，啪！",
        "model_setup": "stool", "camera_position": "front, eye level", "recommended_lens": "50mm f/1.8", "crop": "3/4",
        "micro_adjustments": ["法杖横置形成视觉水平稳定线", "头部微侧打破纯对称"],
        "common_failures": ["法杖完全挡住腿部", "眼神呆滞"],
        "observed": ["坐姿，双手与横置武器互动，头部微倾，构图平衡。"],
        "inferred": ["适合表现战斗间隙的深海沉思。"],
        "proposed": ["用于 Shot 09 与 Chain 02。"],
        "do_not_copy": ["法杖不要遮挡胸前红宝石"],
        "use_for_shots": ["SHOT_09"]
    }
)

# ==========================================
# 03_HALF_BODY (半身英雄肖像)
# ==========================================
# 5. POSE_0301: Middle-center of im04 - half body sitting, leaning forward, eye contact
add_crop(
    get_grid_cell(im04, 1, 1),
    "refs/03_POSE/03_HALF_BODY/POSE_0301_half_body_forward_lean_intense_gaze.webp",
    {
        "id": "POSE_0301",
        "category": "03_POSE",
        "priority": "CORE",
        "source": {"url": "https://www.xiaohongshu.com/explore/69f1e5a000000000350390c1", "page_title": "适合新手的简单好用场照姿势合集", "author": "鬼城Eyra", "platform": "小红书", "source_type": "EXPO_FIELD_PHOTO", "verified": True},
        "target_relevance": 0.96, "aesthetic_value": 0.94, "technical_value": 0.97, "source_confidence": 0.95,
        "production_cost": "LOW", "expo_feasibility": "A",
        "reference_roles": ["HALF_BODY", "DIRECTING_SCRIPT", "INTENSE_GAZE"],
        "director_script": "上身往前探过来一点！靠近我的镜头，右手握住法杖斜搭在肩后，左手在胸前微曲。眼神凌厉而清冷，直接盯着镜头正中央！嘴唇微张，好，保持一秒钟，啪！",
        "model_setup": "standing", "camera_position": "front, eye level, 1.5m", "recommended_lens": "50mm f/1.8", "crop": "half body",
        "micro_adjustments": ["上身前倾拉近与镜头距离，增强压迫感", "锁骨与颈部线条自然拉出"],
        "common_failures": ["前倾变成耸肩龟颈", "眼神太凶失去神女灵气"],
        "observed": ["中景半身前倾构图，面容极具冲击力，法杖作为背景对角线，景深虚化良好。"],
        "inferred": ["50mm 在 1.5 米处拍摄半身前倾，能获得极强的主体沉浸感。"],
        "proposed": ["作为 Shot 03（半身英雄肖像）的爆发力变体。"],
        "do_not_copy": ["不可伸头驼背"],
        "use_for_shots": ["SHOT_03"]
    }
)

# 6. POSE_0302: Middle-left of im12 - half body seated, hand to cheek
add_crop(
    get_grid_cell(im12, 1, 0),
    "refs/03_POSE/03_HALF_BODY/POSE_0302_half_body_hand_near_mouth_meditation.webp",
    {
        "id": "POSE_0302",
        "category": "03_POSE",
        "priority": "CORE",
        "source": {"url": "https://www.xiaohongshu.com/explore/69f1e5a000000000350390c1", "page_title": "适合新手的简单好用场照姿势合集", "author": "鬼城Eyra", "platform": "小红书", "source_type": "EXPO_FIELD_PHOTO", "verified": True},
        "target_relevance": 0.95, "aesthetic_value": 0.93, "technical_value": 0.96, "source_confidence": 0.95,
        "production_cost": "LOW", "expo_feasibility": "A",
        "reference_roles": ["HALF_BODY", "DIRECTING_SCRIPT", "HAND_GESTURE"],
        "director_script": "侧身对镜头，右手食指指尖虚贴在下唇角，手指微曲，眼神看向左边斜上方。表现出在深渊里听到微弱声音的神态，安静，好，啪！",
        "model_setup": "standing", "camera_position": "front-right 30°, eye level", "recommended_lens": "50mm f/1.8", "crop": "half body / bust",
        "micro_adjustments": ["指尖虚碰，绝对不可压迫面颊", "手背朝向侧面，展现纤细手腕"],
        "common_failures": ["整只手包住下巴像牙疼", "手腕僵直发硬"],
        "observed": ["半身特写，手势优雅微曲置于唇角，侧颜神态静谧专注。"],
        "inferred": ["极其高级的时尚人像手势，易于普通 Coser 掌握。"],
        "proposed": ["用于 Shot 03 与 Shot 04 之间的过渡。"],
        "do_not_copy": ["不可真用力托腮"],
        "use_for_shots": ["SHOT_03", "SHOT_04"]
    }
)

# ==========================================
# 04_CLOSEUP (面部特写与表情)
# ==========================================
# 7. POSE_0402: Bottom-right of im12 - low angle closeup looking into lens
add_crop(
    get_grid_cell(im12, 2, 2),
    "refs/03_POSE/04_CLOSEUP/POSE_0402_low_angle_closeup_cool_look.webp",
    {
        "id": "POSE_0402",
        "category": "03_POSE",
        "priority": "CORE",
        "source": {"url": "https://www.xiaohongshu.com/explore/69f1e5a000000000350390c1", "page_title": "适合新手的简单好用场照姿势合集", "author": "鬼城Eyra", "platform": "小红书", "source_type": "EXPO_FIELD_PHOTO", "verified": True},
        "target_relevance": 0.95, "aesthetic_value": 0.92, "technical_value": 0.96, "source_confidence": 0.95,
        "production_cost": "LOW", "expo_feasibility": "A",
        "reference_roles": ["FACE_CLOSEUP", "DIRECTING_SCRIPT", "LOW_ANGLE_LOOK"],
        "director_script": "我稍微蹲下来一点仰拍你的脸，你下巴收紧，眼神居高临下看向镜头！嘴唇抿住带一丝冷傲，不要笑，头顶水母帽露出来，很好，稳住，啪！",
        "model_setup": "standing", "camera_position": "front low angle 30°", "recommended_lens": "50mm f/1.8", "crop": "bust / closeup",
        "micro_adjustments": ["仰拍特写必须收下巴拉长颈线，严禁仰头露鼻孔", "眼神向下压，产生神性俯视感"],
        "common_failures": ["仰头露大鼻孔", "收下巴过猛挤出双下巴"],
        "observed": ["微仰视角面部特写，神色坚毅冷峻，五官轮廓分明。"],
        "inferred": ["低角度特写能极大增强角色的神圣主宰感。"],
        "proposed": ["用于 Shot 04 面部神性特写。"],
        "do_not_copy": ["避免鼻孔对准镜头"],
        "use_for_shots": ["SHOT_04"]
    }
)

# ==========================================
# 05_HANDS_EXPRESSION (手势与神圣微光)
# ==========================================
# 8. POSE_0501: Center of im11 - hands holding mask to face (adapt to veil/orb)
add_crop(
    get_grid_cell(im11, 1, 1),
    "refs/03_POSE/05_HANDS_EXPRESSION/POSE_0501_hands_cupping_face_veil_peep.webp",
    {
        "id": "POSE_0501",
        "category": "03_POSE",
        "priority": "CORE",
        "source": {"url": "https://www.xiaohongshu.com/explore/69f1e5a000000000350390c1", "page_title": "适合新手的简单好用场照姿势合集", "author": "鬼城Eyra", "platform": "小红书", "source_type": "EXPO_FIELD_PHOTO", "verified": True},
        "target_relevance": 0.95, "aesthetic_value": 0.94, "technical_value": 0.97, "source_confidence": 0.95,
        "production_cost": "LOW", "expo_feasibility": "A",
        "reference_roles": ["HANDS_EXPRESSION", "DIRECTING_SCRIPT", "VEIL_PEEP"],
        "director_script": "双手捧在脸颊下半部，指尖拉住水母面纱的边缘，把鼻子和嘴唇轻轻遮住，只露出一双眼睛看我！眼神要深邃，睫毛扬起来，绝美，保持，啪！",
        "model_setup": "standing", "camera_position": "front eye level", "recommended_lens": "50mm f/1.8", "crop": "bust closeup",
        "micro_adjustments": ["双手手指错落排开，手背微向外翻", "仅露出眉眼与瞳孔高光"],
        "common_failures": ["双手完全挡死面部", "手指并拢像鸭蹼"],
        "observed": ["双手持道具/薄纱半掩面容，露出极其迷人的双眸与睫毛，具有极强东方神秘神性。"],
        "inferred": ["完美契合王昭君水母头冠半透面纱的实拍互动。"],
        "proposed": ["用于 Shot 07（水母头纱互动）与 Chain 04。"],
        "do_not_copy": ["不要将整张脸遮光"],
        "use_for_shots": ["SHOT_07"]
    }
)

# ==========================================
# 07_TURNING_DYNAMIC (小幅度转身与流动)
# ==========================================
# 9. POSE_0702: Middle-right of im12 - standing single leg kick, dynamic turn
add_crop(
    get_grid_cell(im12, 1, 2),
    "refs/03_POSE/07_TURNING_DYNAMIC/POSE_0702_dynamic_turn_one_leg_pivot.webp",
    {
        "id": "POSE_0702",
        "category": "03_POSE",
        "priority": "CORE",
        "source": {"url": "https://www.xiaohongshu.com/explore/69f1e5a000000000350390c1", "page_title": "适合新手的简单好用场照姿势合集", "author": "鬼城Eyra", "platform": "小红书", "source_type": "EXPO_FIELD_PHOTO", "verified": True},
        "target_relevance": 0.95, "aesthetic_value": 0.93, "technical_value": 0.96, "source_confidence": 0.95,
        "production_cost": "LOW", "expo_feasibility": "A",
        "reference_roles": ["TURNING_DYNAMIC", "DIRECTING_SCRIPT", "PIVOT_SPIN"],
        "director_script": "以左脚为轴，身体原地向右猛地转半圈，裙子甩开的瞬间脸马上回头看我！一、二、转！啪啪啪（高速连拍）！",
        "model_setup": "standing", "camera_position": "front, 3m, eye level", "recommended_lens": "24-240 @ 35–50mm", "crop": "full body",
        "micro_adjustments": ["快门速度设为 1/320s 凝固面部", "脚下原地旋转，严禁跑动位移"],
        "common_failures": ["旋转停下前面部表情失控挤眉弄眼", "快门太慢导致全脸模糊"],
        "observed": ["模特以单腿为轴原地旋转，短裙与飘带在空中张开成优美弧度，面部清晰锐利。"],
        "inferred": ["漫展场地无需奔跑，原地半圈轴心旋转即可让水母伞状短裙摆完全张开。"],
        "proposed": ["用于 Shot 12（轻微转身裙摆动态）与 Chain 06。"],
        "do_not_copy": ["切勿在漫展奔跑"],
        "use_for_shots": ["SHOT_12"]
    }
)

# ==========================================
# 08_LOW_ANGLE (低机位仰角威严长腿)
# ==========================================
# 10. POSE_0802: Bottom-middle of im07 - low angle seated, leg forward to camera
add_crop(
    get_grid_cell(im07, 2, 1),
    "refs/03_POSE/08_LOW_ANGLE/POSE_0802_low_angle_leg_projection_stool.webp",
    {
        "id": "POSE_0802",
        "category": "03_POSE",
        "priority": "CORE",
        "source": {"url": "https://www.xiaohongshu.com/explore/69f1e5a000000000350390c1", "page_title": "适合新手的简单好用场照姿势合集", "author": "鬼城Eyra", "platform": "小红书", "source_type": "EXPO_FIELD_PHOTO", "verified": True},
        "target_relevance": 0.96, "aesthetic_value": 0.92, "technical_value": 0.97, "source_confidence": 0.95,
        "production_cost": "LOW", "expo_feasibility": "B",
        "reference_roles": ["LOW_ANGLE", "DIRECTING_SCRIPT", "PERSPECTIVE_LEGS"],
        "director_script": "坐马扎上，右腿冲着我的镜头斜着伸出来，脚尖踩实绷紧！我蹲下来拍，你下巴抬起来居高临下看我镜头，眼神要霸气，法杖立稳，好，稳住，啪！",
        "model_setup": "stool", "camera_position": "low angle, 40cm off ground", "recommended_lens": "24-240 @ 28–35mm", "crop": "full body",
        "micro_adjustments": ["广角边缘线性透视自然拉长伸向前方的脚部与小腿", "头部保持在画面中心安全区防止畸变"],
        "common_failures": ["脚掌平摊导致脚掌显得巨大", "头部处于边缘变形拉长"],
        "observed": ["低机位广角仰拍坐姿，单腿斜向镜头前方延展，透视极强，霸气威严。"],
        "inferred": ["完美转译官方原画 10 头身长腿视觉（OFFICIAL_001）。"],
        "proposed": ["用于 Shot 11 与 Chain 07。"],
        "do_not_copy": ["注意防走光检查"],
        "use_for_shots": ["SHOT_11"]
    }
)

# ==========================================
# 09_BACK_VIEW (大露背与回眸)
# ==========================================
# 11. POSE_0901: Top-right of im11 - back view turning head, fan/umbrella
add_crop(
    get_grid_cell(im11, 0, 2),
    "refs/03_POSE/09_BACK_VIEW/POSE_0901_classic_back_turn_glance_rim.webp",
    {
        "id": "POSE_0901",
        "category": "03_POSE",
        "priority": "CORE",
        "source": {"url": "https://www.xiaohongshu.com/explore/69f1e5a000000000350390c1", "page_title": "适合新手的简单好用场照姿势合集", "author": "鬼城Eyra", "platform": "小红书", "source_type": "EXPO_FIELD_PHOTO", "verified": True},
        "target_relevance": 0.96, "aesthetic_value": 0.94, "technical_value": 0.98, "source_confidence": 0.95,
        "production_cost": "LOW", "expo_feasibility": "A",
        "reference_roles": ["BACK_VIEW", "DIRECTING_SCRIPT", "TURNING_GLANCE"],
        "director_script": "身体完全背对我站立，挺胸收腹！肩膀千万不要转动，只把头部慢慢向右后方转过来找镜头！下巴微收，眼神锁定我的镜头，看我！好，啪！",
        "model_setup": "standing", "camera_position": "back-right 20°, eye level", "recommended_lens": "50mm f/1.8", "crop": "full body / 3/4",
        "micro_adjustments": ["肩膀保持背向水平，仅颈椎旋转", "露出完整大露背深V线条与肩胛骨"],
        "common_failures": ["整个身体跟着转过来变成侧身照", "转头过度翻白眼"],
        "observed": ["纯背向站立，身体不转仅头部回眸，展现背部优美线条与服饰背面拖尾细节。"],
        "inferred": ["王昭君长夜焕生官方大露背（OFFICIAL_004/007）的绝对必拍姿态。"],
        "proposed": ["作为 Shot 05（经典神女回眸）与 Chain 03 的核心参考。"],
        "do_not_copy": ["避免后背拉链穿帮"],
        "use_for_shots": ["SHOT_05"]
    }
)

# ==========================================
# 10_EASY_BACKUP (30秒极速保底防疲劳)
# ==========================================
# 12. POSE_1001: Middle-center of im12 - standing arms raised stretching
add_crop(
    get_grid_cell(im12, 1, 1),
    "refs/03_POSE/10_EASY_BACKUP/POSE_1001_standing_arms_raised_stretch.webp",
    {
        "id": "POSE_1001",
        "category": "03_POSE",
        "priority": "CORE",
        "source": {"url": "https://www.xiaohongshu.com/explore/69f1e5a000000000350390c1", "page_title": "适合新手的简单好用场照姿势合集", "author": "鬼城Eyra", "platform": "小红书", "source_type": "EXPO_FIELD_PHOTO", "verified": True},
        "target_relevance": 0.94, "aesthetic_value": 0.90, "technical_value": 0.95, "source_confidence": 0.95,
        "production_cost": "LOW", "expo_feasibility": "A",
        "reference_roles": ["EASY_BACKUP", "DIRECTING_SCRIPT", "RELAXED_POSE"],
        "director_script": "自然站好，单臂举过头顶轻轻舒展，像伸懒腰一样放松！下巴微扬，眼神带一点若有所思，保持这个随性自然的动作，咔嚓！",
        "model_setup": "standing", "camera_position": "front, eye level", "recommended_lens": "50mm f/1.8", "crop": "3/4 / half body",
        "micro_adjustments": ["手臂高举时肩膀下沉，拉长颈部", "神态放松随性，消除拍照紧张感"],
        "common_failures": ["手臂僵直如投降", "驼背"],
        "observed": ["全身站姿，单臂向上轻柔伸展，体态自然放松，充满生命复苏舒展感。"],
        "inferred": ["当 Coser 疲倦僵硬时，伸展动作能瞬间重置身体柔韧感。"],
        "proposed": ["用于 Chain 08 极速保底流。"],
        "do_not_copy": ["不要动作过猛拉扯服装"],
        "use_for_shots": ["SHOT_06"]
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

print(f"Batch curation complete! Successfully added {added} precision expo poses across all subdirectories!")
