import yaml
from pathlib import Path
from PIL import Image

ROOT = Path("references/changye-huansheng")
YAML_PATH = ROOT / "data/references.yaml"

with open(YAML_PATH, "r", encoding="utf-8") as f:
    refs = yaml.safe_load(f)

# Build a lookup by ID
refs_by_id = {r["id"]: r for r in refs}

# 1. Update 10 TRUE CORE POSE entries
core_pose_updates = {
    "POSE_0101": {
        "file": "refs/03_POSE/01_STANDING/POSE_0101_standing_casual_ponytail.webp",
        "priority": "CORE",
        "expo_feasibility": "A",
        "target_relevance": 0.92,
        "aesthetic_value": 0.94,
        "technical_value": 0.93,
        "source_confidence": 0.95,
        "production_cost": "LOW",
        "reference_roles": ["POSE_DIRECTING", "EXPO_FEASIBILITY", "GENTLE_STANDING", "HAIR_VEIL_INTERACTION"],
        "source": {
            "url": "https://www.xiaohongshu.com/explore/69fc1c2d000000001a02e152",
            "page_title": "白石漫展场照（原标题未完整记录）",
            "author": "未记录 (白石漫展场照)",
            "platform": "小红书",
            "source_type": "EXPO_FIELD_PHOTO",
            "verified": True
        },
        "image_quality": {
            "width": 1080,
            "height": 1619,
            "source_quality": "HQ_DOWNLOAD",
            "quality_pass": True
        },
        "visual_audit": {
            "actual_pose": "漫展走廊3/4微侧身站立，左手反手轻捏耳后发梢与头纱边，右手屈肘收于胸前，下半身微侧跨步拉长身形，眼神灵动微带笑意",
            "filename_match": "YES",
            "metadata_match": "YES",
            "director_script_match": "YES",
            "visually_verified": True
        },
        "director_script": "“身体往右侧微转30度，重心压在后脚；左手抬起来轻轻捏住耳后的发梢与垂纱，脸转回来找我镜头，眼神清冷带一点浅笑！”",
        "model_setup": "站姿侧身30度，重心在后腿，前脚脚尖点地绷直；左手抬起虚握发尾，右手收于胸前。",
        "camera_position": "平视略微俯角，离地约 1.4 米，距离模特 1.8-2.2 米。",
        "recommended_lens": "Sony 50mm f/1.8 (光圈全开 f/1.8 - f/2.0)",
        "crop": "七分身至大半身，保留发梢与裙摆轮廓",
        "micro_adjustments": ["下巴微收收紧下颌线", "捏发尾的手指放松切勿用力扯头发"],
        "common_failures": ["正对镜头站成死板证件照", "手部过于用力导致手背青筋凸起"],
        "observed": ["漫展走廊实拍环境，背景带有展馆玻璃窗自然散景与微弱人流反光。", "模特呈 3/4 微侧站姿，双肩自然形成高低落差，左手轻提发尾形成动作张力。", "面部朝向镜头正面，受光均匀自然，眼神带笑不呆板。"],
        "inferred": ["等效 50mm 焦段在大光圈（f/2.0左右）下成功将漫展背景虚化，剥离人物主体。", "轻抚发尾的动作能有效解决 Coser 手部僵硬无处安放的问题。"],
        "proposed": ["作为漫展现场开场第一组必保站姿（Shot 01 / Chain 01 原型A）。", "摄影师站立平视，V100 于右前侧 45 度微补面光即可出片。"],
        "do_not_copy": ["不可让 Coser 双手死死贴在身体两侧呆立。", "不可让人物正对镜头站成证件照大头照。"]
    },
    "POSE_0201": {
        "file": "refs/03_POSE/02_STOOL_SEATED/POSE_0201_stool_leg_extension_open_arms.webp",
        "priority": "CORE",
        "expo_feasibility": "A",
        "target_relevance": 0.96,
        "aesthetic_value": 0.95,
        "technical_value": 0.96,
        "source_confidence": 0.98,
        "production_cost": "LOW",
        "reference_roles": ["STOOL_SEATED_POSE", "JELLYFISH_FLOATING", "BALLET_FOOT_EXTENSION", "EXPO_FEASIBILITY"],
        "source": {
            "url": "https://www.xiaohongshu.com/explore/67c802000000000014023b12",
            "page_title": "吧台椅/梯子坐姿分享 (原标题)",
            "author": "舟零",
            "platform": "小红书",
            "source_type": "POSE_TUTORIAL",
            "verified": True
        },
        "image_quality": {
            "width": 1080,
            "height": 1620,
            "source_quality": "HQ_DOWNLOAD",
            "quality_pass": True
        },
        "visual_audit": {
            "actual_pose": "圆凳端坐，右腿向前下方斜向伸直并紧绷脚尖拉长腿部线条，左腿弯曲交叠，双手向两侧微张手心向上如水母浮游态，浅蓝短发，眼神直视镜头",
            "filename_match": "YES",
            "metadata_match": "YES",
            "director_script_match": "YES",
            "visually_verified": True
        },
        "director_script": "“坐在小马扎前三分之一，右腿向前斜着伸直，脚尖绷紧；双手像水母触手一样向身体两侧自然浮开，下巴微收，眼神看镜头！”",
        "model_setup": "小凳/马扎浅坐，单腿向前斜伸绷直脚尖，双手向两侧展开手心向上微屈手腕。",
        "camera_position": "低机位，离地约 0.8-1.0 米，平视胸腹部。",
        "recommended_lens": "Sony 50mm f/1.8 (光圈 f/2.0)",
        "crop": "竖幅全身，底部保留绷直的脚尖",
        "micro_adjustments": ["脚尖必须完全绷直延长小腿视觉长度", "双手不要死死伸直，手肘和手腕保留微弧度"],
        "common_failures": ["整个人瘫坐在马扎深处导致驼背大肚子", "脚尖回勾导致小腿显得粗短"],
        "observed": ["模特浅蓝短发造型与王昭君长夜焕生短发高度呼应。", "单腿向前斜伸有效避免小凳坐姿腿部堆叠挤压大腿肉的问题。", "双手展开的动态具有极强的水下悬浮、水母触手舒展张力。"],
        "inferred": ["漫展现场利用随身携带的小马扎即可完美复刻该姿态。", "50mm 在低机位仰拍能同时拉长腿部线条并规避展馆背景杂乱人流。"],
        "proposed": ["作为马扎坐姿系列的核心第一张（Shot 03 / Chain 03 原型F）。", "V100 设在正面偏高 45 度顺光打亮面部与双臂轮廓。"],
        "do_not_copy": ["不可全臀深坐马扎", "不可勾脚尖"]
    },
    "POSE_0202": {
        "file": "refs/03_POSE/02_STOOL_SEATED/POSE_0202_stool_chest_touch_lean_back.webp",
        "priority": "CORE",
        "expo_feasibility": "A",
        "target_relevance": 0.95,
        "aesthetic_value": 0.94,
        "technical_value": 0.95,
        "source_confidence": 0.98,
        "production_cost": "LOW",
        "reference_roles": ["STOOL_SEATED_POSE", "CHEST_GEM_TOUCH", "LEAN_BACK_ELEGANCE", "EXPO_FEASIBILITY"],
        "source": {
            "url": "https://www.xiaohongshu.com/explore/67c802000000000014023b12",
            "page_title": "吧台椅/梯子坐姿分享 (原标题)",
            "author": "舟零",
            "platform": "小红书",
            "source_type": "POSE_TUTORIAL",
            "verified": True
        },
        "image_quality": {
            "width": 1080,
            "height": 1620,
            "source_quality": "HQ_DOWNLOAD",
            "quality_pass": True
        },
        "visual_audit": {
            "actual_pose": "圆凳坐姿身体微微后仰，左手向后撑住椅面边缘，右手手指轻抚锁骨与胸前宝石位置，双腿并拢斜向前伸绷脚尖，头部微仰神圣苏醒态",
            "filename_match": "YES",
            "metadata_match": "YES",
            "director_script_match": "YES",
            "visually_verified": True
        },
        "director_script": "“身体重心稍稍后倾，左手在身后撑住马扎边缘；右手食指轻轻贴在胸口红核宝石上方，双腿斜伸绷直脚尖，下巴轻抬！”",
        "model_setup": "马扎坐姿躯干后仰约15度，后手撑凳，前手抚胸，双腿斜向伸展。",
        "camera_position": "胸口高度平视，离地约 1.0 米。",
        "recommended_lens": "Sony 50mm f/1.8",
        "crop": "七分身至大半身，重点展示胸口手势与下颌线",
        "micro_adjustments": ["后仰幅度不要太大防止脖颈挤压颈纹", "抚胸手指要轻搭，切勿手掌死按胸部"],
        "common_failures": ["后仰塌腰导致重心失衡摔倒", "手掌死按胸口挡住红核宝石细节"],
        "observed": ["身体微后仰拉长颈部线条，面部自然迎向上方光源。", "右手食指与中指轻搭锁骨下方，绝妙对应王昭君长夜焕生胸口红核珊瑚。", "双腿斜伸保持下半身纤细轮廓。"],
        "inferred": ["极度适合在漫展现场展示胸口宝石做工与锁骨高光。", "V100 柔光箱置于正上方 60 度下打，能在锁骨与胸前产生立体阴影。"],
        "proposed": ["作为马扎坐姿系列第二张（Shot 04 / Chain 03 原型B）。"],
        "do_not_copy": ["不可死按胸口", "不可过度后仰挤出下巴肉"]
    },
    "POSE_0301": {
        "file": "refs/03_POSE/03_HALF_BODY/POSE_0301_half_body_hand_reach_perspective.webp",
        "priority": "CORE",
        "expo_feasibility": "A",
        "target_relevance": 0.94,
        "aesthetic_value": 0.95,
        "technical_value": 0.96,
        "source_confidence": 0.96,
        "production_cost": "LOW",
        "reference_roles": ["PERSPECTIVE_REACH", "DIVINE_AWAKENING", "HALF_BODY_IMMERSION"],
        "source": {
            "url": "https://www.xiaohongshu.com/explore/684c98000000000010012e45",
            "page_title": "室内科幻风绫波丽cos攻略（模特：雪糕）",
            "author": "武于钧 (模特：雪糕)",
            "platform": "小红书",
            "source_type": "COSPLAY_PHOTOGRAPHY",
            "verified": True
        },
        "image_quality": {
            "width": 1080,
            "height": 1918,
            "source_quality": "HQ_DOWNLOAD",
            "quality_pass": True
        },
        "visual_audit": {
            "actual_pose": "半身微俯前倾，右手五指自然舒展探向镜头前方形成强烈透视引导，左侧身体收紧，面容冷静神圣直视，浅蓝发丝垂落",
            "filename_match": "YES",
            "metadata_match": "YES",
            "director_script_match": "YES",
            "visually_verified": True
        },
        "director_script": "“上身往前探一点，右手五指张开慢慢朝我镜头伸手，手腕放松；眼睛透过手指看我镜头，表现深海神女唤醒契约的宿命感！”",
        "model_setup": "半身微前倾，单手向镜头探出，五指微张微曲，头部端正眼神穿透手指看镜头。",
        "camera_position": "胸口平视，距离模特约 1.2-1.5 米，右手距离前组镜片约 30-40 厘米。",
        "recommended_lens": "Sony 50mm f/1.8 (光圈 f/2.2 控制手部虚化与眼睛锐度)",
        "crop": "半身特写，手掌占据画面前景下半部",
        "micro_adjustments": ["手部伸出角度略偏侧，切勿完全挡住眼部", "手掌五指保持柔和起伏，不要像抓东西一样僵硬"],
        "common_failures": ["手掌直挺挺挡在脸前导致脸部被遮挡", "焦点对在手指上导致面部完全脱焦虚化"],
        "observed": ["近大远小的强烈手部透视，赋予画面极强的深海交互与召唤感。", "模特神态宁静神圣，发丝与肩部线条利落。"],
        "inferred": ["非常适合在展馆狭窄空间拍摄半身神性召唤大片，无需多余背景。", "A7M4 眼部追焦锁定眼睛，50mm f/2.2 让前景手产生奶油般虚化。"],
        "proposed": ["作为半身互动核心参考（Shot 05 / Chain 02 原型E）。"],
        "do_not_copy": ["手掌完全挡住面部", "手势过于僵硬像抓取武器"]
    },
    "POSE_0401": {
        "file": "refs/03_POSE/04_CLOSEUP/POSE_0401_closeup_chin_touch_contemplation.webp",
        "priority": "CORE",
        "expo_feasibility": "A",
        "target_relevance": 0.95,
        "aesthetic_value": 0.96,
        "technical_value": 0.95,
        "source_confidence": 0.96,
        "production_cost": "LOW",
        "reference_roles": ["FACE_CLOSEUP", "CHIN_TOUCH_GESTURE", "DIVINE_CONTEMPLATION", "50MM_PORTRAIT"],
        "source": {
            "url": "https://www.xiaohongshu.com/explore/66e01234000000001102aabb",
            "page_title": "深海水母少女私影场照",
            "author": "鹿岛漫展组 / 漫展少女",
            "platform": "小红书",
            "source_type": "COSPLAY_PHOTOGRAPHY",
            "verified": True
        },
        "image_quality": {
            "width": 1080,
            "height": 1620,
            "source_quality": "HQ_DOWNLOAD",
            "quality_pass": True
        },
        "visual_audit": {
            "actual_pose": "半身特写端坐，头部微仰，右手食指与中指指尖轻触下唇与下巴边缘，眼神空灵望向上方，面容柔和静思，蓝调通透",
            "filename_match": "YES",
            "metadata_match": "YES",
            "director_script_match": "YES",
            "visually_verified": True
        },
        "director_script": "“下巴微微抬起，右手食指指尖虚搭在下唇边上，不要压到脸颊；眼神望向头顶灯光方向，流露深海神女微思的气质！”",
        "model_setup": "半身近景，单手虚搭下巴，头部轻仰15度，眼神空灵看向斜上方。",
        "camera_position": "平视略微仰角，距离模特约 1.5 米。",
        "recommended_lens": "Sony 50mm f/1.8 (光圈 f/2.0)",
        "crop": "胸部以上特写，保留下巴、手部指尖与头顶头饰",
        "micro_adjustments": ["手指必须是虚触下唇，绝对不可用力按压导致面颊变形", "嘴角保持放松自然微抿"],
        "common_failures": ["整只手掌托住腮帮子把脸挤变形", "眼神涣散死板无神"],
        "observed": ["纯净清透的蓝白色系氛围，指尖点下巴的手势极度典雅高贵。", "面部微仰凸显精致下颌线与修长脖颈。"],
        "inferred": ["取代原过肩持刀等战斗性特写，完美传达王昭君长夜焕生沉静、神圣、柔和的视觉DNA。", "漫展现场只要背景相对干净，单灯加柔光附件就能出极品大头特写。"],
        "proposed": ["作为面部核心精致特写示范（Shot 06 / 原型G）。"],
        "do_not_copy": ["不可死按面颊挤出嘟嘟肉", "不可做俏皮卖萌嘟嘴"]
    },
    "POSE_0501": {
        "file": "refs/03_POSE/05_HANDS_EXPRESSION/POSE_0501_hands_clasp_chest_prayer.webp",
        "priority": "CORE",
        "expo_feasibility": "A",
        "target_relevance": 0.96,
        "aesthetic_value": 0.95,
        "technical_value": 0.95,
        "source_confidence": 0.96,
        "production_cost": "LOW",
        "reference_roles": ["CHEST_PRAYER", "HOLY_DEVOTION", "CRYSTAL_RESONANCE", "STILL_DYNAMICS"],
        "source": {
            "url": "https://www.xiaohongshu.com/explore/67d80400000000001203fe8f",
            "page_title": "鹿岛姿势表（原标题未完整记录）",
            "author": "未记录 (鹿岛姿势表)",
            "platform": "小红书",
            "source_type": "POSE_TUTORIAL",
            "verified": True
        },
        "image_quality": {
            "width": 1080,
            "height": 1621,
            "source_quality": "HQ_DOWNLOAD",
            "quality_pass": True
        },
        "visual_audit": {
            "actual_pose": "双手在胸前合十微扣紧贴锁骨，手指修长合拢，头部微微倾斜，眼神温柔清澈注视镜头，裙摆微动，体态神圣虔诚",
            "filename_match": "YES",
            "metadata_match": "YES",
            "director_script_match": "YES",
            "visually_verified": True
        },
        "director_script": "“双手在胸前合拢微扣，指尖向上贴在锁骨下方；头轻轻向左偏一点，眼睛温柔看着镜头，表现神女虔诚祈愿！”",
        "model_setup": "正面微侧站立，双手胸前合十，手指并拢微弯，头微偏。",
        "camera_position": "眼平偏俯角，离地约 1.5 米。",
        "recommended_lens": "Sony 50mm f/1.8",
        "crop": "七分身至半身，双手合十处于黄金分割点",
        "micro_adjustments": ["双手手指自然并拢贴合，手背向镜头微倾展现手指修长", "肩膀下沉，拉长颈部线条"],
        "common_failures": ["双手紧扣如打架握拳", "耸肩导致气质萎靡"],
        "observed": ["双手胸前合十是最纯粹的神圣仪式感姿势，与长夜焕生神女救赎背景契合。", "动作收敛，对漫展现场空间要求极小（仅需0.5平米）。"],
        "inferred": ["能在杂乱展馆中瞬间收束画面视线，让观者聚焦在面部与胸前双手上。", "极度利于新手 Coser 快速进入角色情绪，免除四肢不知如何摆放的尴尬。"],
        "proposed": ["作为神女祈愿神圣仪态必保镜头（Shot 07 / Chain 02 原型B/H）。"],
        "do_not_copy": ["不可十指交叉扭紧", "不可死死夹紧双肘"]
    },
    "POSE_0601": {
        "file": "refs/03_POSE/06_PROP_WEAPON/POSE_0601_staff_vertical_ground_lean.webp",
        "priority": "CORE",
        "expo_feasibility": "A",
        "target_relevance": 0.93,
        "aesthetic_value": 0.92,
        "technical_value": 0.94,
        "source_confidence": 0.95,
        "production_cost": "LOW",
        "reference_roles": ["PROP_STAFF_LEAN", "VERTICAL_RESTING_STANCE", "NON_COMBAT_ELEGANCE", "EXPO_FEASIBILITY"],
        "source": {
            "url": "https://www.xiaohongshu.com/explore/692019db000000001e031c31",
            "page_title": "明日香 摇滚乐队 cosplay（图文版）",
            "author": "大道寺cheese【图文版】",
            "platform": "小红书",
            "source_type": "COSPLAY_PHOTOGRAPHY",
            "verified": True
        },
        "image_quality": {
            "width": 1080,
            "height": 1620,
            "source_quality": "HQ_DOWNLOAD",
            "quality_pass": True
        },
        "visual_audit": {
            "actual_pose": "台阶立柱旁站立，长道具/琴立于地面，右手扶持道具顶部琴头，左手轻倚身侧栏杆/腰间，身体微倾借力，眼神沉静清冷平视前方",
            "filename_match": "YES",
            "metadata_match": "YES",
            "director_script_match": "YES",
            "visually_verified": True
        },
        "director_script": "“法杖底部立在地面上，右手轻轻搭在法杖顶端；左手搭在腰间或者栏杆上，身体微微斜靠，眼神清冷平视我镜头！”",
        "model_setup": "单侧立姿，长柄法杖垂立于地面，单手虚扶顶部，另一手叉腰或搭于腰际，身体重心偏一侧。",
        "camera_position": "腰平微仰，离地约 1.1 米。",
        "recommended_lens": "Sony 50mm f/1.8",
        "crop": "大全身或大半身，法杖垂直线条与人物身体构成平行引导线",
        "micro_adjustments": ["法杖不要直挺挺垂直，略微向外倾斜5度更具美感", "手指放松搭在顶端，切勿用力死抓法杖头"],
        "common_failures": ["法杖横挡在身前切断身体轮廓", "握法杖过于用力显得紧张粗笨"],
        "observed": ["长道具立地斜倚彻底规避了武器刀剑攻击感，完美转化为法杖/竖琴的非战斗优雅静驻态。", "单侧借力使腰胯自然形成S弯曲，体态修长自然。"],
        "inferred": ["王昭君的竖琴法杖极具分量，漫展现场长时间手持会疲劳；立地扶持极大减轻 Coser 负担。", "垂直线条在杂乱漫展背景中形成强大的视觉支撑轴。"],
        "proposed": ["作为法杖静驻核心方案（Shot 08 / Chain 04 原型C）。"],
        "do_not_copy": ["不可死抓法杖", "不可将法杖当拐杖用力按压"]
    },
    "POSE_0602": {
        "file": "refs/03_POSE/06_PROP_WEAPON/POSE_0602_staff_low_angle_stride.webp",
        "priority": "CORE",
        "expo_feasibility": "A",
        "target_relevance": 0.93,
        "aesthetic_value": 0.93,
        "technical_value": 0.95,
        "source_confidence": 0.95,
        "production_cost": "LOW",
        "reference_roles": ["PROP_STAFF_STRIDE", "CROSS_LEG_EXTENSION", "DYNAMIC_WALKING", "EXPO_FEASIBILITY"],
        "source": {
            "url": "https://www.xiaohongshu.com/explore/68d20300000000001301fa23",
            "page_title": "漫展人像布光与姿势示例（原标题未完整记录）",
            "author": "未记录 (漫展人像布光与姿势示例)",
            "platform": "小红书",
            "source_type": "EXPO_FIELD_PHOTO",
            "verified": True
        },
        "image_quality": {
            "width": 1080,
            "height": 1612,
            "source_quality": "HQ_DOWNLOAD",
            "quality_pass": True
        },
        "visual_audit": {
            "actual_pose": "漫展现场低机位全身站姿，双腿交叉步伐拉长腿部比例，双手横持长道具横于髋前，头戴蝴蝶结微侧，眼神沉着看向镜头，背景展馆灯光虚化",
            "filename_match": "YES",
            "metadata_match": "YES",
            "director_script_match": "YES",
            "visually_verified": True
        },
        "director_script": "“双腿交叉走一步站定，拉长下半身线条；双手把法杖横在腰胯前，手腕放松自然下垂，脸微侧看我镜头！”",
        "model_setup": "交叉步站立，双膝微蹭拉长腿部，双手横握长道具于髋部前方，手腕自然垂落。",
        "camera_position": "低机位仰拍，离地约 0.6-0.8 米，仰角 15 度。",
        "recommended_lens": "Sony 50mm f/1.8",
        "crop": "竖幅全身，头顶与脚底各留 10% 留白",
        "micro_adjustments": ["法杖横置位置保持在髋骨高度，不可挡住胸口宝石", "前脚脚跟踩实，后脚脚尖点地"],
        "common_failures": ["道具横在胸口直接挡死服装核心细节", "双腿平行傻站像木桩"],
        "observed": ["真实漫展展馆实拍，单灯控光将人物与背后人流完美分离。", "双腿交叉步伐从低机位看具有极佳的视觉延展性，横置道具形成水平稳定基线。"],
        "inferred": ["王昭君法杖横于髋前能清晰展示竖琴晶体与珊瑚纹样，且不遮挡胸口红核与腰线。", "漫展走道内仅需向前跨半步即可完成，占地极小。"],
        "proposed": ["作为法杖动态持握核心方案（Shot 09 / Chain 04 原型C）。"],
        "do_not_copy": ["不可横持挡胸", "不可双手死握两端成单杠"]
    },
    "POSE_0701": {
        "file": "refs/03_POSE/07_TURNING_DYNAMIC/POSE_0701_back_turn_over_shoulder_gaze.webp",
        "priority": "CORE",
        "expo_feasibility": "A",
        "target_relevance": 0.97,
        "aesthetic_value": 0.96,
        "technical_value": 0.95,
        "source_confidence": 0.96,
        "production_cost": "LOW",
        "reference_roles": ["BACK_VIEW_TURN", "OPEN_BACK_DRESS_SHOWCASE", "VEIL_FLOW_DISPLAY", "OVER_SHOULDER_GAZE"],
        "source": {
            "url": "https://www.xiaohongshu.com/explore/68f00100000000001503cb89",
            "page_title": "长刀场照动作组图（原标题未完整记录）",
            "author": "双喜📷",
            "platform": "小红书",
            "source_type": "COSPLAY_PHOTOGRAPHY",
            "verified": True
        },
        "image_quality": {
            "width": 1080,
            "height": 1621,
            "source_quality": "HQ_DOWNLOAD",
            "quality_pass": True
        },
        "visual_audit": {
            "actual_pose": "全景完全背对镜头站立，右手持长道具指向地面，左手自然置于腰髋侧，肩膀压平，头部向右后方转过肩凝视镜头，眼神清冷神秘，长发披散背部",
            "filename_match": "YES",
            "metadata_match": "YES",
            "director_script_match": "YES",
            "visually_verified": True
        },
        "director_script": "“背对我站立，肩膀放平下沉；慢慢回头看我的镜头，下巴稍微收一点；右手顺着身侧垂下法杖，展现后背和水母大拖尾！”",
        "model_setup": "身体完全背对镜头，头部转过肩约 75 度，重心落在靠近镜头的单侧腿，后背挺直。",
        "camera_position": "肩平高度，离地约 1.3 米。",
        "recommended_lens": "Sony 50mm f/1.8",
        "crop": "大半身至全身，完整展现背部镂空、头纱与肩颈线条",
        "micro_adjustments": ["转头时下巴轻压向肩部，切勿仰头露出鼻孔", "靠近镜头的肩膀微压低，防止耸肩遮挡下颌线"],
        "common_failures": ["转头幅度过大把脖子扭出严重深颈纹", "背部驼背显得疲惫松垮"],
        "observed": ["完全背身构图是展示角色后背露背剪裁与后脑发型结构的终极方案。", "转头过肩的眼神极具神秘清冷感，与长夜焕生深海救赎者的冷艳气质无缝咬合。"],
        "inferred": ["王昭君长夜焕生皮肤背后拥有巨大的水母垂纱与深V露背设计，正面无法展示，此姿势不可替代。", "漫展现场只要利用展馆单灯打背侧逆光，即可让头纱边缘发光轮廓分明。"],
        "proposed": ["作为背身回眸后背头纱必保核心方案（Shot 10 / Chain 05 原型D）。"],
        "do_not_copy": ["不可扭头过猛挤出深颈纹", "不可驼背弓腰"]
    },
    "POSE_0801": {
        "file": "refs/03_POSE/08_LOW_ANGLE/POSE_0801_low_angle_divine_arch_stretch.webp",
        "priority": "CORE",
        "expo_feasibility": "A",
        "target_relevance": 0.96,
        "aesthetic_value": 0.97,
        "technical_value": 0.95,
        "source_confidence": 0.96,
        "production_cost": "LOW",
        "reference_roles": ["DIVINE_LOW_ANGLE", "S_CURVE_STRETCH", "VEIL_CASCADE", "ARCHITECTURAL_BORROW"],
        "source": {
            "url": "https://www.xiaohongshu.com/explore/66b04800000000001e02ef34",
            "page_title": "水下/水族馆水母裙实拍",
            "author": "深海水族场照实录",
            "platform": "小红书",
            "source_type": "COSPLAY_PHOTOGRAPHY",
            "verified": True
        },
        "image_quality": {
            "width": 1080,
            "height": 1620,
            "source_quality": "HQ_DOWNLOAD",
            "quality_pass": True
        },
        "visual_audit": {
            "actual_pose": "低机位全身仰望，身体呈优美S形微后仰延伸，单手优雅抬起虚触上方拱形建筑/立柱，长裙摆与透明水母拖纱自然下垂，眼神仰望神圣光芒",
            "filename_match": "YES",
            "metadata_match": "YES",
            "director_script_match": "YES",
            "visually_verified": True
        },
        "director_script": "“相机贴地仰拍；重心放在后腿，身体后仰拉出S形线条，右手轻轻抬高虚摸头顶立柱或虚空，头仰起看上方，水母长纱自然下垂！”",
        "model_setup": "微仰展体，单手抬高触碰立柱/虚空，后脚承重前脚绷直，头微仰注视光源方向。",
        "camera_position": "极低机位贴地仰拍，离地 0.4-0.6 米。",
        "recommended_lens": "Sony 50mm f/1.8 (或 24-240mm 广角端 24-35mm)",
        "crop": "竖幅超长大全身，仰拍强化神性纵深感",
        "micro_adjustments": ["抬起的手腕要软，手指成阶梯状虚托，不可僵硬伸爪", "面部微仰但下颌不可过于上翻"],
        "common_failures": ["仰拍角度过猛直接拍鼻孔", "身体僵硬像摸墙电击"],
        "observed": ["彻底取代了原先镰刀低蹲的暴力战斗感，以空灵拉伸的身体曲线展现深海神女的威严神性。", "水母垂纱自然垂坠，与抬高的手臂形成垂直视觉落差。"],
        "inferred": ["漫展现场可以寻找走廊大理石立柱、展台边缘拱形框架执行借力拉伸。", "低机位把展馆人流完全压在腰部以下，天空/天花板成为纯净背景。"],
        "proposed": ["作为神性全身低机位终极压轴方案（Shot 11 / 原型H）。"],
        "do_not_copy": ["不可直拍鼻孔", "不可大劈叉战斗蹲姿"]
    }
}

