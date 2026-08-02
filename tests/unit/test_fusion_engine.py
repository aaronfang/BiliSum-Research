from video_sum_core.evidence import EvidenceItem, EvidenceKind, EvidenceSet
from video_sum_core.fusion import CorrectionDecision, FusionEngine
from video_sum_core.transcript import (
    Transcript,
    TranscriptSegment,
    TranscriptSource,
    TranscriptSourceKind,
)


def test_reconcile_corrects_technical_token_when_aligned_frame_evidence_supports_it() -> None:
    raw = Transcript(
        source=TranscriptSource(
            kind=TranscriptSourceKind.ASR,
            location="audio.wav",
            model="local-asr",
            automatic=True,
        ),
        segments=(
            TranscriptSegment(
                start=11,
                end=14,
                text="My job is to write loops. We call it Loof Engineering.",
            ),
        ),
    )
    evidence = EvidenceSet(
        items=(
            EvidenceItem(
                evidence_id="frame-1",
                kind=EvidenceKind.FRAME_OCR,
                observed_text="Loop Engineering",
                start=12,
                end=12,
                confidence=0.98,
                derivation_method="frame_ocr",
                source_ref="frame-1.jpg",
                media_ref="video.mp4",
                anchor_id="anchor-1",
            ),
        )
    )

    corrected = FusionEngine().reconcile(raw, evidence)

    assert raw.text.endswith("Loof Engineering.")
    assert corrected.text.endswith("Loop Engineering.")
    assert corrected.original is raw
    assert len(corrected.corrections) == 1
    assert corrected.corrections[0].from_value == "Loof Engineering"
    assert corrected.corrections[0].to_value == "Loop Engineering"
    assert corrected.corrections[0].evidence_ids == ("frame-1",)
    assert corrected.corrections[0].decision is CorrectionDecision.ACCEPTED


def test_reconcile_corrects_multiple_independent_tokens_in_one_segment() -> None:
    raw = Transcript(
        source=TranscriptSource(
            kind=TranscriptSourceKind.ASR,
            location="audio.wav",
            automatic=True,
        ),
        segments=(
            TranscriptSegment(
                start=11,
                end=14,
                text="Loof Engineering uses Pythom 3.12",
            ),
        ),
    )
    evidence = EvidenceSet(
        items=(
            EvidenceItem(
                evidence_id="frame-loop",
                kind=EvidenceKind.FRAME_OCR,
                observed_text="Loop Engineering",
                start=12,
                end=12,
                confidence=0.98,
                derivation_method="frame_ocr_scene_quality",
                source_ref="frame-loop.jpg",
                media_ref="video.mp4",
            ),
            EvidenceItem(
                evidence_id="frame-python",
                kind=EvidenceKind.FRAME_OCR,
                observed_text="Python 3.12",
                start=12.5,
                end=12.5,
                confidence=0.98,
                derivation_method="frame_ocr_scene_quality",
                source_ref="frame-python.jpg",
                media_ref="video.mp4",
            ),
        )
    )

    corrected = FusionEngine().reconcile(raw, evidence)

    assert corrected.text == "Loop Engineering uses Python 3.12"
    assert {(item.from_value, item.to_value) for item in corrected.corrections} == {
        ("Loof Engineering", "Loop Engineering"),
        ("Pythom 3.12", "Python 3.12"),
    }


def test_reconcile_does_not_audit_overlapping_noop_corrections() -> None:
    raw = Transcript(
        source=TranscriptSource(
            kind=TranscriptSourceKind.ASR,
            location="audio.wav",
            automatic=True,
        ),
        segments=(
            TranscriptSegment(
                start=11,
                end=14,
                text="Loof Engineering uses Pythom 3.12",
            ),
        ),
    )
    evidence = EvidenceSet(
        items=(
            EvidenceItem(
                evidence_id="frame-combined",
                kind=EvidenceKind.FRAME_OCR,
                observed_text="Loop Engineering uses Python 3.12",
                start=12,
                end=12,
                confidence=0.98,
                derivation_method="frame_ocr_scene_quality",
                source_ref="frame-combined.jpg",
                media_ref="video.mp4",
            ),
        )
    )

    corrected = FusionEngine().reconcile(raw, evidence)

    assert corrected.text == "Loop Engineering uses Python 3.12"
    assert {(item.from_value, item.to_value) for item in corrected.corrections} == {
        ("Loof Engineering", "Loop Engineering"),
        ("Pythom 3.12", "Python 3.12"),
    }
    assert all(item.decision is CorrectionDecision.ACCEPTED for item in corrected.corrections)


