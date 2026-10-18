# Learning Loop V1: local experiment entry points

This is an opt-in, read-only experiment. It does not replace the production ranking, update the aesthetic profile, save curation decisions, or generate images. Private data, features, feedback, predictions, model state, and detailed evaluation reports remain under ignored `.local/learning-v1/`.

## Use the saved result

Open `.local/learning-v1/index.html` locally. The entry page links to a blind comparison, the unranked candidate order, specified-costume results, the dataset audit, and a technical retrospective. The pages contain local original received image bytes and source links. Reading them performs no write to the library. Keep the folder structure intact because image links are relative.

The blind page compares two frozen methods on the same candidate pool. The method mapping is in a separate local JSON file. Do not inspect that mapping before recording a preference. A changed order does not establish improved taste; owner acceptance is separate from engineering verification.

## Single-image human review (2026-10-18)

The older A/B page is retained only as historical evidence. The current human-truth entry is a single-image review: each original SHA is shown once, and the owner records three independent dimensions (character accuracy, photography usefulness, personal aesthetic) plus an optional short reason. Skipping a photo is a missing label, not a dislike. The review page shows no model score, strategy name or ranking suggestion.

Start a loopback-only server from the repository:

```powershell
python -B -X utf8 -m tools.learning_v1_human serve --open
```

The page is served at `http://127.0.0.1:<random-port>/` (only that interface is opened). It reads the frozen `ruby-pool.json`, `ruby-predictions.json` and `ruby-evaluation.json` without changing them, serves original image bytes, and stores drafts keyed by SHA. Drafts survive refresh/close because they are written atomically to `.local/learning-v1/ruby-human-labels.json`. Submitting writes a write-once read-only snapshot `.local/learning-v1/ruby-human-labels-final.json` and generates the report.

The review page can also be opened directly as a file for browsing, but saving and submission require the local server. Opening or leaving the page does not create an empty label entry; only an actual selection, reason or explicit skip is persisted.

Generate the report only after submission (the server does this on submit):

```powershell
python -B -X utf8 -m tools.learning_v1_human report
```

Before submission, `report` refuses to produce metrics. For the empty-label acceptance check only, an explicitly marked N/A page can be generated with `--allow-unsubmitted`; it contains no accuracy claim. The server is never exposed beyond `127.0.0.1`, and no image or label is uploaded.

The report table follows the frozen `baseline0`, `baseline1` and `candidate2` orders. It reports Top-5 likes, graded NDCG@5, photography-useful counts, character confirmation/wrong/uncertain counts, coverage and missing labels. Missing aesthetic labels are never treated as 0: NDCG@5 is `N/A` until the relevant Top-5 is fully labelled. Identical frozen orders are reported as `NO_RANKING_DIFFERENCE`; if the two methods have the same Top-5, the report says the result did not improve the owner's Top-5. The conclusion remains `NOT_PROVEN` because this is one fixed pool evaluated once, not an independent held-out taste benchmark.

Protected-input verification:

```powershell
python -B -X utf8 tools/learning_v1.py check-freeze
python -B -X utf8 -m tools.learning_v1_human verify --baseline .local/learning-v1/human-review-before.json
```

`tools/learning_v1_report.py` is itself in `freeze.json`, so this round adds the human-review module rather than editing that frozen renderer; the existing style and helpers are imported unchanged. `learning_v1_human.py` never re-ranks, trains or writes production K/I/M/X.

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
python -B -X utf8 -m pytest -q tests/test_learning_v1.py tests/test_learning_v1_human.py tests/test_learning_query_plan.py tests/test_search_quality_loop.py -k "not detail_dom" -p no:cacheprovider
```

The remaining two existing `detail_dom` cases can be run with the installed Playwright runtime, or verified with the exact same extraction function against local DOM fixtures in the connected browser. Fixture success is not evidence of real-image accuracy. Detailed commands, actual results, failed attempts, original-byte checks, and browser screenshots belong in the private experiment report rather than in a public repository artifact.
