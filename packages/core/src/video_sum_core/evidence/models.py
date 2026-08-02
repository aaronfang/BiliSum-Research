from enum import StrEnum
from pathlib import Path

from pydantic import BaseModel, ConfigDict, Field


class EvidenceKind(StrEnum):
    SUBTITLE = "subtitle"
    ASR = "asr"
    FRAME_OCR = "frame_ocr"
    CONTEXT = "context"


class TextAnchor(BaseModel):
    model_config = ConfigDict(frozen=True)

    anchor_id: str
    start: float = Field(ge=0)
    end: float = Field(ge=0)
    query: str


class EvidenceBudget(BaseModel):
    model_config = ConfigDict(frozen=True)

    max_frames: int = Field(default=12, ge=0)
    samples_per_anchor: int = Field(default=3, ge=1)
    sample_radius_seconds: float = Field(default=0.5, ge=0)


class FrameSample(BaseModel):
    model_config = ConfigDict(frozen=True)

    frame_id: str
    timestamp: float = Field(ge=0)
    path: Path


class EvidenceItem(BaseModel):
    model_config = ConfigDict(frozen=True)

    evidence_id: str
    kind: EvidenceKind
    observed_text: str
    start: float = Field(ge=0)
    end: float = Field(ge=0)
    confidence: float = Field(ge=0, le=1)
    derivation_method: str
    source_ref: str
    anchor_id: str | None = None


class EvidenceSet(BaseModel):
    model_config = ConfigDict(frozen=True)

    items: tuple[EvidenceItem, ...] = ()
