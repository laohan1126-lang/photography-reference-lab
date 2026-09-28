# 2026-09-29 Collection Command Adapter Implementation

## User Intent and Recorded Boundaries

The user encountered "等待执行 / 受阻：未配置 LAB_COLLECTION_COMMAND；请下载任务 ZIP 交给本地 Agent，或配置适配器。没有自动后备浏览抓取或备用抓图。" in the web UI when clicking "启动已配置的本地采集 Agent".
When presented with options, the user chose Option B:
Configure a working local collection adapter (`LAB_COLLECTION_COMMAND`) so clicking the button in the UI directly triggers local agent collection.

### Boundaries
- Do not mutate or overwrite existing database assets or user decisions.
- Strictly adhere to `agent_collection.py` contract:
  - Command must be a JSON array of strings with `{task_file}` (or `{task_dir}`) and `{result_file}`.
  - Adapter must exit 0 and write a valid `result.zip` (Schema 3 CandidatePackage) containing `manifest.json`, visual preflight for each candidate, execution report, and images in `images/`.
  - Download only observed image bytes with valid headers and dimensions.
  - Report genuine execution logs and query records.
- Configure `run_server.sh` with `LAB_COLLECTION_COMMAND`.
- Verify with backend unit/integration tests and real execution on current job `7ba922ae411f4c74864f5d19348af5ba`.

## Outcome & Verification

### Implementation
1. Added `tools/collect_adapter.py`:
   - Conforms strictly to `agent_collection` transport contract.
   - Extracts character, costume, work, notes, and target count from unpacked job bundle.
   - Executes image search, downloads real full/original resolution images, verifies with PIL (minimum dimensions 250px, valid formats).
   - Generates Schema 3 compliant CandidatePackage zip (`manifest.json` with visual preflight, execution report, and images).
2. Added `tests/test_collect_adapter.py`:
   - Validates that `run_collection_attempt` executes the adapter, receives the zip bundle, imports candidates, and records receipts properly.
3. Updated `/home/dell/projects/photography-reference-lab-regression/run_server.sh`:
   - Added `export LAB_COLLECTION_COMMAND='["/home/dell/projects/photography-reference-lab-regression/.venv/bin/python", "/mnt/d/AI PROJECTS/photography-reference-lab/tools/collect_adapter.py", "{task_file}", "{result_file}"]'`.
   - Restarted live server on port 18765.

### Verification Results
- `pytest -q tests/test_library.py tests/test_imports_jobs.py tests/test_workers.py tests/test_operations.py tests/test_personal_library.py tests/test_collection_runner.py tests/test_collect_adapter.py`:
  **110 passed, 1 warning in 20.89s**.
- `node --check web/app.js`: exit code 0.
- Live server test against real job `7ba922ae411f4c74864f5d19348af5ba` (王昭君 · 长夜焕生):
  - HTTP 200 returned.
  - Successfully imported 30 real candidates.
  - Status transitioned from `blocked` to `succeeded`.
  - All candidates now available in the project for human review.
