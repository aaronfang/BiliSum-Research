from video_sum_core.transcript.models import (
    Transcript,
    TranscriptSegment,
    TranscriptSource,
)


def transcript_from_legacy(
    transcript_text: str,
    raw_segments: list[dict[str, object]],
    source: TranscriptSource,
) -> Transcript:
    segments: list[TranscriptSegment] = []
    for raw_segment in raw_segments:
        text = str(raw_segment.get("text") or "").strip()
        if not text:
            continue
        start = max(0.0, float(raw_segment.get("start") or 0))
        end = max(start, float(raw_segment.get("end") or start))
        confidence_value = raw_segment.get("confidence")
        confidence = None
        if confidence_value is not None:
            try:
                confidence = max(0.0, min(1.0, float(confidence_value)))
            except (TypeError, ValueError):
                confidence = None
        segments.append(
            TranscriptSegment(start=start, end=end, text=text, confidence=confidence)
        )
    if not segments and transcript_text.strip():
        segments.append(TranscriptSegment(start=0, end=0, text=transcript_text.strip()))
    return Transcript(source=source, segments=tuple(segments))
