#!/usr/bin/env python3
"""Build interactive A/B calibration review board for 10 representative photography reference pairs."""
import sys
import json
import html
import shutil
from pathlib import Path

if not sys.stdout.encoding.lower().startswith('utf'):
    sys.stdout.reconfigure(encoding='utf-8')

ROOT = Path(__file__).resolve().parents[1]
INSPECTIONS = ROOT / "inspections"
OUT_DIR = INSPECTIONS / "ab-calibration-board"
IMG_OUT = OUT_DIR / "images"
OUT_DIR.mkdir(parents=True, exist_ok=True)
IMG_OUT.mkdir(parents=True, exist_ok=True)

# Load manifests
m_zhaojun = {it["index"]: it for it in json.loads((INSPECTIONS / "inspection-changye-huansheng-100" / "manifest.json").read_text(encoding="utf-8"))}
m_kana = {it["index"]: it for it in json.loads((INSPECTIONS / "inspection-arima-kana-100" / "manifest.json").read_text(encoding="utf-8"))}
m_xishi = {it["index"]: it for it in json.loads((INSPECTIONS / "inspection-xishi-100" / "manifest.json").read_text(encoding="utf-8"))}
m_jk = {it["index"]: it for it in json.loads((INSPECTIONS / "inspection-jk-100" / "manifest.json").read_text(encoding="utf-8"))}

