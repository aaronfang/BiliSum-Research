from pathlib import Path

from video_sum_core.transcript import (
    MediaSource,
    Transcript,
    TranscriptPolicy,
    TranscriptResolver,
    TranscriptSegment,
    TranscriptSource,
    TranscriptSourceKind,
)


class UnexpectedAsrAdapter:
    def transcribe(self, source: MediaSource):
        raise AssertionError(f"ASR must not run when an accepted sidecar exists: {source.path}")


class StubAsrAdapter:
    def transcribe(self, source: MediaSource) -> Transcript:
        return Transcript(
            source=TranscriptSource(
                kind=TranscriptSourceKind.ASR,
                location=str(source.path),
                model="stub-asr",
                automatic=True,
            ),
            segments=(TranscriptSegment(start=0, end=2, text="Loof Engineering"),),
        )


def test_resolve_prefers_same_stem_srt_and_retains_provenance(tmp_path: Path) -> None:
    media_path = tmp_path / "loop-engineering.mp4"
    media_path.write_bytes(b"video")
    sidecar_path = tmp_path / "loop-engineering.srt"
    sidecar_path.write_text(
        "1\n00:00:11,000 --> 00:00:14,500\nLoop Engineering\n",
        encoding="utf-8",
    )

    transcript = TranscriptResolver(asr_adapter=UnexpectedAsrAdapter()).resolve(
        MediaSource(path=media_path),
        TranscriptPolicy(prefer_subtitles=True),
    )

    assert transcript.source.kind is TranscriptSourceKind.SIDECAR
    assert transcript.source.location == str(sidecar_path)
    assert transcript.text == "Loop Engineering"
    assert transcript.segments[0].start == 11.0
    assert transcript.segments[0].end == 14.5
    assert transcript.segments[0].text == "Loop Engineering"


def test_resolve_falls_back_to_asr_with_explicit_provenance(tmp_path: Path) -> None:
    media_path = tmp_path / "loop-engineering.mp4"
    media_path.write_bytes(b"video")

    transcript = TranscriptResolver(asr_adapter=StubAsrAdapter()).resolve(
        MediaSource(path=media_path),
        TranscriptPolicy(prefer_subtitles=True),
    )

    assert transcript.source.kind is TranscriptSourceKind.ASR
    assert transcript.source.model == "stub-asr"
    assert transcript.source.automatic is True
    assert transcript.source.fallback_reason == "no accepted sidecar subtitle"
    assert transcript.text == "Loof Engineering"


def test_resolve_reads_same_stem_webvtt_when_srt_is_absent(tmp_path: Path) -> None:
    media_path = tmp_path / "loop-engineering.mp4"
    media_path.write_bytes(b"video")
    sidecar_path = tmp_path / "loop-engineering.vtt"
    sidecar_path.write_text(
        "WEBVTT\n\n00:11.000 --> 00:14.500\nLoop Engineering\n",
        encoding="utf-8",
    )

    transcript = TranscriptResolver(asr_adapter=UnexpectedAsrAdapter()).resolve(
        MediaSource(path=media_path),
        TranscriptPolicy(prefer_subtitles=True),
    )

    assert transcript.source.format == "vtt"
    assert transcript.segments[0].start == 11.0
    assert transcript.segments[0].end == 14.5
