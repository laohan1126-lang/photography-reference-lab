# Visible persistent Playwright collection trial

Owner: “先尝试使用 Playwright Python，配一个独立、可见、保留登录状态的采集浏览器，你来安排和审计，派子代理去执行。”

Parent owns integration and acceptance. Start with an explicit independent browser trial, not a replacement of the live collector. Preserve originals, decisions, existing jobs/budgets and existing Edge profiles. Do not copy browser credentials, bypass site restrictions or silently fall back to headless mode. Earlier BrowserSkill work and incomplete real-image acceptance remain separate.

Transaction: 01a18cc3-9d1c-7d01-9d11-2900ae4af13a. Contract recorded before implementation. Candidate code is isolated under `.local/worktrees/playwright-trial/implementation`; profile and receipts are ignored under `.local`.

Acceptance frozen before candidate review: (1) new dedicated persistent profile and visible window; (2) local HTTP navigation/read/write, close and restart with state retained; (3) actual local attachment download and content/hash check; (4) real source page access, explicit login/challenge handling, actual login persistence only after user login; (5) no reference-library data changes. Synthetic local state does not establish real site authentication or image acquisition.

Delegation preflight: implementation child Chandrasekhar `01a18cc4-9b02-7b73-9854-f1e1ffe0d641`; Magpie route1793362674277 served opencode-go/deepseek-v4.1-flash, HTTP200. Browser acceptance child Harvey `01a18cc4-9e38-7d22-ab36-94602453c2fe`; route1793362674276 served codex/gpt-6.1-terra, HTTP200. Both initially returned tools-free markers. These routes establish preflight only, not all subsequent calls.

Status: implementation in progress; no browser trial accepted, no commit/push or Notion result claimed.

## Implemented trial and verification

Added standalone `tools/playwright_collection_trial.py`, its local fixture verifier, and scoped tests. The main collector is not switched. Launch from the repository using `.venv/Scripts/python.exe -X utf8 -m tools.playwright_collection_trial --url https://www.xiaohongshu.com/`. The visible window uses `.local/playwright-collection-profile`; closing it preserves that profile. Running from a temporary agent command still ties the window to its controlling Python process. For ordinary manual use, run the command in the owner's terminal; no global daemon or scheduled task was added.

Parent review caught a non-pumping sleep loop and unsafe server-controlled download filenames. First directed revision fixed event pumping, explicit30s launch timeout, propagated non-close errors and generated safe unique download paths. Actual candidate verification then failed on Playwright1.63's `Page.goto: Download is starting`; second revision accepted that exact signal while still requiring the real download event and verified bytes. Other network errors remain failures.

Final candidate SHA256 `ecfe80def7ab3b679bbc55c0312bf04005630243d273a7df825d6a58e03445f0`. Parent integrated identical bytes and ran `python -m unittest discover -s tests -p test_playwright_collection_trial.py -v`:14 passed. Terra executed the actual headed candidate verifier: local HTTP navigation, DOM input, attachment SHA256 and close/reopen localStorage checks passed, exit0. This is not real-image acquisition. Raw output and separate independent baseline are under `.local/playwright-collection-trial/verification/receipt.json`.

TUN investigation: owner disclosed enabling TUN the previous day. Read-only Windows inspection showed iKuuuVPN active with a default route through198.18.0.2;127/8 stayed on Loopback. Owner then disabled TUN, and parent confirmed only WLAN default route remained. Same Playwright profile and same Xiaohongshu URL: TUN-on observation was HTTP200/empty title/no text; TUN-off navigation took4.26s and showed the expected homepage/login modal. This supports a relationship between TUN and site loading in this trial, not proof that all earlier BrowserSkill CDP failures had that cause. No proxy settings were changed by agents.

Owner confirmed manual login and normal window closure. Actual site-login persistence is pending the same-profile reopening check. The termination experiment separately confirmed that killing the parent Python process closes Chromium while retaining the profile; it was not relabelled normal window closure. Private profile and screenshots remain ignored and excluded from publication.

Final site check: owner-confirmed normal close was followed by verification of old process exit and zero Chromium processes using that profile. Reopened the same profile: HTTP200,10.53s, login button/text absent and personal entry visible. No account details were logged. Actual site login persistence PASS. The independent observer logged TargetClosedError/exit1 when its page was manually closed; this is preserved. The candidate's manual window-close lifecycle was unit checked but not separately live accepted. Its real context-close/reopen fixture did pass. Visible authenticated window retained (verification session21845, PID1764 at handoff). No real reference image was downloaded or imported and the default collector remains unchanged.

The scoped trial is implemented and verified to the limits above. Publication covers only these new trial scripts/tests and this record; earlier tasks, BrowserSkill patches, private data and historical deletions remain excluded.
