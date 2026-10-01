"""Upload Pilot Batch 001 to user's private Google Drive folder with minimal scope drive.file."""
import os
import sys
import json
from pathlib import Path
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
from googleapiclient.http import MediaFileUpload

ROOT = Path(__file__).resolve().parent.parent
LOCAL_DIR = ROOT / ".local"
CLIENT_SECRET_FILE = LOCAL_DIR / "client_secret.json"
TOKEN_FILE = LOCAL_DIR / "drive_token.json"
BATCH_DIR = ROOT / "batches" / "photography_batch_001"

# Strictly minimal scope: only files created/opened by this app
SCOPES = ["https://www.googleapis.com/auth/drive.file"]

def get_drive_service():
    sys.stdout.reconfigure(line_buffering=True)
    creds = None
    if TOKEN_FILE.exists():
        creds = Credentials.from_authorized_user_file(str(TOKEN_FILE), SCOPES)
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            flow = InstalledAppFlow.from_client_secrets_file(str(CLIENT_SECRET_FILE), SCOPES)
            print("\n" + "="*70, flush=True)
            print("[OAuth] 正在打开浏览器以完成 Google 账号授权...", flush=True)
            print("[OAuth] 权限范围: https://www.googleapis.com/auth/drive.file (最小特权)", flush=True)
            print("="*70 + "\n", flush=True)
            creds = flow.run_local_server(port=0, open_browser=True)
        TOKEN_FILE.write_text(creds.to_json(), encoding="utf-8")
        print(f"[OAuth] 授权成功！Token 已安全保存至 {TOKEN_FILE}", flush=True)
    
    return build("drive", "v3", credentials=creds)

def find_or_create_folder(service, folder_name):
    # Search if folder already exists in root
    query = f"name = '{folder_name}' and mimeType = 'application/vnd.google-apps.folder' and trashed = false"
    res = service.files().list(q=query, spaces='drive', fields='files(id, name)').execute()
    files = res.get('files', [])
    if files:
        folder_id = files[0]['id']
        print(f"[Drive] Reusing existing folder: '{folder_name}' (ID: {folder_id})")
        return folder_id
    
    # Create private folder
    meta = {
        'name': folder_name,
        'mimeType': 'application/vnd.google-apps.folder'
    }
    folder = service.files().create(body=meta, fields='id').execute()
    folder_id = folder.get('id')
    print(f"[Drive] Created private folder: '{folder_name}' (ID: {folder_id})")
    return folder_id

def upload_file(service, file_path, folder_id, mime_type, target_name=None):
    p = Path(file_path)
    name = target_name or p.name
    file_metadata = {
        'name': name,
        'parents': [folder_id]
    }
    media = MediaFileUpload(str(p), mimetype=mime_type, resumable=True)
    f = service.files().create(body=file_metadata, media_body=media, fields='id, name, size').execute()
    file_id = f.get('id')
    print(f"  + Uploaded: {name:<20} | File ID: {file_id}")
    return file_id

def main():
    if not CLIENT_SECRET_FILE.exists():
        print(f"Error: {CLIENT_SECRET_FILE} not found.")
        sys.exit(1)

    print("=== Starting Google Drive Upload for Pilot Batch 001 ===")
    service = get_drive_service()

    folder_name = "Photography Reference Lab - Pilot Batch 001"
    folder_id = find_or_create_folder(service, folder_name)

    # 1. Upload Core Batch Files
    print("\n--- Uploading Core Batch Documents ---")
    core_files = {}
    
    pdf_path = BATCH_DIR / "contact_sheet.pdf"
    if pdf_path.exists():
        core_files["contact_sheet.pdf"] = upload_file(service, pdf_path, folder_id, "application/pdf")
        
    manifest_path = BATCH_DIR / "manifest.md"
    if manifest_path.exists():
        core_files["manifest.md"] = upload_file(service, manifest_path, folder_id, "text/markdown")
        
    delta_path = BATCH_DIR / "batch_delta.md"
    if delta_path.exists():
        core_files["batch_delta.md"] = upload_file(service, delta_path, folder_id, "text/markdown")

    # 2. Upload 36 Individual Images with Stable Asset IDs
    print("\n--- Uploading 36 Individual Asset Images with Stable IDs ---")
    raw_items_path = BATCH_DIR / "items_raw.json"
    if not raw_items_path.exists():
        from tools.generate_pilot_batch import fetch_sample
        items = fetch_sample()
    else:
        items = json.loads(raw_items_path.read_text(encoding="utf-8"))

    asset_map = {}
    for item in items:
        aid = item["asset_id"]
        local_p = Path(item["file_path"])
        ext = item.get("ext", local_p.suffix.lstrip("."))
        target_name = f"{aid}.{ext}"
        mime = f"image/{ext}" if ext != "jpg" else "image/jpeg"
        
        file_id = upload_file(service, local_p, folder_id, mime, target_name=target_name)
        asset_map[aid] = {
            "drive_file_id": file_id,
            "filename": target_name,
            "role": item["role"],
            "decision": item["decision"],
            "sha": item["sha"],
            "width": item.get("width"),
            "height": item.get("height")
        }

    # 3. Save Structured Drive Manifest locally for Dot
    result_manifest = {
        "batch_id": "photography_batch_001",
        "folder_name": folder_name,
        "folder_id": folder_id,
        "core_files": core_files,
        "asset_count": len(asset_map),
        "assets": asset_map
    }

    manifest_output = BATCH_DIR / "drive_manifest.json"
    manifest_output.write_text(json.dumps(result_manifest, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"\n[Drive] Upload complete! Saved Drive manifest to: {manifest_output}")

    print("\n" + "="*70)
    print("DELIVERY FOR DOT & USER:")
    print(f"Drive Folder Name: {folder_name}")
    print(f"Drive Folder ID  : {folder_id}")
    print(f"Total Assets     : {len(asset_map)} images + {len(core_files)} documents")
    print("="*70)

if __name__ == "__main__":
    main()
