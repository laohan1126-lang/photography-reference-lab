"""Shared API and worker contracts. Missing evidence is never a positive default."""
from __future__ import annotations

import re
from typing import Annotated, Literal
from urllib.parse import urlsplit
from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

Text = Annotated[str, Field(max_length=12000)]
Short = Annotated[str, Field(max_length=400)]
NonEmpty = Annotated[str, Field(min_length=1, max_length=12000)]
Digest = Annotated[str, Field(pattern=r"^[a-f0-9]{64}$")]
Kind = Literal["unknown", "cosplay_photo", "portrait_photo", "illustration", "equipment", "location", "collage", "generated"]
Decision = Literal["pending", "keep", "maybe", "reject"]


class Strict(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)


class ProjectInput(Strict):
    character: Annotated[str, Field(min_length=1, max_length=120)]
    work: Short = ""
    costume: Short = ""
    brief: Text = ""
    gear: Text = "Sony A7M4；50mm f/1.8；24–240mm；Godox V100 一盏、灯架、圆形柔光附件。以 cosplay／日常、社交、现场可执行为主。"


class ProjectEdit(ProjectInput):
    expected_revision: int = Field(ge=1)


def safe_url(value: str) -> str:
    if not value:
        return ""
    parsed = urlsplit(value)
    if parsed.scheme not in {"https", "http"} or not parsed.hostname or parsed.username or parsed.password:
        raise ValueError("URL must be http(s), without embedded credentials")
    if any(ord(char) < 32 for char in value):
        raise ValueError("URL contains control characters")
    # Credentials belong neither in metadata nor public logs.
    if re.search(r"(?:[?&])(?:access_token|authorization|cookie|api_key|password)=", value, re.I):
        raise ValueError("Credential-bearing URL is not allowed")
    return value


class Source(Strict):
    page_url: Annotated[str, Field(max_length=4000)] = ""
    image_url: Annotated[str, Field(max_length=4000)] = ""
    author: Short = ""
    title: Short = ""
    search_query: Short = ""
    search_category: Short = ""
    rights: Literal["unknown", "personal_reference", "owned", "licensed"] = "unknown"
    rights_note: Text = ""
    source_confirmed: bool = False
    # This is provenance, not a promise that a platform file is the photographer's original.
    obtained_as: Literal["as_received", "platform_variant", "legacy_reencoded", "screenshot", "unknown"] = "unknown"

    _urls = field_validator("page_url", "image_url")(safe_url)


class CandidateInput(Strict):
    asset_sha: Digest | None = None
    title: Short = ""
    source: Source = Field(default_factory=Source)
    import_key: Annotated[str, Field(max_length=600)] = ""
    legacy_notes: Text = ""
    job_id: Short = ""


class ReferenceEdit(Strict):
    expected_revision: int = Field(ge=1)
    title: Short | None = None
    decision: Decision | None = None
    lane: Literal["field", "inspiration"] | None = None
    preference: Text | None = None
    borrow: list[Short] | None = Field(default=None, max_length=20)
    allow_cross_domain: bool | None = None
    source: Source | None = None


class VisualReview(Strict):
    asset_sha: Digest
    kind: Kind
    visible_person: bool
    pose_readable: bool
    single_image: bool
    sufficiently_clear: bool
    character_match: Literal["exact", "adapted", "unknown", "irrelevant"]
    observations: list[NonEmpty] = Field(min_length=1, max_length=30)
    critical_uncertainties: list[NonEmpty] = Field(max_length=20)


class ReviewInput(Strict):
    expected_revision: int = Field(ge=1)
    review: VisualReview


class PosePlan(Strict):
    verbal_cues: list[NonEmpty] = Field(min_length=1, max_length=8)
    static_steps: list[NonEmpty] = Field(min_length=1, max_length=12)
    action_directing: Text
    photographer_steps: list[NonEmpty] = Field(min_length=1, max_length=12)
    safety: NonEmpty
    fallback: NonEmpty


class LightingPlan(Strict):
    visible_evidence: list[NonEmpty] = Field(min_length=1, max_length=12)
    interpretation: NonEmpty
    confidence: Literal["low", "medium", "high"]
    available_gear_plan: NonEmpty


class RetouchPlan(Strict):
    route: Literal["none", "cleanup", "composite"]
    steps: list[NonEmpty] = Field(max_length=20)
    capture_preparation: Text
    background_prompt: Text

    @model_validator(mode="after")
    def require_composite_plan(self) -> "RetouchPlan":
        if self.route == "composite" and (not self.background_prompt or not self.capture_preparation):
            raise ValueError("Composite cards need a background brief and capture preparation")
        return self


class Card(Strict):
    title: NonEmpty
    intent: NonEmpty
    pose: PosePlan
    lighting: LightingPlan
    retouch: RetouchPlan


class CardInput(Strict):
    expected_revision: int = Field(ge=1)
    card: Card


class RevisionInput(Strict):
    expected_revision: int = Field(ge=1)


class ReflectionInput(Strict):
    expected_revision: int = Field(ge=1)
    tried: bool
    worked: Text = ""
    failed: Text = ""
    next_time: Text = ""


class JobInput(Strict):
    kind: Literal["collection", "analysis"]
    reference_ids: list[Short] = Field(default_factory=list, max_length=50)
    notes: Text = ""


class JobResult(Strict):
    expected_revision: int = Field(ge=1)
    status: Literal["running", "blocked", "succeeded", "failed", "cancelled"]
    detail: NonEmpty


class AnalysisResult(Strict):
    review: VisualReview
    # Null is explicitly correct for irrelevant/uncertain images. Never manufacture a pose.
    card: Card | None


class AnalysisImport(Strict):
    expected_revision: int = Field(ge=1)
    producer: Annotated[str, Field(min_length=1, max_length=200)]
    result: AnalysisResult


class PackInput(Strict):
    reference_ids: list[Short] = Field(default_factory=list, max_length=200)
    mode: Literal["field", "inspiration"] = "field"


class NoteInput(Strict):
    title: Annotated[str, Field(min_length=1, max_length=400)]
    body: Annotated[str, Field(max_length=200000)]
    source_path: Short = ""


class NoteEdit(Strict):
    expected_revision: int = Field(ge=1)
    title: Annotated[str, Field(min_length=1, max_length=400)]
    body: Annotated[str, Field(max_length=200000)]
