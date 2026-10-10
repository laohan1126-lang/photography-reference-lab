"""Structured evidence input schemas and gate exchange models.

Implements strict validation for research claims, sources, media artifacts,
and rework packages without permitting self-attested bypasses.
"""
from __future__ import annotations

import hashlib
import json
from typing import Annotated, Any, Literal, Optional
from pydantic import BaseModel, ConfigDict, Field, field_validator


class Strict(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)


ClaimCategory = Literal["A", "B", "C", "D"]
PlatformType = Literal["bilibili", "youtube", "xiaohongshu", "local", "other"]
MediaStatus = Literal["ACCESSIBLE", "UNACCESSIBLE", "NOT_DOWNLOADED", "SIMULATED_TEST"]
MediaType = Literal["video", "audio", "transcript", "screenshot", "image"]
IssueSeverity = Literal["ERROR", "WARNING"]
GateDecision = Literal["PASS", "REVISE", "BLOCKED"]


class SourceMetadata(Strict):
    """Metadata identifying an original photography reference video/post."""
    url: Annotated[str, Field(min_length=5, max_length=1000)]
    platform: PlatformType
    author: Annotated[str, Field(min_length=1, max_length=200)]
    title: Annotated[str, Field(min_length=1, max_length=500)]
    published_date: Optional[str] = None  # Format: YYYY-MM-DD
    duration_seconds: Annotated[float, Field(ge=0.0)]
    known_equipment: list[str] = Field(default_factory=list)
    is_tutorial_confirmed: bool = True
    notes: str = ""


class MediaArtifactRecord(Strict):
    """Local media file reference with cryptographic hash and access status."""
    local_path: Annotated[str, Field(min_length=1, max_length=1000)]
    sha256: Annotated[str, Field(pattern=r"^[a-fA-F0-9]{64}$")]
    media_type: MediaType
    status: MediaStatus
    file_size_bytes: Optional[int] = None


class TimestampSpan(Strict):
    """Specific time range in video with optional screenshot alignment."""
    start_seconds: Annotated[float, Field(ge=0.0)]
    end_seconds: Annotated[float, Field(ge=0.0)]
    formatted_time: str = ""
    screenshot_path: Optional[str] = None
    screenshot_timestamp_seconds: Optional[float] = None

    @field_validator("end_seconds")
    @classmethod
    def validate_range(cls, end: float, info) -> float:
        start = info.data.get("start_seconds")
        if start is not None and end < start:
            raise ValueError(f"end_seconds ({end}) cannot be less than start_seconds ({start})")
        return end


class ClaimedNumber(Strict):
    """Explicit quantitative assertion (ratio, angle, percentage, etc.)."""
    value: str
    metric: str = ""
    has_empirical_basis: bool = False
    empirical_source: Optional[str] = None


class ClaimRecord(Strict):
    """Structured research assertion categorized by epistemological tier (A/B/C/D)."""
    claim_id: Annotated[str, Field(min_length=1, max_length=100)]
    statement: Annotated[str, Field(min_length=5, max_length=2000)]
    category: ClaimCategory  # A: 直接观察, B: 作者实际表达, C: 专业解释, D: 项目推断
    source_url: str
    time_spans: list[TimestampSpan] = Field(default_factory=list)
    supporting_evidence: Annotated[str, Field(min_length=5, max_length=3000)]
    verbatim_quote: Optional[str] = None
    unknown_conditions: list[str] = Field(default_factory=list)
    equipment_tags: list[str] = Field(default_factory=list)
    claimed_numbers: list[ClaimedNumber] = Field(default_factory=list)
    self_attested_verified: Optional[bool] = None  # Ignored by quality gate


class ResearchEvidencePackage(Strict):
    """Full research bundle delivered by research agent for independent audit."""
    package_id: Annotated[str, Field(min_length=1, max_length=120)]
    topic: Annotated[str, Field(min_length=2, max_length=300)]
    author: Annotated[str, Field(min_length=1, max_length=100)]
    created_at: str
    sources: list[SourceMetadata] = Field(default_factory=list)
    media_artifacts: list[MediaArtifactRecord] = Field(default_factory=list)
    claims: list[ClaimRecord] = Field(default_factory=list)
    cross_document_context: dict[str, Any] = Field(default_factory=dict)

    def compute_fingerprint(self) -> str:
        """Deterministic sha256 hash of claims and sources."""
        raw = self.model_dump_json(exclude={"package_id", "created_at"})
        return hashlib.sha256(raw.encode("utf-8")).hexdigest()


class AuditIssue(Strict):
    """Detailed defect discovered during programmatic or semantic checks."""
    tier: Literal["TIER_1_PROGRAMMATIC", "TIER_2_SEMANTIC"]
    issue_code: str
    severity: IssueSeverity
    claim_id: Optional[str] = None
    field: Optional[str] = None
    message: str
    actual_value: Any = None
    expected_or_conflict: Any = None
    remediation: str


class ReworkPackage(Strict):
    """Machine-readable feedback bundle sent back to research agent on failure."""
    package_id: str
    cycle: int
    max_cycles: int = 2
    decision: GateDecision
    issues: list[AuditIssue] = Field(default_factory=list)
    affected_claim_ids: list[str] = Field(default_factory=list)
    summary: str
    remediation_guidance: list[str] = Field(default_factory=list)


class AdmissionReceipt(Strict):
    """Cryptographic certificate granting admission to formal curriculum."""
    receipt_id: str
    package_id: str
    verified_at: str
    decision: Literal["PASS"] = "PASS"
    total_claims_verified: int
    approved_manifest_hash: str
    scope: str = "photography_course_curriculum"
