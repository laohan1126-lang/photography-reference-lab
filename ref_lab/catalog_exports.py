"""Owned, refreshable browsing copies in the legacy exports directory."""
from __future__ import annotations

import html
import json
import os
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
from urllib.parse import quote

from .collection_history import _is_link_or_junction
from .local_catalog import (
    GENERATOR_ID as CATALOG_GENERATOR_ID,
    CatalogError,
    SHA_RE,
    _assert_no_links,
    _atomic_bytes,
    _atomic_json,
    _canonical_group,
    _inside,
    _load_owned_manifest,
    _owned_write,
    _relative_owned,
    _safe_existing_file,
    _safe_name,
    _same_path,
    _sha_file,
)


EXPORT_GENERATOR_ID = "photography-reference-lab/catalog-exports"
EXPORT_SCHEMA = 1
SETTINGS_FILE = "export-settings.json"
MARKER_FILE = "export-marker.json"
MANIFEST_FILE = "manifest.json"
INDEX_FILE = "index.html"


def _load_json(path: Path, label: str) -> dict:
    if _is_link_or_junction(path) or not path.is_file():
        raise CatalogError(f"{label}不存在或不是普通文件：{path}")
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError) as exc:
        raise CatalogError(f"{label}无法读取：{path}") from exc
    if not isinstance(payload, dict):
        raise CatalogError(f"{label}格式无效：{path}")
    return payload


def _binding(*, repo_root: Path, data_dir: Path, catalog_root: Path, character: str) -> dict:
    return {"schema": EXPORT_SCHEMA, "generator": EXPORT_GENERATOR_ID,
            "repo_root": str(repo_root), "data_dir": str(data_dir),
            "catalog_root": str(catalog_root), "character": character}


def _export_paths(catalog_root: Path, data_dir: Path) -> tuple[Path, dict]:
    catalog_root = catalog_root.resolve(strict=True)
    data_dir = data_dir.resolve(strict=True)
    raw = _load_json(catalog_root / MANIFEST_FILE, "图册 manifest")
    repo_text = str(raw.get("repo_root") or "")
    if raw.get("generator") != CATALOG_GENERATOR_ID or not repo_text:
        raise CatalogError("图册 manifest 未绑定当前 local_catalog 生成器")
    try:
        repo_root = Path(repo_text).resolve(strict=True)
    except OSError as exc:
        raise CatalogError("图册 manifest 绑定的仓库不存在") from exc
    if (not _inside(catalog_root, repo_root) or not _inside(data_dir, repo_root)
            or not _same_path(catalog_root.parent, data_dir)):
        raise CatalogError("图册目录与资料目录必须属于 manifest 绑定的同一仓库")
    _assert_no_links(catalog_root, repo_root)
    _assert_no_links(data_dir, repo_root)
    manifest, _ = _load_owned_manifest(catalog_root, repo_root)
    if not isinstance(manifest.get("items"), list) or not isinstance(manifest.get("roles"), list):
        raise CatalogError("图册 manifest 缺少 items/roles")
    return catalog_root, manifest


def _load_export_ownership(target: Path, binding: dict) -> tuple[dict, dict]:
    marker = target / MARKER_FILE
    manifest = target / MANIFEST_FILE
    if not target.exists():
        return {}, {}
    _assert_no_links(target, target.parent)
    if not target.is_dir():
        raise CatalogError(f"导出路径不是目录：{target}")
    entries = list(target.iterdir())
    if not entries:
        return {}, {}
    if not marker.is_file():
        raise CatalogError("导出目录非空但缺少所有权 marker；拒绝接管")
    marker_data = _load_json(marker, "导出 marker")
    if marker_data != binding:
        raise CatalogError("导出 marker 与当前仓库、图册或角色不一致")
    if not manifest.is_file():
        if set(entries) == {marker}:
            return {}, {}
        raise CatalogError("导出目录缺少 manifest；拒绝覆盖")
    payload = _load_json(manifest, "导出 manifest")
    if (payload.get("schema") != EXPORT_SCHEMA or payload.get("generator") != EXPORT_GENERATOR_ID
            or any(payload.get(key) != value for key, value in binding.items() if key != "generator" and key != "schema")
            or not isinstance(payload.get("owned_files"), dict)):
        raise CatalogError("导出 manifest 所有权或绑定校验失败")
    return marker_data, payload


