"""Deterministic, local-only collage detection and splitting.

This stage runs after an original has been received and persisted. It makes **no
model calls**, never upscales, never repaints and never rewrites the original
bytes: a collage is only cut along boundaries the pixel data actually supports,
and each derived tile is a lossless PNG crop of the decoded original.

Two distinctions matter for the product:

* a *detected* collage is not automatically a *usable* one. A 1080x1440 nine-grid
  yields 360x480 tiles, which are not independent photography references even
  though they can be cut. Such tiles are recorded as ``low_resolution`` and do
  not count towards "usable independent photos".
* an original and all of its children are alternatives, never additional photos.
  Counting lives in :func:`count_summary` so Search, the candidate queue and the
  web view agree.

Everything is keyed by the original's content hash, so re-running the stage over
the same run directory is idempotent: the same record and the same child files
are reused instead of being generated again.
"""
from __future__ import annotations

import hashlib
import json
import math
import queue
import threading
import time
from pathlib import Path

import numpy as np
from PIL import Image, ImageOps

from .storage import atomic_write

# --- conservative thresholds -------------------------------------------------
# Bump whenever detection, cropping or quality rules change. Records written by
# another version are never reused as an effective result: they may be
# snapshotted and recomputed by an explicit processing operation, but a read-only
# view reports them as pending update instead of silently counting them.
ALGORITHM_VERSION = 2

# A tile smaller than this is not delivered as an independent photography
# reference (the 1080x1440 nine-grid case: 360x480).
MIN_CHILD_SHORT_SIDE = 480
MIN_CHILD_AREA = 300_000
MIN_CHILD_ASPECT = 0.40
MAX_CHILD_ASPECT = 2.60
# Laplacian variance of a 640px copy. Real photographs are usually >100; this
# floor only rejects severe blur, so soft/bokeh photos are not discarded.
MIN_SHARPNESS = 12.0
MIN_TILE_STD = 3.0
# Geometry
MAX_DETECT_PARTS = 5           # remember "looks like a grid" up to 5x5
MAX_SPLIT_PARTS = 3            # only auto-split regular 1x2..3x3 layouts
MIN_CELL_FRACTION = 0.12       # no sliver tiles
MAX_AXIS = 4000                # refuse absurd canvases before doing numpy work
SEAM_SCORE_MIN = 4.0           # boundary gradient / median gradient
SEAM_AMPLITUDE_MIN = 8.0       # grey levels
# A complete 3x3 grid is strong evidence on its own: platform grids often have
# white gutters between panels, so the seam gradient is only a few grey levels.
# Such a grid is only accepted when BOTH axes show the same periodic structure.
SEAM_GRID_AMPLITUDE_MIN = 4.5
SEAM_GRID_SCORE_MIN = 2.0
# A single-seam split needs either a clearly strong discontinuity or two clearly
# independent lines; a long structure inside one photograph is neither.
SEAM_STRONG_AMPLITUDE = 20.0
SEAM_TOLERANCE_FRAC = 0.020
# Two adjacent pixel lines inside one photograph are strongly correlated even
# across a hard edge (a door frame, a horizon). Two panels of a collage come from
# different photographs and are not. This is what separates a real seam from a
# long vertical structure that merely looks like one.
SEAM_MAX_CORRELATION = 0.60
FLAT_BAND_STD = 6.0            # a near-uniform separator/gutter line
MAX_FLAT_BAND_FRAC = 0.04
ANALYSIS_MAX_SIDE = 1600       # detection runs on a bounded copy

VALID = "valid"
LOW_RESOLUTION = "low_resolution"
TOO_BLURRY = "too_blurry"
BLANK_TILE = "blank_tile"
ODD_ASPECT = "odd_aspect"
DUPLICATE_RUN = "duplicate_run"
DUPLICATE_HISTORY = "duplicate_history"
ENCODE_FAILED = "encode_failed"
CORRUPT = "corrupt"

STATUS_NO_COLLAGE = "no_collage"
STATUS_SPLIT_OK = "split_ok"
STATUS_SPLIT_PARTIAL = "split_partial"
STATUS_NEEDS_MANUAL = "needs_manual_crop"
STATUS_LOW_RESOLUTION = "low_resolution"
STATUS_DUPLICATE = "duplicate_only"
STATUS_FAILED = "failed"

# Statuses that never count as an independent photography reference.
UNRESOLVED_STATUSES = {STATUS_NEEDS_MANUAL, STATUS_LOW_RESOLUTION, STATUS_DUPLICATE,
                       STATUS_FAILED}


class CollageError(ValueError):
    """A deterministic, reportable failure; the original is never modified."""


def record_is_current(record: dict | None) -> bool:
    """A record may only contribute numbers when written by this algorithm."""
    return (isinstance(record, dict)
            and str(record.get("algorithm_version", "")) == str(ALGORITHM_VERSION))



def _display_image(image: Image.Image) -> Image.Image:
    """Decode orientation and normalise to RGB without touching the source file."""
    if getattr(image, "n_frames", 1) != 1:
        raise CollageError("animated_or_multiframe")
    rgb = ImageOps.exif_transpose(image)
    return rgb.convert("RGB")


def _profiles(gray: np.ndarray) -> tuple[np.ndarray, np.ndarray]:
    height, width = gray.shape
    vertical = np.abs(np.diff(gray, axis=0)).mean(axis=1) if height > 1 else np.zeros(0, np.float32)
    horizontal = np.abs(np.diff(gray, axis=1)).mean(axis=0) if width > 1 else np.zeros(0, np.float32)
    return vertical.astype(np.float64), horizontal.astype(np.float64)


