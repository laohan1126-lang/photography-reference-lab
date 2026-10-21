#!/usr/bin/env python3
"""Single-image human review for the frozen Ruby holdout.

This is an evaluation-method repair, not a new training round. It writes only
inside the isolated experiment directory. Frozen rankings, predictions, model
inputs and production K/I/M/X decisions are read-only.

The page shows one image at a time, stores three independent human dimensions
keyed by original SHA, recovers drafts after refresh, and only compares the
three already-frozen rankings after the owner submits.
"""
from __future__ import annotations

import argparse
from collections import Counter
from datetime import datetime, timezone
import hashlib
import hmac
import json
import math
import mimetypes
import os
from pathlib import Path
import secrets
import threading
import time
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import quote, unquote, urlsplit

from tools.learning_v1 import EXPERIMENT, load_json, source_group
from tools.learning_v1_report import STYLE, escape

PROTOCOL_VERSION = "ruby-single-image-review-v1"
EXPERIMENT_ID = "learning-loop-v1-20261018"
METHODS = ("baseline0", "baseline1", "candidate2")
METHOD_LABELS = {
    "baseline0": "原始入库顺序",
    "baseline1": "规则排序",
    "candidate2": "规则 + 正例相似检索",
}
REVIEW_PAGE = "ruby-human-review.html"
REPORT_PAGE = "ruby-human-report.html"
METRICS_FILE = "ruby-human-metrics.json"
LABELS_WORKING = "ruby-human-labels.json"
LABELS_FINAL = "ruby-human-labels-final.json"
BASELINE_FILE = "human-review-before.json"
REVIEW_ID_PREFIX = "R"

IDENTITY_CHOICES = {
    "target_cosplay": "确认是目标角色真人 Cosplay",
    "not_target": "不是目标角色，或并非真人 Cosplay",
    "uncertain": "无法确定",
}
PHOTOGRAPHY_CHOICES = {
    "useful": "值得用于拍摄参考",
    "limited": "参考价值有限",
    "unsuitable": "不适合",
    "uncertain": "无法判断",
}
AESTHETIC_CHOICES = {
    "like": "喜欢",
    "neutral": "一般",
    "dislike": "不喜欢",
    "uncertain": "暂时无法评价",
}
CHOICES = {"identity": IDENTITY_CHOICES, "photography": PHOTOGRAPHY_CHOICES, "aesthetic": AESTHETIC_CHOICES}
AESTHETIC_SCORE = {"like": 2, "neutral": 1, "dislike": 0}
DHASH_DISTANCE = 5
MAX_REASON = 300


class ExperimentDrift(RuntimeError):
    """The frozen experiment changed after the review started."""


class ValidationError(ValueError):
    """A review payload was not valid."""


class AlreadySubmitted(RuntimeError):
    """The final snapshot already exists; never overwrite it silently."""


def stamp() -> str:
    return datetime.now(timezone.utc).isoformat()


def sha256_bytes(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


def sha256_file(path: Path) -> str:
    return sha256_bytes(path.read_bytes())


def canonical(value: object) -> str:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))


def json_bytes(value: object) -> bytes:
    return (json.dumps(value, ensure_ascii=False, indent=2) + "\n").encode("utf-8")


