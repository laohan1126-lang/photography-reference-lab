"""Tier 2: Independent Semantic Audit Engine.

Evaluates semantic accuracy and epistemological integrity:
1. Verbatim quote grounding against ASR transcripts and dialogue ledgers
2. Identification of fabricated dialogues (e.g., "剑像小棍子")
3. Intent misattribution (attributing speculative physics to photographer's actual spoken motive)
4. Pseudoscience overgeneralization (e.g. embryonic startle reflex applied to posing)
"""
from __future__ import annotations

import difflib
import re
from typing import Optional

from ref_lab.evidence_gate.models import (
    AuditIssue,
    ClaimRecord,
    ResearchEvidencePackage,
)

# Known fabricated dialogue strings from previous failure audits
KNOWN_HALLUCINATED_QUOTES: list[str] = [
    "像个小棍子",
    "剑像小棍子",
    "剑根本看不出来，像个小棍子",
    "像根小棍子",
    "像小棍子一样",
]

# Known verified dialogues for BV1MD421L7VK (小言Jun)
VERIFIED_DIALOGUES_BV1MD421L7VK: list[dict] = [
    {
        "span": (73.0, 85.0),
        "actual": "往这边斜一点点……不是，你剑斜，你脸别斜，剑斜一点点，好，上来，好！",
        "topic": "剑斜脸别斜",
    },
    {
        "span": (105.0, 134.0),
        "actual": "因为这样一只手，你把那只手完全挡完了！换那只手撑出来，侧过来一点，这只手弯一点。",
        "topic": "换手防遮挡",
    },
    {
        "span": (160.0, 170.0),
        "actual": "这个弯一点点自然放着，这里弯一点不要绷，对，好！",
        "topic": "关节放松不要绷",
    },
    {
        "span": (230.0, 250.0),
        "actual": "就是我相对来说这种角色的硬一点的姿势我没那么会，我比较倾向于拍甜美的……后面就全拍这种蹲着了，你不能动太多，这个是给你定位的。",
        "topic": "蹲姿与定位",
    },
]

# Known verified dialogues for BV1imaN6tEc8 (林海音)
VERIFIED_DIALOGUES_BV1imaN6tEc8: list[dict] = [
    {
        "span": (162.0, 180.0),
        "actual": "那不太会摆姿势的人呢，我们可以先让他动起来：往前走几步，回头看一看，或者给掉他一个视线的方向，持续地去给他一些动作的指令。让他在完成动作的过程中的抓拍，往往会比静止拍摄要更自然一些。",
        "topic": "动起来抓拍",
    },
    {
        "span": (212.0, 240.0),
        "actual": "其实我们在拍摄的时候也可以利用现场的道具，比如一个小竹篓，一个蒲扇，一个小鱼灯。给被摄者手上拿一个东西，他就不会觉得手无处安放，视线也有了聚焦的地方。",
        "topic": "道具互动",
    },
]

# Patterns for speculative pseudoscience and overgeneralized claims
PSEUDOSCIENCE_PATTERNS: list[str] = [
    "胎儿期",
    "惊跳反射",
    "进化早期的防御性",
    "不可违抗的生理定律",
    "绝对神经系统禁令",
]

# Patterns for speculative mechanics masquerading as photographer's direct intent
SPECULATIVE_MECHANICS_INTENT: list[str] = [
    "力学三角支架消除身体颤动",
    "力学支架",
    "消除颤动支点",
]