def _uniformity(gray: np.ndarray) -> tuple[np.ndarray, np.ndarray]:
    """Per-row / per-column standard deviation: separator gutters are near-flat."""
    rows = gray.std(axis=1) if gray.size else np.zeros(0, np.float32)
    cols = gray.std(axis=0) if gray.size else np.zeros(0, np.float32)
    return rows.astype(np.float64), cols.astype(np.float64)


def _find_axis(diff: np.ndarray, length: int, *, parts: int,
               score_min: float = SEAM_SCORE_MIN,
               amplitude_min: float = SEAM_AMPLITUDE_MIN,
               tolerance_frac: float = SEAM_TOLERANCE_FRAC,
               bands: list[tuple[int, int]] | None = None) -> dict | None:
    """Try one uniform split of ``length`` into ``parts``; return measured seams.

    A seam is either a measured grey-level discontinuity (two photographs meet
    directly) or a near-uniform separator band between two panels. The second
    case is common on platform collages with white gutters, where the seam has
    almost no gradient because both sides are white; those are still real borders
    and must not be missed.
    """
    if parts < 2 or length < parts * 8 or len(diff) < length - 1:
        return None
    expected = [int(round(length * index / parts)) for index in range(1, parts)]
    window = max(3, int(round(length * 0.015)))
    tolerance = max(3, int(round(length * tolerance_frac)))
    baseline = float(np.median(diff)) or 1e-6
    bands = bands or []
    seams = []
    for want in expected:
        band = next(((start, end) for start, end in bands
                     if start - tolerance <= want <= end + tolerance), None)
        if band is not None and 0 < band[0] < band[1] < length:
            seams.append({"at": (band[0] + band[1]) // 2, "amplitude": 0.0,
                          "score": 0.0, "gutter": True, "band": [band[0], band[1]]})
            continue
        low = max(1, want - window)
        high = min(length - 1, want + window)
        if high <= low:
            return None
        segment = diff[low - 1:high - 1]          # diff[i] separates row i / i+1
        found = low + int(np.argmax(segment))
        peak = float(diff[found - 1])
        if abs(found - want) > tolerance:
            return None
        if peak < amplitude_min or peak / baseline < score_min:
            return None
        seams.append({"at": found, "amplitude": round(peak, 3),
                      "score": round(peak / baseline, 3), "gutter": False})
    bounds = [0, *[seam["at"] for seam in seams], length]
    sizes = [right - left for left, right in zip(bounds, bounds[1:])]
    if any(size < length * MIN_CELL_FRACTION for size in sizes):
        return None
    return {"parts": parts, "seams": seams, "sizes": sizes}


def _candidate_parts(diff: np.ndarray, length: int, *, score_min: float,
                     amplitude_min: float, tolerance_frac: float,
                     bands: list[tuple[int, int]] | None = None) -> list[dict]:
    candidates = []
    for parts in range(2, MAX_DETECT_PARTS + 1):
        measured = _find_axis(diff, length, parts=parts, score_min=score_min,
                              amplitude_min=amplitude_min, tolerance_frac=tolerance_frac,
                              bands=bands)
        if measured:
            candidates.append(measured)
    return candidates


def _flat_bands(uniformity: np.ndarray, length: int) -> list[tuple[int, int]]:
    """Runs of near-uniform rows/columns: a printed separator or whitespace gutter."""
    if uniformity.size < length:
        return []
    flat = uniformity < FLAT_BAND_STD
    bands = []
    start = None
    max_band = max(2, int(round(length * MAX_FLAT_BAND_FRAC)))
    for index, value in enumerate(flat):
        if value and start is None:
            start = index
        elif not value and start is not None:
            if index - start >= 2 and index - start <= max_band:
                bands.append((start, index))
            start = None
    if start is not None and length - start >= 2 and length - start <= max_band:
        bands.append((start, length))
    return bands


def _seam_cut(seam_at: int, bands: list[tuple[int, int]]) -> tuple[int, int]:
    """Return (end_of_previous_tile, start_of_next_tile) as half-open row indices."""
    for start, end in bands:
        if start <= seam_at <= end:
            return start, end
    return max(0, seam_at - 1), min(seam_at, 1 << 30)


def _pearson(first: np.ndarray, second: np.ndarray) -> float:
    first = np.asarray(first, dtype=np.float64).ravel()
    second = np.asarray(second, dtype=np.float64).ravel()
    if first.size < 2 or first.std() < 1e-6 or second.std() < 1e-6:
        return 1.0
    return float(np.corrcoef(first, second)[0, 1])


def _seam_is_discontinuous(gray: np.ndarray, axis: str, at: int,
                           bands: list[tuple[int, int]]) -> tuple[float, bool]:
    """Measure whether two lines across the candidate seam are independent.

    Returns ``(correlation, has_gutter)``. A near-uniform separator band is
    accepted evidence even when both sides happen to be similar.
    """
    height, width = gray.shape
    if axis == "rows":
        if at < 1 or at >= height:
            return 1.0, False
        correlation = _pearson(gray[at - 1], gray[at])
    else:
        if at < 1 or at >= width:
            return 1.0, False
        correlation = _pearson(gray[:, at - 1], gray[:, at])
    has_gutter = any(start <= at <= end for start, end in bands)
    return correlation, has_gutter


