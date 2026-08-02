import re
from collections.abc import Callable
from pathlib import Path
from typing import Protocol

from video_sum_core.errors import VideoSumError
from video_sum_core.transcript.models import (
    MediaSource,
    Transcript,
    TranscriptPolicy,
    TranscriptSegment,
    TranscriptSource,
    TranscriptSourceKind,
)


class AsrAdapter(Protocol):
    def transcribe(self, source: MediaSource) -> Transcript: ...


class CallableAsrAdapter:
    def __init__(self, callback: Callable[[MediaSource], Transcript]) -> None:
        self._callback = callback

    def transcribe(self, source: MediaSource) -> Transcript:
        return self._callback(source)


class TranscriptResolver:
    def __init__(self, asr_adapter: AsrAdapter | None = None) -> None:
        self._asr_adapter = asr_adapter

    def resolve(self, source: MediaSource, policy: TranscriptPolicy) -> Transcript:
        fallback_reason = "subtitle preference disabled"
        if policy.prefer_subtitles:
            sidecar = self._find_sidecar(source.path)
            if sidecar is not None:
                try:
                    return self._read_sidecar(sidecar)
                except VideoSumError as exc:
                    fallback_reason = str(exc)
            else:
                fallback_reason = "no accepted sidecar subtitle"
        if self._asr_adapter is None:
            raise VideoSumError(f"No accepted subtitle or ASR adapter for media: {source.path}")
        transcript = self._asr_adapter.transcribe(source)
        return transcript.model_copy(
            update={
                "source": transcript.source.model_copy(
                    update={"fallback_reason": fallback_reason}
                )
            }
        )

    def _find_sidecar(self, media_path: Path) -> Path | None:
        for suffix in (".srt", ".vtt"):
            candidate = media_path.with_suffix(suffix)
            if candidate.is_file():
                return candidate
        return None

    def _read_sidecar(self, path: Path) -> Transcript:
        text = path.read_text(encoding="utf-8-sig")
        segments = self._parse_srt(text) if path.suffix.lower() == ".srt" else self._parse_vtt(text)
        if not segments:
            raise VideoSumError(f"Sidecar subtitle contains no usable timed text: {path}")
        return Transcript(
            source=TranscriptSource(
                kind=TranscriptSourceKind.SIDECAR,
                location=str(path),
                format=path.suffix.lower().lstrip("."),
            ),
            segments=tuple(segments),
        )

    def _parse_srt(self, text: str) -> list[TranscriptSegment]:
        segments: list[TranscriptSegment] = []
        for block in re.split(r"\r?\n\s*\r?\n", text.strip()):
            lines = [line.strip() for line in block.splitlines() if line.strip()]
            timing_index = next((index for index, line in enumerate(lines) if "-->" in line), None)
            if timing_index is None:
                continue
            segment = self._segment_from_lines(lines[timing_index], lines[timing_index + 1 :])
            if segment is not None:
                segments.append(segment)
        return segments

    def _parse_vtt(self, text: str) -> list[TranscriptSegment]:
        content = re.sub(r"^\ufeff?WEBVTT[^\n]*\r?\n", "", text, count=1)
        return self._parse_srt(content)

    def _segment_from_lines(self, timing: str, text_lines: list[str]) -> TranscriptSegment | None:
        match = re.match(r"\s*([^ ]+)\s+-->\s+([^ ]+)", timing)
        cue_text = " ".join(text_lines).strip()
        if match is None or not cue_text:
            return None
        start = self._parse_timestamp(match.group(1))
        end = self._parse_timestamp(match.group(2))
        if start is None or end is None or end < start:
            return None
        return TranscriptSegment(start=start, end=end, text=cue_text)

    def _parse_timestamp(self, value: str) -> float | None:
        normalized = value.strip().replace(",", ".")
        parts = normalized.split(":")
        if len(parts) not in {2, 3}:
            return None
        try:
            seconds = float(parts[-1])
            minutes = int(parts[-2])
            hours = int(parts[-3]) if len(parts) == 3 else 0
        except ValueError:
            return None
        return hours * 3600 + minutes * 60 + seconds