class SemanticAuditor:
    """Executes Tier 2 independent semantic and epistemological reviews."""

    def __init__(self, transcripts: Optional[dict[str, list[dict]]] = None):
        self.transcripts = transcripts or {
            "BV1MD421L7VK": VERIFIED_DIALOGUES_BV1MD421L7VK,
            "BV1imaN6tEc8": VERIFIED_DIALOGUES_BV1imaN6tEc8,
        }

    def audit(self, package: ResearchEvidencePackage) -> list[AuditIssue]:
        issues: list[AuditIssue] = []
        for claim in package.claims:
            issues.extend(self._audit_claim(claim, package))
        return issues

    def _audit_claim(self, claim: ClaimRecord, package: ResearchEvidencePackage) -> list[AuditIssue]:
        issues: list[AuditIssue] = []

        # 1. Dialogue verbatim check
        issues.extend(self._check_verbatim_dialogue(claim))

        # 2. Intent misattribution check (speculation masquerading as author intent/direct observation)
        issues.extend(self._check_intent_misattribution(claim))

        # 3. Pseudoscience & causal overgeneralization check
        issues.extend(self._check_pseudoscience_and_overreach(claim))

        return issues

    def _check_verbatim_dialogue(self, claim: ClaimRecord) -> list[AuditIssue]:
        issues: list[AuditIssue] = []
        text_to_check = f"{claim.statement} {claim.verbatim_quote or ''}"

        # Check for known hallucinated dialogue phrases
        for fake_quote in KNOWN_HALLUCINATED_QUOTES:
            if fake_quote in text_to_check:
                issues.append(
                    AuditIssue(
                        tier="TIER_2_SEMANTIC",
                        issue_code="VERBATIM_HALLUCINATION",
                        severity="ERROR",
                        claim_id=claim.claim_id,
                        field="verbatim_quote" if claim.verbatim_quote else "statement",
                        message=(
                            f"Hallucinated dialogue detected: '{fake_quote}'. The photographer never uttered "
                            f"this line in audio or verified transcripts."
                        ),
                        actual_value=fake_quote,
                        expected_or_conflict="因为这样一只手，你把那只手完全挡完了！",
                        remediation=(
                            "Replace fabricated quote with verified dialogue from transcript at 02:08-02:14: "
                            "'因为这样一只手，你把那只手完全挡完了！'"
                        ),
                    )
                )

        # Check category B (Author Expression) against transcript if available
        if claim.category == "B" and claim.verbatim_quote:
            found_match = False
            for source_key, dialogues in self.transcripts.items():
                if source_key in claim.source_url:
                    for d in dialogues:
                        # Check keyword similarity
                        ratio = difflib.SequenceMatcher(None, claim.verbatim_quote, d["actual"]).ratio()
                        if ratio > 0.4 or any(w in d["actual"] for w in ["挡完", "斜", "绷", "动起来", "道具"]):
                            found_match = True
                            break
            if not found_match and len(claim.verbatim_quote) > 10:
                issues.append(
                    AuditIssue(
                        tier="TIER_2_SEMANTIC",
                        issue_code="VERBATIM_GROUNDING_UNVERIFIED",
                        severity="WARNING",
                        claim_id=claim.claim_id,
                        field="verbatim_quote",
                        message=f"Verbatim quote '{claim.verbatim_quote}' has low overlap with verified transcript.",
                        actual_value=claim.verbatim_quote,
                        expected_or_conflict="Verbatim audio matching",
                        remediation="Verify quote against audio recording.",
                    )
                )

        return issues

    def _check_intent_misattribution(self, claim: ClaimRecord) -> list[AuditIssue]:
        issues: list[AuditIssue] = []

        # If claim category is A (Direct Observation) or B (Author Expression),
        # but asserts speculative mechanics like "建立力学三角支架消除身体颤动"
        for mech in SPECULATIVE_MECHANICS_INTENT:
            if mech in claim.statement:
                if claim.category in ("A", "B"):
                    issues.append(
                        AuditIssue(
                            tier="TIER_2_SEMANTIC",
                            issue_code="INTENT_MISATTRIBUTION",
                            severity="ERROR",
                            claim_id=claim.claim_id,
                            field="category",
                            message=(
                                f"Speculative mechanical hypothesis '{mech}' falsely attributed to Category {claim.category} "
                                f"(Direct Observation / Author Expression). Author's stated motive was difficulty with hard poses."
                            ),
                            actual_value=claim.category,
                            expected_or_conflict="Category D (Project Inference) or removal",
                            remediation=(
                                "Reclassify as Category D (Project Inference) or remove speculative mechanical claim. "
                                "Author's real stated reason was: '这种角色的硬一点的姿势我没那么会，后面全拍这种蹲着了'."
                            ),
                        )
                    )

        return issues

    def _check_pseudoscience_and_overreach(self, claim: ClaimRecord) -> list[AuditIssue]:
        issues: list[AuditIssue] = []

        # Check for ungrounded pseudoscience patterns
        for pattern in PSEUDOSCIENCE_PATTERNS:
            if pattern in claim.statement or pattern in claim.supporting_evidence:
                issues.append(
                    AuditIssue(
                        tier="TIER_2_SEMANTIC",
                        issue_code="PSEUDOSCIENCE_OVERGENERALIZATION",
                        severity="ERROR",
                        claim_id=claim.claim_id,
                        field="statement",
                        message=(
                            f"Unverified speculative hypothesis '{pattern}' asserted as definitive causal explanation "
                            f"without anatomical/medical evidence."
                        ),
                        actual_value=pattern,
                        expected_or_conflict="Grounded ergonomic/biomechanical explanation (e.g. isometric muscle fatigue)",
                        remediation=(
                            "Replace speculative evolutionary/embryological claims with grounded biomechanical "
                            "explanations (e.g., isometric muscle contraction fatigue)."
                        ),
                    )
                )

        return issues