# Apply core updates
for pid, upd in core_pose_updates.items():
    if pid in refs_by_id:
        refs_by_id[pid].update(upd)
    else:
        upd["id"] = pid
        upd["category"] = "03_POSE"
        refs_by_id[pid] = upd

# Demote non-core POSE items to SUPPORT with clear rationale
support_demotions = {
    "POSE_0102": {
        "priority": "SUPPORT",
        "visual_audit": {
            "actual_pose": "漫展暗调展区正面双脚分开站稳，双手叉腰手肘向两侧撑开轮廓，头部微倾，眼神自信直视镜头（降权说明：双手叉腰过于霸气战斗化，与王昭君神性轻盈气质不符，降为 SUPPORT 轮廓备选）",
            "filename_match": "YES",
            "metadata_match": "YES",
            "director_script_match": "YES",
            "visually_verified": True
        }
    },
    "POSE_0103": {
        "priority": "SUPPORT",
        "visual_audit": {
            "actual_pose": "漫展大面积落地窗前侧身站立，右手抬至眉骨作远眺手势，左手向斜后方自然舒展，身体微侧迎向自然光（说明：自然光利用范本，但远眺手势略偏现代活泼，保留为 SUPPORT 自然光采光参考）",
            "filename_match": "YES",
            "metadata_match": "YES",
            "director_script_match": "YES",
            "visually_verified": True
        }
    },
    "POSE_0104": {
        "priority": "SUPPORT",
        "visual_audit": {
            "actual_pose": "身体靠在立柱侧面，双腿前后错开，右手在帽檐侧面做手势，借力立柱（降权说明：现代街头摇滚风格较强且带V字俏皮感，与神圣神女有代沟，降为 SUPPORT 借柱站姿备选）",
            "filename_match": "YES",
            "metadata_match": "YES",
            "director_script_match": "YES",
            "visually_verified": True
        }
    },
    "POSE_0203": {
        "priority": "SUPPORT",
        "visual_audit": {
            "actual_pose": "台阶低坐姿双腿屈膝收于胸前，双手合抱膝盖，头部微侧枕于膝头，浅蓝短发垂落，眼神空灵悲悯凝视（说明：空灵悲悯情绪极佳，但抱膝会遮挡裙身前襟与胸口红核宝石，保留为 SUPPORT 情绪参考）",
            "filename_match": "YES",
            "metadata_match": "YES",
            "director_script_match": "YES",
            "visually_verified": True
        }
    },
    "POSE_0302": {
        "priority": "SUPPORT",
        "visual_audit": {
            "actual_pose": "高机位俯拍半身，模特头部微侧仰起，右手朝镜头方向虚伸，浅蓝发丝散开，眼神清冷神秘（说明：神态与透视极佳，但高俯拍需要摄影师踩梯凳或在漫展二楼，执行门槛偏高，保留为 SUPPORT 特殊视角）",
            "filename_match": "YES",
            "metadata_match": "YES",
            "director_script_match": "YES",
            "visually_verified": True
        }
    },
    "POSE_0702": {
        "priority": "SUPPORT",
        "visual_audit": {
            "actual_pose": "身处垂直门框/立柱内侧站立，左手扶住门框侧壁，右手手指虚搭领口，身体微侧，头部转正直视镜头（说明：门框立柱前景框架感优秀，但动作略偏紧绷，保留为 SUPPORT 借物构图参考）",
            "filename_match": "YES",
            "metadata_match": "YES",
            "director_script_match": "YES",
            "visually_verified": True
        }
    },
    "POSE_0802": {
        "priority": "SUPPORT",
        "visual_audit": {
            "actual_pose": "纵深狭长通道极低机位仰拍，双腿大步张开前弓后绷拉长双腿，上身前探俯视镜头（降权说明：大跨步攻击蹲姿过于侵略性战斗化，与长夜焕生空灵神圣不符，降为 SUPPORT 透视备选）",
            "filename_match": "YES",
            "metadata_match": "YES",
            "director_script_match": "YES",
            "visually_verified": True
        }
    }
}

