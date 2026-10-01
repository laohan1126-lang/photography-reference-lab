"""Prepare and Upload Full Verified Library (Keep & Inspirations) to user's private Google Drive.
Organizes into structured subfolders:
- 01_JK (57)
- 02_王昭君 (24)
- 03_西施 (15)
- 04_有马加奈 (10)
- 05_通用灵感 (21)
Each folder includes contact_sheet.pdf, manifest.md, and individual high-res original images with stable IDs.
Generates a master library_manifest.json for Dot.
"""
import sqlite3
import json
import os
import sys
import shutil
from pathlib import Path
from PIL import Image, ImageDraw, ImageFont, ImageOps, ImageStat

from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build
from googleapiclient.http import MediaFileUpload

ROOT = Path(__file__).resolve().parent.parent
LOCAL_DIR = ROOT / ".local"
CLIENT_SECRET_FILE = LOCAL_DIR / "client_secret.json"
TOKEN_FILE = LOCAL_DIR / "drive_token.json"
EXPORT_DIR = ROOT / "batches" / "verified_library_export"
EXPORT_DIR.mkdir(parents=True, exist_ok=True)

DB_PATH = ROOT / "data" / "library.sqlite3"
FONT_PATH = "C:/Windows/Fonts/msyh.ttc"
FONT_BOLD_PATH = "C:/Windows/Fonts/msyhbd.ttc"
if not os.path.exists(FONT_BOLD_PATH):
    FONT_BOLD_PATH = FONT_PATH

SCOPES = ["https://www.googleapis.com/auth/drive.file"]

def load_font(size, bold=False):
    path = FONT_BOLD_PATH if bold else FONT_PATH
    try:
        return ImageFont.truetype(path, size)
    except Exception:
        return ImageFont.load_default()

def fetch_all_verified():
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()
    projects = dict(cur.execute("SELECT id, data FROM projects").fetchall())

    keep_rows = cur.execute("""
        SELECT id, project_id, asset_sha, state, data 
        FROM refs 
        WHERE decision='keep'
        ORDER BY project_id, id
    """).fetchall()

    insp_rows = cur.execute("""
        SELECT id, asset_sha, data 
        FROM inspirations 
        WHERE active=1 
        ORDER BY id
    """).fetchall()

    categories = {
        "01_JK": {"name": "JK", "prefix": "JK", "items": []},
        "02_王昭君": {"name": "王昭君", "prefix": "ZHAOJUN", "items": []},
        "03_西施": {"name": "西施", "prefix": "XISHI", "items": []},
        "04_有马加奈": {"name": "有马加奈", "prefix": "KANA", "items": []},
        "05_通用灵感": {"name": "通用灵感", "prefix": "INSP", "items": []}
    }

    # 1. Map keep refs
    for r in keep_rows:
        r_id, p_id, sha, st, rdata_str = r
        pdata = json.loads(projects.get(p_id, "{}"))
        cname = pdata.get("character_name") or pdata.get("character") or pdata.get("name") or ""
        rdata = json.loads(rdata_str)
        arow = cur.execute("SELECT data FROM assets WHERE id=?", (sha,)).fetchone()
        adata = json.loads(arow[0]) if arow else {}
        ext = adata.get("ext", "jpg")
        img_p = ROOT / "data" / "assets" / sha[:2] / sha / f"original.{ext}"

        if "jk" in cname.lower():
            target_cat = "01_JK"
        elif "王昭君" in cname:
            target_cat = "02_王昭君"
        elif "西施" in cname:
            target_cat = "03_西施"
        elif "有马加奈" in cname:
            target_cat = "04_有马加奈"
        else:
            target_cat = "01_JK"

        categories[target_cat]["items"].append({
            "ref_id": r_id,
            "sha": sha,
            "role": categories[target_cat]["name"],
            "decision": "keep",
            "human_reason": rdata.get("reason") or rdata.get("note") or "",
            "title": rdata.get("title", ""),
            "source": rdata.get("source", {}),
            "file_path": str(img_p),
            "ext": ext,
            "width": adata.get("width", 0),
            "height": adata.get("height", 0)
        })

    # 2. Map inspirations
    for insp in insp_rows:
        i_id, sha, idata_str = insp
        idata = json.loads(idata_str)
        arow = cur.execute("SELECT data FROM assets WHERE id=?", (sha,)).fetchone()
        adata = json.loads(arow[0]) if arow else {}
        ext = adata.get("ext", "jpg")
        img_p = ROOT / "data" / "assets" / sha[:2] / sha / f"original.{ext}"

        categories["05_通用灵感"]["items"].append({
            "ref_id": idata.get("origin_reference_ids", [""])[0],
            "sha": sha,
            "role": "通用灵感 (Global Inspiration)",
            "decision": "active_inspiration",
            "human_reason": idata.get("reason") or idata.get("note") or "",
            "title": idata.get("title", ""),
            "source": idata.get("source", {}),
            "file_path": str(img_p),
            "ext": ext,
            "width": adata.get("width", 0),
            "height": adata.get("height", 0)
        })

    # Assign stable IDs per category
    for cat_key, cat_data in categories.items():
        prefix = cat_data["prefix"]
        for idx, item in enumerate(cat_data["items"]):
            item["asset_id"] = f"{prefix}_{idx+1:04d}"

    conn.close()
    return categories

