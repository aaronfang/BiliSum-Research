from enum import StrEnum

from pydantic import BaseModel, ConfigDict, Field

from video_sum_core.transcript import Transcript, TranscriptSegment


class CorrectionDecision(StrEnum):
    ACCEPTED = "accepted"
    UNCERTAIN = "uncertain"


class Correction(BaseModel):
    model_config = ConfigDict(frozen=True)

    segment_index: int = Field(ge=0)
    from_value: str
    to_value: str
    evidence_ids: tuple[str, ...]
    confidence: float = Field(ge=0, le=1)
    rule_version: str
    decision: CorrectionDecision


class CorrectedTranscript(BaseModel):
    model_config = ConfigDict(frozen=True)

    original: Transcript
    segments: tuple[TranscriptSegment, ...]
    corrections: tuple[Correction, ...] = ()

    @property
    def text(self) -> str:
        return "\n".join(segment.text for segment in self.segments).strip()