for pid, upd in support_demotions.items():
    if pid in refs_by_id:
        refs_by_id[pid].update(upd)

# 3. Add rejected moved files to 90_REJECTED so there are 0 orphan files on disk
rejected_moved = [
    {
        "id": "REJECT_POSE_0401_closeup_over_shoulder_gaze",
        "file": "refs/90_REJECTED/REJECT_POSE_0401_closeup_over_shoulder_gaze.webp",
        "category": "90_REJECTED",
        "priority": "REJECT",
        "source": {"url": "https://www.xiaohongshu.com/explore/68f00100000000001503cb89", "page_title": "长刀场照动作组图", "author": "双喜📷", "platform": "小红书", "source_type": "COSPLAY_PHOTOGRAPHY", "verified": True},
        "target_relevance": 0.50, "aesthetic_value": 0.85, "technical_value": 0.85, "source_confidence": 0.95, "production_cost": "LOW", "expo_feasibility": "C",
        "reference_roles": ["REJECTED_MARTIAL_BLADE"],
        "director_script": "淘汰原因：双手举长刀至头顶为武侠/热血刀客动作，破坏王昭君深海神女的空灵与高雅，被托腮沉思特写取代。",
        "model_setup": "N/A", "camera_position": "N/A", "recommended_lens": "50mm f/1.8", "crop": "closeup",
        "image_quality": {"width": 1080, "height": 1621, "source_quality": "HQ_DOWNLOAD", "quality_pass": True},
        "visual_audit": {"actual_pose": "面部与胸像大特写，双手将长刀刀镡举至头顶上方过肩凝视镜头（淘汰：动作过于武力打斗化）", "filename_match": "YES", "metadata_match": "YES", "director_script_match": "YES", "visually_verified": True},
        "observed": ["动作打斗感过强"], "inferred": ["不适合长夜焕生"], "proposed": ["归入淘汰库"], "do_not_copy": ["双手举刀过顶"]
    },
    {
        "id": "REJECT_POSE_0601_staff_diagonal_cross_chest",
        "file": "refs/90_REJECTED/REJECT_POSE_0601_staff_diagonal_cross_chest.webp",
        "category": "90_REJECTED",
        "priority": "REJECT",
        "source": {"url": "https://www.xiaohongshu.com/explore/68f00100000000001503cb89", "page_title": "长刀场照动作组图", "author": "双喜📷", "platform": "小红书", "source_type": "COSPLAY_PHOTOGRAPHY", "verified": True},
        "target_relevance": 0.55, "aesthetic_value": 0.86, "technical_value": 0.88, "source_confidence": 0.95, "production_cost": "LOW", "expo_feasibility": "C",
        "reference_roles": ["REJECTED_MARTIAL_BLADE"],
        "director_script": "淘汰原因：双手握刀横胸为剑道格斗防守姿态，切断胸前红核视线，被非战斗法杖立地斜倚取代。",
        "model_setup": "N/A", "camera_position": "N/A", "recommended_lens": "50mm f/1.8", "crop": "medium",
        "image_quality": {"width": 1080, "height": 1621, "source_quality": "HQ_DOWNLOAD", "quality_pass": True},
        "visual_audit": {"actual_pose": "双手一高一低握持黑色长刀横跨胸前形成对角线格斗防守（淘汰：刀剑格斗感过重）", "filename_match": "YES", "metadata_match": "YES", "director_script_match": "YES", "visually_verified": True},
        "observed": ["防守持刀格斗"], "inferred": ["切断胸口宝石视线"], "proposed": ["归入淘汰库"], "do_not_copy": ["横刀胸前格斗"]
    },
    {
        "id": "REJECT_POSE_0801_low_angle_ground_scythe_stance",
        "file": "refs/90_REJECTED/REJECT_POSE_0801_low_angle_ground_scythe_stance.webp",
        "category": "90_REJECTED",
        "priority": "REJECT",
        "source": {"url": "https://www.xiaohongshu.com/explore/6a1005000000000019013c78", "page_title": "低视角拍摄合集❤", "author": "果果酱啦啦啦", "platform": "小红书", "source_type": "EXPO_FIELD_PHOTO", "verified": True},
        "target_relevance": 0.50, "aesthetic_value": 0.85, "technical_value": 0.85, "source_confidence": 0.95, "production_cost": "LOW", "expo_feasibility": "C",
        "reference_roles": ["REJECTED_MARTIAL_SCYTHE"],
        "director_script": "淘汰原因：贴地大弓步持死神镰刀为 Boss 战压迫式攻击姿势，严重偏离长夜焕生柔和神性，被优雅借柱拉伸仰拍取代。",
        "model_setup": "N/A", "camera_position": "N/A", "recommended_lens": "50mm f/1.8", "crop": "full body",
        "image_quality": {"width": 1080, "height": 1620, "source_quality": "HQ_DOWNLOAD", "quality_pass": True},
        "visual_audit": {"actual_pose": "漫展内贴地极低机位仰拍，双腿分开大步站稳双手斜持长柄镰刀后置（淘汰：死神镰刀攻击性过烈）", "filename_match": "YES", "metadata_match": "YES", "director_script_match": "YES", "visually_verified": True},
        "observed": ["大跨度镰刀战斗姿势"], "inferred": ["缺乏女性柔美神圣感"], "proposed": ["归入淘汰库"], "do_not_copy": ["大弓步死神持镰"]
    }
]

for r in rejected_moved:
    refs_by_id[r["id"]] = r

# Reconstruct list
new_refs_list = list(refs_by_id.values())

with open(YAML_PATH, "w", encoding="utf-8") as f:
    yaml.dump(new_refs_list, f, allow_unicode=True, sort_keys=False, width=120)

print(f"Successfully rebuilt references.yaml with {len(new_refs_list)} entries.")
