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
