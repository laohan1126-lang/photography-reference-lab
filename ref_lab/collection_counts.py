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
* ``usable_named``         the subset of that union with a name-hit association,
                           discovered through any parent record and intersected
                           with the unique photos afterwards
* ``awaiting_manual``      originals with an unresolved crop, quality or
                           relevance problem, counted once per original; a
                           blurred tile next to a qualified sibling still needs
                           a human, pure duplicate exclusion does not

Records from another algorithm version, unprocessed originals and integrity
failures never silently count as a single photograph.
"""
from __future__ import annotations

from pathlib import Path
from functools import lru_cache

from . import collage
from .integrity import sha_matches

EXPLORATION_TIERS = {"target_context", "unconfirmed"}


@lru_cache(maxsize=1024)
def _quality(path, size, mtime):
    from PIL import Image, ImageOps
    with Image.open(path) as image:
        return collage._tile_quality(ImageOps.exif_transpose(image))["status"] == collage.VALID


def quality_ok(path):
    try:
        path = Path(path)
        stat = path.stat()
        return _quality(str(path), stat.st_size, stat.st_mtime_ns)
    except (OSError, ValueError):
        return False


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
    from .search_relevance import is_confirmed, source_warnings
    folder = Path(folder)
    from .collection_checkpoint import read_json
    from .photo_types import verified_photo, receipt_intact
    classifications = read_json(folder / 'photo-types.json', {}).get('items', {})
    goal = read_json(folder / 'goal.json', {})
    baseline = set(goal.get('baseline_shas', []))
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
        "independent_candidates": 0, "named_candidates": 0, "type_pending": 0,
        "type_rejected": 0, "goal_excluded": 0,
        "source_pending": 0,
    }
    records = records if isinstance(records, dict) else {}
    # Photo uniqueness and name-hit discovery are aggregated separately, then
    # intersected. A tile can appear in two parent records: whichever record is
    # seen first owns the unique photo, while a name-hit association discovered
    # through either parent still applies to that photo. Parent order therefore
    # cannot change ``usable_named``.
    usable: set[str] = set()
    provenance: set[str] = set()
    old_parents: set[str] = set()
    named_associations: set[str] = set()
    valid_tiles: set[str] = set()
    source_pending: set[str] = set()
    seen_originals: set[str] = set()
    for row in rows or ():
        if not isinstance(row, dict):
            continue
        sha = str(row.get("asset_sha") or "")
        if not sha or sha in seen_originals:
            continue
        seen_originals.add(sha)
        counts["found"] += 1
        if goal and (not isinstance(row.get('acquired_at'), (float, int))
                     or row['acquired_at'] < float(goal['started_at'])):
            old_parents.add(sha)
        from urllib.parse import urlsplit
        source_ok = all(urlsplit(str(row.get(key) or '')).scheme == 'https'
                        and bool(urlsplit(str(row.get(key) or '')).hostname)
                        for key in ('page_url', 'image_url'))
        if source_ok:
            provenance.add(sha)
        tier = str((row.get("relevance") or {}).get("tier") or "unconfirmed")
        named_row = bool(predicate(row))
        if named_row:
            counts["target_confirmed"] += 1
            named_associations.add(sha)
        elif tier in EXPLORATION_TIERS:
            counts["exploration"] += 1
        elif tier in {"other_character", "non_photo"}:
            counts[tier] += 1

        warning = bool(source_warnings(row))
        if warning:
            source_pending.add(sha)
        unresolved = not named_row or warning
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
        if warning:
            source_pending.update(child.get('child_sha') for child in children)
        counts["derived_total"] += len(children)
        good = [child for child in children
                if child.get("status") == collage.VALID and _child_ok(folder, child, sha)]
        rejected = [child for child in children
                    if child.get("status") not in {collage.VALID, collage.DUPLICATE_RUN,
                                                   collage.DUPLICATE_HISTORY}
                    or (child.get("status") == collage.VALID and child not in good)]
        counts["derived_rejected"] += len(rejected)
        counts["derived_duplicate"] += sum(
            1 for child in children
            if child.get("status") in {collage.DUPLICATE_RUN, collage.DUPLICATE_HISTORY})
        if status == collage.STATUS_NO_COLLAGE:
            counts["original_singles"] += 1
            if quality_ok(row['original_path']):
                usable.add(sha)
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
            if named_row:
                # Name hit is discovery information: it may come from a record
                # whose tile was already counted through another parent, but it
                # never adds a photo that is not in ``usable``.
                for child in children:
                    child_sha = str(child.get("child_sha") or "")
                    if child_sha and child.get("status") in {collage.VALID, collage.DUPLICATE_RUN}:
                        named_associations.add(child_sha)
            if good:
                for child in good:
                    child_sha = str(child.get("child_sha") or "")
                    if not child_sha or child_sha in valid_tiles:
                        continue
                    valid_tiles.add(child_sha)
                    if quality_ok(child['path']):
                        usable.add(child_sha)
                        if source_ok:
                            provenance.add(child_sha)
            only_duplicates = bool(children) and all(
                child.get("status") in {collage.DUPLICATE_RUN, collage.DUPLICATE_HISTORY}
                for child in children)
            if rejected or (not good and not only_duplicates):
                # One qualified tile does not resolve a blurred sibling: the
                # original still needs a human, counted once per original.
                # Pure duplicate exclusion is not a crop or quality problem.
                unresolved = True
        if unresolved:
            counts["awaiting_manual"] += 1
    counts["derived_valid"] = len(valid_tiles)
    counts['independent_candidates'] = len(usable)
    counts['named_candidates'] = len(usable & named_associations)
    excluded = usable & (baseline | old_parents)
    # A new crop of an old parent is still historical material.
    for row in rows or ():
        if row.get('asset_sha') in baseline | old_parents:
            excluded.update(c.get('child_sha') for c in records.get(row['asset_sha'], {}).get('children', []))
    counts['goal_excluded'] = len(usable & excluded)
    usable -= excluded
    counts['source_pending'] = len(usable & source_pending)
    usable -= source_pending
    counts['type_pending'] = sum(not classifications.get(sha) or
        classifications[sha].get('status') != 'succeeded' or
        classifications[sha].get('result', {}).get('kind') == 'unknown' for sha in usable)
    photographic = {sha for sha in usable & provenance
                    if verified_photo(classifications.get(sha), sha)
                    and receipt_intact(folder, classifications[sha])}
    counts['type_rejected'] = len(usable - photographic) - counts['type_pending']
    if goal:
        from .collection_history import FINGERPRINT_ALGORITHM_VERSION, goal_baseline
        try:
            goal_baseline(folder, goal)
            checked = {sha for sha in photographic
                       if classifications[sha].get('history_check') == {
                           'state':'clear', 'baseline_sha':goal['baseline_sha'],
                           'algorithm_version':FINGERPRINT_ALGORITHM_VERSION}
                       and classifications[sha].get('result', {}).get('kind') == 'cosplay_photo'}
        except (OSError, ValueError, KeyError, TypeError):
            checked = set()
        counts['history_pending'] = len(photographic - checked)
        photographic = checked
    audit = read_json(folder / 'photo-audit.json', {}).get('items', {})
    duplicates = {sha: item['duplicate_of'] for sha, item in audit.items()
                  if isinstance(item, dict) and item.get('asset_sha') == sha
                  and item.get('status') == 'duplicate' and item.get('producer')
                  and item.get('evidence') and sha in photographic
                  and item.get('duplicate_of') in photographic and item['duplicate_of'] != sha}
    for sha, original in duplicates.items():
        if sha in named_associations:
            named_associations.add(original)
    counts['photo_duplicates'] = len(duplicates)
    usable = photographic - duplicates.keys()
    counts["usable_independent"] = len(usable)
    counts["usable_named"] = len(usable & named_associations)
    counts['goal_shas'] = sorted(usable & named_associations)
    # Plain Search has no type worker; only an explicit Goal promises verified photos.
    counts['target_metric'] = 'usable_named' if goal else 'named_candidates'
    counts['target_progress'] = counts[counts['target_metric']]
    return counts
