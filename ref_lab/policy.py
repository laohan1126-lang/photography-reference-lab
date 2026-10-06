"""Deterministic publication gates. Visual truth is supplied by a named reviewer, not inferred from queries."""
from __future__ import annotations

import hashlib
from urllib.parse import urlsplit
from .db import encode
from .identity import identity_digest

UNTRUSTED_EVIDENCE_PRODUCERS = {"vision-preflight-gate", "local_collection_adapter"}

def trusted_producer_sql(producer_path: str, data_column: str = "data") -> str:
    producers = ",".join("'" + p + "'" for p in sorted(UNTRUSTED_EVIDENCE_PRODUCERS))
    return f"COALESCE(json_extract({data_column},'$.{producer_path}'),'') NOT IN ({producers})"


def preflight_bound_sql(data_column: str = "data") -> str:
    return f"({trusted_producer_sql('preflight.producer', data_column)} AND json_extract({data_column},'$.preflight.asset_sha')=json_extract({data_column},'$.asset_sha') AND json_extract({data_column},'$.preflight.project_context')=json_extract({data_column},'$.preflight_context'))"


def preflight_filter_sql(data_column: str = "data") -> str:
    return f"(COALESCE(json_extract({data_column},'$.preflight_filtered'),0)=1 AND COALESCE({preflight_bound_sql(data_column)},0))"


def preflight_status_sql(data_column: str = "data") -> str:
    return f"CASE WHEN {preflight_bound_sql(data_column)} THEN COALESCE(json_extract({data_column},'$.preflight_status'),'unreviewed') ELSE 'unreviewed' END"


def review_kind_sql(data_column: str = "data") -> str:
    return f"CASE WHEN {trusted_producer_sql('review_producer', data_column)} AND json_extract({data_column},'$.review.asset_sha')=json_extract({data_column},'$.asset_sha') THEN COALESCE(json_extract({data_column},'$.review.kind'),'unknown') ELSE 'unknown' END"


def project_preflight(preflight: dict, *, current_asset_sha: str | None, current_context: str) -> dict:
    """Effective evidence binds its producer, current reference bytes and project inputs."""
    trusted = preflight.get("producer") not in UNTRUSTED_EVIDENCE_PRODUCERS
    if (trusted and current_asset_sha and preflight.get("asset_sha") == current_asset_sha
            and preflight.get("project_context") == current_context):
        return {**preflight, "effective": True, "evidence_status": "current"}
    return {"id": preflight.get("id"), "project_id": preflight.get("project_id"),
            "asset_sha": preflight.get("asset_sha"), "reference_id": preflight.get("reference_id"),
            "producer": preflight.get("producer"), "created_at": preflight.get("created_at"),
            "status": "unreviewed", "content_type": "unknown", "identity_prediction": "uncertain",
            "visual_evidence": [], "quality": None, "identity": None, "effective": False,
            "evidence_status": "stale_context" if trusted else "legacy_unverified", "legacy_preflight": preflight,
            "reason": "预检没有绑定当前图片、角色、版本或身份依据，仅保留作历史记录" if trusted else "旧启发式预检不是视觉核验，仅保留作历史记录"}


def effective_preflight_filtered(ref: dict) -> bool:
    pf = ref.get("preflight") or {}
    return bool(ref.get("preflight_filtered") and pf.get("producer") not in UNTRUSTED_EVIDENCE_PRODUCERS
                and ref.get("asset_sha") and pf.get("asset_sha") == ref["asset_sha"]
                and ref.get("preflight_context") and pf.get("project_context") == ref["preflight_context"])


def review_is_current(ref: dict) -> bool:
    review = ref.get("review") or {}
    return bool(ref.get("asset_sha") and review.get("asset_sha") == ref["asset_sha"]
                and ref.get("review_producer") not in UNTRUSTED_EVIDENCE_PRODUCERS
                and ref.get("review_current_context", False))


def preflight_is_current(ref: dict) -> bool:
    pf = ref.get("preflight") or {}
    return bool(ref.get("asset_sha") and pf.get("asset_sha") == ref["asset_sha"]
                and pf.get("producer") not in UNTRUSTED_EVIDENCE_PRODUCERS
                and ref.get("preflight_current_context", False))


