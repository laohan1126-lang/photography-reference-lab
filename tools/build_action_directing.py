"""Build the additive action-directing course payload from canonical research only.

The course is a second, read-only teaching payload. It never rewrites the base
bundle, the skill tree, personal records or the base gateway catalogue: it is
merged into the existing reader at boot. Nothing is invented here — without the
reviewed `COURSE.json` this builder fails loudly instead of emitting a
placeholder chapter.
"""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import sys

if __package__ in {None, ""}:
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from ref_lab.action_directing_media import ACTION_DIRECTING_SOURCE_CASE_MEDIA
from tools.validate_learning_gateways import validate_gateways

ROOT = Path(__file__).resolve().parents[1]
RESEARCH = ROOT / "docs/research/photography-atlas"
# The course is its own directory; the three files below stay the base atlas's files and
# are read where they live. Nothing here copies them into the course directory.
COURSE_DIRECTORY = RESEARCH / "action-directing"
BASE_FILES = ("SKILL_TREE.json", "GATEWAYS.json", "LEARNING_CONTENT.json")
BASE_HINT = ("--base-directory points at the directory holding "
             f"{', '.join(BASE_FILES)} (default {RESEARCH})")
# Fixed bundle id. It is also the course entry id, so /learning?course=action-directing-module
# keeps working without a second lookup table.
EXTENSION = "action-directing-module"
COURSE_FILE = "COURSE.json"
# Only teaching payload fields may travel in an extension. Skills, modules,
# domains, sources, state and tutorials belong to the base bundle alone.
ALLOWED_CATALOG_KEYS = {"schema_version", "meta", "gateways", "sources"}
ALLOWED_META_KEYS = {"label", "note"}
LABEL_LIMIT = 60
META_LIMIT = 160


def read_json(path: Path, label: str, hint: str = "") -> dict:
    if not path.is_file():
        raise ValueError(
            f"{label} not found at {path}. The action-directing payload cannot be built "
            f"without reviewed research; nothing is generated and no placeholder course is written."
            + (f" {hint}" if hint else "")
        )
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as error:
        raise ValueError(f"{label} at {path} is not valid JSON: {error}") from error
    if not isinstance(value, dict):
        raise ValueError(f"{label} at {path} must contain a JSON object.")
    return value


def _short_text(value, limit: int) -> bool:
    return isinstance(value, str) and bool(value.strip()) and len(value.strip()) <= limit


def shape_errors(catalog: dict) -> list[str]:
    errors = []
    if catalog.get("schema_version") != 1:
        errors.append("Course payload requires schema_version=1")
    if not isinstance(catalog.get("gateways"), list) or not catalog["gateways"]:
        errors.append("Course payload requires a non-empty gateways list")
    if not isinstance(catalog.get("sources"), list) or not catalog["sources"]:
        errors.append("Course payload requires a non-empty sources list")
    extra = set(catalog) - ALLOWED_CATALOG_KEYS
    if extra:
        errors.append(f"Course payload may not carry base atlas fields: {sorted(extra)}")
    meta = catalog.get("meta")
    if meta is not None:
        if not isinstance(meta, dict):
            errors.append("Course meta must be an object")
        else:
            unknown = set(meta) - ALLOWED_META_KEYS
            if unknown:
                errors.append(f"Unknown course meta fields: {sorted(unknown)}")
            for key, value in meta.items():
                if not _short_text(value, META_LIMIT):
                    errors.append(f"Course meta {key} must be short non-empty text")
    for gateway in catalog.get("gateways") or []:
        if not isinstance(gateway, dict):
            errors.append("Course gateway entries must be objects")
            continue
        # A course payload may only add read-only chapters; conceptual gateways
        # stay in the base catalogue with their self-assessment behaviour.
        if gateway.get("kind") != "course":
            errors.append(f"Unsupported course kind: {gateway.get('kind')!r} ({gateway.get('id')})")
        if "label" in gateway and not _short_text(gateway.get("label"), LABEL_LIMIT):
            errors.append(f"Course label must be short non-empty text: {gateway.get('id')}")
    return errors


