"""Upload 06_排雷与反例库_含人工原因 to Google Drive.
Packages the 10 human-rejected reference items with explicit rejection reasons:
1. Generates 06_排雷与反例库_contact_sheet.pdf with clear visual rejection badges and printed human reasons.
2. Generates manifest.md with full tabular provenance and reasons.
3. Uploads each original image to Google Drive subfolder with File Description metadata:
   - 【状态】淘汰 (Reject)
   - 【人工排除原因】<reason>
   - 【所属项目】<project_name>
   - 【原标题】<title>
   - 【Asset SHA】<sha>
4. Updates library_manifest.json locally and syncs to Google Drive root folder.
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
REJECT_EXPORT_DIR = EXPORT_DIR / "06_排雷与反例库_含人工原因"
REJECT_EXPORT_DIR.mkdir(parents=True, exist_ok=True)

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

def fetch_rejection_items():
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()
    projects = dict(cur.execute("SELECT id, data FROM projects").fetchall())

    rows = cur.execute("""
        SELECT id, project_id, asset_sha, data 
        FROM refs 
        WHERE decision='reject'
        ORDER BY project_id, id
    """).fetchall()

    items = []
    for rid, pid, sha, dstr in rows:
        d = json.loads(dstr)
        reason = (d.get("rejection_reason") or "").strip()
        if not reason:
            continue
        pdata = json.loads(projects.get(pid, "{}"))
        pname = pdata.get("character_name") or pdata.get("character") or pdata.get("name") or pid

        arow = cur.execute("SELECT data FROM assets WHERE id=?", (sha,)).fetchone()
        adata = json.loads(arow[0]) if arow else {}
        ext = adata.get("ext", "jpg")
        img_p = ROOT / "data" / "assets" / sha[:2] / sha / f"original.{ext}"

        items.append({
            "ref_id": rid,
            "project_id": pid,
            "project_name": pname,
            "sha": sha,
            "reason": reason,
            "is_aesthetic_negative": d.get("is_aesthetic_negative", False),
            "title": d.get("title", ""),
            "width": adata.get("width", 0),
            "height": adata.get("height", 0),
            "ext": ext,
            "file_path": str(img_p)
        })

    for idx, it in enumerate(items):
        it["asset_id"] = f"REJECT_{idx+1:04d}"

    conn.close()
    return items

def render_rejection_contact_sheet(items, out_pdf_path):
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
    body_bold_font = load_font(26, bold=True)
    small_font = load_font(22, bold=False)

    pages = []
    for p_idx in range(total_pages):
        page_img = Image.new("RGB", (page_w, page_h), "#18191c")
        draw = ImageDraw.Draw(page_img)

        # Header banner
        draw.rectangle([(margin_x, 60), (page_w - margin_x, 140)], fill="#2d1c1c")
        draw.text(
            (margin_x + 30, 80),
            "Photography Reference Lab · 06_排雷与反例库 (人工原因标注)",
            font=title_font,
            fill="#ff8b8b"
        )
        page_str = f"Page {p_idx+1} of {total_pages} (Items {p_idx*per_page+1} - {min((p_idx+1)*per_page, len(items))})"
        draw.text(
            (page_w - margin_x - 550, 88),
            page_str,
            font=body_font,
            fill="#d1a7a7"
        )

        page_items = items[p_idx * per_page : (p_idx + 1) * per_page]
        for i, item in enumerate(page_items):
            c = i % cols
            r = i // cols
            x0 = margin_x + c * (cell_w + 80)
            y0 = margin_top + r * (cell_h + 40)
            x1 = x0 + cell_w
            y1 = y0 + cell_h

            draw.rectangle([(x0, y0), (x1, y1)], fill="#201c1c", outline="#4a2a2a", width=2)

            bar_h = 60
            draw.rectangle([(x0, y0), (x1, y0 + bar_h)], fill="#302020")
            draw.rectangle([(x0 + 10, y0 + 10), (x0 + 300, y0 + bar_h - 10)], fill="#150f0f", outline="#593232", width=1)
            draw.text((x0 + 25, y0 + 14), item["asset_id"], font=header_font, fill="#ffffff")

            # Decision pill (Red for REJECT)
            draw.rounded_rectangle([(x1 - 320, y0 + 10), (x1 - 15, y0 + bar_h - 10)], radius=6, fill="#5c1d1d")
            draw.text((x1 - 305, y0 + 16), "REJECT (人工排除)", font=small_font, fill="#fca5a5")

            img_area_top = y0 + bar_h + 15
            img_area_bottom = y1 - 120
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

            foot_y = y1 - 110
            meta_line1 = f"项目: {item['project_name']} | 尺寸: {item['width']}x{item['height']} | 标题: {item['title'][:20]}"
            reason_line = f"【排除原因】{item['reason']}"
            if len(reason_line) > 36:
                reason_line = reason_line[:35] + "..."
            meta_line2 = f"SHA: {item['sha'][:20]}..."

            draw.text((x0 + 15, foot_y), meta_line1, font=small_font, fill="#b5a4a4")
            draw.text((x0 + 15, foot_y + 32), reason_line, font=body_bold_font, fill="#ff6b6b")
            draw.text((x0 + 15, foot_y + 68), meta_line2, font=small_font, fill="#786767")

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

def upload_file(service, file_path, folder_id, mime_type, target_name=None, description=None):
    p = Path(file_path)
    name = target_name or p.name
    query = f"name = '{name}' and '{folder_id}' in parents and trashed = false"
    res = service.files().list(q=query, spaces='drive', fields='files(id, name, description)').execute()
    files = res.get('files', [])
    
    file_metadata = {'name': name, 'parents': [folder_id]}
    if description:
        file_metadata['description'] = description

    if files:
        file_id = files[0]['id']
        # If description is provided and differs, update metadata
        if description and files[0].get('description') != description:
            service.files().update(fileId=file_id, body={'description': description}).execute()
        return file_id
    
    media = MediaFileUpload(str(p), mimetype=mime_type, resumable=True)
    f = service.files().create(body=file_metadata, media_body=media, fields='id, name, description').execute()
    return f.get('id')

def update_file_content(service, file_id, file_path, mime_type):
    media = MediaFileUpload(str(file_path), mimetype=mime_type, resumable=True)
    return service.files().update(fileId=file_id, media_body=media).execute()

def main():
    print("=== Fetching all human-rejected assets with reasons ===")
    items = fetch_rejection_items()
    print(f"Total rejection items with human reasons: {len(items)}\n")
    for it in items:
        print(f"  - [{it['asset_id']}] ({it['project_name']}) {it['reason']}")

    service = get_drive_service()
    root_folder_name = "Photography Reference Lab - Verified Library (Keep & Inspirations)"
    root_folder_id = find_or_create_folder(service, root_folder_name)
    print(f"\n[Drive] Root Private Library Folder: '{root_folder_name}' (ID: {root_folder_id})")

    cat_dir_name = "06_排雷与反例库_含人工原因"
    cat_folder_id = find_or_create_folder(service, cat_dir_name, parent_id=root_folder_id)
    print(f"[Drive] Created Subfolder: '{cat_dir_name}' (ID: {cat_folder_id})\n")

    # 1. Render Contact Sheet PDF
    pdf_path = REJECT_EXPORT_DIR / f"{cat_dir_name}_contact_sheet.pdf"
    render_rejection_contact_sheet(items, pdf_path)
    pdf_drive_id = upload_file(service, pdf_path, cat_folder_id, "application/pdf")
    print(f"  + Uploaded PDF to Drive (ID: {pdf_drive_id})")

    # 2. Upload individual images with Description metadata
    print("\nUploading images with Google Drive Description metadata:")
    cat_assets_map = {}
    for idx, it in enumerate(items):
        aid = it["asset_id"]
        lp = Path(it["file_path"])
        ext = it["ext"]
        target_name = f"{aid}.{ext}"
        mime = f"image/{ext}" if ext != "jpg" else "image/jpeg"

        # Drive file description with human rejection reason
        desc = (
            f"【状态】淘汰 (Reject - 人工排除)\n"
            f"【排除原因】{it['reason']}\n"
            f"【所属项目】{it['project_name']}\n"
            f"【原始标题】{it['title']}\n"
            f"【尺寸】{it['width']}x{it['height']}\n"
            f"【Asset SHA256】{it['sha']}"
        )

        f_id = upload_file(service, lp, cat_folder_id, mime, target_name=target_name, description=desc)
        print(f"  [{idx+1}/{len(items)}] {target_name} -> {f_id} | 原因: {it['reason']}")

        cat_assets_map[aid] = {
            "drive_file_id": f_id,
            "filename": target_name,
            "project_name": it["project_name"],
            "decision": "reject",
            "reason": it["reason"],
            "sha": it["sha"],
            "width": it["width"],
            "height": it["height"],
            "title": it["title"]
        }

    # 3. Generate manifest.md for this category
    manifest_lines = [
        f"# 排雷与反例库清单: {cat_dir_name}",
        f"- **Folder**: `{cat_dir_name}`",
        f"- **Drive Folder ID**: `{cat_folder_id}`",
        f"- **Asset Count**: {len(items)}",
        f"- **说明**: 本目录包含人工严格排除的负样本，每张图片在 Google Drive 的 Description 元数据中均已写入具体的排除理由，供排雷避坑参考。",
        "",
        "| Asset ID | 所属项目 | 淘汰决策 | 人工排除原因 | 尺寸 | Drive File ID | SHA256 |",
        "| :--- | :--- | :---: | :--- | :---: | :--- | :--- |"
    ]
    for it in items:
        aid = it["asset_id"]
        fid = cat_assets_map[aid]["drive_file_id"]
        manifest_lines.append(
            f"| `{aid}` | {it['project_name']} | `reject` | **{it['reason']}** | {it['width']}x{it['height']} | `{fid}` | `{it['sha'][:16]}...` |"
        )
    manifest_md_path = REJECT_EXPORT_DIR / "manifest.md"
    manifest_md_path.write_text("\n".join(manifest_lines), encoding="utf-8")
    manifest_drive_id = upload_file(service, manifest_md_path, cat_folder_id, "text/markdown")
    print(f"  + Uploaded manifest.md to Drive (ID: {manifest_drive_id})")

    # 4. Update master library_manifest.json
    master_json_path = EXPORT_DIR / "library_manifest.json"
    if master_json_path.exists():
        master_data = json.loads(master_json_path.read_text(encoding="utf-8"))
    else:
        master_data = {
            "library_name": root_folder_name,
            "root_folder_id": root_folder_id,
            "total_assets": 0,
            "categories": {}
        }

    master_data["categories"][cat_dir_name] = {
        "name": "排雷与反例库 (含人工原因)",
        "folder_id": cat_folder_id,
        "contact_sheet_drive_id": pdf_drive_id,
        "manifest_drive_id": manifest_drive_id,
        "asset_count": len(items),
        "assets": cat_assets_map
    }
    master_data["total_assets"] = sum(c.get("asset_count", len(c.get("assets", {}))) for c in master_data["categories"].values())
    master_json_path.write_text(json.dumps(master_data, ensure_ascii=False, indent=2), encoding="utf-8")

    # Sync updated master manifest to root folder
    master_drive_id = upload_file(service, master_json_path, root_folder_id, "application/json")
    print(f"\n[Drive] Synced updated Master library_manifest.json (ID: {master_drive_id})")

    print("\n" + "="*70)
    print("06_排雷与反例库_含人工原因 UPLOADED SUCCESSFULLY!")
    print(f"Subfolder ID   : {cat_folder_id}")
    print(f"Total Negative : {len(items)} images")
    print(f"Contact Sheet  : {pdf_path.name} (ID: {pdf_drive_id})")
    print(f"Master Manifest: {master_json_path}")
    print("="*70)

if __name__ == "__main__":
    main()