def _role_items(manifest: dict, character: str) -> tuple[str, str, int, list[dict]]:
    group = _canonical_group(character.strip())
    role = next((row for row in manifest["roles"]
                 if isinstance(row, dict) and row.get("group") == group), None)
    if role is None:
        raise CatalogError(f"图册中没有角色组：{character}")
    folder_text = str(role.get("folder") or "").replace("\\", "/")
    folder = _relative_owned(folder_text)
    if folder is None or len(folder.parts) != 2 or folder.parts[0] != "角色项目":
        raise CatalogError("图册角色目录路径无效")
    count = role.get("count")
    if isinstance(count, bool) or not isinstance(count, int) or count < 0:
        raise CatalogError("图册角色数量无效")
    items = [item for item in manifest["items"] if isinstance(item, dict)
             and f" {group} " in f" {item.get('role_groups') or ''} "]
    if len(items) != count:
        raise CatalogError(f"图册角色数量与真实归属不一致：{group}（{count} != {len(items)}）")
    return group, folder.as_posix(), count, items


def _verified_sources(manifest: dict, items: list[dict], folder: str, data_dir: Path) -> list[dict]:
    owned = manifest["owned_files"]
    sources = []
    names: set[str] = set()
    for item in items:
        role_paths = item.get("role_paths")
        role_text = role_paths.get(folder) if isinstance(role_paths, dict) else ""
        browse_text = item.get("browse_path")
        relative_text = role_text or browse_text
        if not relative_text:
            raise CatalogError(f"角色图片缺少可导出的派生预览：{item.get('sha')}")
        relative = _relative_owned(str(relative_text))
        expected = str(item.get("preview_sha256") or "").lower()
        item_sha = str(item.get("sha") or "").lower()
        expected_parent = folder if role_text else "images"
        expected_depth = 3 if role_text else 2
        if (relative is None or len(relative.parts) != expected_depth or relative.parent.as_posix() != expected_parent
                or relative.suffix.lower() != ".jpg" or not SHA_RE.fullmatch(expected)
                or not SHA_RE.fullmatch(item_sha) or owned.get(relative.as_posix()) != expected):
            raise CatalogError(f"角色图片路径、SHA 或所有权无效：{relative_text}")
        if relative.name.casefold() in names:
            raise CatalogError(f"角色导出文件名重复：{relative.name}")
        names.add(relative.name.casefold())
        source = _safe_existing_file(Path(manifest["_catalog_root"]) / relative, Path(manifest["_catalog_root"]))
        if source is None or _inside(source, data_dir / "assets") or _sha_file(source) != expected:
            raise CatalogError(f"角色派生 JPG 越界、链接、原件或 hash 不符：{relative_text}")
        original_text = str(item.get("original_path") or "")
        if original_text:
            original = Path(original_text)
            if original.is_file():
                try:
                    if os.path.samefile(source, original):
                        raise CatalogError(f"角色派生 JPG 与原图共享文件身份：{relative_text}")
                except OSError as exc:
                    raise CatalogError(f"无法核对角色派生 JPG 文件身份：{relative_text}") from exc
        sources.append({"source": source, "relative": relative.as_posix(), "filename": relative.name,
                        "sha": expected, "item": item})
    return sources


