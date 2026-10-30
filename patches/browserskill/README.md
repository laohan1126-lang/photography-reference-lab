# BrowserSkill 0.4.0 local domain-setup deadline patch

Upstream: Tencent/BrowserSkill, `ext-v0.4.0`, commit `7e300ff6a35b326ac9abd03f315f30769ad01861`.

`0.4.0-bounded-domain-setup.patch` bounds diagnostic-domain setup (`Page.enable`, lifecycle events, Runtime, Log and Network) using the existing CDP read gate and ten-second deadline. Previously these calls could wait forever before navigation's own wait began, leaving a cancelled command in the extension's active-operation slot. The regression holds `Page.enable` unresolved: stock code never completes; patched code reports the named timeout, rolls back its debugger attachment and does not issue further initialization reads.

This patch does not disable cooperation, target ownership, cancellation, content freshness, URL restrictions or user control. It does not replay navigation or input. It is not evidence that every observed local stall has the same cause.

## Build and validation

Use the upstream tag in a repository-local private checkout. Apply the patch with `git apply`, install upstream lockfile dependencies with pnpm 10.17.0, then use the extension's existing Vitest, TypeScript and WXT commands. No added dependency or altered permissions.

Executed: regression fails on stock source; patched `chromium-cdp.test.ts`, `command-deadline.test.ts`, and `navigation-recovery.test.ts`: 154 passed. `tsc --noEmit` and WXT production build passed.

Prepared artifacts (ignored, local only):

- `.local/browser-skill-repair-20261030/BrowserSkill-0.4.0-local-20261030.zip`
- `.local/browser-skill-repair-20261030/extension/`
- Archive SHA256: `428dbbae727c831b2c8aa47fbb005173cea29db50a53d7923537c6b26924d527`.

## Activation and rollback

The original installed extension is unchanged. A human can open `edge://extensions`, temporarily disable the original BrowserSkill (do not remove it), enable developer mode if necessary and load the prepared `extension` directory unpacked. The local variant is labelled `BrowserSkill - local setup-timeout patch`. Use `bsk browsers --json` to bind the newly returned instance; the old ID must not be reused. Keep CLI/daemon at 0.4.0. The collector rejects ambiguous Edge instances instead of guessing.

Rollback: disable the local variant and re-enable the original. No browser profile, login state, reference image, selection or task budget needs replacement.

Installed-browser acceptance is UNVERIFIED. Windows Computer Use stopped because it could not reliably establish the current browser URL; no alternate UI backend or direct profile edit was used to bypass that stop. Before real acquisition, verify a fresh owned session can navigate to the local health page, synchronize, read its actual text, navigate again with a new context, and stop without affecting another session. If this fails, preserve the full named setup/renderer error rather than retrying a full collection.

## Second candidate: raw debugger attachment

The owner installed the first candidate and confirmed the popup became faster after relieving severe system memory pressure. The copied DeepSeek Harness instructions are a generic upstream alternative; the reference library still uses the Antigravity agent and BSK CLI. Installed foreground and background health navigation both continued to time out around 34 seconds. Permission metadata contained the requested debugger and host grants. This does not prove a unique internal cause.

`0.4.0-bounded-setup-v2.patch` is a **combined** patch against the same upstream tag; apply it instead of the first patch. It also bounds a raw `chrome.debugger.attach` that never acknowledges. A timed-out attachment generation is retired, later callers cannot issue a duplicate attach, and late completion rolls back without publishing the stale attachment or dispatching page commands. Existing domain/frame deadlines retain their own diagnostics and budgets.

The new regression failed on candidate 1. Candidate 2 passed 161 tests across CDP, deadline, tab-detachment and navigation-recovery suites, TypeScript checking and the production build. During development one aggregate initialization deadline incorrectly replaced a frame-configuration error; the implementation was narrowed to raw attachment and the original assertion was preserved.

Prepared candidate 2: `.local/browser-skill-repair-20261030/BrowserSkill-0.4.0-local-20261030-v2.zip`, SHA256 `63ccb13ad5514b45cbb0c963ff197975678c0a567006e176a3ad68681548db5d`. The existing unpacked directory is updated in place; `version_name` is `0.4.0-local.20261030.2`. Reloading it preserves the profile/instance mapping. Restore candidate 1 from its retained ZIP or re-enable the untouched original extension to roll back. Actual installed acceptance remains pending until navigation and a page read succeed.

## Diagnostic candidate (installed acceptance still blocked)

Candidate2's real health navigation failed after34.115s. `0.4.0-control-diagnostics-v3.patch` is combined against the upstream tag and supersedes, rather than stacks on, the earlier patches. It adds only pending native method names/elapsed times and dispatch phase to the existing settling-error response, restricted to the requesting session. It records no command arguments, result bodies or credentials and does not loosen a guard or replay an action. Two red regressions preceded implementation; five related suites passed222 tests, followed by typecheck/build.

Candidate3 still timed out and did not expose the expected diagnostic field despite matching files on disk. To establish actual loaded-code identity, candidate3b adds `localdiag3` to the existing debug-capabilities build field and uses `background-localdiag3.js` as the local manifest's worker filename. This is a diagnostic build, not a proven recovery. After loading, first require `bsk debug capabilities --session <owned-id> --json` to return the marker; only then test navigation and inspect failures.

Current local artifact: `.local/browser-skill-repair-20261030/BrowserSkill-0.4.0-local-20261030-v3b.zip`; SHA256 `a95a315bade1374c511812ab15117c2a11f24290bbdd76663580ee6e63eaaaa4`. Stage is `extension-v3b`, and the existing installed directory remains `extension`. Build normally, copy `background.js` to `background-localdiag3.js`, and point the local manifest at that file; permissions and protocol remain unchanged. Candidate2 ZIP and original disabled extension are retained. Owner reload and the actual runtime marker must precede any recovery claim.