def _accept_axis_candidate(gray: np.ndarray, axis: str, measured: dict,
                           bands: list[tuple[int, int]]) -> bool:
    """Single-panel-wide seams need discontinuity evidence; 3+ grids do not.

    For a two-part split the geometry is weak evidence (one line only), so the
    lines on both sides must not be a continuous photograph. A 3x3/3x2 grid needs
    two equal seams on the same axis plus a second axis, which a single exposure
    practically never produces; its seams may be similar (same location, similar
    background) and are accepted on geometry.
    """
    if measured["parts"] >= 3:
        return True
    height, width = gray.shape
    for seam in measured["seams"]:
        if seam.get("gutter"):
            # A uniform band only proves a border when photo content is present
            # on both sides; a bright sky band inside one photo is not a collage.
            band = seam.get("band") or []
            if len(band) != 2:
                return False
            start, end = band
            if axis == "rows":
                before = gray[max(0, start - 12):start]
                after = gray[end:min(height, end + 12)]
                before_std = float(before.std()) if before.size else 0.0
                after_std = float(after.std()) if after.size else 0.0
            else:
                before = gray[:, max(0, start - 12):start]
                after = gray[:, end:min(width, end + 12)]
                before_std = float(before.std()) if before.size else 0.0
                after_std = float(after.std()) if after.size else 0.0
            if min(before_std, after_std) < 6.0:
                return False
            continue
        correlation, has_gutter = _seam_is_discontinuous(gray, axis, seam["at"], bands)
        seam["correlation"] = round(correlation, 4)
        if has_gutter:
            continue
        if seam["amplitude"] >= SEAM_STRONG_AMPLITUDE:
            continue
        if correlation < SEAM_MAX_CORRELATION:
            continue
        return False
    return True


def _sharpness(tile: Image.Image) -> float:
    gray = tile.convert("L")
    if max(gray.size) > 640:
        gray = gray.copy()
        gray.thumbnail((640, 640), Image.Resampling.BILINEAR)
    array = np.asarray(gray, dtype=np.float32)
    if array.shape[0] < 3 or array.shape[1] < 3:
        return 0.0
    laplacian = (-4.0 * array[1:-1, 1:-1] + array[:-2, 1:-1] + array[2:, 1:-1]
                 + array[1:-1, :-2] + array[1:-1, 2:])
    return float(laplacian.var())


def _tile_quality(tile: Image.Image) -> dict:
    width, height = tile.size
    area = width * height
    short = min(width, height)
    aspect = width / height if height else 0.0
    grain = float(np.asarray(tile.convert("L"), dtype=np.float32).std())
    sharp = _sharpness(tile)
    reasons = []
    if short < MIN_CHILD_SHORT_SIDE or area < MIN_CHILD_AREA:
        reasons.append(LOW_RESOLUTION)
    if not (MIN_CHILD_ASPECT <= aspect <= MAX_CHILD_ASPECT):
        reasons.append(ODD_ASPECT)
    if sharp < MIN_SHARPNESS:
        reasons.append(TOO_BLURRY)
    if grain < MIN_TILE_STD:
        reasons.append(BLANK_TILE)
    return {"width": width, "height": height, "aspect": round(aspect, 4),
            "sharpness": round(sharp, 3), "grayscale_std": round(grain, 3),
            "status": reasons[0] if reasons else VALID, "reasons": reasons}


def _axis_decision(strict: list[dict], grid: list[dict], *, other_axis_parts: int,
                   allow_grid: bool) -> tuple[int, dict | None, str, str]:
    """Choose one supported split for an axis, or report why it cannot be trusted.

    Denser regular grids (4/5-part) and mutually inconsistent seam sets are not
    "close enough" to a 2- or 3-part split: cutting them would deliver large
    blocks that are not independent photographs. They return a problem instead.
    """
    supported = [c for c in strict if c["parts"] <= MAX_SPLIT_PARTS]
    dense = [c for c in strict if c["parts"] > MAX_SPLIT_PARTS]
    if dense:
        return 1, None, "dense_grid", f"dense_grid_{max(c['parts'] for c in dense)}_part"
    distinct = sorted({c["parts"] for c in supported})
    if len(distinct) > 1:
        return 1, None, "conflicting", "conflicting_boundaries_" + "-".join(str(p) for p in distinct)
    if supported:
        return supported[0]["parts"], supported[0], "", ""
    if not allow_grid or other_axis_parts < 2:
        return 1, None, "", ""
    grid_dense = [c for c in grid if c["parts"] > MAX_SPLIT_PARTS]
    if grid_dense:
        return 1, None, "dense_grid", f"dense_grid_{max(c['parts'] for c in grid_dense)}_part"
    grid_supported = [c for c in grid if c["parts"] <= MAX_SPLIT_PARTS]
    distinct = sorted({c["parts"] for c in grid_supported})
    if len(distinct) > 1:
        return 1, None, "conflicting", "conflicting_low_contrast_boundaries"
    if grid_supported:
        return grid_supported[0]["parts"], grid_supported[0], "", ""
    return 1, None, "", ""