def render_category_contact_sheet(cat_name, items, out_pdf_path):
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
            f"Photography Reference Lab · {cat_name} (Verified Kept)",
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

            bar_h = 60
            draw.rectangle([(x0, y0), (x1, y0 + bar_h)], fill="#2c2e35")
            draw.rectangle([(x0 + 10, y0 + 10), (x0 + 260, y0 + bar_h - 10)], fill="#0f1115", outline="#40444f", width=1)
            draw.text((x0 + 25, y0 + 14), item["asset_id"], font=header_font, fill="#ffffff")

            # Decision pill
            draw.rounded_rectangle([(x1 - 320, y0 + 10), (x1 - 15, y0 + bar_h - 10)], radius=6, fill="#1b4d3e")
            draw.text((x1 - 305, y0 + 16), "KEEP (人工确认保留)", font=small_font, fill="#4ade80")

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
            meta_line1 = f"角色: {item['role']} | 尺寸: {item['width']}x{item['height']} | 原标题: {item['title'][:25]}"
            meta_line2 = f"SHA: {item['sha'][:16]}... | (人工理由: 留空)"
            draw.text((x0 + 15, foot_y), meta_line1, font=small_font, fill="#c2c7d0")
            draw.text((x0 + 15, foot_y + 36), meta_line2, font=small_font, fill="#838896")

        pages.append(page_img)

    out_pdf_path.parent.mkdir(parents=True, exist_ok=True)
    pages[0].save(
        out_pdf_path,
        "PDF",
        resolution=300.0,
        save_all=True,
        append_images=pages[1:]
    )
    print(f"  + Generated contact sheet: {out_pdf_path.name} ({len(pages)} pages)")

def get_drive_service():
    sys.stdout.reconfigure(line_buffering=True)
    creds = Credentials.from_authorized_user_file(str(TOKEN_FILE), SCOPES)
    if creds.expired and creds.refresh_token:
        creds.refresh(Request())
        TOKEN_FILE.write_text(creds.to_json(), encoding="utf-8")
    return build("drive", "v3", credentials=creds)

def find_or_create_folder(service, folder_name, parent_id=None):
    query = f"name = '{folder_name}' and mimeType = 'application/vnd.google-apps.folder' and trashed = false"
    if parent_id:
        query += f" and '{parent_id}' in parents"
    res = service.files().list(q=query, spaces='drive', fields='files(id, name)').execute()
    files = res.get('files', [])
    if files:
        return files[0]['id']
    meta = {'name': folder_name, 'mimeType': 'application/vnd.google-apps.folder'}
    if parent_id:
        meta['parents'] = [parent_id]
    folder = service.files().create(body=meta, fields='id').execute()
    return folder.get('id')

def upload_file(service, file_path, folder_id, mime_type, target_name=None):
    p = Path(file_path)
    name = target_name or p.name
    # Check if already exists in folder
    query = f"name = '{name}' and '{folder_id}' in parents and trashed = false"
    res = service.files().list(q=query, spaces='drive', fields='files(id, name)').execute()
    files = res.get('files', [])
    if files:
        return files[0]['id']
    
    file_metadata = {'name': name, 'parents': [folder_id]}
    media = MediaFileUpload(str(p), mimetype=mime_type, resumable=True)
    f = service.files().create(body=file_metadata, media_body=media, fields='id, name').execute()
    return f.get('id')