def _index(character: str, sources: list[dict]) -> bytes:
    cards = []
    for row in sources:
        item = row["item"]
        href = html.escape(quote(row["export_name"], safe=""), quote=True)
        title = html.escape(str(item.get("title") or row["sha"][:12]))
        status = html.escape("用户文件已保留" if row.get("protected") else str(item.get("status") or ""))
        cards.append(f'<article><a href="{href}"><img loading="lazy" src="{href}" alt="{title}"></a>'
                     f'<h2>{title}</h2><p>{status}</p><small>{row["sha"][:12]}</small></article>')
    page = f'''<!doctype html><html lang="zh-CN"><meta charset="utf-8"><meta name="viewport" content="width=device-width">
<title>{html.escape(character)} · 全部下载</title><style>
body{{max-width:1400px;margin:auto;padding:28px;background:#f4f1e9;color:#20221f;font:15px/1.5 "Microsoft YaHei",sans-serif}}
header{{margin-bottom:22px}}h1{{margin:0 0 6px}}p{{color:#6a7068}}main{{display:grid;grid-template-columns:repeat(auto-fill,minmax(180px,1fr));gap:14px}}
article{{background:#fffdf8;border:1px solid #d8d3c7;padding:10px;min-width:0}}img{{display:block;width:100%;aspect-ratio:4/5;object-fit:contain;background:#e6e1d7}}
h2{{font-size:14px;overflow-wrap:anywhere;margin:10px 0 4px}}article p{{margin:0}}@media(max-width:520px){{body{{padding:12px}}main{{grid-template-columns:repeat(2,minmax(0,1fr));gap:8px}}}}
</style><header><h1>{html.escape(character)} · 全部下载</h1><p>共 {len(sources)} 张；这些是图册派生的浏览副本，不是相机原图。</p></header>
<main>{''.join(cards)}</main></html>'''
    return page.encode("utf-8")


