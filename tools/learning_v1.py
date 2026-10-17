#!/usr/bin/env python3
"""Offline Learning Loop V1. Never opens the live library for writing.

Experiment artifacts stay under .local/learning-v1. Curation is supervision only
for its declared task; AI observations are features, never human target labels.
"""
from __future__ import annotations

import argparse
from collections import Counter, defaultdict
from contextlib import closing
from datetime import datetime, timezone
import hashlib
import html
import json
from pathlib import Path
import re
import sqlite3
import sys
from typing import Any
from urllib.parse import urlsplit, urlunsplit

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
EXPERIMENT = ROOT / ".local" / "learning-v1"
SEED = 20261018
FEATURES = ("viewpoint", "framing", "pose", "lighting", "background", "gesture")
HOLDOUT_TERMS = ("星野露比", "星野ルビー", "hoshino ruby", "ruby hoshino")
PHOTO_KINDS = {"cosplay_photo", "portrait_photo", "real_person_cosplay", "real_person_photo"}
NONPHOTO_KINDS = {"illustration", "generated", "collage", "equipment", "location", "product", "game_screenshot"}


def stamp() -> str:
    return datetime.now(timezone.utc).isoformat()


def digest(value: Any) -> str:
    return hashlib.sha256(json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode()).hexdigest()


