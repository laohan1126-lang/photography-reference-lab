# Learning Loop V1: local experiment entry points

This is an opt-in, read-only experiment. It does not replace the production ranking, update the aesthetic profile, save curation decisions, or generate images. Private data, features, feedback, predictions, model state, and detailed evaluation reports remain under ignored `.local/learning-v1/`.

## Use the saved result

Open `.local/learning-v1/index.html` locally. The entry page links to a blind comparison, the unranked candidate order, specified-costume results, the dataset audit, and a technical retrospective. The pages contain local original received image bytes and source links. Reading them performs no write to the library. Keep the folder structure intact because image links are relative.

The blind page compares two frozen methods on the same candidate pool. The method mapping is in a separate local JSON file. Do not inspect that mapping before recording a preference. A changed order does not establish improved taste; owner acceptance is separate from engineering verification.

## Reproduce without new network work

Use the existing Python environment that has Pillow installed:

```powershell
python -B -X utf8 tools/learning_v1.py check-freeze
python -B -X utf8 tools/learning_v1.py holdout
python -B -X utf8 tools/learning_v1.py report
```

These commands verify the frozen inputs, replay the received and individually reviewed holdout, and regenerate local pages. They do not run new searches or fit parameters. `audit` captures a new snapshot only when none exists; `--reuse-snapshot` explicitly reuses the original one. `evaluate` refuses to fit or recompute validation after `freeze.json` exists. Do not rerun either training-stage command against a completed frozen experiment.

The six features describe visible viewpoint, framing, pose, lighting appearance, background, and gesture. They are Agent observations bound to exact image bytes, not human labels. The provided fallback uses equal-weight similarity to explicitly liked examples and reports that it has no fitted parameters. Missing coverage and unknown identity remain visible. A perceptual hash is used only to group near images; it is recomputed from both pools with the same EXIF-oriented encoding, never used as a taste feature.

## New bounded acquisition

`tools/learning_v1_search.py` accepts a local task file plus `--browser` and `--bsk`. Obtain a currently connected browser ID rather than copying a historical one. The task has a `project_snapshot` and a `query_plan` whose scope must match character, costume, and work exactly. Up to eight explicit translated queries are allowed. Discovery phrases need not contain the Chinese spelling of the outfit; that permission does not establish a visual character or costume match.

The live runner uses the existing visible Pinterest detail-page adapter and saves received bytes locally. It claims a one-time `started.json` before network work and refuses silent retries that would conceal a consumed search budget. Frozen holdout tasks verify file hashes before searching. Post-holdout tuning invalidates the experiment; it is not a retry.

## Disable and rollback

There is no production enable switch to undo: the experiment was never connected to default ranking or human curation. Stop calling its CLI to disable it. Ordinary collection jobs without `query_plan` retain their existing query behavior. Remove the optional `query_plan` from an experiment job to use that legacy path; do not delete old data or rewrite a frozen result. Code rollback, when needed, should revert only the scoped task commit, preserving all ignored evidence and unrelated changes.

## Verification boundary

```powershell
python -B -X utf8 -m pytest -q tests/test_learning_v1.py tests/test_learning_query_plan.py tests/test_search_quality_loop.py -k "not detail_dom" -p no:cacheprovider
```

The remaining two existing `detail_dom` cases can be run with the installed Playwright runtime, or verified with the exact same extraction function against local DOM fixtures in the connected browser. Fixture success is not evidence of real-image accuracy. Detailed commands, actual results, failed attempts, original-byte checks, and browser screenshots belong in the private experiment report rather than in a public repository artifact.
