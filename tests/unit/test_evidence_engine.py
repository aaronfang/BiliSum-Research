from pathlib import Path

from video_sum_core.evidence import (
    EvidenceBudget,
    EvidenceEngine,
    EvidenceKind,
    FrameObservation,
    FrameSample,
    MediaSource,
    TextAnchor,
    TextAnchorPlanner,
)
from video_sum_core.transcript import (
    Transcript,
    TranscriptSegment,
    TranscriptSource,
    TranscriptSourceKind,
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
    def read(self, frame: FrameSample) -> FrameObservation:
        return FrameObservation(text="Loop Engineering", confidence=0.98)


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
    assert len(evidence.items) == 1
    assert all(item.kind is EvidenceKind.FRAME_OCR for item in evidence.items)
    assert all(item.observed_text == "Loop Engineering" for item in evidence.items)
    assert all(item.anchor_id == "a1" for item in evidence.items)
    assert all(item.media_ref == str(media.path) for item in evidence.items)


def test_collect_ranks_quality_and_retains_scene_or_ocr_changes(tmp_path: Path) -> None:
    media = MediaSource(path=tmp_path / "loop-engineering.mp4")
    extractor = RecordingFrameExtractor()

    class ChangingFrameReader:
        def read(self, frame: FrameSample) -> FrameObservation:
            observations = {
                "frame-0": FrameObservation(
                    text="Loop Engineering",
                    confidence=0.92,
                    scene_signature="slide-a",
                    quality_score=0.4,
                ),
                "frame-1": FrameObservation(
                    text="Loop Engineering",
                    confidence=0.97,
                    scene_signature="slide-a",
                    quality_score=0.9,
                ),
                "frame-2": FrameObservation(
                    text="Loop Engineering workflow",
                    confidence=0.95,
                    scene_signature="slide-b",
                    quality_score=0.8,
                ),
            }
            return observations[frame.frame_id]

    engine = EvidenceEngine(frame_extractor=extractor, text_reader=ChangingFrameReader())

    evidence = engine.collect(
        media,
        [TextAnchor(anchor_id="a1", start=11.0, end=14.0, query="Loof Engineering")],
        EvidenceBudget(max_frames=3, samples_per_anchor=3, sample_radius_seconds=0.5),
    )

    assert [item.source_ref for item in evidence.items] == [
        str(tmp_path / "frame-1.jpg"),
        str(tmp_path / "frame-2.jpg"),
    ]


def test_text_anchor_planner_covers_commands_urls_versions_numbers_and_tool_names() -> None:
    transcript = Transcript(
        source=TranscriptSource(
            kind=TranscriptSourceKind.ASR,
            location="audio.wav",
            automatic=True,
        ),
        segments=(
            TranscriptSegment(
                start=20,
                end=30,
                text=(
                    "Run `kubectl apply`, then open https://example.com/docs for PostgreSQL "
                    "v1.2.3; the timeout is 500ms."
                ),
            ),
        ),
    )

    queries = {anchor.query for anchor in TextAnchorPlanner().plan(transcript)}

    assert "kubectl apply" in queries
    assert "https://example.com/docs" in queries
    assert "PostgreSQL" in queries
    assert "v1.2.3" in queries
    assert "500ms" in queries
