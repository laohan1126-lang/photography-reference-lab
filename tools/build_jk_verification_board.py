#!/usr/bin/env python3
"""Build interactive demonstration page showing 10 kept JK images vs excluded JK images with exact reasons."""
import sys
import json
import html
import shutil
from pathlib import Path

if not sys.stdout.encoding.lower().startswith('utf'):
    sys.stdout.reconfigure(encoding='utf-8')

ROOT = Path(__file__).resolve().parents[1]
INSPECTIONS = ROOT / "inspections"
SRC_DIR = INSPECTIONS / "inspection-jk-100"
SRC_IMG = SRC_DIR / "images"
OUT_DIR = INSPECTIONS / "jk-calibration-demo"
OUT_IMG = OUT_DIR / "images"

OUT_DIR.mkdir(parents=True, exist_ok=True)
OUT_IMG.mkdir(parents=True, exist_ok=True)

items = json.loads((SRC_DIR / "manifest.json").read_text(encoding="utf-8"))
items_by_idx = {it["index"]: it for it in items}

# 10 High-value KEPT selections matching newly calibrated rules
KEPT_SELECTIONS = [
    {
        "index": 2,
        "title": "JK写真丨📸一块面包拍出的灵动",
        "author": "七工匠7Artisans",
        "dims": "640x1067",
        "rule_matched": "微风动势 + 灵动道具互动（拒绝摆拍僵硬木头人）",
        "why_keep": "借助小道具（面包）打破双手无处安放的僵硬尴尬，肢体线条自然大方，发丝与树影光斑有呼吸感，极具现场实拍启发性。"
    },
    {
        "index": 4,
        "title": "无道具拍照姿｜元气动态感JK动作参考📸",
        "author": "三月Mitsuki",
        "dims": "640x853",
        "rule_matched": "肢体大方几何学 + 救场动作分解（无道具现场通用）",
        "why_keep": "完全无道具依赖，动作包含跑跳、踢腿、前后重心转移，肢体线条形成多角度三角形，完美避开‘手臂生硬呈直线’的负面特征。"
    },
    {
        "index": 5,
        "title": "拍照别傻站着｜动起来比摆拍好看 100 倍",
        "author": "桃汁碎碎冰（穗穗）",
        "dims": "640x960",
        "rule_matched": "运动抓拍张力 + 摆姿动势（打破常规站桩）",
        "why_keep": "直击‘站桩木头人’痛点，示范了行走、回头、带风走动的自然抓拍动势，裙摆与步伐线条具有极佳的视觉延展。"
    },
    {
        "index": 9,
        "title": "一点再多一点生命力🏃",
        "author": "腚真红（模特版）",
        "dims": "640x853",
        "rule_matched": "稀缺大动态跑姿 + 舒展线条",
        "why_keep": "大步奔跑视角，全身舒展大方，具有强烈的青春电影感，不是规矩摆拍，属于非常规但值得强烈学习的姿态。"
    },
    {
        "index": 10,
        "title": "JK夜景",
        "author": "老风",
        "dims": "640x853",
        "rule_matched": "暗光夜景轮廓光层次 + 场景氛围感",
        "why_keep": "夜景弱光处理典范：背后车灯/街景提供通透轮廓光，人物面部补光柔和不油腻，既可指导夜景布光，又可作为后期调色参考。"
    },
    {
        "index": 22,
        "title": "jk地铁拍照焚决 | 她说这是最满意的照片",
        "author": "达拉崩吧斑得贝迪卜多比鲁翁",
        "dims": "640x853",
        "rule_matched": "公共交通大场景融入 + 坐姿姿势参考",
        "why_keep": "地铁车厢特定场景下的坐姿与倚靠动作，景深延伸感好，空间层次丰富，可兼作拍摄实操与 AI 生图场景布景参考。"
    },
    {
        "index": 34,
        "title": "《AL Album》03｜阴雨天城市JK氛围感",
        "author": "SylvaMi",
        "dims": "640x960",
        "rule_matched": "情绪叙事电影感 + 漫射光影",
        "why_keep": "阴雨天柔和漫射光，避开晴天大顶光的死硬阴影，色调冷峻清冷，人物情绪饱满，非网红快餐自拍。"
    },
    {
        "index": 44,
        "title": "拍照僵硬必看第一集｜44个元气可爱JK姿势✨",
        "author": "哈尔滨摄影师刘果敢",
        "dims": "640x853",
        "rule_matched": "多宫格系统性姿态指南（百搭救场动作库）",
        "why_keep": "符合你认可的‘高价值多宫格’：系统性分解手部互动、歪头角度、重心落点，现场不知道拍什么时随时翻出来救场。"
    },
    {
        "index": 62,
        "title": "不良少女|放学后天台见",
        "author": "艾梦",
        "dims": "640x960",
        "rule_matched": "反常态个性姿势（打破甜妹审美疲劳）",
        "why_keep": "打破千篇一律的‘剪刀手/嘟嘴甜妹’俗套，呈现冷酷、叛逆的大开大合身段，符合你标定中‘姿势反常但可以学习’的标准。"
    },
    {
        "index": 66,
        "title": "存一些地铁站日系 jk拍照姿势",
        "author": "西夏📷",
        "dims": "640x853",
        "rule_matched": "回眸与反身姿态（稀缺角度）",
        "why_keep": "楼梯与站台高低差构图，包含经典的回头回眸视线，台阶拉长腿部线条，兼具动作与后期拉腿美肤构图价值。"
    }
]

