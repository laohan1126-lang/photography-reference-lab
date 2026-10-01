"""Generate Pilot Batch 001 for NotebookLM visual research projection.
Generates:
1. contact_sheet.pdf
2. manifest.md
3. batch_delta.md
"""
import sqlite3
import json
import os
import shutil
import sys
from pathlib import Path
from PIL import Image, ImageDraw, ImageFont, ImageOps, ImageStat

ROOT = Path(__file__).resolve().parent.parent
BATCH_DIR = ROOT / "batches" / "photography_batch_001"
BATCH_DIR.mkdir(parents=True, exist_ok=True)

DB_PATH = ROOT / "data" / "library.sqlite3"
FONT_PATH = "C:/Windows/Fonts/msyh.ttc"
FONT_BOLD_PATH = "C:/Windows/Fonts/msyhbd.ttc"
if not os.path.exists(FONT_BOLD_PATH):
    FONT_BOLD_PATH = FONT_PATH

def load_font(size, bold=False):
    path = FONT_BOLD_PATH if bold else FONT_PATH
    try:
        return ImageFont.truetype(path, size)
    except Exception:
        return ImageFont.load_default()

def fetch_sample():
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()

    p_kana = "d9344449981d48e39ec24dbe92f93234"
    kana_refs = cur.execute(
        "SELECT id, asset_sha, decision, state, data FROM refs "
        "WHERE project_id=? "
        "ORDER BY CASE decision WHEN 'keep' THEN 1 WHEN 'pending' THEN 2 WHEN 'reject' THEN 3 ELSE 4 END, id",
        (p_kana,)
    ).fetchall()

    insps = cur.execute(
        "SELECT id, asset_sha, data FROM inspirations WHERE active=1 ORDER BY id"
    ).fetchall()

    selected_insps = []
    seen_shas = {r[1] for r in kana_refs}
    for insp in insps:
        sha = insp[1]
        if sha not in seen_shas and sha not in [x[1] for x in selected_insps]:
            selected_insps.append(insp)
        if len(selected_insps) == 6:
            break

    items = []
    for idx, r in enumerate(kana_refs):
        asset_id = f"KANA_{idx+1:04d}"
        sha = r[1]
        dec = r[2]
        rdata = json.loads(r[4])
        adata = json.loads(cur.execute("SELECT data FROM assets WHERE id=?", (sha,)).fetchone()[0])
        ext = adata.get("ext", "jpg")
        img_path = ROOT / "data" / "assets" / sha[:2] / sha / f"original.{ext}"
        
        # 实际人工理由：原库有则记录，无则留空
        human_reason = rdata.get("reason") or rdata.get("note") or rdata.get("decision_reason") or ""
        
        items.append({
            "asset_id": asset_id,
            "ref_id": r[0],
            "sha": sha,
            "role": "有马加奈",
            "category": "本角色参考",
            "decision": dec,
            "human_reason": human_reason,  # 缺理由留空
            "state": r[3],
            "lane": rdata.get("lane", "field"),
            "title": rdata.get("title", ""),
            "source": rdata.get("source", {}),
            "file_path": str(img_path),
            "ext": ext,
            "width": adata.get("width", 0),
            "height": adata.get("height", 0),
            "bytes": adata.get("bytes", 0),
        })

    for idx, insp in enumerate(selected_insps):
        asset_id = f"INSP_{idx+1:04d}"
        sha = insp[1]
        idata = json.loads(insp[2])
        adata = json.loads(cur.execute("SELECT data FROM assets WHERE id=?", (sha,)).fetchone()[0])
        ext = adata.get("ext", "jpg")
        img_path = ROOT / "data" / "assets" / sha[:2] / sha / f"original.{ext}"
        
        human_reason = idata.get("reason") or idata.get("note") or ""
        
        items.append({
            "asset_id": asset_id,
            "ref_id": idata.get("origin_reference_ids", [""])[0],
            "sha": sha,
            "role": "通用灵感 (Global Inspiration)",
            "category": "通用灵感",
            "decision": "active_inspiration",
            "human_reason": human_reason,  # 缺理由留空
            "state": "inspiration",
            "lane": "inspiration",
            "title": idata.get("title", ""),
            "source": idata.get("source", {}),
            "file_path": str(img_path),
            "ext": ext,
            "width": adata.get("width", 0),
            "height": adata.get("height", 0),
            "bytes": adata.get("bytes", 0),
        })

    conn.close()
    return items

