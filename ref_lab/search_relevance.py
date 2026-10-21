"""Cheap, text-only discovery relevance for character search.

This module never identifies a character from an image and never claims visual
verification. It only answers: did the *visible discovery text* contain a
trusted name, a work clue, an explicit other-character clue, or nothing usable?

Unknown/empty text stays an exploration candidate with an explicit
``角色相关性未确认`` label. A bounded number of such candidates may be acquired,
but they never count as confirmed target hits.
"""
from __future__ import annotations

import re
from typing import Iterable

PHOTO_TERMS = (
    "cosplay", "coser", "cos ", "cos正片", "cos 正片", "正片", "场照", "返图",
    "写真", "棚拍", "摄影", "漫展", "自拍", "出片", "拍了", "客片", "约拍",
    "コスプレ", "コスプレイヤー", "写真撮影", "撮影", "レイヤー",
    "photography", "photoshoot", "photograph", "portrait", "convention",
    "pose", "posing", "📷", "动作参考",
)

# Text/explicit type markers that cannot be a real-person photography reference.
NON_PHOTO_TERMS = (
    "游戏截图", "游戏画面", "游戏cg", "游戏 cg", "皮肤特效", "特效设计", "技能特效",
    "官方立绘", "立绘", "插画", "同人图", "同人画", "原画", "壁纸",
    "concept art", "illustration", "fanart", "fan art", "wallpaper", "render",
    "3d model", "3d模型", "建模", "模型展示", "商品图", "商品展示", "服装展示",
    "人台", "假人", "mannequin", "手办", "雕像", "粘土", "三视图", "设定图",
    "ai生成", "ai 生成", "ai绘画", "ai 绘画", "generated image",
)

OTHER_CHARACTER_MARKERS = (
    "別キャラ", "別のキャラ", "他のキャラ", "別角色", "其他角色", "另一个角色",
    "different character", "another character", "not the target character",
    "不是目标角色", "非目标角色",
)

TIERS = ("target_named", "target_context", "unconfirmed", "other_character", "non_photo")
TIER_RANK = {tier: index for index, tier in enumerate(TIERS)}
TIER_LABELS = {
    "target_named": "名称命中 · 角色相关性待视觉核验",
    "target_context": "作品线索 · 角色相关性未确认",
    "unconfirmed": "角色相关性未确认",
    "other_character": "疑似其他角色",
    "non_photo": "非真人摄影内容",
}


def _casefold(value: object) -> str:
    text = str(value or "").casefold().replace("\u3000", " ")
    return re.sub(r"\s+", " ", text).strip()


def _card_text(card: dict) -> str:
    values = [card.get("text"), card.get("title"), card.get("description"),
              card.get("alt"), card.get("aria_label"), card.get("source_text")]
    return "\n".join(str(value) for value in values if value)


def _as_records(names: Iterable) -> list[dict]:
    records = []
    for item in names or ():
        if isinstance(item, dict):
            name = str(item.get("name") or "").strip()
            if name:
                records.append({"name": name,
                                "language": str(item.get("language") or ""),
                                "source": str(item.get("source") or "")})
        else:
            name = str(item or "").strip()
            if name:
                records.append({"name": name, "language": "", "source": ""})
    seen = set()
    output = []
    for record in records:
        key = _casefold(record["name"])
        if key and key not in seen:
            seen.add(key)
            output.append(record)
    return output


def _contains_term(text: str, term: str) -> bool:
    if not term:
        return False
    # ASCII terms need boundaries where possible; CJK terms can be substrings.
    if re.fullmatch(r"[\x00-\x7f ]+", term):
        return re.search(r"(?<![a-z0-9])" + re.escape(term) + r"(?![a-z0-9])", text) is not None
    return term in text


