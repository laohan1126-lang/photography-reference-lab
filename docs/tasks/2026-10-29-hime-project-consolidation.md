# Hime project consolidation and complete character export

User: “项目里还是有两个安养寺姬芽，而且另一个项目的图片没有出现在 data 的安养寺姬芽里。” The owner clarified the directory is `data/exports/安养寺姬芽`, the kept-only legacy export.

The previous task improved future search reuse but deliberately retained both existing projects and produced a separate complete catalogue. This follow-up closes those concrete gaps rather than treating the prior engineering checks as completion of the owner's current expectation.

## Inspected baseline and narrow plan

The two projects have identical character/work/costume/brief/gear. Old source `77458f14b4d64487a5aae3302acef152` has20 distinct references:6 pending and14 rejected; new target `f0619bf62bb04d41825fee93fe3164a2` has1 kept reference and the active search. There is no source/target SHA overlap. Source references have no cards, VisualReview or accepted fingerprints; their old preflight predictions are untrusted legacy evidence. Source notes are empty. The complete catalogue already has30 character images including history, while the legacy kept-only folder has1 file.

Keep the target ID so its Job and received files remain bound correctly. With a verified backup and transaction, move the existing source reference IDs to the target, preserve human fields and all raw historical provenance, invalidate project-bound predictions, and archive the source with a merge marker. Refuse mismatched projects, conflicting files/aliases, active source jobs, stale plans or unsupported reviewed data. Keep a scoped rollback receipt; do not restore a whole stale database over later activity.

Add a managed `全部下载` export below the existing character export directory. Reuse verified independent catalogue JPGs; preserve `已确认` and user files. Register that export for future manual catalogue refreshes. No daemon, paid call, global configuration change, schema migration, image regeneration or main merge.

ROOT owns live backup/apply/acceptance and publication. Two DeepSeek workers own disjoint consolidation-tool and export-code slices; no child publishes or mutates the live library. Current task branch starts at7facf3e. Prior local deliverables remain owned by the earlier task; any carry-forward publication must match its exact accepted-file hashes and use Publisher's explicit pre-existing-path provenance mechanism. Do not alter the earlier deferred transaction.

Status: implementation and live acceptance pending.

## Continued execution and actual acceptance

The owner explicitly continued the operation. The two original DeepSeek candidates were reviewed and integrated with the preceding task's 14 accepted hashes rechecked. A scoped Publisher continuation declared those exact prior paths plus this task record; unrelated edits and historical deletions remain excluded.

An online SQLite backup and all 21 scoped original hashes were retained before writing. The merge first passed on an independent restored library, then a fresh version-2 plan was applied to the daily Windows database. The live API now returns exactly one active Hime project, target `f0619bf62bb04d41825fee93fe3164a2`. All 21 reference IDs survive: 6 pending, 14 reject and 1 keep; the default view contains 7. The source is archived with `merged_into`; no original or reference was deleted. Five jobs, 24 aliases, 25 discoveries, 31 historical preflights, one screening session, two identity contexts, 21 assets and the existing target reference are unchanged. The target project and active search are unchanged. The existing 72 foreign-key findings are identical, not newly repaired or introduced.

The first real export attempt exposed a candidate defect: tests invented `roles[].projects`, while actual catalogues contain only `group/folder/count`; the candidate falsely returned success with zero files. ROOT rejected it. A new DeepSeek repair worker, verified through response-ID-to-Magpie routing evidence, changed selection to the real role mapping, checked completeness and added a fixture built through `refresh_catalog`. ROOT separately reproduced the nine run-only legacy copies missing from `role_paths` and fixed recovery through their known project identity and matching preview hash. This preserves unknown or modified files and fixes the shared catalogue boundary.

The user's exact entry `data/exports/安养寺姬芽/全部下载/` now contains 30 independent JPG browsing copies: all current project assets plus historical downloads. No claim is made that an unverified search candidate visually depicts the named character. The existing one-file `已确认/` export is byte-identical. All 30 copies decode and match the source hashes; all 60 HTML image/link targets resolve. A subsequent ordinary refresh, without `--export-character`, exited 0 and retained all 30 through the remembered registration. The full catalogue remains 2,056 available assets / 19 role groups / zero errors; all 20 non-internal SQLite tables were byte-semantically unchanged by this refresh.

Actual checks:

- `.venv/Scripts/python.exe -X utf8 -m pytest tests/test_project_consolidation.py tests/test_catalog_exports.py tests/test_local_catalog.py -q --basetemp=.local/hime-consolidation-20261029/integrated-pytest`: 29 passed, 1 skipped before the real-export correction. Merge tests are unchanged and their 11 passing cases remain valid.
- New run-only legacy regression reproduced `KeyError` before the fix; final `tests/test_local_catalog.py` suite: 14 passed.
- Final `tests/test_catalog_exports.py` suite: 6 passed, 1 skipped. The skipped symbolic-link test is UNVERIFIED because Windows denied link creation with `WinError 1314`, including the host-level attempt. No check was weakened.
- `verify_consolidation.py` on the restored copy and `--live` against the daily API both passed; originals, IDs, human fields, jobs and FK baseline matched.
- `tools/sync_local_catalog.py --repo-root .` and `verify_export.py` both passed on the real library. No browser relaunch, service restart, collection trial or unrelated full-suite run was needed. Previous UI/layout evidence is reused because those files and dependencies are unchanged.

Private evidence is under `.local/hime-consolidation-20261029/`; the merge receipt and consistent database backup are under `.local/backups/20261029-hime-project-consolidation/live-receipts/merge-20261029T113802Z-f7bcba2a/`. Rollback is scoped and refuses newer edits; never restore the whole stale database over later activity. Originals, rejected selections and historical provenance remain intact.

Engineering and live acceptance: VERIFIED. Both execution worktrees were removed only after ZIP readback/hash verification of all unique changed, untracked and ignored files (10 and 2,437 files); their archives and manifests remain under the scoped backup directory. Originals and daily data were outside this cleanup.

Formal delivery uses continuation transaction `01a18756-8db6-71c3-b1b8-ef2a51c0af87` on `codex/hime-project-consolidation-20261029`, with exactly 19 owned source/test/document/launcher paths. Its canonical seal/finish output is retained as `.local/hime-consolidation-20261029/publication-seal.json` and `publication-receipt.json`; those receipts and the actual remote SHA determine publication success independently of the live acceptance above. Notion is disabled. The preceding task's original deferred transaction remains untouched; no main merge or force push is authorized.