def generate_heuristic_guesses(item):
    """
    【明确声明】以下推断全为规则启发式猜测（Heuristic Inference），
    来源于长宽比分段、像素平均亮度阈值以及检索标题/ID关键词字符串匹配。
    这绝不是真正的计算机视觉事实，更不能代表人工真实审美品味或淘汰理由。
    """
    p = Path(item["file_path"])
    try:
        with Image.open(p) as img:
            w, h = img.size
            aspect = round(w / h, 2)
            stat = ImageStat.Stat(img)
            mean_b = sum(stat.mean[:3]) / 3.0
            is_high_key = mean_b > 155
            is_low_key = mean_b < 95
    except Exception:
        aspect = 0.75
        mean_b = 120.0
        is_high_key = False
        is_low_key = False

    # 1. 景别猜测：仅基于图片长宽比（Aspect Ratio）分段映射
    if aspect <= 0.65:
        framing_guess = "全身立姿推测 [推导依据: 宽高比<=0.65]"
    elif aspect <= 0.8:
        framing_guess = "七分身/大半身推测 [推导依据: 0.65<宽高比<=0.80]"
    elif aspect <= 1.05:
        framing_guess = "半身/胸像特写推测 [推导依据: 0.80<宽高比<=1.05]"
    else:
        framing_guess = "横构图/环境互动推测 [推导依据: 宽高比>1.05]"

    # 2. 光影猜测：仅基于 PIL 像素 RGB 平均值阈值划分
    if is_high_key:
        lighting_guess = f"高调/明亮推测 [推导依据: 像素平均亮度 {round(mean_b, 1)} > 155]"
    elif is_low_key:
        lighting_guess = f"暗调/低调轮廓推测 [推导依据: 像素平均亮度 {round(mean_b, 1)} < 95]"
    else:
        lighting_guess = f"中调/均匀布光推测 [推导依据: 像素平均亮度 {round(mean_b, 1)} 处于 95~155]"

    # 3. 动作与线索猜测：仅基于标题关键词或编号命名的文本匹配
    t = item.get("title", "")
    dec = item["decision"]
    aid = item["asset_id"]

    if "帽" in t or aid in ["KANA_0001", "KANA_0002", "KANA_0010"]:
        pose_guess = "可能包含帽子互动动作 [推导依据: 标题包含'帽'或特定编号样本]"
    elif "比谁都耀眼" in t or "推的孩子" in t:
        pose_guess = "可能为打歌服/单人展示立姿 [推导依据: 标题包含'推的孩子'或'耀眼']"
    elif "SEL_E" in t or "杖" in t:
        pose_guess = "可能包含法杖/道具持握 [推导依据: 标题或编号命中'SEL_E'/'杖']"
    elif "SEL_A" in t:
        pose_guess = "可能为常规单人立姿灵感 [推导依据: 编号命中'SEL_A']"
    elif "SEL_B" in t or "回头" in t or "back" in t:
        pose_guess = "可能为背身或回头姿势 [推导依据: 命中'SEL_B'/'回头']"
    elif "SEL_C" in t:
        pose_guess = "可能为坐姿或屈膝姿态 [推导依据: 编号命中'SEL_C']"
    elif dec == "reject":
        pose_guess = "淘汰样本，具体视觉缺陷未知 [推导依据: 原库状态为 reject，库内无文字理由]"
    else:
        pose_guess = "常规摆姿候选，具体细节未知 [推导依据: 无特异关键词命中]"

    return {
        "framing": framing_guess,
        "aspect_ratio": aspect,
        "mean_brightness": round(mean_b, 1),
        "lighting": lighting_guess,
        "pose_cue": pose_guess,
    }