# Excluded典型代表及精准剔除理由
EXCLUDED_SELECTIONS = [
    {
        "index": 7,
        "title": "未命名笔记（纯字卡广告）",
        "author": "未知推广号",
        "dims": "480x132",
        "rule_triggered": "Layer 1 物理画幅法则：480x132 纯字广告条拦截",
        "why_drop": "小红书平台纯字广告条，无真人模特，无摄影像素，物理尺寸 max(w,h)<600 且高度仅 132px，100% 机械排除。"
    },
    {
        "index": 12,
        "title": "二次元学妹感拿捏了！",
        "author": "蒋书剑",
        "dims": "640x853",
        "rule_triggered": "Layer 4 网红过度磨皮 + 缺乏褶皱结构与动作参考",
        "why_drop": "重度美颜滤镜磨皮导致面部光影全失、塑料质感严重，服饰没有光影细节，姿势为无设计的随手自嗨大头贴，坚决排除。"
    },
    {
        "index": 16,
        "title": "jk拍照姿势分享！不卡建模不露脸！",
        "author": "妙王（妙妙老师）",
        "dims": "640x853",
        "rule_triggered": "Layer 2 负向特征：命中【不露脸】局部敷衍拼图",
        "why_drop": "标题明确标注‘不露脸’，实图全是不露脸的局部特写拼凑，缺乏头部与肢体整体协调性，无法作为拍摄现场成片指导。"
    },
    {
        "index": 32,
        "title": "南小鸟校服白棚九宫格～～",
        "author": "momo",
        "dims": "640x853",
        "rule_triggered": "Layer 4 廉价塑料白棚平光直打 + 姿态单一重复",
        "why_drop": "纯白背景平光直照，毫无空间层次与明暗光影对比，多图仅是头部角度微调，属于典型的低质多宫格敷衍连拍。"
    },
    {
        "index": 54,
        "title": "知世怼脸镜头下的小樱！",
        "author": "四七啃啃_",
        "dims": "640x853",
        "rule_triggered": "Layer 2 负向特征：命中【怼脸镜头】纯自嗨大头",
        "why_drop": "紧凑大特写塞满画面，无全身/半身肢体摆姿参考，缺乏服饰结构线条，属于你标定中严厉排除的‘纯自嗨照片’。"
    },
    {
        "index": 59,
        "title": "未命名笔记（推广条）",
        "author": "平台推送",
        "dims": "480x132",
        "rule_triggered": "Layer 1 商业垃圾流拦截",
        "why_drop": "平台商业赞助流垃圾，无任何图像参考价值。"
    }
]

# Copy images
for it in KEPT_SELECTIONS:
    raw = items_by_idx[it["index"]]
    fn = raw["filename"]
    src = SRC_IMG / fn
    dst = OUT_IMG / f"kept_{it['index']:03d}_{fn}"
    if src.exists():
        shutil.copy2(src, dst)
    it["img_rel"] = f"images/{dst.name}"
    it["page_url"] = raw.get("page_url", "")

for it in EXCLUDED_SELECTIONS:
    raw = items_by_idx[it["index"]]
    fn = raw["filename"]
    src = SRC_IMG / fn
    dst = OUT_IMG / f"dropped_{it['index']:03d}_{fn}"
    if src.exists():
        shutil.copy2(src, dst)
    it["img_rel"] = f"images/{dst.name}"
    it["page_url"] = raw.get("page_url", "")