# 10 High-entropy contrastive pairs
PAIRS_CONFIG = [
    {
        "id": "pair_01",
        "title": "第 01 组 · 漫展实况：全身舒展动态 vs 杂乱随手抓拍",
        "dimension": "动作动态 & 漫展现场容忍度",
        "core_question": "在漫展这种路人杂乱的弱控场环境下，若全身动作舒展、体态线条清晰（A），是否可以放宽对背景路人的容忍？",
        "item_a": {
            "source_dir": "inspection-xishi-100",
            "data": m_xishi[2], # 北京ijoy漫展cos西施拍照姿势
            "tag": "候选 A（西施）",
            "feature": "漫展现场全身照，虽然周围有展台和少许路人，但人物体态线条舒展，有明确的拍照动作与角色身段参考价值。"
        },
        "item_b": {
            "source_dir": "inspection-arima-kana-100",
            "data": m_kana[1], # 你有这样的xox出没在萤火虫
            "tag": "候选 B（有马加奈）",
            "feature": "同样是漫展现场，但角度偏近偏平，缺少身体动势与构图，属于随手自娱自乐抓拍，摄影参考价值弱。"
        }
    },
    {
        "id": "pair_02",
        "title": "第 02 组 · 多宫格笔记：系统性摆姿指南 vs 纯服装版型买家秀",
        "dimension": "多宫格拼图价值与排他",
        "core_question": "多图拼图中，系统性分解动作姿态的组图（A）与专门对比服装做工/布料/版型的买家秀（B），如何界定？",
        "item_a": {
            "source_dir": "inspection-xishi-100",
            "data": m_xishi[4], # 一些西施的动态感拍照姿势
            "tag": "候选 A（西施）",
            "feature": "多宫格动作分解，每张展示不同的跑跳、回头、手势和重心变化，具备极高的现场拍摄可执行性。"
        },
        "item_b": {
            "source_dir": "inspection-xishi-100",
            "data": m_xishi[10], # 喵屋和次元依西施详细对比
            "tag": "候选 B（西施）",
            "feature": "多图服装做工测评，重点全在衣服领口、暗纹印花和裁缝细节对比，属于服装导购与商业买家秀。"
        }
    },
    {
        "id": "pair_03",
        "title": "第 03 组 · 近景特写尺度：角色情绪眼神光 vs 敷衍无参考大头",
        "dimension": "特写尺度与面部神态",
        "core_question": "特写镜头不含全身动作时，具有考究布光与剧情台词共鸣的面部特写（A），是否属于高价值审美灵感？而日常大头（B）是否坚决淘汰？",
        "item_a": {
            "source_dir": "inspection-arima-kana-100",
            "data": m_kana[3], # “10秒就能哭出的天才童星”
            "tag": "候选 A（有马加奈）",
            "feature": "特写情绪拉满，面部打光层次细腻，眼神光清晰，紧扣原著台词情境，适合作为情绪与眼神指导灵感。"
        },
        "item_b": {
            "source_dir": "inspection-arima-kana-100",
            "data": m_kana[7], # 咪。
            "tag": "候选 B（有马加奈）",
            "feature": "无布光考量的大头贴，面部角度单调，既无服饰造型全貌，也无动作构图参考价值。"
        }
    },
    {
        "id": "pair_04",
        "title": "第 04 组 · 舞台表演动态：打歌舞台爆发力 vs 僵硬站立公式照",
        "dimension": "舞台动态与肢体张力",
        "core_question": "同样是偶像题材打歌服，是捕捉跳跃/挥手等瞬间动态动作（A）更具指导性，还是规矩站立的半身公式照（B）更好？",
        "item_a": {
            "source_dir": "inspection-arima-kana-100",
            "data": m_kana[19], # B小町打歌舞台提前泄露！
            "tag": "候选 A（有马加奈）",
            "feature": "舞台抓拍瞬间，发丝与裙摆具有动势飞扬感，肢体线条舒展有活力，能指导模特跳脱木头人状态。"
        },
        "item_b": {
            "source_dir": "inspection-arima-kana-100",
            "data": m_kana[5], # 小偶像公式照
            "tag": "候选 B（有马加奈）",
            "feature": "规矩直立的证件照/公式照风格，动作拘谨平淡，缺乏舞台现场感和身体动势。"
        }
    },
    {
        "id": "pair_05",
        "title": "第 05 组 · 角色融入环境：大场景外景正片 vs 廉价塑料白棚",
        "dimension": "环境层次与场景氛围",
        "core_question": "大场景外景（A）人物与空间互动感强；若遇到背景单一、平光直打的棚拍（B），你的审美取向如何？",
        "item_a": {
            "source_dir": "inspection-xishi-100",
            "data": m_xishi[18], # 西施原皮外景
            "tag": "候选 A（西施）",
            "feature": "自然外景拍摄，江水与绿植与角色意境融合，景深与空间层次丰富，构图具备完整成片品质。"
        },
        "item_b": {
            "source_dir": "inspection-xishi-100",
            "data": m_xishi[15], # 请多多支持小西施✨
            "tag": "候选 B（西施）",
            "feature": "室内平光直照，背景平淡单调，缺乏明暗对比与环境氛围烘托，塑料感较明显。"
        }
    },
    {
        "id": "pair_06",
        "title": "第 06 组 · 专属法杖道具：互动舒展姿势 vs 道具挂人买家避雷",
        "dimension": "道具互动与商业杂质",
        "core_question": "法杖/武器类道具是 Cosplay 重心。手持道具的实拍姿态（A）与道具做工避雷/挂人贴（B）的判定边界？",
        "item_a": {
            "source_dir": "inspection-changye-huansheng-100",
            "data": m_zhaojun[5], # 王昭君长夜焕生场照姿势分享
            "tag": "候选 A（王昭君）",
            "feature": "双手持长法杖在漫展现场展开身姿，动作兼具力量感与优雅线条，道具与肢体形成良好三角形构图。"
        },
        "item_b": {
            "source_dir": "inspection-changye-huansheng-100",
            "data": m_zhaojun[14], # 两位数的平价cos道具推荐
            "tag": "候选 B（王昭君）",
            "feature": "纯道具商品开箱、材料评测与店铺比价，不含任何可实行的摄影构图与摆姿指导。"
        }
    },
    {
        "id": "pair_07",
        "title": "第 07 组 · JK 制服日常感：情绪叙事电影画幅 vs 网红快餐摆拍",
        "dimension": "日常人像松弛感与电影感",
        "core_question": "在 JK/日常写真中，带有故事感、微风动势或特定构图（A），对比千篇一律的剪刀手与网红磨皮（B），你的筛选标准？",
        "item_a": {
            "source_dir": "inspection-jk-100",
            "data": m_jk[2], # 树下微风与光影
            "tag": "候选 A（JK实拍）",
            "feature": "自然光斑透过树叶洒在发丝上，微风吹动裙角，带有日系胶片色彩与松弛故事感，非摆拍工业感。"
        },
        "item_b": {
            "source_dir": "inspection-jk-100",
            "data": m_jk[12], # 纯大头网红磨皮
            "tag": "候选 B（JK实拍）",
            "feature": "重度假睫毛与过度磨皮，脸部光影细节全失，缺乏制服褶皱结构与肢体动态线条。"
        }
    },
    {
        "id": "pair_08",
        "title": "第 08 组 · 电影宽画幅：横幅 3:2 叙事感 vs 紧凑竖图",
        "dimension": "画幅语言与留白",
        "core_question": "摄影师常采用 640x427 (3:2) 或 640x360 (16:9) 横幅展现景深与意境（A），你是否更偏好这种横画幅电影感，还是竖版竖拍？",
        "item_a": {
            "source_dir": "inspection-changye-huansheng-100",
            "data": m_zhaojun[62], # 横幅大场景
            "tag": "候选 A（王昭君）",
            "feature": "大比例横画幅，留白充沛，冷蓝色暗调背景与人物高光形成鲜明反差，画面极具电影叙事感。"
        },
        "item_b": {
            "source_dir": "inspection-changye-huansheng-100",
            "data": m_zhaojun[6], # 长夜焕生竖图
            "tag": "候选 B（王昭君）",
            "feature": "标准居中竖图，构图紧凑压迫，背景被主体完全挡住，缺少空间延伸感。"
        }
    },
    {
        "id": "pair_09",
        "title": "第 09 组 · 真实成片质感 vs AI生成假Coser",
        "dimension": "真实真人摄影 vs AI生图伪装",
        "core_question": "目前小红书有大量用 Midjourney / Stable Diffusion 生成的假 Coser，光影油腻但手指或发丝有破绽。是否一票否决 AI 图？",
        "item_a": {
            "source_dir": "inspection-arima-kana-100",
            "data": m_kana[14], # 有马加奈独家专栏 (实拍正片)
            "tag": "候选 A（有马加奈）",
            "feature": "真人拍摄，布料真实褶皱与织物肌理清晰，发丝与皮肤纹理自然，能在现实拍摄中真实复刻。"
        },
        "item_b": {
            "source_dir": "inspection-arima-kana-100",
            "data": m_kana[11], # TEST ME (AI合成插画感)
            "tag": "候选 B（有马加奈）",
            "feature": "AI 二次元生成质感，皮肤呈塑料蜡像高光，服饰结构违反现实物理重力，无法在现场实操拍摄。"
        }
    },
    {
        "id": "pair_10",
        "title": "第 10 组 · 出片正片返图 vs 二手闲鱼出物转单",
        "dimension": "正片标记与闲置商业过滤",
        "core_question": "很多包含精美封面的帖子实际是‘急出c服/求物/转单’，这类纯二手出物帖是否需要被 Layer 2 彻底清除？",
        "item_a": {
            "source_dir": "inspection-arima-kana-100",
            "data": m_kana[16], # “我要成为—你推的孩子！”
            "tag": "候选 A（有马加奈）",
            "feature": "完整 Cosplay 成片创作，包含专属色系打光、精心修图与情绪表达，属于标准参考样片。"
        },
        "item_b": {
            "source_dir": "inspection-arima-kana-100",
            "data": m_kana[23], # 好价急抛cos服
            "tag": "候选 B（有马加奈）",
            "feature": "闲鱼转卖帖子，封面虽然借用了他人的精修图，但帖内全是出服尺寸、瑕疵说明与价格，不属于摄影作品。"
        }
    }
]

