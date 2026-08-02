from enum import StrEnum
from pathlib import Path

from pydantic import BaseModel, ConfigDict, Field


class TranscriptSourceKind(StrEnum):
    SIDECAR = "sidecar"
    PLATFORM_SUBTITLE = "platform_subtitle"
    ASR = "asr"


class MediaSource(BaseModel):
    model_config = ConfigDict(frozen=True)

    path: Path


class TranscriptPolicy(BaseModel):
    model_config = ConfigDict(frozen=True)

    prefer_subtitles: bool = True


class TranscriptSource(BaseModel):
    model_config = ConfigDict(frozen=True)

    kind: TranscriptSourceKind
    location: str
    format: str | None = None
    language: str | None = None
    model: str | None = None
    automatic: bool = False
    fallback_reason: str | None = None


class TranscriptSegment(BaseModel):
    model_config = ConfigDict(frozen=True)

    start: float = Field(ge=0)
    end: float = Field(ge=0)
    text: str
    confidence: float | None = Field(default=None, ge=0, le=1)


class Transcript(BaseModel):
    model_config = ConfigDict(frozen=True)

    source: TranscriptSource
    segments: tuple[TranscriptSegment, ...]

    @property
    def text(self) -> str:
        return "\n".join(segment.text for segment in self.segments).strip()
