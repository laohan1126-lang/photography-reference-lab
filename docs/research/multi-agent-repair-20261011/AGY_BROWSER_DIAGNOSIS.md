# Independent AGY / Chrome diagnostic — integration remains conditional

Root investigated the prior `D:/AI PROJECTS/agy-browser-check-20261011-01a126b7/RESULT.md`, original `/browser` stream and the precise child transcript. AGY did not judge its own repair. No new AGY model call or three-party video research was made this turn.

## Observed versions, target and launch arguments

- `Get-Command agy`: `C:/Users/Dell/AppData/Local/agy/bin/agy.exe`; `agy --version`: **1.3.3**.
- Installed and CDP-reported Chrome: **154.0.8037.98**, executable `C:/Program Files/Google/Chrome/Application/chrome.exe`.
- Existing ordinary Chrome main PID **24400** remained running. A filtered process-command inventory found **no `--remote-debugging-port`, `--remote-debugging-pipe` or `--user-data-dir` flags** on it. Unrelated page URLs and other user command-line details were not printed.
- Prior `/browser` parent conversation `5b356b06-0d4e-4e65-a71f-f61670bfd059` invoked a browser child `0e7cfb4c-c622-4216-b6c6-ef2a0bfc2df5`. Actual `mcp_chrome_devtools_list_pages` returned `ERROR`, seeking `C:/Users/Dell/AppData/Local/Google/Chrome/User Data/DevToolsActivePort`. It failed before connecting or navigating to YouTube.
- No AGY-initiated Chrome launch command was captured in that prior run. Therefore a claimed historical Chrome launch command, profile reuse or successful IDE attachment would be unsupported. The concrete error establishes a lookup in the ordinary default directory, rather than successful use of an isolated IDE profile.

## Chrome 136 boundary

Chrome documents that from version 136 the debugging port/pipe flags are ignored for the default data directory, and recommends a non-standard `--user-data-dir`. Installed Chrome 154 is subject to that boundary. [Chrome's official announcement](https://developer.chrome.com/blog/remote-debugging-port)

The previous missing `DevToolsActivePort` is consistent with an invalid default-directory attachment, but **does not prove that the 136 restriction alone caused it**: the observed ordinary browser also lacked debugging flags. Root did not test remote debugging against real user data to distinguish these explanations. The independent non-standard-profile test demonstrates a supported safe Chrome/CDP path on this installed version.

## Actual isolated Chrome/CDP experiment

Two bounded diagnostic subprocesses used separate, initially empty UUID profile directories in the isolated worktree's ignored `.local/pilot-repair/`. No cookies, existing browser profile files or sign-in data were copied. Security protections and certificate validation remained enabled. Only each owned Chrome process received the existing proxy; no permanent proxy was changed.

Actual argument shape (full UUID paths, times and results are in `EXECUTION.json`):

```text
"C:/Program Files/Google/Chrome/Application/chrome.exe"
  --headless=new --remote-debugging-address=127.0.0.1
  --remote-debugging-port=0 --user-data-dir=<new isolated UUID directory>
  --no-first-run --no-default-browser-check
  --proxy-server=http://127.0.0.1:12002 about:blank
```

- First PID **33880**, UTC **17:14:05.425887–17:14:50.060303** on 2026-10-10: new profile produced port **57643**; Playwright `connect_over_cdp` and `Browser.getVersion` succeeded. A diagnostic assumption that example.com contained an `h1` timed out, leaving public content verification incomplete. Owned Chrome was terminated; its recorded exit was 1. This failed diagnostic is retained.
- Instrumented content recheck PID **15716**, UTC **17:19:19.120275–17:19:26.206532**: new profile produced port **63752**, CDP connected, public `https://example.com/` returned **HTTP 200**, title **Example Domain**, and actual multilingual document body. Root opened the saved screenshot and observed the corresponding rendered document. `Browser.close` closed only this owned profile; Chrome exited **0**. Ordinary Chrome PID 24400 remained unchanged.
- The recheck helper's `public_page_pass` is **false**, because it required the title phrase inside the body; the current public page contains multilingual paragraphs instead. Its helper exit was **1**, although a subsequent shell validation command ended the combined shell with exit 0. Neither result is concealed or relabelled. Root's conclusion that CDP and public-page rendering work relies on the separate recorded port, protocol response, HTTP status, title, nonempty body and inspected screenshot, rather than this over-specific helper assertion. No third browser run was made.

## Official AGY integration investigated

Root read the installed `agy --help`, `agy mcp --help/list`, built-in CLI guide, and current official [CLI settings](https://www.antigravity.google/docs/settings?tab=cli), [CLI reference](https://www.antigravity.google/docs/cli/reference/), [subagents](https://antigravity.google/docs/subagents/) and [MCP](https://www.antigravity.google/docs/mcp/) documentation.

No documented CLI profile-selector or CDP-endpoint setting was found in those settings references or installed command flags. Current AGY settings have no browser/Chrome/CDP keys. This is **absence of an established official integration method**, not proof that no undocumented implementation exists.

The [IDE separate-profile page](https://www.antigravity.google/docs/ide/separate-chrome-profile/) provides IDE isolation guidance; it does not establish a CLI selector or CLI/IDE profile sharing. AGY officially supports generic workspace MCP configuration in `.agents/mcp_config.json`, but the reviewed documentation does not establish that this can redirect the built-in `/browser` child's Chrome attachment. Installing/injecting a new MCP server was not used as a substitute for that proof.

**Stop boundary:** independent Chrome/CDP works; current AGY connection evidence is the earlier default-directory attachment error, and an official safe way to point `/browser` to this isolated endpoint was not established. Per the user's condition, no further `/browser` call was made. The unresolved layer is **AGY browser integration / target selection**, before website login. A fresh AGY retest after CDP success remains **NOT_RUN**, not a newly reproduced error.

## Site outcomes and alternative path

- YouTube: prior `read_url_content` returned `LOGIN_REQUIRED` / “Sign in to confirm you're not a bot”; no browser sign-in or playback has been verified. **Not retested this turn.**
- B&H: prior fetch of its public portrait tutorial returned **HTTP 403**. **Not retested this turn.** This is a different HTTP-access outcome, not evidence of the same Google login issue.
- A bounded alternative remains Codex-owned Playwright capture of genuinely accessible public material, followed by AGY analysis of already verified material. This turn established only CDP/public-document access; it did not establish new video or timed audio evidence.

No real-profile debugging, security-disabling flags, cookie fabrication, login automation, challenge bypass, wider AGY permissions, provider changes or permanent configuration edits occurred. Temporary profiles and screenshots remain local/ignored for review; they are not Git deliverables. Do not recursively delete through the test `.venv` junction during later cleanup.