# Process and copy images
processed_pairs = []
for p in PAIRS_CONFIG:
    pair_id = p["id"]
    # Item A
    dir_a = INSPECTIONS / p["item_a"]["source_dir"] / "images"
    fn_a = p["item_a"]["data"]["filename"]
    src_a = dir_a / fn_a
    dst_a = IMG_OUT / f"{pair_id}_A_{fn_a}"
    if src_a.exists():
        shutil.copy2(src_a, dst_a)
    
    # Item B
    dir_b = INSPECTIONS / p["item_b"]["source_dir"] / "images"
    fn_b = p["item_b"]["data"]["filename"]
    src_b = dir_b / fn_b
    dst_b = IMG_OUT / f"{pair_id}_B_{fn_b}"
    if src_b.exists():
        shutil.copy2(src_b, dst_b)

    processed_pairs.append({
        "id": p["id"],
        "title": p["title"],
        "dimension": p["dimension"],
        "core_question": p["core_question"],
        "a": {
            "img_rel": f"images/{dst_a.name}",
            "title": p["item_a"]["data"].get("title", ""),
            "author": p["item_a"]["data"].get("author", ""),
            "page_url": p["item_a"]["data"].get("page_url", ""),
            "dims": p["item_a"]["data"].get("dimensions", ""),
            "tag": p["item_a"]["tag"],
            "feature": p["item_a"]["feature"],
        },
        "b": {
            "img_rel": f"images/{dst_b.name}",
            "title": p["item_b"]["data"].get("title", ""),
            "author": p["item_b"]["data"].get("author", ""),
            "page_url": p["item_b"]["data"].get("page_url", ""),
            "dims": p["item_b"]["data"].get("dimensions", ""),
            "tag": p["item_b"]["tag"],
            "feature": p["item_b"]["feature"],
        }
    })

