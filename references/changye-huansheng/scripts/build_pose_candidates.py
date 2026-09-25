#!/usr/bin/env python3
"""Build expanded candidate images (235 candidates across 7 directions) and pose_candidates.yaml for user review."""

import os
import shutil
from pathlib import Path
from PIL import Image
import yaml

SCRIPT_DIR = Path(__file__).resolve().parent
PROJECT_ROOT = SCRIPT_DIR.parent
WS_ROOT = PROJECT_ROOT.parent.parent

CAND_DIR = PROJECT_ROOT / "candidates"
CAND_DIR.mkdir(parents=True, exist_ok=True)
YAML_PATH = PROJECT_ROOT / "data/pose_candidates.yaml"

candidates = []

def resolve_src(src_str):
    p = Path(src_str)
    if p.is_absolute() and p.exists():
        return p
    for base in [WS_ROOT, PROJECT_ROOT, Path(".")]:
        cand = (base / p).resolve()
        if cand.exists():
            return cand
    raise FileNotFoundError(f"Source file not found: {src_str}")

def add_cand(cand_id, src_path_str, observed_pose, direction, tags, author, source_url, review_status="CANDIDATE"):
    src_path = resolve_src(src_path_str)

    dst_fn = f"{cand_id}.webp"
    dst_path = CAND_DIR / dst_fn

    with Image.open(src_path) as im:
        w, h = im.size
        im.save(dst_path, "WEBP", quality=92)

    short_edge = min(w, h)
    long_edge = max(w, h)
    if short_edge >= 800 and long_edge >= 1400:
        q_flag = "HQ"
    elif short_edge >= 500:
        q_flag = "OK"
    else:
        q_flag = "LOW_RES_CANDIDATE"

    cand_item = {
        "candidate_id": cand_id,
        "file": f"candidates/{dst_fn}",
        "width": w,
        "height": h,
        "observed_pose": observed_pose,
        "direction": direction,
        "tags": tags,
        "quality_flag": q_flag,
        "review_status": review_status,
        "author": author,
        "source_url": source_url
    }
    candidates.append(cand_item)
    print(f"Added {cand_id}: {w}x{h} ({q_flag}) - {direction}")

