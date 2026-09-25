#!/usr/bin/env python3
"""Organize user-selected 47 pose candidates into a curated dataset and visual board."""

import html
import json
import math
import shutil
from pathlib import Path
from PIL import Image, ImageDraw, ImageFont
import yaml

ROOT = Path(__file__).resolve().parents[1]
DECISIONS_FILE = ROOT / "data/live_pose_decisions.json"
MANIFEST_FILE = ROOT / "staging/live_manifest.json"
CURATED_DIR = ROOT / "curated_candidates"
OUTPUT_YAML = ROOT / "data/selected_candidates.yaml"
OUTPUT_HTML = ROOT / "dist/curated_selection_board.html"
SHEETS_DIR = ROOT / "dist/curated_contact_sheets"

CURATED_DIR.mkdir(parents=True, exist_ok=True)
SHEETS_DIR.mkdir(parents=True, exist_ok=True)

DIRECTION_META = {
    "A_STANDING": {
        "name": "A 基础立姿 (Standing)",
        "code": "A",
        "role": "长夜昭君冷冽神女正立态，展现袍服修长剪影与垂直仪态",
        "key_points": "沉肩立颈、重心单足微侧移、目光平视或微微下睨、双手自然交叠或微垂"
    },
    "B_TURN_BACK": {
        "name": "B 回眸/背身 (Turn Back)",
        "code": "B",
        "role": "展示披风刺绣、背身冰晶饰物与侧颈孤清线条",
        "key_points": "背对或大侧身对镜头、转头回眸、目光越肩看向摄影师、披风自然垂坠留白"
    },
    "C_HANDS_FACE": {
        "name": "C 情绪/手部特写 (Hands & Face)",
        "code": "C",
        "role": "冰雪孤傲感手势，抚面、敛容、托腮或轻触轻纱",
        "key_points": "指尖松弛虚搭、不挤压面颊软组织、眼神微聚或半垂眸、强调睫毛与面部受光"
    },
    "D_LOW_STOOL": {
        "name": "D 矮凳/坐姿 (Low Stool)",
        "code": "D",
        "role": "漫展现场减缓 Coser 体力消耗的高贵静坐态，收拢裙摆",
        "key_points": "浅坐凳沿前半段、挺直腰背不塌陷、裙摆顺势在地面自然铺展、法杖侧立地面"
    },
    "E_PROP": {
        "name": "E 法杖/道具交互 (Prop & Staff)",
        "code": "E",
        "role": "昭君权杖核心互动，双手擎杖、单手握杖下顿或横杖蓄势",
        "key_points": "杖顶冰晶朝向受光面、握杖手虎口留空不僵硬、前手导向与后手支撑平衡"
    },
    "F_LOW_ANGLE": {
        "name": "F 广角低机位 (Low Angle)",
        "code": "F",
        "role": "神性压迫感与身材拉长视角，避开漫展现场杂乱人头背景",
        "key_points": "摄影机机位贴地仰拍、广角透视延伸下身线条、头部置于安全画幅中上部防止畸变"
    },
    "G_DYNAMIC": {
        "name": "G 动态/披风甩动 (Dynamic & Fabric)",
        "code": "G",
        "role": "长夜破晓风动动势，披风甩动与转身动感捕捉",
        "key_points": "单手或风机带起斗篷下摆、定点半转身回旋、连拍捕捉布料飘扬最高点"
    }
}