# Generate HTML
pairs_cards_html = []
for idx, pair in enumerate(processed_pairs, 1):
    card = f"""
    <section class="pair-card" id="{pair['id']}" data-pair-idx="{idx}">
        <div class="pair-header">
            <div class="pair-title-box">
                <span class="pair-badge">PAIR #{idx:02d}</span>
                <h2>{html.escape(pair['title'])}</h2>
            </div>
            <span class="pair-dim-badge">{html.escape(pair['dimension'])}</span>
        </div>
        
        <div class="pair-prompt-bar">
            <strong>核心审美品味边界：</strong> {html.escape(pair['core_question'])}
        </div>

        <div class="comparison-grid">
            <!-- CANDIDATE A -->
            <div class="candidate-col" id="{pair['id']}_col_a">
                <div class="candidate-header a-header">
                    <span class="cand-tag">{html.escape(pair['a']['tag'])}</span>
                    <span class="cand-dim">{html.escape(pair['a']['dims'])}</span>
                </div>
                <div class="img-wrap">
                    <img src="{pair['a']['img_rel']}" alt="{html.escape(pair['a']['title'])}" onclick="zoomImage(this.src, '{html.escape(pair['a']['title'])}')" loading="lazy">
                </div>
                <div class="cand-info">
                    <h4 title="{html.escape(pair['a']['title'])}">{html.escape(pair['a']['title'])}</h4>
                    <p class="cand-meta">作者: {html.escape(pair['a']['author'])} | <a href="{html.escape(pair['a']['page_url'])}" target="_blank" rel="noopener">小红书原帖 ↗</a></p>
                    <p class="cand-feature"><strong>特征分析：</strong>{html.escape(pair['a']['feature'])}</p>
                </div>
            </div>

            <!-- CANDIDATE B -->
            <div class="candidate-col" id="{pair['id']}_col_b">
                <div class="candidate-header b-header">
                    <span class="cand-tag">{html.escape(pair['b']['tag'])}</span>
                    <span class="cand-dim">{html.escape(pair['b']['dims'])}</span>
                </div>
                <div class="img-wrap">
                    <img src="{pair['b']['img_rel']}" alt="{html.escape(pair['b']['title'])}" onclick="zoomImage(this.src, '{html.escape(pair['b']['title'])}')" loading="lazy">
                </div>
                <div class="cand-info">
                    <h4 title="{html.escape(pair['b']['title'])}">{html.escape(pair['b']['title'])}</h4>
                    <p class="cand-meta">作者: {html.escape(pair['b']['author'])} | <a href="{html.escape(pair['b']['page_url'])}" target="_blank" rel="noopener">小红书原帖 ↗</a></p>
                    <p class="cand-feature"><strong>特征分析：</strong>{html.escape(pair['b']['feature'])}</p>
                </div>
            </div>
        </div>

        <!-- DECISION & RATIONALE ROW -->
        <div class="decision-section">
            <div class="decision-buttons" data-pair-id="{pair['id']}">
                <button type="button" class="dec-btn btn-keep-a" data-choice="keep_a" onclick="selectChoice('{pair['id']}', 'keep_a')">
                    <strong>保留 A · 淘汰 B</strong>
                    <small>A 具有参考价值，B 不予录用</small>
                </button>
                <button type="button" class="dec-btn btn-keep-b" data-choice="keep_b" onclick="selectChoice('{pair['id']}', 'keep_b')">
                    <strong>保留 B · 淘汰 A</strong>
                    <small>B 具有参考价值，A 不予录用</small>
                </button>
                <button type="button" class="dec-btn btn-both-keep" data-choice="both_keep" onclick="selectChoice('{pair['id']}', 'both_keep')">
                    <strong>两者皆留</strong>
                    <small>各有千秋，均可保留借鉴</small>
                </button>
                <button type="button" class="dec-btn btn-both-drop" data-choice="both_drop" onclick="selectChoice('{pair['id']}', 'both_drop')">
                    <strong>两者皆弃</strong>
                    <small>均不符合要求，坚决淘汰</small>
                </button>
            </div>

            <div class="reason-box">
                <div class="quick-tags-row">
                    <span class="quick-tags-title">快捷判词标签：</span>
                    <button type="button" class="qtag" onclick="appendTag('{pair['id']}', '背景杂乱/路人抢镜')">📷 背景杂乱</button>
                    <button type="button" class="qtag" onclick="appendTag('{pair['id']}', '动作舒展自然')">🧍 动作舒展</button>
                    <button type="button" class="qtag" onclick="appendTag('{pair['id']}', '姿势僵硬木头人')">🧍 姿势生硬</button>
                    <button type="button" class="qtag" onclick="appendTag('{pair['id']}', '轮廓光/质感层次好')">💡 轮廓光高级</button>
                    <button type="button" class="qtag" onclick="appendTag('{pair['id']}', '顶闪/死白油光')">💡 打光惨白</button>
                    <button type="button" class="qtag" onclick="appendTag('{pair['id']}', 'C服买家秀/非成片')">👗 商业买家秀</button>
                    <button type="button" class="qtag" onclick="appendTag('{pair['id']}', '眼神情绪充沛')">🎭 眼神情绪好</button>
                    <button type="button" class="qtag" onclick="appendTag('{pair['id']}', '电影感宽画幅')">🎞️ 电影宽画幅</button>
                    <button type="button" class="qtag" onclick="appendTag('{pair['id']}', 'AI生成/无法实操')">🤖 AI假图</button>
                </div>
                <div class="reason-input-wrap">
                    <input type="text" id="reason_{pair['id']}" class="reason-input" placeholder="写一句您的具体判定直觉（选填，如：留A因为肢体动作很舒展，淘汰B因为打光过曝像随手拍）..." oninput="onReasonChange('{pair['id']}')">
                </div>
            </div>
        </div>
    </section>
    """
    pairs_cards_html.append(card)