def classify_card(card: dict, *, names: Iterable = (), work_terms: Iterable = (),
                  other_terms: Iterable = ()) -> dict:
    """Classify one visible card using discovery text only.

    ``target_named`` is text evidence for routing, not visual identity evidence.
    ``unconfirmed`` is deliberately kept: a missing title or foreign language is
    not a rejection.
    """
    text = _casefold(_card_text(card))
    records = _as_records(names)
    name_hits = [record["name"] for record in records if _contains_term(text, _casefold(record["name"]))]
    work_hits = [str(term) for term in work_terms or () if _contains_term(text, _casefold(term))]
    photo_hit = any(_contains_term(text, _casefold(term)) for term in PHOTO_TERMS)
    non_photo = any(_contains_term(text, _casefold(term)) for term in NON_PHOTO_TERMS)
    other_hits = [str(term) for term in other_terms or () if _contains_term(text, _casefold(term))]
    explicit_other = any(_contains_term(text, _casefold(term)) for term in OTHER_CHARACTER_MARKERS)
    if non_photo:
        tier = "non_photo"
    elif other_hits and not name_hits:
        tier = "other_character"
    elif explicit_other and not name_hits:
        tier = "other_character"
    elif name_hits:
        tier = "target_named"
    elif work_hits and photo_hit:
        tier = "target_context"
    else:
        tier = "unconfirmed"
    return {
        "tier": tier,
        "rank": TIER_RANK[tier],
        "label": TIER_LABELS[tier],
        "name_hits": name_hits,
        "work_hits": work_hits,
        "photo_intent": bool(photo_hit),
        "other_character_hits": other_hits,
        "explicit_other_marker": bool(explicit_other),
        "non_photo_marker": bool(non_photo),
        "text_present": bool(text),
        "reason": {
            "target_named": "可见文字命中可信角色名称；身份仍需独立视觉核验。",
            "target_context": "可见文字命中作品与摄影意图，但未命中角色名称。",
            "unconfirmed": "没有可用的角色文字证据；保留探索，不冒充已确认目标。",
            "other_character": "可见文字明确指向其他角色；不作为目标角色候选。",
            "non_photo": "可见文字明确为非真人摄影内容；不作为摄影候选。",
        }[tier],
    }


def exploration_limit(target: int) -> int:
    """Bounded unconfirmed/context-only downloads; never the whole target."""
    target = max(1, int(target or 1))
    return max(1, min(8, target // 4))


def is_confirmed(row: dict) -> bool:
    return str((row.get("relevance") or {}).get("tier") or "") == "target_named"


def confirmed_count(rows: Iterable[dict]) -> int:
    return sum(1 for row in rows if is_confirmed(row))


def exploration_count(rows: Iterable[dict]) -> int:
    return len({row.get('page_url') or row.get('asset_sha') for row in rows
                if str((row.get("relevance") or {}).get("tier") or "") in
                {"target_context", "unconfirmed"}})


def associate_detail(card, row, *, names=(), work_terms=(), other_terms=()):
    """Keep card and author-only detail evidence, and re-evaluate new evidence."""
    card_evidence = {k: card[k] for k in ('page', 'text', 'title', 'description') if k in card}
    detail = row.get('author_detail') or {}
    detail_evidence = {k: detail[k] for k in ('title', 'description', 'author') if k in detail}
    card_result = classify_card(card_evidence, names=names, work_terms=work_terms, other_terms=other_terms)
    detail_result = classify_card(detail_evidence, names=names, work_terms=work_terms, other_terms=other_terms)
    result = detail_result if detail_result['text_present'] else card_result
    return {**result, 'card': {'evidence': card_evidence, 'relevance': card_result},
            'detail': {'evidence': detail_evidence, 'relevance': detail_result}}


def relevance_counts(rows: Iterable[dict]) -> dict:
    rows = list(rows)
    counts = {tier: 0 for tier in TIERS}
    for row in rows:
        tier = str((row.get("relevance") or {}).get("tier") or "unconfirmed")
        counts[tier if tier in counts else "unconfirmed"] += 1
    counts["confirmed"] = counts["target_named"]
    counts["exploration"] = counts["target_context"] + counts["unconfirmed"]
    return counts