MESSAGES = {
    "not_selected": "尚未由你明确保留",
    "inspiration_only": "这张图归在灵感库，不作为现场姿势卡",
    "missing_asset": "缺少可用图片文件",
    "missing_review": "尚未逐图核验",
    "stale_identity_context": "角色适配核验尚未绑定当前角色、版本或身份依据，请重新核对",
    "untrusted_review": "旧启发式判断不是视觉核验，请重新逐图核对",
    "stale_review": "核验对应的图片版本已经改变",
    "wrong_kind": "不是可用的真人摄影参考",
    "no_person": "没有明确可见的人物",
    "pose_unreadable": "需要借鉴的动作不可辨认",
    "collage": "拼图不能作为独立姿势主卡",
    "unclear": "画质不足以支持动作分析",
    "uncertain": "仍有未解决的关键疑点",
    "character_unconfirmed": "角色适配关系尚未确认",
    "adaptation_unapproved": "跨角色／普通人像借鉴需要你明确同意",
    "source_unconfirmed": "来源未确认；需原发布页或自有作品说明",
    "missing_card": "尚未编写资料卡",
    "stale_context": "角色、要求或器材已改变，请重新核对资料卡",
    "not_accepted": "资料卡尚未由你确认",
}


def digest(data: object) -> str:
    return hashlib.sha256(encode(data).encode("utf-8")).hexdigest()


def context_digest(project: dict) -> str:
    inputs = {key: project.get(key, "") for key in ("character", "work", "costume", "brief", "gear")}
    if project.get("identity_context_revision"):
        inputs["identity_context_revision"] = project["identity_context_revision"]
    return digest(inputs)


def acceptance_digest(ref: dict, project: dict) -> str:
    return digest({"asset": ref.get("asset_sha"), "review": ref.get("review"), "card": ref.get("card"),
                   "context": context_digest(project), "source": ref["source"], "title": ref["title"],
                   "borrow": ref["borrow"], "allow_cross_domain": ref["allow_cross_domain"],
                   "preference": ref["preference"]})


def review_context_matches(ref: dict, project: dict) -> bool:
    if not ref.get("review"):
        return False
    bound = ref.get("review_identity_context")
    if bound:
        return bound == identity_digest(project)
    # An older accepted record proves its project binding through the complete
    # acceptance fingerprint; an unaccepted legacy review has no such proof.
    return bool(ref.get("accepted_fingerprint")
                and ref.get("card_context") == context_digest(project)
                and ref["accepted_fingerprint"] == acceptance_digest(ref, project))


def source_is_traceable(source: dict) -> bool:
    if not source.get("source_confirmed"):
        return False
    if source.get("rights") == "owned":
        return bool(source.get("rights_note"))
    url = urlsplit(source.get("page_url", ""))
    host, path = (url.hostname or "").lower(), url.path.lower()
    if url.scheme not in {"http", "https"} or not host or path in {"", "/"}:
        return False
    if host.endswith(("pinimg.com", "xhscdn.com")) or "/search" in path:
        return False
    if path.endswith((".jpg", ".jpeg", ".png", ".webp")):
        return False
    return True


def blockers(ref: dict, project: dict, asset_exists: bool, *, require_acceptance: bool = True) -> list[str]:
    errors = []
    if ref["decision"] != "keep": errors.append("not_selected")
    if ref["lane"] != "field": errors.append("inspiration_only")
    if not asset_exists: errors.append("missing_asset")
    review = ref.get("review")
    if not review:
        errors.append("missing_review")
    else:
        if ref.get("review_producer") in UNTRUSTED_EVIDENCE_PRODUCERS: errors.append("untrusted_review")
        if not review_context_matches(ref, project):
            errors.append("stale_identity_context")
        if review["asset_sha"] != ref.get("asset_sha"): errors.append("stale_review")
        if review["kind"] not in {"cosplay_photo", "portrait_photo"}: errors.append("wrong_kind")
        for key, error in (("visible_person", "no_person"), ("pose_readable", "pose_unreadable"),
                           ("single_image", "collage"), ("sufficiently_clear", "unclear")):
            if not review[key]: errors.append(error)
        if review["character_match"] in {"unknown", "irrelevant"}: errors.append("character_unconfirmed")
        if (review["kind"] == "portrait_photo" or review["character_match"] == "adapted") and not ref["allow_cross_domain"]:
            errors.append("adaptation_unapproved")
    if not source_is_traceable(ref["source"]): errors.append("source_unconfirmed")
    if not ref.get("card"):
        errors.append("missing_card")
    elif ref.get("card_context") != context_digest(project):
        errors.append("stale_context")
    if require_acceptance and ref.get("accepted_fingerprint") != acceptance_digest(ref, project):
        errors.append("not_accepted")
    return errors


def state_for(ref: dict, project: dict, asset_exists: bool) -> str:
    if ref["decision"] == "reject": return "rejected"
    if ref["decision"] != "keep": return "candidate"
    if ref["lane"] == "inspiration": return "inspiration"
    errors = blockers(ref, project, asset_exists)
    if not errors: return "ready"
    if "missing_asset" in errors: return "missing_asset"
    if any(e in errors for e in ("missing_review", "stale_review", "stale_identity_context", "untrusted_review", "wrong_kind", "collage", "no_person", "unclear", "pose_unreadable")):
        return "needs_review"
    if "missing_card" in errors: return "needs_card"
    return "draft"