# Accurate observed action notes for the selected 47 candidates
POSE_OBSERVATIONS = {
    # A_STANDING
    "LIVE_A_STANDING_7666289_2": ("正面微侧立姿，双手自然叠放身前，浅色纱裙垂坠，眼神沉静微冷", "冷冽仪态标准全身卡"),
    "LIVE_A_STANDING_7666300_3": ("全身直立微仰，单手微抬引颈，裙摆纵向线条挺拔，圣洁神态", "高冷神性全身全身照"),
    "LIVE_A_STANDING_7666311_4": ("大半身立姿，右手扶肩/领口，身体微呈S弧线，温婉而端庄", "上半身半景仪态参考"),
    "LIVE_A_STANDING_7666322_5": ("中远景立姿，双臂微微张开垂落两侧，纱摆蓬松，体态轻盈冷寂", "全身剪影与裙摆张力"),
    "LIVE_A_STANDING_7666349_7": ("侧身45度静立，面部转正，单手垂落微提裙角，层次分明", "侧身线条与服装侧面展示"),
    "LIVE_A_STANDING_7666359_8": ("全景正面立姿，双臂自然下垂略带张度，纯净神性背景感", "核心基准全身构图"),
    "LIVE_A_STANDING_7676289_1": ("经典礼服端庄站姿，一手屈肘微收于腰侧，身形挺立修长", "腰线展示与挺拔仪态"),
    "LIVE_A_STANDING_7687070_2": ("日系唯美站姿，重心移至后足，肩颈微倾，柔和且内敛", "漫展现场易出片自然站姿"),
    "LIVE_A_STANDING_7687088_3": ("修长全身立姿，头微昂，下颌线分明，披风由双肩垂落至地面", "昭君高傲气场全身立像"),
    "LIVE_A_STANDING_7687140_6": ("3/4侧立微转体，手轻按腹前腰节，发丝顺垂于前胸", "胸腹线条与前发整理参考"),
    "LIVE_A_STANDING_7687157_7": ("挺拔立姿微俯视镜头，双手下垂相扣，气场沉稳内敛", "神女审视感正位立姿"),

    # B_TURN_BACK
    "LIVE_B_TURN_BACK_7696528_2": ("半侧身回头过肩，下巴微敛，目光精准直视镜头，肩背线条极美", "经典回眸特写/中景"),
    "LIVE_B_TURN_BACK_7722465_2": ("大角度转体回头，身体背向，头部转过约90度，发丝甩动", "转身动感瞬间捕捉"),
    "LIVE_B_TURN_BACK_7722494_4": ("静止背身回眸，单手轻抬护于肩后，披风大面积背身留白", "背部冰晶与斗篷细节展示"),
    "LIVE_B_TURN_BACK_7722509_5": ("侧背立姿，头部微扬越肩下视，带冷漠审视情绪", "孤傲疏离感越肩构图"),
    "LIVE_B_TURN_BACK_7733490_1": ("柔和侧回眸，身体自然前倾，眼神幽深带有叙事感", "情绪向背身回头"),
    "LIVE_B_TURN_BACK_7733516_3": ("高机位俯瞰背身回首，发丝与长裙在地面铺展", "俯拍视角回眸参考"),
    "LIVE_B_TURN_BACK_7733526_4": ("大幅度回眸，肩头微耸锁骨清晰，回望眼神专注清澈", "肩部特写与面部高光"),
    "LIVE_B_TURN_BACK_7733575_8": ("正背身站立，头部大幅度侧转，突出身后披风整体轮廓", "全身背影与披风剪影"),

    # C_HANDS_FACE
    "LIVE_C_HANDS_FACE_7743758_6": ("单手轻抚面纱/颊侧，指尖虚点唇边，眼神空灵微怅", "面纱与指尖情绪特写"),
    "LIVE_C_HANDS_FACE_7761958_6": ("双手环抱于胸前上方靠近下颌，指节柔美修长，微闭目或垂眸", "祈祷与沉思神态"),
    "LIVE_C_HANDS_FACE_7772054_3": ("单手托腮/抚颊，手腕柔和折角，眼神直视微冷", "昭君孤寂感面部特写"),
    "LIVE_C_HANDS_FACE_7772078_5": ("双手轻掩心口，指尖放松微曲，带哀怜与觉醒之态", "长夜破晓前的心绪抒发"),
    "LIVE_C_HANDS_FACE_7772091_6": ("指尖微触眼下或耳际，微侧头，突出眼妆与冰雪睫毛", "眼部妆容与高光近景"),

    # D_LOW_STOOL
    "LIVE_D_LOW_STOOL_7814881_6": ("浅坐矮凳微侧身，双膝并拢斜放，双手交叠置于膝上，腰背挺直", "漫展现场休息且保持高雅的坐姿"),

    # E_PROP
    "LIVE_E_PROP_7621285_6": ("双手持法杖立于身前，法杖垂直立地，身体端立如卫", "法杖持握标准防御/立态"),
    "LIVE_E_PROP_7631371_1": ("单手高握法杖上段，另一手微提裙摆，法杖向前微倾", "权杖威仪向神明姿势"),
    "LIVE_E_PROP_7631386_2": ("特写法杖顶部交互，手握权杖权柄，眼神落在权杖核心", "法杖道具近景特写"),
    "LIVE_E_PROP_7641145_1": ("法杖横置于胸腹前，双手交错握持，蓄势待发感", "横杖构图与破除长夜动势"),
    "LIVE_E_PROP_7641160_2": ("单手持杖侧立，法杖斜插身侧地面，体态轻盈优雅", "侧向持杖全身构图"),
    "LIVE_E_PROP_7641184_4": ("双手托抱法杖于胸前，微低头闭目，仿佛与法杖共鸣", "神力注入与圣洁祈愿姿"),
    "LIVE_E_PROP_7641203_5": ("单手后引法杖，身体前倾，法杖形成强劲对角线延伸", "破除冰封的突刺蓄力动势"),
    "LIVE_E_PROP_7641233_7": ("双手撑于杖首上方，下巴轻搭手背或微倚法杖", "静止休憩持杖姿态"),

    # F_LOW_ANGLE
    "LIVE_F_LOW_ANGLE_7844675_2": ("贴地仰拍全身立姿，裙摆向四方延展，身材比例拉长极具气场", "广角气场拉长神作"),
    "LIVE_F_LOW_ANGLE_7844688_3": ("低角度半身仰视，下颌微抬，俯视众生神性傲然", "避开漫展人流的神女俯视视角"),
    "LIVE_F_LOW_ANGLE_7844730_6": ("低机位斜角仰拍，身形与建筑/立柱线条呼应", "透视纵深与垂直张力"),
    "LIVE_F_LOW_ANGLE_7857426_2": ("广角超低机位大仰拍，脚部向前延伸，气场霸气全开", "昭君觉醒威严压迫感"),
    "LIVE_F_LOW_ANGLE_7857438_3": ("仰拍全身微侧，披风在身后垂向地面，画面干净纯粹", "干净背景全身大片视角"),
    "LIVE_F_LOW_ANGLE_7857451_4": ("低角度持杖仰拍，法杖自下而上刺向天空，构图冲力极强", "权杖与低机位完美结合"),
    "LIVE_F_LOW_ANGLE_7857467_5": ("超广角低位半身回眸仰拍，动态与透视兼备", "仰角回眸绝美透视"),
    "LIVE_F_LOW_ANGLE_7857477_6": ("低机位正位挺拔立像，光线从后方勾勒神圣轮廓光", "逆光/轮廓光低角度立像"),
    "LIVE_F_LOW_ANGLE_7857491_7": ("广角低位微仰，单臂高扬，斗篷顺风张开覆盖大半画幅", "覆盖画面的广角大冲击力"),

    # G_DYNAMIC
    "LIVE_G_DYNAMIC_7867902_2": ("转身瞬间裙摆离地飞扬，形成优美弧形水花感，身姿灵动", "大裙摆定点旋风动势"),
    "LIVE_G_DYNAMIC_7867941_4": ("疾步微跃或急停，斗篷向侧后方高高扬起，破风感极强", "长夜破晓破风动势"),
    "LIVE_G_DYNAMIC_7898913_4": ("单手甩动长披风，布料在半空形成波浪褶皱，视觉焦点突出", "甩斗篷经典漫展连拍动作"),
    "LIVE_G_DYNAMIC_7898954_7": ("侧向大幅度转体，长发与布料呈对角线流向展开", "发丝与布料联动飘动"),
    "LIVE_G_DYNAMIC_7898964_8": ("正向双手带起斗篷两角，如翼展翅，气势恢宏壮阔", "神女展翼般浩瀚气场")
}

