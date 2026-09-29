"""Explicit, conservative cleanup of old unreferenced rejections.

Dry-run is the default. Never touches repository history, migration backups, active
inspiration, any non-rejected project link, notes, or an unfinished analysis job.
Metadata and choices survive; restoring purged pixels requires reimporting bytes.
"""
from __future__ import annotations

import json
from datetime import datetime, timedelta, timezone
from .db import encode, now
from .service import Library


def cleanup(library: Library, *, days: int = 30, apply: bool = False) -> dict:
    if days < 7:
        raise ValueError("回收等待期不得少于 7 天")
    cutoff = datetime.now(timezone.utc) - timedelta(days=days)
    report = {"dry_run": not apply, "retention_days": days, "eligible": [], "purged": [], "protected": 0, "errors": []}
    with library.db.transaction() as con:
        assets = [json.loads(r[0]) for r in con.execute("SELECT data FROM assets")]
        refs = [json.loads(r[0]) for r in con.execute("SELECT data FROM refs")]
        notes = [json.loads(r[0]) for r in con.execute("SELECT data FROM notes")]
        jobs = [json.loads(r[0]) for r in con.execute("SELECT data FROM jobs WHERE kind='analysis' AND status IN ('blocked','queued','running','failed')")]
        active = {r[0] for r in con.execute("SELECT asset_sha FROM inspirations WHERE active=1")}
        by_asset: dict[str, list[dict]] = {}
        for ref in refs:
            by_asset.setdefault(ref.get("asset_sha"), []).append(ref)
        for asset in assets:
            sha = asset["id"]
            if asset.get("storage_status") == "purged":
                continue
            links = by_asset.get(sha, [])
            favorites = [json.loads(r[0]) for r in con.execute("SELECT data FROM inspirations WHERE asset_sha=?", (sha,))]
            timestamps = [r.get("rejected_at") for r in links] + [i.get("removed_at") for i in favorites]
            safe = bool(timestamps) and all(timestamps) and all(r["decision"] == "reject" for r in links)
            try:
                safe = safe and all(datetime.fromisoformat(t) < cutoff for t in timestamps)
            except (ValueError, TypeError):
                safe = False
            safe = safe and sha not in active
            safe = safe and not any(sha in n.get("body", "") or sha in n.get("image_assets", []) for n in notes)
            safe = safe and not any(sha == s.get("asset_sha") for j in jobs for s in j.get("snapshots", {}).values())
            if not safe:
                report["protected"] += 1
                continue
            paths = [library.assets.path(asset, v) for v in ("original", "preview", "thumb")]
            root = library.assets.root.resolve()
            if any(not p.resolve().is_relative_to(root) for p in paths):
                report["errors"].append({"sha": sha, "error": "Unsafe asset path"})
                continue
            report["eligible"].append({"sha": sha, "bytes": asset["bytes"], "references": len(links)})
            if not apply:
                continue
            try:
                for path in paths:
                    path.unlink(missing_ok=True)
                asset.update(storage_status="purged", purged_at=now())
                report["purged"].append(sha)
            except OSError:
                asset.update(storage_status="purge_failed", integrity="failed")
                report["errors"].append({"sha": sha, "error": "Partial cleanup; reimport exact bytes to recover"})
            con.execute("UPDATE assets SET data=? WHERE id=?", (encode(asset), sha))
            library.db.event(con, None, sha, "asset." + asset["storage_status"], {"retention_days": days}, "cleanup")
    return report
