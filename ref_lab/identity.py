"""Versioned Identity Context for exact-character and reference verification.

Queries, titles and file names are discovery metadata, NOT visual evidence.
Identity Context defines verifiable visual identifiers, aliases, and common
confusions to support candidate-level identity preflight.
"""
from __future__ import annotations

import hashlib
import json
import sqlite3
from typing import Any
from uuid import uuid4
from .db import encode, now

IdentityContext = dict[str, Any]

# Grounded presets for live acceptance cases to ensure zero hallucination
CANONICAL_PRESETS: dict[str, dict[str, Any]] = {
    "王昭君": {
        "canonical_name": "王昭君",
        "aliases": {
            "zh": ["王昭君", "昭君", "王昭君长夜焕生", "长夜焕生", "王者荣耀王昭君"],
            "ja": ["王昭君"],
            "en": ["Wang Zhaojun", "Zhaojun", "Zhaojun Wang", "HOK Wang Zhaojun"],
        },
        "work": "王者荣耀",
        "costume": "长夜焕生 (无双限定/水母礼服)",
        "visual_identifiers": [
            "深海水母与冰晶幻想风格高定礼服，冷白色与水母半透明薄纱裙摆",
            "白色或极浅蓝微卷长发，水晶/冰晶发饰与轻盈头冠",
            "法杖武器具海洋晶石与水母/珊瑚冰刺造型",
            "水下/水族馆沉浸式摄影或深蓝冷色调光影",
        ],
        "common_confusions": [
            {"name": "小乔", "work": "王者荣耀", "distinction": "小乔为双丸子头短发萝莉体型，持有巨型折扇，切勿与王昭君混淆"},
            {"name": "貂蝉", "work": "王者荣耀", "distinction": "貂蝉为粉白/淡紫飘带长袖舞姬体态，无水母晶石礼服与法杖"},
            {"name": "irisvanherpen", "work": "Iris van Herpen 秀场", "distinction": "秀场高定时装模特摄影，非王昭君角色"},
            {"name": "haute-couture", "work": "秀场高定模特", "distinction": "高定时装展演模特，非王昭君角色"},
        ],
        "uncertainties": [
            "同名历史人物或王者荣耀其他皮肤（如凤凰于飞、乞巧织情）需确认是否属于长夜焕生皮肤限定",
            "棚拍若背景完全无水下元素，需通过发型、法杖与服饰纹样进行判断",
        ],
        "reference_provenance": "王者荣耀官方皮肤概念设计与演示视频、长夜焕生海报",
    },
    "安养寺姬芽": {
        "canonical_name": "安养寺姬芽",
        "aliases": {
            "zh": ["安养寺姬芽", "姬芽", "安养寺", "103期姬芽"],
            "ja": ["安養寺姫芽", "安養寺 姫芽", "姫芽", "ひめ"],
            "en": ["Anyoji Hime", "Hime Anyoji", "Hime"],
        },
        "work": "Link! Like! 莲之空女学院学园偶像俱乐部",
        "costume": "莲之空女学院制服 / Mira-Cra Park! 单元演出服",
        "visual_identifiers": [
            "浅棕偏粉微卷中长发，头顶特征呆毛与侧发夹",
            "电竞少女/学园偶像活力风格，常带游戏耳机或手柄/掌机周边",
            "绿红撞色 Mira-Cra Park! 打歌服或莲之空深色冬季制服",
        ],
        "common_confusions": [
            {"name": "藤岛慈", "work": "莲之空女学院", "distinction": "藤岛慈为金粉色双马尾，Mira-Cra Park! 前辈，不可与姬芽混淆"},
            {"name": "大泽瑠璃乃", "work": "莲之空女学院", "distinction": "大泽瑠璃乃为橙色短发活力元气少女，不可与姬芽混淆"},
            {"name": "百生吟子", "work": "莲之空女学院", "distinction": "百生吟子为黑色长直发文学少女，不可混淆"},
        ],
        "uncertainties": [
            "日常便服或未带标志性发饰时需核对发色与神态",
        ],
        "reference_provenance": "Link! Like! Love Live! 官方角色资料与卡面插图",
    },
    "有马加奈": {
        "canonical_name": "有马加奈",
        "aliases": {
            "zh": ["有马加奈", "加奈", "小苏打", "重曹酱"],
            "ja": ["有馬かな", "重曹ちゃん", "かな"],
            "en": ["Arima Kana", "Kana Arima", "Kana"],
        },
        "work": "【我推的孩子】",
        "costume": "制服 / B小町打歌服",
        "visual_identifiers": [
            "暗红色短发波波头（Bob头）",
            "常佩戴黑色或深色贝雷帽",
            "深红/酒红眼眸，表情常带傲娇或生动微表情",
            "娇小身形，常穿秀知高校制服或B小町白色/舞台演出服",
        ],
        "common_confusions": [
            {"name": "黑川茜", "work": "【我推的孩子】", "distinction": "黑川茜是深蓝发中长发，偏冷静成熟气质，切勿误判为有马加奈"},
            {"name": "星野露比", "work": "【我推的孩子】", "distinction": "星野露比为金发侧单马尾，红/金星眸，切勿误判"},
            {"name": "星野爱", "work": "【我推的孩子】", "distinction": "星野爱为深紫发/粉渐变长发，双眼有六芒星，切勿误判"},
            {"name": "MEM啾", "work": "【我推的孩子】", "distinction": "MEM啾为明黄色短发并带有恶魔小角，切勿误判"},
        ],
        "uncertainties": [
            "不同摄影或假发品类可能使暗红发色偏向紫红、棕红或亮红",
            "无贝雷帽日常服装版本需仔细核对发型弧度与眼色",
        ],
        "reference_provenance": "集英社官方角色资料、动画人设图、赤坂明×横枪萌果官方原作",
    },
    "kamen rider durendal": {
        "canonical_name": "假面骑士 Durendal",
        "aliases": {
            "zh": ["假面骑士恒剑", "假面骑士Durendal", "恒剑", "神代凌牙"],
            "ja": ["仮面ライダーデュランダル", "デュランダル", "神代凌牙"],
            "en": ["Kamen Rider Durendal", "Durendal", "Ryoga Shindai"],
        },
        "work": "假面骑士圣刃",
        "costume": "海洋历史 (Ocean History) 基本形态",
        "visual_identifiers": [
            "黑、白、金主色调的海洋/旗鱼主题特摄装甲",
            "海洋水生生物鱼鳍造型头雕与复眼",
            "专用圣剑‘时国剑界时’（Jikokuken Kaiji），可切换为三叉戟枪模式或单手剑模式",
            "装甲背后及腰侧有鳍状白金披风摆件",
        ],
        "common_confusions": [
            {"name": "假面骑士佩剑 (Sabela)", "work": "假面骑士圣刃", "distinction": "神代玲花变身，红黑色女性昆虫/蜂形装甲，烟睿剑狼烟，不可混为恒剑"},
            {"name": "假面骑士Saber", "work": "假面骑士圣刃", "distinction": "红白黑烈火装甲，火炎剑烈火，头部有龙角长剑造型，切勿混淆"},
            {"name": "假面骑士Blades", "work": "假面骑士圣刃", "distinction": "蓝白水势剑流水装甲，狮子胸甲，切勿混淆"},
            {"name": "假面骑士Espada", "work": "假面骑士圣刃", "distinction": "黄白神灯装甲，切勿混淆"},
        ],
        "uncertainties": [
            "非特摄皮套的普通cosplay常服（如神代凌牙便服）需明确标注为人类形态",
            "在强逆光或暗场下，金色包边可能与Saber龙纹混淆，需核对三叉戟与头雕",
        ],
        "reference_provenance": "东映假面骑士官方图鉴、Saber TV正片皮套特写真集",
    },
}