def analyze(image: Image.Image) -> dict:
    """Detect a regular grid without cutting anything.

    Returns ``{"status", "layout", "rows", "cols", "seams", "reason"}`` where
    ``status`` is one of ``no_collage`` / ``split_ok`` / ``needs_manual_crop``.
    """
    display = _display_image(image)
    width, height = display.size
    if min(width, height) < 200:
        return {"status": STATUS_NO_COLLAGE, "layout": "single_image", "rows": 1, "cols": 1,
                "seams": {}, "reason": "image_smaller_than_candidate_floor"}
    if max(width, height) > 40_000_000:
        raise CollageError("image_area_exceeds_limit")
    scale = min(1.0, ANALYSIS_MAX_SIDE / max(width, height))
    probe = display
    if scale < 1.0:
        probe = display.resize((max(1, int(width * scale)), max(1, int(height * scale))),
                               Image.Resampling.BILINEAR)
    gray = np.asarray(probe.convert("L"), dtype=np.float32)
    height_p, width_p = gray.shape
    rows_uniformity, cols_uniformity = _uniformity(gray)
    row_bands = _flat_bands(rows_uniformity, height_p)
    col_bands = _flat_bands(cols_uniformity, width_p)
    vertical_diff, horizontal_diff = _profiles(gray)

    strict_rows = [candidate for candidate in _candidate_parts(
        vertical_diff, height_p, score_min=SEAM_SCORE_MIN, amplitude_min=SEAM_AMPLITUDE_MIN,
        tolerance_frac=SEAM_TOLERANCE_FRAC, bands=row_bands)
        if _accept_axis_candidate(gray, "rows", candidate, row_bands)]
    strict_cols = [candidate for candidate in _candidate_parts(
        horizontal_diff, width_p, score_min=SEAM_SCORE_MIN, amplitude_min=SEAM_AMPLITUDE_MIN,
        tolerance_frac=SEAM_TOLERANCE_FRAC, bands=col_bands)
        if _accept_axis_candidate(gray, "cols", candidate, col_bands)]
    loose_rows = _candidate_parts(vertical_diff, height_p, score_min=2.0, amplitude_min=6.0,
                                  tolerance_frac=0.03, bands=row_bands)
    loose_cols = _candidate_parts(horizontal_diff, width_p, score_min=2.0, amplitude_min=6.0,
                                  tolerance_frac=0.03, bands=col_bands)
    # Low-contrast grid seams (white gutters) are only trusted when the other
    # axis independently shows the same periodic layout.
    grid_rows = [candidate for candidate in _candidate_parts(
        vertical_diff, height_p, score_min=SEAM_GRID_SCORE_MIN,
        amplitude_min=SEAM_GRID_AMPLITUDE_MIN, tolerance_frac=SEAM_TOLERANCE_FRAC,
        bands=row_bands) if candidate["parts"] >= 3]
    grid_cols = [candidate for candidate in _candidate_parts(
        horizontal_diff, width_p, score_min=SEAM_GRID_SCORE_MIN,
        amplitude_min=SEAM_GRID_AMPLITUDE_MIN, tolerance_frac=SEAM_TOLERANCE_FRAC,
        bands=col_bands) if candidate["parts"] >= 3]

    row_parts, row_measure, row_problem, row_reason = _axis_decision(
        strict_rows, grid_rows, other_axis_parts=1, allow_grid=False)
    col_parts, col_measure, col_problem, col_reason = _axis_decision(
        strict_cols, grid_cols, other_axis_parts=1, allow_grid=False)
    if not row_problem and row_parts == 1 and col_parts >= 2:
        row_parts, row_measure, row_problem, row_reason = _axis_decision(
            strict_rows, grid_rows, other_axis_parts=col_parts, allow_grid=True)
    if not col_problem and col_parts == 1 and row_parts >= 2:
        col_parts, col_measure, col_problem, col_reason = _axis_decision(
            strict_cols, grid_cols, other_axis_parts=row_parts, allow_grid=True)
    detections = {
        "row_parts_found": sorted({c["parts"] for c in (*strict_rows, *grid_rows)}),
        "col_parts_found": sorted({c["parts"] for c in (*strict_cols, *grid_cols)}),
    }
    if row_problem or col_problem:
        return {"status": STATUS_NEEDS_MANUAL,
                "layout": f"unsupported_{row_parts}x{col_parts}",
                "rows": 1, "cols": 1, "seams": {}, "detections": detections,
                "reason": row_reason or col_reason or "unsupported_grid"}
    if row_parts == 1 and col_parts == 1:
        # Nothing splittable. A strong multi-seam pattern that is not a regular
        # 1x2..3x3 grid is reported as "needs manual crop" instead of being
        # silently counted as a single usable photograph.
        unsupported = [c["parts"] for c in (*loose_rows, *loose_cols) if c["parts"] > MAX_SPLIT_PARTS]
        if unsupported:
            return {"status": STATUS_NEEDS_MANUAL, "layout": f"irregular_{max(unsupported)}_part",
                    "rows": 1, "cols": 1, "seams": {}, "detections": detections,
                    "reason": "unusual_grid_density_beyond_supported_layouts"}
        return {"status": STATUS_NO_COLLAGE, "layout": "single_image", "rows": 1, "cols": 1,
                "seams": {}, "detections": detections, "reason": "no_supported_uniform_seams"}

    scale_back = 1.0 / scale if scale < 1.0 else 1.0
    row_seams = (row_measure or {}).get("seams", [])
    col_seams = (col_measure or {}).get("seams", [])
    return {
        "status": STATUS_SPLIT_OK,
        "layout": f"grid_{row_parts}x{col_parts}",
        "rows": row_parts,
        "cols": col_parts,
        "detections": detections,
        "seams": {
            "rows": [round(seam["at"] * scale_back) for seam in row_seams],
            "cols": [round(seam["at"] * scale_back) for seam in col_seams],
            "row_scores": [seam["score"] for seam in row_seams],
            "col_scores": [seam["score"] for seam in col_seams],
            "row_correlation": [seam.get("correlation") for seam in row_seams],
            "col_correlation": [seam.get("correlation") for seam in col_seams],
            "row_bands": row_bands,
            "col_bands": col_bands,
        },
        "reason": "uniform_seams_measured",
    }