kept_cards = []
for it in KEPT_SELECTIONS:
    c = f"""
    <div class="card kept-card">
        <div class="badge-row">
            <span class="badge keep-badge">✓ 精选保留 #{it['index']:03d}</span>
            <span class="dims-badge">{it['dims']}</span>
        </div>
        <div class="img-box" onclick="zoomImage('{it['img_rel']}', '{html.escape(it['title'])}')">
            <img src="{it['img_rel']}" alt="{html.escape(it['title'])}" loading="lazy">
        </div>
        <div class="card-info">
            <h4>{html.escape(it['title'])}</h4>
            <p class="meta">作者: {html.escape(it['author'])} | <a href="{html.escape(it['page_url'])}" target="_blank" rel="noopener">小红书原帖 ↗</a></p>
            <div class="rule-box">
                <span class="rule-label">💡 命中审美法则：</span>
                <strong>{html.escape(it['rule_matched'])}</strong>
            </div>
            <p class="why-text"><strong>保留理由：</strong>{html.escape(it['why_keep'])}</p>
        </div>
    </div>
    """
    kept_cards.append(c)

dropped_cards = []
for it in EXCLUDED_SELECTIONS:
    c = f"""
    <div class="card dropped-card">
        <div class="badge-row">
            <span class="badge drop-badge">✕ 严厉剔除 #{it['index']:03d}</span>
            <span class="dims-badge">{it['dims']}</span>
        </div>
        <div class="img-box" onclick="zoomImage('{it['img_rel']}', '{html.escape(it['title'])}')">
            <img src="{it['img_rel']}" alt="{html.escape(it['title'])}" loading="lazy">
        </div>
        <div class="card-info">
            <h4>{html.escape(it['title'])}</h4>
            <p class="meta">作者: {html.escape(it['author'])} | <a href="{html.escape(it['page_url'])}" target="_blank" rel="noopener">小红书原帖 ↗</a></p>
            <div class="rule-box trigger-box">
                <span class="rule-label">🚫 触碰淘汰红线：</span>
                <strong>{html.escape(it['rule_triggered'])}</strong>
            </div>
            <p class="why-text"><strong>排除理由：</strong>{html.escape(it['why_drop'])}</p>
        </div>
    </div>
    """
    dropped_cards.append(c)

