import yaml
import shutil
from pathlib import Path

ROOT = Path("references/changye-huansheng")
YAML_FILE = ROOT / "data" / "references.yaml"

with open(YAML_FILE, "r", encoding="utf-8") as f:
    items = yaml.safe_load(f)

# 1. Physical file relocation
# Move POSE_003 to 90_REJECTED
pose_003_src = ROOT / "refs" / "03_POSE" / "POSE_003_cool_expression_upward.webp"
pose_003_dst = ROOT / "refs" / "90_REJECTED" / "REJECT_003_nikke_liberelio_quadruped_kneel.webp"
if pose_003_src.exists():
    shutil.move(str(pose_003_src), str(pose_003_dst))
    print("Moved POSE_003 to 90_REJECTED")

# Move POSE_001 to 03_POSE/02_STOOL_SEATED
pose_001_src = ROOT / "refs" / "03_POSE" / "POSE_001_jellyfish_body_curve.webp"
pose_001_dst = ROOT / "refs" / "03_POSE" / "02_STOOL_SEATED" / "POSE_001_jk_bathtub_kneel.webp"
if pose_001_src.exists():
    shutil.move(str(pose_001_src), str(pose_001_dst))
    print("Moved POSE_001 to 03_POSE/02_STOOL_SEATED")

# Move POSE_002 to 03_POSE/02_STOOL_SEATED
pose_002_src = ROOT / "refs" / "03_POSE" / "POSE_002_holding_jellyfish.webp"
pose_002_dst = ROOT / "refs" / "03_POSE" / "02_STOOL_SEATED" / "POSE_002_seated_chin_gesture.webp"
if pose_002_src.exists():
    shutil.move(str(pose_002_src), str(pose_002_dst))
    print("Moved POSE_002 to 03_POSE/02_STOOL_SEATED")

# Move POSE_004 to 03_POSE/08_LOW_ANGLE
pose_004_src = ROOT / "refs" / "03_POSE" / "POSE_004_weightless_floating_arch.webp"
pose_004_dst = ROOT / "refs" / "03_POSE" / "08_LOW_ANGLE" / "POSE_004_underwater_column_floating.webp"
if pose_004_src.exists():
    shutil.move(str(pose_004_src), str(pose_004_dst))
    print("Moved POSE_004 to 03_POSE/08_LOW_ANGLE")