def _cut_axis(length: int, seams_scaled: list[int], bands_probe: list[tuple[int, int]],
              scale: float) -> list[tuple[int, int]]:
    """Return contiguous, non-overlapping half-open intervals along one axis."""
    display_bands = [(int(round(start / scale)), int(round(end / scale))) for start, end in bands_probe] \
        if scale else bands_probe
    cuts = [(0, length)]
    for seam in sorted(seams_scaled):
        end, start = _seam_cut(seam, display_bands)
        left_start, left_end = cuts[-1]
        end = max(left_start + 1, min(end, length))
        start = max(end, min(start, length))
        cuts[-1] = (left_start, end)
        cuts.append((start, length))
    # Trim the final interval so it ends at the image edge.
    cuts[-1] = (cuts[-1][0], length if cuts[-1][1] >= length else cuts[-1][1])
    return [(start, end) for start, end in cuts if end - start > 0]


def split(image: Image.Image) -> dict:
    """Detect and cut a collage; always returns a record, never half-written state."""
    started = time.monotonic()
    display = _display_image(image)
    detected = analyze(display)
    record = {"version": 1, "algorithm_version": ALGORITHM_VERSION,
              "status": STATUS_NO_COLLAGE, "layout": detected["layout"],
              "rows": detected["rows"], "cols": detected["cols"],
              "original_size": [display.width, display.height],
              "children": [], "reason": detected["reason"], "seams": detected.get("seams", {}),
              "detections": detected.get("detections", {})}
    if detected["status"] != STATUS_SPLIT_OK:
        record["status"] = detected["status"]
        record["elapsed_seconds"] = round(time.monotonic() - started, 4)
        return record

    # Recompute the probe scale exactly as analyze() did to map seams back.
    scale = min(1.0, ANALYSIS_MAX_SIDE / max(display.size))
    rows = _cut_axis(display.height, detected["seams"]["rows"], detected["seams"]["row_bands"], scale)
    cols = _cut_axis(display.width, detected["seams"]["cols"], detected["seams"]["col_bands"], scale)
    if len(rows) != detected["rows"] or len(cols) != detected["cols"]:
        record.update(status=STATUS_NEEDS_MANUAL, reason="seam_band_cut_mismatch")
        record["elapsed_seconds"] = round(time.monotonic() - started, 4)
        return record

    for top, bottom in rows:
        for left, right in cols:
            box = (left, top, right, bottom)
            tile = display.crop(box)
            if tile.width == 0 or tile.height == 0:
                continue
            quality = _tile_quality(tile)
            record["children"].append({
                "crop": [left, top, right - left, bottom - top],
                "source_size": [display.width, display.height],
                "size": [tile.width, tile.height],
                "quality": quality,
                "status": quality["status"],
                "_image": tile,
            })
    usable = [child for child in record["children"] if child["status"] == VALID]
    if usable and len(usable) == len(record["children"]):
        record["status"] = STATUS_SPLIT_OK
    elif usable:
        record["status"] = STATUS_SPLIT_PARTIAL
    else:
        record["status"] = STATUS_LOW_RESOLUTION
    record["elapsed_seconds"] = round(time.monotonic() - started, 4)
    return record


def count_summary(parent_status: str, children: list[dict]) -> dict:
    """Counting rule shared by the queue, summary and tests.

    A collage parent and its children are alternatives: when at least one child
    is usable the parent stops being an independent photo.
    """
    usable = [child for child in children if child.get("status") == VALID]
    rejected = [child for child in children
                if child.get("status") not in {VALID}]
    if parent_status == STATUS_NO_COLLAGE:
        return {"independent": 1, "parent_counts": True, "usable_children": 0,
                "rejected_children": 0}
    if parent_status in {STATUS_SPLIT_OK, STATUS_SPLIT_PARTIAL} and usable:
        return {"independent": len(usable), "parent_counts": False,
                "usable_children": len(usable), "rejected_children": len(rejected)}
    # No usable child: the original stays the only viewable candidate, but it is
    # not silently promoted to an independent photography reference.
    return {"independent": 0, "parent_counts": False, "usable_children": 0,
            "rejected_children": len(rejected)}


def _sha_bytes(raw: bytes) -> str:
    return hashlib.sha256(raw).hexdigest()


def _encode_png(tile: Image.Image) -> bytes:
    import io
    buffer = io.BytesIO()
    tile.save(buffer, format="PNG", compress_level=6)
    return buffer.getvalue()


def _inside(path: Path, root: Path) -> bool:
    try:
        return not path.is_symlink() and path.resolve().is_relative_to(root.resolve())
    except (OSError, RuntimeError):
        return False