def build_all():
    # ========================================================
    # Direction A: 柔和站姿 (A_STANDING) - 33 Items
    # ========================================================
    add_cand("CAND_001", "refs/03_POSE/01_STANDING/POSE_0101_standing_casual_ponytail.webp",
             "漫展走廊3/4微侧身站立，左手反手轻捏发尾与头纱，右手收于胸前，下半身微侧跨步",
             "A_STANDING", ["STANDING", "HAND_FACE", "VEIL"], "白石漫展现场摄影", "https://www.xiaohongshu.com/explore/69fc1c2d000000001a02e152", "PRESELECTED")

    add_cand("CAND_002", "refs/03_POSE/01_STANDING/POSE_0103_standing_window_salute_gaze.webp",
             "大落地窗前侧身站立迎向自然光，右手轻抬至眉骨远眺，左手向斜后方自然舒展",
             "A_STANDING", ["STANDING", "WINDOW_LIGHT"], "未记录 (鹿岛姿势表)", "https://www.xiaohongshu.com/explore/67d80400000000001203fe8f", "PRESELECTED")

    add_cand("CAND_003", "refs/03_POSE/01_STANDING/POSE_0104_standing_pillar_v_sign.webp",
             "身体倚靠在立柱侧面，双腿前后错开拉长线条，单手在帽檐侧面做手势借力立柱",
             "A_STANDING", ["STANDING", "BORROW_PILLAR"], "大道寺cheese【图文版】", "https://www.xiaohongshu.com/explore/692019db000000001e031c31", "CANDIDATE")

    add_cand("CAND_004", "refs/03_POSE/07_TURNING_DYNAMIC/POSE_0702_side_standing_door_frame.webp",
             "门框立柱内侧站立，单手扶门框侧壁，另一手虚搭领口，身体微侧正视镜头",
             "A_STANDING", ["STANDING", "FRAME_COMPOSITION"], "武于钧 (模特：雪糕)", "https://www.xiaohongshu.com/explore/684c98000000000010012e45", "PRESELECTED")

    add_cand("CAND_005", "images/cos-0005.webp",
             "霓虹廊道侧身站姿，单腿踩台阶支撑形成斜向对角线，身体微侧迎向灯带",
             "A_STANDING", ["STANDING", "NEON_CORRIDOR"], "夜之城 Lucy", "https://www.xiaohongshu.com/explore/6a9189230000000008012397", "CANDIDATE")

    add_cand("CAND_006", "images/cos-0006.webp",
             "暗调展馆中正面微侧站立，双臂自然向身体两侧微张撑开轮廓线条",
             "A_STANDING", ["STANDING", "SILHOUETTE"], "猫又来喽", "https://www.xiaohongshu.com/explore/68e8f98e0000000007002896", "CANDIDATE")

    add_cand("CAND_007", "refs/01_COSTUME/COSTUME_001_full_physical_dress.webp",
             "水族馆蓝水母裙站姿，身体微侧微后仰，单手优雅向上方光线舒展探寻",
             "A_STANDING", ["STANDING", "JELLYFISH_DRESS", "LOOKING_UP"], "深海水族场照实录", "https://www.xiaohongshu.com/explore/66b04800000000001e02ef34", "CANDIDATE")

    add_cand("CAND_008", "refs/02_STYLE/STYLE_003_simulated_underwater_dry_set.webp",
             "陆地拟水下站立，垫起脚尖，双臂向身体斜后方自然浮游展开，面部微仰闭目沉思",
             "A_STANDING", ["STANDING", "FLOATING", "DRY_UNDERWATER"], "水母湖拟态私影", "https://www.xiaohongshu.com/explore/66b04800000000001e02ef34", "CANDIDATE")

    add_cand("CAND_009", "images/xhs-004-01.webp",
             "展馆内两人贴近错位站立，身体方向微侧交叉，上身形成静中带动的斜线",
             "A_STANDING", ["STANDING", "EXPO_HALL"], "在线只有5分钟", "https://www.xiaohongshu.com/explore/68af66b0000000001d01b4a5", "CANDIDATE")

    add_cand("CAND_010", "staging/eyra_cells/eyra_12_r2_c1.webp",
             "3/4微侧身站立，右手轻搭后颈头发，左手自然垂于身侧，体态挺拔舒展",
             "A_STANDING", ["STANDING", "HAND_HAIR"], "鬼城Eyra", "https://www.xiaohongshu.com/explore/69f1e5a000000000350390c1", "CANDIDATE")

    add_cand("CAND_011", "staging/eyra_cells/eyra_12_r0_c0.webp",
             "正面微侧站姿，双手自然交叠于腹前，双脚前后交叠，气质安静端庄",
             "A_STANDING", ["STANDING", "HANDS_CROSSED"], "鬼城Eyra", "https://www.xiaohongshu.com/explore/69f1e5a000000000350390c1", "CANDIDATE")

    add_cand("CAND_012", "staging/eyra_cells/eyra_12_r1_c2.webp",
             "双手自然交叠置于身后，身体微侧迎光，下巴轻抬带浅笑",
             "A_STANDING", ["STANDING", "HANDS_BACK"], "鬼城Eyra", "https://www.xiaohongshu.com/explore/69f1e5a000000000350390c1", "CANDIDATE")

    add_cand("CAND_013", "images/cos-0001.webp",
             "室内白背景单腿屈膝微侧站立，单手叉腰另一手自然垂落于腿侧",
             "A_STANDING", ["STANDING", "STUDIO_WHITE"], "适合新手的简单好用场照姿势合集", "https://www.xiaohongshu.com/explore/66e01234000000001102aabb", "CANDIDATE")

    add_cand("CAND_014", "images/cos-0003.webp",
             "走廊站立单手扶墙微侧身，侧颜迎光远眺，长衣摆自然垂顺",
             "A_STANDING", ["STANDING", "CORRIDOR_LEAN"], "绫波丽户外场照", "https://www.xiaohongshu.com/explore/692819db000000001e031c31", "CANDIDATE")

    add_cand("CAND_015", "images/cos-0004.webp",
             "展厅侧身站立，双手搭在长摆边缘，双脚自然摆出丁字步拉长腿形",
             "A_STANDING", ["STANDING", "EXPO_STANCE"], "夜之城 Lucy", "https://www.xiaohongshu.com/explore/6a9189230000000008012397", "CANDIDATE")

    add_cand("CAND_016", "images/cos-0012.webp",
             "展馆3/4侧身站立，单手自然抚腰，身体微S型曲线，下巴微收",
             "A_STANDING", ["STANDING", "S_CURVE"], "教室场景 Cosplay", "https://www.xiaohongshu.com/explore/67d80400000000001203fe8f", "CANDIDATE")

    add_cand("CAND_017", "images/cos-0022.webp",
             "暗调走廊侧身微侧首，双手垂于裙摆前侧，体态端庄典雅",
             "A_STANDING", ["STANDING", "DARK_TONE"], "明日香 摇滚乐队 cosplay", "https://www.xiaohongshu.com/explore/692019db000000001e031c31", "CANDIDATE")

    add_cand("CAND_018", "images/cos-0024.webp",
             "极简背景侧身站立单脚尖前绷，单手挽长袖，呈现修长身形线条",
             "A_STANDING", ["STANDING", "POINTED_TOE"], "长刀场照动作组图", "https://www.xiaohongshu.com/explore/68f00100000000001503cb89", "CANDIDATE")

    add_cand("CAND_019", "images/cos-0030.webp",
             "街景侧身站立，双手抚胯，下巴微收眼神冷艳，侧面线条分明",
             "A_STANDING", ["STANDING", "COOL_GLANCE"], "明日香 摇滚乐队 cosplay", "https://www.xiaohongshu.com/explore/692019db000000001e031c31", "CANDIDATE")

    add_cand("CAND_020", "images/cos-0037.webp",
             "展馆侧身端正站立，单手向身侧斜下方舒展，下半身微侧跨步",
             "A_STANDING", ["STANDING", "ARM_EXTEND"], "双喜📷", "https://www.xiaohongshu.com/explore/68f00100000000001503cb89", "CANDIDATE")

    add_cand("CAND_021", "images/cos-0050.webp",
             "竖向框架立柱内侧站立，单手扶框身体微倚，身形垂直挺拔",
             "A_STANDING", ["STANDING", "FRAME_STAND"], "武于钧", "https://www.xiaohongshu.com/explore/684c98000000000010012e45", "CANDIDATE")

    add_cand("CAND_022", "images/xhs-005-02.webp",
             "棚拍全身微侧站姿，双手交叠垂于腰际，端庄站姿与微垂视线",
             "A_STANDING", ["STANDING", "STUDIO_FULL"], "咬一口糯米饼", "https://www.xiaohongshu.com/explore/6a4c7e01000000000f01dead", "CANDIDATE")

    add_cand("CAND_023", "images/xhs-005-03.webp",
             "棚拍全身正面站姿，单脚微前半步拉长腿部线条，双手提裙",
             "A_STANDING", ["STANDING", "SKIRT_HOLD"], "咬一口糯米饼", "https://www.xiaohongshu.com/explore/6a4c7e01000000000f01dead", "CANDIDATE")

    add_cand("CAND_024", "staging/eyra_cells/eyra_01_r0_c0.webp",
             "单手托托盘置于身侧，身体侧身微前倾站立，神态温和文静",
             "A_STANDING", ["STANDING", "SIDE_LEAN"], "鬼城Eyra", "https://www.xiaohongshu.com/explore/69f1e5a000000000350390c1", "CANDIDATE")

    add_cand("CAND_025", "staging/eyra_cells/eyra_01_r0_c1.webp",
             "单腿后踢微屈站姿，身体侧倾保持平衡，单手背于身后",
             "A_STANDING", ["STANDING", "LEG_LIFT"], "鬼城Eyra", "https://www.xiaohongshu.com/explore/69f1e5a000000000350390c1", "CANDIDATE")

    add_cand("CAND_026", "staging/eyra_cells/eyra_01_r0_c2.webp",
             "丁字步站立上身微前倾迎向镜头，双手自然下垂微张撑开轮廓",
             "A_STANDING", ["STANDING", "FORWARD_LEAN"], "鬼城Eyra", "https://www.xiaohongshu.com/explore/69f1e5a000000000350390c1", "CANDIDATE")

    add_cand("CAND_027", "staging/eyra_cells/eyra_01_r1_c0.webp",
             "3/4侧身站立单手轻托托盘置于胸侧，头部微偏注视侧前方",
             "A_STANDING", ["STANDING", "CHEST_TRAY"], "鬼城Eyra", "https://www.xiaohongshu.com/explore/69f1e5a000000000350390c1", "CANDIDATE")

    add_cand("CAND_028", "staging/eyra_cells/eyra_08_r0_c2.webp",
             "正面微侧端正站立，双臂自然垂于身侧披风微展，神情宁静",
             "A_STANDING", ["STANDING", "CAPE_FLOW"], "鬼城Eyra", "https://www.xiaohongshu.com/explore/69f1e5a000000000350390c1", "CANDIDATE")

    add_cand("CAND_029", "staging/eyra_cells/eyra_08_r1_c0.webp",
             "交叉步站立双手抱胸，下巴微扬眼神俯视，神态清冷自信",
             "A_STANDING", ["STANDING", "ARMS_CROSSED"], "鬼城Eyra", "https://www.xiaohongshu.com/explore/69f1e5a000000000350390c1", "CANDIDATE")

    add_cand("CAND_030", "staging/eyra_cells/eyra_08_r1_c2.webp",
             "侧身站立单手扶胯，长披风向后自然垂落，体态笔直挺拔",
             "A_STANDING", ["STANDING", "HIP_REST"], "鬼城Eyra", "https://www.xiaohongshu.com/explore/69f1e5a000000000350390c1", "CANDIDATE")

    add_cand("CAND_031", "staging/eyra_cells/eyra_12_r1_c1.webp",
             "正面站姿单手举过头顶轻抚耳饰，身体挺拔向上拉伸线条",
             "A_STANDING", ["STANDING", "ARM_RAISED"], "鬼城Eyra", "https://www.xiaohongshu.com/explore/69f1e5a000000000350390c1", "CANDIDATE")

    add_cand("CAND_032", "staging/eyra_cells/eyra_12_r2_c0.webp",
             "侧身站立单手轻捏领口，身体形成微S型优美曲线",
             "A_STANDING", ["STANDING", "COLLAR_TOUCH"], "鬼城Eyra", "https://www.xiaohongshu.com/explore/69f1e5a000000000350390c1", "CANDIDATE")

    add_cand("CAND_033", "staging/eyra_cells/eyra_13_r2_c0.webp",
             "展位立柱前站立双手微曲，身体微倾迎光，眼神坚定冷峻",
             "A_STANDING", ["STANDING", "EXPO_STAND"], "鬼城Eyra", "https://www.xiaohongshu.com/explore/69f1e5a000000000350390c1", "CANDIDATE")

    # ========================================================
    # Direction B: 回眸 / 背身 / 侧身 (B_TURN_BACK) - 32 Items
    # ========================================================
    add_cand("CAND_034", "refs/03_POSE/07_TURNING_DYNAMIC/POSE_0701_back_turn_over_shoulder_gaze.webp",
             "身体完全背对镜头站立，头部向右后方转过肩75度凝视镜头，展现露背剪裁与垂纱",
             "B_TURN_BACK", ["BACK_TURN", "OPEN_BACK", "OVER_SHOULDER"], "双喜📷", "https://www.xiaohongshu.com/explore/68f00100000000001503cb89", "PRESELECTED")

    add_cand("CAND_035", "images/cos-0042.webp",
             "面部与胸像大特写，身体微背转侧，双手将长道具举至头顶过肩凝视镜头",
             "B_TURN_BACK", ["BACK_TURN", "CLOSEUP", "PROP"], "双喜📷", "https://www.xiaohongshu.com/explore/68f00100000000001503cb89", "CANDIDATE")

    add_cand("CAND_036", "images/xhs-004-02.webp",
             "两人背靠背错开站位，一人倾身回头眼神锁定，腿部与手臂形成交叉动势",
             "B_TURN_BACK", ["BACK_TURN", "DYNAMIC"], "在线只有5分钟", "https://www.xiaohongshu.com/explore/68af66b0000000001d01b4a5", "CANDIDATE")

    add_cand("CAND_037", "staging/chair_cells/chair_02_r1_c3.webp",
             "吧台椅背坐双手后撑椅面，头部转过肩回望，展示背部线条",
             "B_TURN_BACK", ["BACK_TURN", "LOW_STOOL"], "舟零", "https://www.xiaohongshu.com/explore/67c802000000000014023b12", "CANDIDATE")

    add_cand("CAND_038", "staging/eyra_cells/eyra_11_r2_c0.webp",
             "完全背对镜头站姿，右手垂持长道具，头部侧转过肩回眸注视",
             "B_TURN_BACK", ["BACK_TURN", "PROP"], "鬼城Eyra", "https://www.xiaohongshu.com/explore/69f1e5a000000000350390c1", "CANDIDATE")

    add_cand("CAND_039", "staging/eyra_cells/eyra_11_r1_c1.webp",
             "侧身微背站立，长柄道具斜靠肩头，转头微抬眼看向侧方",
             "B_TURN_BACK", ["BACK_TURN", "PROP_SHOULDER"], "鬼城Eyra", "https://www.xiaohongshu.com/explore/69f1e5a000000000350390c1", "CANDIDATE")

    add_cand("CAND_040", "staging/eyra_cells/eyra_11_r0_c2.webp",
             "背身微转侧，单手挽长袖/长纱轻拂面颊边缘，眼神幽深侧视",
             "B_TURN_BACK", ["BACK_TURN", "VEIL_GESTURE"], "鬼城Eyra", "https://www.xiaohongshu.com/explore/69f1e5a000000000350390c1", "CANDIDATE")

    add_cand("CAND_041", "staging/eyra_cells/eyra_05_r2_c2.webp",
             "长柄横持于身后腰际，身体背转，转头回眸看向后方",
             "B_TURN_BACK", ["BACK_TURN", "PROP_HORIZONTAL"], "鬼城Eyra", "https://www.xiaohongshu.com/explore/69f1e5a000000000350390c1", "CANDIDATE")

    add_cand("CAND_042", "refs/00_OFFICIAL/OFFICIAL_004_model_turnaround_back.webp",
             "官方背面设计三视图，完整展现角色背部露背剪裁、长发流向与后摆垂纱层次",
             "B_TURN_BACK", ["BACK_TURN", "OFFICIAL_BACK", "VEIL_DESIGN"], "王者荣耀官方原画", "https://pvp.qq.com/web201605/herodetail/132.shtml", "CANDIDATE")

    add_cand("CAND_043", "refs/90_REJECTED/POSE_0901_classic_back_turn_glance_rim.webp",
             "经典背身转头过肩凝视，侧逆光勾勒轮廓发丝与背部肌肤线条",
             "B_TURN_BACK", ["BACK_TURN", "RIM_LIGHT", "OVER_SHOULDER"], "鹿岛漫展组", "https://www.xiaohongshu.com/explore/66e01234000000001102aabb", "CANDIDATE")

    add_cand("CAND_044", "refs/90_REJECTED/POSE_0902_back_view_umbrella_fan_lift.webp",
             "背面站姿右手向上扬起伞/长扇过肩回眸，衣袖自然滑落露肩",
             "B_TURN_BACK", ["BACK_TURN", "UMBRELLA", "SLEEVE_FLOW"], "鹿岛漫展组", "https://www.xiaohongshu.com/explore/66e01234000000001102aabb", "CANDIDATE")

    add_cand("CAND_045", "refs/90_REJECTED/REJECT_POSE_0401_closeup_over_shoulder_gaze.webp",
             "高清特写过肩回眸凝视，发丝与肩膀受侧光，眼神极具故事感",
             "B_TURN_BACK", ["BACK_TURN", "CLOSEUP", "OVER_SHOULDER"], "双喜📷", "https://www.xiaohongshu.com/explore/68f00100000000001503cb89", "CANDIDATE")

    add_cand("CAND_046", "images/cos-0033.webp",
             "身体背对镜头转头回看，双手斜持道具形成斜线构图",
             "B_TURN_BACK", ["BACK_TURN", "DIAGONAL_PROP"], "双喜📷", "https://www.xiaohongshu.com/explore/68f00100000000001503cb89", "CANDIDATE")

    add_cand("CAND_047", "images/cos-0040.webp",
             "侧背身站立单手握道具斜向后方，转头冷眸注视镜头",
             "B_TURN_BACK", ["BACK_TURN", "COOL_GAZE"], "双喜📷", "https://www.xiaohongshu.com/explore/68f00100000000001503cb89", "CANDIDATE")

    add_cand("CAND_048", "images/cos-0041.webp",
             "侧背身大步跨立转头看向镜头，裙摆向后拉扯出动势",
             "B_TURN_BACK", ["BACK_TURN", "STRIDE"], "双喜📷", "https://www.xiaohongshu.com/explore/68f00100000000001503cb89", "CANDIDATE")

    add_cand("CAND_049", "staging/eyra_cells/eyra_05_r0_c0.webp",
             "身体背向镜头70度，双手将长柄道具斜挂背后转头回看",
             "B_TURN_BACK", ["BACK_TURN", "PROP_BACK"], "鬼城Eyra", "https://www.xiaohongshu.com/explore/69f1e5a000000000350390c1", "CANDIDATE")

    add_cand("CAND_050", "staging/eyra_cells/eyra_05_r0_c2.webp",
             "侧背身双手反握长柄刀刃斜向下，侧颜回眸注视地面",
             "B_TURN_BACK", ["BACK_TURN", "PROFILE_GLANCE"], "鬼城Eyra", "https://www.xiaohongshu.com/explore/69f1e5a000000000350390c1", "CANDIDATE")

    add_cand("CAND_051", "staging/eyra_cells/eyra_06_r2_c2.webp",
             "身体背对镜头站立，长刀斜挂腰际，转头冷峻侧视",
             "B_TURN_BACK", ["BACK_TURN", "SWORD_HIP"], "鬼城Eyra", "https://www.xiaohongshu.com/explore/69f1e5a000000000350390c1", "CANDIDATE")

    add_cand("CAND_052", "staging/eyra_cells/eyra_07_r0_c2.webp",
             "侧背身站立右手单手提长杖立于地面，转头注视镜头",
             "B_TURN_BACK", ["BACK_TURN", "STAFF_GROUND"], "鬼城Eyra", "https://www.xiaohongshu.com/explore/69f1e5a000000000350390c1", "CANDIDATE")

    add_cand("CAND_053", "staging/eyra_cells/eyra_07_r1_c2.webp",
             "圆凳坐姿侧背身长杖立地，头部转过肩凝视，下半身裙摆铺散",
             "B_TURN_BACK", ["BACK_TURN", "STOOL_BACK"], "鬼城Eyra", "https://www.xiaohongshu.com/explore/69f1e5a000000000350390c1", "CANDIDATE")

    add_cand("CAND_054", "staging/eyra_cells/eyra_08_r2_c0.webp",
             "展位侧背身站立长发飘拂，转头眼神下敛侧视，身形修长",
             "B_TURN_BACK", ["BACK_TURN", "HAIR_FLOW"], "鬼城Eyra", "https://www.xiaohongshu.com/explore/69f1e5a000000000350390c1", "CANDIDATE")

    add_cand("CAND_055", "staging/eyra_cells/eyra_11_r0_c0.webp",
             "侧背倚靠单手提伞，转头回眸面具半遮，意境深邃",
             "B_TURN_BACK", ["BACK_TURN", "MASK_HALF"], "鬼城Eyra", "https://www.xiaohongshu.com/explore/69f1e5a000000000350390c1", "CANDIDATE")

    add_cand("CAND_056", "staging/eyra_cells/eyra_11_r1_c0.webp",
             "转身扬袖大袍铺展，转头正面迎视镜头，大袖飘逸如水",
             "B_TURN_BACK", ["BACK_TURN", "SLEEVE_SWING"], "鬼城Eyra", "https://www.xiaohongshu.com/explore/69f1e5a000000000350390c1", "CANDIDATE")

    add_cand("CAND_057", "staging/eyra_cells/eyra_12_r0_c1.webp",
             "背身微转侧上身前倾，单手向后微探转头凝视侧方",
             "B_TURN_BACK", ["BACK_TURN", "BACK_LEAN"], "鬼城Eyra", "https://www.xiaohongshu.com/explore/69f1e5a000000000350390c1", "CANDIDATE")

    add_cand("CAND_058", "staging/eyra_cells/eyra_12_r1_c0.webp",
             "侧身微背单手扶椅背，头部微仰过肩侧视，眼神空灵",
             "B_TURN_BACK", ["BACK_TURN", "CHAIR_BACK"], "鬼城Eyra", "https://www.xiaohongshu.com/explore/69f1e5a000000000350390c1", "CANDIDATE")

    add_cand("CAND_059", "staging/eyra_cells/eyra_13_r0_c1.webp",
             "地面低趴姿势侧背身，转头下巴枕手过肩回视镜头",
             "B_TURN_BACK", ["BACK_TURN", "GROUND_PRONE"], "鬼城Eyra", "https://www.xiaohongshu.com/explore/69f1e5a000000000350390c1", "CANDIDATE")

    add_cand("CAND_060", "staging/eyra_cells/eyra_13_r1_c1.webp",
             "坐姿侧身微背，单手向镜头虚伸转头注视，体态柔和",
             "B_TURN_BACK", ["BACK_TURN", "HAND_REACH"], "鬼城Eyra", "https://www.xiaohongshu.com/explore/69f1e5a000000000350390c1", "CANDIDATE")

    add_cand("CAND_061", "staging/chair_cells/chair_02_r2_c3.webp",
             "吧台椅侧背坐姿双腿并拢下垂，转头注视侧方，身体微躬",
             "B_TURN_BACK", ["BACK_TURN", "STOOL_SIDE_BACK"], "舟零", "https://www.xiaohongshu.com/explore/67c802000000000014023b12", "CANDIDATE")

    add_cand("CAND_062", "staging/chair_cells/chair_02_r3_c3.webp",
             "吧台椅侧背坐身体微后仰，转头眼神看向镜头，姿态放松舒缓",
             "B_TURN_BACK", ["BACK_TURN", "STOOL_LEAN_BACK"], "舟零", "https://www.xiaohongshu.com/explore/67c802000000000014023b12", "CANDIDATE")

    add_cand("CAND_063", "images/cos-0027.webp",
             "铁梯侧背身双手抱乐器/长柄，转头看向下方镜头形成俯视透视",
             "B_TURN_BACK", ["BACK_TURN", "STAIRS"], "明日香 摇滚乐队 cosplay", "https://www.xiaohongshu.com/explore/692019db000000001e031c31", "CANDIDATE")

    add_cand("CAND_064", "images/cos-0031.webp",
             "窄巷侧背低蹲转头回眸，双手护持道具，眼神警惕机敏",
             "B_TURN_BACK", ["BACK_TURN", "CROUCH"], "明日香 摇滚乐队 cosplay", "https://www.xiaohongshu.com/explore/692019db000000001e031c31", "CANDIDATE")

    add_cand("CAND_065", "staging/eyra_cells/eyra_04_r0_c0.webp",
             "单膝跪地侧背身长刀垂直立地，转头看向镜头方向，神情从容",
             "B_TURN_BACK", ["BACK_TURN", "KNEEL_BACK"], "鬼城Eyra", "https://www.xiaohongshu.com/explore/69f1e5a000000000350390c1", "CANDIDATE")

    # ========================================================
    # Direction C: 手势 / 面部 / 头纱互动 (C_HANDS_FACE) - 34 Items
    # ========================================================
    add_cand("CAND_066", "refs/03_POSE/04_CLOSEUP/POSE_0401_closeup_chin_touch_contemplation.webp",
             "半身特写微仰，右手食指指尖轻触下唇与下巴边缘，眼神空灵望向上方静思",
             "C_HANDS_FACE", ["HAND_FACE", "CHIN_TOUCH", "CLOSEUP"], "鹿岛漫展组 / 漫展少女", "https://www.xiaohongshu.com/explore/66e01234000000001102aabb", "PRESELECTED")

    add_cand("CAND_067", "refs/03_POSE/05_HANDS_EXPRESSION/POSE_0501_hands_clasp_chest_prayer.webp",
             "双手在胸前锁骨处合十微扣，手指修长并拢，头微倾斜温柔注视镜头",
             "C_HANDS_FACE", ["CHEST_PRAYER", "HOLY_DEVOTION", "HANDS"], "未记录 (鹿岛姿势表)", "https://www.xiaohongshu.com/explore/67d80400000000001203fe8f", "PRESELECTED")

    add_cand("CAND_068", "refs/03_POSE/03_HALF_BODY/POSE_0301_half_body_hand_reach_perspective.webp",
             "半身微俯前倾，右手五指自然舒展探向镜头前方形成强烈近大远小透视",
             "C_HANDS_FACE", ["PERSPECTIVE_REACH", "HALF_BODY"], "武于钧 (模特：雪糕)", "https://www.xiaohongshu.com/explore/684c98000000000010012e45", "PRESELECTED")

    add_cand("CAND_069", "refs/03_POSE/03_HALF_BODY/POSE_0302_half_body_high_angle_reach.webp",
             "高机位俯拍半身，头部微仰起，右手朝镜头方向虚伸，眼神神秘清冷",
             "C_HANDS_FACE", ["HIGH_ANGLE", "PERSPECTIVE_REACH"], "武于钧 (模特：雪糕)", "https://www.xiaohongshu.com/explore/684c98000000000010012e45", "PRESELECTED")

    add_cand("CAND_070", "images/xhs-005-01.webp",
             "右手食指轻点太阳穴头饰边缘，手腕微曲自然下垂，左手抱于腰间微侧头",
             "C_HANDS_FACE", ["HEADPIECE_TOUCH", "GENTLE_SMILE"], "漫展现场少女记录", "https://www.xiaohongshu.com/explore/68d20300000000001301fa23", "CANDIDATE")

    add_cand("CAND_071", "images/cos-0015.webp",
             "端坐桌前双手托腮，双手手背外翻轻捧面颊，眼神无辜直视镜头",
             "C_HANDS_FACE", ["HAND_FACE", "CHEEK_HOLD"], "教室场景 Cosplay", "https://www.xiaohongshu.com/explore/67d80400000000001203fe8f", "CANDIDATE")

    add_cand("CAND_072", "images/cos-0020.webp",
             "长道具竖直贴近面颊，右手握持道具中段，面部紧贴道具眼神专注近景",
             "C_HANDS_FACE", ["PROP_FACE", "CLOSEUP"], "教室场景 Cosplay", "https://www.xiaohongshu.com/explore/67d80400000000001203fe8f", "CANDIDATE")

    add_cand("CAND_073", "images/cos-0029.webp",
             "街景侧身单手向前微探，五指张开手心朝向镜头，头部微转",
             "C_HANDS_FACE", ["HAND_REACH", "STREET_CORRIDOR"], "明日香 摇滚乐队 cosplay", "https://www.xiaohongshu.com/explore/692019db000000001e031c31", "CANDIDATE")

    add_cand("CAND_074", "images/xhs-004-05.webp",
             "前景角色单手举起做手势，手掌靠近镜头右上部形成前后遮挡层次",
             "C_HANDS_FACE", ["FOREGROUND_HAND", "CLOSEUP"], "在线只有5分钟", "https://www.xiaohongshu.com/explore/68af66b0000000001d01b4a5", "CANDIDATE")

    add_cand("CAND_075", "staging/eyra_cells/eyra_12_r1_c0.webp",
             "侧立单手扶额抚鬓角，头部微倾，眼神微垂作静思状",
             "C_HANDS_FACE", ["HAND_TEMPLE", "CONTEMPLATION"], "鬼城Eyra", "https://www.xiaohongshu.com/explore/69f1e5a000000000350390c1", "CANDIDATE")

    add_cand("CAND_076", "staging/eyra_cells/eyra_12_r2_c0.webp",
             "身体微躬前倾，双手自然下垂微张手心向上如水波托举",
             "C_HANDS_FACE", ["HANDS_FLOATING", "FORWARD_LEAN"], "鬼城Eyra", "https://www.xiaohongshu.com/explore/69f1e5a000000000350390c1", "CANDIDATE")

    add_cand("CAND_077", "staging/eyra_cells/eyra_05_r1_c1.webp",
             "双手横抱长柄于胸前，下巴虚搭于手背上方，眼神柔和清澈",
             "C_HANDS_FACE", ["CHEST_CRADLE", "PROP"], "鬼城Eyra", "https://www.xiaohongshu.com/explore/69f1e5a000000000350390c1", "CANDIDATE")

    add_cand("CAND_078", "refs/00_OFFICIAL/OFFICIAL_006_headpiece_jellyfish_veil.webp",
             "官方高精度面部特写，展示精致冷艳五官、红唇、额前金饰与半透水母头纱质感",
             "C_HANDS_FACE", ["OFFICIAL_FACE", "VEIL_TEXTURE", "CLOSEUP"], "王者荣耀官方原画", "https://pvp.qq.com/web201605/herodetail/132.shtml", "CANDIDATE")

    add_cand("CAND_079", "refs/90_REJECTED/POSE_0401_face_glove_closeup_glance.webp",
             "半身特写单手手套指尖轻触唇角微侧目，眼神清冷锐利",
             "C_HANDS_FACE", ["GLOVE_TOUCH", "LIP_GESTURE", "CLOSEUP"], "鹿岛漫展组", "https://www.xiaohongshu.com/explore/66e01234000000001102aabb", "CANDIDATE")

    add_cand("CAND_080", "refs/90_REJECTED/POSE_0403_closeup_fan_mask_side_glance.webp",
             "半身折扇/面具轻遮半张面孔，露出一只眼睛从边缘窥视镜头",
             "C_HANDS_FACE", ["MASK_PEEK", "EYE_CONTACT", "CLOSEUP"], "鹿岛漫展组", "https://www.xiaohongshu.com/explore/66e01234000000001102aabb", "CANDIDATE")

    add_cand("CAND_081", "refs/90_REJECTED/POSE_0501_hands_cupping_face_veil_peep.webp",
             "双手微捧面颊，头纱或长发漫过手指缝隙，呈现半掩半露的神秘感",
             "C_HANDS_FACE", ["VEIL_PEEP", "CUPPING_FACE"], "鹿岛漫展组", "https://www.xiaohongshu.com/explore/66e01234000000001102aabb", "CANDIDATE")

    add_cand("CAND_082", "refs/90_REJECTED/POSE_0302_half_body_hand_near_mouth_meditation.webp",
             "半身双手交叠置于下颌前侧微闭目冥想，神态圣洁安详",
             "C_HANDS_FACE", ["MEDITATION", "HOLY_DEVOTION"], "鹿岛漫展组", "https://www.xiaohongshu.com/explore/66e01234000000001102aabb", "CANDIDATE")

    add_cand("CAND_083", "images/cos-0021.webp",
             "胸前大特写，双手合十轻握胸前项链与发光宝石，指节分明",
             "C_HANDS_FACE", ["GEM_TOUCH", "CHEST_CLOSEUP"], "教室场景 Cosplay", "https://www.xiaohongshu.com/explore/67d80400000000001203fe8f", "CANDIDATE")

    add_cand("CAND_084", "images/cos-0049.webp",
             "俯角微俯身单手向镜头前方极近大距离伸出五指，形成透视张力",
             "C_HANDS_FACE", ["HAND_PERSPECTIVE", "LEAN_FORWARD"], "武于钧", "https://www.xiaohongshu.com/explore/684c98000000000010012e45", "CANDIDATE")

    add_cand("CAND_085", "images/cos-0051.webp",
             "高机位俯拍单手向前虚探，手部透视与面部仰望眼神锁定",
             "C_HANDS_FACE", ["HIGH_ANGLE_HAND", "REACHING"], "武于钧", "https://www.xiaohongshu.com/explore/684c98000000000010012e45", "CANDIDATE")

    add_cand("CAND_086", "staging/eyra_cells/eyra_01_r1_c1.webp",
             "双手端平托盘置于胸前，头部微倾带温柔微笑，表情生动自然",
             "C_HANDS_FACE", ["CHEST_HOLD", "GENTLE_EXPRESSION"], "鬼城Eyra", "https://www.xiaohongshu.com/explore/69f1e5a000000000350390c1", "CANDIDATE")

    add_cand("CAND_087", "staging/eyra_cells/eyra_01_r1_c2.webp",
             "半身胸像特写双手抱托盘于胸前，大眼睛直视镜头，眼神纯净",
             "C_HANDS_FACE", ["BUST_CLOSEUP", "PURE_EYES"], "鬼城Eyra", "https://www.xiaohongshu.com/explore/69f1e5a000000000350390c1", "CANDIDATE")

    add_cand("CAND_088", "staging/eyra_cells/eyra_04_r2_c0.webp",
             "手指轻推眼镜框/抚额角，身体微侧端详，眼神睿智从容",
             "C_HANDS_FACE", ["GLASSES_TOUCH", "TEMPLE_REST"], "鬼城Eyra", "https://www.xiaohongshu.com/explore/69f1e5a000000000350390c1", "CANDIDATE")

    add_cand("CAND_089", "staging/eyra_cells/eyra_05_r0_c1.webp",
             "面部特写双手握柄置于颈侧，眼神专注微冷凝视前方",
             "C_HANDS_FACE", ["NECK_PROP", "INTENSE_GAZE"], "鬼城Eyra", "https://www.xiaohongshu.com/explore/69f1e5a000000000350390c1", "CANDIDATE")

    add_cand("CAND_090", "staging/eyra_cells/eyra_07_r1_c1.webp",
             "手指比剑诀虚抚帽檐与发饰，面部微侧嘴角含笑，具仙侠灵气",
             "C_HANDS_FACE", ["SWORD_FINGER", "HAT_GESTURE"], "鬼城Eyra", "https://www.xiaohongshu.com/explore/69f1e5a000000000350390c1", "CANDIDATE")

    add_cand("CAND_091", "staging/eyra_cells/eyra_07_r2_c1.webp",
             "双手轻按胸前衣襟，眼神含蓄下敛，端庄含蓄的神态展示",
             "C_HANDS_FACE", ["CHEST_HOLD", "MODEST_GAZE"], "鬼城Eyra", "https://www.xiaohongshu.com/explore/69f1e5a000000000350390c1", "CANDIDATE")

    add_cand("CAND_092", "staging/eyra_cells/eyra_08_r1_c1.webp",
             "半身特写双手持道具横于胸前，眼神沉着冷静直视镜头",
             "C_HANDS_FACE", ["HALF_BODY_PROP", "STEADY_GAZE"], "鬼城Eyra", "https://www.xiaohongshu.com/explore/69f1e5a000000000350390c1", "CANDIDATE")

    add_cand("CAND_093", "staging/eyra_cells/eyra_08_r2_c2.webp",
             "面部特写单手轻抚领口领巾，眼眸微转带若有所思的神情",
             "C_HANDS_FACE", ["COLLAR_CARESS", "SOFT_EYES"], "鬼城Eyra", "https://www.xiaohongshu.com/explore/69f1e5a000000000350390c1", "CANDIDATE")

    add_cand("CAND_094", "staging/eyra_cells/eyra_11_r0_c1.webp",
             "狐狸面具遮半面，单眼从面具边缘望向镜头，妖艳而神秘",
             "C_HANDS_FACE", ["FOX_MASK", "HALF_FACE_GAZE"], "鬼城Eyra", "https://www.xiaohongshu.com/explore/69f1e5a000000000350390c1", "CANDIDATE")

    add_cand("CAND_095", "staging/eyra_cells/eyra_11_r1_c1.webp",
             "双手挽大袖于胸前抱拢，神态端庄典雅，衣袖层叠舒展",
             "C_HANDS_FACE", ["SLEEVE_GATHER", "NOBLE_POSTURE"], "鬼城Eyra", "https://www.xiaohongshu.com/explore/69f1e5a000000000350390c1", "CANDIDATE")

    add_cand("CAND_096", "staging/eyra_cells/eyra_12_r0_c0.webp",
             "面部特写双手调整手套腕部，眼神直勾勾注视镜头极具穿透力",
             "C_HANDS_FACE", ["GLOVE_ADJUST", "PIERCING_GAZE"], "鬼城Eyra", "https://www.xiaohongshu.com/explore/69f1e5a000000000350390c1", "CANDIDATE")

    add_cand("CAND_097", "staging/eyra_cells/eyra_13_r1_c0.webp",
             "半身特写单手猫爪轻挡嘴唇作轻咬状，表情娇憨可爱",
             "C_HANDS_FACE", ["PAW_LIP", "CUTE_GESTURE"], "鬼城Eyra", "https://www.xiaohongshu.com/explore/69f1e5a000000000350390c1", "CANDIDATE")

    add_cand("CAND_098", "staging/eyra_cells/eyra_13_r2_c2.webp",
             "面部特写双手拢于下颌，大眼睛清澈对视镜头，柔光肤质",
             "C_HANDS_FACE", ["CHIN_CUPPING", "LUMINOUS_SKIN"], "鬼城Eyra", "https://www.xiaohongshu.com/explore/69f1e5a000000000350390c1", "CANDIDATE")

    add_cand("CAND_099", "refs/02_STYLE/STYLE_002_dreamy_blue_jellyfish_lake.webp",
             "水母水下意境特写，双手轻捻发光透明长纱悬于眼前，发丝散开",
             "C_HANDS_FACE", ["VEIL_HOLD", "UNDERWATER_GLOW"], "水母湖拟态私影", "https://www.xiaohongshu.com/explore/66b04800000000001e02ef34", "CANDIDATE")

    # ========================================================
    # Direction D: 小凳 / 低马扎坐姿 (D_LOW_STOOL) - 35 Items
    # ========================================================
    add_cand("CAND_100", "refs/03_POSE/02_STOOL_SEATED/POSE_0201_stool_leg_extension_open_arms.webp",
             "小圆凳浅坐，右腿向前下方斜向伸直并紧绷脚尖，左腿弯曲交叠，双手向两侧微张如水母浮游",
             "D_LOW_STOOL", ["LOW_STOOL", "POINTED_TOE", "FLOATING_ARMS"], "舟零", "https://www.xiaohongshu.com/explore/67c802000000000014023b12", "PRESELECTED")

    add_cand("CAND_101", "refs/03_POSE/02_STOOL_SEATED/POSE_0202_stool_chest_touch_lean_back.webp",
             "小圆凳坐姿身体微后仰，左手后撑凳面，右手食指轻抚锁骨与红核宝石，双腿斜伸绷脚尖",
             "D_LOW_STOOL", ["LOW_STOOL", "CHEST_TOUCH", "LEAN_BACK"], "舟零", "https://www.xiaohongshu.com/explore/67c802000000000014023b12", "PRESELECTED")

    add_cand("CAND_102", "staging/downloads/zhoulan_chair/chair_pose_03.webp",
             "圆凳侧身坐姿，右手抬起轻搭对侧肩膀吊带，眼神侧视微思，双腿交叠自然下垂",
             "D_LOW_STOOL", ["LOW_STOOL", "SHOULDER_TOUCH"], "舟零", "https://www.xiaohongshu.com/explore/67c802000000000014023b12", "CANDIDATE")

    add_cand("CAND_103", "refs/03_POSE/02_STOOL_SEATED/POSE_0203_stool_hug_knees_head_tilt.webp",
             "台阶低坐姿双腿屈膝收于胸前，双手合抱膝盖，头部微侧枕于膝头，眼神空灵悲悯",
             "D_LOW_STOOL", ["STEP_SEATED", "HUG_KNEES", "MELANCHOLY"], "未记录 (绫波丽户外场照)", "https://www.xiaohongshu.com/explore/692819db000000001e031c31", "PRESELECTED")

    add_cand("CAND_104", "images/cos-0016.webp",
             "课桌椅侧坐单腿抬起微屈，一手轻搭椅背，另一手收于胸前",
             "D_LOW_STOOL", ["CHAIR_SEATED", "LEG_LIFT"], "教室场景 Cosplay", "https://www.xiaohongshu.com/explore/67d80400000000001203fe8f", "CANDIDATE")

    add_cand("CAND_105", "images/cos-0018.webp",
             "地面低坐双腿并拢侧屈，双手环抱身前物品遮挡，鞋底自然伸向镜头透视",
             "D_LOW_STOOL", ["FLOOR_SEATED", "LOW_POSE"], "教室场景 Cosplay", "https://www.xiaohongshu.com/explore/67d80400000000001203fe8f", "CANDIDATE")

    add_cand("CAND_106", "images/cos-0047.webp",
             "阶梯梯凳侧坐屈腿微侧仰头，手搭领口，双腿高低错开拉长线条",
             "D_LOW_STOOL", ["LADDER_SEATED", "HIGH_LEG"], "低视角拍摄合集❤", "https://www.xiaohongshu.com/explore/6a1005000000000019013c78", "CANDIDATE")

    add_cand("CAND_107", "staging/chair_cells/chair_02_r0_c1.webp",
             "小凳侧坐双腿向前斜向伸展绷直脚尖，双手向后轻撑凳面，上身微后倾舒展",
             "D_LOW_STOOL", ["LOW_STOOL", "LEG_EXTENSION"], "舟零", "https://www.xiaohongshu.com/explore/67c802000000000014023b12", "CANDIDATE")

    add_cand("CAND_108", "staging/chair_cells/chair_02_r2_c2.webp",
             "小凳端坐双腿并拢斜放，右手抚胸，左手自然垂于大腿外侧",
             "D_LOW_STOOL", ["LOW_STOOL", "CHEST_TOUCH"], "舟零", "https://www.xiaohongshu.com/explore/67c802000000000014023b12", "CANDIDATE")

    add_cand("CAND_109", "staging/chair_cells/chair_02_r1_c2.webp",
             "小凳坐姿身体前倾微俯，双臂环抱膝部前侧，头部微仰直视镜头",
             "D_LOW_STOOL", ["LOW_STOOL", "FORWARD_LEAN"], "舟零", "https://www.xiaohongshu.com/explore/67c802000000000014023b12", "CANDIDATE")

    add_cand("CAND_110", "staging/chair_cells/chair_02_r0_c2.webp",
             "小凳侧坐双手向身体两侧水平微张，掌心向上如水中失重悬浮",
             "D_LOW_STOOL", ["LOW_STOOL", "FLOATING_ARMS"], "舟零", "https://www.xiaohongshu.com/explore/67c802000000000014023b12", "CANDIDATE")

    add_cand("CAND_111", "refs/02_STYLE/STYLE_001_hanging_jellyfish_portrait.webp",
             "悬挂发光水母灯下端坐，双手挽长纱向两侧微扬做水母触须流动展示",
             "D_LOW_STOOL", ["SEATED", "JELLYFISH_LAMP", "VEIL_FLOW"], "水母湖拟态私影", "https://www.xiaohongshu.com/explore/66b04800000000001e02ef34", "CANDIDATE")

    add_cand("CAND_112", "staging/downloads/zhoulan_chair/chair_pose_01.webp",
             "高清圆凳坐姿单腿高抬搭梯档双手向外舒展，展示修长线条",
             "D_LOW_STOOL", ["STOOL_LEG_HIGH", "ARM_SPREAD"], "舟零", "https://www.xiaohongshu.com/explore/67c802000000000014023b12", "CANDIDATE")

    add_cand("CAND_113", "staging/downloads/zhoulan_chair/chair_pose_04.webp",
             "高清圆凳坐姿身体后倾双腿斜伸紧绷脚尖，单手后撑凳面优雅舒展",
             "D_LOW_STOOL", ["STOOL_LEAN_BACK", "LEG_STRETCH"], "舟零", "https://www.xiaohongshu.com/explore/67c802000000000014023b12", "CANDIDATE")

    add_cand("CAND_114", "refs/90_REJECTED/POSE_0201_stool_staff_chin_gesture.webp",
             "小凳端坐双腿斜放单手托腮手肘撑膝，眼神清冷凝视前方",
             "D_LOW_STOOL", ["STOOL_CHIN_REST", "ELEGANT_SIT"], "鹿岛漫展组", "https://www.xiaohongshu.com/explore/66e01234000000001102aabb", "CANDIDATE")

    add_cand("CAND_115", "refs/90_REJECTED/POSE_0202_stool_crossed_legs_forward_lean.webp",
             "小凳坐姿身体前倾双手交叠手肘搭大腿，双腿交叠自然下垂",
             "D_LOW_STOOL", ["STOOL_LEAN", "CROSSED_LEGS"], "鹿岛漫展组", "https://www.xiaohongshu.com/explore/66e01234000000001102aabb", "CANDIDATE")

    add_cand("CAND_116", "refs/90_REJECTED/POSE_0203_stool_staff_horizontal_cross.webp",
             "小凳坐姿横持长道具横于腿上，双手自然搭于柄身",
             "D_LOW_STOOL", ["STOOL_PROP_LAP", "RESTING_STAFF"], "鹿岛漫展组", "https://www.xiaohongshu.com/explore/66e01234000000001102aabb", "CANDIDATE")

    add_cand("CAND_117", "refs/90_REJECTED/POSE_0802_low_angle_leg_projection_stool.webp",
             "低凳坐姿单腿向前伸长形成透视，脚尖自然下指拉长双腿",
             "D_LOW_STOOL", ["STOOL_PERSPECTIVE", "TOE_POINT"], "鹿岛漫展组", "https://www.xiaohongshu.com/explore/66e01234000000001102aabb", "CANDIDATE")

    add_cand("CAND_118", "staging/chair_cells/chair_02_r0_c0.webp",
             "吧台凳侧坐单腿屈膝搭脚踏单腿自然下垂，身体挺拔从容",
             "D_LOW_STOOL", ["BAR_STOOL", "FOOT_REST"], "舟零", "https://www.xiaohongshu.com/explore/67c802000000000014023b12", "CANDIDATE")

    add_cand("CAND_119", "staging/chair_cells/chair_02_r0_c3.webp",
             "吧台凳正坐双手自然搭腿外侧双腿并拢斜放，神情端庄文静",
             "D_LOW_STOOL", ["BAR_STOOL", "MODEST_SIT"], "舟零", "https://www.xiaohongshu.com/explore/67c802000000000014023b12", "CANDIDATE")

    add_cand("CAND_120", "staging/chair_cells/chair_02_r1_c0.webp",
             "吧台凳坐姿双手扶后脑勺身体拉长舒展，展现腰身曲线",
             "D_LOW_STOOL", ["BAR_STOOL", "ARMS_HEAD"], "舟零", "https://www.xiaohongshu.com/explore/67c802000000000014023b12", "CANDIDATE")

    add_cand("CAND_121", "staging/chair_cells/chair_02_r1_c1.webp",
             "吧台凳正坐双手平摊向两侧身体微倾，神情从容放松",
             "D_LOW_STOOL", ["BAR_STOOL", "OPEN_HANDS"], "舟零", "https://www.xiaohongshu.com/explore/67c802000000000014023b12", "CANDIDATE")

    add_cand("CAND_122", "staging/chair_cells/chair_02_r2_c0.webp",
             "吧台凳侧身坐一手抚下颌一手扶膝，侧颜凝视侧方",
             "D_LOW_STOOL", ["BAR_STOOL", "PROFILE_SIT"], "舟零", "https://www.xiaohongshu.com/explore/67c802000000000014023b12", "CANDIDATE")

    add_cand("CAND_123", "staging/chair_cells/chair_02_r2_c1.webp",
             "吧台凳侧坐单腿屈起单手扶膝，姿态自然不僵硬",
             "D_LOW_STOOL", ["BAR_STOOL", "KNEE_LIFT"], "舟零", "https://www.xiaohongshu.com/explore/67c802000000000014023b12", "CANDIDATE")

    add_cand("CAND_124", "staging/chair_cells/chair_02_r3_c0.webp",
             "吧台凳侧坐双手轻抚后颈头部微仰，展现颈部线条",
             "D_LOW_STOOL", ["BAR_STOOL", "NECK_TOUCH"], "舟零", "https://www.xiaohongshu.com/explore/67c802000000000014023b12", "CANDIDATE")

    add_cand("CAND_125", "staging/chair_cells/chair_02_r3_c1.webp",
             "吧台凳坐姿双手垂于身侧双腿斜伸交叠，体态优雅文静",
             "D_LOW_STOOL", ["BAR_STOOL", "ELEGANT_LEGS"], "舟零", "https://www.xiaohongshu.com/explore/67c802000000000014023b12", "CANDIDATE")

    add_cand("CAND_126", "staging/chair_cells/chair_02_r3_c2.webp",
             "吧台凳坐姿微前倾双手抱胸神情专注，气质冷冽从容",
             "D_LOW_STOOL", ["BAR_STOOL", "ARMS_CHEST"], "舟零", "https://www.xiaohongshu.com/explore/67c802000000000014023b12", "CANDIDATE")

    add_cand("CAND_127", "staging/eyra_cells/eyra_01_r2_c0.webp",
             "白色矮木箱坐姿二郎腿翘起双手搭大腿，神态优雅安坐",
             "D_LOW_STOOL", ["WOOD_BOX", "CROSS_LEG"], "鬼城Eyra", "https://www.xiaohongshu.com/explore/69f1e5a000000000350390c1", "CANDIDATE")

    add_cand("CAND_128", "staging/eyra_cells/eyra_01_r2_c1.webp",
             "白色矮木箱浅坐双腿并拢微侧双手搭膝盖，姿态端正乖巧",
             "D_LOW_STOOL", ["WOOD_BOX", "DEMURE_SIT"], "鬼城Eyra", "https://www.xiaohongshu.com/explore/69f1e5a000000000350390c1", "CANDIDATE")

    add_cand("CAND_129", "staging/eyra_cells/eyra_01_r2_c2.webp",
             "圆台地面低坐双腿并拢侧叠双手虚撑地面，裙摆自然铺地",
             "D_LOW_STOOL", ["PLATFORM_FLOOR", "SKIRT_SPREAD"], "鬼城Eyra", "https://www.xiaohongshu.com/explore/69f1e5a000000000350390c1", "CANDIDATE")

    add_cand("CAND_130", "staging/eyra_cells/eyra_04_r1_c1.webp",
             "矮梯凳坐姿长刀斜靠单腿高踩梯档拉长线条，身形修长",
             "D_LOW_STOOL", ["LADDER_STOOL", "LEG_LINE"], "鬼城Eyra", "https://www.xiaohongshu.com/explore/69f1e5a000000000350390c1", "CANDIDATE")

    add_cand("CAND_131", "staging/eyra_cells/eyra_07_r0_c1.webp",
             "矮凳坐姿双手横握长杖搭在膝头双腿交叠，目光如炬",
             "D_LOW_STOOL", ["STOOL_STAFF", "INTENSE_LOOK"], "鬼城Eyra", "https://www.xiaohongshu.com/explore/69f1e5a000000000350390c1", "CANDIDATE")

    add_cand("CAND_132", "staging/eyra_cells/eyra_07_r2_c2.webp",
             "矮凳极低机位坐姿单腿向前伸出靴尖透视，极具视觉冲击",
             "D_LOW_STOOL", ["STOOL_LOW_ANGLE", "BOOT_PERSPECTIVE"], "鬼城Eyra", "https://www.xiaohongshu.com/explore/69f1e5a000000000350390c1", "CANDIDATE")

    add_cand("CAND_133", "staging/eyra_cells/eyra_11_r2_c0.webp",
             "地面侧卧单手撑地和伞斜放于身侧，大袖长裙铺散在地",
             "D_LOW_STOOL", ["GROUND_RECLINE", "UMBRELLA_REST"], "鬼城Eyra", "https://www.xiaohongshu.com/explore/69f1e5a000000000350390c1", "CANDIDATE")

    add_cand("CAND_134", "staging/eyra_cells/eyra_12_r0_c2.webp",
             "矮凳坐姿二郎腿高高翘起单手轻搭脚踝，神情高傲冷漠",
             "D_LOW_STOOL", ["HIGH_CROSS_LEG", "ANKLE_TOUCH"], "鬼城Eyra", "https://www.xiaohongshu.com/explore/69f1e5a000000000350390c1", "CANDIDATE")

    # ========================================================
    # Direction E: 长柄道具 / 法杖 / 伞优雅互动 (E_PROP) - 35 Items
    # ========================================================
    add_cand("CAND_135", "refs/03_POSE/06_PROP_WEAPON/POSE_0601_staff_vertical_ground_lean.webp",
             "台阶立柱旁站立，长道具/琴立于地面，右手扶持道具顶部琴头，左手轻倚身侧栏杆/腰间微斜靠",
             "E_PROP", ["PROP_LEAN", "VERTICAL_STAFF", "NON_COMBAT"], "大道寺cheese【图文版】", "https://www.xiaohongshu.com/explore/692019db000000001e031c31", "PRESELECTED")

    add_cand("CAND_136", "refs/03_POSE/06_PROP_WEAPON/POSE_0602_staff_low_angle_stride.webp",
             "漫展现场低机位双腿交叉跨步，双手横持长道具横于髋前，手腕自然垂落不挡胸",
             "E_PROP", ["PROP_STRIDE", "CROSS_LEG", "HORIZONTAL_HOLD"], "未记录 (漫展人像布光与姿势示例)", "https://www.xiaohongshu.com/explore/68d20300000000001301fa23", "PRESELECTED")

    add_cand("CAND_137", "images/cos-0019.webp",
             "课桌旁交叉腿站姿，单手将长道具竖立垂持于身侧，另一手自然下垂",
             "E_PROP", ["PROP_VERTICAL", "CROSS_LEG"], "教室场景 Cosplay", "https://www.xiaohongshu.com/explore/67d80400000000001203fe8f", "CANDIDATE")

    add_cand("CAND_138", "images/cos-0027.webp",
             "铁梯阶梯站立，双手横向抱持长道具/乐器，身体侧立微前探",
             "E_PROP", ["PROP_HOLD", "STAIR_STANDING"], "明日香 摇滚乐队 cosplay", "https://www.xiaohongshu.com/explore/692019db000000001e031c31", "CANDIDATE")

    add_cand("CAND_139", "images/cos-0033.webp",
             "侧身3/4站立，双手一高一低握持黑色长道具斜跨胸前形成对角线，身体重心在后脚",
             "E_PROP", ["PROP_DIAGONAL", "TWO_HANDS"], "双喜📷", "https://www.xiaohongshu.com/explore/68f00100000000001503cb89", "CANDIDATE")

    add_cand("CAND_140", "images/cos-0038.webp",
             "单腿微抬平衡，长道具平放搭在单侧肩膀，双手虚扶柄部，身体微侧微倾",
             "E_PROP", ["PROP_SHOULDER", "BALANCE"], "双喜📷", "https://www.xiaohongshu.com/explore/68f00100000000001503cb89", "CANDIDATE")

    add_cand("CAND_141", "images/cos-0040.webp",
             "侧立站姿，双手握道具出鞘斜持于体侧，身体微后坐形成端正站姿",
             "E_PROP", ["PROP_DRAW", "SIDE_STANDING"], "双喜📷", "https://www.xiaohongshu.com/explore/68f00100000000001503cb89", "CANDIDATE")

    add_cand("CAND_142", "images/cos-0045.webp",
             "双持长道具向斜后方V形展开，身体微侧站立，眼神清冷侧视",
             "E_PROP", ["PROP_V_SHAPE", "DUAL_HOLD"], "双喜📷", "https://www.xiaohongshu.com/explore/68f00100000000001503cb89", "CANDIDATE")

    add_cand("CAND_143", "staging/eyra_cells/eyra_05_r0_c1.webp",
             "长柄垂直立地，右手扶上方手柄，左手扶下方中段，身体正面微侧端立",
             "E_PROP", ["PROP_VERTICAL", "TWO_HANDED"], "鬼城Eyra", "https://www.xiaohongshu.com/explore/69f1e5a000000000350390c1", "CANDIDATE")

    add_cand("CAND_144", "staging/eyra_cells/eyra_04_r1_c1.webp",
             "长道具斜靠肩膀，单手虚扶刀柄，身体双腿交叠站立，眼神下视",
             "E_PROP", ["PROP_SHOULDER", "RELAXED"], "鬼城Eyra", "https://www.xiaohongshu.com/explore/69f1e5a000000000350390c1", "CANDIDATE")

    add_cand("CAND_145", "staging/eyra_cells/eyra_04_r2_c0.webp",
             "侧身坐姿长道具立于身侧地面，单手搭在柄头，双腿并拢斜放",
             "E_PROP", ["PROP_SEATED", "LOW_STOOL"], "鬼城Eyra", "https://www.xiaohongshu.com/explore/69f1e5a000000000350390c1", "CANDIDATE")

    add_cand("CAND_146", "staging/eyra_cells/eyra_11_r0_c0.webp",
             "正面双手交叠于长伞/法杖柄头，身体笔直站立，下巴微收端庄安详",
             "E_PROP", ["PROP_FRONT", "HANDS_CLASP"], "鬼城Eyra", "https://www.xiaohongshu.com/explore/69f1e5a000000000350390c1", "CANDIDATE")

    add_cand("CAND_147", "refs/90_REJECTED/REJECT_POSE_0601_staff_diagonal_cross_chest.webp",
             "双手握长柄斜跨胸前45度对角线，神态庄严威仪，线条凌厉修长",
             "E_PROP", ["STAFF_DIAGONAL", "CHEST_CROSS"], "双喜📷", "https://www.xiaohongshu.com/explore/68f00100000000001503cb89", "CANDIDATE")

    add_cand("CAND_148", "refs/90_REJECTED/POSE_0104_staff_ground_stance_noble.webp",
             "单手扶立地长杖身形挺拔贵族站姿，另一手叉腰贵气从容",
             "E_PROP", ["STAFF_GROUND", "NOBLE_STANCE"], "鹿岛漫展组", "https://www.xiaohongshu.com/explore/66e01234000000001102aabb", "CANDIDATE")

    add_cand("CAND_149", "refs/90_REJECTED/POSE_0601_staff_vertical_standing_grip.webp",
             "垂直立地单手握持长杖中上部，身体正面微侧笔直伫立",
             "E_PROP", ["STAFF_VERTICAL", "ELEGANT_HOLD"], "鹿岛漫展组", "https://www.xiaohongshu.com/explore/66e01234000000001102aabb", "CANDIDATE")

    add_cand("CAND_150", "refs/90_REJECTED/POSE_0602_staff_two_handed_front_guard.webp",
             "双手持长柄横于腹前防守预备姿态，眼神坚定锁定前方",
             "E_PROP", ["STAFF_GUARD", "TWO_HANDED"], "鹿岛漫展组", "https://www.xiaohongshu.com/explore/66e01234000000001102aabb", "CANDIDATE")

    add_cand("CAND_151", "refs/90_REJECTED/POSE_0502_hands_umbrella_shaft_interact.webp",
             "双手扶长伞杆轻轻旋转伞面，伞骨遮挡形成诗意阴影",
             "E_PROP", ["UMBRELLA_INTERACT", "ROTATING_SHAFT"], "鹿岛漫展组", "https://www.xiaohongshu.com/explore/66e01234000000001102aabb", "CANDIDATE")

    add_cand("CAND_152", "images/cos-0044.webp",
             "手臂交叉双刃横于胸前近景，身体微俯形成向前压迫动势",
             "E_PROP", ["PROP_CROSS", "CLOSEUP_PROP"], "双喜📷", "https://www.xiaohongshu.com/explore/68f00100000000001503cb89", "CANDIDATE")

    add_cand("CAND_153", "images/cos-0046.webp",
             "场馆内贴地极低机位仰拍双腿拉开站稳，双手斜持长柄道具后置",
             "E_PROP", ["PROP_LONG", "EXPO_HALL"], "果果酱啦啦啦", "https://www.xiaohongshu.com/explore/6a1005000000000019013c78", "CANDIDATE")

    add_cand("CAND_154", "staging/eyra_cells/eyra_04_r0_c0.webp",
             "单膝跪地长刀垂直立地右手扶刀柄头部微仰，气质沉静从容",
             "E_PROP", ["KNEEL_PROP", "VERTICAL_BLADE"], "鬼城Eyra", "https://www.xiaohongshu.com/explore/69f1e5a000000000350390c1", "CANDIDATE")

    add_cand("CAND_155", "staging/eyra_cells/eyra_04_r1_c0.webp",
             "蹲姿双手握长刀斜放体侧刀尖指向后方，眼神机敏警惕",
             "E_PROP", ["CROUCH_BLADE", "SIDE_GUARD"], "鬼城Eyra", "https://www.xiaohongshu.com/explore/69f1e5a000000000350390c1", "CANDIDATE")

    add_cand("CAND_156", "staging/eyra_cells/eyra_04_r2_c2.webp",
             "正面微侧立长刀垂直点地双手交叠于柄端，身姿优雅挺拔",
             "E_PROP", ["BLADE_POINT_GROUND", "TALL_STAND"], "鬼城Eyra", "https://www.xiaohongshu.com/explore/69f1e5a000000000350390c1", "CANDIDATE")

    add_cand("CAND_157", "staging/eyra_cells/eyra_05_r0_c2.webp",
             "侧背身双手反握长柄刀刃斜指地面，体态利落帅气",
             "E_PROP", ["REVERSE_GRIP", "STAFF_GROUND"], "鬼城Eyra", "https://www.xiaohongshu.com/explore/69f1e5a000000000350390c1", "CANDIDATE")

    add_cand("CAND_158", "staging/eyra_cells/eyra_05_r1_c0.webp",
             "展位双手持长柄斜横身前形成强烈对角线，身体微蹲蓄力",
             "E_PROP", ["STAFF_DIAGONAL", "READY_STANCE"], "鬼城Eyra", "https://www.xiaohongshu.com/explore/69f1e5a000000000350390c1", "CANDIDATE")

    add_cand("CAND_159", "staging/eyra_cells/eyra_05_r1_c2.webp",
             "单膝跪地单手持长柄向斜后方撑开动势，身体前倾压低重心",
             "E_PROP", ["KNEEL_STAFF", "OUTSTRETCHED"], "鬼城Eyra", "https://www.xiaohongshu.com/explore/69f1e5a000000000350390c1", "CANDIDATE")

    add_cand("CAND_160", "staging/eyra_cells/eyra_05_r2_c0.webp",
             "地面侧卧长柄斜靠身侧神情慵懒清冷，发丝散落地面",
             "E_PROP", ["FLOOR_PROP", "RECLINING"], "鬼城Eyra", "https://www.xiaohongshu.com/explore/69f1e5a000000000350390c1", "CANDIDATE")

    add_cand("CAND_161", "staging/eyra_cells/eyra_06_r0_c0.webp",
             "蹲姿长刀出鞘双手横握刀鞘与刀柄，眼神冷冽如霜",
             "E_PROP", ["DRAW_BLADE", "CROUCH_GUARD"], "鬼城Eyra", "https://www.xiaohongshu.com/explore/69f1e5a000000000350390c1", "CANDIDATE")

    add_cand("CAND_162", "staging/eyra_cells/eyra_06_r0_c2.webp",
             "单手将长刀扛在肩后刀鞘斜垂身侧，侧身站立自信从容",
             "E_PROP", ["SHOULDER_BLADE", "CONFIDENT"], "鬼城Eyra", "https://www.xiaohongshu.com/explore/69f1e5a000000000350390c1", "CANDIDATE")

    add_cand("CAND_163", "staging/eyra_cells/eyra_06_r1_c2.webp",
             "双手持双剑/双刀交叉胸前呈X形，神态威风凛凛",
             "E_PROP", ["X_CROSS_BLADES", "DUAL_WEAPON"], "鬼城Eyra", "https://www.xiaohongshu.com/explore/69f1e5a000000000350390c1", "CANDIDATE")

    add_cand("CAND_164", "staging/eyra_cells/eyra_07_r0_c0.webp",
             "低蹲单手提长杖立地另一手做指法，身形紧凑灵敏",
             "E_PROP", ["CROUCH_STAFF", "MAGIC_GESTURE"], "鬼城Eyra", "https://www.xiaohongshu.com/explore/69f1e5a000000000350390c1", "CANDIDATE")

    add_cand("CAND_165", "staging/eyra_cells/eyra_07_r1_c0.webp",
             "丁字步单手提长杖斜跨身体侧面，神情英姿飒爽",
             "E_PROP", ["SIDE_STAFF", "HEROIC_STANCE"], "鬼城Eyra", "https://www.xiaohongshu.com/explore/69f1e5a000000000350390c1", "CANDIDATE")

    add_cand("CAND_166", "staging/eyra_cells/eyra_07_r2_c0.webp",
             "提腿单手舞动长杖微仰头展现灵动感，衣服摆带飘逸",
             "E_PROP", ["STAFF_DANCE", "LIFT_LEG"], "鬼城Eyra", "https://www.xiaohongshu.com/explore/69f1e5a000000000350390c1", "CANDIDATE")

    add_cand("CAND_167", "staging/eyra_cells/eyra_11_r0_c2.webp",
             "撑开红伞斜搭肩后身形前探漫步，和风优雅端庄",
             "E_PROP", ["PARASOL_SHOULDER", "ELEGANT_WALK"], "鬼城Eyra", "https://www.xiaohongshu.com/explore/69f1e5a000000000350390c1", "CANDIDATE")

    add_cand("CAND_168", "staging/eyra_cells/eyra_11_r2_c1.webp",
             "低坐手举红伞遮顶头部微仰注视伞骨，红伞逆光通透",
             "E_PROP", ["PARASOL_OVERHEAD", "SEATED_GAZE"], "鬼城Eyra", "https://www.xiaohongshu.com/explore/69f1e5a000000000350390c1", "CANDIDATE")

    add_cand("CAND_169", "refs/90_REJECTED/POSE_0303_half_body_staff_horizontal_point.webp",
             "半身长柄水平横指向侧方眼神顺指，极具指向性视觉引导",
             "E_PROP", ["STAFF_POINT", "DIRECTIONAL"], "鹿岛漫展组", "https://www.xiaohongshu.com/explore/66e01234000000001102aabb", "CANDIDATE")

    # ========================================================
    # Direction F: 柔和低机位 (F_LOW_ANGLE) - 33 Items
    # ========================================================
    add_cand("CAND_170", "refs/03_POSE/08_LOW_ANGLE/POSE_0801_low_angle_divine_arch_stretch.webp",
             "贴地极低机位仰拍，身体后仰拉出S弯，单手高抬虚抚立柱上方拱顶，长裙长纱自然倾泻",
             "F_LOW_ANGLE", ["LOW_ANGLE", "S_CURVE", "BORROW_PILLAR"], "深海水族场照实录", "https://www.xiaohongshu.com/explore/66b04800000000001e02ef34", "PRESELECTED")

    add_cand("CAND_171", "refs/03_POSE/08_LOW_ANGLE/POSE_004_underwater_column_floating.webp",
             "水下悬浮低机位仰望，双臂浮游微展，闭目静思，水下裙摆失重散开",
             "F_LOW_ANGLE", ["LOW_ANGLE", "UNDERWATER", "FLOATING"], "深海水族场照实录", "https://www.xiaohongshu.com/explore/66b04800000000001e02ef34", "PRESELECTED")

    add_cand("CAND_172", "images/xhs-005-03.webp",
             "低机位圆台站姿，双手轻捏两侧裙摆向外微展，头微低俯视镜头",
             "F_LOW_ANGLE", ["LOW_ANGLE", "SKIRT_LIFT", "DIVINE_GAZE"], "漫展现场少女记录", "https://www.xiaohongshu.com/explore/68d20300000000001301fa23", "CANDIDATE")

    add_cand("CAND_173", "images/cos-0046.webp",
             "场馆内贴地极低机位仰拍，双腿拉开站稳拉长下半身线条，双手斜持长柄道具后置",
             "F_LOW_ANGLE", ["LOW_ANGLE", "PROP_LONG", "EXPO_HALL"], "果果酱啦啦啦", "https://www.xiaohongshu.com/explore/6a1005000000000019013c78", "CANDIDATE")

    add_cand("CAND_174", "images/cos-0048.webp",
             "吧台低机位仰拍单腿前伸靴尖透视，上身斜靠吧台轻举小物",
             "F_LOW_ANGLE", ["LOW_ANGLE", "PERSPECTIVE_LEG"], "低视角拍摄合集❤", "https://www.xiaohongshu.com/explore/6a1005000000000019013c78", "CANDIDATE")

    add_cand("CAND_175", "refs/03_POSE/08_LOW_ANGLE/POSE_0802_low_angle_wide_stance_perspective.webp",
             "狭长过道极低机位仰拍，双腿大步张开前弓后绷拉长双腿，上身前探俯视镜头",
             "F_LOW_ANGLE", ["LOW_ANGLE", "WIDE_STANCE"], "大道寺cheese【图文版】", "https://www.xiaohongshu.com/explore/692019db000000001e031c31", "CANDIDATE")

    add_cand("CAND_176", "images/cos-0009.webp",
             "展馆低蹲姿态，双手握持道具横于前侧，重心压低仰角拍摄",
             "F_LOW_ANGLE", ["LOW_ANGLE", "LOW_CROUCH"], "鹿岛姿势表", "https://www.xiaohongshu.com/explore/67d80400000000001203fe8f", "CANDIDATE")

    add_cand("CAND_177", "images/cos-0011.webp",
             "双人构图低机位，一人单膝低跪一人直立扶膝，黑白制服对比",
             "F_LOW_ANGLE", ["LOW_ANGLE", "DUO_STANCE"], "漫展人像布光与姿势示例", "https://www.xiaohongshu.com/explore/68d20300000000001301fa23", "CANDIDATE")

    add_cand("CAND_178", "refs/90_REJECTED/REJECT_POSE_0801_low_angle_ground_scythe_stance.webp",
             "贴地低机位长柄武器点地，单腿跨步前弓后绷，裙摆贴地铺开气势磅礴",
             "F_LOW_ANGLE", ["LOW_ANGLE", "SCYTHE_GROUND", "FULL_BODY"], "双喜📷", "https://www.xiaohongshu.com/explore/68f00100000000001503cb89", "CANDIDATE")

    add_cand("CAND_179", "refs/90_REJECTED/POSE_0402_low_angle_closeup_cool_look.webp",
             "低机位半身仰拍下巴微扬眼神高傲俯瞰，避开杂乱天花板背景",
             "F_LOW_ANGLE", ["LOW_ANGLE", "HALF_BODY_COOL"], "鹿岛漫展组", "https://www.xiaohongshu.com/explore/66e01234000000001102aabb", "CANDIDATE")

    add_cand("CAND_180", "refs/90_REJECTED/POSE_0802_low_angle_leg_projection_stool.webp",
             "极低机位坐姿单腿向前伸长脚尖占满下半部，透视拉伸腿长效果极佳",
             "F_LOW_ANGLE", ["LOW_ANGLE", "LEG_PERSPECTIVE"], "鹿岛漫展组", "https://www.xiaohongshu.com/explore/66e01234000000001102aabb", "CANDIDATE")

    add_cand("CAND_181", "images/cos-0008.webp",
             "暗调展区低机位双手向外张开撑出大轮廓，身形高挑挺拔",
             "F_LOW_ANGLE", ["LOW_ANGLE", "OUTSTRETCHED"], "猫又来喽", "https://www.xiaohongshu.com/explore/68e8f98e0000000007002896", "CANDIDATE")

    add_cand("CAND_182", "images/cos-0049.webp",
             "低机位仰视角色俯身伸手探向镜头极富冲击力，近大远小对比鲜明",
             "F_LOW_ANGLE", ["LOW_ANGLE", "HAND_FOREGROUND"], "武于钧", "https://www.xiaohongshu.com/explore/684c98000000000010012e45", "CANDIDATE")

    add_cand("CAND_183", "images/cos-0050.webp",
             "机柜内低机位仰拍立柱框架全身线条拉长，工整对称构图",
             "F_LOW_ANGLE", ["LOW_ANGLE", "FRAME_SYMMETRY"], "武于钧", "https://www.xiaohongshu.com/explore/684c98000000000010012e45", "CANDIDATE")

    add_cand("CAND_184", "images/cos-0051.webp",
             "高机位透视与低机位对比之极具纵深感构图，单手伸向镜头",
             "F_LOW_ANGLE", ["LOW_ANGLE", "PERSPECTIVE_DEPTH"], "武于钧", "https://www.xiaohongshu.com/explore/684c98000000000010012e45", "CANDIDATE")

    add_cand("CAND_185", "staging/eyra_cells/eyra_02_r0_c0.webp",
             "低机位仰拍单膝跪地双手举道具过头顶拉长腰线，气场强大",
             "F_LOW_ANGLE", ["LOW_ANGLE", "KNEEL_RAISE"], "鬼城Eyra", "https://www.xiaohongshu.com/explore/69f1e5a000000000350390c1", "CANDIDATE")

    add_cand("CAND_186", "staging/eyra_cells/eyra_02_r0_c2.webp",
             "低机位双膝贴地向前俯身双手按膝神态专注，眼神俯视镜头",
             "F_LOW_ANGLE", ["LOW_ANGLE", "GROUND_LEAN"], "鬼城Eyra", "https://www.xiaohongshu.com/explore/69f1e5a000000000350390c1", "CANDIDATE")

    add_cand("CAND_187", "staging/eyra_cells/eyra_02_r1_c0.webp",
             "极低机位道具斜向直插镜头形成强烈近大远小，透视张力十足",
             "F_LOW_ANGLE", ["LOW_ANGLE", "PROP_EXTREME"], "鬼城Eyra", "https://www.xiaohongshu.com/explore/69f1e5a000000000350390c1", "CANDIDATE")

    add_cand("CAND_188", "staging/eyra_cells/eyra_02_r2_c0.webp",
             "低机位单腿踩台阶单手持道具侧身俯瞰，姿态帅气利落",
             "F_LOW_ANGLE", ["LOW_ANGLE", "STEP_REST"], "鬼城Eyra", "https://www.xiaohongshu.com/explore/69f1e5a000000000350390c1", "CANDIDATE")

    add_cand("CAND_189", "staging/eyra_cells/eyra_02_r2_c2.webp",
             "极低机位仰拍单腿抬高踩椅面双手持道具，居高临下霸气",
             "F_LOW_ANGLE", ["LOW_ANGLE", "CHAIR_HIGH_LEG"], "鬼城Eyra", "https://www.xiaohongshu.com/explore/69f1e5a000000000350390c1", "CANDIDATE")

    add_cand("CAND_190", "staging/eyra_cells/eyra_03_r0_c0.webp",
             "低机位单膝跪地道具指向上空眼神仰望，身形舒展",
             "F_LOW_ANGLE", ["LOW_ANGLE", "KNEEL_POINT_UP"], "鬼城Eyra", "https://www.xiaohongshu.com/explore/69f1e5a000000000350390c1", "CANDIDATE")

    add_cand("CAND_191", "staging/eyra_cells/eyra_03_r1_c0.webp",
             "极低机位贴地仰拍道具直指镜头中央，强烈透视纵深",
             "F_LOW_ANGLE", ["LOW_ANGLE", "PROP_CENTER"], "鬼城Eyra", "https://www.xiaohongshu.com/explore/69f1e5a000000000350390c1", "CANDIDATE")

    add_cand("CAND_192", "staging/eyra_cells/eyra_03_r2_c2.webp",
             "低机位贴地仰拍高抬腿踩凳面居高临下，拉长腿部线条",
             "F_LOW_ANGLE", ["LOW_ANGLE", "HIGH_LEG_STOOL"], "鬼城Eyra", "https://www.xiaohongshu.com/explore/69f1e5a000000000350390c1", "CANDIDATE")

    add_cand("CAND_193", "staging/eyra_cells/eyra_04_r0_c1.webp",
             "贴地极低机位单腿横向劈叉伸展拉出修长腿线，贴地气势磅礴",
             "F_LOW_ANGLE", ["LOW_ANGLE", "GROUND_SPLIT"], "鬼城Eyra", "https://www.xiaohongshu.com/explore/69f1e5a000000000350390c1", "CANDIDATE")

    add_cand("CAND_194", "staging/eyra_cells/eyra_04_r0_c2.webp",
             "矮凳低机位坐姿身体微仰高跟鞋尖自然下指，线条修长舒展",
             "F_LOW_ANGLE", ["LOW_ANGLE", "HEEL_LINE"], "鬼城Eyra", "https://www.xiaohongshu.com/explore/69f1e5a000000000350390c1", "CANDIDATE")

    add_cand("CAND_195", "staging/eyra_cells/eyra_04_r1_c0.webp",
             "极低机位贴地单膝跪地侧身端持长刀，避开杂乱背景",
             "F_LOW_ANGLE", ["LOW_ANGLE", "KNEEL_BLADE"], "鬼城Eyra", "https://www.xiaohongshu.com/explore/69f1e5a000000000350390c1", "CANDIDATE")

    add_cand("CAND_196", "staging/eyra_cells/eyra_06_r1_c0.webp",
             "极低机位仰拍靴尖几乎触碰镜头单腿屈膝前踩，纵深冲击强烈",
             "F_LOW_ANGLE", ["LOW_ANGLE", "BOOT_TOUCH"], "鬼城Eyra", "https://www.xiaohongshu.com/explore/69f1e5a000000000350390c1", "CANDIDATE")

    add_cand("CAND_197", "staging/eyra_cells/eyra_06_r1_c1.webp",
             "低机位单手撑地另一手拔剑出鞘蓄势待发，重心极低防穿帮",
             "F_LOW_ANGLE", ["LOW_ANGLE", "GROUND_DRAW"], "鬼城Eyra", "https://www.xiaohongshu.com/explore/69f1e5a000000000350390c1", "CANDIDATE")

    add_cand("CAND_198", "staging/eyra_cells/eyra_07_r2_c2.webp",
             "低机位坐姿单腿向前踹出鞋底透视霸气十足，视角震撼",
             "F_LOW_ANGLE", ["LOW_ANGLE", "KICK_PERSPECTIVE"], "鬼城Eyra", "https://www.xiaohongshu.com/explore/69f1e5a000000000350390c1", "CANDIDATE")

    add_cand("CAND_199", "staging/eyra_cells/eyra_08_r0_c1.webp",
             "贴地低趴姿势单手支撑地面双腿斜向拉伸，贴地避开展厅顶灯",
             "F_LOW_ANGLE", ["LOW_ANGLE", "PRONE_STRETCH"], "鬼城Eyra", "https://www.xiaohongshu.com/explore/69f1e5a000000000350390c1", "CANDIDATE")

    add_cand("CAND_200", "staging/eyra_cells/eyra_09_r0_c1.webp",
             "矮梯极低机位仰拍单腿高高搭在横档双手反握双刀，气势拔群",
             "F_LOW_ANGLE", ["LOW_ANGLE", "LADDER_DUAL"], "鬼城Eyra", "https://www.xiaohongshu.com/explore/69f1e5a000000000350390c1", "CANDIDATE")

    add_cand("CAND_201", "staging/eyra_cells/eyra_10_r2_c1.webp",
             "贴地低姿趴在反光地面双手托腮双腿向后翘起，倒影清晰",
             "F_LOW_ANGLE", ["LOW_ANGLE", "MIRROR_FLOOR"], "鬼城Eyra", "https://www.xiaohongshu.com/explore/69f1e5a000000000350390c1", "CANDIDATE")

    add_cand("CAND_202", "staging/eyra_cells/eyra_13_r0_c0.webp",
             "贴地极低机位双腿向前大叉开靴尖直接对准镜头，腿部超长透视",
             "F_LOW_ANGLE", ["LOW_ANGLE", "EXTREME_LEGS"], "鬼城Eyra", "https://www.xiaohongshu.com/explore/69f1e5a000000000350390c1", "CANDIDATE")

    # ========================================================
    # Direction G: 小幅动态 (G_DYNAMIC) - 33 Items
    # ========================================================
    add_cand("CAND_203", "refs/03_POSE/01_STANDING/POSE_0102_standing_hands_on_hips.webp",
             "正面双脚分开站稳，双手叉腰手肘向两侧撑开轮廓，头部微倾，眼神自信直视镜头",
             "G_DYNAMIC", ["DYNAMIC", "HANDS_ON_HIPS"], "猫又来喽", "https://www.xiaohongshu.com/explore/68e8f98e0000000007002896", "PRESELECTED")

    add_cand("CAND_204", "images/cos-0041.webp",
             "宽弓步双手持长道具向前跨步攻击预备动态，裙摆微扬",
             "G_DYNAMIC", ["DYNAMIC", "LUNGE_STEP"], "双喜📷", "https://www.xiaohongshu.com/explore/68f00100000000001503cb89", "CANDIDATE")

    add_cand("CAND_205", "images/cos-0044.webp",
             "手臂交叉双刃横于胸前近景，身体微俯形成向前压迫动势",
             "G_DYNAMIC", ["DYNAMIC", "PROP_CROSS"], "双喜📷", "https://www.xiaohongshu.com/explore/68f00100000000001503cb89", "CANDIDATE")

    add_cand("CAND_206", "images/cos-0008.webp",
             "暗调展区红白科技装双手张开，手持道具向外侧展开撑出大轮廓动态",
             "G_DYNAMIC", ["DYNAMIC", "PROP_OUTSTRETCH"], "猫又来喽", "https://www.xiaohongshu.com/explore/68e8f98e0000000007002896", "CANDIDATE")

    add_cand("CAND_207", "images/cos-0031.webp",
             "窄巷低蹲单腿跪地双手抱持乐器/长道具，上身前倾动态",
             "G_DYNAMIC", ["DYNAMIC", "LOW_CROUCH"], "明日香 摇滚乐队 cosplay", "https://www.xiaohongshu.com/explore/692019db000000001e031c31", "CANDIDATE")

    add_cand("CAND_208", "staging/eyra_cells/eyra_05_r0_c0.webp",
             "长柄斜下垂指地面，单手提持迈步向前跨步定格动态",
             "G_DYNAMIC", ["DYNAMIC", "FORWARD_STEP"], "鬼城Eyra", "https://www.xiaohongshu.com/explore/69f1e5a000000000350390c1", "CANDIDATE")

    add_cand("CAND_209", "staging/chair_cells/chair_02_r3_c0.webp",
             "小凳坐姿单腿高抬搭梯档，手抚长发微微侧头动态",
             "G_DYNAMIC", ["DYNAMIC", "LEG_REST"], "舟零", "https://www.xiaohongshu.com/explore/67c802000000000014023b12", "CANDIDATE")

    add_cand("CAND_210", "staging/chair_cells/chair_02_r1_c1.webp",
             "小凳正坐双腿微开手搭膝头，身体微晃侧倾动态",
             "G_DYNAMIC", ["DYNAMIC", "SEATED_MOTION"], "舟零", "https://www.xiaohongshu.com/explore/67c802000000000014023b12", "CANDIDATE")

    add_cand("CAND_211", "refs/00_OFFICIAL/OFFICIAL_001_key_visual.webp",
             "官方原画海报，身体悬浮于虚空、双手展臂、长纱水母裙摆飞舞流动动态",
             "G_DYNAMIC", ["DYNAMIC", "OFFICIAL_FLOATING", "DRESS_FLOW"], "王者荣耀官方原画", "https://pvp.qq.com/web201605/herodetail/132.shtml", "CANDIDATE")

    add_cand("CAND_212", "refs/90_REJECTED/POSE_0702_dynamic_turn_one_leg_pivot.webp",
             "单腿为轴原地慢速旋转半周，发丝与裙摆甩开的小幅定格动态",
             "G_DYNAMIC", ["DYNAMIC", "SPIN_PIVOT", "SKIRT_FLAIR"], "鹿岛漫展组", "https://www.xiaohongshu.com/explore/66e01234000000001102aabb", "CANDIDATE")

    add_cand("CAND_213", "refs/90_REJECTED/POSE_0703_turn_weapon_over_shoulder.webp",
             "原地转身长武器过肩挥动发尾微扬定格瞬间",
             "G_DYNAMIC", ["DYNAMIC", "WEAPON_SWING"], "鹿岛漫展组", "https://www.xiaohongshu.com/explore/66e01234000000001102aabb", "CANDIDATE")

    add_cand("CAND_214", "refs/90_REJECTED/POSE_1001_standing_arms_raised_stretch.webp",
             "双臂向上优雅舒展身体微提脚跟失重感，如水母水中浮游",
             "G_DYNAMIC", ["DYNAMIC", "WEIGHTLESS_FLOAT"], "鹿岛漫展组", "https://www.xiaohongshu.com/explore/66e01234000000001102aabb", "CANDIDATE")

    add_cand("CAND_215", "staging/eyra_cells/eyra_01_r0_c1.webp",
             "原地单腿后扬轻踢小腿身体微倾平衡动态，活泼生动",
             "G_DYNAMIC", ["DYNAMIC", "KICK_BALANCE"], "鬼城Eyra", "https://www.xiaohongshu.com/explore/69f1e5a000000000350390c1", "CANDIDATE")

    add_cand("CAND_216", "staging/eyra_cells/eyra_02_r1_c2.webp",
             "迈步向前单手甩道具在身侧微风扬发动态，单灯瞬间定格",
             "G_DYNAMIC", ["DYNAMIC", "FORWARD_STRIDE"], "鬼城Eyra", "https://www.xiaohongshu.com/explore/69f1e5a000000000350390c1", "CANDIDATE")

    add_cand("CAND_217", "staging/eyra_cells/eyra_03_r0_c2.webp",
             "单腿跨前重心下移预备迈步跨越动态，动作干净利落",
             "G_DYNAMIC", ["DYNAMIC", "STEP_LUNGE"], "鬼城Eyra", "https://www.xiaohongshu.com/explore/69f1e5a000000000350390c1", "CANDIDATE")

    add_cand("CAND_218", "staging/eyra_cells/eyra_04_r0_c1.webp",
             "侧向滑步单腿向侧方急速伸展动态，线条舒展流动",
             "G_DYNAMIC", ["DYNAMIC", "SLIDE_STEP"], "鬼城Eyra", "https://www.xiaohongshu.com/explore/69f1e5a000000000350390c1", "CANDIDATE")

    add_cand("CAND_219", "staging/eyra_cells/eyra_04_r2_c1.webp",
             "矮梯坐姿单腿凌空踢起向前踢踏动态，神采飞扬",
             "G_DYNAMIC", ["DYNAMIC", "LEG_KICK_SIT"], "鬼城Eyra", "https://www.xiaohongshu.com/explore/69f1e5a000000000350390c1", "CANDIDATE")

    add_cand("CAND_220", "staging/eyra_cells/eyra_06_r0_c1.webp",
             "侧身极速拔刀长刀挥出弧线瞬间定格，眼神锐利动势强",
             "G_DYNAMIC", ["DYNAMIC", "FAST_DRAW"], "鬼城Eyra", "https://www.xiaohongshu.com/explore/69f1e5a000000000350390c1", "CANDIDATE")

    add_cand("CAND_221", "staging/eyra_cells/eyra_06_r2_c0.webp",
             "原地半蹲急速出鞘剑指侧方衣角飞扬，静中带动的张力",
             "G_DYNAMIC", ["DYNAMIC", "SWORD_THRUST"], "鬼城Eyra", "https://www.xiaohongshu.com/explore/69f1e5a000000000350390c1", "CANDIDATE")

    add_cand("CAND_222", "staging/eyra_cells/eyra_07_r0_c1.webp",
             "矮凳坐姿双手舞棍旋转定格瞬间，衣袖翻飞具中国武侠美感",
             "G_DYNAMIC", ["DYNAMIC", "STAFF_SPIN"], "鬼城Eyra", "https://www.xiaohongshu.com/explore/69f1e5a000000000350390c1", "CANDIDATE")

    add_cand("CAND_223", "staging/eyra_cells/eyra_07_r2_c0.webp",
             "单腿微悬踢踏双手挥杖轻盈小幅动态，宛如水波轻摇",
             "G_DYNAMIC", ["DYNAMIC", "LIGHT_BOUNCE"], "鬼城Eyra", "https://www.xiaohongshu.com/explore/69f1e5a000000000350390c1", "CANDIDATE")

    add_cand("CAND_224", "staging/eyra_cells/eyra_08_r0_c0.webp",
             "矮凳坐姿单腿悬空甩动长靴，姿态灵动不僵硬",
             "G_DYNAMIC", ["DYNAMIC", "SWING_BOOT"], "鬼城Eyra", "https://www.xiaohongshu.com/explore/69f1e5a000000000350390c1", "CANDIDATE")

    add_cand("CAND_225", "staging/eyra_cells/eyra_08_r2_c1.webp",
             "漫展现场微风吹动双马尾长发飞舞定格瞬间，眼神定格",
             "G_DYNAMIC", ["DYNAMIC", "WIND_HAIR"], "鬼城Eyra", "https://www.xiaohongshu.com/explore/69f1e5a000000000350390c1", "CANDIDATE")

    add_cand("CAND_226", "staging/eyra_cells/eyra_09_r1_c0.webp",
             "双手挥双刃侧身翻转预备式，身体微跃腾空定格感",
             "G_DYNAMIC", ["DYNAMIC", "AIR_FREEZE"], "鬼城Eyra", "https://www.xiaohongshu.com/explore/69f1e5a000000000350390c1", "CANDIDATE")

    add_cand("CAND_227", "staging/eyra_cells/eyra_09_r1_c1.webp",
             "大步弓步向前冲刺瞬间定格，地面摩擦力拉满动感",
             "G_DYNAMIC", ["DYNAMIC", "SPRINT_LUNGE"], "鬼城Eyra", "https://www.xiaohongshu.com/explore/69f1e5a000000000350390c1", "CANDIDATE")

    add_cand("CAND_228", "staging/eyra_cells/eyra_10_r0_c0.webp",
             "单腿金鸡独立双手微晃保持平衡可爱动态，神态俏皮",
             "G_DYNAMIC", ["DYNAMIC", "ONE_LEG_BALANCE"], "鬼城Eyra", "https://www.xiaohongshu.com/explore/69f1e5a000000000350390c1", "CANDIDATE")

    add_cand("CAND_229", "staging/eyra_cells/eyra_10_r0_c1.webp",
             "矮梯坐姿单腿高抬悬空双手伸展，空中悬滞感",
             "G_DYNAMIC", ["DYNAMIC", "HIGH_LEG_SUSPEND"], "鬼城Eyra", "https://www.xiaohongshu.com/explore/69f1e5a000000000350390c1", "CANDIDATE")

    add_cand("CAND_230", "staging/eyra_cells/eyra_10_r1_c1.webp",
             "侧步迈出双手甩刀向后回旋，披风与发梢自然扬起",
             "G_DYNAMIC", ["DYNAMIC", "CAPE_FLICK"], "鬼城Eyra", "https://www.xiaohongshu.com/explore/69f1e5a000000000350390c1", "CANDIDATE")

    add_cand("CAND_231", "staging/eyra_cells/eyra_10_r1_c2.webp",
             "大步侧弓步双手拉开向外推掌动势，肢体大开大合",
             "G_DYNAMIC", ["DYNAMIC", "WIDE_PALM"], "鬼城Eyra", "https://www.xiaohongshu.com/explore/69f1e5a000000000350390c1", "CANDIDATE")

    add_cand("CAND_232", "staging/eyra_cells/eyra_10_r2_c0.webp",
             "原地慢步走动单手撩长发动态，步伐轻缓优雅",
             "G_DYNAMIC", ["DYNAMIC", "SLOW_WALK_HAIR"], "鬼城Eyra", "https://www.xiaohongshu.com/explore/69f1e5a000000000350390c1", "CANDIDATE")

    add_cand("CAND_233", "staging/eyra_cells/eyra_10_r2_c2.webp",
             "矮凳坐姿单腿高抬向前踢伸脚尖，下半身充满动感",
             "G_DYNAMIC", ["DYNAMIC", "FORWARD_KICK"], "鬼城Eyra", "https://www.xiaohongshu.com/explore/69f1e5a000000000350390c1", "CANDIDATE")

    add_cand("CAND_234", "staging/eyra_cells/eyra_11_r1_c0.webp",
             "转身大袍甩开长袖向外飘扬慢转定格，大袖水流感强烈",
             "G_DYNAMIC", ["DYNAMIC", "SLEEVE_WHIRL"], "鬼城Eyra", "https://www.xiaohongshu.com/explore/69f1e5a000000000350390c1", "CANDIDATE")

    add_cand("CAND_235", "staging/eyra_cells/eyra_12_r1_c2.webp",
             "原地单脚提踵跳跃微提膝单手后扬披风微扬，轻快失重动态",
             "G_DYNAMIC", ["DYNAMIC", "HOVER_HOP"], "鬼城Eyra", "https://www.xiaohongshu.com/explore/69f1e5a000000000350390c1", "CANDIDATE")

    # Write YAML
    with open(YAML_PATH, "w", encoding="utf-8") as f:
        yaml.dump(candidates, f, allow_unicode=True, sort_keys=False, width=120)

    print(f"\n========================================================")
    print(f"SUCCESS: Generated {len(candidates)} pose candidates!")
    print(f"YAML saved to: {YAML_PATH}")
    print(f"========================================================")

if __name__ == "__main__":
    build_all()