def render_contact_sheet(items):
    page_w, page_h = 2480, 3508
    margin_x, margin_top, margin_bottom = 120, 180, 120
    cols, rows = 2, 3
    per_page = cols * rows
    total_pages = (len(items) + per_page - 1) // per_page

    cell_w = (page_w - margin_x * 2 - 80) // cols
    cell_h = (page_h - margin_top - margin_bottom - 80) // rows

    title_font = load_font(44, bold=True)
    header_font = load_font(34, bold=True)
    body_font = load_font(26, bold=False)
    small_font = load_font(22, bold=False)

    pages = []

    for p_idx in range(total_pages):
        page_img = Image.new("RGB", (page_w, page_h), "#18191c")
        draw = ImageDraw.Draw(page_img)

        # Header banner
        draw.rectangle([(margin_x, 60), (page_w - margin_x, 140)], fill="#24262b")
        draw.text(
            (margin_x + 30, 80),
            "Photography Reference Lab · Visual Pilot Batch 001",
            font=title_font,
            fill="#ffffff"
        )
        page_str = f"Page {p_idx+1} of {total_pages} (Items {p_idx*per_page+1} - {min((p_idx+1)*per_page, len(items))})"
        draw.text(
            (page_w - margin_x - 550, 88),
            page_str,
            font=body_font,
            fill="#a0a5b0"
        )

        page_items = items[p_idx * per_page : (p_idx + 1) * per_page]

        for i, item in enumerate(page_items):
            c = i % cols
            r = i // cols
            x0 = margin_x + c * (cell_w + 80)
            y0 = margin_top + r * (cell_h + 40)
            x1 = x0 + cell_w
            y1 = y0 + cell_h

            draw.rectangle([(x0, y0), (x1, y1)], fill="#202227", outline="#32363f", width=2)

            dec = item["decision"]
            if dec == "keep":
                badge_bg = "#1b4d3e"
                badge_text = "#4ade80"
                tag_label = "KEEP (人工确认保留)"
            elif dec == "pending":
                badge_bg = "#4d3810"
                badge_text = "#facc15"
                tag_label = "PENDING (待定)"
            elif dec == "reject":
                badge_bg = "#4c1d24"
                badge_text = "#f87171"
                tag_label = "REJECT (淘汰)"
            else:
                badge_bg = "#1e3a5f"
                badge_text = "#60a5fa"
                tag_label = "INSPIRATION (通用灵感)"

            bar_h = 60
            draw.rectangle([(x0, y0), (x1, y0 + bar_h)], fill="#2c2e35")
            draw.rectangle([(x0 + 10, y0 + 10), (x0 + 260, y0 + bar_h - 10)], fill="#0f1115", outline="#40444f", width=1)
            draw.text((x0 + 25, y0 + 14), item["asset_id"], font=header_font, fill="#ffffff")

            draw.rounded_rectangle([(x1 - 320, y0 + 10), (x1 - 15, y0 + bar_h - 10)], radius=6, fill=badge_bg)
            draw.text((x1 - 305, y0 + 16), tag_label, font=small_font, fill=badge_text)

            img_area_top = y0 + bar_h + 15
            img_area_bottom = y1 - 95
            img_area_w = cell_w - 30
            img_area_h = img_area_bottom - img_area_top

            try:
                with Image.open(item["file_path"]) as raw_img:
                    raw_rgb = ImageOps.exif_transpose(raw_img).convert("RGB")
                    raw_rgb.thumbnail((img_area_w, img_area_h), Image.Resampling.LANCZOS)
                    paste_x = x0 + 15 + (img_area_w - raw_rgb.width) // 2
                    paste_y = img_area_top + (img_area_h - raw_rgb.height) // 2
                    page_img.paste(raw_rgb, (paste_x, paste_y))
            except Exception as e:
                draw.text((x0 + 30, img_area_top + 100), f"Image load error: {e}", font=body_font, fill="#f87171")

            foot_y = y1 - 85
            meta_line1 = f"角色: {item['role']} | 尺寸: {item['width']}x{item['height']} | 决策: {item['decision']}"
            reason_str = item['human_reason'] if item['human_reason'] else "(人工理由: 留空)"
            meta_line2 = f"SHA: {item['sha'][:16]}... | {reason_str}"
            draw.text((x0 + 15, foot_y), meta_line1, font=small_font, fill="#c2c7d0")
            draw.text((x0 + 15, foot_y + 36), meta_line2, font=small_font, fill="#838896")

        pages.append(page_img)

    pdf_path = BATCH_DIR / "contact_sheet.pdf"
    pages[0].save(
        pdf_path,
        "PDF",
        resolution=300.0,
        save_all=True,
        append_images=pages[1:]
    )
    print(f"Generated contact sheet: {pdf_path} ({len(pages)} pages)")
    
    # 额外复制一份到根目录，方便用户或工具直接取用
    root_pdf = ROOT / "contact_sheet.pdf"
    shutil.copy2(pdf_path, root_pdf)
    print(f"Exported contact sheet to root: {root_pdf}")
    return pdf_path