def save_json(path: Path, value: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def read_only(path: Path) -> sqlite3.Connection:
    connection = sqlite3.connect(path.resolve().as_uri() + "?mode=ro", uri=True)
    connection.row_factory = sqlite3.Row
    connection.execute("PRAGMA query_only=ON")
    return connection


def rows(connection: sqlite3.Connection, table: str) -> list[dict]:
    # Table names come exclusively from this module, never from a request.
    return [json.loads(row["data"]) for row in connection.execute(f'SELECT data FROM "{table}"')]


def human_label(ref: dict) -> dict:
    """Do not reinterpret K or a generic X as an aesthetic target."""
    origin = ref.get("decision_origin")
    current = origin == "human_curation"
    negative = (ref.get("decision") == "reject" and ref.get("is_aesthetic_negative") is True
                and ref.get("aesthetic_negative_origin") == "human_curation")
    return {
        "project_use": (1 if ref.get("decision") == "keep" else 0 if ref.get("decision") == "reject" else None) if current else None,
        "aesthetic": 0 if negative else None,
        "origin": origin or "legacy_unverified",
        "reason": ref.get("rejection_reason", "") if ref.get("rejection_feedback_origin") == "human" else "",
        "preference": ref.get("preference", "") if ref.get("preference_origin") == "human_curation" else "",
    }


def is_holdout(record: Any) -> bool:
    text = json.dumps(record, ensure_ascii=False).casefold()
    return any(term in text for term in HOLDOUT_TERMS)


def original_path(data_dir: Path, asset: dict) -> Path:
    sha, ext = asset["id"], asset["ext"]
    if not re.fullmatch(r"[a-f0-9]{64}", sha) or ext not in {"jpg", "png", "webp", "avif"}:
        raise ValueError("Invalid immutable asset identity")
    return data_dir / "assets" / sha[:2] / sha / f"original.{ext}"


def canonical_group_hash(path: Path) -> str:
    """One documented big-endian, EXIF-oriented dHash for BOTH input pools.

    Library and collector historical encodings differ; never compare their
    stored strings across that boundary. This value is not a taste feature.
    """
    from PIL import Image, ImageOps
    with Image.open(path) as original:
        image = ImageOps.exif_transpose(original).convert("L").resize((9, 8), Image.Resampling.LANCZOS)
        pixels = list(image.get_flattened_data() if hasattr(image, "get_flattened_data") else image.getdata())
    value = 0
    for y in range(8):
        for x in range(8):
            value = (value << 1) | int(pixels[y * 9 + x] > pixels[y * 9 + x + 1])
    return f"{value:016x}"


def source_group(url: str) -> str | None:
    parsed = urlsplit(url)
    if parsed.scheme not in {"http", "https"} or not parsed.netloc:
        return None
    path = re.sub(r"/photo/\d+/?$", "", parsed.path).rstrip("/")
    if any(part in path.lower() for part in ("/search", "/search_result")):
        return None
    return urlunsplit((parsed.scheme, parsed.netloc.lower(), path, "", ""))


def grouped_components(records: list[dict], dhash_distance: int = 5) -> tuple[dict[str, str], dict]:
    """Conservative transitive groups: same SHA, declared character, source, author or near image.

    Unknown source records share a bucket. This may make CV impossible; it must
    not manufacture independence by assigning unknown photographers unique IDs.
    dHash is only a duplicate hint, never an aesthetic feature or fact of a shoot.
    """
    parent = {r["asset_sha"]: r["asset_sha"] for r in records}

    def find(x: str) -> str:
        while parent[x] != x:
            parent[x] = parent[parent[x]]
            x = parent[x]
        return x

    def join(a: str, b: str) -> None:
        a, b = find(a), find(b)
        if a != b:
            parent[max(a, b)] = min(a, b)

    seen: dict[str, str] = {}
    hashes: list[tuple[str, int]] = []
    near_edges = []
    for record in records:
        sha = record["asset_sha"]
        keys = [f"character:{x.casefold()}" for x in record.get("declared_characters", []) if x]
        urls = [source_group(x) for x in record.get("source_pages", [])]
        keys += [f"source:{x}" for x in urls if x]
        keys += [f"author:{x.casefold()}" for x in record.get("declared_authors", []) if x]
        if not any(urls):
            keys.append("source:unknown")
        for key in keys:
            if key in seen:
                join(sha, seen[key])
            else:
                seen[key] = sha
        value = record.get("dhash", "")
        if re.fullmatch(r"[a-f0-9]{16}", value):
            val = int(value, 16)
            for other, other_val in hashes:
                if (val ^ other_val).bit_count() <= dhash_distance:
                    near_edges.append([other, sha])
                    join(sha, other)
            hashes.append((sha, val))
    mapping = {sha: find(sha) for sha in parent}
    return mapping, {"group_count": len(set(mapping.values())), "near_duplicate_edges": near_edges,
                     "method": "conservative connected components; not confirmed shoot identities",
                     "dhash_distance": dhash_distance, "unknown_source_policy": "one shared group"}


def similarity(left: dict, right: dict) -> tuple[float | None, int]:
    comparable = [key for key in FEATURES if left.get(key) not in {None, "", "unknown"}
                  and right.get(key) not in {None, "", "unknown"}]
    if len(comparable) < 2:
        return None, len(comparable)
    # Fixed, equal feature weights. No fitted parameters or taste probabilities.
    return sum(left[key] == right[key] for key in comparable) / len(FEATURES), len(comparable)


def fit_exemplars(records: list[dict]) -> dict:
    if any(is_holdout(record) for record in records):
        raise ValueError("Holdout data cannot enter fitting")
    positives = [r for r in records if r.get("aesthetic_label") == 1 and r.get("aesthetic_label_origin") == "explicit_user_message"]
    negatives = [r for r in records if r.get("aesthetic_label") == 0 and r.get("aesthetic_label_origin") == "human_curation"]
    return {"schema_version": 1, "strategy": "positive-exemplar-retrieval-v1", "seed": SEED,
            "trained_parameters": False, "parametric_training_status": "NOT_TRAINABLE",
            "reason": "No adequately grouped independently labelled positive/negative preference dataset; use retrieval only.",
            "feature_names": list(FEATURES), "weights": {key: 1 / len(FEATURES) for key in FEATURES},
            "weight_origin": "fixed equal weights, not user labels and not fitted",
            "positive_count": len(positives), "negative_count": len(negatives),
            "exemplars": [{"asset_sha": r["asset_sha"], "features": r.get("features", {}), "group": r.get("group")}
                          for r in positives], "training_sha": [r["asset_sha"] for r in positives],
            "input_fingerprint": digest(records)}


def rule_state(record: dict) -> str:
    visual = record.get("visual") or {}
    if visual.get("asset_sha") != record.get("asset_sha") or not visual.get("observed") or not visual.get("evidence"):
        return "needs_evidence"
    if visual.get("kind") in NONPHOTO_KINDS or visual.get("identity") == "mismatch" or visual.get("costume") == "mismatch":
        return "excluded"
    if visual.get("kind") in PHOTO_KINDS and visual.get("identity") == "match" and visual.get("costume") in {"match", "not_required"}:
        return "candidate"
    return "needs_evidence"


def rank_pool(pool: list[dict], strategy: str, model: dict | None = None) -> list[dict]:
    if strategy not in {"baseline0", "baseline1", "candidate2"}:
        raise ValueError("Unknown strategy")
    result = []
    seen = set()
    for index, record in enumerate(pool):
        sha = record["asset_sha"]
        if sha in seen:
            raise ValueError("Fixed candidate pool must be SHA unique")
        seen.add(sha)
        score, closest, coverage = None, None, 0
        if strategy == "candidate2":
            for exemplar in (model or {}).get("exemplars", []):
                if sha == exemplar["asset_sha"] or (record.get("group") and record.get("group") == exemplar.get("group")):
                    continue
                value, count = similarity(record.get("features", {}), exemplar.get("features", {}))
                if value is not None and (score is None or value > score):
                    score, closest, coverage = value, exemplar["asset_sha"], count
        result.append({**record, "original_rank": index + 1, "strategy": strategy, "strategy_version": 1,
                       "rule_state": rule_state(record), "similarity": score, "nearest_exemplar": closest,
                       "feature_coverage": coverage, "uncertainty": "not a probability of personal liking"})
    if strategy != "baseline0":
        order = {"candidate": 0, "needs_evidence": 1, "excluded": 2}
        result.sort(key=lambda r: (order[r["rule_state"]], -(r["similarity"] if r["similarity"] is not None else -1)
                                  if strategy == "candidate2" else 0, r["original_rank"]))
    return result


def scored_ratio(numerator: int, denominator: int) -> dict:
    return {"numerator": numerator, "denominator": denominator,
            "value": numerator / denominator if denominator else None,
            "status": "SCORED" if denominator else "NOT_SCORABLE"}


def rule_metrics(predictions: list[dict]) -> dict:
    # Targets must be explicit human rule judgements for this exact context.
    labelled = [r for r in predictions if r.get("human_rule_origin") == "human"
                and r.get("human_rule_label") in {0, 1}]
    tp = sum(r["rule_state"] == "candidate" and r["human_rule_label"] == 1 for r in labelled)
    fp = sum(r["rule_state"] == "candidate" and r["human_rule_label"] == 0 for r in labelled)
    fn = sum(r["rule_state"] == "excluded" and r["human_rule_label"] == 1 for r in labelled)
    tn = sum(r["rule_state"] == "excluded" and r["human_rule_label"] == 0 for r in labelled)
    return {"labelled": len(labelled), "tp": tp, "fp": fp, "fn": fn, "tn": tn,
            "abstained": len(labelled) - tp - fp - fn - tn,
            "precision": scored_ratio(tp, tp + fp),
            "recall_including_abstentions": scored_ratio(tp, sum(r["human_rule_label"] == 1 for r in labelled)),
            "coverage": scored_ratio(tp + fp + fn + tn, len(labelled))}


def preservation(connection: sqlite3.Connection) -> dict:
    keys = ("id", "asset_sha", "project_id", "decision", "lane", "preference", "borrow", "rejection_reason",
            "is_aesthetic_negative", "aesthetic_negative_origin", "decision_origin", "accepted_fingerprint", "detached_at")
    refs = [{key: r.get(key) for key in keys} for r in rows(connection, "refs")]
    values = {"references": sorted(refs, key=lambda r: r["id"]), "projects": rows(connection, "projects"),
              "inspirations": rows(connection, "inspirations"), "study_candidates": rows(connection, "study_candidates"),
              "screening_sessions": rows(connection, "screening_sessions"), "aesthetic_profiles": rows(connection, "aesthetic_profiles")}
    return {key: {"count": len(value), "sha256": digest(value)} for key, value in values.items()}


def audit(data_dir: Path, reuse_snapshot: bool = False) -> dict:
    EXPERIMENT.mkdir(parents=True, exist_ok=True)
    snapshot = EXPERIMENT / "snapshot.sqlite3"
    if snapshot.exists() and not reuse_snapshot:
        raise FileExistsError("Snapshot already exists; never silently replace a frozen dataset")
    if not snapshot.exists():
        with closing(read_only(data_dir / "library.sqlite3")) as live, closing(sqlite3.connect(snapshot)) as target:
            live.backup(target)
    with closing(read_only(snapshot)) as connection:
        projects = {r["id"]: r for r in rows(connection, "projects")}
        assets, refs = rows(connection, "assets"), rows(connection, "refs")
        studies, sessions = rows(connection, "study_candidates"), rows(connection, "screening_sessions")
        annotations = {r["asset_sha"]: r for r in rows(connection, "library_annotations")}
        observations = rows(connection, "asset_observations")
        save_json(EXPERIMENT / "production-before.json", preservation(connection))
        event_counts = dict(connection.execute("SELECT actor,count(*) FROM events GROUP BY actor"))
        human_events = [dict(r) for r in connection.execute("SELECT * FROM events WHERE actor='human'")]
    actions = [a for session in sessions for a in session.get("actions", [])]
    typed_actions = [a for a in actions if a.get("origin") == "human_curation"]
    last_actions = {(a.get("reference_id"), a.get("asset_sha")): a for a in sorted(typed_actions, key=lambda a: a.get("at", ""))}
    by_sha: dict[str, list] = defaultdict(list)
    for ref in refs:
        by_sha[ref["asset_sha"]].append(ref)
    study_by_sha = {r["asset_sha"]: r for r in studies}
    explicit_positive = json.loads((ROOT / ".local/search-quality-20261018/owner-positive/feedback.json").read_text(encoding="utf-8"))
    records, quarantined, integrity_errors, note_rows = [], [], [], []
    for asset in assets:
        sha = asset["id"]
        uses = by_sha.get(sha, [])
        study = study_by_sha.get(sha, {})
        path = original_path(data_dir, asset)
        actual = hashlib.sha256(path.read_bytes()).hexdigest() if path.is_file() else None
        if actual != sha:
            integrity_errors.append({"asset_sha": sha, "path": str(path), "actual": actual})
        annotation = annotations.get(sha, {})
        feature_valid = annotation.get("actor") in {"human", "ai"} and bool(annotation.get("evidence")) and annotation.get("asset_sha") == sha
        labels = []
        for ref in uses:
            action = last_actions.get((ref["id"], sha), {})
            supported = (action.get("decision") == ref.get("decision") and action.get("lane") == ref.get("lane")
                         and action.get("origin") == "human_curation")
            local_ref = {**ref, "decision_origin": "human_curation"} if supported else ref
            label = human_label(local_ref)
            label["reference_id"] = ref["id"]
            label["provenance"] = "matching_sha_and_choice_session_record" if supported else "current_reference"
            project = projects.get(ref["project_id"], {})
            label["synthetic_project_excluded"] = "测试" in project.get("character", "")
            if label["synthetic_project_excluded"]:
                label["project_use"] = None
                label["aesthetic"] = None
            labels.append(label)
        aesthetic_negative = any(l["aesthetic"] == 0 for l in labels)
        positive = sha == explicit_positive.get("image_sha256") and explicit_positive.get("feedback_origin") == "explicit_user_message"
        source_pages = sorted({(r.get("source") or {}).get("page_url", "") for r in uses} | {study.get("source_page", "")})
        authors = sorted({(r.get("source") or {}).get("author", "") for r in uses} - {""})
        characters = sorted({projects.get(r["project_id"], {}).get("character", "") for r in uses} - {""})
        record = {"asset_sha": sha, "original_path": str(path.resolve()), "bytes_verified": actual == sha,
                  "dhash": canonical_group_hash(path) if actual == sha else "", "stored_dhash": asset.get("dhash", ""),
                  "width": asset.get("width"), "height": asset.get("height"),
                  "reference_ids": [r["id"] for r in uses], "project_ids": sorted({r["project_id"] for r in uses}),
                  "declared_characters": characters, "source_pages": [u for u in source_pages if u],
                  "declared_authors": authors, "labels": labels,
                  "aesthetic_label": None if positive and aesthetic_negative else 1 if positive else 0 if aesthetic_negative else None,
                  "aesthetic_label_origin": "conflict" if positive and aesthetic_negative else "explicit_user_message" if positive else "human_curation" if aesthetic_negative else None,
                  "explicit_positive_quote": explicit_positive["user_feedback"] if positive else None,
                  "features": {key: annotation.get(key, "unknown") if feature_valid else "unknown" for key in FEATURES},
                  "feature_evidence": annotation.get("evidence", "") if feature_valid else "",
                  "feature_origin": annotation.get("actor", "unknown") if feature_valid else "unknown",
                  "study_status": study.get("status"), "study_decision_origin": study.get("decision_origin"),
                  "human_study_reasons": study.get("study_reasons", []) if study.get("reason_origin") == "human" else [],
                  "discovery_titles": [r.get("title", "") for r in uses] + [study.get("title", "")],
                  "holdout_check_context": study.get("source_record", {}).get("角色标注", "")}
        for ref, label in zip(uses, labels):
            if label["reason"] or label["preference"]:
                note_rows.append({"asset_sha": sha, "reference_id": ref["id"], "project_id": ref["project_id"],
                                  "human_reason": label["reason"], "human_preference": label["preference"],
                                  "structured_aesthetic_negative": label["aesthetic"] == 0,
                                  "interpretation": "Raw human text retained; no keyword-to-taste-label conversion"})
        if is_holdout(record):
            quarantined.append(record)
        else:
            records.append(record)
    groups, group_report = grouped_components(records)
    for record in records:
        record["group"] = groups[record["asset_sha"]]
    human_refs = [r for r in refs if r.get("decision_origin") == "human_curation"]
    report = {"created_at": stamp(), "snapshot_sha256": hashlib.sha256(snapshot.read_bytes()).hexdigest(),
              "independent_asset_shas": len(assets), "reference_rows": len(refs), "cross_project_extra_uses": len(refs) - len(by_sha),
              "project_count": len(projects), "active_project_count": sum(not r.get("archived_at") for r in projects.values()),
              "declared_characters": sorted({r.get("character", "") for r in projects.values()}),
              "declared_costumes": sorted({r.get("costume", "") for r in projects.values()} - {""}),
              "raw_decisions": dict(Counter(r["decision"] for r in refs)),
              "explicit_origin_decisions": dict(Counter(r["decision"] for r in human_refs)),
              "explicit_origin_reference_shas": len({r["asset_sha"] for r in human_refs}),
              "session_actions": len(actions), "explicit_origin_session_actions": len(typed_actions),
              "explicit_origin_session_unique_shas": len({a["asset_sha"] for a in typed_actions}),
              "session_or_reference_supported_project_use_shas": sum(any(l["project_use"] is not None for l in r["labels"]) for r in records),
              "supported_project_use_shas_with_visual_features": sum(any(l["project_use"] is not None for l in r["labels"]) and r["feature_origin"] != "unknown" for r in records),
              "event_actor_counts": event_counts, "human_event_unique_entities": len({r["entity_id"] for r in human_events}),
              "study_count": len(studies), "human_study_count": sum(r.get("decision_origin") == "human" for r in studies),
              "human_text_feedback_count": len(note_rows),
              "explicit_aesthetic_positive_shas": sum(r["aesthetic_label"] == 1 for r in records),
              "structured_aesthetic_negative_shas": sum(r["aesthetic_label"] == 0 for r in records),
              "untyped_human_aesthetic_criticism": "Inspect human-feedback.json; false flags do not erase explicit prose, but prose needs scoped adjudication.",
              "image_bound_annotation_count": sum(r["feature_origin"] != "unknown" for r in records),
              "annotation_origins": dict(Counter(r["feature_origin"] for r in records)),
              "asset_observation_origins": dict(Counter(r.get("actor", "unknown") for r in observations)),
              "sourced_with_image_bound_features": sum(bool(r["source_pages"]) and r["feature_origin"] != "unknown" and r["bytes_verified"] for r in records),
              "known_post_source_shas": sum(any(source_group(u) for u in r["source_pages"]) for r in records),
              "quarantined_holdout_count": len(quarantined), "integrity_verified": len(assets) - len(integrity_errors),
              "group_hash_encoding": "recomputed_from_original_bytes; EXIF-oriented 64-bit big-endian dHash, equally for training and holdout",
              "stored_vs_canonical_encoding_differences": sum(r["dhash"] != r["stored_dhash"] for r in records + quarantined),
              "integrity_errors": integrity_errors, "groups": group_report,
              "shoot_identity_status": "NOT_FULLY_VERIFIED; connected groups are conservative metadata/dHash safeguards",
              "aesthetic_binary_training": "NOT_TRAINABLE", "parametric_rule_training": "NOT_TRAINABLE pending independent visual truth and usable feature coverage",
              "human_ground_truth_policy": "K/project use, I/inspiration, M/undecided, X/project rejection are separate. AI facts never become target labels."}
    save_json(EXPERIMENT / "dataset-audit.json", report)
    save_json(EXPERIMENT / "dataset.json", records)
    save_json(EXPERIMENT / "quarantine.json", quarantined)
    save_json(EXPERIMENT / "human-feedback.json", note_rows)
    save_json(EXPERIMENT / "group-manifest.json", {"groups": groups, "report": group_report})
    return report


def load_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def attach_review(record: dict, review: dict) -> dict:
    sha = record["asset_sha"]
    if review.get("asset_sha") != sha or review.get("visual", {}).get("asset_sha") != sha:
        raise ValueError("Visual review is not bound to these image bytes")
    path = Path(record["original_path"])
    if hashlib.sha256(path.read_bytes()).hexdigest() != sha:
        raise ValueError("Reviewed image bytes changed")
    features = review.get("features", {})
    if set(features) != set(FEATURES) or any(not isinstance(value, str) for value in features.values()):
        raise ValueError("Visual feature schema mismatch")
    if not review.get("visual", {}).get("observed") or not review["visual"].get("evidence"):
        raise ValueError("A direct image review with evidence is required")
    return {**record, "features": features, "visual": review["visual"],
            "feature_origin": review.get("feature_origin", "ai_direct_image_review")}


def utility_at_k(ranked: list[dict], k: int) -> dict:
    top = ranked[:k]
    labelled = [r for r in top if r.get("project_use_label") in {0, 1}]
    metric = scored_ratio(sum(r["project_use_label"] == 1 for r in labelled), len(top))
    metric.update({"k": k, "known": len(labelled), "unknown": len(top) - len(labelled),
                   "target": "human project-use decisions, NOT aesthetic liking"})
    if len(labelled) < len(top):
        metric.update(value=None, status="NOT_SCORABLE")
    return metric


def evaluate_offline() -> dict:
    if (EXPERIMENT / "freeze.json").exists():
        raise ValueError("The experiment is frozen; do not recompute training or validation after holdout")
    dataset = load_json(EXPERIMENT / "dataset.json")
    by_sha = {r["asset_sha"]: r for r in dataset}
    reviews = {r["asset_sha"]: r for r in load_json(EXPERIMENT / "visual-features.json")}
    selected = load_json(EXPERIMENT / "offline-selection.json")["items"]
    positive_rows = [r for r in dataset if r["aesthetic_label"] == 1]
    exemplars = [attach_review(r, reviews[r["asset_sha"]]) for r in positive_rows]
    model = fit_exemplars(exemplars)
    save_json(EXPERIMENT / "model.json", model)
    pool = [attach_review({**by_sha[r["asset_sha"]], "project_use_label": r["project_use_label"]}, reviews[r["asset_sha"]]) for r in selected]
    with closing(read_only(EXPERIMENT / "snapshot.sqlite3")) as connection:
        insertion_order: dict[str, int] = {}
        for row in connection.execute("SELECT rowid, data FROM refs ORDER BY rowid"):
            ref = json.loads(row["data"])
            insertion_order.setdefault(ref["asset_sha"], row["rowid"])
    pool.sort(key=lambda r: insertion_order[r["asset_sha"]])
    # Only unambiguous explicitly written human rule rejections are targets.
    # The full-body contradiction in label-caveats.json is deliberately excluded.
    for record in pool:
        reason = next((l["reason"] for l in record["labels"] if l["reason"]), "")
        if reason in {"AI假图/非真人", "无关角色"} or reason.startswith("这是星野爱 不是有马加奈"):
            record.update(human_rule_label=0, human_rule_origin="human", human_rule_quote=reason)
    folds = []
    for group in sorted({r["group"] for r in pool}):
        train = [r for r in exemplars if r["group"] != group]
        validation = [r for r in pool if r["group"] == group]
        fold_model = fit_exemplars(train)
        strategies = {strategy: rank_pool(validation, strategy, fold_model)
                      for strategy in ("baseline0", "baseline1", "candidate2")}
        folds.append({"validation_group": group, "train_shas": fold_model["training_sha"],
                      "validation_shas": [r["asset_sha"] for r in validation],
                      "character_contexts": sorted({c for r in validation for c in r["declared_characters"]}),
                      "no_sha_overlap": not set(fold_model["training_sha"]) & {r["asset_sha"] for r in validation},
                      "no_group_overlap": all(r["group"] != group for r in train),
                      "prototype_available": bool(train),
                      "metrics": {key: utility_at_k(value, min(3, len(value))) for key, value in strategies.items()},
                      "rankings": {key: [r["asset_sha"] for r in value] for key, value in strategies.items()},
                      "ablation_removing_exemplar_changes_order": [r["asset_sha"] for r in strategies["baseline1"]] != [r["asset_sha"] for r in strategies["candidate2"]]})
    predictions = {strategy: rank_pool(pool, strategy, model) for strategy in ("baseline0", "baseline1", "candidate2")}
    report = {"at": stamp(), "status": "NOT_PROVEN", "parameter_training": "NOT_TRAINABLE",
              "method": model["strategy"], "trained_parameters": False, "positive_exemplars": len(exemplars),
              "pool_size": len(pool), "pool_fingerprint": digest([r["asset_sha"] for r in pool]),
              "selection": "Predeclared SHA-based balanced subset, not a random sample of future traffic",
              "arrival_order": "Original reference SQLite insertion order in the immutable snapshot",
              "feature_origin": "17 images directly opened by this Agent; only descriptive features, not user labels",
              "rule_evaluation": rule_metrics(predictions["baseline1"]),
              "rule_comparison_boundary": "All strategies share the same observations and gate. Baseline1 changes order, not classifier truth or learned parameters.",
              "aesthetic_top_k": {"status": "NOT_SCORABLE", "known_positive_numerator": 0,
                                   "independently_labelled_denominator": 0, "unknown": len(pool),
                                   "reason": "The only explicit like is training-only; project K/X and dimension-specific criticism are not binary taste labels."},
              "global_proxy_metrics": {key: utility_at_k(value, 5) for key, value in predictions.items()},
              "folds": folds,
              "ablations": {"remove_aesthetic_module": "baseline1", "same_pool": True,
                            "changed_fold_count": sum(f["ablation_removing_exemplar_changes_order"] for f in folds),
                            "aesthetic_benefit": "NOT_PROVEN; no independent aesthetic targets"},
              "generalisation": "Too few effective groups; unknown sources and possible unobserved same-shoot links remain. No reliable taste accuracy estimate.",
              "production_integration": "DISABLED; the offline method has not earned promotion"}
    save_json(EXPERIMENT / "offline-pool.json", pool)
    save_json(EXPERIMENT / "offline-predictions.json", predictions)
    save_json(EXPERIMENT / "offline-evaluation.json", report)
    return report


def freeze_experiment() -> dict:
    files = [ROOT / "tools/learning_v1.py", ROOT / "tools/learning_v1_search.py", ROOT / "tools/learning_v1_report.py",
             ROOT / "tools/collect_adapter.py"]
    files += [EXPERIMENT / name for name in ("snapshot.sqlite3", "dataset-audit.json", "dataset.json", "quarantine.json",
                                            "group-manifest.json", "offline-selection.json", "visual-features.json", "model.json",
                                            "label-caveats.json", "offline-pool.json", "offline-evaluation.json", "ruby-task.json")]
    files += [EXPERIMENT / "search" / key / name for key in ("zhaojun", "tohru") for name in ("manifest.json", "visual-review.json")]
    records = load_json(EXPERIMENT / "dataset.json")
    if any(is_holdout(r) for r in records):
        raise ValueError("Detected held-out character in training input")
    frozen = {"version": 1, "at": stamp(), "seed": SEED, "status": "FROZEN_BEFORE_RUBY_SEARCH",
              "file_hashes": {str(p.resolve().relative_to(ROOT)): hashlib.sha256(p.read_bytes()).hexdigest() for p in files},
              "model_config_fingerprint": digest(load_json(EXPERIMENT / "model.json")),
              "holdout_policy": {"character": "星野露比", "costume_required": False, "max_queries": 8, "max_reviewed_images": 20,
                                 "post_holdout_tuning": False, "blind_seed": SEED},
              "scope": "Experiment input, rules, features, equal weights, implementation and query plan",
              "limitations": ["Only one explicit positive prototype", "Unknown photographers/sessions are not proven independent",
                              "No independently labelled held-out aesthetic truth until the owner reviews"]}
    with (EXPERIMENT / "freeze.json").open("x", encoding="utf-8") as stream:
        json.dump(frozen, stream, ensure_ascii=False, indent=2)
    return frozen


def check_freeze() -> dict:
    frozen = load_json(EXPERIMENT / "freeze.json")
    for relative, expected in frozen["file_hashes"].items():
        path = (ROOT / relative).resolve()
        if not path.is_relative_to(ROOT) or hashlib.sha256(path.read_bytes()).hexdigest() != expected:
            raise ValueError(f"Frozen input or implementation changed: {relative}")
    return frozen


def reviewed_search(key: str) -> list[dict]:
    if key not in {"zhaojun", "tohru", "ruby"}:
        raise ValueError("Unknown search key")
    folder = EXPERIMENT / "search" / key
    manifest = load_json(folder / "manifest.json")
    reviewed = {r["asset_sha"]: r for r in load_json(folder / "visual-review.json")}
    if len(reviewed) > 20 or set(reviewed) != {r["asset_sha"] for r in manifest["candidates"]}:
        raise ValueError("Candidate review coverage or budget mismatch")
    return [attach_review(r, reviewed[r["asset_sha"]]) for r in manifest["candidates"]]


def evaluate_holdout() -> dict:
    frozen = check_freeze()
    pool = reviewed_search("ruby")
    manifest = load_json(EXPERIMENT / "search/ruby/manifest.json")
    if frozen["at"] >= load_json(EXPERIMENT / "search/ruby/started.json")["at"]:
        raise ValueError("Holdout must start strictly after freeze")
    prior = load_json(EXPERIMENT / "dataset.json") + load_json(EXPERIMENT / "quarantine.json")
    prior_shas = {r["asset_sha"] for r in prior}
    prior_sources = {source_group(url) for r in prior for url in r.get("source_pages", [])} - {None}
    leakage = []
    for record in pool:
        dhash = canonical_group_hash(Path(record["original_path"]))
        record["dhash"] = dhash
        near = [r["asset_sha"] for r in prior if re.fullmatch(r"[a-f0-9]{16}", r.get("dhash", ""))
                and (int(dhash, 16) ^ int(r["dhash"], 16)).bit_count() <= 5]
        source_seen = source_group(record["source"]["page_url"]) in prior_sources
        if record["asset_sha"] in prior_shas or near or source_seen:
            leakage.append({"asset_sha": record["asset_sha"], "exact": record["asset_sha"] in prior_shas,
                            "near_shas": near, "source_seen": source_seen})
        record["holdout_overlap_detected"] = bool(record["asset_sha"] in prior_shas or near or source_seen)
    usable = [r for r in pool if not r["holdout_overlap_detected"]]
    model = load_json(EXPERIMENT / "model.json")
    predictions = {strategy: rank_pool(usable, strategy, model) for strategy in ("baseline0", "baseline1", "candidate2")}
    report = {"at": stamp(), "freeze_at": frozen["at"], "frozen_hashes_verified": True,
              "query_count": manifest["query_count_including_prior"], "received_count": len(pool), "individually_reviewed": len(pool),
              "holdout_eligible_count": len(usable), "overlap_quarantined": leakage,
              "photographic_type_counts": dict(Counter(r["visual"]["kind"] for r in pool)),
              "rule_counts": dict(Counter(rule_state(r) for r in pool)),
              "scope": "One fixed candidate pool; three reproducible rankings. No post-test fitting or query expansion.",
              "aesthetic_accuracy": {"status": "NOT_SCORABLE", "human_rated_numerator": 0, "human_rated_denominator": 0},
              "blind_acceptance": "PENDING_OWNER_REVIEW", "outcome": "NOT_PROVEN",
              "provenance_limitations": "No exact/near/source overlap is not proof of different photographers or shoots; authors remain unverified.",
              "query_budget_pass": manifest["query_count_including_prior"] <= 8,
              "image_budget_pass": len(pool) <= 20}
    save_json(EXPERIMENT / "ruby-pool.json", pool)
    save_json(EXPERIMENT / "ruby-predictions.json", predictions)
    save_json(EXPERIMENT / "holdout-leakage.json", {"status": "DETECTED_OVERLAPS_QUARANTINED" if leakage else "NO_DETECTED_OVERLAP_WITH_KNOWN_LIBRARY",
                                                  "overlaps": leakage, "not_a_guarantee_of_shoot_independence": True})
    save_json(EXPERIMENT / "ruby-evaluation.json", report)
    return report


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("action", choices=["audit", "evaluate", "freeze", "check-freeze", "holdout", "report"])
    parser.add_argument("--data-dir", type=Path, default=ROOT / "data")
    parser.add_argument("--reuse-snapshot", action="store_true", help="Recompute audit from the existing snapshot; never recapture live data")
    args = parser.parse_args()
    if args.action == "audit":
        result = audit(args.data_dir.resolve(), reuse_snapshot=args.reuse_snapshot)
    elif args.action == "evaluate":
        result = evaluate_offline()
    elif args.action == "freeze":
        result = freeze_experiment()
    elif args.action == "check-freeze":
        frozen = check_freeze()
        result = {"status": "PASS", "freeze_at": frozen["at"], "verified_files": len(frozen["file_hashes"])}
    elif args.action == "holdout":
        result = evaluate_holdout()
    else:
        from tools.learning_v1_report import render_all
        result = render_all()
    print(json.dumps({k: v for k, v in result.items() if k not in {"groups", "declared_characters"}}, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
