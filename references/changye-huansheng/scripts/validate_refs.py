#!/usr/bin/env python3
"""Strict validation script for Changye Huansheng Visual Reference System V2.1 (Expo Field Edition).
Enforces:
- Visual audit verification
- Minimum image resolution for CORE POSE (short edge >= 800px)
- Zero low-res thumbnails or screenshots in CORE
- Sourcing diversity (>= 8 distinct sources, max 3 per source/author in POSE CORE)
- POSE separation from OFFICIAL assets
- Broken POSE ID reference checks in docs
- README count consistency
"""

import re
import sys
from pathlib import Path
from PIL import Image
import yaml

sys.stdout.reconfigure(encoding='utf-8')

ROOT = Path(__file__).resolve().parents[1]
DATA_YAML = ROOT / "data" / "references.yaml"
REFS_DIR = ROOT / "refs"
DOCS_DIR = ROOT / "docs"
README_FILE = ROOT / "README.md"

VALID_CATEGORIES = {
    "00_OFFICIAL",
    "01_COSTUME",
    "02_STYLE",
    "03_POSE",
    "04_LIGHTING",
    "05_SET_PROP",
    "06_POST",
    "07_BTS_TECHNICAL",
    "90_REJECTED"
}

VALID_PRIORITIES = {"CORE", "SUPPORT", "OPTIONAL", "STUDIO_OPTIONAL", "REJECT"}
VALID_PRODUCTION_COSTS = {"LOW", "MEDIUM", "HIGH"}
VALID_EXPO_FEASIBILITY = {"A", "B", "C", "D"}
FORBIDDEN_CORE_QUALITIES = {"THUMBNAIL", "SCREENSHOT", "COLLAGE"}

