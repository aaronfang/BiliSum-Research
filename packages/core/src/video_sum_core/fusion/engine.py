import re
from collections import defaultdict
from difflib import SequenceMatcher

from video_sum_core.evidence import EvidenceItem, EvidenceKind, EvidenceSet
from video_sum_core.fusion.models import (
    CorrectedTranscript,
    Correction,
    CorrectionAlternative,
    CorrectionDecision,
)
from video_sum_core.transcript import Transcript, TranscriptSegment


class FusionEngine:
    RULE_VERSION = "technical-token-v1"
    def reconcile(self, transcript: Transcript, evidence: EvidenceSet) -> CorrectedTranscript:
        segments = list(transcript.segments)
        corrections: list[Correction] = []
        for segment_index, segment in enumerate(transcript.segments):
            aligned = [item for item in evidence.items if self._overlaps(segment, item)]
            proposal = self._best_proposal(segment.text, aligned, evidence.context_hints)
            if proposal is None:
                continue
            from_value, to_value, supporting, confidence, decision, alternatives = proposal
            corrections.append(
                Correction(
                    segment_index=segment_index,
                    from_value=from_value,
                    to_value=to_value,
                    evidence_ids=tuple(item.evidence_id for item in supporting),
                    confidence=confidence,
                    rule_version=self.RULE_VERSION,
                    decision=decision,
                    alternatives=alternatives,
                )
            )
            if decision is CorrectionDecision.ACCEPTED:
                segments[segment_index] = segment.model_copy(
                    update={"text": segment.text.replace(from_value, to_value, 1)}
                )
        return CorrectedTranscript(
            original=transcript,
            segments=tuple(segments),
            corrections=tuple(corrections),
        )

    def _overlaps(self, segment: TranscriptSegment, item: EvidenceItem) -> bool:
        return item.start <= segment.end and item.end >= segment.start

    def _best_proposal(
        self,
        segment_text: str,
        evidence: list[EvidenceItem],
        context_hints: tuple[str, ...],
    ) -> tuple[
        str,
        str,
        list[EvidenceItem],
        float,
        CorrectionDecision,
        tuple[CorrectionAlternative, ...],
    ] | None:
        grouped: dict[str, list[EvidenceItem]] = defaultdict(list)
        display_value: dict[str, str] = {}
        for item in evidence:
            for candidate in self._technical_candidates(item.observed_text):
                key = candidate.casefold()
                grouped[key].append(item)
                display_value[key] = candidate

        proposals: list[tuple[float, str, str, list[EvidenceItem]]] = []
        for key, supporting in grouped.items():
            candidate = display_value[key]
            match = self._nearest_window(segment_text, candidate)
            if match is None:
                continue
            from_value, similarity = match
            if from_value.casefold() == candidate.casefold() or similarity < 0.78:
                continue
            evidence_confidence = max(item.confidence for item in supporting)
            score = round(similarity * 0.55 + evidence_confidence * 0.45, 4)
            if any(candidate.casefold() in hint.casefold() for hint in context_hints):
                score = min(1.0, round(score + 0.02, 4))
            proposals.append((score, from_value, candidate, supporting))

        if not proposals:
            return None
        proposals.sort(key=lambda proposal: proposal[0], reverse=True)
        score, from_value, candidate, supporting = proposals[0]
        competing = [
            proposal
            for proposal in proposals[1:]
            if proposal[1].casefold() == from_value.casefold() and proposal[0] >= score - 0.05
        ]
        has_visual_support = any(
            item.kind is EvidenceKind.FRAME_OCR and item.confidence >= 0.85
            for item in supporting
        )
        decision = (
            CorrectionDecision.ACCEPTED
            if has_visual_support and not competing and score >= 0.88
            else CorrectionDecision.UNCERTAIN
        )
        alternatives = ()
        if decision is CorrectionDecision.UNCERTAIN:
            alternatives = tuple(
                CorrectionAlternative(
                    value=proposal_candidate,
                    evidence_ids=tuple(item.evidence_id for item in proposal_supporting),
                    confidence=proposal_score,
                )
                for proposal_score, _proposal_from, proposal_candidate, proposal_supporting in (
                    [proposals[0], *competing]
                )
            )
        return from_value, candidate, supporting, score, decision, alternatives

    def _technical_candidates(self, observed_text: str) -> list[str]:
        candidates: list[str] = []
        for line in observed_text.splitlines():
            candidate = re.sub(r"\s+", " ", line).strip(" \t.,;:!?()[]{}\"'")
            words = candidate.split()
            if (
                1 <= len(words) <= 5
                and all(re.fullmatch(r"[A-Za-z0-9_.+/#-]+", word) for word in words)
                and (
                    (len(words) >= 2 and any(word[:1].isupper() for word in words))
                    or any(re.search(r"[0-9_.+/#-]", word) for word in words)
                )
            ):
                candidates.append(candidate)

            title_phrase = re.compile(
                r"\b(?:[A-Z][A-Za-z0-9_+/#.-]*\s+){1,3}[A-Z][A-Za-z0-9_+/#.-]*\b"
            )
            candidates.extend(match.group(0) for match in title_phrase.finditer(line))
            candidates.extend(
                match.group(0).rstrip(".,;:!?)\"]}")
                for match in re.finditer(r"https?://[^\s<]+", line)
            )
        return list(dict.fromkeys(value for value in candidates if value))

    def _nearest_window(self, text: str, candidate: str) -> tuple[str, float] | None:
        word_count = len(candidate.split())
        token_pattern = r"[A-Za-z0-9_+/#-]+(?:\.[A-Za-z0-9_+/#-]+)*"
        matches = list(re.finditer(token_pattern, text))
        if len(matches) < word_count:
            return None
        best: tuple[str, float] | None = None
        for index in range(len(matches) - word_count + 1):
            start = matches[index].start()
            end = matches[index + word_count - 1].end()
            window = text[start:end]
            similarity = SequenceMatcher(None, window.casefold(), candidate.casefold()).ratio()
            if best is None or similarity > best[1]:
                best = (window, similarity)
        return best
