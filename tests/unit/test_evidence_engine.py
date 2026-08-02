from pathlib import Path

from video_sum_core.evidence import (
    EvidenceBudget,
    EvidenceEngine,
    EvidenceKind,
    FrameSample,
    MediaSource,
    TextAnchor,
)


class RecordingFrameExtractor:
    def __init__(self) -> None:
        self.timestamps: list[float] = []

    def extract(self, media: MediaSource, timestamps: list[float]) -> list[FrameSample]:
        self.timestamps = timestamps
        return [
            FrameSample(
                frame_id=f"frame-{index}",
                timestamp=timestamp,
                path=media.path.parent / f"frame-{index}.jpg",
            )
            for index, timestamp in enumerate(timestamps)
        ]


class LoopEngineeringReader:
    def read(self, frame: FrameSample) -> tuple[str, float]:
        return "Loop Engineering", 0.98


def test_collect_inspects_only_frames_around_the_text_anchor(tmp_path: Path) -> None:
    media = MediaSource(path=tmp_path / "loop-engineering.mp4")
    extractor = RecordingFrameExtractor()
    engine = EvidenceEngine(frame_extractor=extractor, text_reader=LoopEngineeringReader())

    evidence = engine.collect(
        media,
        [TextAnchor(anchor_id="a1", start=11.0, end=14.0, query="Loof Engineering")],
        EvidenceBudget(max_frames=3, samples_per_anchor=3, sample_radius_seconds=0.5),
    )

    assert extractor.timestamps == [12.0, 12.5, 13.0]
    assert len(evidence.items) == 3
    assert all(item.kind is EvidenceKind.FRAME_OCR for item in evidence.items)
    assert all(item.observed_text == "Loop Engineering" for item in evidence.items)
    assert all(item.anchor_id == "a1" for item in evidence.items)