def verify_record(folder: Path, record: dict, parent_sha: str, original_path) -> dict:
    """Verify a stored record without changing it.

    A record is reusable only when it was written by the current algorithm, its
    parent binding is intact, every path stays inside the run directory and every
    file hash matches. Corrupt files are reported and never overwritten.
    """
    from .integrity import sha_matches
    problems: list[str] = []
    bad_children: list[str] = []
    verified_children = 0
    outdated = not record_is_current(record)
    if str(record.get("parent_sha") or "") != parent_sha:
        problems.append("parent_binding_mismatch")
    images_root = (folder / "images").resolve()
    derived_root = (folder / "derived").resolve()
    source = Path(str(original_path or ""))
    if not _inside(source, images_root) or not sha_matches(source, parent_sha):
        problems.append("original_missing_or_changed")
    for child in record.get("children") or []:
        if not isinstance(child, dict):
            problems.append("child_record_invalid")
            continue
        sha = str(child.get("child_sha") or "")
        path = Path(str(child.get("path") or ""))
        if str(child.get("parent_sha") or "") != parent_sha:
            problems.append("child_parent_mismatch")
            bad_children.append(sha)
            continue
        if not sha or not _inside(path, derived_root):
            problems.append("child_path_outside_derived")
            bad_children.append(sha)
            continue
        if not sha_matches(path, sha):
            problems.append("child_missing_or_changed")
            bad_children.append(sha)
            continue
        verified_children += 1
    corrupt = any(problem in {"original_missing_or_changed", "child_missing_or_changed",
                              "child_path_outside_derived", "child_parent_mismatch",
                              "child_record_invalid"}
                  for problem in problems)
    return {"ok": not problems and not outdated,
            "outdated": outdated,
            "corrupt": corrupt,
            "problems": sorted(set(problems)),
            "bad_children": sorted(set(bad_children)),
            "verified_children": verified_children}


def process_original(folder: Path, row: dict, *, history=None, known_shas: set[str] | None = None,
                     record_only: bool = False) -> dict:
    """Analyse one received original and persist its derived record.

    Idempotent by ``parent_sha`` for records written by the current algorithm
    whose files still verify. An outdated record is snapshotted and recomputed by
    this explicit processing operation; a corrupt record is kept as evidence and
    marked failed instead of being regenerated over damaged files.
    """
    folder = Path(folder)
    parent_sha = str(row.get("asset_sha") or "")
    if not parent_sha:
        raise CollageError("missing_parent_sha")
    source = Path(str(row.get("original_path") or ""))
    images_root = (folder / "images").resolve()
    if source.is_symlink() or not source.resolve().is_relative_to(images_root) or not source.is_file():
        raise CollageError("original_outside_run")
    store = DerivedStore(folder)
    previous_version = None
    snapshot_path = ""
    own_children: dict[str, dict] = {}
    existing = store.get(parent_sha)
    if existing is not None:
        integrity = verify_record(folder, existing, parent_sha, source)
        if integrity["ok"]:
            return {**existing, "reused": True}
        if integrity["corrupt"]:
            bad = set(integrity["bad_children"])
            children = []
            for child in existing.get("children") or []:
                if not isinstance(child, dict):
                    continue
                updated = child
                if child.get("child_sha") in bad:
                    updated = {**child, "status": CORRUPT,
                               "corrupt_reason": "content_hash_mismatch_missing_or_unbound"}
                children.append(updated)
            original_bad = any(problem in {"original_missing_or_changed", "parent_binding_mismatch",
                                           "child_parent_mismatch",
                                           "child_path_outside_derived", "child_record_invalid"}
                               for problem in integrity["problems"])
            if original_bad:
                # The record itself cannot be trusted (wrong parent, escaped path,
                # changed original): nothing from it may count.
                for child in children:
                    child["status"] = CORRUPT
                    child["corrupt_reason"] = "record_integrity_failure"
                status = STATUS_FAILED
            else:
                usable = [child for child in children if child.get("status") == VALID]
                if usable and len(usable) == len(children):
                    status = STATUS_SPLIT_OK
                elif usable:
                    status = STATUS_SPLIT_PARTIAL
                elif children and all(child.get("status") in {DUPLICATE_RUN, DUPLICATE_HISTORY}
                                      for child in children):
                    status = STATUS_DUPLICATE
                else:
                    status = STATUS_LOW_RESOLUTION
            record = {**existing, "integrity": integrity, "status": status,
                      "reason": "integrity_failure:" + ",".join(integrity["problems"]),
                      "counts": count_summary(status, children), "children": children,
                      "checked_at": time.time()}
            if original_bad:
                record["status"] = STATUS_FAILED
                record["counts"] = count_summary(STATUS_FAILED, children)
            store.put(parent_sha, record)
            return {**record, "reused": False, "integrity": integrity}
        # Outdated version: keep the old record, old files and old SHA-keyed
        # human decisions, then recompute with the current rules.
        previous_version = str(existing.get("algorithm_version") or "legacy")
        snapshot_path = store.snapshot(parent_sha, existing)
        # A v1 Job may already have imported its own tiles into the library, so a
        # rebuilt index lists them as "history". They are this Job's own results,
        # not external repeats: prove identity through the old record, its parent
        # binding and the unchanged bytes, then let the current algorithm decide
        # their status again instead of excluding the Job's own work.
        from .integrity import sha_matches as _sha_matches
        derived_root = (folder / "derived").resolve()
        for child in existing.get("children") or []:
            if not isinstance(child, dict) or child.get("status") != VALID:
                continue
            sha = str(child.get("child_sha") or "")
            path = Path(str(child.get("path") or ""))
            if (not sha or str(child.get("parent_sha") or "") != parent_sha
                    or not _inside(path, derived_root) or not _sha_matches(path, sha)):
                continue
            own_children[sha] = child
        if own_children and history is not None:
            # Keep the external index honest for everyone else; the reclaimed
            # tiles stay counted through their own record, never twice.
            history.exclude(own_children)

    raw = source.read_bytes()
    if hashlib.sha256(raw).hexdigest() != parent_sha:
        raise CollageError("original_sha_changed")

    started = time.monotonic()
    with Image.open(source) as opened:
        opened.load()
        result = split(opened)
    record = {key: value for key, value in result.items() if key != "children"}
    record.pop("_image", None)
    record.update(parent_sha=parent_sha, processed_at=time.time(),
                  algorithm_version=ALGORITHM_VERSION,
                  elapsed_seconds=round(time.monotonic() - started, 4), children=[])
    if previous_version is not None:
        record["previous_algorithm_version"] = previous_version
        record["previous_record_snapshot"] = snapshot_path
        record["own_previous_children"] = len(own_children)
    children = []
    seen_children: set[str] = set()
    for item in result.get("children", []):
        tile = item.pop("_image", None)
        if tile is None:
            continue
        raw_png = _encode_png(tile)
        child_sha = _sha_bytes(raw_png)
        child = {**item, "child_sha": child_sha, "parent_sha": parent_sha,
                 "path": str((folder / "derived" / f"{child_sha}.png"))}
        if record_only:
            child["status"] = VALID
            children.append(child)
            continue
        target = folder / "derived" / f"{child_sha}.png"
        target.parent.mkdir(parents=True, exist_ok=True)
        if target.exists():
            if target.read_bytes() != raw_png:
                child["status"] = ENCODE_FAILED
                children.append(child)
                continue
        else:
            atomic_write(target, raw_png)
        if child_sha in seen_children:
            child["status"] = DUPLICATE_RUN
            child["duplicate_of"] = child_sha
        elif child["status"] == VALID:
            if known_shas and child_sha in known_shas:
                child["status"] = DUPLICATE_RUN
                child["duplicate_of"] = child_sha
            elif child_sha in own_children:
                # Same SHA as this Job's own verified older tile: keep the Job's
                # result identity (and its SHA-keyed human decision); the fresh
                # algorithm run, not the old verdict, decided the status.
                child["own_previous_result"] = True
                child["recovered_from_algorithm_version"] = previous_version
            elif history is not None:
                try:
                    match = history.consider(target)
                except (OSError, ValueError) as exc:
                    match = {"duplicate_of": "", "reason": "history_error:" + type(exc).__name__}
                if match:
                    child["status"] = DUPLICATE_HISTORY
                    child["duplicate_of"] = str(match.get("duplicate_of") or "")
                    child["duplicate_reason"] = str(match.get("reason") or "")
        seen_children.add(child_sha)
        if known_shas is not None:
            known_shas.add(child_sha)
        children.append(child)
    record["children"] = children
    if record["status"] in {STATUS_SPLIT_OK, STATUS_SPLIT_PARTIAL, STATUS_LOW_RESOLUTION}:
        usable = [child for child in children if child["status"] == VALID]
        if usable and len(usable) == len(children):
            record["status"] = STATUS_SPLIT_OK
        elif usable:
            record["status"] = STATUS_SPLIT_PARTIAL
        elif children and all(child["status"] in {DUPLICATE_RUN, DUPLICATE_HISTORY} for child in children):
            record["status"] = STATUS_DUPLICATE
        else:
            record["status"] = STATUS_LOW_RESOLUTION
    record["counts"] = count_summary(record["status"], children)
    record["integrity"] = {"ok": True, "problems": [], "verified_children": len(children)}
    record["elapsed_seconds"] = round(time.monotonic() - started, 4)
    store.put(parent_sha, record)
    return record