# 2. Update metadata in items
for it in items:
    # Ensure default expo_feasibility
    if "expo_feasibility" not in it:
        if it["category"] == "00_OFFICIAL":
            it["expo_feasibility"] = "A"
        elif it["category"] == "90_REJECTED":
            it["expo_feasibility"] = "D"
        elif it["category"] in ["04_LIGHTING", "05_SET_PROP", "07_BTS_TECHNICAL"]:
            it["expo_feasibility"] = "D"
        else:
            it["expo_feasibility"] = "B"

    # Specific audits
    if it["id"] == "POSE_001":
        it["file"] = "refs/03_POSE/02_STOOL_SEATED/POSE_001_jk_bathtub_kneel.webp"
        it["priority"] = "STUDIO_OPTIONAL"
        it["expo_feasibility"] = "D"
        it["model_setup"] = "floor_kneel"
        it["camera_position"] = "front-high 30°"
        it["recommended_lens"] = "50mm f/1.8"
        it["crop"] = "3/4"
        it["director_script"] = "（漫展不推荐执行本动作，需下跪且需大型浴缸道具）"
        it["micro_adjustments"] = ["双膝并拢跪地", "双手微提裙角", "下巴轻收"]
        it["common_failures"] = ["漫展地面脏乱无法下跪", "提裙幅度过大走光", "与王昭君神女气质不符"]
        it["observed"] = [
            "实拍图显示模特身着水手服跪于蓝色影棚内的白色浴缸前，双手提裙角。",
            "背景包含大型白色浴缸与蓝色花海造景。",
            "并非王昭君长夜焕生服装，姿势为影棚日系萌系下跪提裙。"
        ]
        it["inferred"] = [
            "该动作高度依赖干净的地面或大型道具，漫展人流密集环境下极难实施且易弄脏Coser裙子。"
        ]
        it["proposed"] = [
            "归入 STUDIO_OPTIONAL，漫展现场禁止要求 Coser 跪地，转译为小马扎端坐微提裙角。"
        ]
        it["do_not_copy"] = [
            "严禁在漫展地面要求跪地动作",
            "严禁水手服萌系提裙动作"
        ]

    elif it["id"] == "POSE_002":
        it["file"] = "refs/03_POSE/02_STOOL_SEATED/POSE_002_seated_chin_gesture.webp"
        it["priority"] = "SUPPORT"
        it["expo_feasibility"] = "B"
        it["model_setup"] = "stool"
        it["camera_position"] = "front-right 20°, eye level"
        it["recommended_lens"] = "50mm f/1.8 或 24-240 @ 50–70mm"
        it["crop"] = "full body / 3/4"
        it["director_script"] = "侧身坐小马扎上，右腿往前伸一点，脚尖点地绷直。右手轻轻抬起来放在下巴右侧，不要真托住脸，两指微触即可。眼神看我镜头偏右上方一点，别直瞪镜头，表情放柔和。"
        it["micro_adjustments"] = [
            "双腿不要平行并拢，靠近镜头的一条腿往前伸展拉长线条",
            "手指触下巴要轻，绝不要用力挤压面部肌肉导致肉被压变形",
            "挺胸立腰，不要因坐着而弓背"
        ]
        it["common_failures"] = [
            "坐姿放松导致腹部衣褶堆叠",
            "用力托脸导致脸颊变形",
            "双腿垂直90度坐立显得呆板腿短"
        ]
        it["observed"] = [
            "实拍图显示模特侧坐于白色浴缸边缘，双腿自然倾斜下垂，右手手指轻触下颌，头部微侧。",
            "上方悬挂巨型水母装置，背景为纯蓝影棚布光。"
        ]
        it["inferred"] = [
            "去除去除浴缸和水母吊顶后，此坐姿与手指抚颊手势可在漫展使用折叠小马扎 100% 复刻。"
        ]
        it["proposed"] = [
            "作为漫展坐姿核心方案（POSE_STOOL），用于缓解 Coser 站立疲劳，同时快速出片。"
        ]
        it["do_not_copy"] = [
            "不可要求漫展有浴缸置景与吊挂水母",
            "不要照搬JK水手服配饰"
        ]

    elif it["id"] == "POSE_003":
        it["id"] = "REJECT_003"
        it["file"] = "refs/90_REJECTED/REJECT_003_nikke_liberelio_quadruped_kneel.webp"
        it["category"] = "90_REJECTED"
        it["priority"] = "REJECT"
        it["expo_feasibility"] = "D"
        it["observed"] = [
            "实拍图为《胜利女神：妮姬》角色莉贝雷利奥（Liberelio）的Cosplay。",
            "模特身穿紧身连体衣，四肢着地（双膝跪地、双手撑地）趴在白色地面上，身体前倾昂首，重点展示胸部与紧身衣。",
            "动作带有强烈性暗示和二次元肉感风格。"
        ]
        it["inferred"] = [
            "该动作无论在角色设定还是场景执行上均严重脱离《王者荣耀》王昭君长夜焕生的庄严神性、悲悯与灵动特质。",
            "在漫展公共场合趴在地上撑地极为不雅、地面污脏、且极易招致围观拥堵。"
        ]
        it["proposed"] = [
            "彻底移入 90_REJECTED 废弃库，作为严禁模仿的反面教材！"
        ]
        it["do_not_copy"] = [
            "严禁模仿四肢着地爬行姿态",
            "严禁引入妮姬角色要素与胸前大面积低俗露肉构图"
        ]
        it["notes"] = "审计发现图文严重不符，实为妮姬莉贝雷利奥趴地姿态，已正式降级废弃。"

    elif it["id"] == "POSE_004":
        it["file"] = "refs/03_POSE/08_LOW_ANGLE/POSE_004_underwater_column_floating.webp"
        it["priority"] = "STUDIO_OPTIONAL"
        it["expo_feasibility"] = "D"
        it["model_setup"] = "underwater_pool"
        it["camera_position"] = "underwater low angle"
        it["recommended_lens"] = "50mm f/1.8"
        it["crop"] = "full body"
        it["director_script"] = "（漫展不可执行，真水下摄影棚限定）"
        it["micro_adjustments"] = ["水下闭气", "四肢失重舒展", "脚尖下绷"]
        it["common_failures"] = ["漫展完全无水下条件", "陆地无法实现头发真实360度水下浮动"]
        it["observed"] = [
            "实拍图为真水下摄影，模特身穿白色Lolita裙坐于水下罗马柱上，发丝在水中完全失重向上漂浮，闭目敛神，双手微扬。"
        ]
        it["inferred"] = [
            "该图具有极高水下失重动势艺术参考价值，但 100% 依赖专业潜水恒温摄影池，漫展现场物理不可行。"
        ]
        it["proposed"] = [
            "移入 STUDIO_OPTIONAL 艺术参考库，漫展现场仅作为后期 AI 背景扩展和姿态舒展的视觉灵感。"
        ]
        it["do_not_copy"] = [
            "切勿在漫展现场尝试水下浮动发型动作"
        ]

    # Relocate multi-light studio references to STUDIO_OPTIONAL
    elif it["id"] in ["LIGHTING_001", "LIGHTING_002", "PROP_001", "BTS_001", "BTS_002", "BTS_003"]:
        it["priority"] = "STUDIO_OPTIONAL"
        it["expo_feasibility"] = "D"

with open(YAML_FILE, "w", encoding="utf-8") as f:
    yaml.dump(items, f, allow_unicode=True, sort_keys=False, indent=2)

print("Updated references.yaml successfully!")
