"""Check teaching recommendations without promoting them to research evidence."""
from __future__ import annotations

from tools.validate_photography_atlas import public_url


def validate_tutorials(catalog: dict, tree: dict, source_map: dict) -> list[str]:
    errors: list[str] = []
    if catalog.get("schema_version") != 1 or not isinstance(catalog.get("resources"), list):
        return ["tutorials: schema_version 1 and resources list required"]
    skills = {item["id"]: item for item in tree["skills"]}
    modules = {item["id"]: item for item in tree["modules"]}
    sources = {item["id"]: item for item in source_map["sources"]}
    ids, urls = set(), set()
    text_fields = ("id", "title", "original_title", "author", "language", "trust_reason",
                   "summary", "start_here", "study_task", "limitations")
    for item in catalog["resources"]:
        if not isinstance(item, dict):
            errors.append("tutorials: resource must be an object")
            continue
        ident = item.get("id", "unknown")
        if any(not isinstance(item.get(key), str) or not item[key].strip() for key in text_fields):
            errors.append(f"{ident}: missing tutorial guidance or attribution")
        if not isinstance(ident, str) or ident in ids:
            errors.append(f"{ident}: duplicate or invalid tutorial id")
            continue
        ids.add(ident)
        url = item.get("url")
        if not public_url(url):
            errors.append(f"{ident}: unsafe public URL")
        elif url in urls:
            errors.append(f"{ident}: duplicate tutorial URL")
        else:
            urls.add(url)
        if item.get("kind") not in {"article", "video", "course", "paper", "case_study"}:
            errors.append(f"{ident}: unknown learning material type")
        if item.get("access") not in {"free", "paid", "preview", "login_required"}:
            errors.append(f"{ident}: explicit access condition required")
        verification = item.get("verification", {})
        if (not isinstance(verification, dict) or not verification.get("checked_at")
                or not verification.get("locator")
                or verification.get("level") not in {"full_text", "page_and_description", "transcript", "watched"}):
            errors.append(f"{ident}: actual verification scope required")
        elif item.get("kind") == "video" and verification["level"] == "full_text":
            errors.append(f"{ident}: video must distinguish transcript, watched or page-only verification")
        sid = item.get("source_id")
        if sid is not None and (sid not in sources or sources[sid]["url"] != url):
            errors.append(f"{ident}: source identity/URL mismatch")
        mapped = item.get("skill_ids")
        if (not isinstance(mapped, list) or not mapped
                or any(not isinstance(value, str) or value not in skills for value in mapped)):
            errors.append(f"{ident}: explicit known skill mappings required")
            continue
        if len(mapped) != len(set(mapped)):
            errors.append(f"{ident}: duplicate skill mapping")
        domains = item.get("domain_ids")
        actual_domains = {modules[skills[value]["module_id"]]["domain_id"] for value in mapped}
        if not isinstance(domains, list) or set(domains) != actual_domains:
            errors.append(f"{ident}: domains must describe mapped skills exactly")
    return errors