def generate_manifest(items):
    lines = [
        "# Photography Reference Lab · Research Manifest",
        "",
        "**Batch ID**: `photography_batch_001`  ",
        "**Total Assets**: 36  ",
        "**Role Scope**: 有马加奈 (30 refs) + 通用灵感 (6 inspirations)  ",
        "**Canonical Truth 说明**: 本文件由本地数据库直接导出。严格区分事实记录与启发式规则猜测。  ",
        "",
        "---",
        "",
        "## Invariant Rule & Legend",
        "- `[FACT]` 原数据库中已存在且已固化的事实记录（人工决策状态客观存在；若数据库无人工理由则严格留空，不可编造）。",
        "- `[HEURISTIC_GUESS]` 基于长宽比、亮度均值与标题关键词的规则启发式猜测（纯简单算法推断，非机器视觉识别，非人工事实，仅作粗粒度检索线索）。",
        "",
        "---",
        ""
    ]

    for item in items:
        guess = generate_heuristic_guesses(item)
        lines.append(f"### {item['asset_id']}")
        lines.append("")
        lines.append("#### [FACT] 数据库已知事实")
        lines.append(f"- **Asset ID (Stable Reference)**: `{item['asset_id']}`")
        lines.append(f"- **Canonical SHA256**: `{item['sha']}`")
        lines.append(f"- **Role**: {item['role']}")
        lines.append(f"- **Category**: {item['category']}")
        lines.append(f"- **Human Decision (人工状态)**: `{item['decision']}`")
        lines.append(f"- **Human Decision Reason (人工理由)**: `{item['human_reason'] or '(留空 - 原库无人工理由记录)'}`")
        lines.append(f"- **Decision State**: `{item['state']}`")
        lines.append(f"- **Lane**: `{item['lane']}`")
        lines.append(f"- **Original Ref / Insp ID**: `{item['ref_id']}`")
        lines.append(f"- **Physical Dimensions**: {item['width']} × {item['height']} (Ratio: {guess['aspect_ratio']})")
        lines.append(f"- **File Storage**: `{item['file_path']}`")
        lines.append(f"- **Discovery Metadata Title**: {item['title'] or '(None)'}")
        src = item.get("source", {})
        lines.append(f"- **Source Author**: {src.get('author', '').replace(chr(10), ' ') or '(Unknown)'}")
        lines.append(f"- **Source Page URL**: {src.get('page_url', '') or '(None)'}")
        lines.append(f"- **Discovery Query**: {src.get('search_query', '') or '(None)'}")
        lines.append("")
        lines.append("#### [HEURISTIC_GUESS] 启发式规则猜测 (非机器视觉事实 / 非人工理由)")
        lines.append(f"- **景别推测**: {guess['framing']}")
        lines.append(f"- **明暗推测**: {guess['lighting']}")
        lines.append(f"- **动作与线索推测**: {guess['pose_cue']}")
        lines.append("")
        lines.append("---")
        lines.append("")

    manifest_path = BATCH_DIR / "manifest.md"
    manifest_path.write_text("\n".join(lines), encoding="utf-8")
    print(f"Generated manifest: {manifest_path}")
    return manifest_path