def atomic_write(path: Path, data: bytes, *, read_only: bool = False) -> None:
    """Write via same-directory temp file, fsync, then atomic replace."""
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_name(f".{path.name}.{os.getpid()}.{secrets.token_hex(6)}.tmp")
    descriptor = os.open(temporary, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
    try:
        with os.fdopen(descriptor, "wb") as stream:
            stream.write(data)
            stream.flush()
            os.fsync(stream.fileno())
        if read_only:
            os.chmod(temporary, 0o444)
        for attempt in range(10):
            try:
                os.replace(temporary, path)
                break
            except (PermissionError, OSError):
                if attempt == 9:
                    raise
                time.sleep(0.05)
    finally:
        try:
            temporary.unlink(missing_ok=True)
        except OSError:
            pass


def save_json_atomic(path: Path, value: object, *, read_only: bool = False) -> None:
    atomic_write(path, json_bytes(value), read_only=read_only)


def file_state(experiment: Path, relative: str) -> dict:
    path = experiment / relative
    if not path.is_file():
        return {"exists": False, "sha256": None, "size": None}
    return {"exists": True, "sha256": sha256_file(path), "size": path.stat().st_size}


def input_hashes(experiment: Path) -> dict:
    names = ("freeze.json", "ruby-pool.json", "ruby-predictions.json", "ruby-evaluation.json", "model.json")
    return {name: file_state(experiment, name) for name in names}


def read_inputs(experiment: Path) -> dict:
    experiment = Path(experiment)
    required = ("ruby-pool.json", "ruby-predictions.json")
    missing = [name for name in required if not (experiment / name).is_file()]
    if missing:
        raise FileNotFoundError(f"Frozen experiment inputs missing under {experiment}: {', '.join(missing)}")
    result = {
        "freeze": load_json(experiment / "freeze.json") if (experiment / "freeze.json").is_file() else {},
        "pool": load_json(experiment / "ruby-pool.json"),
        "predictions": load_json(experiment / "ruby-predictions.json"),
        "evaluation": load_json(experiment / "ruby-evaluation.json") if (experiment / "ruby-evaluation.json").is_file() else {},
        "model": load_json(experiment / "model.json") if (experiment / "model.json").is_file() else {},
        "inputs": input_hashes(experiment),
    }
    for method in METHODS:
        if method not in result["predictions"]:
            raise ValueError(f"Frozen predictions are missing method {method}")
    return result


def dedupe_by_sha(pool: list[dict]) -> tuple[list[dict], list[dict]]:
    """One review sample per original SHA; later repeats are recorded, not shown."""
    kept: list[dict] = []
    duplicates: list[dict] = []
    seen: dict[str, dict] = {}
    for index, record in enumerate(pool):
        sha = record.get("asset_sha")
        if not isinstance(sha, str) or not sha:
            raise ValueError("Candidate without a valid asset SHA")
        if sha in seen:
            duplicates.append({"asset_sha": sha, "duplicate_position": index,
                               "kept_path": seen[sha].get("original_path"),
                               "duplicate_path": record.get("original_path"),
                               "kept_source": (seen[sha].get("source") or {}).get("page_url"),
                               "duplicate_source": (record.get("source") or {}).get("page_url")})
            continue
        seen[sha] = record
        kept.append(record)
    return kept, duplicates


def relative_image(record: dict, experiment: Path) -> str:
    path = Path(record.get("original_path", ""))
    try:
        relative = path.resolve().relative_to(Path(experiment).resolve())
        return quote(relative.as_posix(), safe="/:")
    except ValueError:
        return path.resolve().as_uri() if path.is_absolute() else ""


def dhash_distance(left: str, right: str) -> int | None:
    if not (isinstance(left, str) and isinstance(right, str) and len(left) == 16 and len(right) == 16):
        return None
    try:
        return (int(left, 16) ^ int(right, 16)).bit_count()
    except ValueError:
        return None


def build_review(experiment: Path = EXPERIMENT) -> dict:
    experiment = Path(experiment).resolve()
    inputs = read_inputs(experiment)
    unique, duplicates = dedupe_by_sha(inputs["pool"])
    ordered = sorted(unique, key=lambda record: record["asset_sha"])
    shas = [record["asset_sha"] for record in ordered]
    for method in METHODS:
        ranking = [record["asset_sha"] for record in inputs["predictions"][method]]
        if len(ranking) != len(set(ranking)) or set(ranking) != set(shas):
            raise ValueError(f"Frozen ranking {method} does not match the unique candidate pool")
    evaluation = inputs["evaluation"]
    overlap = {row.get("asset_sha") for row in evaluation.get("overlap_quarantined", []) if row.get("asset_sha")}
    training_shas = {record["asset_sha"] for record in load_json(experiment / "dataset.json")} if (experiment / "dataset.json").is_file() else set()
    if (experiment / "quarantine.json").is_file():
        training_shas |= {record["asset_sha"] for record in load_json(experiment / "quarantine.json")}

    near_pairs: list[dict] = []
    source_pairs: list[dict] = []
    for index, left in enumerate(ordered):
        for right in ordered[index + 1:]:
            distance = dhash_distance(left.get("dhash", ""), right.get("dhash", ""))
            if distance is not None and distance <= DHASH_DISTANCE:
                near_pairs.append({"left": left["asset_sha"], "right": right["asset_sha"], "distance": distance})
            left_group = source_group((left.get("source") or {}).get("page_url", ""))
            right_group = source_group((right.get("source") or {}).get("page_url", ""))
            if left_group and left_group == right_group:
                source_pairs.append({"left": left["asset_sha"], "right": right["asset_sha"], "source_group": left_group})

    blocked: dict[str, str] = {}
    for sha in shas:
        if sha in overlap:
            blocked[sha] = "TRAINING_OVERLAP"
        elif sha in training_shas:
            blocked[sha] = "TRAINING_SET_OVERLAP"
    for pair in near_pairs:
        blocked.setdefault(pair["right"], "NEAR_DUPLICATE")
    for pair in source_pairs:
        blocked.setdefault(pair["right"], "SAME_SOURCE_GROUP")

    assets: list[dict] = []
    for position, record in enumerate(ordered, start=1):
        sha = record["asset_sha"]
        path = Path(record.get("original_path", ""))
        actual = sha256_file(path) if path.is_file() else None
        verified = actual == sha
        if not verified:
            blocked[sha] = "IMAGE_BYTES_MISSING_OR_CHANGED"
        source = record.get("source") or {}
        assets.append({
            "asset_sha": sha,
            "review_id": f"{REVIEW_ID_PREFIX}{position:02d}",
            "display_order": position,
            "original_path": str(path.resolve()) if path.is_absolute() else str(path),
            "image_file": relative_image(record, experiment),
            "width": record.get("width"),
            "height": record.get("height"),
            "source": {"page_url": source.get("page_url", ""), "author": source.get("author", ""),
                       "title": source.get("title", "") or record.get("title", "")},
            "dhash": record.get("dhash", ""),
            "bytes_sha_verified": verified,
            "scorable": sha not in blocked,
            "unscorable_reason": blocked.get(sha),
        })

    source_urls = [asset["source"]["page_url"] for asset in assets if asset["source"]["page_url"]]
    hosts = sorted({urlsplit(url).netloc.lower() for url in source_urls if urlsplit(url).netloc})
    authors = sorted({asset["source"]["author"] for asset in assets if asset["source"]["author"]})
    source_ids = {source_group(url) for url in source_urls} - {None}
    independence = {
        "unique_assets": len(assets),
        "unique_source_pages": len(set(source_urls)),
        "source_hosts": hosts,
        "known_authors": authors,
        "known_author_count": len(authors),
        "distinct_source_groups": len(source_ids),
        "training_shas_detected": sorted(({sha for sha in shas if sha in training_shas} | overlap)),
        "duplicates_in_pool": duplicates,
        "near_duplicate_pairs": near_pairs,
        "same_source_group_pairs": source_pairs,
        "status": "UNVERIFIED_PLATFORM_ONLY" if (not authors or len(hosts) == 1) else "PARTIALLY_VERIFIED",
        "note": ("来源作者为空或集中在单一平台；这些图片只能作为本固定候选池的逐图人工样本，"
                 "不能宣称是相互独立的拍摄组或可外推到其他来源。"),
    }
    if not (experiment / "ruby-pool.json").is_file():
        raise FileNotFoundError("ruby-pool.json missing")

    doc = {
        "protocol": PROTOCOL_VERSION,
        "experiment_id": EXPERIMENT_ID,
        "experiment": str(experiment),
        "freeze_at": inputs["freeze"].get("at"),
        "inputs": inputs["inputs"],
        "review_order": shas,
        "assets": assets,
        "asset_by_sha": {asset["asset_sha"]: asset for asset in assets},
        "duplicates": duplicates,
        "independence": independence,
        "predictions": inputs["predictions"],
        "evaluation": evaluation,
        "model": inputs["model"],
    }
    write_review_page(doc)
    return doc


def public_asset(asset: dict) -> dict:
    return {
        "asset_sha": asset["asset_sha"],
        "review_id": asset["review_id"],
        "display_order": asset["display_order"],
        "width": asset["width"],
        "height": asset["height"],
        "source": asset["source"],
        "image_file": asset["image_file"],
        "scorable": asset["scorable"],
        "unscorable_reason": asset["unscorable_reason"],
    }


def entry_template(asset: dict) -> dict:
    return {
        "asset_sha": asset["asset_sha"],
        "review_id": asset["review_id"],
        "display_order": asset["display_order"],
        "source": asset["source"],
        "original_path": asset["original_path"],
        "image_file": asset["image_file"],
        "width": asset["width"],
        "height": asset["height"],
        "scorable": asset["scorable"],
        "unscorable_reason": asset["unscorable_reason"],
        "labels": {"identity": None, "photography": None, "aesthetic": None},
        "reason": "",
        "skipped": False,
        "status": "unrated",
        "reviewed_at": None,
        "saved_at": None,
    }


def normalize_entry(entry: dict, asset: dict) -> dict:
    base = entry_template(asset)
    labels = entry.get("labels") if isinstance(entry.get("labels"), dict) else {}
    for dimension in CHOICES:
        value = labels.get(dimension)
        base["labels"][dimension] = value if value in CHOICES[dimension] else None
    reason = entry.get("reason")
    base["reason"] = reason[:MAX_REASON] if isinstance(reason, str) else ""
    base["skipped"] = bool(entry.get("skipped"))
    base["status"] = entry.get("status") if entry.get("status") in {"unrated", "rated", "skipped"} else (
        "rated" if any(base["labels"].values()) or base["reason"] else "unrated")
    base["reviewed_at"] = entry.get("reviewed_at") if isinstance(entry.get("reviewed_at"), str) else None
    base["saved_at"] = entry.get("saved_at") if isinstance(entry.get("saved_at"), str) else None
    return base


def any_label(entry: dict) -> bool:
    return any((entry.get("labels") or {}).get(dimension) for dimension in CHOICES)


class LabelStore:
    """SHA-keyed draft store with atomic writes and a write-once final snapshot."""

    def __init__(self, experiment: Path, doc: dict):
        self.experiment = Path(experiment)
        self.doc = doc
        self.assets = {asset["asset_sha"]: asset for asset in doc["assets"]}
        self.path = self.experiment / LABELS_WORKING
        self.final_path = self.experiment / LABELS_FINAL
        self.lock = threading.RLock()

    def base(self) -> dict:
        return {
            "schema_version": 1,
            "protocol": PROTOCOL_VERSION,
            "experiment_id": EXPERIMENT_ID,
            "created_at": stamp(),
            "updated_at": stamp(),
            "status": "draft",
            "submitted_at": None,
            "freeze_at": self.doc.get("freeze_at"),
            "experiment_inputs": self.doc["inputs"],
            "review_order": self.doc["review_order"],
            "independence": self.doc["independence"],
            "assets": {asset["asset_sha"]: entry_template(asset) for asset in self.doc["assets"]},
        }

    def _validate(self, data: dict, *, allow_final: bool = False) -> dict:
        if not isinstance(data, dict):
            raise ExperimentDrift("Labels file is not an object")
        if data.get("protocol") != PROTOCOL_VERSION or data.get("experiment_id") != EXPERIMENT_ID:
            raise ExperimentDrift("Labels protocol or experiment ID mismatch")
        if data.get("review_order") != self.doc["review_order"]:
            raise ExperimentDrift("Review order changed")
        if canonical(data.get("experiment_inputs")) != canonical(self.doc["inputs"]):
            raise ExperimentDrift("Frozen experiment inputs changed after the review started")
        raw_assets = data.get("assets") if isinstance(data.get("assets"), dict) else {}
        if set(raw_assets) != set(self.assets):
            raise ExperimentDrift("Labels do not match the frozen asset SHA set")
        normalized = {}
        for sha, asset in self.assets.items():
            entry = raw_assets[sha]
            normalized[sha] = normalize_entry(entry if isinstance(entry, dict) else {}, asset)
        data["assets"] = normalized
        return data

    def load(self) -> dict:
        with self.lock:
            if not self.path.is_file():
                return self.base()
            return self._validate(load_json(self.path))

    def state(self) -> dict:
        with self.lock:
            data = self.load()
        entries = [data["assets"][sha] for sha in self.doc["review_order"]]
        return {
            "protocol": PROTOCOL_VERSION,
            "experiment_id": EXPERIMENT_ID,
            "status": data["status"],
            "submitted": data["status"] == "submitted",
            "updated_at": data["updated_at"],
            "assets": entries,
            "choices": CHOICES,
            "progress": progress(entries),
            "independence": self.doc["independence"],
            "final_exists": self.final_path.is_file(),
        }

    def draft(self, payload: dict) -> dict:
        if not isinstance(payload, dict):
            raise ValidationError("Draft payload must be an object")
        sha = payload.get("asset_sha")
        if sha not in self.assets:
            raise ValidationError("Unknown asset SHA")
        if not isinstance(payload.get("labels", {}), dict):
            raise ValidationError("labels must be an object")
        for dimension, value in (payload.get("labels") or {}).items():
            if dimension not in CHOICES or (value is not None and value not in CHOICES[dimension]):
                raise ValidationError(f"Invalid {dimension} label")
        reason = payload.get("reason", "")
        if reason is not None and (not isinstance(reason, str) or len(reason) > MAX_REASON):
            raise ValidationError("Reason must be a string of at most 300 characters")
        skipped = payload.get("skipped", False)
        if not isinstance(skipped, bool):
            raise ValidationError("skipped must be a boolean")
        labels_payload = payload.get("labels") or {}
        has_values = (any(value is not None for value in labels_payload.values())
                      or bool((reason or "").strip()) or skipped)
        with self.lock:
            data = self.load()
            if data["status"] == "submitted":
                raise AlreadySubmitted("The final review has already been submitted")
            if not has_values:
                # Browsing or navigating away must not create an empty draft entry.
                return {"ok": True, "asset_sha": sha, "saved_at": None, "status": "noop"}
            entry = data["assets"][sha]
            for dimension, value in (payload.get("labels") or {}).items():
                entry["labels"][dimension] = value
            if reason is not None:
                entry["reason"] = reason
            if any_label(entry) or entry["reason"]:
                entry["skipped"] = False
                entry["status"] = "rated"
                entry["reviewed_at"] = entry["reviewed_at"] or stamp()
            elif skipped:
                entry["skipped"] = True
                entry["status"] = "skipped"
            else:
                entry["status"] = "unrated"
            entry["saved_at"] = stamp()
            data["updated_at"] = entry["saved_at"]
            data["status"] = "draft"
            save_json_atomic(self.path, data)
            return {"ok": True, "asset_sha": sha, "saved_at": entry["saved_at"], "status": entry["status"]}

    def submit(self) -> dict:
        with self.lock:
            if self.final_path.exists():
                raise AlreadySubmitted(f"Final snapshot already exists: {self.final_path.name}")
            data = self.load()
            data["status"] = "submitted"
            data["submitted_at"] = stamp()
            data["updated_at"] = data["submitted_at"]
            save_json_atomic(self.path, data)
            snapshot = json.loads(json.dumps(data, ensure_ascii=False))
            snapshot["snapshot"] = {
                "written_at": stamp(),
                "read_only": True,
                "source_file": LABELS_WORKING,
                "source_sha256": sha256_bytes(self.path.read_bytes()),
                "protocol": PROTOCOL_VERSION,
            }
            atomic_write(self.final_path, json_bytes(snapshot), read_only=True)
            atomically_verify_final(self.final_path)
            metrics = write_report(self.experiment, self.doc, snapshot, mode="post_submit")
            return {"ok": True, "report": REPORT_PAGE, "labels_sha256": snapshot["snapshot"]["source_sha256"],
                    "metrics": metrics["outcome"]}


def atomically_verify_final(path: Path) -> None:
    if not Path(path).is_file():
        raise RuntimeError("Final snapshot write failed")


def progress(entries: list[dict]) -> dict:
    rated = sum(1 for entry in entries if any_label(entry))
    skipped = sum(1 for entry in entries if entry.get("skipped") and not any_label(entry))
    unrated = len(entries) - rated - skipped
    return {"total": len(entries), "rated": rated, "skipped": skipped, "unrated": unrated}


# ---------------------------------------------------------------------------
# Metrics over the already-frozen rankings. No re-training, no re-ranking.

def ndcg_at_k(ranking: list[str], scores: dict[str, int | None], k: int = 5) -> float | None:
    """Graded NDCG@k; returns None when any top-k relevance is unknown.

    gain = 2**relevance - 1 with relevance like=2, neutral=1, dislike=0.
    Missing labels are never silently treated as zero.
    """
    top = ranking[:k]
    relevances: list[int] = []
    for sha in top:
        value = scores.get(sha)
        if value is None:
            return None
        relevances.append(value)
    if not relevances:
        return None
    dcg = sum((2 ** relevance - 1) / math.log2(position + 2)
              for position, relevance in enumerate(relevances))
    ideal = sorted(relevances, reverse=True)
    idcg = sum((2 ** relevance - 1) / math.log2(position + 2)
               for position, relevance in enumerate(ideal))
    return dcg / idcg if idcg else 0.0


def score_map(doc: dict, labels: dict) -> tuple[dict[str, int | None], dict[str, str]]:
    scores: dict[str, int | None] = {}
    reasons: dict[str, str] = {}
    for asset in doc["assets"]:
        sha = asset["asset_sha"]
        entry = (labels.get("assets") or {}).get(sha, {})
        label = (entry.get("labels") or {}).get("aesthetic")
        if not asset["scorable"]:
            scores[sha] = None
            reasons[sha] = "不可计分：" + str(asset.get("unscorable_reason") or "unknown")
        elif label in AESTHETIC_SCORE:
            scores[sha] = AESTHETIC_SCORE[label]
        elif label == "uncertain":
            scores[sha] = None
            reasons[sha] = "暂时无法评价"
        elif entry.get("skipped"):
            scores[sha] = None
            reasons[sha] = "已跳过"
        elif entry.get("saved_at"):
            scores[sha] = None
            reasons[sha] = "已保存但未选审美维度"
        else:
            scores[sha] = None
            reasons[sha] = "未评价"
    return scores, reasons


def _label_value(labels: dict, sha: str, dimension: str) -> str | None:
    entry = (labels.get("assets") or {}).get(sha, {})
    value = (entry.get("labels") or {}).get(dimension)
    return value if value in CHOICES[dimension] else None


def method_metrics(doc: dict, labels: dict, scores: dict[str, int | None], method: str) -> dict:
    ranking = [record["asset_sha"] for record in doc["predictions"][method]]
    top = ranking[:5]
    rated = [sha for sha in top if scores.get(sha) is not None]
    likes = [sha for sha in top if scores.get(sha) == 2]
    neutral = [sha for sha in top if scores.get(sha) == 1]
    dislikes = [sha for sha in top if scores.get(sha) == 0]
    identity_values = [_label_value(labels, sha, "identity") for sha in top]
    photo_values = [_label_value(labels, sha, "photography") for sha in top]
    asset_by_sha = doc["asset_by_sha"]

    def top_entry(sha: str, position: int) -> dict:
        asset = asset_by_sha[sha]
        entry = (labels.get("assets") or {}).get(sha, {})
        return {
            "rank": position,
            "asset_sha": sha,
            "review_id": asset["review_id"],
            "image_file": asset["image_file"],
            "source_page": asset["source"]["page_url"],
            "scorable": asset["scorable"],
            "aesthetic": (entry.get("labels") or {}).get("aesthetic"),
            "identity": (entry.get("labels") or {}).get("identity"),
            "photography": (entry.get("labels") or {}).get("photography"),
            "reason": entry.get("reason", ""),
        }

    return {
        "method": method,
        "label": METHOD_LABELS[method],
        "top5": [top_entry(sha, position) for position, sha in enumerate(top, start=1)],
        "top5_like": len(likes) if rated else None,
        "top5_like_rated": len(rated),
        "top5_neutral": len(neutral) if rated else None,
        "top5_dislike": len(dislikes) if rated else None,
        "top5_rated": len(rated),
        "top5_missing": len(top) - len(rated),
        "ndcg_at_5": ndcg_at_k(ranking, scores, 5),
        "ndcg_status": "SCORED" if len(rated) == len(top) and top else "MISSING_LABELS",
        "identity_confirmed": sum(value == "target_cosplay" for value in identity_values) if any(identity_values) else None,
        "identity_wrong": sum(value == "not_target" for value in identity_values) if any(identity_values) else None,
        "identity_uncertain": sum(value in {None, "uncertain"} for value in identity_values),
        "identity_rated": sum(value is not None for value in identity_values),
        "photography_useful": sum(value == "useful" for value in photo_values) if any(photo_values) else None,
        "photography_limited": sum(value == "limited" for value in photo_values) if any(photo_values) else None,
        "photography_uncertain": sum(value in {None, "uncertain"} for value in photo_values),
        "photography_rated": sum(value is not None for value in photo_values),
        "rank_index": {sha: position for position, sha in enumerate(ranking, start=1)},
    }


def ranking_differences(doc: dict) -> dict:
    orders = {method: [record["asset_sha"] for record in doc["predictions"][method]] for method in METHODS}
    top5 = {method: set(orders[method][:5]) for method in METHODS}
    pairs = {}
    for index, left in enumerate(METHODS):
        for right in METHODS[index + 1:]:
            pairs[f"{left}__{right}"] = {
                "same_order": orders[left] == orders[right],
                "same_top5_set": top5[left] == top5[right],
                "entered_top5": sorted(top5[right] - top5[left]),
                "left_top5": sorted(top5[left] - top5[right]),
                "reordered_within_top5": top5[left] == top5[right] and orders[left][:5] != orders[right][:5],
            }
    return {"orders": orders, "top5_sets": {key: sorted(value) for key, value in top5.items()},
            "pairs": pairs,
            "no_ranking_difference": all(orders[method] == orders[METHODS[0]] for method in METHODS),
            "candidate2_vs_baseline1_ranking_identical": orders["candidate2"] == orders["baseline1"],
            "candidate2_vs_baseline1_top5_identical": top5["candidate2"] == top5["baseline1"],
            "candidate2_vs_baseline1_order_identical": orders["candidate2"] == orders["baseline1"]}


def review_cases(doc: dict, labels: dict, scores: dict[str, int | None]) -> dict:
    rank = {method: {record["asset_sha"]: index + 1 for index, record in enumerate(doc["predictions"][method])}
            for method in METHODS}
    asset_by_sha = doc["asset_by_sha"]
    rule_state = {record["asset_sha"]: record.get("rule_state") for record in doc["predictions"]["baseline1"]}
    liked = [sha for sha, score in scores.items() if score == 2]
    disliked = [sha for sha, score in scores.items() if score == 0]

    def row(sha: str, **extra) -> dict:
        return {"asset_sha": sha, "review_id": asset_by_sha[sha]["review_id"], **extra}

    pushed_vs_rule = [row(sha, baseline1_rank=rank["baseline1"][sha], candidate2_rank=rank["candidate2"][sha])
                      for sha in liked if rank["candidate2"][sha] > 5 and rank["baseline1"][sha] <= 5]
    pushed_vs_arrival = [row(sha, baseline0_rank=rank["baseline0"][sha], candidate2_rank=rank["candidate2"][sha])
                         for sha in liked if rank["candidate2"][sha] > 5 and rank["baseline0"][sha] <= 5]
    pulled_up = [row(sha, baseline1_rank=rank["baseline1"][sha], candidate2_rank=rank["candidate2"][sha])
                 for sha in disliked if rank["candidate2"][sha] <= 5 and rank["baseline1"][sha] > 5]
    disliked_early = {method: [row(sha, rank=rank[method][sha]) for sha in disliked if rank[method][sha] <= 5]
                      for method in METHODS}
    liked_late = {method: [row(sha, rank=rank[method][sha]) for sha in liked if rank[method][sha] > 5]
                  for method in METHODS}

    rule_candidate_but_dislike = [row(sha, rule_state=rule_state[sha], aesthetic_score=scores[sha])
                                  for sha in disliked if rule_state.get(sha) == "candidate"]
    rule_not_candidate_but_like = [row(sha, rule_state=rule_state[sha], aesthetic_score=scores[sha])
                                   for sha in liked if rule_state.get(sha) != "candidate"]
    identity_confirmed_but_rule_needs_evidence = [
        row(sha, rule_state=rule_state.get(sha))
        for sha in doc["review_order"]
        if _label_value(labels, sha, "identity") == "target_cosplay" and rule_state.get(sha) != "candidate"]
    identity_wrong_but_rule_candidate = [
        row(sha, rule_state=rule_state.get(sha))
        for sha in doc["review_order"]
        if _label_value(labels, sha, "identity") == "not_target" and rule_state.get(sha) == "candidate"]
    photography_useful_but_rule_not_candidate = [
        row(sha, rule_state=rule_state.get(sha))
        for sha in doc["review_order"]
        if _label_value(labels, sha, "photography") == "useful" and rule_state.get(sha) != "candidate"]
    photography_unsuitable_but_rule_candidate = [
        row(sha, rule_state=rule_state.get(sha))
        for sha in doc["review_order"]
        if _label_value(labels, sha, "photography") == "unsuitable" and rule_state.get(sha) == "candidate"]
    return {
        "liked_count": len(liked),
        "disliked_count": len(disliked),
        "liked_pushed_down_by_candidate2_vs_rule": pushed_vs_rule,
        "liked_pushed_down_by_candidate2_vs_arrival": pushed_vs_arrival,
        "disliked_pulled_up_by_candidate2_vs_rule": pulled_up,
        "disliked_in_top5": disliked_early,
        "liked_outside_top5": liked_late,
        "rule_vs_aesthetic": {
            "rule_candidate_but_dislike": rule_candidate_but_dislike,
            "rule_not_candidate_but_like": rule_not_candidate_but_like,
            "identity_confirmed_but_rule_needs_evidence": identity_confirmed_but_rule_needs_evidence,
            "identity_wrong_but_rule_candidate": identity_wrong_but_rule_candidate,
            "photography_useful_but_rule_not_candidate": photography_useful_but_rule_not_candidate,
            "photography_unsuitable_but_rule_candidate": photography_unsuitable_but_rule_candidate,
        },
    }


def compute_metrics(doc: dict, labels: dict, *, labels_source: str = "LABELS_FILE", mode: str = "post_submit") -> dict:
    scores, missing_reasons = score_map(doc, labels)
    scorable = [asset for asset in doc["assets"] if asset["scorable"]]
    rated = [asset["asset_sha"] for asset in scorable if scores[asset["asset_sha"]] is not None]
    uncertain = [asset["asset_sha"] for asset in scorable
                 if _label_value(labels, asset["asset_sha"], "aesthetic") == "uncertain"]
    skipped = [asset["asset_sha"] for asset in scorable
               if (labels.get("assets", {}).get(asset["asset_sha"], {}) or {}).get("skipped")
               and scores[asset["asset_sha"]] is None]
    missing = [asset["asset_sha"] for asset in scorable if scores[asset["asset_sha"]] is None]
    methods = {method: method_metrics(doc, labels, scores, method) for method in METHODS}
    differences = ranking_differences(doc)
    cases = review_cases(doc, labels, scores)
    submitted = labels.get("status") == "submitted"
    if not submitted or not rated:
        outcome_status = "NO_HUMAN_LABELS"
    elif any(value["ndcg_status"] != "SCORED" for value in methods.values()):
        outcome_status = "INCOMPLETE_LABELS"
    else:
        outcome_status = "SCORED"
    candidate = methods["candidate2"]["ndcg_at_5"]
    baseline0 = methods["baseline0"]["ndcg_at_5"]
    baseline1 = methods["baseline1"]["ndcg_at_5"]
    improvement: bool | None = None
    if outcome_status == "SCORED" and None not in (candidate, baseline0, baseline1):
        improvement = candidate > max(baseline0, baseline1)
    return {
        "at": stamp(),
        "protocol": PROTOCOL_VERSION,
        "experiment_id": EXPERIMENT_ID,
        "mode": mode,
        "labels_source": labels_source,
        "labels_status": labels.get("status"),
        "submitted": submitted,
        "labels_sha256": sha256_bytes(json_bytes(labels)),
        "experiment_inputs": doc["inputs"],
        "method_labels": METHOD_LABELS,
        "coverage": {
            "assets_total": len(doc["assets"]),
            "scorable_total": len(scorable),
            "excluded_total": len(doc["assets"]) - len(scorable),
            "excluded": [{"asset_sha": asset["asset_sha"], "review_id": asset["review_id"],
                          "reason": asset["unscorable_reason"]} for asset in doc["assets"] if not asset["scorable"]],
            "aesthetic_rated": len(rated),
            "aesthetic_missing": len(missing),
            "missing_breakdown": {
                "unrated": sum(missing_reasons[sha] == "未评价" for sha in missing),
                "uncertain": len(uncertain),
                "skipped": len(skipped),
                "saved_without_aesthetic": sum(missing_reasons[sha] == "已保存但未选审美维度" for sha in missing),
                "unscorable": sum(missing_reasons[sha].startswith("不可计分") for sha in missing),
            },
            "rated_shas": rated,
            "missing_shas": missing,
        },
        "methods": methods,
        "ranking_difference": differences,
        "cases": cases,
        "outcome": {
            "status": outcome_status,
            "conclusion": "NOT_PROVEN",
            "prior_conclusion": "NOT_PROVEN",
            "prior_conclusion_changed": False,
            "candidate2_exceeds_both_baselines": improvement,
            "candidate2_no_improvement": (None if improvement is None else not improvement),
            "no_top5_improvement": differences["candidate2_vs_baseline1_top5_identical"],
            "reason": (
                "尚无人完成逐图评价：不计算准确率，不以 AI、旧 K/X 或空值代替人工真值。"
                if outcome_status == "NO_HUMAN_LABELS" else
                "人工标签不完整：缺失标签未按 0 分处理，NDCG@5 显示 N/A。"
                if outcome_status == "INCOMPLETE_LABELS" else
                "单固定候选池上的观测；不足以证明可泛化的审美收益。"
            ),
        },
    }


# ---------------------------------------------------------------------------
# HTML rendering. The review page deliberately omits strategy names, model
# scores, rule states and ranking suggestions.

REVIEW_STYLE = STYLE + """
.review-wrap{display:grid;grid-template-columns:minmax(0,1.15fr) minmax(340px,.85fr);gap:26px;align-items:start}
.review-figure{position:sticky;top:16px}
.review-figure img{height:min(66vh,640px);object-fit:contain;background:#e9e7e3}
.review-figure figcaption{padding:14px 16px}
.review-form{background:#fff;border:1px solid #ddd8d0;border-radius:8px;padding:18px 20px}
fieldset{border:0;border-top:1px solid #e6e1da;margin:0;padding:16px 0 6px}
fieldset:first-of-type{border-top:0;padding-top:0}
legend{font-weight:700;font-size:17px;padding:0}
.hint{margin:2px 0 10px;color:#606b72;font-size:13px}
.choices{display:grid;gap:8px}
.choice{display:flex;gap:10px;align-items:flex-start;border:1px solid #ddd8d0;border-radius:6px;padding:9px 11px;cursor:pointer;background:#fbfaf8}
.choice:hover{border-color:#8ba6ae}
.choice input{margin-top:3px;flex:0 0 auto}
.choice:has(input:checked){border-color:#42636d;background:#eef4f4}
.reason-label{display:block;margin:16px 0 6px;font-weight:700}
#reason{width:100%;border:1px solid #cfc9c0;border-radius:6px;padding:9px;font:15px/1.6 inherit;resize:vertical;background:#fff}
.nav-row{display:flex;gap:10px;flex-wrap:wrap;margin:18px 0 6px}
button{font:15px/1.4 inherit;padding:9px 15px;border:1px solid #42636d;border-radius:6px;background:#fff;color:#24424c;cursor:pointer}
button:hover:not(:disabled){background:#eef4f4}
button:disabled{opacity:.45;cursor:not-allowed}
button.primary{background:#42636d;color:#fff;border-color:#42636d}
button.primary:hover:not(:disabled){background:#31525c}
.progress{background:#fff;border:1px solid #ddd8d0;border-radius:8px;padding:10px 14px;margin:18px 0;font-size:14px}
.progress b{font-size:16px}
.banner{border-left:4px solid #a8702a;background:#fff8ec;padding:12px 16px;margin:16px 0;border-radius:4px}
.banner:empty{display:none}
.badge{display:inline-block;background:#ffe9e5;color:#8a2f1d;border-radius:4px;padding:1px 7px;font-size:12px;margin-left:6px}
.unscorable{background:#fff1ee;border-left:3px solid #b4452d;padding:8px 11px;margin:8px 0;font-size:13px}
.after{margin-top:28px;color:#4b565c}
#done{background:#eef5ee;border-left:4px solid #3f6b45;padding:18px 22px;margin:20px 0}
#done a{font-weight:700}
.review-meta{font-size:14px;color:#5a666d}
.top5{display:grid;grid-template-columns:repeat(auto-fit,minmax(180px,1fr));gap:14px;margin:14px 0 26px}
.top5 article{background:#fff;border:1px solid #ddd8d0;border-radius:8px;overflow:hidden}
.top5 img{display:block;width:100%;height:190px;object-fit:contain;background:#e9e7e3}
.top5 .body{padding:10px 12px;font-size:13px;line-height:1.6}
.chip{display:inline-block;border-radius:999px;padding:1px 8px;font-size:12px;margin:2px 4px 2px 0;background:#ece9e3}
.chip.like{background:#dcecdf;color:#28572f}.chip.dislike{background:#f6ddd8;color:#7a2d1e}
.chip.uncertain{background:#eee8d8;color:#665c39}
.report-table td,.report-table th{vertical-align:top}
.report-note{max-width:90ch}
.analysis li{margin:5px 0;max-width:90ch}
@media(max-width:820px){.review-wrap{grid-template-columns:1fr}.review-figure{position:static}.review-figure img{height:48vh;min-height:240px}}
@media(max-width:600px){.review-form{padding:13px 12px}.nav-row{display:grid;grid-template-columns:1fr 1fr;gap:8px}.nav-row button{width:100%}.top5 img{height:150px}}
"""

REVIEW_JS = r"""
(function () {
  'use strict';
  var BOOT = window.__BOOT__ || {assets: [], choices: {}, protocol: ''};
  var TOKEN = window.__TOKEN__ || '';
  var isHttp = location.protocol === 'http:' || location.protocol === 'https:';
  var hasServer = isHttp && TOKEN.length > 20;
  var LOCAL_KEY = 'ruby-human-review-draft-v1';
  var state = null;
  var index = 0;
  var submitted = false;
  var saveTimer = null;
  var recovery = [];

  function $(id) { return document.getElementById(id); }
  function emptyLabels() { return {identity: null, photography: null, aesthetic: null}; }
  function hasAny(labels) {
    labels = labels || {};
    return !!(labels.identity || labels.photography || labels.aesthetic);
  }
  function entryDirty(asset) {
    return !!(asset && (hasAny(asset.labels) || (asset.reason || '').trim() || asset.skipped));
  }
  function normalize(asset) {
    asset.labels = Object.assign(emptyLabels(), asset.labels || {});
    asset.reason = asset.reason || '';
    asset.skipped = !!asset.skipped;
    asset.status = asset.status || (hasAny(asset.labels) ? 'rated' : 'unrated');
    return asset;
  }
  function banner(text) {
    var node = $('banner');
    if (!text) { node.hidden = true; node.textContent = ''; return; }
    node.hidden = false; node.textContent = text;
  }
  function current() { return state.assets[index]; }
  function formatTime(value) {
    if (!value) { return ''; }
    try { return new Date(value).toLocaleTimeString('zh-CN', {hour: '2-digit', minute: '2-digit'}); }
    catch (e) { return ''; }
  }
  function setStatus(text) { $('save-status').textContent = text; }

  function updateProgress() {
    var rated = 0, skipped = 0;
    state.assets.forEach(function (asset) {
      if (hasAny(asset.labels)) { rated += 1; }
      else if (asset.skipped) { skipped += 1; }
    });
    var total = state.assets.length;
    var unrated = total - rated - skipped;
    $('progress-text').textContent = '已填写 ' + rated + ' / ' + total + ' 张 · 跳过 ' + skipped + ' · 未处理 ' + unrated;
  }

  function choiceList(kind) {
    return BOOT.choices[kind] || {};
  }

  function renderChoices(kind, asset) {
    var host = $(kind + '-choices');
    host.textContent = '';
    Object.keys(choiceList(kind)).forEach(function (value, i) {
      var id = kind + '-' + value;
      var label = document.createElement('label');
      label.className = 'choice';
      label.htmlFor = id;
      var input = document.createElement('input');
      input.type = 'radio';
      input.name = kind;
      input.value = value;
      input.id = id;
      input.checked = asset.labels[kind] === value;
      input.disabled = submitted;
      input.addEventListener('change', function () {
        asset.labels[kind] = value;
        asset.skipped = false;
        asset.status = 'rated';
        setStatus('待保存…');
        updateProgress();
        scheduleSave(asset);
      });
      var span = document.createElement('span');
      span.textContent = choiceList(kind)[value];
      label.appendChild(input);
      label.appendChild(span);
      host.appendChild(label);
    });
  }

  function render() {
    if (!state || !state.assets.length) { return; }
    var asset = current();
    var image = $('photo');
    image.src = asset.image_file;
    image.alt = asset.review_id + ' 原始图片';
    $('photo-link').href = asset.image_file;
    $('review-id').textContent = asset.review_id;
    $('dims').textContent = (asset.width && asset.height) ? (asset.width + ' × ' + asset.height) : '';
    var source = asset.source || {};
    $('source-link').href = source.page_url || '#';
    $('source-link').style.display = source.page_url ? '' : 'none';
    var host = '';
    if (source.page_url) { try { host = new URL(source.page_url).host; } catch (e) { host = ''; } }
    $('source-host').textContent = host || '来源未记录';
    $('position').textContent = '第 ' + (index + 1) + ' / ' + state.assets.length + ' 张';
    $('reason').value = asset.reason || '';
    var notice = $('unscorable-notice');
    if (asset.scorable === false) {
      notice.hidden = false;
      notice.textContent = '此图已被标记为不可计分（' + (asset.unscorable_reason || '来源/重合问题') +
        '）。仍可记录你的看法，但不会进入排序指标。';
    } else {
      notice.hidden = true; notice.textContent = '';
    }
    renderChoices('identity', asset);
    renderChoices('photography', asset);
    renderChoices('aesthetic', asset);
    $('prev').disabled = index === 0;
    $('next').disabled = index === state.assets.length - 1;
    $('skip').disabled = submitted;
    $('submit').disabled = submitted;
    $('reason').disabled = submitted;
    setStatus(submitted ? '最终评价已提交（只读）' : (asset.saved_at ? '已保存 ' + formatTime(asset.saved_at) : '尚未保存'));
    updateProgress();
    if (submitted) { showSubmitted(); }
  }

  function go(delta) {
    if (!state) { return; }
    var next = index + delta;
    if (next < 0 || next >= state.assets.length) { return; }
    index = next;
    render();
    window.scrollTo({top: 0, behavior: 'smooth'});
  }

  function saveLocal() {
    try {
      var assets = {};
      state.assets.forEach(function (asset) {
        assets[asset.asset_sha] = {labels: asset.labels, reason: asset.reason,
                                   skipped: asset.skipped, saved_at: asset.saved_at};
      });
      localStorage.setItem(LOCAL_KEY, JSON.stringify({protocol: BOOT.protocol, at: new Date().toISOString(), assets: assets}));
    } catch (e) { /* private mode or disabled storage */ }
  }

  function postDraft(asset) {
    if (!entryDirty(asset)) { setStatus(submitted ? '最终评价已提交（只读）' : '尚未保存'); return; }
    if (!hasServer) { saveLocal(); setStatus('本地草稿已保存（未连接评价服务）'); return; }
    if (submitted) { return; }
    fetch('/api/draft', {
      method: 'POST',
      headers: {'Content-Type': 'application/json', 'X-Review-Token': TOKEN},
      body: JSON.stringify({asset_sha: asset.asset_sha, labels: asset.labels,
                            reason: asset.reason, skipped: !!asset.skipped})
    }).then(function (response) {
      if (!response.ok) { throw new Error('HTTP ' + response.status); }
      return response.json();
    }).then(function (data) {
      asset.saved_at = data.saved_at;
      asset.status = data.status;
      setStatus('已保存 ' + formatTime(data.saved_at));
      saveLocal();
    }).catch(function (error) {
      setStatus('保存失败：' + error.message + '（已保留本地草稿）');
      saveLocal();
    });
  }

  function scheduleSave(asset) {
    if (saveTimer) { clearTimeout(saveTimer); }
    saveTimer = setTimeout(function () { postDraft(asset); }, 250);
  }

  function applyLocalRecovery() {
    if (!hasServer || submitted) { return; }
    var raw;
    try { raw = JSON.parse(localStorage.getItem(LOCAL_KEY) || 'null'); } catch (e) { return; }
    if (!raw || !raw.assets) { return; }
    state.assets.forEach(function (asset) {
      var local = raw.assets[asset.asset_sha];
      if (local && (hasAny(local.labels) || local.skipped) && !hasAny(asset.labels) && !asset.skipped) {
        asset.labels = Object.assign(emptyLabels(), local.labels || {});
        asset.reason = local.reason || '';
        asset.skipped = !!local.skipped;
        asset.status = asset.skipped ? 'skipped' : 'rated';
        recovery.push(asset);
      }
    });
    if (recovery.length) {
      banner('已从本机浏览器草稿恢复 ' + recovery.length + ' 张未提交评价。');
      recovery.forEach(function (asset) { postDraft(asset); });
    }
  }

  function showSubmitted() {
    var done = $('done');
    done.hidden = false;
    done.innerHTML = '<p><strong>最终评价已提交，并保存为独立只读快照。</strong></p>' +
      '<p><a href="ruby-human-report.html">查看三种冻结排序的对照报告</a></p>' +
      '<p class="muted">本页现在只读。报告只使用你填写的标签；缺失标签显示 N/A，不以 AI 或旧项目选择代填。</p>';
    document.querySelectorAll('input,textarea,button').forEach(function (node) { node.disabled = true; });
    document.querySelectorAll('a').forEach(function (node) { node.style.pointerEvents = ''; });
  }

  function loadState() {
    if (hasServer) {
      fetch('/api/state', {headers: {'X-Review-Token': TOKEN}, cache: 'no-store'}).then(function (response) {
        if (!response.ok) { throw new Error('HTTP ' + response.status); }
        return response.json();
      }).then(function (data) {
        state = data;
        submitted = !!data.submitted;
        state.assets.forEach(normalize);
        applyLocalRecovery();
        if (!submitted) {
          var next = state.assets.findIndex(function (asset) { return !hasAny(asset.labels) && !asset.skipped; });
          index = next >= 0 ? next : 0;
        }
        render();
      }).catch(function (error) {
        offlineState('无法连接本地评价服务（' + error.message + '），当前只能预览。');
      });
    } else {
      offlineState('当前是通过文件直接打开：可以浏览，但保存与提交需要本地评价服务。');
    }
  }

  function offlineState(message) {
    state = {assets: (BOOT.assets || []).map(normalize), submitted: false, protocol: BOOT.protocol};
    submitted = false;
    index = 0;
    banner(message + ' 请在仓库运行 python -B -X utf8 -m tools.learning_v1_human serve 后再打开 http://127.0.0.1 地址。');
    render();
  }

  function submitReview() {
    if (!hasServer) { banner('提交需要本地评价服务。'); return; }
    var rated = 0, skipped = 0;
    state.assets.forEach(function (asset) {
      if (hasAny(asset.labels)) { rated += 1; } else if (asset.skipped) { skipped += 1; }
    });
    var message = '提交后不能修改。\n已填写 ' + rated + ' / ' + state.assets.length + ' 张，跳过 ' + skipped + ' 张。\n确定提交吗？';
    if (!window.confirm(message)) { return; }
    $('submit').disabled = true;
    setStatus('提交中…');
    fetch('/api/submit', {method: 'POST', headers: {'X-Review-Token': TOKEN}}).then(function (response) {
      if (!response.ok) {
        return response.text().then(function (text) { throw new Error(text || ('HTTP ' + response.status)); });
      }
      return response.json();
    }).then(function () {
      submitted = true;
      state.submitted = true;
      state.status = 'submitted';
      render();
      setStatus('最终评价已提交（只读）');
      banner('');
      window.scrollTo({top: 0, behavior: 'smooth'});
    }).catch(function (error) {
      $('submit').disabled = false;
      setStatus('提交失败：' + error.message);
    });
  }

  function bind() {
    $('prev').addEventListener('click', function () { go(-1); });
    $('next').addEventListener('click', function () { go(1); });
    $('skip').addEventListener('click', function () {
      if (submitted) { return; }
      var asset = current();
      if (!hasAny(asset.labels)) {
        asset.skipped = true;
        asset.status = 'skipped';
        postDraft(asset);
      }
      updateProgress();
      go(1);
    });
    $('reason').addEventListener('input', function () {
      if (submitted) { return; }
      var asset = current();
      asset.reason = $('reason').value.slice(0, 300);
      setStatus('待保存…');
      scheduleSave(asset);
    });
    $('submit').addEventListener('click', submitReview);
    document.addEventListener('keydown', function (event) {
      if (event.target && /^(INPUT|TEXTAREA|SELECT)$/.test(event.target.tagName)) { return; }
      if (event.key === 'ArrowLeft') { event.preventDefault(); go(-1); }
      if (event.key === 'ArrowRight') { event.preventDefault(); go(1); }
    });
    document.addEventListener('visibilitychange', function () {
      if (document.visibilityState === 'hidden' && state && !submitted) {
        var asset = current();
        if (entryDirty(asset)) { postDraft(asset); }
      }
    });
  }

  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', function () { bind(); loadState(); });
  } else {
    bind(); loadState();
  }
})();
"""

REVIEW_BODY = """
<a href="index.html">返回实验总览</a>
<small>PRIVATE LOCAL REVIEW · SINGLE IMAGE</small>
<h1>星野露比 · 逐图人工评价</h1>
<div class="lead">
<p>一次只看一张。每张原图只评价一次；角色准确性、摄影参考价值、个人审美分别判断。</p>
<p>没有标准答案，可以跳过，也可以只填一部分。所有选择只写入本机私有实验目录，不上传，不会修改正式图库的 K/I/M/X。</p>
</div>
<div id="banner" class="banner" hidden></div>
<div class="progress"><span id="progress-text">正在载入…</span></div>
<div class="review-wrap">
<section class="review-visual">
<figure class="review-figure">
<a id="photo-link" href="#" target="_blank" rel="noopener noreferrer"><img id="photo" alt="原始图片" loading="eager"></a>
<figcaption>
<strong id="review-id">—</strong> <span id="dims" class="muted"></span>
<p class="review-meta"><a id="source-link" href="#" target="_blank" rel="noopener noreferrer">原发布页</a> · <span id="source-host"></span></p>
<p class="review-meta" id="position"></p>
<p class="muted">点击图片可查看原图大图。来源只作追溯，不代表已验证拍摄组独立。</p>
</figcaption>
</figure>
</section>
<section class="review-form" aria-label="评价表单">
<div id="unscorable-notice" class="unscorable" hidden></div>
<fieldset>
<legend>A. 角色准确性</legend>
<p class="hint">只判断这张图是否是目标角色的真人 Cosplay，不评价好不好看。</p>
<div class="choices" id="identity-choices"></div>
</fieldset>
<fieldset>
<legend>B. 摄影参考价值</legend>
<p class="hint">动作、构图、光线、场景等是否有实际借鉴价值；与角色是否正确无关。</p>
<div class="choices" id="photography-choices"></div>
</fieldset>
<fieldset>
<legend>C. 个人审美</legend>
<p class="hint">只表示你个人是否喜欢。项目 K 不等于喜欢，项目 X 也不等于审美负例。</p>
<div class="choices" id="aesthetic-choices"></div>
</fieldset>
<label class="reason-label" for="reason">可选原因（一句话即可，不强制）</label>
<textarea id="reason" maxlength="300" rows="2" placeholder="例如：逆光轮廓好看，但动作太僵"></textarea>
<div class="nav-row">
<button id="prev" type="button">上一张</button>
<button id="skip" type="button">跳过这张</button>
<button id="next" type="button">下一张</button>
</div>
<p class="muted" id="save-status" aria-live="polite">尚未保存</p>
<div class="submit-row">
<button id="submit" type="button" class="primary">提交最终评价</button>
<span class="muted">提交后生成只读快照，不能再修改。</span>
</div>
</section>
</div>
<div id="done" class="lead" hidden></div>
<details class="after">
<summary>评价协议与数据边界</summary>
<p>协议 <code>ruby-single-image-review-v1</code>。评价按原图 SHA 绑定；同一 SHA 只展示、只计入一次。跳过是缺失标签，不是“不喜欢”。提交后的快照只读。排序与指标只使用先前冻结的三种方法，不会因为你本轮的评价重新排序或重新训练。缺失标签不会被自动当成 0 分。</p>
</details>
<noscript><p class="banner">此评价页需要 JavaScript 才能保存你的选择；但仍可查看图片。</p></noscript>
"""


def review_document(boot: dict) -> str:
    data = json.dumps(boot, ensure_ascii=False).replace("</", "<\\/")
    return ("<!doctype html><html lang=\"zh-CN\"><head><meta charset=\"utf-8\">"
            "<meta name=\"viewport\" content=\"width=device-width, initial-scale=1\">"
            "<meta http-equiv=\"Content-Security-Policy\" content=\"default-src 'none'; "
            "img-src 'self' file: data:; style-src 'unsafe-inline'; script-src 'unsafe-inline'; "
            "connect-src 'self'; form-action 'none'; base-uri 'none'\">"
            "<link rel=\"icon\" href=\"data:,\">"
            "<title>星野露比逐图人工评价</title>"
            f"<style>{REVIEW_STYLE}</style></head><body><main>{REVIEW_BODY}</main>"
            f"<script>window.__BOOT__={data};window.__TOKEN__=\"__REVIEW_TOKEN__\";</script>"
            f"<script>{REVIEW_JS}</script></body></html>")


def write_review_page(doc: dict) -> None:
    boot = {
        "protocol": PROTOCOL_VERSION,
        "experiment_id": EXPERIMENT_ID,
        "choices": CHOICES,
        "assets": [public_asset(asset) for asset in doc["assets"]],
        "independence": doc["independence"],
    }
    atomic_write(Path(doc["experiment"]) / REVIEW_PAGE, review_document(boot).encode("utf-8"))


# ---------------------------------------------------------------------------
# Report rendering

def fmt_metric(value: int | float | None, rated: int, *, digits: int = 0) -> str:
    if value is None:
        return "N/A"
    if digits:
        return f"{value:.{digits}f}（覆盖 {rated}/5）"
    return f"{value}/5（覆盖 {rated}/5）"


def chip(value: str | None, dimension: str) -> str:
    labels = CHOICES[dimension]
    text = labels.get(value, "未评价") if value else "未评价"
    css = "uncertain" if value in {None, "uncertain"} else ("like" if value in {"like", "useful", "target_cosplay"}
                                                           else "dislike" if value in {"dislike", "unsuitable", "not_target"} else "")
    return f'<span class="chip {css}">{escape(text)}</span>'


def top5_block(metrics: dict) -> str:
    cards = []
    for item in metrics["top5"]:
        image = item["image_file"]
        cards.append(
            f'<article><a href="{escape(image)}" target="_blank" rel="noopener noreferrer">'
            f'<img src="{escape(image)}" alt="{escape(item["review_id"])} 缩略图" loading="lazy"></a>'
            f'<div class="body"><strong>{escape(item["review_id"])}</strong> <small>原图 #{item["rank"]}</small>'
            f'<div>{chip(item["aesthetic"], "aesthetic")}</div>'
            f'<div>{chip(item["identity"], "identity")}</div>'
            f'<div>{chip(item["photography"], "photography")}</div>'
            + (f'<div class="muted">“{escape(item["reason"])}”</div>' if item.get("reason") else "")
            + '</div></article>')
    return '<div class="top5">' + ''.join(cards) + '</div>'


def case_list(rows: list[dict], formatter, empty: str = "无") -> str:
    if not rows:
        return f'<li class="muted">{escape(empty)}</li>'
    return ''.join(f'<li>{formatter(row)}</li>' for row in rows)


def report_html(doc: dict, metrics: dict, labels: dict) -> str:
    coverage = metrics["coverage"]
    outcome = metrics["outcome"]
    differences = metrics["ranking_difference"]
    cases = metrics["cases"]
    no_labels = outcome["status"] == "NO_HUMAN_LABELS"
    lead = ('<div class="lead"><p><strong>尚无人完成逐图评价，因此没有可计算的人工准确率。</strong></p>'
            '<p>本页只展示冻结排序与标签缺口；所有指标为 N/A，不以 AI 观察、旧 K/X 或空值代填。</p></div>'
            if no_labels else
            '<div class="lead"><p><strong>结论仍为 NOT_PROVEN。</strong>本页只对照冻结的三种排序，'
            '不因本轮评价重新排序、调参或训练。</p></div>')
    rows = []
    identity_rows = []
    for method in METHODS:
        value = metrics["methods"][method]
        rows.append(
            f'<tr><td><strong>{escape(value["label"])}</strong><br><small>{escape(method)}</small></td>'
            f'<td>{fmt_metric(value["top5_like"], value["top5_rated"])}</td>'
            f'<td>{fmt_metric(value["ndcg_at_5"], value["top5_rated"], digits=3)}</td>'
            f'<td>{fmt_metric(value["photography_useful"], value["photography_rated"])}</td></tr>')
        identity_rated = value["identity_rated"]
        photography_rated = value["photography_rated"]
        confirmed = value["identity_confirmed"]
        wrong = None if not identity_rated else value["identity_wrong"]
        uncertain = None if not identity_rated else value["identity_uncertain"]
        photo_useful_count = value["photography_useful"]
        photo_uncertain = None if not photography_rated else value["photography_uncertain"]
        identity_rows.append(
            f'<tr><td><strong>{escape(value["label"])}</strong></td>'
            f'<td>{fmt_metric(confirmed, identity_rated)}</td>'
            f'<td>{fmt_metric(wrong, identity_rated)}</td>'
            f'<td>{fmt_metric(uncertain, identity_rated)}</td>'
            f'<td>{fmt_metric(photo_useful_count, photography_rated)}</td>'
            f'<td>{fmt_metric(photo_uncertain, photography_rated)}</td></tr>')

    top_sections = []
    for letter, method in zip(("A", "B", "C"), METHODS):
        value = metrics["methods"][method]
        top_sections.append(f'<h3>{letter}. {escape(value["label"])} Top-5</h3>')
        if value["ndcg_status"] != "SCORED":
            top_sections.append(f'<p class="muted">NDCG@5 为 N/A：Top-5 中有 {value["top5_missing"]} 张缺少审美标签。</p>')
        top_sections.append(top5_block(value))

    if no_labels:
        top5_verdict = ('<p>无论三种排序差异如何，当前没有用户前五张的审美真值，不能声称改善或退步。</p>')
    elif differences["candidate2_vs_baseline1_top5_identical"]:
        top5_verdict = ('<p><strong>本次对用户前五张结果没有改善。</strong>'
                        '规则排序与正例相似排序的前五张是同一组图片'
                        + ('，只是组内顺序不同。' if not differences["candidate2_vs_baseline1_order_identical"] else '，顺序也相同。')
                        + '</p>')
    else:
        top5_verdict = ('<p>正例相似排序与规则排序的前五张不是同一组；是否更符合你的审美见上表，'
                        '但不能据此宣称可泛化收益。</p>')

    empty_text = "尚无人工作答，无法判断" if no_labels else "已评价样本中无"
    pushed = case_list(cases["liked_pushed_down_by_candidate2_vs_rule"],
                       lambda row: f'{escape(row["review_id"])}：规则排序第 {row["baseline1_rank"]} → 正例相似第 {row["candidate2_rank"]}',
                       empty_text)
    pulled = case_list(cases["disliked_pulled_up_by_candidate2_vs_rule"],
                       lambda row: f'{escape(row["review_id"])}：规则排序第 {row["baseline1_rank"]} → 正例相似第 {row["candidate2_rank"]}',
                       empty_text)
    disliked = {method: case_list(cases["disliked_in_top5"][method],
                                  lambda row: f'{escape(row["review_id"])}（第 {row["rank"]}）', empty_text)
                for method in METHODS}
    rule_cases = cases["rule_vs_aesthetic"]
    rule_candidate_dislike = case_list(rule_cases["rule_candidate_but_dislike"],
                                       lambda row: f'{escape(row["review_id"])}：规则判为候选，你标记不喜欢', empty_text)
    rule_reject_like = case_list(rule_cases["rule_not_candidate_but_like"],
                                 lambda row: f'{escape(row["review_id"])}：规则未判为候选，你标记喜欢', empty_text)
    identity_gap = case_list(rule_cases["identity_confirmed_but_rule_needs_evidence"],
                             lambda row: f'{escape(row["review_id"])}：你确认角色，规则仍缺证据（{escape(row.get("rule_state"))}）',
                             empty_text)
    identity_wrong = case_list(rule_cases["identity_wrong_but_rule_candidate"],
                               lambda row: f'{escape(row["review_id"])}：你判断不是目标角色，规则仍判为候选', empty_text)
    photo_useful = case_list(rule_cases["photography_useful_but_rule_not_candidate"],
                             lambda row: f'{escape(row["review_id"])}：你认为摄影可用，规则未判为候选', empty_text)
    photo_unsuitable = case_list(rule_cases["photography_unsuitable_but_rule_candidate"],
                                 lambda row: f'{escape(row["review_id"])}：你认为不适合，规则仍判为候选', empty_text)

    pair_lines = []
    for pair, value in differences["pairs"].items():
        left, right = pair.split("__")
        if value["same_order"]:
            state = "完整排序完全相同"
        elif value["same_top5_set"]:
            state = "前五张集合相同，仅组内顺序不同"
        else:
            state = f'前五张变化：进入 {len(value["entered_top5"])} 张，退出 {len(value["left_top5"])} 张'
        pair_lines.append(f'<li>{escape(left)} ↔ {escape(right)}：{escape(state)}</li>')
    no_difference = ('<p><strong>NO_RANKING_DIFFERENCE</strong>：三种冻结排序实际完全相同，'
                     '因此任何指标差异都不可能来自排序。</p>'
                     if differences["no_ranking_difference"] else
                     '<p><strong>NO_RANKING_DIFFERENCE</strong>：规则排序与正例相似排序的完整顺序完全相同；'
                     '两者之间不可能产生指标差异。</p>'
                     if differences.get("candidate2_vs_baseline1_ranking_identical") else
                     '<p class="muted">三种冻结排序并非完全相同；逐对差异见上。</p>')

    excluded = coverage["excluded"]
    excluded_html = ('<li class="muted">无</li>' if not excluded else ''.join(
        f'<li>{escape(row["review_id"])}：{escape(row["reason"])}</li>' for row in excluded))
    independence = doc["independence"]
    dedupe_note = ('<li class="muted">输入池没有重复 SHA。</li>' if not doc["duplicates"] else ''.join(
        f'<li>重复 SHA 已去重：{escape(row["asset_sha"][:12])}… 只保留一张。</li>' for row in doc["duplicates"]))
    near_note = ('<li class="muted">未检测到 dHash 距离 ≤ 5 的近似重复对。</li>' if not independence["near_duplicate_pairs"]
                 else ''.join(f'<li>近似重复：{escape(row["left"][:12])}… 与 {escape(row["right"][:12])}…（距离 {row["distance"]}）</li>'
                              for row in independence["near_duplicate_pairs"]))

    conclusion_reason = outcome["reason"]
    if outcome["status"] == "SCORED":
        if outcome["candidate2_no_improvement"]:
            conclusion_reason += " 正例相似排序没有同时超过原始顺序和规则排序，NOT_PROVEN 保持不变。"
        else:
            conclusion_reason += (" 正例相似排序在本池的 NDCG@5 高于两个基线，但样本只有一个固定候选池，"
                                  "仍不足以证明可泛化收益，NOT_PROVEN 保持不变。")

    prediction_by_sha = {record["asset_sha"]: record for record in doc["predictions"]["baseline1"]}
    ai_rows = []
    for asset in doc["assets"]:
        record = prediction_by_sha.get(asset["asset_sha"], {})
        visual = record.get("visual") or {}
        evidence = "；".join(visual.get("evidence") or [])
        ai_rows.append(
            f'<li>{escape(asset["review_id"])}：类型 {escape(str(visual.get("kind") or "unknown"))} · '
            f'身份 {escape(str(visual.get("identity") or "unknown"))} · 服装 {escape(str(visual.get("costume") or "unknown"))}'
            + (f' · {escape(evidence)}' if evidence else '') + '</li>')


    body = f'''
<a href="ruby-human-review.html">返回逐图评价</a> · <a href="index.html">实验总览</a>
<small>PHOTOGRAPHY REFERENCE LAB / RUBY HUMAN REVIEW</small>
<h1>星野露比 · 逐图评价与冻结排序对照</h1>
{lead}
<p class="muted">协议 {escape(metrics["protocol"])} · 实验 {escape(metrics["experiment_id"])} ·
标签来源 {escape(metrics["labels_source"])} · 状态 {escape(str(metrics["labels_status"]))} · 生成于 {escape(metrics["at"])}</p>
<h2>结果表</h2>
<table class="report-table"><thead><tr><th>方法</th><th>Top-5 喜欢数量</th><th>NDCG@5</th><th>摄影可用数</th></tr></thead>
<tbody>{''.join(rows)}</tbody></table>
<p class="muted">NDCG@5 使用人工审美分级（喜欢=2、一般=1、不喜欢=0；增益 2^rel−1，折损 log2(rank+1)）；Top-5 中只要有一张缺少审美标签就显示 N/A，不把未知当 0。覆盖：已评价 {coverage["aesthetic_rated"]} / {coverage["scorable_total"]} 张可计分图片；缺失 {coverage["aesthetic_missing"]} 张（未评价 {coverage["missing_breakdown"]["unrated"]}、无法评价 {coverage["missing_breakdown"]["uncertain"]}、跳过 {coverage["missing_breakdown"]["skipped"]}）。</p>

<h2>角色及摄影适用性（Top-5）</h2>
<table class="report-table"><thead><tr><th>方法</th><th>角色确认</th><th>角色错误</th><th>角色未确定</th><th>摄影可用</th><th>摄影不确定</th></tr></thead>
<tbody>{''.join(identity_rows)}</tbody></table>
<p class="muted">角色与摄影是两套独立判断：角色确认不等于摄影有用，摄影有用也不等于个人喜欢。数字后的“覆盖”表示 Top-5 中已填写该维度的数量；未填写不会自动成为“错误”或“不适合”。</p>

<h2>三个 Top-5</h2>
{''.join(top_sections)}
{top5_verdict}

<h2>排序变化是否影响前五张</h2>
<ul class="analysis">{''.join(pair_lines)}</ul>
{no_difference}

<h2>喜欢的图片是否被排到后面</h2>
<p>相对规则排序，正例相似排序把以下明确喜欢的图片排到第 5 名之后：</p>
<ul class="analysis">{pushed}</ul>
<p>相对原始入库顺序：</p>
<ul class="analysis">{case_list(cases["liked_pushed_down_by_candidate2_vs_arrival"], lambda row: f'{escape(row["review_id"])}：原始第 {row["baseline0_rank"]} → 正例相似第 {row["candidate2_rank"]}', empty_text)}</ul>

<h2>不喜欢的图片是否被错误提前</h2>
<p>正例相似排序把以下明确不喜欢的图片从规则排序的第 5 名之后提到前五：</p>
<ul class="analysis">{pulled}</ul>
<p>各方法前五中的明确不喜欢图片：</p>
<ul class="analysis">
<li>原始入库顺序：<ul>{disliked["baseline0"]}</ul></li>
<li>规则排序：<ul>{disliked["baseline1"]}</ul></li>
<li>正例相似排序：<ul>{disliked["candidate2"]}</ul></li>
</ul>

<h2>规则判断与个人审美在哪里不一致</h2>
<ul class="analysis">
<li>规则判为候选、但你标记不喜欢：<ul>{rule_candidate_dislike}</ul></li>
<li>规则未判为候选、但你标记喜欢：<ul>{rule_reject_like}</ul></li>
<li>你确认角色、规则仍缺证据：<ul>{identity_gap}</ul></li>
<li>你判断不是目标角色、规则仍判为候选：<ul>{identity_wrong}</ul></li>
<li>你认为摄影可用、规则未判为候选：<ul>{photo_useful}</ul></li>
<li>你认为不适合、规则仍判为候选：<ul>{photo_unsuitable}</ul></li>
</ul>

<h2>结论</h2>
<p><strong>{escape(outcome["conclusion"])}</strong>。{escape(conclusion_reason)}</p>
<p>上一轮结论是 {escape(outcome["prior_conclusion"])}；本轮没有修改冻结预测、模型、特征权重或正式排序，因此该结论仍成立，除非出现新的独立证据。</p>
<p>不使用本轮评价调整排序后重算同一批图片来证明成功；本轮只做评估方法修复。</p>

<details class="after"><summary>AI 辅助观察（不是用户确认，不参与人工标签）</summary>
<p class="muted">以下为冻结候选池已有的逐图 AI 观察，仅用于审计与解释规则状态；它们不是你的角色、摄影或审美判断。</p>
<ul class="analysis">{''.join(ai_rows)}</ul>
</details>

<h2>样本、去重与独立性</h2>
<ul class="analysis">
{dedupe_note}
<li>独立 SHA：{coverage["assets_total"]}；可计分 {coverage["scorable_total"]}；不可计分 {coverage["excluded_total"]}。</li>
<li>来源页 {independence["unique_source_pages"]} 个；平台 {escape("、".join(independence["source_hosts"]) or "未记录")}；已知作者 {independence["known_author_count"]} 位；独立来源组 {independence["distinct_source_groups"]} 个。</li>
<li>来源独立性状态：<strong>{escape(independence["status"])}</strong>。{escape(independence["note"])}</li>
<li>不可计分图片：<ul>{excluded_html}</ul></li>
<li>近似重复：<ul>{near_note}</ul></li>
</ul>

<h2>仍然缺少的人工证据</h2>
<p>本页不替代你的判断。要得到有人工真值的最终对照，仍需你实际完成逐图评价并提交；在此之前，任何“喜欢数量”“NDCG”或“摄影可用数”都是 N/A。若只评价一部分，报告会保留覆盖和缺失数量，不会把未评价图片当成不喜欢。角色准确性、摄影参考价值与个人审美仍是三套独立标签，不能互相替代。</p>
<details><summary>冻结输入哈希</summary><pre>{escape(json.dumps(metrics["experiment_inputs"], ensure_ascii=False, indent=2))}</pre></details>
<details><summary>标签快照哈希与协议</summary><pre>{escape(json.dumps({"labels_sha256": metrics["labels_sha256"], "protocol": metrics["protocol"], "labels_status": metrics["labels_status"], "mode": metrics["mode"]}, ensure_ascii=False, indent=2))}</pre></details>
'''
    return ("<!doctype html><html lang=\"zh-CN\"><head><meta charset=\"utf-8\">"
            "<meta name=\"viewport\" content=\"width=device-width, initial-scale=1\">"
            "<meta http-equiv=\"Content-Security-Policy\" content=\"default-src 'none'; img-src 'self' file: data:; style-src 'unsafe-inline'; base-uri 'none'\">"
            "<link rel=\"icon\" href=\"data:,\">"
            f"<title>星野露比逐图评价结果</title><style>{REVIEW_STYLE}</style></head><body><main>{body}</main></body></html>")


def write_report(experiment: Path, doc: dict, labels: dict, *, mode: str = "post_submit",
                 labels_source: str = "LABELS_FILE") -> dict:
    metrics = compute_metrics(doc, labels, labels_source=labels_source, mode=mode)
    experiment = Path(experiment)
    save_json_atomic(experiment / METRICS_FILE, metrics)
    atomic_write(experiment / REPORT_PAGE, report_html(doc, metrics, labels).encode("utf-8"))
    return metrics


def load_labels_for_report(experiment: Path, doc: dict) -> tuple[dict, str]:
    store = LabelStore(experiment, doc)
    if store.path.is_file():
        return store.load(), "LABELS_FILE"
    return store.base(), "NO_LABELS_FILE"


# ---------------------------------------------------------------------------
# Minimal loopback HTTP service

class ReviewRequestHandler(BaseHTTPRequestHandler):
    server_version = "RefLabHumanReview/1"
    protocol_version = "HTTP/1.1"

    def log_message(self, fmt: str, *args) -> None:  # keep terminal output for the URL only
        return

    def _send(self, status: int, body: bytes, content_type: str) -> None:
        self.send_response(status)
        self.send_header("Content-Type", content_type)
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Cache-Control", "no-store")
        self.send_header("X-Content-Type-Options", "nosniff")
        self.send_header("Referrer-Policy", "no-referrer")
        self.end_headers()
        self.wfile.write(body)

    def _json(self, status: int, value: object) -> None:
        self._send(status, json_bytes(value), "application/json; charset=utf-8")

    def _error(self, status: int, message: str) -> None:
        self._json(status, {"ok": False, "error": message})

    def _authorized(self) -> bool:
        supplied = self.headers.get("X-Review-Token", "")
        return hmac.compare_digest(supplied, self.server.token)

    def do_GET(self) -> None:
        path = unquote(urlsplit(self.path).path)
        if path in {"/", "/ruby-human-review.html"}:
            page = Path(self.server.doc["experiment"]) / REVIEW_PAGE
            if not page.is_file():
                write_review_page(self.server.doc)
            html_text = page.read_text(encoding="utf-8").replace("__REVIEW_TOKEN__", self.server.token)
            self._send(200, html_text.encode("utf-8"), "text/html; charset=utf-8")
            return
        if path == "/api/health":
            self._json(200, {"ok": True, "protocol": PROTOCOL_VERSION})
            return
        if path == "/api/state":
            if not self._authorized():
                self._error(403, "Invalid review token")
                return
            try:
                self._json(200, self.server.store.state())
            except ExperimentDrift as error:
                self._error(409, str(error))
            return
        if path == "/ruby-human-report.html":
            report = Path(self.server.doc["experiment"]) / REPORT_PAGE
            if not report.is_file():
                self._error(404, "Report has not been generated yet")
                return
            self._send(200, report.read_bytes(), "text/html; charset=utf-8")
            return
        if path.lower().endswith(".html"):
            relative = path.lstrip("/")
            candidate = (Path(self.server.doc["experiment"]) / relative).resolve()
            experiment = Path(self.server.doc["experiment"]).resolve()
            if candidate.is_relative_to(experiment) and candidate.is_file():
                self._send(200, candidate.read_bytes(), "text/html; charset=utf-8")
                return
            self._error(404, "Not found")
            return
        if path.startswith("/image/"):
            sha = path[len("/image/"):]
            blob = self.server.images.get(sha)
            if blob is None:
                self._error(404, "Unknown image SHA")
                return
            data, content_type = blob
            self._send(200, data, content_type)
            return
        # Report thumbnails are relative paths under the experiment directory.
        relative = path.lstrip("/")
        candidate = (Path(self.server.doc["experiment"]) / relative).resolve()
        experiment = Path(self.server.doc["experiment"]).resolve()
        if (candidate.is_relative_to(experiment) and candidate.is_file()
                and candidate.suffix.lower() in {".jpg", ".jpeg", ".png", ".webp", ".avif"}):
            self._send(200, candidate.read_bytes(), mimetypes.guess_type(candidate.name)[0] or "application/octet-stream")
            return
        self._error(404, "Not found")

    def do_POST(self) -> None:
        path = urlsplit(self.path).path
        if path not in {"/api/draft", "/api/submit"}:
            self._error(404, "Not found")
            return
        if not self._authorized():
            self._error(403, "Invalid review token")
            return
        if path == "/api/submit":
            try:
                result = self.server.store.submit()
            except AlreadySubmitted as error:
                self._error(409, str(error))
            except ExperimentDrift as error:
                self._error(409, str(error))
            except Exception as error:  # keep the server alive; report the actual reason
                self._error(500, f"Submit failed: {error}")
            else:
                self._json(200, result)
            return
        length = int(self.headers.get("Content-Length", "0") or 0)
        if length <= 0 or length > 100_000:
            self._error(400, "Invalid request size")
            return
        if "application/json" not in self.headers.get("Content-Type", ""):
            self._error(415, "Content-Type must be application/json")
            return
        try:
            payload = json.loads(self.rfile.read(length).decode("utf-8"))
        except (UnicodeDecodeError, json.JSONDecodeError):
            self._error(400, "Invalid JSON")
            return
        try:
            result = self.server.store.draft(payload)
        except ValidationError as error:
            self._error(400, str(error))
        except AlreadySubmitted as error:
            self._error(409, str(error))
        except ExperimentDrift as error:
            self._error(409, str(error))
        else:
            self._json(200, result)


class ReviewHTTPServer(ThreadingHTTPServer):
    daemon_threads = True
    allow_reuse_address = True

    def __init__(self, address, doc: dict, store: LabelStore, token: str, images: dict):
        self.doc = doc
        self.store = store
        self.token = token
        self.images = images
        super().__init__(address, ReviewRequestHandler)


def load_image_blobs(doc: dict) -> dict:
    blobs = {}
    for asset in doc["assets"]:
        path = Path(asset["original_path"])
        if not path.is_file():
            continue
        data = path.read_bytes()
        if sha256_bytes(data) != asset["asset_sha"]:
            raise ExperimentDrift(f"Original image bytes changed: {asset['review_id']}")
        content_type = mimetypes.guess_type(path.name)[0] or "application/octet-stream"
        blobs[asset["asset_sha"]] = (data, content_type)
    return blobs


def create_server(experiment: Path = EXPERIMENT, port: int = 0, *, host: str = "127.0.0.1") -> ReviewHTTPServer:
    experiment = Path(experiment).resolve()
    doc = build_review(experiment)
    store = LabelStore(experiment, doc)
    token = secrets.token_urlsafe(24)
    images = load_image_blobs(doc)
    return ReviewHTTPServer((host, port), doc, store, token, images)


def serve(experiment: Path = EXPERIMENT, port: int = 0, *, open_browser: bool = False) -> None:
    server = create_server(experiment, port)
    actual_port = server.server_address[1]
    url = f"http://127.0.0.1:{actual_port}/"
    print(f"REVIEW_URL {url}", flush=True)
    print(f"REVIEW_EXPERIMENT {Path(experiment).resolve()}", flush=True)
    print("Press Ctrl+C to stop. No network interface other than 127.0.0.1 is opened.", flush=True)
    if open_browser:
        import webbrowser
        webbrowser.open(url)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        server.server_close()


# ---------------------------------------------------------------------------
# Verification helpers

def verify_against_baseline(experiment: Path, baseline: Path) -> dict:
    experiment = Path(experiment)
    record = load_json(Path(baseline))
    checks = []
    for relative, expected in (record.get("files") or {}).items():
        current = file_state(experiment, relative)
        checks.append({"path": relative, "expected": expected.get("sha256"), "actual": current["sha256"],
                       "pass": current["sha256"] == expected.get("sha256")})
    for sha, expected in (record.get("original_images") or {}).items():
        path = Path(expected.get("path", ""))
        actual = sha256_file(path) if path.is_file() else None
        checks.append({"path": str(path), "asset_sha": sha, "expected": expected.get("sha256"),
                       "actual": actual, "pass": actual == expected.get("sha256") == sha})
    return {"baseline": str(baseline), "pass": all(check["pass"] for check in checks),
            "checked": len(checks), "failures": [check for check in checks if not check["pass"]]}


def verify_images(experiment: Path = EXPERIMENT) -> dict:
    doc = build_review(experiment)
    failures = []
    for asset in doc["assets"]:
        path = Path(asset["original_path"])
        actual = sha256_file(path) if path.is_file() else None
        if actual != asset["asset_sha"]:
            failures.append({"review_id": asset["review_id"], "asset_sha": asset["asset_sha"], "actual": actual})
    return {"pass": not failures, "checked": len(doc["assets"]), "failures": failures,
            "independent_shas": len({asset["asset_sha"] for asset in doc["assets"]}),
            "duplicates_removed": len(doc["duplicates"])}


def main(argv: list[str] | None = None) -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("action", choices=["render", "serve", "report", "verify"])
    parser.add_argument("--experiment", type=Path, default=EXPERIMENT)
    parser.add_argument("--port", type=int, default=0)
    parser.add_argument("--open", action="store_true", help="Open the review URL in the default browser")
    parser.add_argument("--allow-unsubmitted", action="store_true",
                        help="Generate an explicitly marked pre-submit/N/A report; never used to claim accuracy")
    parser.add_argument("--baseline", type=Path, help="Compare protected file hashes to a recorded baseline")
    args = parser.parse_args(argv)

    experiment = args.experiment.resolve()
    if args.action == "render":
        doc = build_review(experiment)
        print(json.dumps({"page": str(experiment / REVIEW_PAGE), "assets": len(doc["assets"]),
                          "duplicates_removed": len(doc["duplicates"]),
                          "independence": doc["independence"]["status"]}, ensure_ascii=False, indent=2))
        return
    if args.action == "serve":
        serve(experiment, args.port, open_browser=args.open)
        return
    if args.action == "report":
        doc = build_review(experiment)
        labels, source = load_labels_for_report(experiment, doc)
        submitted = labels.get("status") == "submitted"
        if not submitted and not args.allow_unsubmitted:
            raise SystemExit("Refusing to generate metrics before submission; pass --allow-unsubmitted for an explicit N/A report")
        metrics = write_report(experiment, doc, labels, mode="post_submit" if submitted else "pre_submit_dry_run",
                               labels_source=source)
        print(json.dumps({"report": str(experiment / REPORT_PAGE), "metrics": str(experiment / METRICS_FILE),
                          "outcome": metrics["outcome"], "coverage": metrics["coverage"]},
                         ensure_ascii=False, indent=2))
        return
    result = verify_images(experiment)
    if args.baseline:
        comparison = verify_against_baseline(experiment, args.baseline)
        result["baseline"] = comparison
        result["pass"] = result["pass"] and comparison["pass"]
    print(json.dumps(result, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
