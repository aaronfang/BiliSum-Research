import re

from video_sum_core.evidence.models import TextAnchor
from video_sum_core.transcript import Transcript


class TextAnchorPlanner:
    _PATTERNS = (
        re.compile(r"`([^`\n]{2,120})`"),
        re.compile(r"https?://[^\s<]+"),
        re.compile(r"\bv?\d+(?:\.\d+){1,3}\b", re.IGNORECASE),
        re.compile(r"\b\d+(?:\.\d+)?\s?(?:ms|s|GB|MB|TB|%|x)\b", re.IGNORECASE),
        re.compile(r"\b(?:[A-Z]{2,}[A-Za-z0-9]*|[A-Z][a-z]+[A-Z][A-Za-z0-9]*)\b"),
        re.compile(r"\b(?:[A-Z][A-Za-z0-9_+/#-]*\s+){1,3}[A-Z][A-Za-z0-9_+/#-]*\b"),
    )

    def plan(self, transcript: Transcript) -> list[TextAnchor]:
        anchors: list[TextAnchor] = []
        for segment_index, segment in enumerate(transcript.segments):
            candidates: list[tuple[int, str]] = []
            for pattern in self._PATTERNS:
                for match in pattern.finditer(segment.text):
                    value = (match.group(1) if match.lastindex else match.group(0)).strip()
                    value = value.rstrip(".,;:!?)\"]}")
                    if value:
                        candidates.append((match.start(), value))
            seen: set[str] = set()
            candidate_index = 0
            for _position, value in sorted(candidates, key=lambda candidate: candidate[0]):
                normalized = value.casefold()
                if normalized in seen:
                    continue
                seen.add(normalized)
                anchors.append(
                    TextAnchor(
                        anchor_id=f"segment-{segment_index}-candidate-{candidate_index}",
                        start=segment.start,
                        end=segment.end,
                        query=value,
                    )
                )
                candidate_index += 1
        return anchors
