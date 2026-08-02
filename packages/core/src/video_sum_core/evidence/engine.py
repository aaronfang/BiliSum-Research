from typing import Protocol

from video_sum_core.evidence.models import (
    EvidenceBudget,
    EvidenceItem,
    EvidenceKind,
    EvidenceSet,
    FrameObservation,
    FrameSample,
    TextAnchor,
)
from video_sum_core.transcript import MediaSource


class FrameExtractor(Protocol):
    def extract(self, media: MediaSource, timestamps: list[float]) -> list[FrameSample]: ...


class FrameTextReader(Protocol):
    def read(self, frame: FrameSample) -> FrameObservation: ...


class EvidenceEngine:
    def __init__(self, frame_extractor: FrameExtractor, text_reader: FrameTextReader) -> None:
        self._frame_extractor = frame_extractor
        self._text_reader = text_reader

    def collect(
        self,
        media: MediaSource,
        anchors: list[TextAnchor],
        budget: EvidenceBudget,
    ) -> EvidenceSet:
        items: list[EvidenceItem] = []
        remaining = budget.max_frames
        for anchor in anchors:
            if remaining <= 0:
                break
            timestamps = self._timestamps(anchor, budget)[:remaining]
            observed_frames = [
                (frame, self._text_reader.read(frame))
                for frame in self._frame_extractor.extract(media, timestamps)
            ]
            for frame, observation in self._select_frames(observed_frames):
                normalized_text = observation.text.strip()
                items.append(
                    EvidenceItem(
                        evidence_id=f"{anchor.anchor_id}:{frame.frame_id}",
                        kind=EvidenceKind.FRAME_OCR,
                        observed_text=normalized_text,
                        start=frame.timestamp,
                        end=frame.timestamp,
                        confidence=observation.confidence,
                        derivation_method="frame_ocr_scene_quality",
                        source_ref=str(frame.path),
                        media_ref=str(media.path),
                        anchor_id=anchor.anchor_id,
                    )
                )
            remaining -= len(timestamps)
        return EvidenceSet(items=tuple(items))

    def _select_frames(
        self,
        candidates: list[tuple[FrameSample, FrameObservation]],
    ) -> list[tuple[FrameSample, FrameObservation]]:
        ranked = sorted(
            (
                (frame, observation)
                for frame, observation in candidates
                if observation.text.strip()
            ),
            key=lambda candidate: (
                -candidate[1].quality_score,
                -candidate[1].confidence,
                candidate[0].timestamp,
            ),
        )
        selected: list[tuple[FrameSample, FrameObservation]] = []
        signatures: set[tuple[str, str]] = set()
        for frame, observation in ranked:
            signature = (
                " ".join(observation.text.casefold().split()),
                observation.scene_signature.casefold().strip(),
            )
            if signature in signatures:
                continue
            signatures.add(signature)
            selected.append((frame, observation))
        return sorted(selected, key=lambda candidate: candidate[0].timestamp)

    def _timestamps(self, anchor: TextAnchor, budget: EvidenceBudget) -> list[float]:
        center = (anchor.start + anchor.end) / 2
        if budget.samples_per_anchor == 1:
            return [round(center, 3)]
        step = (budget.sample_radius_seconds * 2) / (budget.samples_per_anchor - 1)
        first = center - budget.sample_radius_seconds
        return [
            round(min(anchor.end, max(anchor.start, first + index * step)), 3)
            for index in range(budget.samples_per_anchor)
        ]