def main():
    with open(DECISIONS_FILE, "r", encoding="utf-8") as f:
        decisions_data = json.load(f)
    with open(MANIFEST_FILE, "r", encoding="utf-8") as f:
        manifest_list = json.load(f)

    man_map = {x["id"]: x for x in manifest_list}
    keep_ids = decisions_data.get("keep_ids", [])
    print(f"Total keep ids to organize: {len(keep_ids)}")

    # Group by direction
    dir_groups = {}
    for kid in keep_ids:
        item = man_map.get(kid)
        if not item:
            print(f"Warning: {kid} not in manifest!")
            continue
        d = item.get("direction", "UNKNOWN")
        dir_groups.setdefault(d, []).append((kid, item))

    # Sort each direction group
    curated_records = []
    card_html_list = []

    # Direction ordering
    dir_order = ["A_STANDING", "B_TURN_BACK", "C_HANDS_FACE", "D_LOW_STOOL", "E_PROP", "F_LOW_ANGLE", "G_DYNAMIC"]

    for d in dir_order:
        items = dir_groups.get(d, [])
        items.sort(key=lambda x: x[0]) # sort by original ID
        d_meta = DIRECTION_META.get(d, {"name": d, "code": "X", "role": "", "key_points": ""})
        code = d_meta["code"]

        sub_curated_dir = CURATED_DIR / d
        sub_curated_dir.mkdir(parents=True, exist_ok=True)

        for idx, (kid, it) in enumerate(items, 1):
            sel_id = f"SEL_{code}_{idx:02d}"
            orig_src = ROOT / it["file"]
            dest_filename = f"{sel_id}.jpg"
            dest_file = sub_curated_dir / dest_filename

            # Copy file
            if orig_src.exists():
                shutil.copy2(orig_src, dest_file)

            # Get image dimensions
            w = it.get("width", 0)
            h = it.get("height", 0)

            obs_info = POSE_OBSERVATIONS.get(kid, ("单人高清写真姿势", "适合漫展实拍参考"))
            obs_pose = obs_info[0]
            suitability = obs_info[1]

            rel_curated_path = f"curated_candidates/{d}/{dest_filename}"

            record = {
                "selected_id": sel_id,
                "source_id": kid,
                "direction": d,
                "direction_name": d_meta["name"],
                "file": rel_curated_path,
                "width": w,
                "height": h,
                "aspect_ratio": f"{w}:{h}",
                "observed_pose": obs_pose,
                "suitability": suitability,
                "query": it.get("query", ""),
                "source_url": it.get("url", ""),
                "pin_href": it.get("pin_href", "")
            }
            curated_records.append(record)

            # Build HTML Card
            web_img = f"../{rel_curated_path}"
            card_html = f"""
            <div class="card" data-direction="{d}" data-id="{sel_id}">
                <div class="card-img-wrap" onclick="viewLightbox('{web_img}', '{sel_id}', '{obs_pose}', '{suitability}', '{w}×{h}')">
                    <img src="{web_img}" alt="{sel_id}" loading="lazy">
                    <span class="badge-sel-id">{sel_id}</span>
                    <span class="badge-res">{w}×{h}</span>
                </div>
                <div class="card-body">
                    <div class="dir-pill">{d_meta['name']}</div>
                    <div class="pose-desc">{html.escape(obs_pose)}</div>
                    <div class="suitability-box">
                        <span class="suitability-label">💡 实战价值:</span> {html.escape(suitability)}
                    </div>
                    <div class="meta-footer">
                        <span class="src-id">源: {kid}</span>
                        <a href="{web_img}" target="_blank" class="view-link">查看大图</a>
                    </div>
                </div>
            </div>
            """
            card_html_list.append(card_html)

    # Write YAML
    with open(OUTPUT_YAML, "w", encoding="utf-8") as f:
        yaml.dump(curated_records, f, allow_unicode=True, sort_keys=False)
    print(f"Saved {len(curated_records)} records to {OUTPUT_YAML}")

    # Build Interactive HTML
    tabs_html = ['<button class="tab active" onclick="filterCat(\'ALL\', this)">全部已选 ALL (47)</button>']
    for d in dir_order:
        cnt = len(dir_groups.get(d, []))
        d_meta = DIRECTION_META.get(d, {})
        tabs_html.append(f'<button class="tab" onclick="filterCat(\'{d}\', this)">{d_meta.get("code")}. {d_meta.get("name").split()[1]} ({cnt})</button>')

    full_html = f"""<!DOCTYPE html>
<html lang="zh-CN">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>《王昭君·长夜焕生》精选 47 张高清单人姿势库 (Curated Pose References)</title>
    <style>
        :root {{
            --bg: #07090e;
            --surface: #0f141f;
            --surface-card: #141b2a;
            --primary: #00f2ff;
            --primary-glow: rgba(0, 242, 255, 0.25);
            --accent: #38bdf8;
            --text-main: #f8fafc;
            --text-dim: #94a3b8;
            --border: #1e293b;
            --border-hover: #0284c7;
        }}
        * {{ box-sizing: border-box; margin: 0; padding: 0; }}
        body {{
            background: var(--bg);
            color: var(--text-main);
            font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, "PingFang SC", "Microsoft YaHei", sans-serif;
            min-height: 100vh;
        }}
        header {{
            background: var(--surface);
            border-bottom: 1px solid var(--border);
            padding: 20px 32px;
            position: sticky;
            top: 0;
            z-index: 100;
            display: flex;
            justify-content: space-between;
            align-items: center;
            flex-wrap: wrap;
            gap: 16px;
        }}
        .header-title h1 {{
            font-size: 22px;
            font-weight: 800;
            color: var(--primary);
            letter-spacing: 0.5px;
            display: flex;
            align-items: center;
            gap: 10px;
        }}
        .header-title p {{
            font-size: 13px;
            color: var(--text-dim);
            margin-top: 6px;
            line-height: 1.4;
        }}
        .stats-group {{
            display: flex;
            align-items: center;
            gap: 12px;
            background: #090d14;
            padding: 8px 16px;
            border-radius: 8px;
            border: 1px solid var(--border);
            font-size: 13px;
        }}
        .stats-highlight {{
            color: var(--primary);
            font-weight: 700;
        }}
        .nav-tabs {{
            background: #0b0f17;
            border-bottom: 1px solid var(--border);
            padding: 12px 32px;
            display: flex;
            gap: 10px;
            overflow-x: auto;
            white-space: nowrap;
        }}
        .tab {{
            background: transparent;
            border: 1px solid var(--border);
            color: var(--text-dim);
            padding: 7px 16px;
            border-radius: 20px;
            font-size: 13px;
            font-weight: 600;
            cursor: pointer;
            transition: all 0.2s;
        }}
        .tab:hover {{
            background: var(--surface);
            color: #fff;
            border-color: #38bdf8;
        }}
        .tab.active {{
            background: linear-gradient(135deg, #00f2ff, #0284c7);
            color: #000;
            border-color: var(--primary);
            box-shadow: 0 0 14px var(--primary-glow);
        }}
        .container {{
            padding: 32px;
            display: grid;
            grid-template-columns: repeat(auto-fill, minmax(280px, 1fr));
            gap: 24px;
        }}
        .card {{
            background: var(--surface-card);
            border: 1px solid var(--border);
            border-radius: 12px;
            overflow: hidden;
            display: flex;
            flex-direction: column;
            transition: all 0.25s ease;
        }}
        .card:hover {{
            border-color: var(--border-hover);
            transform: translateY(-4px);
            box-shadow: 0 12px 28px rgba(0, 0, 0, 0.6);
        }}
        .card-img-wrap {{
            width: 100%;
            height: 380px;
            background: #000;
            position: relative;
            cursor: pointer;
            overflow: hidden;
        }}
        .card-img-wrap img {{
            width: 100%;
            height: 100%;
            object-fit: cover;
            transition: transform 0.35s cubic-bezier(0.2, 0.8, 0.2, 1);
        }}
        .card-img-wrap:hover img {{
            transform: scale(1.05);
        }}
        .badge-sel-id {{
            position: absolute;
            top: 10px;
            left: 10px;
            background: rgba(0, 0, 0, 0.85);
            border: 1px solid var(--primary);
            color: var(--primary);
            padding: 3px 10px;
            border-radius: 6px;
            font-size: 12px;
            font-weight: 800;
            letter-spacing: 0.5px;
        }}
        .badge-res {{
            position: absolute;
            top: 10px;
            right: 10px;
            background: rgba(0, 0, 0, 0.75);
            border: 1px solid rgba(255, 255, 255, 0.2);
            color: #cbd5e1;
            padding: 3px 8px;
            border-radius: 6px;
            font-size: 11px;
            font-weight: 600;
        }}
        .card-body {{
            padding: 16px;
            display: flex;
            flex-direction: column;
            gap: 10px;
            flex: 1;
        }}
        .dir-pill {{
            font-size: 12px;
            font-weight: 700;
            color: var(--primary);
            text-transform: uppercase;
            letter-spacing: 0.5px;
        }}
        .pose-desc {{
            font-size: 13.5px;
            font-weight: 600;
            line-height: 1.45;
            color: #f1f5f9;
        }}
        .suitability-box {{
            background: rgba(0, 242, 255, 0.05);
            border-left: 3px solid var(--primary);
            padding: 8px 12px;
            border-radius: 4px;
            font-size: 12.5px;
            color: #cbd5e1;
            line-height: 1.4;
        }}
        .suitability-label {{
            font-weight: 700;
            color: var(--accent);
        }}
        .meta-footer {{
            margin-top: auto;
            padding-top: 10px;
            border-top: 1px solid rgba(255, 255, 255, 0.06);
            display: flex;
            justify-content: space-between;
            align-items: center;
            font-size: 11.5px;
            color: var(--text-dim);
        }}
        .view-link {{
            color: var(--accent);
            text-decoration: none;
            font-weight: 600;
        }}
        .view-link:hover {{
            text-decoration: underline;
        }}

        /* Lightbox */
        #lightbox {{
            position: fixed;
            inset: 0;
            background: rgba(0, 0, 0, 0.94);
            z-index: 1000;
            display: none;
            align-items: center;
            justify-content: center;
            flex-direction: column;
            padding: 24px;
        }}
        #lightbox.active {{
            display: flex;
        }}
        #lb-img {{
            max-width: 90vw;
            max-height: 80vh;
            border-radius: 8px;
            box-shadow: 0 16px 48px rgba(0, 0, 0, 0.9);
            object-fit: contain;
        }}
        #lb-info {{
            margin-top: 16px;
            text-align: center;
            max-width: 800px;
        }}
        #lb-title {{
            font-size: 18px;
            font-weight: 700;
            color: var(--primary);
            margin-bottom: 6px;
        }}
        #lb-desc {{
            font-size: 14px;
            color: #e2e8f0;
            line-height: 1.5;
        }}
        .lb-close {{
            position: absolute;
            top: 24px;
            right: 32px;
            font-size: 36px;
            color: #fff;
            cursor: pointer;
            transition: transform 0.2s;
        }}
        .lb-close:hover {{
            transform: scale(1.15);
            color: var(--primary);
        }}
    </style>
</head>
<body>
    <header>
        <div class="header-title">
            <h1>👑 王昭君·长夜焕生 摄影精选候选库 (Curated 47 Poses)</h1>
            <p>已淘汰全数低清切块拼图 | 100% 单人高清实拍与精准构图参考 | 覆盖 7 个摄影执行方向</p>
        </div>
        <div class="stats-group">
            <div>精选总量: <span class="stats-highlight">47 张</span></div>
            <div>平均分辨率: <span class="stats-highlight">728×1089</span></div>
            <div>最高分辨率: <span class="stats-highlight">736×1308</span></div>
        </div>
    </header>

    <div class="nav-tabs">
        {''.join(tabs_html)}
    </div>

    <div class="container" id="grid">
        {''.join(card_html_list)}
    </div>

    <div id="lightbox" onclick="closeLightbox(event)">
        <span class="lb-close" onclick="closeLightbox(event)">&times;</span>
        <img id="lb-img" src="" alt="Zoom">
        <div id="lb-info">
            <div id="lb-title"></div>
            <div id="lb-desc"></div>
        </div>
    </div>

    <script>
        function filterCat(dir, btn) {{
            document.querySelectorAll('.tab').forEach(t => t.classList.remove('active'));
            btn.classList.add('active');
            const cards = document.querySelectorAll('.card');
            cards.forEach(card => {{
                if (dir === 'ALL' || card.dataset.direction === dir) {{
                    card.style.display = 'flex';
                }} else {{
                    card.style.display = 'none';
                }}
            }});
        }}

        function viewLightbox(src, id, desc, suit, res) {{
            document.getElementById('lb-img').src = src;
            document.getElementById('lb-title').innerText = `${{id}} (${{res}})`;
            document.getElementById('lb-desc').innerHTML = `<strong>动作特征:</strong> ${{desc}}<br><span style="color:#38bdf8;"><strong>实战价值:</strong> ${{suit}}</span>`;
            document.getElementById('lightbox').classList.add('active');
        }}

        function closeLightbox(e) {{
            if (e.target.id === 'lightbox' || e.target.classList.contains('lb-close')) {{
                document.getElementById('lightbox').classList.remove('active');
            }}
        }}

        document.addEventListener('keydown', (e) => {{
            if (e.key === 'Escape') {{
                document.getElementById('lightbox').classList.remove('active');
            }}
        }});
    </script>
</body>
</html>
"""

    with open(OUTPUT_HTML, "w", encoding="utf-8") as f:
        f.write(full_html)
    print(f"Saved Curated Selection Board HTML to {OUTPUT_HTML}")

    # Build 7 category contact sheets for the curated 47
    render_curated_contact_sheets(curated_records)