html_template = f"""<!DOCTYPE html>
<html lang="zh-CN">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>摄影审美 A/B 对照标定看板 · Cosplay Reference Curator</title>
    <style>
        :root {{
            --ink: #14242e;
            --paper: #f0f3f5;
            --card-bg: #ffffff;
            --line: #dfe5e8;
            --accent: #1e6b52;
            --accent-soft: #e8f3ef;
            --danger: #b33939;
            --gold: #b78103;
            --radius: 12px;
        }}
        * {{ box-sizing: border-box; }}
        body {{
            margin: 0;
            padding: 0;
            background: var(--paper);
            font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, "PingFang SC", "Microsoft YaHei", sans-serif;
            color: var(--ink);
            line-height: 1.6;
        }}
        header.topbar {{
            position: sticky;
            top: 0;
            z-index: 100;
            background: white;
            box-shadow: 0 4px 16px rgba(0,0,0,0.06);
            padding: 16px 28px;
            display: flex;
            align-items: center;
            justify-content: space-between;
            gap: 20px;
        }}
        .brand-box h1 {{
            margin: 0;
            font-size: 19px;
            color: var(--ink);
            display: flex;
            align-items: center;
            gap: 8px;
        }}
        .brand-box p {{
            margin: 2px 0 0;
            font-size: 13px;
            color: #666;
        }}
        .progress-box {{
            display: flex;
            align-items: center;
            gap: 16px;
        }}
        .progress-text {{
            font-size: 14px;
            font-weight: 600;
            color: var(--accent);
        }}
        .btn-copy {{
            background: var(--accent);
            color: white;
            border: none;
            padding: 9px 18px;
            border-radius: 8px;
            font-weight: 600;
            font-size: 13px;
            cursor: pointer;
            box-shadow: 0 2px 8px rgba(30,107,82,0.25);
            transition: all 0.2s ease;
        }}
        .btn-copy:hover {{
            background: #15503d;
            transform: translateY(-1px);
        }}
        .main-container {{
            max-width: 1420px;
            margin: 24px auto;
            padding: 0 20px 80px;
            display: flex;
            flex-direction: column;
            gap: 32px;
        }}
        .pair-card {{
            background: white;
            border-radius: var(--radius);
            box-shadow: 0 2px 12px rgba(0,0,0,0.04);
            border: 2px solid transparent;
            overflow: hidden;
            transition: border-color 0.2s ease;
        }}
        .pair-card.completed {{
            border-color: #81c784;
        }}
        .pair-header {{
            padding: 16px 24px;
            background: #fafbfc;
            border-bottom: 1px solid var(--line);
            display: flex;
            align-items: center;
            justify-content: space-between;
            gap: 16px;
        }}
        .pair-title-box {{
            display: flex;
            align-items: center;
            gap: 12px;
        }}
        .pair-badge {{
            background: #e3f2fd;
            color: #1976d2;
            font-size: 11px;
            font-weight: 700;
            padding: 4px 10px;
            border-radius: 6px;
            letter-spacing: 0.5px;
        }}
        .pair-header h2 {{
            margin: 0;
            font-size: 16px;
            font-weight: 650;
        }}
        .pair-dim-badge {{
            font-size: 12px;
            color: #555;
            background: #f0f0f0;
            padding: 3px 10px;
            border-radius: 12px;
        }}
        .pair-prompt-bar {{
            padding: 10px 24px;
            background: #fff8e1;
            border-bottom: 1px solid #ffe082;
            font-size: 13px;
            color: #855b18;
        }}
        .comparison-grid {{
            display: grid;
            grid-template-columns: 1fr 1fr;
            gap: 20px;
            padding: 24px;
        }}
        .candidate-col {{
            background: #f8fafc;
            border: 1px solid var(--line);
            border-radius: 10px;
            overflow: hidden;
            display: flex;
            flex-direction: column;
            transition: all 0.2s ease;
        }}
        .candidate-col.chosen-keep {{
            border-color: #2e7d32;
            background: #f1f8f3;
        }}
        .candidate-col.chosen-drop {{
            opacity: 0.6;
            border-color: #e57373;
            background: #fef7f7;
        }}
        .candidate-header {{
            padding: 8px 14px;
            display: flex;
            align-items: center;
            justify-content: space-between;
            font-size: 12px;
            font-weight: 600;
            border-bottom: 1px solid var(--line);
        }}
        .a-header {{ background: #e8f5e9; color: #2e7d32; }}
        .b-header {{ background: #e3f2fd; color: #1565c0; }}
        .img-wrap {{
            height: 380px;
            background: #111;
            display: flex;
            align-items: center;
            justify-content: center;
            cursor: pointer;
            overflow: hidden;
        }}
        .img-wrap img {{
            max-width: 100%;
            max-height: 100%;
            object-fit: contain;
            transition: transform 0.2s ease;
        }}
        .img-wrap img:hover {{
            transform: scale(1.02);
        }}
        .cand-info {{
            padding: 14px;
            flex: 1;
            display: flex;
            flex-direction: column;
            gap: 6px;
        }}
        .cand-info h4 {{
            margin: 0;
            font-size: 14px;
            line-height: 1.4;
            color: var(--ink);
        }}
        .cand-meta {{
            margin: 0;
            font-size: 12px;
            color: #777;
        }}
        .cand-meta a {{
            color: #1976d2;
            text-decoration: none;
        }}
        .cand-meta a:hover {{
            text-decoration: underline;
        }}
        .cand-feature {{
            margin: 4px 0 0;
            font-size: 12.5px;
            color: #444;
            background: white;
            padding: 8px 10px;
            border-radius: 6px;
            border: 1px solid var(--line);
            line-height: 1.5;
        }}
        .decision-section {{
            padding: 16px 24px 20px;
            background: #fafbfc;
            border-top: 1px solid var(--line);
            display: flex;
            flex-direction: column;
            gap: 14px;
        }}
        .decision-buttons {{
            display: grid;
            grid-template-columns: repeat(4, 1fr);
            gap: 12px;
        }}
        .dec-btn {{
            padding: 12px 14px;
            border: 2px solid var(--line);
            background: white;
            border-radius: 8px;
            cursor: pointer;
            display: flex;
            flex-direction: column;
            align-items: center;
            gap: 4px;
            transition: all 0.15s ease;
        }}
        .dec-btn strong {{
            font-size: 13.5px;
            color: var(--ink);
        }}
        .dec-btn small {{
            font-size: 11px;
            color: #777;
        }}
        .dec-btn:hover {{
            border-color: #a3b6ad;
            background: #f7faf8;
        }}
        .dec-btn.selected {{
            border-color: var(--accent);
            background: var(--accent-soft);
        }}
        .dec-btn.selected strong {{
            color: var(--accent);
        }}
        .dec-btn.btn-both-drop.selected {{
            border-color: var(--danger);
            background: #ffebee;
        }}
        .dec-btn.btn-both-drop.selected strong {{
            color: var(--danger);
        }}
        .reason-box {{
            display: flex;
            flex-direction: column;
            gap: 8px;
            background: white;
            padding: 12px 14px;
            border-radius: 8px;
            border: 1px solid var(--line);
        }}
        .quick-tags-row {{
            display: flex;
            align-items: center;
            gap: 6px;
            flex-wrap: wrap;
        }}
        .quick-tags-title {{
            font-size: 12px;
            color: #666;
            font-weight: 600;
        }}
        .qtag {{
            background: #f4f6f8;
            border: 1px solid #dce2e6;
            font-size: 11.5px;
            padding: 3px 9px;
            border-radius: 12px;
            cursor: pointer;
            transition: all 0.15s ease;
        }}
        .qtag:hover {{
            background: #eef2f5;
            border-color: #9cbcae;
            color: var(--accent);
        }}
        .reason-input {{
            width: 100%;
            padding: 9px 12px;
            font-size: 13px;
            border: 1px solid var(--line);
            border-radius: 6px;
            outline: none;
        }}
        .reason-input:focus {{
            border-color: var(--accent);
            box-shadow: 0 0 0 2px var(--accent-soft);
        }}
        /* Zoom Lightbox */
        .zoom-modal {{
            display: none;
            position: fixed;
            inset: 0;
            background: rgba(0,0,0,0.88);
            z-index: 1000;
            align-items: center;
            justify-content: center;
            flex-direction: column;
            padding: 20px;
        }}
        .zoom-modal.active {{
            display: flex;
        }}
        .zoom-img {{
            max-width: 90vw;
            max-height: 85vh;
            object-fit: contain;
            border-radius: 6px;
            box-shadow: 0 8px 32px rgba(0,0,0,0.5);
        }}
        .zoom-caption {{
            color: white;
            font-size: 14px;
            margin-top: 10px;
        }}
        .zoom-close {{
            position: absolute;
            top: 20px;
            right: 25px;
            color: white;
            font-size: 32px;
            cursor: pointer;
        }}
    </style>
</head>
<body>

    <header class="topbar">
        <div class="brand-box">
            <h1>✨ 摄影审美 A/B 对照标定看板</h1>
            <p>10 组典型灰色地带实拍对比 · 勾选你的真实取舍与判词 · 一键导出给 AI 沉淀为 Skill 规则</p>
        </div>
        <div class="progress-box">
            <span class="progress-text" id="progress-indicator">已完成: 0 / 10 组</span>
            <button class="btn-copy" onclick="exportResults()">📋 一键复制标定结果 (发给 Agent)</button>
        </div>
    </header>

    <main class="main-container">
        {''.join(pairs_cards_html)}
    </main>

    <div class="zoom-modal" id="zoomModal" onclick="closeZoom()">
        <span class="zoom-close">&times;</span>
        <img class="zoom-img" id="zoomImg" src="" alt="放大查看">
        <div class="zoom-caption" id="zoomCaption"></div>
    </div>

    <script>
        const state = JSON.parse(localStorage.getItem('ab_calibration_state') || '{{}}');

        function saveState() {{
            localStorage.setItem('ab_calibration_state', JSON.stringify(state));
            updateProgress();
        }}

        function selectChoice(pairId, choice) {{
            if (!state[pairId]) state[pairId] = {{}};
            state[pairId].choice = choice;

            // Update UI buttons
            const card = document.getElementById(pairId);
            card.querySelectorAll('.dec-btn').forEach(btn => {{
                btn.classList.toggle('selected', btn.dataset.choice === choice);
            }});

            // Highlight columns
            const colA = document.getElementById(pairId + '_col_a');
            const colB = document.getElementById(pairId + '_col_b');
            colA.classList.remove('chosen-keep', 'chosen-drop');
            colB.classList.remove('chosen-keep', 'chosen-drop');

            if (choice === 'keep_a') {{
                colA.classList.add('chosen-keep');
                colB.classList.add('chosen-drop');
            }} else if (choice === 'keep_b') {{
                colB.classList.add('chosen-keep');
                colA.classList.add('chosen-drop');
            }} else if (choice === 'both_keep') {{
                colA.classList.add('chosen-keep');
                colB.classList.add('chosen-keep');
            }} else if (choice === 'both_drop') {{
                colA.classList.add('chosen-drop');
                colB.classList.add('chosen-drop');
            }}

            card.classList.add('completed');
            saveState();
        }}

        function appendTag(pairId, tag) {{
            const input = document.getElementById('reason_' + pairId);
            if (input.value) {{
                if (!input.value.includes(tag)) input.value += '，' + tag;
            }} else {{
                input.value = tag;
            }}
            onReasonChange(pairId);
        }}

        function onReasonChange(pairId) {{
            if (!state[pairId]) state[pairId] = {{}};
            state[pairId].reason = document.getElementById('reason_' + pairId).value.trim();
            saveState();
        }}

        function updateProgress() {{
            const total = 10;
            let done = 0;
            for (let i = 1; i <= total; i++) {{
                const pid = 'pair_' + String(i).padStart(2, '0');
                if (state[pid] && state[pid].choice) done++;
            }}
            document.getElementById('progress-indicator').textContent = `已完成: ${{done}} / ${{total}} 组`;
        }}

        function restoreFromStorage() {{
            for (const [pairId, val] of Object.entries(state)) {{
                if (val.choice) {{
                    selectChoice(pairId, val.choice);
                }}
                if (val.reason) {{
                    const input = document.getElementById('reason_' + pairId);
                    if (input) input.value = val.reason;
                }}
            }}
            updateProgress();
        }}

        function zoomImage(src, caption) {{
            document.getElementById('zoomImg').src = src;
            document.getElementById('zoomCaption').textContent = caption;
            document.getElementById('zoomModal').classList.add('active');
        }}

        function closeZoom() {{
            document.getElementById('zoomModal').classList.remove('active');
        }}

        function exportResults() {{
            const lines = [];
            lines.push('【摄影审美 A/B 标定结果】');
            const choiceMap = {{
                keep_a: '保留 A · 淘汰 B',
                keep_b: '保留 B · 淘汰 A',
                both_keep: '两者皆留',
                both_drop: '两者皆弃'
            }};

            let count = 0;
            for (let i = 1; i <= 10; i++) {{
                const pid = 'pair_' + String(i).padStart(2, '0');
                const p = state[pid];
                const card = document.getElementById(pid);
                const title = card ? card.querySelector('h2').textContent : pid;
                if (p && p.choice) {{
                    count++;
                    const cText = choiceMap[p.choice] || p.choice;
                    const rText = p.reason ? `（判词: ${{p.reason}}）` : '（无备注）';
                    lines.push(`- ${{title}}:【${{cText}}】${{rText}}`);
                }}
            }}

            if (count === 0) {{
                alert('您尚未进行任何标定选择，请先为卡片做出取舍！');
                return;
            }}

            const text = lines.join('\\n');
            navigator.clipboard.writeText(text).then(() => {{
                alert(`已成功复制 ${{count}} 组标定结果到剪贴板！可以直接在对话框中 Ctrl+V 粘贴发送给我。`);
            }}).catch(() => {{
                prompt('复制失败，请手动全选复制：', text);
            }});
        }}

        document.addEventListener('DOMContentLoaded', restoreFromStorage);
    </script>
</body>
</html>
"""

(OUT_DIR / "index.html").write_text(html_template, encoding="utf-8")
print(f"Successfully generated A/B calibration board at: {OUT_DIR / 'index.html'}")
print(f"Total pairs generated: {len(processed_pairs)}")
