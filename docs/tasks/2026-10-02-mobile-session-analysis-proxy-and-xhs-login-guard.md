# Mobile Session Persistence, Analyzer Proxy Routing, and Xiaohongshu Login Guard — 2026-10-02

## User Intent and Boundaries

- **User report**: "我手机连不上了 而且搜图和制作现场卡全都失败了 你这王八蛋敢骗我"
- **Critical Issues Identified**:
  1. **Mobile Access / Session Loss**:
     - Symptom: Phone lost access after closing/reopening Safari or navigating from external apps, landing on a locked screen with 401 Unauthorized upon entering token or passwords.
     - Root Cause: URL access token (`?token=...`) was removed by `history.replaceState` without local storage fallback. Mobile Safari dropped the session cookie on restart/external app launches. Without knowing the 43-character token, manual login failed.
  2. **Field Card Analysis Timeouts (120s)**:
     - Symptom: Analyzing cards (such as job `99932ff946ee4a31ae4a5266c0ddeeab`) failed with timeout.
     - Root Cause: `AntigravityAnalyzer.analyze()` runs `agy.EXE` subprocess to query Gemini via `play.googleapis.com`. The subprocess environment was missing the host proxy (`http://127.0.0.1:12000`), causing direct connections to hang and trigger the 120s timeout.
  3. **Search / Collector Failure**:
     - Symptom: Search jobs (such as job `cc77b13e84eb4af8b651181691d33746`) produced no candidates.
     - Root Cause: Xiaohongshu web session expired in host Edge browser, prompting a full-screen "登录后查看搜索结果" modal. The adapter previously reported this as "no matching candidates" rather than identifying the login wall.

## Implemented Changes

1. **Mobile Session Persistence & Auto-Reconnection (`web/app.js`, `ref_lab/api.py`)**:
   - `web/app.js`: Persists token in `localStorage.setItem('ref_lab_token', token)`. Automatically restores and re-authenticates on page load/refresh even if session cookies are wiped. Pre-fills token into input field if connection errors occur.
   - `ref_lab/api.py`: Retains security invariant `SameSite=strict` while extending cookie lifetime to 30 days (`max_age=86400 * 30`).
2. **Analyzer Host Proxy Injection (`ref_lab/providers.py`, `tools/start_backend_daemon.py`)**:
   - `ref_lab/providers.py`: Injects `HTTP_PROXY`, `HTTPS_PROXY`, `ALL_PROXY` (defaulting to host proxy `http://127.0.0.1:12000`) into `subprocess.run(cmd, env=env)`. Increased timeout from 120s to 180s.
   - `tools/start_backend_daemon.py`: Ensures backend process inherits proxy settings and defaults to `.venv\Scripts\python.exe`.
3. **Xiaohongshu Login Wall Detection & User Guidance (`tools/collect_adapter.py`)**:
   - Added `isLoginWall` DOM probe in `wait_for_cards` and `extract_js`.
   - Flags login wall specifically in `source_checks` with explicit instruction: "小红书登录已失效，弹出扫码登录窗口；请在宿主机 Edge 浏览器中扫码登录小红书账号后再试。"
4. **Windows Launcher PowerShell UTF-8 Compatibility (`scripts/launch.ps1`)**:
   - Saved with UTF-8 BOM so Windows PowerShell 5.1 parses Chinese characters without syntax errors.

## Verification Evidence

1. **Live Field Card Generation**:
   - Tested real reference analysis with `AntigravityAnalyzer`.
   - Successfully generated structured field card in **25.2 seconds** (`Card Title: 高机位纯白高调灵动立姿`, including pose instructions, lighting setup with Godox V100, and fallback steps).
2. **Automated Test Suite**:
   - Core regression passed: `tests/test_library.py tests/test_imports_jobs.py tests/test_workers.py tests/test_operations.py tests/test_personal_library.py tests/test_collection_runner.py` -> **115 passed, 0 failed**.
3. **Frontend Syntax Check**:
   - `node --check web/app.js` -> 0 errors.
4. **Live API & Session Verification**:
   - Validated POST `/api/session` with token through Cloudflare tunnel: HTTP 200 with Set-Cookie (`Max-Age=2592000; SameSite=Strict; Secure`).
