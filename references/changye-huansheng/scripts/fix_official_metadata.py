import yaml
from pathlib import Path

ROOT = Path("references/changye-huansheng")
YAML_FILE = ROOT / "data" / "references.yaml"

with open(YAML_FILE, "r", encoding="utf-8") as f:
    items = yaml.safe_load(f)

for it in items:
    ref_id = it.get("id")
    if ref_id == "OFFICIAL_003":
        it["observed"] = [
            "官方3D提取资产：水母竖琴法杖（武器）的正视、侧视、后视及顶视三视图（1080x1472）。",
            "法杖顶端为半透明水母钟形伞盖与弧形晶体竖琴融合构型，琴身带冰晶折射质感，琴弦为5根笔直荧光弦。",
            "握杆为银蓝螺旋金属渐变，下端带海螺与晶锥配重。"
        ]
        it["notes"] = "官方3D资产武器竖琴法杖三视图，道具翻模与持握核心基准。"
    elif ref_id == "OFFICIAL_004":
        it["observed"] = [
            "官方3D提取资产：王昭君正面上半身特写立绘（1080x1472）。",
            "展现银白水母抹胸、腰部镂空流光材质、两侧透明泡泡袖与扇贝形波浪短裙摆上沿。",
            "头戴透明水母伞盖帽，两侧长发垂落，胸前佩戴AG战队红宝石核心与珊瑚软骨托架。"
        ]
        it["notes"] = "官方3D资产正面半身，抹胸、腰腹镂空与正面服饰立体结构最直接参照。"
    elif ref_id == "OFFICIAL_005":
        it["observed"] = [
            "官方3D提取资产：王昭君后背全头纱披肩半身特写（1080x1472）。",
            "展现水母帽顶自发光小水母触须、大面积半透明青绿薄纱下垂至后腰、以及透过薄纱隐现的深蓝星空露背裙。"
        ]
        it["notes"] = "官方3D资产背面全透光披肩与头纱层次，回眸与背面构图基准。"
    elif ref_id == "OFFICIAL_006":
        it["observed"] = [
            "官方3D提取资产：王昭君背面短发与披肩分层结构（1080x1472）。",
            "去除外层大面纱后的后脑假发层次，展现羽毛状/水母状剪裁发尾与后颈线条。"
        ]
        it["notes"] = "官方3D资产背面发型分层，假发修剪内层结构依据。"
    elif ref_id == "OFFICIAL_007":
        it["observed"] = [
            "官方3D提取资产：王昭君无假发遮挡的大露背与肩带结构（1080x1472）。",
            "清晰展现深V露背剪裁、交叉透明细肩带贴合走线、以及水母短裙摆后部波浪褶皱。"
        ]
        it["notes"] = "官方3D资产大露背与肩带隐形走线绝对依据，指导Coser背部穿戴与防走光。"
    elif ref_id == "OFFICIAL_008":
        it["observed"] = [
            "官方3D提取资产：王昭君全身正视角A-Pose标准立绘（1080x1080）。",
            "完整展现头冠、抹胸、短裙、双臂水母长飘带、修长双腿与渐变透明高跟鞋的全身体态比例。"
        ]
        it["notes"] = "官方3D资产全身正面A-Pose，漫展全身体态与比例最高基准。"
    elif ref_id == "OFFICIAL_009":
        it["observed"] = [
            "官方3D提取资产：王昭君前侧方45度半身立体视角（1080x1472）。",
            "展现胸部立体杯型、腰腹镂空侧面厚度、肩部半透泡泡袖与头纱向后自然飘散的立体空间关系。"
        ]
        it["notes"] = "官方3D资产侧前45度视角，指导半身侧角运镜与V100单灯侧光雕刻。"
    elif ref_id == "OFFICIAL_010":
        it["observed"] = [
            "官方3D提取资产：王昭君正侧方90度半身侧颜与胸腰线条（1080x1472）。",
            "清晰展现水母头冠倾角、侧面立挺下颌线、挺拔胸腰S曲线与薄纱向后飞掠的流线型。"
        ]
        it["notes"] = "官方3D资产90度正侧颜与脊柱S形体态，Shot 05与侧脸特写基准。"
    elif ref_id == "OFFICIAL_011":
        it["observed"] = [
            "官方3D提取资产：王昭君后侧方45度半透明披纱与拖尾层叠（1080x1472）。",
            "展现背部V字下沿、双层水母长拖尾向地面垂直垂落的透光渐变质感。"
        ]
        it["notes"] = "官方3D资产后侧45度拖尾与背部透光，回眸构图与高定质感参考。"
    elif ref_id == "OFFICIAL_012":
        it["observed"] = [
            "官方3D提取资产：王昭君后背骨架与折叠拖尾内部透视结构（1080x1472）。",
            "关闭半透明度后的工程结构图，标注'这张把后面的不透明度关了，好观察结构'，清晰展现骨架受力与折叠层数。"
        ]
        it["notes"] = "官方3D资产后背工程解剖图，服装工坊版型硬骨架制作依据。"
    elif ref_id == "OFFICIAL_013":
        it["observed"] = [
            "官方3D提取资产：王昭君正侧面90度全身立姿（1080x1080）。",
            "从头顶小水母到脚底高跟鞋的完整侧面全身投影，展现双腿笔直度、足尖下绷角度与长拖尾飘拂长度。"
        ]
        it["notes"] = "官方3D资产正侧面全身立姿，指导漫展全身侧立与足背绷紧线条。"

with open(YAML_FILE, "w", encoding="utf-8") as f:
    yaml.dump(items, f, allow_unicode=True, sort_keys=False, indent=2)

print("Official metadata corrected cleanly!")