def export_character_catalog(catalog_root: Path, data_dir: Path, character: str) -> dict:
    """Copy one manifest role's verified JPGs into its legacy all-downloads folder."""
    catalog_root, manifest = _export_paths(Path(catalog_root), Path(data_dir))
    group, folder, _, items = _role_items(manifest, character)
    data_root = Path(data_dir).resolve(strict=True)
    repo_root = Path(manifest["repo_root"])
    sources = _verified_sources({**manifest, "_catalog_root": str(catalog_root)}, items, folder, data_root)
    target = data_root / "exports" / _safe_name(group, limit=80) / "全部下载"
    if target.exists() and _is_link_or_junction(target):
        raise CatalogError(f"导出目录不能是链接或重解析点：{target}")
    binding = _binding(repo_root=repo_root, data_dir=data_root, catalog_root=catalog_root, character=group)
    _, previous = _load_export_ownership(target, binding)
    _assert_no_links(target, data_root)
    target.mkdir(parents=True, exist_ok=True)
    prior_files = previous.get("owned_files", {}) if isinstance(previous.get("owned_files"), dict) else {}
    owned_files: dict[str, str] = {}
    errors: list[dict] = []
    retained = copied = removed = 0
    desired: set[str] = set()
    rows = []
    for row in sources:
        name = row["filename"]
        destination = target / name
        conflict = False
        if destination.exists():
            if (_is_link_or_junction(destination) or not destination.is_file()
                    or prior_files.get(name) != row["sha"] or _sha_file(destination) != row["sha"]
                    or os.path.samefile(row["source"], destination)):
                errors.append({"kind": "catalog_export_user_path_conflict", "path": name,
                               "reason": "用户新增、修改或替换了导出文件，保留原文件"})
                conflict = True
            else:
                retained += 1
        if conflict:
            source_path = Path(name)
            name = f"{source_path.stem}.ref-lab-{row['sha'][:12]}{source_path.suffix}"
            destination = target / name
            if destination.exists():
                if (_is_link_or_junction(destination) or not destination.is_file()
                        or prior_files.get(name) != row["sha"] or _sha_file(destination) != row["sha"]
                        or os.path.samefile(row["source"], destination)):
                    errors.append({"kind": "catalog_export_user_path_conflict", "path": name,
                                   "reason": "备用导出路径也被用户占用或修改，保留原文件"})
                    rows.append({**row, "export_name": name, "protected": True})
                    desired.add(name)
                    continue
                retained += 1
        if not destination.exists():
            _atomic_bytes(destination, row["source"].read_bytes())
            if os.path.samefile(row["source"], destination) or _sha_file(destination) != row["sha"]:
                raise CatalogError(f"独立导出复制校验失败：{name}")
            copied += 1
        desired.add(name)
        owned_files[name] = row["sha"]
        rows.append({**row, "export_name": name})
    index = _index(group, rows)
    digest = _owned_write(target, INDEX_FILE, index, prior_files, errors, recoverable=prior_files.get(INDEX_FILE, ""))
    if digest:
        owned_files[INDEX_FILE] = digest
    conflicted = {error["path"] for error in errors if error["kind"] == "catalog_export_user_path_conflict"}
    stale = set(prior_files) - desired - {INDEX_FILE}
    for relative_name in sorted(stale):
        relative = _relative_owned(relative_name)
        if relative is None or len(relative.parts) != 1:
            errors.append({"kind": "catalog_export_invalid_owned_path", "path": relative_name})
            continue
        candidate = target / relative
        if not candidate.exists():
            continue
        if relative_name in conflicted or not candidate.is_file():
            continue
        if (_is_link_or_junction(candidate)
                or _sha_file(candidate) != prior_files.get(relative_name)):
            errors.append({"kind": "catalog_export_user_path_conflict", "path": relative_name,
                           "reason": "过期生成文件已被用户修改，保留"})
            continue
        candidate.unlink()
        removed += 1
    known = {MARKER_FILE, MANIFEST_FILE, INDEX_FILE, *desired, *prior_files, *conflicted}
    for child in target.iterdir():
        if child.name not in known:
            errors.append({"kind": "catalog_export_user_file_preserved", "path": child.name,
                           "reason": "用户混入的文件不纳入所有权，保留"})
    manifest_payload = {**binding, "generated_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
                        "catalog_manifest_generator": CATALOG_GENERATOR_ID,
                        "summary": {"images": len(sources), "exported": len(rows),
                                    "copied": copied, "retained": retained, "removed": removed},
                        "items": [{"sha": row["sha"], "filename": row["export_name"],
                                   "href": quote(row["export_name"], safe=""), "source": row["relative"],
                                   "title": row["item"].get("title"), "status": row["item"].get("status")}
                                  for row in rows],
                        "owned_files": owned_files, "errors": errors}
    _atomic_json(target / MANIFEST_FILE, manifest_payload)
    _atomic_json(target / MARKER_FILE, binding)
    return {"ok": not errors, "character": group, "export_dir": str(target),
            "index": str(target / INDEX_FILE), "manifest": str(target / MANIFEST_FILE),
            "images": len(sources), "exported": len(rows), "copied": copied,
            "retained": retained, "removed": removed, "errors": errors}


def load_export_settings(catalog_root: Path) -> list[str]:
    path = Path(catalog_root) / SETTINGS_FILE
    if not path.exists():
        return []
    payload = _load_json(path, "导出设置")
    characters = payload.get("characters")
    if (payload.get("schema") != EXPORT_SCHEMA or payload.get("generator") != EXPORT_GENERATOR_ID
            or not isinstance(characters, list) or not all(isinstance(value, str) and value.strip() for value in characters)):
        raise CatalogError("导出设置格式无效")
    return list(dict.fromkeys(_canonical_group(value.strip()) for value in characters))


def save_export_settings(catalog_root: Path, characters: list[str]) -> Path:
    if not characters:
        raise CatalogError("至少登记一个导出角色")
    path = Path(catalog_root) / SETTINGS_FILE
    payload: Any = {"schema": EXPORT_SCHEMA, "generator": EXPORT_GENERATOR_ID,
                    "characters": list(dict.fromkeys(_canonical_group(value.strip()) for value in characters))}
    _atomic_json(path, payload)
    return path
