from collections.abc import Callable
from dataclasses import dataclass

from video_sum_core.errors import VideoSumError
from video_sum_core.evidence import (
    EvidenceBudget,
    EvidenceEngine,
    EvidenceItem,
    EvidenceKind,
    EvidenceSet,
    TextAnchorPlanner,
)
from video_sum_core.fusion.engine import FusionEngine
from video_sum_core.fusion.models import CorrectedTranscript
from video_sum_core.transcript import (
    AsrAdapter,
    MediaSource,
    Transcript,
    TranscriptPolicy,
    TranscriptResolver,
    TranscriptSourceKind,
)


@dataclass(frozen=True)
class TranscriptFusionOutcome:
    primary: Transcript
    supporting: tuple[Transcript, ...]
    corrected: CorrectedTranscript
    evidence: EvidenceSet
    warnings: tuple[str, ...] = ()

    def provenance_payload(self) -> dict[str, object]:
        return {
            "schema_version": 1,
            "primary": self.primary.source.model_dump(mode="json"),
            "supporting": [item.source.model_dump(mode="json") for item in self.supporting],
        }

    def audit_payload(self) -> dict[str, object]:
        return {
            "schema_version": 1,
            "primary_source": self.primary.source.model_dump(mode="json"),
            "corrections": [
                correction.model_dump(mode="json") for correction in self.corrected.corrections
            ],
            "evidence": [item.model_dump(mode="json") for item in self.evidence.items],
            "context_hints": list(self.evidence.context_hints),
        }


class TranscriptFusionWorkflow:
    def __init__(
        self,
        resolver: TranscriptResolver,
        asr_adapter: AsrAdapter,
        fusion_engine: FusionEngine | None = None,
        anchor_planner: TextAnchorPlanner | None = None,
    ) -> None:
        self._resolver = resolver
        self._asr_adapter = asr_adapter
        self._fusion_engine = fusion_engine or FusionEngine()
        self._anchor_planner = anchor_planner or TextAnchorPlanner()

    def process(
        self,
        media: MediaSource,
        policy: TranscriptPolicy,
        *,
        title: str,
        fusion_enabled: bool,
        collect_supporting_asr: bool,
        evidence_budget: EvidenceBudget,
        evidence_engine_factory: Callable[[Transcript], EvidenceEngine | None],
    ) -> TranscriptFusionOutcome:
        primary = self._resolver.resolve(media, policy)
        supporting: list[Transcript] = []
        warnings: list[str] = []
        if (
            fusion_enabled
            and collect_supporting_asr
            and primary.source.kind is not TranscriptSourceKind.ASR
        ):
            try:
                supporting.append(self._asr_adapter.transcribe(media))
            except VideoSumError as exc:
                warnings.append(str(exc))

        if not fusion_enabled:
            evidence = EvidenceSet()
            return TranscriptFusionOutcome(
                primary=primary,
                supporting=tuple(supporting),
                corrected=self._fusion_engine.reconcile(primary, evidence),
                evidence=evidence,
                warnings=tuple(warnings),
            )

        anchors = self._anchor_planner.plan(primary)
        collected = EvidenceSet()
        evidence_engine = evidence_engine_factory(primary)
        if anchors and evidence_engine is not None:
            collected = evidence_engine.collect(media, anchors, evidence_budget)
        supporting_items = tuple(
            EvidenceItem(
                evidence_id=f"{track.source.kind.value}:{track_index}:{segment_index}",
                kind=(
                    EvidenceKind.ASR
                    if track.source.kind is TranscriptSourceKind.ASR
                    else EvidenceKind.SUBTITLE
                ),
                observed_text=segment.text,
                start=segment.start,
                end=segment.end,
                confidence=segment.confidence
                or (0.72 if track.source.kind is TranscriptSourceKind.ASR else 0.95),
                derivation_method=track.source.kind.value,
                source_ref=track.source.location,
                media_ref=str(media.path),
            )
            for track_index, track in enumerate(supporting)
            for segment_index, segment in enumerate(track.segments)
        )
        evidence = EvidenceSet(
            items=supporting_items + collected.items,
            context_hints=(title.strip(),) if title.strip() else (),
        )
        return TranscriptFusionOutcome(
            primary=primary,
            supporting=tuple(supporting),
            corrected=self._fusion_engine.reconcile(primary, evidence),
            evidence=evidence,
            warnings=tuple(warnings),
        )
