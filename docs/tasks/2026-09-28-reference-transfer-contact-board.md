# 2026-09-28 Reference transfer/reuse + model contact board

## User intent recorded before implementation

The owner has many useful images originally collected under the wrong character project. Directly archiving them wastes useful pose/aesthetic material. The library already treats image bytes as independent Assets, so the product should manipulate project-use relationships rather than copy/delete image files.

The owner also wants to pick a small subset from a project (typically from 20–30 references) and export a clear visual board to show a model what kinds of poses / mood / framing they prefer. The first version should prioritize a simple, legible four-image-per-page board rather than a dense 9-grid.

## Product decisions

### Cross-project reuse / transfer

Provide human-controlled actions for current project References:

- copy to another project: current project relation stays;
- move to another project: create/reuse the target project relation, then detach the current project relation;
- add to Global Inspiration remains a separate existing capability;
- remove from current project: detach only this project relation.

Asset bytes, source provenance and global/other-project use must not be deleted. Target project relation defaults to `pending`; no K/I/M/X choice is inherited automatically. Existing target-project choice must be preserved rather than overwritten.

A move/removal should remain auditable and recoverable. Do not overload X/reject semantics: being in the wrong project is not an aesthetic rejection.

### Selection + contact board export

Add a lightweight project-local selection basket usable while browsing references. The same selected IDs can support batch copy/move and board export.

Contact board behavior:

- current project only;
- user explicitly selects images;
- preserve selection order and allow short optional per-image notes;
- maximum 4 images per rendered page;
- 1–4 selected images download one PNG;
- more than 4 produce a ZIP of sequential PNG pages;
- images use contain-style fitting with no destructive crop;
- include simple project title / page number / optional short note;
- no AI-generated content and no automatic image selection.

This is a communication artifact, not a field card and not a new K/I/M/X state.

## Data-safety invariants

- One Asset stays one content-addressed file even when reused across projects.
- Copy/move must not inherit target character identity, preflight, review, card or acceptance.
- Existing target-project relation and choice are never silently overwritten.
- Global Inspiration is independent.
- Detach/remove preserves the source Reference record/history and can be restored.
- Project archive semantics remain independent from per-reference detach.
- Contact-board generation is read-only except for an append-only export event; it must not mutate human choices.
- No private images, databases, exports or runtime files are committed to Git.

## Acceptance criteria

1. Copy one Reference to another project: same asset SHA, new target Reference pending, source still active.
2. Move one Reference: target pending/reused safely; source disappears from normal project flows without becoming X; source can be restored.
3. Batch copy/move is atomic enough to report each outcome and never overwrite existing target choices.
4. Shared Asset, Global Inspiration and unrelated projects survive move/remove.
5. UI offers project transfer/copy and a selected-items basket without replacing K/I/M/X.
6. User can select 1–4 images and download one PNG contact board.
7. More than 4 selected images generate multiple 4-up PNG pages in a ZIP.
8. Portrait/landscape source images are fitted without destructive crop.
9. Board notes/order come only from the user's explicit request.
10. Regression verifies project reuse/detach/restore, existing-target preservation and exported page count/content geometry.

## Verification boundary

Synthetic images can verify data semantics and deterministic board layout, but they do not prove the user's real-model communication preference. Final local Antigravity handoff should open the real UI, move/copy real references between test projects, export a board and visually inspect the generated PNG before asking the owner to accept it.