def render_curated_contact_sheets(records):
    by_dir = {}
    for r in records:
        d = r["direction"]
        by_dir.setdefault(d, []).append(r)

    thumb_w = 380
    thumb_h = 550
    padding = 24
    header_h = 96
    footer_slot_h = 60

    try:
        font_title = ImageFont.truetype("msyh.ttc", 30)
        font_desc = ImageFont.truetype("msyh.ttc", 13)
        font_badge = ImageFont.truetype("msyh.ttc", 12)
    except Exception:
        font_title = ImageFont.load_default()
        font_desc = ImageFont.load_default()
        font_badge = ImageFont.load_default()

    for d, items in by_dir.items():
        n = len(items)
        cols = min(4, max(1, n))
        rows = math.ceil(n / cols)

        total_w = cols * thumb_w + (cols + 1) * padding
        total_h = header_h + rows * (thumb_h + footer_slot_h) + padding

        sheet = Image.new("RGB", (total_w, total_h), color=(7, 9, 14))
        draw = ImageDraw.Draw(sheet)

        d_meta = DIRECTION_META.get(d, {})
        title_text = f"{d_meta.get('name', d)} ({n} 张精选)"
        draw.text((padding, 24), title_text, fill=(0, 242, 255), font=font_title)
        draw.text((padding, 64), f"角色应用: {d_meta.get('role', '')}", fill=(148, 163, 184), font=font_badge)

        for i, it in enumerate(items):
            col = i % cols
            row = i // cols
            x = padding + col * (thumb_w + padding)
            y = header_h + row * (thumb_h + footer_slot_h)

            img_file = ROOT / it["file"]
            if img_file.exists():
                try:
                    with Image.open(img_file) as im:
                        im_rgb = im.convert("RGB")
                        target_ratio = thumb_w / thumb_h
                        current_ratio = im_rgb.width / im_rgb.height
                        if current_ratio > target_ratio:
                            new_w = int(im_rgb.height * target_ratio)
                            offset = (im_rgb.width - new_w) // 2
                            im_crop = im_rgb.crop((offset, 0, offset + new_w, im_rgb.height))
                        else:
                            new_h = int(im_rgb.width / target_ratio)
                            offset = (im_rgb.height - new_h) // 2
                            im_crop = im_rgb.crop((0, offset, im_rgb.width, offset + new_h))
                        im_resized = im_crop.resize((thumb_w, thumb_h), Image.Resampling.LANCZOS)
                        sheet.paste(im_resized, (x, y))
                except Exception:
                    pass

            draw.rectangle([x, y, x + thumb_w, y + thumb_h], outline=(30, 41, 59), width=1)

            # Badge top left
            sel_id = it["selected_id"]
            draw.rectangle([x + 8, y + 8, x + 120, y + 32], fill=(0, 0, 0, 220), outline=(0, 242, 255), width=1)
            draw.text((x + 14, y + 11), sel_id, fill=(0, 242, 255), font=font_badge)

            # Badge top right
            res_str = f"{it['width']}x{it['height']}"
            draw.rectangle([x + thumb_w - 90, y + 8, x + thumb_w - 8, y + 32], fill=(0, 0, 0, 200))
            draw.text((x + thumb_w - 82, y + 11), res_str, fill=(255, 255, 255), font=font_badge)

            # Text footer
            ty = y + thumb_h + 6
            obs_short = it["observed_pose"][:25] + ("..." if len(it["observed_pose"]) > 25 else "")
            suit_short = it["suitability"][:26] + ("..." if len(it["suitability"]) > 26 else "")
            draw.text((x, ty), obs_short, fill=(241, 245, 249), font=font_desc)
            draw.text((x, ty + 20), f"★ {suit_short}", fill=(56, 189, 248), font=font_badge)

        out_sheet_path = SHEETS_DIR / f"curated_contact_{d}.jpg"
        sheet.save(out_sheet_path, quality=92)
        print(f"Rendered curated contact sheet: {out_sheet_path.name}")

if __name__ == "__main__":
    main()