class DerivedStore:
    """Atomic ``derived.json`` with one record per original content hash."""

    def __init__(self, folder: Path):
        self.folder = Path(folder)
        self.path = self.folder / "derived.json"
        self.lock = threading.RLock()

    def _read(self) -> dict:
        try:
            data = json.loads(self.path.read_text("utf8"))
        except (OSError, ValueError):
            return {"version": 1, "items": {}}
        if not isinstance(data, dict) or not isinstance(data.get("items"), dict):
            return {"version": 1, "items": {}}
        return data

    def items(self) -> dict[str, dict]:
        with self.lock:
            return dict(self._read()["items"])

    def get(self, parent_sha: str) -> dict | None:
        with self.lock:
            value = self._read()["items"].get(parent_sha)
        return value if isinstance(value, dict) else None

    def put(self, parent_sha: str, record: dict) -> None:
        with self.lock:
            data = self._read()
            data["items"][parent_sha] = record
            payload = json.dumps(data, ensure_ascii=False, indent=2, sort_keys=True)
            atomic_write(self.path, payload.encode("utf8"))

    def snapshot(self, parent_sha: str, record: dict) -> str:
        """Keep a previous record verbatim before an explicit recomputation."""
        version = str(record.get("algorithm_version") or "legacy")
        target = (self.folder / "derived-snapshots"
                  / f"{parent_sha}@v{version}-{int(time.time())}.json")
        target.parent.mkdir(parents=True, exist_ok=True)
        payload = json.dumps({"parent_sha": parent_sha, "snapshot_of_version": version,
                              "snapshot_at": time.time(), "record": record},
                             ensure_ascii=False, indent=2, sort_keys=True)
        atomic_write(target, payload.encode("utf8"))
        return str(target)

    def children_intact(self, record: dict) -> bool:
        from .integrity import sha_matches
        if not record_is_current(record):
            return False
        derived_root = (self.folder / "derived").resolve()
        for child in record.get("children") or []:
            if not isinstance(child, dict):
                return False
            sha = str(child.get("child_sha") or "")
            path = Path(str(child.get("path") or ""))
            if not sha or not _inside(path, derived_root) or not sha_matches(path, sha):
                return False
            if str(child.get("parent_sha")) != str(record.get("parent_sha")):
                return False
        return True


