# Confirmed references auto-archive to character folder — 2026-10-01

## User intent and boundaries

- **User intent (in original wording)**:
  > “就是现在这个图片位置的这个规则我不知道你是怎么定的，但是我还是希望能够稍微优化一下。我看了一下这个参考原图，比如说我现在在看托尔，然后托尔我这里未淘汰的有14张，然后我给它全部定为本角色参考，然后确定到本角色参考以后，这个文件位置它依旧是这个你给它一些数字的排列，然后并不是把这些图片放在同一个文件夹里面。然后每一个都是一个文件夹，里面是原图，然后jpg什么的。我希望就是它们能不能一旦被我确认以后自动归位到一个文件夹里面去。就是比如说这个分类应该是某角色，比如说托尔，然后下面子文件夹已确认，然后里面是这些jpg。一旦确认以后就以jpg的形式放过去，然后在那个页面里面这个文件位置也是，就会以保留导出目录，或者说你下面再加一个新的位置，以归档至哪个文件夹。”
- **Key requirements**:
  1. Once a reference is confirmed/kept ("本角色参考" / `decision == "keep"`), automatically archive/sync it into a clean, human-readable directory: `<data_dir>/exports/<角色名>/已确认/`.
  2. All archived images in this directory must be formatted as `.jpg` images, with clean human-readable naming (e.g., `01_标题.jpg`), placed together in this single directory rather than scattered across CAS hash folders.
  3. If a reference is rejected or un-kept, it should be removed from the "已确认" folder so the folder strictly reflects current confirmed references.
  4. On the web detail page, display the archived path (e.g. `已归档至：.../exports/托尔/已确认/01_xxx.jpg` or target folder when not yet kept), alongside the underlying CAS original path.
  5. Provide easy Windows Explorer reveal buttons: open the specific archived `.jpg` file in Explorer, and open the character's `已确认` folder.
  6. Existing kept references (such as the 14 Thor references) must be immediately synced and archived to `exports/托尔/已确认/`.
- **Invariants & Safety**:
  - CAS asset storage (`data/assets/...`) remains the immutable single source of truth for original bytes. Never delete or mutate original CAS asset files.
  - The human-facing archive directory is derived from project decisions and can be safely re-generated or updated idempotently.
  - Safe path sanitization for character names and titles on Windows.

## Acceptance Criteria

1. **Auto-archive logic**:
   - Calling decision update (`keep`) immediately syncs/exports the image to `<data_dir>/exports/<character>/已确认/<idx>_<title>.jpg` as a standard, high-quality JPEG.
   - Changing decision to `reject` or clearing decision removes the file from `已确认`.
2. **Batch & Self-healing sync**:
   - `sync_project_confirmed_archive(project_id)` reliably synchronizes all `keep` references for a project.
   - Thor's 14 kept references exist in `data/exports/托尔/已确认/` with valid JPEG headers and viewable images.
3. **API & UI metadata**:
   - `reference` / `references` response includes `archive_dir` and `archive_path` (when kept).
   - Detail panel in `web/app.js` displays the archive status and location clearly.
   - Quick action buttons to reveal the archived file or open the character's `已确认` folder in Windows Explorer.
4. **Verification**:
   - Python unit tests covering archive creation, update on decision change, deletion on reject, and path sanitization.
   - Manual/API verification on Thor's 14 references and existing projects.
   - JavaScript syntax verification (`node --check web/app.js`).

## Outcomes

### Implemented

- `ref_lab/archiver.py`:
  - Added `sanitize_filename` for cross-platform safe naming.
  - Added `get_project_archive_dir` targeting `<data_dir>/exports/<character>/已确认`.
  - Added `export_asset_as_jpeg` to safely convert any format (RGBA, PNG, WebP) to high-quality JPEG (Quality 95).
  - Added `sync_project_confirmed_archive` for idempotent folder synchronization and stale image cleanup.
- `ref_lab/service.py`:
  - `_decorate`: computes `archive_dir` and `archive_path` for references.
  - `edit_reference`, `restore_reference`: hooks `sync_project_confirmed_archive` on decision/lane/title change so files are immediately synced to character archive.
- `ref_lab/api.py`:
  - Updated `reveal_reference` to prioritize revealing the archived `.jpg` file in Windows Explorer.
  - Updated `reveal_project_export` to open the character's `已确认` folder.
  - Added `POST /api/projects/{project_id}/sync-archive` endpoint.
- `web/app.js` & `web/styles.css`:
  - Highlighted `已归档至：<archive_path>` with a clean green badge.
  - Added buttons: `📂 定位归档 JPG` and `📁 打开已确认文件夹`.
  - Preserved underlying CAS original path as secondary metadata with quick inspect button.
  - Updated confirmation toast.

### Verification Evidence

1. `tests/test_confirmed_archive.py`: 5 passed covering filename sanitization, archive directory derivation, JPEG conversion, project archive sync, and full API auto-archive & reveal flow.
2. Regression suite: `.venv/Scripts/python.exe -m pytest -q tests/test_confirmed_archive.py tests/test_library.py tests/test_imports_jobs.py tests/test_workers.py tests/test_operations.py tests/test_personal_library.py tests/test_collection_runner.py`: **120 passed, 0 failed**.
3. `node --check web/app.js`: exit 0, no syntax errors.
4. Real data sync: all 14 kept references of "托尔" now exist in `D:\AI PROJECTS\photography-reference-lab\data\exports\托尔\已确认\` as readable `.jpg` files (`01_小林家的龙女仆，今日限定营业中.jpg` through `14_小林家的龙女仆.jpg`). Verified via live authenticated HTTP API (`GET /api/projects/{id}/references`).
5. Live Windows service: active daemon running at `http://127.0.0.1:18765`.
