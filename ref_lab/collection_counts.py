"""One canonical set of candidate counts.

Search's stop condition, the candidate queue API, ``search-summary.json`` and
``counts.json`` all call :func:`compute`. They used to derive their own numbers,
which is how "usable independent photos" could differ between the page and the
search target.

Rules (field names are kept for existing readers):

* ``found``                unique received originals
* ``target_confirmed``     originals whose discovery text names the target; never
                           including derived tiles
* ``original_singles``     originals confirmed as non-collage by the current
                           algorithm with an intact file
* ``derived_valid``        unique, intact, qualified tiles
* ``usable_independent``   unique-SHA union of qualified singles and valid tiles
* ``usable_named``         the subset of that union with a name-hit association
* ``awaiting_manual``      originals with an unresolved crop, quality or
                           relevance problem, counted once per original

Records from another algorithm version, unprocessed originals and integrity
failures never silently count as a single photograph.
"""
from __future__ import annotations

from pathlib import Path

from . import collage
from .integrity import sha_matches

EXPLORATION_TIERS = {"target_context", "unconfirmed"}


def _original_ok(folder: Path, row: dict) -> bool:
    from .collage import _inside
    path = Path(str(row.get("original_path") or ""))
    return _inside(path, folder / "images") and sha_matches(path, str(row.get("asset_sha") or ""))


def _child_ok(folder: Path, child: dict, parent_sha: str) -> bool:
    from .collage import _inside
    if str(child.get("parent_sha") or "") != parent_sha:
        return False
    sha = str(child.get("child_sha") or "")
    path = Path(str(child.get("path") or ""))
    if not sha or not _inside(path, folder / "derived"):
        return False
    return sha_matches(path, sha)


def compute(folder, rows, records, *, named=None) -> dict:
    """Return the shared counts for a run directory.

    ``rows`` are received originals; ``records`` are ``derived.json`` items keyed
    by parent SHA. File integrity results are cached by size/mtime, so this can be
    called from a one-second polling loop without re-reading every image.
    """
    from .search_relevance import is_confirmed
    folder = Path(folder)
    predicate = named or is_confirmed
    counts = {
        "found": 0, "target_confirmed": 0, "exploration": 0,
        "other_character": 0, "non_photo": 0,
        "original_singles": 0, "derived_valid": 0,
        "usable_independent": 0, "usable_named": 0, "awaiting_manual": 0,
        "collages": 0, "collage_split_ok": 0, "collage_partial": 0,
        "collage_needs_manual": 0, "collage_low_resolution": 0,
        "collage_duplicate": 0, "collage_failed": 0,
        "derived_total": 0, "derived_rejected": 0, "derived_duplicate": 0,
        "outdated_records": 0, "unprocessed": 0, "integrity_failures": 0,
    }
    records = records if isinstance(records, dict) else {}
    usable: set[str] = set()
    usable_named: set[str] = set()
    valid_tiles: set[str] = set()
    seen_originals: set[str] = set()
    for row in rows or ():
        if not isinstance(row, dict):
            continue
        sha = str(row.get("asset_sha") or "")
        if not sha or sha in seen_originals:
            continue
        seen_originals.add(sha)
        counts["found"] += 1
        tier = str((row.get("relevance") or {}).get("tier") or "unconfirmed")
        named_row = bool(predicate(row))
        if named_row:
            counts["target_confirmed"] += 1
        elif tier in EXPLORATION_TIERS:
            counts["exploration"] += 1
        elif tier in {"other_character", "non_photo"}:
            counts[tier] += 1

        unresolved = not named_row
        record = records.get(sha)
        if not _original_ok(folder, row):
            counts["integrity_failures"] += 1
            unresolved = True
            counts["awaiting_manual"] += 1
            continue
        if not isinstance(record, dict):
            counts["unprocessed"] += 1
            counts["awaiting_manual"] += 1
            continue
        if not collage.record_is_current(record):
            counts["outdated_records"] += 1
            counts["awaiting_manual"] += 1
            continue
        status = str(record.get("status") or "")
        if (record.get("integrity") or {}).get("ok") is False:
            counts["integrity_failures"] += 1
            unresolved = True
        children = [child for child in (record.get("children") or []) if isinstance(child, dict)]
        counts["derived_total"] += len(children)
        good = [child for child in children
                if child.get("status") == collage.VALID and _child_ok(folder, child, sha)]
        counts["derived_rejected"] += sum(
            1 for child in children
            if child.get("status") not in {collage.VALID, collage.DUPLICATE_RUN,
                                           collage.DUPLICATE_HISTORY}
            or (child.get("status") == collage.VALID and child not in good))
        counts["derived_duplicate"] += sum(
            1 for child in children
            if child.get("status") in {collage.DUPLICATE_RUN, collage.DUPLICATE_HISTORY})
        if status == collage.STATUS_NO_COLLAGE:
            counts["original_singles"] += 1
            usable.add(sha)
            if named_row:
                usable_named.add(sha)
        else:
            counts["collages"] += 1
            if status == collage.STATUS_SPLIT_OK:
                counts["collage_split_ok"] += 1
            elif status == collage.STATUS_SPLIT_PARTIAL:
                counts["collage_partial"] += 1
            elif status == collage.STATUS_NEEDS_MANUAL:
                counts["collage_needs_manual"] += 1
            elif status == collage.STATUS_LOW_RESOLUTION:
                counts["collage_low_resolution"] += 1
            elif status == collage.STATUS_DUPLICATE:
                counts["collage_duplicate"] += 1
            elif status == collage.STATUS_FAILED:
                counts["collage_failed"] += 1
            if good:
                for child in good:
                    child_sha = str(child.get("child_sha") or "")
                    if not child_sha or child_sha in valid_tiles:
                        continue
                    valid_tiles.add(child_sha)
                    usable.add(child_sha)
                    if named_row:
                        usable_named.add(child_sha)
            else:
                unresolved = True
        if unresolved:
            counts["awaiting_manual"] += 1
    counts["derived_valid"] = len(valid_tiles)
    counts["usable_independent"] = len(usable)
    counts["usable_named"] = len(usable_named)
    return counts