def main():
    print("=== Fetching all verified (keep & inspiration) assets ===")
    categories = fetch_all_verified()
    total_items = sum(len(c["items"]) for c in categories.values())
    print(f"Total verified assets across all categories: {total_items}\n")

    service = get_drive_service()
    root_folder_name = "Photography Reference Lab - Verified Library (Keep & Inspirations)"
    root_folder_id = find_or_create_folder(service, root_folder_name)
    print(f"[Drive] Root Private Library Folder: '{root_folder_name}' (ID: {root_folder_id})\n")

    master_manifest = {
        "library_name": root_folder_name,
        "root_folder_id": root_folder_id,
        "total_assets": total_items,
        "categories": {}
    }

    uploaded_count = 0

    for cat_dir_name, cat_data in categories.items():
        cat_name = cat_data["name"]
        items = cat_data["items"]
        print(f"\n[{cat_dir_name}] Processing {len(items)} assets...")

        # 1. Create subfolder in Drive
        cat_folder_id = find_or_create_folder(service, cat_dir_name, parent_id=root_folder_id)
        
        # 2. Local export prep
        local_cat_dir = EXPORT_DIR / cat_dir_name
        local_cat_dir.mkdir(parents=True, exist_ok=True)

        # 3. Generate Contact Sheet PDF
        pdf_path = local_cat_dir / f"{cat_dir_name}_contact_sheet.pdf"
        render_category_contact_sheet(cat_name, items, pdf_path)
        pdf_drive_id = upload_file(service, pdf_path, cat_folder_id, "application/pdf")
        print(f"  + Uploaded PDF to Drive (ID: {pdf_drive_id})")

        # 4. Generate manifest.md for this category
        cat_manifest_lines = [
            f"# Verified Asset Manifest: {cat_name}",
            f"- **Folder**: `{cat_dir_name}`",
            f"- **Drive Folder ID**: `{cat_folder_id}`",
            f"- **Asset Count**: {len(items)}",
            "",
            "| Asset ID | Role | Decision | Reason | Dimensions | SHA256 (Original) |",
            "| :--- | :--- | :---: | :---: | :---: | :--- |"
        ]
        for it in items:
            cat_manifest_lines.append(
                f"| `{it['asset_id']}` | {it['role']} | `{it['decision']}` | (留空) | {it['width']}x{it['height']} | `{it['sha']}` |"
            )
        manifest_md_path = local_cat_dir / "manifest.md"
        manifest_md_path.write_text("\n".join(cat_manifest_lines), encoding="utf-8")
        manifest_drive_id = upload_file(service, manifest_md_path, cat_folder_id, "text/markdown")

        # 5. Upload individual images
        cat_assets_map = {}
        for it in items:
            aid = it["asset_id"]
            lp = Path(it["file_path"])
            ext = it["ext"]
            target_name = f"{aid}.{ext}"
            mime = f"image/{ext}" if ext != "jpg" else "image/jpeg"
            
            f_id = upload_file(service, lp, cat_folder_id, mime, target_name=target_name)
            uploaded_count += 1
            print(f"  [{uploaded_count}/{total_items}] Uploaded {target_name:<18} -> {f_id}")

            cat_assets_map[aid] = {
                "drive_file_id": f_id,
                "filename": target_name,
                "role": it["role"],
                "decision": it["decision"],
                "sha": it["sha"],
                "width": it["width"],
                "height": it["height"],
                "title": it["title"]
            }

        master_manifest["categories"][cat_dir_name] = {
            "name": cat_name,
            "folder_id": cat_folder_id,
            "contact_sheet_drive_id": pdf_drive_id,
            "manifest_drive_id": manifest_drive_id,
            "asset_count": len(items),
            "assets": cat_assets_map
        }

    # 6. Save master manifest locally and upload to root folder
    master_json_path = EXPORT_DIR / "library_manifest.json"
    master_json_path.write_text(json.dumps(master_manifest, ensure_ascii=False, indent=2), encoding="utf-8")
    master_drive_id = upload_file(service, master_json_path, root_folder_id, "application/json")
    print(f"\n[Drive] Uploaded Master library_manifest.json (ID: {master_drive_id})")

    print("\n" + "="*70)
    print("ALL VERIFIED ASSETS UPLOADED SUCCESSFULLY!")
    print(f"Root Folder Name: {root_folder_name}")
    print(f"Root Folder ID  : {root_folder_id}")
    print(f"Total Categories: {len(categories)}")
    print(f"Total Assets    : {total_items} images")
    print(f"Local Manifest  : {master_json_path}")
    print("="*70)

if __name__ == "__main__":
    main()
