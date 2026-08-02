from collections.abc import Callable
from pathlib import Path

from video_sum_core.evidence.engine import EvidenceEngine
from video_sum_core.evidence.models import FrameSample
from video_sum_core.transcript import MediaSource

RawFrame = dict[str, object]
ExtractFrames = Callable[[MediaSource, list[float], Path], list[RawFrame]]
ReadFrame = Callable[[RawFrame], tuple[str, float]]


def build_visual_evidence_engine(
    evidence_dir: Path,
    extract_frames: ExtractFrames,
    read_frame: ReadFrame,
) -> EvidenceEngine:
    raw_frames: dict[str, RawFrame] = {}
    extraction_count = 0

    class VisualFrameExtractor:
        def extract(
            self,
            source: MediaSource,
            timestamps: list[float],
        ) -> list[FrameSample]:
            nonlocal extraction_count
            extraction_count += 1
            frames_dir = evidence_dir / f"anchor-{extraction_count:03d}"
            frames_dir.mkdir(parents=True, exist_ok=True)
            frames = extract_frames(source, timestamps, frames_dir)
            samples: list[FrameSample] = []
            for frame in frames:
                frame_id = f"a{extraction_count:03d}-{frame['frame_id']}"
                frame["frame_id"] = frame_id
                raw_frames[frame_id] = frame
                samples.append(
                    FrameSample(
                        frame_id=frame_id,
                        timestamp=float(frame["timestamp_seconds"]),
                        path=Path(str(frame["_absolute_path"])),
                    )
                )
            return samples

    class VisualFrameTextReader:
        def read(self, frame: FrameSample) -> tuple[str, float]:
            raw_frame = raw_frames.get(frame.frame_id)
            if raw_frame is None:
                return "", 0.0
            return read_frame(raw_frame)

    return EvidenceEngine(
        frame_extractor=VisualFrameExtractor(),
        text_reader=VisualFrameTextReader(),
    )
