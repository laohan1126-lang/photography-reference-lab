import yaml
from pathlib import Path
from PIL import Image

ROOT = Path("references/changye-huansheng")
YAML_PATH = ROOT / "data/references.yaml"

with open(YAML_PATH, "r", encoding="utf-8") as f:
    refs = yaml.safe_load(f)

print(f"Loaded {len(refs)} references from {YAML_PATH}")

updated_refs = []
for r in refs:
    rid = r.get("id")
    cat = r.get("category")
    pri = r.get("priority")

    # Ensure review_status and field_pack_eligible
    if cat == "90_REJECTED":
        r["review_status"] = "REJECTED"
        r["field_pack_eligible"] = False
    else:
        r["review_status"] = "PRESELECTED"
        r["field_pack_eligible"] = False

    # Remove pseudo-precise scores if present or keep them neutral
    for sk in ["target_relevance", "aesthetic_value", "technical_value", "source_confidence"]:
        if sk in r:
            # keep as float in yaml for schema, but will not show in review UI
            pass

    # 1. Fix LIGHTING_004 -> move to BTS_005
    if rid == "LIGHTING_004":
        r["id"] = "BTS_005"
        r["category"] = "07_BTS_TECHNICAL"
        r["file"] = "refs/07_BTS_TECHNICAL/BTS_005_folded_light_stands_hardware.webp"
        r["priority"] = "SUPPORT"
        r["review_status"] = "PRESELECTED"
        r["field_pack_eligible"] = False
        r["reference_roles"] = ["LIGHT_STAND_SELECTION", "HARDWARE_PORTABILITY"]
        r["source"] = {
            "url": "https://www.xiaohongshu.com/explore/68e8f98e0000000007002896",
            "page_title": "漫展便携灯位与器材分享",
            "author": "猫又来喽",
            "platform": "小红书",
            "source_type": "EXPO_EQUIPMENT_BTS",
            "verified": True
        }
        r["image_quality"] = {
            "width": 1080,
            "height": 1440,
            "source_quality": "HQ_DOWNLOAD",
            "quality_pass": True
        }
        r["visual_audit"] = {
            "actual_pose": "非人物姿态；画面为四支不同规格便携反折灯架（黑/紫/金圈）收折平放于展馆水泥地对比",
            "filename_match": "YES",
            "metadata_match": "YES",
            "director_script_match": "YES",
            "visually_verified": True
        }
        r["technical_observation"] = "四支不同规格的便携反折灯架（黑色、金圈、紫圈）折叠平放于展馆水泥地面上，展示不同管径与折叠收纳长度对比。"
        r["source_claim"] = "原作者漫展器材收纳笔记，分享自用轻量反折灯架配置，未声明现场布光参数。"
        r["context"] = "大型漫展单人出勤轻量灯架选型与现场收纳尺寸参考。"
        r["possible_application"] = "单人摄影师在评估 Godox V100 及圆形柔光箱承重时，对比轻量反折灯架的收纳体积与展开抗倾倒能力。"
        # Remove pose directing fields
        for field in ["director_script", "model_setup", "camera_position", "recommended_lens", "crop", "micro_adjustments", "common_failures"]:
            r.pop(field, None)

    # 2. Fix BTS_004
    elif rid == "BTS_004":
        r["technical_observation"] = "大型漫展空旷展厅内多组不同摄影师布置的柔光箱与灯架实拍，图中手写粉色字母标注了 A、B、C、D 四个点位/区域。"
        r["source_claim"] = "原作者展示展馆现场各拍摄点位与柔光设备分布空间，未提供毫米级布光尺寸或现场测光数值。"
        r["context"] = "大型漫展空旷区域实地设备架设环境与多组摄影师之间的安全间距参考。"
        r["possible_application"] = "了解漫展现场灯架占地面积、柔光箱开角以及与其他拍摄者之间的间距，避免人流碰撞打翻灯架。"
        # Remove fabricated parameters & director fields
        for field in ["director_script", "model_setup", "camera_position", "recommended_lens", "crop", "micro_adjustments", "common_failures"]:
            r.pop(field, None)

    # 3. Fix LIGHTING_003
    elif rid == "LIGHTING_003":
        r["lighting_observation"] = "暗色展馆背景中，人物面部与前胸受前侧方较柔和的光源照亮，背部与头发轮廓有边缘光勾勒，背景展馆顶灯形成圆形散景。"
        r["source_claim"] = "来自原作者文字：使用漫展单灯配合柔光附件拍摄；图片本身仅为成片视觉效果，无现场光路布设照片。"
        r["lighting_inference"] = "通过压暗展馆环境曝光（低ISO、较快快门），配合单灯离机闪光照亮人物，可将主体从昏暗背景中剥离，形成油画质感。"
        r["possible_application"] = "王昭君深海神女角色在暗调展区利用 Godox V100 加圆形柔光附件压暗背景、雕刻面部与服饰质感时可借鉴此光比。"
        # Remove pose directing fields
        for field in ["director_script", "model_setup", "camera_position", "recommended_lens", "crop", "micro_adjustments", "common_failures"]:
            r.pop(field, None)

    # 4. Remove director_script from all other non-pose references
    elif cat != "03_POSE":
        for field in ["director_script", "model_setup", "camera_position", "recommended_lens", "crop", "micro_adjustments", "common_failures"]:
            r.pop(field, None)

    # 5. Fix 00_OFFICIAL: remove expo_feasibility
    if cat == "00_OFFICIAL":
        r.pop("expo_feasibility", None)
        r.pop("director_script", None)
        if "character_anchor" not in r:
            r["character_anchor"] = r.get("observed", ["官方三视图与角色锚点"])[0]

    # 6. For 03_POSE: retain director_script only for documentation, but mark review_status: PRESELECTED
    if cat == "03_POSE":
        r["review_status"] = "PRESELECTED"
        r["field_pack_eligible"] = False

    updated_refs.append(r)

with open(YAML_PATH, "w", encoding="utf-8") as f:
    yaml.dump(updated_refs, f, allow_unicode=True, sort_keys=False, width=120)

print(f"Successfully cleaned and updated {len(updated_refs)} references in {YAML_PATH}")