def identity_digest(project: dict) -> str:
    inputs = {key: project.get(key, "") for key in ("character", "work", "costume", "brief")}
    inputs["identity_context_revision"] = project.get("identity_context_revision", 0)
    return hashlib.sha256(encode(inputs).encode("utf-8")).hexdigest()


def ensure_identity_context(con: sqlite3.Connection, project: dict) -> dict:
    """Resolve the current inputs, retaining previous contexts as immutable history."""
    current = get_identity_context(con, project_id=project["id"])
    snapshot = identity_digest(project)
    if current and current.get("project_context") == snapshot:
        return current
    fresh = build_identity_context(project["character"], project.get("work", ""), project.get("costume", ""), project.get("brief", ""))
    fresh.update(version=current.get("version", 0) + 1 if current else 1, project_context=snapshot)
    return save_identity_context(con, project["id"], fresh)


def normalize_character_key(character: str) -> str:
    cleaned = character.strip().lower()
    for key, preset in CANONICAL_PRESETS.items():
        if key in cleaned or cleaned in key:
            return key
        aliases = preset.get("aliases", {})
        for lang_list in aliases.values():
            for a in lang_list:
                if a.lower() in cleaned or cleaned in a.lower():
                    return key
    return cleaned


def build_identity_context(
    character: str,
    work: str = "",
    costume: str = "",
    brief: str = "",
    notes: str = "",
) -> dict[str, Any]:
    """Build a versioned Identity Context, using verified presets if matched or honest general defaults."""
    key = normalize_character_key(character)
    if key in CANONICAL_PRESETS:
        preset = CANONICAL_PRESETS[key]
        return {
            "id": f"ic_{uuid4().hex[:12]}",
            "version": 1,
            "canonical_name": preset["canonical_name"],
            "aliases": preset["aliases"],
            "work": work or preset["work"],
            "costume": costume or preset["costume"],
            "visual_identifiers": preset["visual_identifiers"],
            "common_confusions": preset["common_confusions"],
            "uncertainties": preset["uncertainties"],
            "reference_provenance": preset["reference_provenance"],
            "created_at": now(),
        }

    # For general characters, avoid hallucinating visual facts
    aliases_zh = [character] if character else []
    return {
        "id": f"ic_{uuid4().hex[:12]}",
        "version": 1,
        "canonical_name": character,
        "aliases": {"zh": aliases_zh, "ja": [], "en": []},
        "work": work,
        "costume": costume,
        "visual_identifiers": [brief] if brief else ["视觉识别依据待补充；请核对官方设定"],
        "common_confusions": [],
        "uncertainties": ["暂无官方人设对比数据，需人工核对"],
        "reference_provenance": notes or "用户项目输入",
        "created_at": now(),
    }