def collision_errors(catalog: dict, base_gateways: list, base_sources: list) -> list[str]:
    errors = []
    gateway_ids = {g.get('id') for g in base_gateways if isinstance(g, dict)}
    source_ids = {s.get('id') for s in base_sources if isinstance(s, dict)}
    seen_gateways, seen_sources = set(), set()
    for gateway in catalog['gateways']:
        ident = gateway.get('id')
        if ident in seen_gateways:
            errors.append(f"Duplicate course gateway ID: {ident}")
        seen_gateways.add(ident)
        if ident in gateway_ids:
            errors.append(f"Course gateway ID collides with the base catalogue: {ident}")
    for source in catalog['sources']:
        ident = source.get('id')
        if ident in seen_sources:
            errors.append(f"Duplicate course source ID: {ident}")
        seen_sources.add(ident)
        if ident in source_ids:
            errors.append(f"Course source ID collides with the base catalogue: {ident}")
    if not any(g.get('id') == EXTENSION for g in catalog['gateways']):
        errors.append(f"Course payload must contain the {EXTENSION} entry used by /learning?course={EXTENSION}")
    return errors


def build_payload(directory: Path, base_directory: Path | None = None) -> dict:
    """Build the payload from the reviewed course file plus the base research files.

    `base_directory` defaults to the course directory itself, which keeps a fixture or a
    flat layout working; the CLI names the real base directory, where those three files
    are owned by the base atlas.
    """
    course = read_json(directory / COURSE_FILE, "Canonical action-directing course")
    base_dir = Path(base_directory) if base_directory is not None else Path(directory)
    hint = BASE_HINT if base_directory is not None else \
        f"Pass {BASE_HINT} if these files live beside the base atlas rather than here."
    tree = read_json(base_dir / "SKILL_TREE.json", "Canonical skill tree", hint)
    base = read_json(base_dir / "GATEWAYS.json", "Canonical base gateway catalogue", hint)
    content_path = base_dir / "LEARNING_CONTENT.json"
    content = read_json(content_path, "Canonical learning content", hint) if content_path.is_file() else None

    errors = shape_errors(course)
    if errors:
        raise ValueError("Action-directing course integrity failed: " + "; ".join(errors))
    if not isinstance(base.get('gateways'), list) or not isinstance(base.get('sources'), list):
        raise ValueError(
            "Canonical base gateway catalogue has no gateways/sources lists; "
            "collisions with the base bundle cannot be checked, so nothing is written."
        )
    errors = collision_errors(course, base['gateways'], base['sources'])
    if errors:
        raise ValueError("Action-directing course integrity failed: " + "; ".join(errors))
    errors = validate_gateways(course, tree, content, extra_source_media=ACTION_DIRECTING_SOURCE_CASE_MEDIA)
    if errors:
        raise ValueError("Action-directing course integrity failed: " + "; ".join(errors[:20]))
    digest = hashlib.sha256(json.dumps(course, ensure_ascii=False, sort_keys=True,
                                       separators=(",", ":")).encode("utf-8")).hexdigest()
    return {"schema_version": 1, "extension": EXTENSION, "content_digest": digest,
            "meta": course.get("meta") or {},
            "gateways": course["gateways"], "gateway_sources": course["sources"]}


def serialized(payload: dict) -> str:
    # Sorted keys and fixed separators keep the shipped bytes reproducible.
    return json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True) + "\n"


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--directory", type=Path, default=COURSE_DIRECTORY,
                        help="Course directory holding the canonical COURSE.json.")
    parser.add_argument("--base-directory", type=Path, default=RESEARCH,
                        help=f"Directory holding the base research files ({', '.join(BASE_FILES)}).")
    parser.add_argument("--output", type=Path, default=ROOT / "web/learning-action-directing.json")
    parser.add_argument("--write", action="store_true", help="Write the validated payload; default is read-only.")
    parser.add_argument("--check", action="store_true", help="Fail if the shipped payload differs from COURSE.json.")
    args = parser.parse_args()
    try:
        payload = build_payload(args.directory, args.base_directory)
    except ValueError as error:
        print(f"FAIL: {error}")
        return 1
    content = serialized(payload)
    if args.check and (not args.output.is_file() or args.output.read_text(encoding="utf-8") != content):
        print("FAIL: shipped action-directing payload differs from the canonical course")
        return 1
    if args.write:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(content, encoding="utf-8")
    print(json.dumps({"status": "PASS" if args.check else "WRITTEN" if args.write else "DRY_RUN",
                      "extension": payload["extension"], "courses": len(payload["gateways"]),
                      "sources": len(payload["gateway_sources"]),
                      "content_digest": payload["content_digest"]}, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
