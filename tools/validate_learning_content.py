"""Validate concise knowledge notes, their evidence and linked practice."""
from __future__ import annotations

import re
from urllib.parse import urlparse


_ID = re.compile(r"[a-z0-9][a-z0-9-]{0,79}\Z")
_SHA256 = re.compile(r"[0-9a-f]{64}\Z")


def _nonempty(value, *, limit: int = 500) -> bool:
    return isinstance(value, str) and bool(value.strip()) and len(value) <= limit


def _unique_strings(values, known: set[str] | None = None) -> bool:
    return (isinstance(values, list) and bool(values)
            and all(isinstance(value, str) and _ID.fullmatch(value) for value in values)
            and len(values) == len(set(values))
            and (known is None or set(values) <= known))


def _public_https(value) -> bool:
    if not isinstance(value, str) or "\\" in value:
        return False
    try:
        parsed = urlparse(value)
        return (parsed.scheme == "https" and bool(parsed.hostname)
                and not parsed.username and not parsed.password
                and parsed.hostname.lower() not in {"localhost", "127.0.0.1", "::1"})
    except ValueError:
        return False


def _short_list(value, *, minimum: int = 1, maximum: int = 8, limit: int = 300) -> bool:
    return (isinstance(value, list) and minimum <= len(value) <= maximum
            and all(_nonempty(item, limit=limit) for item in value))


def validate_learning_content(catalog: dict, tree: dict) -> list[str]:
    """Return integrity errors; this checks structure, not instructional quality."""
    errors: list[str] = []
    if not isinstance(catalog, dict) or type(catalog.get("schema_version")) is not int or catalog["schema_version"] != 1:
        return ["learning content: schema_version 1 object required"]
    fields = ("notes", "trainings", "sources", "media")
    if any(not isinstance(catalog.get(name), list) for name in fields):
        return ["learning content: notes, trainings, sources and media lists required"]
    if not isinstance(tree, dict) or not isinstance(tree.get("skills"), list):
        return ["learning content: skill tree required"]

    skills = {item.get("id") for item in tree["skills"] if isinstance(item, dict)}
    ids: set[str] = set()

    def check_id(item: dict, kind: str) -> str | None:
        ident = item.get("id")
        if not isinstance(ident, str) or not _ID.fullmatch(ident) or ident in ids:
            errors.append(f"{kind}: missing, invalid or duplicate id {ident!r}")
            return None
        ids.add(ident)
        return ident

    sources: dict[str, dict] = {}
    source_urls: set[str] = set()
    for source in catalog["sources"]:
        if not isinstance(source, dict):
            errors.append("source: object required")
            continue
        ident = check_id(source, "source")
        if ident is None:
            continue
        sources[ident] = source
        for name in ("author", "title", "inspection"):
            if not _nonempty(source.get(name), limit=800):
                errors.append(f"{ident}: source {name} required")
        url = source.get("url")
        if not _public_https(url):
            errors.append(f"{ident}: source must have a public HTTPS URL")
        elif url in source_urls:
            errors.append(f"{ident}: duplicate source URL")
        else:
            source_urls.add(url)

    media: dict[str, dict] = {}
    filenames: set[str] = set()
    for item in catalog["media"]:
        if not isinstance(item, dict):
            errors.append("media: object required")
            continue
        ident = check_id(item, "media")
        if ident is None:
            continue
        media[ident] = item
        sha = item.get("sha256")
        filename = item.get("filename")
        if (not isinstance(sha, str) or not _SHA256.fullmatch(sha)
                or filename not in {f"{sha}.jpg", f"{sha}.png"}):
            errors.append(f"{ident}: media must use its exact SHA-256 .jpg or .png filename")
        elif filename in filenames:
            errors.append(f"{ident}: duplicate media filename")
        else:
            filenames.add(filename)
        if item.get("source_id") not in sources:
            errors.append(f"{ident}: unknown media source")
        for name in ("position", "caption", "alt"):
            if not _nonempty(item.get(name), limit=500):
                errors.append(f"{ident}: media {name} required")

    notes: dict[str, dict] = {}
    for note in catalog["notes"]:
        if not isinstance(note, dict):
            errors.append("note: object required")
            continue
        ident = check_id(note, "note")
        if ident is None:
            continue
        notes[ident] = note
        for name, limit in (("title", 120), ("lead", 300), ("memory", 120)):
            if not _nonempty(note.get(name), limit=limit):
                errors.append(f"{ident}: note {name} required")
        mapped = note.get("skill_ids")
        if not _unique_strings(mapped, skills):
            errors.append(f"{ident}: note requires unique known skill_ids")
        if not _short_list(note.get("paragraphs"), maximum=6, limit=500):
            errors.append(f"{ident}: note requires concise paragraphs")
        media_ids = note.get("media_ids")
        if not _unique_strings(media_ids, set(media)):
            errors.append(f"{ident}: note media_ids must reference registered media")
        citations = note.get("citations")
        if not isinstance(citations, list) or not 1 <= len(citations) <= 8:
            errors.append(f"{ident}: note requires source citations")
            continue
        cited_sources: set[str] = set()
        for citation in citations:
            if not isinstance(citation, dict):
                errors.append(f"{ident}: citation object required")
                continue
            source_id = citation.get("source_id")
            if source_id not in sources:
                errors.append(f"{ident}: citation references unknown source")
            else:
                cited_sources.add(source_id)
            for name in ("position", "detail"):
                if not _nonempty(citation.get(name), limit=300):
                    errors.append(f"{ident}: citation {name} required")
        if isinstance(media_ids, list):
            for media_id in media_ids:
                entry = media.get(media_id)
                if entry and entry.get("source_id") not in cited_sources:
                    errors.append(f"{ident}: displayed media source must also be cited")

    for training in catalog["trainings"]:
        if not isinstance(training, dict):
            errors.append("training: object required")
            continue
        ident = check_id(training, "training")
        if ident is None:
            continue
        if not _nonempty(training.get("title"), limit=120):
            errors.append(f"{ident}: training title required")
        if not _unique_strings(training.get("skill_ids"), skills):
            errors.append(f"{ident}: training requires unique known skill_ids")
        if not _unique_strings(training.get("note_ids"), set(notes)):
            errors.append(f"{ident}: training must reference at least one known note")
        if training.get("basis") not in {"project_designed", "source_exercise"}:
            errors.append(f"{ident}: explicit training basis required")
        if not _short_list(training.get("steps"), maximum=8, limit=400):
            errors.append(f"{ident}: concise training steps required")
        if not _short_list(training.get("checks"), maximum=6, limit=300):
            errors.append(f"{ident}: concise observable checks required")

    return errors