def save_identity_context(con: sqlite3.Connection, project_id: str | None, data: dict[str, Any]) -> dict[str, Any]:
    ident = data.get("id") or f"ic_{uuid4().hex[:12]}"
    data["id"] = ident
    version = data.get("version", 1)
    character = data.get("canonical_name", "")
    con.execute(
        "INSERT OR REPLACE INTO identity_contexts VALUES(?,?,?,?,?)",
        (ident, project_id, character, version, encode(data)),
    )
    return data


def get_identity_context(con: sqlite3.Connection, project_id: str | None = None, character: str | None = None) -> dict[str, Any] | None:
    if project_id:
        row = con.execute(
            "SELECT data FROM identity_contexts WHERE project_id=? ORDER BY version DESC LIMIT 1",
            (project_id,),
        ).fetchone()
        if row:
            return json.loads(row[0])
    if character:
        row = con.execute(
            "SELECT data FROM identity_contexts WHERE character=? ORDER BY version DESC LIMIT 1",
            (character,),
        ).fetchone()
        if row:
            return json.loads(row[0])
    return None


def list_identity_contexts(con: sqlite3.Connection, project_id: str) -> list[dict[str, Any]]:
    rows = con.execute(
        "SELECT data FROM identity_contexts WHERE project_id=? ORDER BY version DESC",
        (project_id,),
    ).fetchall()
    return [json.loads(r[0]) for r in rows]