class CollageWorker:
    """Single background thread: download never waits for splitting.

    A bounded number of queued originals is intentional; search is faster than the
    processor, and the queue is drained before the run is finalised.
    """

    def __init__(self, folder: Path, *, history=None, known_shas: set[str] | None = None,
                 on_record=None):
        self.folder = Path(folder)
        self.history = history
        self.known_shas = known_shas if known_shas is not None else set()
        self.on_record = on_record
        self._queue: queue.Queue = queue.Queue()
        self._stop = threading.Event()
        self._thread = threading.Thread(target=self._run, name="collage-worker", daemon=True)
        self.errors: list[dict] = []
        self.processed = 0
        self.seconds = 0.0
        self._lock = threading.Lock()
        self._thread.start()

    def enqueue(self, row: dict) -> None:
        sha = str(row.get("asset_sha") or "")
        if not sha:
            return
        self._queue.put((str(row.get("original_path") or ""), sha))

    def _run(self) -> None:
        while not self._stop.is_set():
            try:
                original_path, sha = self._queue.get(timeout=0.2)
            except queue.Empty:
                continue
            try:
                self._process(original_path, sha)
            finally:
                self._queue.task_done()

    def _process(self, original_path: str, sha: str) -> None:
        started = time.monotonic()
        try:
            record = process_original(self.folder, {"asset_sha": sha, "original_path": original_path},
                                      history=self.history, known_shas=self.known_shas)
            with self._lock:
                self.processed += 1
                self.seconds += time.monotonic() - started
            if self.on_record is not None:
                self.on_record(record)
        except (CollageError, OSError, ValueError, Image.DecompressionBombError) as exc:
            with self._lock:
                self.errors.append({"asset_sha": sha, "error": type(exc).__name__ + ": " + str(exc)[:200]})

    def drain(self, timeout: float | None = None) -> None:
        deadline = None if timeout is None else time.monotonic() + max(0.0, timeout)
        while True:
            if self._queue.unfinished_tasks == 0 and self._queue.empty():
                return
            if deadline is not None and time.monotonic() >= deadline:
                return
            time.sleep(0.05)

    def close(self, timeout: float | None = None) -> None:
        self.drain(timeout=timeout)
        self._stop.set()
        self._thread.join(5)

    def summary(self) -> dict:
        records = DerivedStore(self.folder).items()
        return summarize_records(records)


def usable_named_count(folder, rows, records: dict[str, dict], is_named=None) -> int:
    """How many *independent* name-hit photos the local stage has produced.

    Thin compatibility wrapper around :func:`ref_lab.collection_counts.compute`;
    Search, the queue API, the summary and counts.json all use that one function.
    """
    from .collection_counts import compute
    return compute(folder, rows, records, named=is_named)["usable_named"]


def summarize_records(records: dict[str, dict]) -> dict:
    """Aggregate stored records without the received-original rows.

    Used by the offline audit tool; the live product numbers come from
    :func:`ref_lab.collection_counts.compute`, which also checks files and rows.
    """
    totals = {"originals": 0, "collages": 0, "collage_split_ok": 0, "collage_partial": 0,
              "collage_needs_manual": 0, "collage_low_resolution": 0, "collage_duplicate": 0,
              "collage_failed": 0, "derived_total": 0, "derived_valid": 0, "derived_rejected": 0,
              "derived_duplicate": 0, "independent_from_children": 0, "outdated_records": 0}
    for record in records.values():
        if not isinstance(record, dict):
            continue
        if not record_is_current(record):
            totals["outdated_records"] += 1
            continue
        totals["originals"] += 1
        status = str(record.get("status") or STATUS_NO_COLLAGE)
        children = [child for child in record.get("children", []) if isinstance(child, dict)]
        if status != STATUS_NO_COLLAGE:
            totals["collages"] += 1
        if status == STATUS_SPLIT_OK:
            totals["collage_split_ok"] += 1
        elif status == STATUS_SPLIT_PARTIAL:
            totals["collage_partial"] += 1
        elif status == STATUS_NEEDS_MANUAL:
            totals["collage_needs_manual"] += 1
        elif status == STATUS_LOW_RESOLUTION:
            totals["collage_low_resolution"] += 1
        elif status == STATUS_DUPLICATE:
            totals["collage_duplicate"] += 1
        elif status == STATUS_FAILED:
            totals["collage_failed"] += 1
        totals["derived_total"] += len(children)
        usable = [child for child in children if child.get("status") == VALID]
        totals["derived_valid"] += len(usable)
        totals["independent_from_children"] += len(usable)
        totals["derived_rejected"] += sum(1 for child in children
                                          if child.get("status") not in {VALID, DUPLICATE_RUN,
                                                                          DUPLICATE_HISTORY})
        totals["derived_duplicate"] += sum(1 for child in children
                                           if child.get("status") in {DUPLICATE_RUN, DUPLICATE_HISTORY})
    return totals



