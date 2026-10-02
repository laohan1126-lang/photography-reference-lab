# No-Auth Mode (完全免密访问模式) — 2026-10-02

## User Intent and Boundaries

- **User report**: "访问口令能不能不要啊 烦死了 我只自己用 手机上还要访问口令"
- **User decision**: 彻底关闭口令（完全免密模式）：手机打开任何网址都直接进入，不再有任何锁屏或输入框。
- **Observable Acceptance Criteria**:
  1. 手机端访问 `https://ref.koshikorato.top`（不带任何 `?token=...` 参数），直接进入工作区，不弹出访问口令输入框，不显示锁屏遮罩。
  2. 桌面端访问 `http://127.0.0.1:18765` 直接进入，无需输入口令。
  3. API 读写正常（加载项目、查看参考、标记审美、新建项目），不被 401 拦截。
  4. 锁定按钮在完全免密模式下自动隐藏，避免误锁后无法解锁。
  5. 保持可逆性：通过 `data/no-auth` 文件或环境变量 `LAB_NO_AUTH=1` 开关，随时可无缝切换回安全模式。

## Implemented Changes

1. **Runtime Settings & Discovery (`ref_lab/config.py`)**:
   - Added `no_auth: bool = False` to `Settings`.
   - `Settings.from_env()` automatically detects `data/no-auth` marker file, `.local/windows-runtime.json`, and `LAB_NO_AUTH=1`.
   - If `no_auth` is enabled, minimum token length restriction is relaxed while preserving an internal secret for CSRF and signing primitives.
2. **Access Control & Session Endpoint (`ref_lab/api.py`)**:
   - `access_control` middleware sets `request.state.authenticated = True` when `settings.no_auth` is True, allowing direct unauthenticated access to all API routes.
   - `GET /api/session` automatically returns `{"authenticated": true, "no_auth": true, "csrf": "..."}` and issues the 30-day session cookie for CSRF writes.
3. **Frontend Experience (`web/app.js`)**:
   - `boot()` records `state.noAuth = Boolean(session.no_auth)`.
   - In no-auth mode, the sidebar "锁定参考库" button is hidden.
   - `lockScreen()` is bypassed in no-auth mode to ensure the user never gets locked out.
4. **Windows Launcher Banner (`scripts/launch.ps1`)**:
   - Displays clear banner status when completely passwordless mode is active.
5. **Marker Configuration (`data/no-auth`)**:
   - Created `data/no-auth` marker in local data directory.
6. **Regression Tests (`tests/test_library.py`)**:
   - Added `test_no_auth_mode` verifying unauthenticated session retrieval and resource creation.

## Verification Evidence

1. **Automated Regression**:
   - Pytest full regression suite: `116 passed, 0 failed` in 34.24s.
   - `node --check web/app.js`: exit code 0.
2. **Live Local Endpoint Verification**:
   - `curl http://127.0.0.1:18765/api/session` without any credentials -> returned `{"authenticated": true, "no_auth": true}`.
   - `curl http://127.0.0.1:18765/api/projects` -> HTTP 200 with full projects payload.
3. **Live Public Tunnel Endpoint Verification**:
   - `curl -A "iPhone" https://ref.koshikorato.top/api/session` without any credentials -> HTTP 200 `{"authenticated": true, "no_auth": true}`.
   - `curl -A "iPhone" https://ref.koshikorato.top/api/projects` -> HTTP 200 with full projects payload.
