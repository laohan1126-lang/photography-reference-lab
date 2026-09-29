# 2026-09-28 Candidate modality preflight + safe project archive

## User-observed failures before implementation

The owner reviewed the live curation UI and found examples in a character project that were still shown as identity/quality preflight passes even though they were not normal real-person cosplay photography:

- a game UI / game screenshot,
- a costume + mannequin / wig display,
- a stylized illustration.

The problem is not merely personal taste. For the default real-person cosplay reference flow, these modalities must not be promoted as ordinary exact-character photography candidates. Search query/title/project context remain discovery metadata and must never substitute for image observations.

The owner also reported that projects can be created from the left sidebar but cannot be deleted. Deletion must be safe: project removal must not physically delete assets still used by another project or Global Inspiration.

## Scope

1. Add a candidate visual-modality preflight contract that an actual image-inspecting Agent can return with each acquired candidate.
2. Persist preflight separately from human K/I/M/X and from field-card VisualReview.
3. Default project curation hides candidates filtered by preflight, while a dedicated filtered view keeps them recoverable.
4. Treat non-real-person modalities such as game/anime screenshots, illustrations, costume/mannequin/product displays, collages and scenery as filtered from the default real-person candidate flow.
5. Identity mismatch is filtered; uncertainty remains uncertainty rather than being forced to pass.
6. Schema-v3 candidate packages require per-candidate visual preflight. Older package schemas remain import-compatible and remain unverified rather than receiving invented preflight.
7. Add safe project archive/delete from the UI. Archiving hides the project but preserves all refs, events, jobs, notes, assets and cross-project/global reuse. Restoring must be possible.
8. Archived projects reject new edits, candidates, jobs and inspiration-use writes until restored.

## Explicit non-goals

- No paid standalone vision API or new mandatory model service.
- No automatic K/I/M/X.
- No claim that synthetic tests prove real visual-classification accuracy.
- No physical asset deletion as part of project deletion.
- No main-branch merge, public deployment or Golden Path creation.

## Observable acceptance criteria

- A schema-v3 import carrying `content_type=game_screenshot` or `official_illustration` cannot appear in the default project candidate list as an ordinary pass.
- A real-person candidate with `identity_prediction=mismatch` is filtered.
- `identity_prediction=uncertain` is not promoted to `passed`.
- Filtered candidates remain queryable in a dedicated view and can be explicitly restored by the human.
- Human reject/X remains distinct from preflight filtering.
- Project archive removes the project from the normal sidebar/list, survives reload, preserves shared assets/global inspirations/other projects, and can be restored.
- Existing schema-1/2 candidate packages continue importing without fabricated visual evidence.
- Tests cover the failure mechanisms above.

## Verification boundary

Unit/integration tests can verify state transitions, preservation and protocol rules. They cannot prove that an Agent visually classifies arbitrary real images correctly. Live re-scan of the owner's Wang Zhaojun / Arima Kana examples remains a separate Agent/visual validation step and must be reported as VERIFIED / UNVERIFIED / BLOCKED based on actual image inspection.


## Implementation checkpoint

Implemented on task branch `codex/modality-project-archive-20260928`:

- Candidate protocol now defines explicit visual `content_type`, relative `identity_prediction`, confidence, visual evidence and reason. Only real-person cosplay/portrait + identity match is an automatic preflight pass; non-real modalities and mismatch are filtered; unknown/uncertain remain uncertain.
- New schema-3 collection packages require per-candidate preflight. Import remains compatible with schema 1/2 and does not invent preflight for historical packages.
- Preflight is stored on Reference separately from human K/I/M/X and field-card VisualReview. Default reference queries exclude filtered items; `view_filtered=true` and the “已过滤候选” UI keep them visible and recoverable. Human restore records an override without rewriting the original preflight evidence.
- Replacing image bytes clears old preflight, so an assessment cannot silently survive a new asset.
- Project “delete” is soft archive: active project lists hide it, an archived-project UI can restore it, and data/refs/jobs/notes/events/assets are retained. Shared asset bytes, Global Inspiration and other project uses are not physically deleted. Archived projects reject normal mutation/job paths until restored.
- README, ARCHITECTURE, WORKER_PROTOCOL and CODEX regression instructions were updated to match the new protocol and recovery semantics.
- `tests/test_modality_archive.py` covers routing/recovery, mismatch/uncertain, schema3 vs legacy schema2 behavior, and project archive preservation. CI core regression was extended to run it.

### Verification boundary retained

Synthetic protocol tests prove state, compatibility and preservation rules only. They do **not** prove that a vision-capable Agent will classify the owner's Wang Zhaojun screenshots/mannequin/illustration correctly. Those exact live assets must be re-scanned by Antigravity/BrowserSkill (or another authorized image-inspecting Agent), opened individually, and reported separately as live visual validation. Historical schema1/2 candidates remain unreviewed until such a scan; no metadata-based backfill is performed.

A GitHub Actions run for code checkpoint `06fb24a6cb22256ecb1daa161c0812f71c5e6d0e` completed all core Python 3.11/3.13 and browser jobs successfully; the 3.13 core job reported 88 passed and `node --check web/app.js` / compileall succeeded. Later archive-freeze and documentation commits require the final-head CI to be checked before integration.
