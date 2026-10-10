# AGY evidence — PARTIAL

This records actual Headless work, not a claim that a new video was watched.
Execution UTC times, PIDs, tool events, log hashes and exits are in
[EXECUTION.json](EXECUTION.json). No new video supplies two verified moments.

## Runtime and permission boundary

- Installed AGY: **1.3.3**, official Windows Headless CLI. The former 1.3.2
  assumption was not reused as current state.
- Existing `read_url` allow rules: `read_url(youtube.com)`,
  `read_url(antigravity.google)`, `read_url(bhphotovideo.com)`.
  No related Ask/Deny rules were present. Settings bytes/hash were unchanged.
- No global permission, proxy, credential or IDE edits. No skip-permissions flag.
- First run stalled during direct network initialization. The recovery used the
  already configured local proxy only in that child's HTTP_PROXY/HTTPS_PROXY.
- Both processes were stopped by the controller, exit **4294967295**, empty stderr,
  without a terminal JSON result. `denied_actions` is **NOT_REPORTED**, not zero.
  Actual reading outcomes must therefore be judged from individual tool events.
- A PreInvocation publisher hook emitted a Python quoting error. It was **nonfatal**:
  search, reading and file-writing events subsequently completed. The controller
  incorrectly interpreted those warnings as a complete block and stopped the
  recovery early. This orchestration error is retained as a limitation.

## Actual research and source outcomes

The recovery completed 11 search calls, 5 file reads, one successful URL fetch,
one failed URL fetch and two research-file writes in the AGY worktree.
Search metadata is discovery evidence only.

| Candidate | Actual tool result | What is usable |
|---|---|---|
| [YouTube candidate](https://www.youtube.com/watch?v=LPIIiVSyuIQ), search identified as B&H / Dave Krugman, *How to Pose Models: 5 Portrait Photography Tips* | `read_url_content`, step 16, DONE | Returned HTML contained `LOGIN_REQUIRED` and a sign-in/bot challenge; no observed audio, continuous frames or timed transcript |
| [B&H candidate page](https://www.bhphotovideo.com/explora/videos/photography/portrait-photography-posing-angles-5-tips), search identified as Kreshonna Keane | `read_url_content`, step 38, ERROR, HTTP **403** | Access failure itself; no page-body/video teaching claims accepted |

Root independently read the returned YouTube artifact and checked challenge
markers: 1,381,693 bytes, SHA256
`90e1106388d1751f43c0d64ae5690b4846651ad5a02c1b4dd4040490f15e94ea`.
Raw challenge HTML stays local; it is not republished with visitor tokens.
The provider/CDN responsible for the 403 was not independently established.

**New-video A/B/C/D teaching content accepted from AGY: zero.** Neither source
supports two verified operating timestamps. No full-viewing assertion is made.

YouTube webpage retrieval, video playback, subtitles and download are separate:
playback/download were **NOT_ATTEMPTED**, not proven denied or authorized.
No cookies, hidden APIs, challenges or download controls were bypassed.
The official [Headless interface](https://antigravity.google/docs/cli/headless/)
and [CLI permissions](https://www.antigravity.google/docs/permissions?tab=cli)
do not turn a successful URL fetch into evidence of watching a video.

## Rejected draft claims and controller corrections

AGY wrote `AGY_RESEARCH.md` and `RAW_TOOL_EVIDENCE.txt` in its separate research
worktree; their byte hashes are preserved in EXECUTION.json. They are drafts,
not accepted course evidence. Root rejected these observable defects:

- The draft swapped the two existing Bilibili authors: `BV1od4y1n7Ag` belongs
  to 一灯和一镜; `BV1MD421L7VK` belongs to 小言Jun in the registered baseline.
- Search outlines and uninspected material cannot substantiate exact poses,
  angles, instructions, photographer quotations or continuous actions.
- The draft's `DENIED` label for downloads/system commands was changed to
  NOT_ATTEMPTED. No corresponding attempted/denied tool event exists.
- A bot challenge, HTTP 403 and nonfatal local hook warning are separate from
  `read_url` permission soft-denial. No permission expansion was attempted.

## Honest integrated demonstration

To exercise the implemented display with real material, root reopened **eight
already registered public-video stills** from the existing local media caches,
verified their SHA256 identities and preserved their original bytes. These are
not newly researched AGY video evidence and do not establish full-video/audio
review. Original screenshots are excluded from Git.

| Existing case | Registered positions rechecked visually this turn | Accepted scope |
|---|---|---|
| course-fixed-focal | 01:07 | Visible comparison labels and framing in one registered still |
| course-distance | 02:20 | Visible near/far framing in one registered still |
| course-height | 01:48, 01:56 | Two visible framing examples; not a continuous movement claim |
| jun-hand-direction | 02:12, 02:28 | Hand/prop arrangement and visible subtitle text in two stills |
| jun-low-final | 04:35, 05:00 | Arrangement and final image in two stills |

A entries state only visible still content; frame provenance/timestamps are
inherited registrations, not independently replayed video positions. All five B
entries explicitly state that photographer speech/audio has **not** been verified.
C entries use root's actual reading of the primary
[MIT camera-model chapter](https://visionbook.mit.edu/imaging_geometry.html),
sections 39.2/39.4, for the limited ideal-projection explanation. This cannot
identify a video's focal length, body dimensions, load or author intent.
D entries remain project suggestions to test, never photographer quotations.

Independent human clarity/aesthetic acceptance, whole-video playback, audio and
new-video moments remain **UNVERIFIED**. The research part does not meet FULL.
