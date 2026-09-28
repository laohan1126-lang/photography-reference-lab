# Nightly Project Consolidation — 2026-09-29

## Intent recorded before changes

The owner requested a reliable next-day checkpoint, not more features or open-ended polishing. Review real code, history and execution evidence; use VERIFIED / FAILED / UNVERIFIED precisely; fix only small, demonstrable defects or coverage/documentation gaps. Preserve the current narrow product goal: request-driven reference search with effective filtering. Do not add random game-image modes, new ML infrastructure, paid APIs, or broader product features.

Source branch: `codex/reference-library-rebuild`.
Audit baseline: `2b1e843be901aa193d8d0828a8366e4b88f477ae`.
Isolated review branch: `codex/nightly-consolidation-2026-09-29`.
The nightly label follows the current task date. GitHub commit/run timestamps are UTC; the latest baseline commit is 2026-09-28T17:51:41Z. Do not reinterpret historical documents as results on this snapshot.

## Boundaries

- No main merge, force push, deployment, changes to the owner's database, deletion of images, or Notion write.
- Local git clone failed with `Could not resolve host: github.com`. The connected local-workspace read attempt also failed. The owner's uncommitted/staged/untracked work, Windows processes, runtime data directory, and live BrowserSkill session are UNVERIFIED.
- Authorized GitHub reads/writes are available. Existing CI records are real execution evidence, but not a fresh local run or live external search acceptance.
- Baseline GitHub Actions run `36461151099` on head `2b1e843...` completed successfully: core Python 3.11, core Python 3.13, browser Python 3.12. Source workflow: `.github/workflows/regression.yml` at the baseline.
- Browser evidence is explicitly synthetic; full-resolution real image content and current Windows behavior remain UNVERIFIED. Individual pytest counts/skips cannot be inferred from a green job.

## Findings to validate

1. `.github/workflows/regression.yml` omits existing `tests/test_collection_ui.py`, although README/AGENTS require the collector UI regressions. Those tests cover HTTP-200 blocked, failed/cancelled/running, and a late response arriving after another dialog opens.
2. `ref_lab/preflight.py::detect_modality` retains metadata-only positive exceptions for COS_/LIVE_/SEL_ prefixes and couture URL substrings. This contradicts the strict-search task's evidence boundary; reproduce before making runtime claims.
3. `get_preflight` orders random UUID-derived IDs as though chronological and falls back to any project when a requested project has no record. Validate with an isolated SQLite counterexample before deciding the smallest safe fix.
4. Latest inspiration change removed I from an existing stable-filmstrip keyboard loop. A new API regression covers archive/detach/restore, but the removed browser interaction is not thereby verified.
5. Earlier candidate-pipeline documentation reports 457 scanned / 403 passed / 54 filtered / 0 uncertain. These are historical Agent claims, not current audited accuracy. README still describes some pipeline work as absent although the implementation and later task report include it. Preserve history and write a current handoff rather than rewriting old claims as facts.

## Permitted limited changes and acceptance

- Add the existing collector UI suite to the browser CI command, with no product behavior or dependency changes.
- Reproduce any additional definite defect on isolated synthetic data only. No aesthetic/identity accuracy claim from these probes.
- A changed runtime path needs a regression and actual rerun. If full validation is unavailable or unsafe, preserve a clear open issue instead of claiming completion.
- Re-read the remote checkpoint, compare exact changed paths, and record final CI state and outstanding live checks in the NIGHTLY HANDOFF below.

## NIGHTLY HANDOFF

In progress. Outcomes will be appended after verification; this initial intent is not a completion claim.