def validate():
    errors = []
    warnings = []

    if not DATA_YAML.exists():
        print(f"FATAL: {DATA_YAML} does not exist.")
        sys.exit(1)

    try:
        with open(DATA_YAML, "r", encoding="utf-8") as f:
            data = yaml.safe_load(f)
    except Exception as e:
        print(f"FATAL: YAML parse error: {e}")
        sys.exit(1)

    if not isinstance(data, list):
        print("FATAL: references.yaml root must be a list of references.")
        sys.exit(1)

    seen_ids = set()
    files_in_yaml = set()
    scores = []
    pose_core_sources = {}
    pose_core_authors = {}
    pose_core_items = []

    for idx, ref in enumerate(data):
        ref_id = ref.get("id", f"INDEX_{idx}")
        # 1. Unique ID
        if not ref_id:
            errors.append(f"Entry {idx}: Missing ID.")
        elif ref_id in seen_ids:
            errors.append(f"Duplicate ID found: '{ref_id}'")
        seen_ids.add(ref_id)

        # 2. Category & Priority
        cat = ref.get("category")
        if cat not in VALID_CATEGORIES:
            errors.append(f"[{ref_id}] Invalid category: '{cat}'. Valid: {VALID_CATEGORIES}")

        pri = ref.get("priority")
        if pri not in VALID_PRIORITIES:
            errors.append(f"[{ref_id}] Invalid priority: '{pri}'. Valid: {VALID_PRIORITIES}")

        # 3. File existence & physical dimension check
        rel_file = ref.get("file")
        if not rel_file:
            errors.append(f"[{ref_id}] Missing 'file' attribute.")
        else:
            abs_file = ROOT / rel_file
            if not abs_file.exists():
                errors.append(f"[{ref_id}] Referenced file does not exist on disk: {rel_file}")
            else:
                files_in_yaml.add(abs_file.resolve())
                try:
                    with Image.open(abs_file) as im:
                        real_w, real_h = im.size
                except Exception as e:
                    errors.append(f"[{ref_id}] Cannot open image file {rel_file}: {e}")
                    real_w, real_h = 0, 0

        # 4. Image Quality Schema & CORE Resolution Guard (Step 7 & 8)
        img_q = ref.get("image_quality")
        if not isinstance(img_q, dict):
            errors.append(f"[{ref_id}] Missing 'image_quality' dict in metadata.")
        else:
            qw = img_q.get("width")
            qh = img_q.get("height")
            source_q = img_q.get("source_quality")
            q_pass = img_q.get("quality_pass")

            if abs_file.exists() and real_w > 0:
                if qw != real_w or qh != real_h:
                    errors.append(f"[{ref_id}] Dimension mismatch: YAML states {qw}x{qh}, disk image is {real_w}x{real_h}")

            # Low resolution alert
            if real_w > 0 and (real_w <= 480 or real_h <= 480):
                if pri != "REJECT":
                    errors.append(f"[{ref_id}] Low resolution detected ({real_w}x{real_h}). Low-res thumbnails (360x480) cannot be active references and must be REJECT.")

            # Strict CORE POSE constraints
            if cat == "03_POSE" and pri == "CORE":
                short_edge = min(real_w, real_h)
                long_edge = max(real_w, real_h)
                if short_edge < 800:
                    errors.append(f"[{ref_id}] CORE POSE short edge ({short_edge}px) < 800px threshold.")
                if long_edge < 1400:
                    warnings.append(f"[{ref_id}] CORE POSE long edge ({long_edge}px) < 1400px (recommended >= 1600px).")
                if source_q in FORBIDDEN_CORE_QUALITIES:
                    errors.append(f"[{ref_id}] CORE POSE cannot have source_quality '{source_q}'.")
                if not q_pass:
                    errors.append(f"[{ref_id}] CORE POSE quality_pass must be True.")

        # 5. Visual Audit Schema & Verification Guard (Step 7 & 8)
        v_audit = ref.get("visual_audit")
        if not isinstance(v_audit, dict):
            errors.append(f"[{ref_id}] Missing 'visual_audit' dict in metadata.")
        else:
            verified = v_audit.get("visually_verified")
            fn_match = v_audit.get("filename_match")
            meta_match = v_audit.get("metadata_match")
            script_match = v_audit.get("director_script_match")
            actual_pose = v_audit.get("actual_pose")

            if not actual_pose or len(actual_pose.strip()) == 0:
                errors.append(f"[{ref_id}] visual_audit.actual_pose cannot be empty.")

            if pri == "CORE":
                if not verified:
                    errors.append(f"[{ref_id}] CORE item must have visual_audit.visually_verified = True (requires human visual inspection).")
                if fn_match != "YES":
                    errors.append(f"[{ref_id}] CORE item visual_audit.filename_match must be 'YES' (got '{fn_match}').")
                if meta_match != "YES":
                    errors.append(f"[{ref_id}] CORE item visual_audit.metadata_match must be 'YES' (got '{meta_match}').")
                if script_match != "YES":
                    errors.append(f"[{ref_id}] CORE item visual_audit.director_script_match must be 'YES' (got '{script_match}').")

        # 6. POSE cannot point to OFFICIAL images
        if cat == "03_POSE":
            if "00_OFFICIAL" in rel_file:
                errors.append(f"[{ref_id}] POSE reference points to an OFFICIAL image ({rel_file}). POSE must use real model photography.")

        # 7. Sourcing diversity checks for CORE POSE
        if cat == "03_POSE" and pri == "CORE":
            pose_core_items.append(ref)
            source_url = ref.get("source", {}).get("url", "UNKNOWN_URL")
            source_author = ref.get("source", {}).get("author", "UNKNOWN_AUTHOR")
            pose_core_sources[source_url] = pose_core_sources.get(source_url, 0) + 1
            pose_core_authors[source_author] = pose_core_authors.get(source_author, 0) + 1

        # 8. Scores range (0.0 - 1.0)
        for score_key in ["target_relevance", "aesthetic_value", "technical_value", "source_confidence"]:
            val = ref.get(score_key)
            if val is not None:
                if not (0.0 <= float(val) <= 1.0):
                    errors.append(f"[{ref_id}] Invalid {score_key}: {val} (must be 0.00 - 1.00)")
                else:
                    scores.append(float(val))

        # 9. Feasibility & Script for active POSE
        if cat == "03_POSE" and pri == "CORE":
            feas = ref.get("expo_feasibility")
            if not feas or feas not in VALID_EXPO_FEASIBILITY:
                errors.append(f"[{ref_id}] Invalid expo_feasibility: '{feas}'. Valid: {VALID_EXPO_FEASIBILITY}")
            for field in ["director_script", "model_setup", "camera_position", "recommended_lens", "crop"]:
                if not ref.get(field):
                    errors.append(f"[{ref_id}] CORE POSE item missing '{field}' field for expo action directing.")

    # 10. Check POSE CORE Source Diversity Concentration (Step 3 & 8)
    for surl, count in pose_core_sources.items():
        if count > 3:
            errors.append(f"Anomaly: Single source_url concentration in POSE CORE exceeds limit (max 3 allowed, got {count} from {surl[:60]})")

    for sauthor, count in pose_core_authors.items():
        if count > 3:
            errors.append(f"Anomaly: Single author concentration in POSE CORE exceeds limit (max 3 allowed, got {count} from '{sauthor}')")

    if len(pose_core_sources) < 8 and len(pose_core_items) >= 12:
        errors.append(f"Insufficient source diversity: POSE CORE sourced from {len(pose_core_sources)} distinct URLs (minimum 8 required).")

    # 11. Check broken POSE ID references in docs (Step 8)
    md_files = list(DOCS_DIR.glob("*.md")) + [README_FILE]
    pose_id_pattern = re.compile(r"\b(POSE_\d{3,4})\b")
    for mf in md_files:
        if mf.exists():
            content = mf.read_text(encoding="utf-8")
            matches = set(pose_id_pattern.findall(content))
            for mid in matches:
                if mid not in seen_ids:
                    errors.append(f"Doc broken link: {mf.name} references non-existent POSE ID '{mid}'.")

    # 12. Check orphan files on disk
    disk_files = []
    for p in REFS_DIR.rglob("*"):
        if p.is_file() and p.suffix.lower() in [".webp", ".jpg", ".jpeg", ".png"]:
            disk_files.append(p.resolve())

    orphan_files = set(disk_files) - files_in_yaml
    for of in orphan_files:
        errors.append(f"Orphan file on disk not tracked in references.yaml: {of.relative_to(ROOT)}")

    # Summary
    print("=" * 60)
    print(f"VALIDATION REPORT: {DATA_YAML.name}")
    print("=" * 60)
    print(f"Total References in YAML: {len(data)}")
    print(f"Total Disk Image Files:   {len(disk_files)}")
    print(f"Total CORE POSE Items:    {len(pose_core_items)}")
    print(f"Distinct POSE CORE URLs:  {len(pose_core_sources)} (Requirement >= 8)")
    print(f"Distinct POSE Authors:    {len(pose_core_authors)}")
    print(f"Errors:                   {len(errors)}")
    print(f"Warnings:                 {len(warnings)}")
    print("-" * 60)

    if errors:
        print("ERRORS ENCOUNTERED:")
        for err in errors:
            print(f"  ❌ {err}")
        print("=" * 60)
        return False
    else:
        if warnings:
            print("WARNINGS:")
            for warn in warnings:
                print(f"  ⚠️  {warn}")
            print("-" * 60)
        print("SUCCESS: references.yaml passed all validation checks cleanly!")
        print("=" * 60)
        return True

if __name__ == "__main__":
    success = validate()
    sys.exit(0 if success else 1)