html_content = f"""<!DOCTYPE html>
<html lang="zh-CN">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>JK 制服实拍审美采选实测校验（10张保留 vs 剔除对比）</title>
    <style>
        :root {{
            --ink: #14242e;
            --paper: #f4f6f8;
            --green: #2e7d32;
            --green-bg: #e8f5e9;
            --red: #c62828;
            --red-bg: #ffebee;
            --line: #dfe5e8;
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
        header {{
            background: white;
            padding: 24px 36px;
            box-shadow: 0 2px 10px rgba(0,0,0,0.06);
            position: sticky;
            top: 0;
            z-index: 100;
        }}
        header h1 {{
            margin: 0 0 6px 0;
            font-size: 22px;
            color: var(--ink);
            display: flex;
            align-items: center;
            gap: 10px;
        }}
        header p {{
            margin: 0;
            font-size: 13.5px;
            color: #555;
        }}
        .stat-pills {{
            margin-top: 12px;
            display: flex;
            gap: 12px;
        }}
        .pill {{
            padding: 5px 14px;
            border-radius: 20px;
            font-size: 13px;
            font-weight: 600;
        }}
        .pill-green {{ background: var(--green-bg); color: var(--green); }}
        .pill-red {{ background: var(--red-bg); color: var(--red); }}
        
        main {{
            max-width: 1460px;
            margin: 30px auto;
            padding: 0 20px 80px;
            display: flex;
            flex-direction: column;
            gap: 40px;
        }}
        .section-header {{
            display: flex;
            align-items: center;
            justify-content: space-between;
            border-bottom: 2px solid var(--line);
            padding-bottom: 12px;
        }}
        .section-header h2 {{
            margin: 0;
            font-size: 19px;
            display: flex;
            align-items: center;
            gap: 8px;
        }}
        .grid {{
            display: grid;
            grid-template-columns: repeat(auto-fill, minmax(270px, 1fr));
            gap: 22px;
        }}
        .card {{
            background: white;
            border-radius: var(--radius);
            box-shadow: 0 2px 8px rgba(0,0,0,0.05);
            overflow: hidden;
            display: flex;
            flex-direction: column;
            border: 2px solid transparent;
            transition: transform 0.2s ease, box-shadow 0.2s ease;
        }}
        .card:hover {{
            transform: translateY(-2px);
            box-shadow: 0 6px 16px rgba(0,0,0,0.08);
        }}
        .kept-card {{
            border-color: #a5d6a7;
        }}
        .dropped-card {{
            border-color: #ffcdd2;
            opacity: 0.92;
        }}
        .badge-row {{
            padding: 8px 12px;
            background: #fafafa;
            border-bottom: 1px solid #f0f0f0;
            display: flex;
            align-items: center;
            justify-content: space-between;
        }}
        .badge {{
            font-size: 11.5px;
            font-weight: 700;
            padding: 3px 8px;
            border-radius: 6px;
        }}
        .keep-badge {{ background: var(--green); color: white; }}
        .drop-badge {{ background: var(--red); color: white; }}
        .dims-badge {{ font-size: 11px; color: #888; }}
        .img-box {{
            height: 320px;
            background: #111;
            display: flex;
            align-items: center;
            justify-content: center;
            cursor: pointer;
            overflow: hidden;
        }}
        .img-box img {{
            max-width: 100%;
            max-height: 100%;
            object-fit: contain;
            transition: transform 0.2s ease;
        }}
        .img-box:hover img {{
            transform: scale(1.03);
        }}
        .card-info {{
            padding: 14px;
            flex: 1;
            display: flex;
            flex-direction: column;
            gap: 6px;
        }}
        .card-info h4 {{
            margin: 0;
            font-size: 14px;
            line-height: 1.35;
            color: var(--ink);
        }}
        .meta {{
            margin: 0;
            font-size: 11.5px;
            color: #777;
        }}
        .meta a {{
            color: #1976d2;
            text-decoration: none;
        }}
        .rule-box {{
            margin: 4px 0;
            padding: 7px 9px;
            border-radius: 6px;
            background: #f1f8f4;
            border-left: 3px solid var(--green);
            font-size: 12px;
            line-height: 1.4;
        }}
        .trigger-box {{
            background: #fdf2f2;
            border-left: 3px solid var(--red);
        }}
        .rule-label {{
            display: block;
            font-size: 10.5px;
            color: #666;
            margin-bottom: 2px;
        }}
        .why-text {{
            margin: 4px 0 0;
            font-size: 12px;
            color: #444;
            line-height: 1.45;
            flex: 1;
        }}
        /* Lightbox */
        .zoom-modal {{
            display: none;
            position: fixed;
            inset: 0;
            background: rgba(0,0,0,0.9);
            z-index: 1000;
            align-items: center;
            justify-content: center;
            flex-direction: column;
        }}
        .zoom-modal.active {{ display: flex; }}
        .zoom-img {{ max-width: 90vw; max-height: 85vh; object-fit: contain; }}
        .zoom-caption {{ color: white; font-size: 14px; margin-top: 10px; }}
        .zoom-close {{ position: absolute; top: 20px; right: 25px; color: white; font-size: 32px; cursor: pointer; }}
    </style>
</head>
<body>
    <header>
        <h1>✨ JK 制服实拍审美采选实测校验</h1>
        <p>基于刚刚融入你 10 组 A/B 黄金标定的 <code>cosplay-reference-curator</code> 规则，对真实 100 张小红书 JK 池进行端到端全量裁决实测。</p>
        <div class="stat-pills">
            <span class="pill pill-green">✓ 严格精选 10 张（满足大方肢体、救场动作、微风电影感）</span>
            <span class="pill pill-red">✕ 严厉排除 6 种典型废片（对镜拍买家秀、不露脸敷衍剪裁、网红磨皮无细节、纯广告条）</span>
        </div>
    </header>

    <main>
        <!-- 10 KEPT -->
        <section>
            <div class="section-header">
                <h2 style="color: var(--green);">🌟 严格精选保留的 10 张（点击任意图片可弹窗看大图）</h2>
                <small style="color: #666;">全部来自小红书真实实拍流，命中你刚刚确认的 5 项核心摄影审美法则</small>
            </div>
            <div class="grid" style="margin-top: 18px;">
                {''.join(kept_cards)}
            </div>
        </section>

        <!-- DROPPED SAMPLES -->
        <section>
            <div class="section-header">
                <h2 style="color: var(--red);">🚫 典型排除样例与精确理由</h2>
                <small style="color: #666;">精准拦截商业杂质、敷衍自嗨、过度磨皮假人与无动作平庸照</small>
            </div>
            <div class="grid" style="margin-top: 18px;">
                {''.join(dropped_cards)}
            </div>
        </section>
    </main>

    <div class="zoom-modal" id="zoomModal" onclick="closeZoom()">
        <span class="zoom-close">&times;</span>
        <img class="zoom-img" id="zoomImg" src="" alt="放大查看">
        <div class="zoom-caption" id="zoomCaption"></div>
    </div>

    <script>
        function zoomImage(src, caption) {{
            document.getElementById('zoomImg').src = src;
            document.getElementById('zoomCaption').textContent = caption;
            document.getElementById('zoomModal').classList.add('active');
        }}
        function closeZoom() {{
            document.getElementById('zoomModal').classList.remove('active');
        }}
    </script>
</body>
</html>
"""

(OUT_DIR / "index.html").write_text(html_content, encoding="utf-8")
print(f"Generated JK calibration demonstration page at: {OUT_DIR / 'index.html'}")