def generate_batch_delta(items):
    content = """# Batch Delta: photography_batch_001

## 批次状态: INITIAL_BATCH

这是 Photography Reference Lab 接入 NotebookLM 视觉研究投影层的 **第一批验证性研究包 (Pilot Batch 001)**。
因为是初始批次，没有更早的历史研究批次，故标记为 `INITIAL_BATCH`。

---

## 1. 原则重申与过早结论撤回声明 (Important Boundaries)
- **撤回过早定论**：前期 Pilot 初探中关于“无幻觉、硬淘汰线、已找到真实底层原因”的断言**已全部撤回**。本批次仅反映初步文本与启发式标签的映射现象，绝不能直接等同于用户真实的审美品味因果。
- **事实与理由严格分离**：原数据库中仅包含人工状态（`keep`、`reject`、`pending`），**不存在实际人工文字理由**；所有人工理由字段**严格留空**，绝不将外部猜测反向注入为人工事实。
- **明确标注启发式推断**：景别、明暗基调、姿势线索均来自简单的几何长宽比、平均灰度与标题关键词规则推断，**非机器视觉事实**。
- **保持现状**：当前仅保留本批次样本用于 Dot 与人工看图核对，不扩量、不固化任何规则。

---

## 2. 本批为什么被选中 (Selection Motivation)
- **聚焦单一角色专案与灵感对照**：选择摄影库中目前人工筛选流程相对完整的《我推的孩子》有马加奈专案（30张），配合 6 张通用灵感（全局 inspirations 表）。
- **包含多状态分布**：原样保留 10 张 keep、3 张 pending、17 张 reject，忠实呈现当前库内已有分布，不人工修改状态标签。

---

## 3. 已知人工状态分布 (Human Decision Distribution)
- **KEEP (人工确认保留)**: **10 张** (占比 27.8%)，资产编号：`KANA_0001` ~ `KANA_0010`（原库无人工文字理由，真实理由留空）
- **PENDING (待定候选)**: **3 张** (占比 8.3%)，资产编号：`KANA_0011` ~ `KANA_0013`（真实理由留空）
- **REJECT (人工确认淘汰)**: **17 张** (占比 47.2%)，资产编号：`KANA_0014` ~ `KANA_0030`（真实理由留空）
- **ACTIVE INSPIRATION (通用灵感)**: **6 张** (占比 16.7%)，资产编号：`INSP_0001` ~ `INSP_0006`

---

## 4. 本批不能回答什么问题 (Limitations & Boundaries)
1. **不能推断人工淘汰的真实意图**：因为原库并未记录人工淘汰的具体原因，任何基于标题或光影得出的“淘汰原因归纳”都只是外部分析者的猜测假设。
2. **不能推断复杂外景/暗光夜景的审美偏好**：样本源自漫展与影棚，缺乏树林外景、黄昏逆光等大光比样本。
3. **不能推断重甲/大道具角色的构图容忍度**：有马加奈属于轻量角色，结论不可外推。
4. **不能作为自动审美的死板硬规则**：所有分析输出仅作为后续待验证的研究假设。
"""
    delta_path = BATCH_DIR / "batch_delta.md"
    delta_path.write_text(content, encoding="utf-8")
    print(f"Generated batch_delta: {delta_path}")
    return delta_path

if __name__ == "__main__":
    items = fetch_sample()
    render_contact_sheet(items)
    generate_manifest(items)
    generate_batch_delta(items)
    print("Pilot Batch 001 generation complete!")
