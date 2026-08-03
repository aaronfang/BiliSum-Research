import re
from collections import defaultdict
from dataclasses import dataclass
from difflib import SequenceMatcher

from video_sum_core.evidence import EvidenceItem, EvidenceKind, EvidenceSet
from video_sum_core.fusion.models import (
    CorrectedTranscript,
    Correction,
    CorrectionAlternative,
    CorrectionDecision,
)
from video_sum_core.transcript import Transcript, TranscriptSegment


@dataclass(frozen=True)
class _ScoredCandidate:
    score: float
    start: int
    end: int
    from_value: str
    to_value: str
    supporting: tuple[EvidenceItem, ...]


@dataclass(frozen=True)
class _CorrectionProposal:
    start: int
    end: int
    from_value: str
    to_value: str
    supporting: tuple[EvidenceItem, ...]
    confidence: float
    decision: CorrectionDecision
    alternatives: tuple[CorrectionAlternative, ...]


class FusionEngine:
    RULE_VERSION = "technical-token-v2"

    def reconcile(self, transcript: Transcript, evidence: EvidenceSet) -> CorrectedTranscript:
        segments = list(transcript.segments)
        corrections: list[Correction] = []
        for segment_index, segment in enumerate(transcript.segments):
            aligned = [item for item in evidence.items if self._overlaps(segment, item)]
            proposals = self._proposals(segment.text, aligned, evidence.context_hints)
            for proposal in proposals:
                corrections.append(
                    Correction(
                        segment_index=segment_index,
                        from_value=proposal.from_value,
                        to_value=proposal.to_value,
                        evidence_ids=tuple(
                            item.evidence_id for item in proposal.supporting
                        ),
                        confidence=proposal.confidence,
                        rule_version=self.RULE_VERSION,
                        decision=proposal.decision,
                        alternatives=proposal.alternatives,
                    )
                )
            accepted = [
                proposal
                for proposal in proposals
                if proposal.decision is CorrectionDecision.ACCEPTED
            ]
            segment_text = self._apply(segment.text, accepted)
            if segment_text != segment.text:
                segments[segment_index] = segment.model_copy(
                    update={"text": segment_text}
                )
        return CorrectedTranscript(
            original=transcript,
            segments=tuple(segments),
            corrections=tuple(corrections),
        )

    def _overlaps(self, segment: TranscriptSegment, item: EvidenceItem) -> bool:
        return item.start <= segment.end and item.end >= segment.start

    def _apply(self, text: str, proposals: list[_CorrectionProposal]) -> str:
        parts: list[str] = []
        cursor = 0
        for proposal in proposals:
            parts.append(text[cursor : proposal.start])
            parts.append(proposal.to_value)
            cursor = proposal.end
        parts.append(text[cursor:])
        return "".join(parts)

    def _proposals(
        self,
        segment_text: str,
        evidence: list[EvidenceItem],
        context_hints: tuple[str, ...],
    ) -> list[_CorrectionProposal]:
        grouped: dict[str, list[EvidenceItem]] = defaultdict(list)
        display_value: dict[str, str] = {}
        for item in evidence:
            for candidate in self._technical_candidates(item.observed_text):
                key = candidate.casefold()
                grouped[key].append(item)
                display_value[key] = candidate

        candidates: list[_ScoredCandidate] = []
        for key, supporting in grouped.items():
            candidate = display_value[key]
            match = self._nearest_window(segment_text, candidate)
            if match is None:
                continue
            from_value, similarity, start, end = match
            if from_value.casefold() == candidate.casefold() or similarity < 0.78:
                continue
            evidence_confidence = max(item.confidence for item in supporting)
            score = round(similarity * 0.55 + evidence_confidence * 0.45, 4)
            if any(candidate.casefold() in hint.casefold() for hint in context_hints):
                score = min(1.0, round(score + 0.02, 4))
            candidates.append(
                _ScoredCandidate(
                    score=score,
                    start=start,
                    end=end,
                    from_value=from_value,
                    to_value=candidate,
                    supporting=tuple(supporting),
                )
            )

        by_source: dict[tuple[int, int], list[_ScoredCandidate]] = defaultdict(list)
        for candidate in candidates:
            by_source[(candidate.start, candidate.end)].append(candidate)

        proposals: list[_CorrectionProposal] = []
        for grouped_candidates in by_source.values():
            grouped_candidates = self._merge_truncated_candidates(grouped_candidates)
            grouped_candidates.sort(key=lambda proposal: proposal.score, reverse=True)
            winner = grouped_candidates[0]
            competing = grouped_candidates[1:]
            has_visual_support = self._has_qualifying_visual_support(winner)
            decision = (
                CorrectionDecision.ACCEPTED
                if has_visual_support and not competing and winner.score >= 0.88
                else CorrectionDecision.UNCERTAIN
            )
            alternatives = ()
            if decision is CorrectionDecision.UNCERTAIN:
                alternatives = tuple(
                    CorrectionAlternative(
                        value=item.to_value,
                        evidence_ids=tuple(
                            evidence.evidence_id for evidence in item.supporting
                        ),
                        confidence=item.score,
                    )
                    for item in grouped_candidates
                )
            proposals.append(
                _CorrectionProposal(
                    start=winner.start,
                    end=winner.end,
                    from_value=winner.from_value,
                    to_value=winner.to_value,
                    supporting=winner.supporting,
                    confidence=winner.score,
                    decision=decision,
                    alternatives=alternatives,
                )
            )
        selected: list[_CorrectionProposal] = []
        for proposal in sorted(
            proposals,
            key=lambda item: (item.end - item.start, -item.confidence, item.start),
        ):
            if any(
                proposal.start < existing.end and proposal.end > existing.start
                for existing in selected
            ):
                continue
            selected.append(proposal)
        return sorted(selected, key=lambda proposal: proposal.start)

    def _merge_truncated_candidates(
        self,
        candidates: list[_ScoredCandidate],
    ) -> list[_ScoredCandidate]:
        merged: list[_ScoredCandidate] = []
        for candidate in sorted(
            candidates,
            key=lambda item: len(item.to_value),
            reverse=True,
        ):
            longer_candidate = next(
                (
                    item
                    for item in merged
                    if self._is_truncated_variant(candidate.to_value, item.to_value)
                    and self._has_qualifying_visual_support(candidate)
                    and self._has_qualifying_visual_support(item)
                ),
                None,
            )
            if longer_candidate is None:
                merged.append(candidate)
                continue
            supporting_by_id = {
                item.evidence_id: item
                for item in (*longer_candidate.supporting, *candidate.supporting)
            }
            merged[merged.index(longer_candidate)] = _ScoredCandidate(
                score=max(longer_candidate.score, candidate.score),
                start=longer_candidate.start,
                end=longer_candidate.end,
                from_value=longer_candidate.from_value,
                to_value=longer_candidate.to_value,
                supporting=tuple(
                    sorted(
                        supporting_by_id.values(),
                        key=lambda item: (item.start, item.end, item.evidence_id),
                    )
                ),
            )
        return merged

    def _has_qualifying_visual_support(self, candidate: _ScoredCandidate) -> bool:
        return any(
            item.kind is EvidenceKind.FRAME_OCR and item.confidence >= 0.85
            for item in candidate.supporting
        )

    def _is_truncated_variant(self, shorter: str, longer: str) -> bool:
        shorter_words = shorter.casefold().split()
        longer_words = longer.casefold().split()
        if len(shorter_words) != len(longer_words) or not shorter_words:
            return False
        if shorter_words[:-1] != longer_words[:-1]:
            return False
        shorter_tail = shorter_words[-1]
        longer_tail = longer_words[-1]
        missing_characters = len(longer_tail) - len(shorter_tail)
        return (
            len(shorter_tail) >= 8
            and missing_characters == 1
            and longer_tail.startswith(shorter_tail)
            and shorter_tail.endswith("in")
            and longer_tail.endswith("ing")
        )

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
            candidates.extend(
                match.group(0)
                for match in re.finditer(
                    r"\b[A-Z][A-Za-z0-9_+/#.-]*\s+v?\d+(?:\.\d+){1,3}\b",
                    line,
                )
            )
        return list(dict.fromkeys(value for value in candidates if value))

    def _nearest_window(
        self,
        text: str,
        candidate: str,
    ) -> tuple[str, float, int, int] | None:
        if candidate.casefold().startswith(("http://", "https://")):
            return self._nearest_url_window(text, candidate)
        word_count = len(candidate.split())
        token_pattern = r"[A-Za-z0-9_+/#-]+(?:\.[A-Za-z0-9_+/#-]+)*"
        matches = list(re.finditer(token_pattern, text))
        if len(matches) < word_count:
            return None
        best: tuple[str, float, int, int] | None = None
        for index in range(len(matches) - word_count + 1):
            start = matches[index].start()
            end = matches[index + word_count - 1].end()
            window = text[start:end]
            similarity = self._technical_similarity(window, candidate)
            if best is None or similarity > best[1]:
                best = (window, similarity, start, end)
        return best

    def _nearest_url_window(
        self,
        text: str,
        candidate: str,
    ) -> tuple[str, float, int, int] | None:
        url_pattern = r"(?<![A-Za-z0-9+.-])[A-Za-z][A-Za-z0-9+.-]*://[^\s<>\"']+"
        best: tuple[str, float, int, int] | None = None
        for match in re.finditer(url_pattern, text):
            start = match.start()
            window = match.group(0).rstrip(".,;:!?)]}\"'，。！？；：、…")
            if not window:
                continue
            end = start + len(window)
            similarity = self._technical_similarity(window, candidate)
            if best is None or similarity > best[1]:
                best = (window, similarity, start, end)
        return best

    def _technical_similarity(self, observed: str, candidate: str) -> float:
        observed_words = observed.casefold().split()
        candidate_words = candidate.casefold().split()
        whole_phrase = SequenceMatcher(
            None,
            observed.casefold(),
            candidate.casefold(),
        ).ratio()
        if len(observed_words) != len(candidate_words):
            return whole_phrase

        word_scores: list[float] = []
        for observed_word, candidate_word in zip(observed_words, candidate_words, strict=True):
            if (
                min(len(observed_word), len(candidate_word)) >= 4
                and (
                    observed_word.startswith(candidate_word)
                    or candidate_word.startswith(observed_word)
                )
            ):
                word_scores.append(1.0)
            else:
                word_scores.append(
                    SequenceMatcher(None, observed_word, candidate_word).ratio()
                )
        return max(whole_phrase, sum(word_scores) / len(word_scores))
