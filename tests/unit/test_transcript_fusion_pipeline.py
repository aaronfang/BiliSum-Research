import json
from pathlib import Path

from video_sum_core.evidence import EvidenceItem, EvidenceKind, EvidenceSet, TextAnchor
from video_sum_core.models.tasks import InputType
from video_sum_core.pipeline.base import PipelineContext
from video_sum_core.pipeline.real import PipelineSettings, RealPipelineRunner
from video_sum_core.transcript import (
    MediaSource,
    Transcript,
    TranscriptPolicy,
    TranscriptSegment,
    TranscriptSource,
    TranscriptSourceKind,
)


class LoofAsrResolver:
    def resolve(self, source: MediaSource, policy: TranscriptPolicy) -> Transcript:
        return Transcript(
            source=TranscriptSource(
                kind=TranscriptSourceKind.ASR,
                location=str(source.path),
                model="stub-asr",
                automatic=True,
            ),
            segments=(
                TranscriptSegment(start=11, end=14, text="We call it Loof Engineering."),
            ),
        )


class LoopVisualEvidenceEngine:
    def collect(self, media: MediaSource, anchors: list[TextAnchor], budget) -> EvidenceSet:
        assert any(anchor.query == "Loof Engineering" for anchor in anchors)
        return EvidenceSet(
            items=(
                EvidenceItem(
                    evidence_id="frame-1",
                    kind=EvidenceKind.FRAME_OCR,
                    observed_text="Loop Engineering",
                    start=12,
                    end=12,
                    confidence=0.98,
                    derivation_method="frame_ocr",
                    source_ref=str(media.path.parent / "frame-1.jpg"),
                    media_ref=str(media.path),
                    anchor_id=anchors[0].anchor_id,
                ),
            )
        )


class LoopAsrAdapter:
    def transcribe(self, source: MediaSource) -> Transcript:
        return Transcript(
            source=TranscriptSource(
                kind=TranscriptSourceKind.ASR,
                location=str(source.path),
                model="supporting-asr",
                automatic=True,
            ),
            segments=(TranscriptSegment(start=11, end=14, text="Loop Engineering"),),
        )


def test_local_media_run_uses_sidecar_without_asr_and_exports_provenance(tmp_path: Path) -> None:
    media_path = tmp_path / "loop-engineering.mp3"
    media_path.write_bytes(b"sidecar means these bytes are never decoded")
    sidecar_path = tmp_path / "loop-engineering.srt"
    sidecar_path.write_text(
        "1\n00:00:11,000 --> 00:00:14,500\nLoop Engineering\n",
        encoding="utf-8",
    )
    runner = RealPipelineRunner(
        PipelineSettings(
            tasks_dir=tmp_path / "tasks",
            llm_enabled=False,
            local_asr_available=False,
        )
    )

    _events, result = runner.run(
        PipelineContext(
            task_id="task-sidecar",
            task_input={
                "input_type": InputType.AUDIO_FILE,
                "source": str(media_path),
                "title": "Loop Engineering",
            },
        )
    )

    assert "Loop Engineering" in result.transcript_text
    provenance_path = Path(result.artifacts["transcript_provenance_path"])
    provenance = json.loads(provenance_path.read_text(encoding="utf-8"))
    assert provenance["primary"]["kind"] == "sidecar"
    assert provenance["primary"]["location"] == str(sidecar_path)


def test_local_media_run_uses_corrected_transcript_and_exports_audit(tmp_path: Path) -> None:
    media_path = tmp_path / "loop-engineering.mp3"
    media_path.write_bytes(b"the injected resolver does not decode this")
    runner = RealPipelineRunner(
        PipelineSettings(
            tasks_dir=tmp_path / "tasks",
            llm_enabled=False,
            transcript_fusion_enabled=True,
        ),
        transcript_resolver=LoofAsrResolver(),
        evidence_engine=LoopVisualEvidenceEngine(),
    )

    _events, result = runner.run(
        PipelineContext(
            task_id="task-fusion",
            task_input={
                "input_type": InputType.AUDIO_FILE,
                "source": str(media_path),
                "title": "Loop Engineering",
            },
        )
    )

    assert "Loop Engineering" in result.transcript_text
    assert "Loof Engineering" not in result.transcript_text
    assert "Loof Engineering" in Path(result.artifacts["raw_transcript_path"]).read_text(
        encoding="utf-8"
    )
    assert "Loop Engineering" in Path(result.artifacts["corrected_transcript_path"]).read_text(
        encoding="utf-8"
    )
    audit = json.loads(
        Path(result.artifacts["correction_audit_path"]).read_text(encoding="utf-8")
    )
    assert audit["corrections"][0]["decision"] == "accepted"
    assert audit["corrections"][0]["evidence_ids"] == ["frame-1"]
    assert audit["context_hints"] == ["Loop Engineering"]


def test_local_media_fusion_combines_sidecar_asr_and_visual_evidence(tmp_path: Path) -> None:
    media_path = tmp_path / "loop-engineering.mp3"
    media_path.write_bytes(b"sidecar and injected ASR avoid decoding this")
    (tmp_path / "loop-engineering.srt").write_text(
        "1\n00:00:11,000 --> 00:00:14,000\nLoof Engineering\n",
        encoding="utf-8",
    )
    runner = RealPipelineRunner(
        PipelineSettings(
            tasks_dir=tmp_path / "tasks",
            llm_enabled=False,
            transcript_fusion_enabled=True,
        ),
        asr_adapter=LoopAsrAdapter(),
        evidence_engine=LoopVisualEvidenceEngine(),
    )

    _events, result = runner.run(
        PipelineContext(
            task_id="task-multi-source",
            task_input={
                "input_type": InputType.AUDIO_FILE,
                "source": str(media_path),
                "title": "Loop Engineering",
            },
        )
    )

    assert "Loop Engineering" in result.transcript_text
    audit = json.loads(
        Path(result.artifacts["correction_audit_path"]).read_text(encoding="utf-8")
    )
    kinds = {item["kind"] for item in audit["evidence"]}
    assert {"asr", "frame_ocr"} <= kinds
    provenance = json.loads(
        Path(result.artifacts["transcript_provenance_path"]).read_text(encoding="utf-8")
    )
    assert provenance["primary"]["kind"] == "sidecar"
    assert provenance["supporting"][0]["kind"] == "asr"


def test_local_media_fusion_does_not_expand_egress_to_cloud_asr_by_default(
    tmp_path: Path,
) -> None:
    media_path = tmp_path / "loop-engineering.mp3"
    media_path.write_bytes(b"sidecar and visual evidence are sufficient")
    (tmp_path / "loop-engineering.srt").write_text(
        "1\n00:00:11,000 --> 00:00:14,000\nLoof Engineering\n",
        encoding="utf-8",
    )
    runner = RealPipelineRunner(
        PipelineSettings(
            tasks_dir=tmp_path / "tasks",
            llm_enabled=False,
            transcript_fusion_enabled=True,
            transcription_provider="siliconflow",
            siliconflow_asr_api_key="",
        ),
        evidence_engine=LoopVisualEvidenceEngine(),
    )

    events, result = runner.run(
        PipelineContext(
            task_id="task-no-cloud-egress",
            task_input={
                "input_type": InputType.AUDIO_FILE,
                "source": str(media_path),
                "title": "Loop Engineering",
            },
        )
    )

    assert "Loop Engineering" in result.transcript_text
    assert not any("辅助 ASR 不可用" in event.message for event in events)
    provenance = json.loads(
        Path(result.artifacts["transcript_provenance_path"]).read_text(encoding="utf-8")
    )
    assert provenance["supporting"] == []