def test_reconcile_keeps_conflicting_visual_candidates_as_uncertain() -> None:
    raw = Transcript(
        source=TranscriptSource(
            kind=TranscriptSourceKind.ASR,
            location="audio.wav",
            automatic=True,
        ),
        segments=(TranscriptSegment(start=11, end=14, text="Loof Engineering"),),
    )
    evidence = EvidenceSet(
        items=(
            EvidenceItem(
                evidence_id="frame-1",
                kind=EvidenceKind.FRAME_OCR,
                observed_text="Loop Engineering",
                start=12,
                end=12,
                confidence=0.99,
                derivation_method="frame_ocr",
                source_ref="frame-1.jpg",
                media_ref="video.mp4",
            ),
            EvidenceItem(
                evidence_id="frame-2",
                kind=EvidenceKind.FRAME_OCR,
                observed_text="Look Engineering",
                start=12.5,
                end=12.5,
                confidence=0.85,
                derivation_method="frame_ocr",
                source_ref="frame-2.jpg",
                media_ref="video.mp4",
            ),
        )
    )

    corrected = FusionEngine().reconcile(raw, evidence)

    assert corrected.text == "Loof Engineering"
    assert len(corrected.corrections) == 1
    assert corrected.corrections[0].decision is CorrectionDecision.UNCERTAIN
    assert {item.value for item in corrected.corrections[0].alternatives} == {
        "Loop Engineering",
        "Look Engineering",
    }


def test_reconcile_audits_subtitle_asr_visual_and_context_support_together() -> None:
    raw = Transcript(
        source=TranscriptSource(
            kind=TranscriptSourceKind.ASR,
            location="primary.wav",
            automatic=True,
        ),
        segments=(TranscriptSegment(start=11, end=14, text="Loof Engineering"),),
    )
    evidence = EvidenceSet(
        items=tuple(
            EvidenceItem(
                evidence_id=evidence_id,
                kind=kind,
                observed_text="Loop Engineering",
                start=11,
                end=14,
                confidence=confidence,
                derivation_method=kind.value,
                source_ref=evidence_id,
                media_ref="video.mp4",
            )
            for evidence_id, kind, confidence in (
                ("subtitle-1", EvidenceKind.SUBTITLE, 0.97),
                ("asr-2", EvidenceKind.ASR, 0.74),
                ("frame-1", EvidenceKind.FRAME_OCR, 0.98),
            )
        ),
        context_hints=("Loop Engineering",),
    )

    corrected = FusionEngine().reconcile(raw, evidence)

    assert corrected.text == "Loop Engineering"
    assert corrected.corrections[0].decision is CorrectionDecision.ACCEPTED
    assert corrected.corrections[0].evidence_ids == (
        "subtitle-1",
        "asr-2",
        "frame-1",
    )


def test_reconcile_extracts_technical_candidate_from_a_full_subtitle_sentence() -> None:
    raw = Transcript(
        source=TranscriptSource(
            kind=TranscriptSourceKind.ASR,
            location="primary.wav",
            automatic=True,
        ),
        segments=(TranscriptSegment(start=11, end=14, text="We call it Loof Engineering."),),
    )
    evidence = EvidenceSet(
        items=(
            EvidenceItem(
                evidence_id="subtitle-1",
                kind=EvidenceKind.SUBTITLE,
                observed_text="In this talk we call it Loop Engineering.",
                start=11,
                end=14,
                confidence=0.97,
                derivation_method="sidecar",
                source_ref="talk.srt",
                media_ref="talk.mp4",
            ),
        )
    )

    corrected = FusionEngine().reconcile(raw, evidence)

    assert corrected.text == "We call it Loof Engineering."
    assert corrected.corrections[0].evidence_ids == ("subtitle-1",)
    assert corrected.corrections[0].decision is CorrectionDecision.UNCERTAIN
