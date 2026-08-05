from __future__ import annotations

import json
import sys
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from video_sum_core.transcribe_funasr_subprocess import (
    configure_runtime_library_dirs,
    format_timestamp,
    parse_funasr_result,
    transcribe_funasr,
    write_progress,
)


class TestFormatTimestamp:
    def test_format_seconds_only(self):
        assert format_timestamp(45.5) == "00:45"

    def test_format_minutes_and_seconds(self):
        assert format_timestamp(125.3) == "02:05"

    def test_format_hours_minutes_seconds(self):
        assert format_timestamp(3665.7) == "01:01:05"

    def test_format_zero(self):
        assert format_timestamp(0) == "00:00"

    def test_format_negative(self):
        assert format_timestamp(-10) == "00:00"


class TestWriteProgress:
    def test_write_progress(self, tmp_path):
        progress_path = tmp_path / "progress.jsonl"
        payload = {"stage": "transcribing", "progress": 50, "message": "test"}

        write_progress(progress_path, payload)

        content = progress_path.read_text(encoding="utf-8")
        assert json.loads(content.strip()) == payload

    def test_write_progress_append(self, tmp_path):
        progress_path = tmp_path / "progress.jsonl"
        payload1 = {"stage": "transcribing", "progress": 50}
        payload2 = {"stage": "transcribing", "progress": 75}

        write_progress(progress_path, payload1)
        write_progress(progress_path, payload2)

        lines = progress_path.read_text(encoding="utf-8").strip().split("\n")
        assert len(lines) == 2
        assert json.loads(lines[0]) == payload1
        assert json.loads(lines[1]) == payload2


class TestConfigureRuntimeLibraryDirs:
    def test_no_env_var(self, monkeypatch):
        monkeypatch.delenv("VIDEO_SUM_DLL_PATHS", raising=False)
        configure_runtime_library_dirs()

    def test_empty_env_var(self, monkeypatch):
        monkeypatch.setenv("VIDEO_SUM_DLL_PATHS", "")
        configure_runtime_library_dirs()

    def test_with_valid_paths(self, monkeypatch, tmp_path):
        path1 = tmp_path / "lib1"
        path2 = tmp_path / "lib2"
        path1.mkdir()
        path2.mkdir()

        import os

        monkeypatch.setenv("VIDEO_SUM_DLL_PATHS", f"{path1}{os.pathsep}{path2}")
        configure_runtime_library_dirs()

        assert str(path1) in os.environ["PATH"]
        assert str(path2) in os.environ["PATH"]


class TestParseFunasrResult:
    def test_parse_empty_result(self, tmp_path):
        progress_path = tmp_path / "progress.jsonl"
        result = []
        segments = parse_funasr_result(result, None, progress_path)
        assert segments == []

    def test_parse_empty_dict(self, tmp_path):
        progress_path = tmp_path / "progress.jsonl"
        result = {}
        segments = parse_funasr_result(result, None, progress_path)
        assert segments == []

    def test_parse_empty_text_item(self, tmp_path):
        progress_path = tmp_path / "progress.jsonl"
        result = [{"text": ""}]
        segments = parse_funasr_result(result, None, progress_path)
        assert segments == []

    def test_parse_dict_result(self, tmp_path):
        progress_path = tmp_path / "progress.jsonl"
        result = {"text": "测试文本"}
        segments = parse_funasr_result(result, None, progress_path)
        assert len(segments) == 1
        assert segments[0]["text"] == "测试文本"
        assert "start" in segments[0]
        assert "end" in segments[0]

    # ── strategy 1: sentence_info ──────────────────────────────────────

    def test_parse_result_with_sentence_info_ms(self, tmp_path):
        """sentence_info with ms timestamps (span > 100s → ms)."""
        progress_path = tmp_path / "progress.jsonl"
        result = [
            {
                "text": "完整文本",
                "sentence_info": [
                    {"text": "第一句", "start": 0, "end": 2000},
                    {"text": "第二句", "start": 2000, "end": 4000},
                ],
            }
        ]
        segments = parse_funasr_result(result, None, progress_path)
        assert len(segments) == 2
        assert segments[0]["text"] == "第一句"
        assert segments[0]["start"] == 0.0
        assert segments[0]["end"] == 2.0
        assert segments[1]["text"] == "第二句"
        assert segments[1]["start"] == 2.0
        assert segments[1]["end"] == 4.0

    def test_parse_result_with_sentence_info_seconds(self, tmp_path):
        """sentence_info with second timestamps (span < 100s → seconds)."""
        progress_path = tmp_path / "progress.jsonl"
        result = [
            {
                "text": "完整文本",
                "sentence_info": [
                    {"text": "第一句", "start": 0.5, "end": 3.2},
                    {"text": "第二句", "start": 3.5, "end": 6.8},
                ],
            }
        ]
        segments = parse_funasr_result(result, None, progress_path)
        assert len(segments) == 2
        assert segments[0]["text"] == "第一句"
        assert segments[0]["start"] == 0.5
        assert segments[0]["end"] == 3.2
        assert segments[1]["text"] == "第二句"
        assert segments[1]["start"] == 3.5
        assert segments[1]["end"] == 6.8

    def test_parse_result_with_sentences_ms(self, tmp_path):
        """sentences field with ms timestamps."""
        progress_path = tmp_path / "progress.jsonl"
        result = [
            {
                "text": "完整文本",
                "sentences": [
                    {"text": "第一句", "start": 0, "end": 2000},
                    {"text": "第二句", "start": 2000, "end": 4000},
                ],
            }
        ]
        segments = parse_funasr_result(result, None, progress_path)
        assert len(segments) == 2
        assert segments[0]["text"] == "第一句"
        assert segments[0]["start"] == 0.0
        assert segments[0]["end"] == 2.0
        assert segments[1]["text"] == "第二句"
        assert segments[1]["start"] == 2.0
        assert segments[1]["end"] == 4.0

    def test_parse_result_with_sentences_seconds(self, tmp_path):
        """sentences field with second timestamps (span < 100s)."""
        progress_path = tmp_path / "progress.jsonl"
        result = [
            {
                "text": "完整文本",
                "sentences": [
                    {"text": "第一句", "start": 1.0, "end": 5.0},
                    {"text": "第二句", "start": 6.0, "end": 10.0},
                ],
            }
        ]
        segments = parse_funasr_result(result, None, progress_path)
        assert len(segments) == 2
        assert segments[0]["start"] == 1.0
        assert segments[0]["end"] == 5.0
        assert segments[1]["start"] == 6.0
        assert segments[1]["end"] == 10.0

    # ── strategy 2: word-level SEACO dict timestamps ──────────────────

    def test_parse_result_with_seaco_timestamps(self, tmp_path):
        """SEACO word-level timestamps (dict with start/end in seconds)."""
        progress_path = tmp_path / "progress.jsonl"
        result = [
            {
                "text": "你好世界",
                "timestamp": [
                    {"text": "你", "start": 0.1, "end": 0.3},
                    {"text": "好", "start": 0.3, "end": 0.5},
                    {"text": "世", "start": 0.5, "end": 0.7},
                    {"text": "界", "start": 0.7, "end": 0.9},
                ],
            }
        ]
        segments = parse_funasr_result(result, None, progress_path)
        assert len(segments) >= 1
        assert segments[0]["start"] == 0.1
        assert segments[-1]["end"] == 0.9

    # ── strategy 2: word-level legacy list-of-pairs timestamps ────────

    def test_parse_result_with_word_timestamps(self, tmp_path):
        progress_path = tmp_path / "progress.jsonl"
        result = [
            {
                "text": "你好 世界",
                "timestamp": [[0, 1000], [1000, 2000]],
            }
        ]
        segments = parse_funasr_result(result, None, progress_path)
        assert len(segments) >= 1
        assert segments[0]["start"] == 0.0
        assert segments[0]["end"] == 2.0

    # ── strategy 3: no-timestamp fallback (punctuation split) ─────────

    def test_parse_result_no_timestamps(self, tmp_path):
        progress_path = tmp_path / "progress.jsonl"
        result = [{"text": "没有时间戳的文本"}]
        segments = parse_funasr_result(result, None, progress_path)
        assert len(segments) == 1
        assert segments[0]["text"] == "没有时间戳的文本"
        assert segments[0]["start"] >= 0
        assert segments[0]["end"] > segments[0]["start"]

    def test_parse_result_punctuation_split(self, tmp_path):
        """Text with punctuation should be split into sentences."""
        progress_path = tmp_path / "progress.jsonl"
        result = [{"text": "这是第一句。这是第二句！这是第三句？"}]
        segments = parse_funasr_result(result, 30.0, progress_path)
        assert len(segments) == 3
        assert segments[0]["text"] == "这是第一句"
        assert segments[1]["text"] == "这是第二句"
        assert segments[2]["text"] == "这是第三句"
        # All segments should have proportional durations
        for seg in segments:
            assert seg["end"] > seg["start"]

    def test_parse_result_with_duration(self, tmp_path):
        progress_path = tmp_path / "progress.jsonl"
        result = [{"text": "测试", "timestamp": [[0, 5000]]}]
        segments = parse_funasr_result(result, 10.0, progress_path)
        assert len(segments) >= 1

    # ── gap-based sentence splitting ──────────────────────────────────

    def test_parse_result_gap_based_split(self, tmp_path):
        """Word-level timestamps with large gaps should split sentences."""
        progress_path = tmp_path / "progress.jsonl"
        result = [
            {
                "text": "abc def",
                "timestamp": [
                    {"text": "a", "start": 0.0, "end": 0.2},
                    {"text": "b", "start": 0.2, "end": 0.4},
                    {"text": "c", "start": 0.4, "end": 0.6},
                    # gap > 0.3s
                    {"text": "d", "start": 2.0, "end": 2.2},
                    {"text": "e", "start": 2.2, "end": 2.4},
                    {"text": "f", "start": 2.4, "end": 2.6},
                ],
            }
        ]
        segments = parse_funasr_result(result, None, progress_path)
        # Should have 2+ segments due to the gap
        assert len(segments) >= 2
        # First segment should contain "abc", second "def"
        assert "abc" in segments[0]["text"].replace(" ", "")
        assert "def" in segments[1]["text"].replace(" ", "")
        # Timestamps should be different between segments
        assert segments[1]["start"] > segments[0]["start"]

    def test_parse_result_gap_no_split_when_small(self, tmp_path):
        """Small gaps (< 0.3s) should NOT split sentences."""
        progress_path = tmp_path / "progress.jsonl"
        result = [
            {
                "text": "abcdef",
                "timestamp": [
                    {"text": "a", "start": 0.0, "end": 0.2},
                    {"text": "b", "start": 0.2, "end": 0.4},
                    {"text": "c", "start": 0.4, "end": 0.6},
                    {"text": "d", "start": 0.6, "end": 0.8},
                    {"text": "e", "start": 0.8, "end": 1.0},
                    {"text": "f", "start": 1.0, "end": 1.2},
                ],
            }
        ]
        segments = parse_funasr_result(result, None, progress_path)
        assert len(segments) == 1

    def test_parse_result_gap_split_only_with_punctuation(self, tmp_path):
        """Gap split should NOT trigger when punctuation already split text."""
        progress_path = tmp_path / "progress.jsonl"
        result = [
            {
                "text": "第一句。第二句",
                "timestamp": [
                    {"text": "第", "start": 0.0, "end": 0.3},
                    {"text": "一", "start": 0.3, "end": 0.6},
                    {"text": "句", "start": 0.6, "end": 0.9},
                    {"text": "。", "start": 0.9, "end": 1.2},
                    {"text": "第", "start": 1.2, "end": 1.5},
                    {"text": "二", "start": 1.5, "end": 1.8},
                    {"text": "句", "start": 1.8, "end": 2.1},
                ],
            }
        ]
        segments = parse_funasr_result(result, None, progress_path)
        # Punctuation already gives 2 sentences
        assert len(segments) == 2

    # ── multi-item result ─────────────────────────────────────────────

    def test_parse_result_multiple_items(self, tmp_path):
        progress_path = tmp_path / "progress.jsonl"
        result = [
            {"text": "第一段文本", "sentences": [{"text": "第一段", "start": 0, "end": 3000}]},
            {"text": "第二段文本", "sentences": [{"text": "第二段", "start": 3000, "end": 6000}]},
        ]
        segments = parse_funasr_result(result, None, progress_path)
        assert len(segments) == 2
        assert segments[0]["text"] == "第一段"
        assert segments[0]["start"] == 0.0
        assert segments[0]["end"] == 3.0
        assert segments[1]["text"] == "第二段"
        assert segments[1]["start"] == 3.0
        assert segments[1]["end"] == 6.0

    def test_parse_result_current_offset_accumulates(self, tmp_path):
        """When the first item uses fallback, second should start where first ended."""
        progress_path = tmp_path / "progress.jsonl"
        result = [
            {"text": "没有时间戳A"},
            {"text": "没有时间戳B"},
        ]
        segments = parse_funasr_result(result, 20.0, progress_path)
        assert len(segments) == 2
        # Second segment should start where first ended
        assert segments[1]["start"] == pytest.approx(segments[0]["end"])


class TestTranscribeFunasr:
    @patch("video_sum_core.transcribe_funasr_subprocess.configure_runtime_library_dirs")
    def test_transcribe_basic(self, mock_configure, tmp_path):
        audio_path = tmp_path / "test.wav"
        audio_path.write_text("dummy audio")
        progress_path = tmp_path / "progress.jsonl"
        output_path = tmp_path / "output.json"

        mock_model = MagicMock()
        mock_model.generate.return_value = [
            {
                "text": "测试转写结果",
                "sentences": [
                    {"text": "测试转写结果", "start": 0, "end": 3000},
                ],
            }
        ]
        mock_automodel = MagicMock(return_value=mock_model)

        # Mock funasr module
        mock_funasr = MagicMock()
        mock_funasr.AutoModel = mock_automodel
        with patch.dict(sys.modules, {"funasr": mock_funasr}):
            transcribe_funasr(
                audio_path=audio_path,
                model_name="paraformer-zh",
                device="cpu",
                vad_model="fsmn-vad",
                punc_model="ct-punc",
                spk_model="",
                hub="ms",
                hotword="",
                progress_path=progress_path,
                output_path=output_path,
                duration=5.0,
            )

        assert output_path.exists()
        result = json.loads(output_path.read_text(encoding="utf-8"))
        assert "transcript" in result
        assert "segments" in result
        assert len(result["segments"]) == 1
        assert result["segments"][0]["text"] == "测试转写结果"

        mock_automodel.assert_called_once()
        model_kwargs = mock_automodel.call_args.kwargs
        assert model_kwargs["disable_update"] is True
        generate_kwargs = mock_model.generate.call_args.kwargs
        assert generate_kwargs["batch_size_s"] == 30
        assert generate_kwargs["batch_size_threshold_s"] == 30
        mock_model.generate.assert_called_once()

    @patch("video_sum_core.transcribe_funasr_subprocess.configure_runtime_library_dirs")
    def test_transcribe_with_hotword(self, mock_configure, tmp_path):
        audio_path = tmp_path / "test.wav"
        audio_path.write_text("dummy audio")
        progress_path = tmp_path / "progress.jsonl"
        output_path = tmp_path / "output.json"

        mock_model = MagicMock()
        mock_model.generate.return_value = [{"text": "热词测试", "timestamp": [[0, 2000]]}]
        mock_automodel = MagicMock(return_value=mock_model)

        mock_funasr = MagicMock()
        mock_funasr.AutoModel = mock_automodel
        with patch.dict(sys.modules, {"funasr": mock_funasr}):
            transcribe_funasr(
                audio_path=audio_path,
                model_name="paraformer-zh",
                device="cpu",
                vad_model="",
                punc_model="",
                spk_model="",
                hub="ms",
                hotword="热词1 热词2",
                progress_path=progress_path,
                output_path=output_path,
                duration=None,
            )

        assert output_path.exists()
        call_kwargs = mock_model.generate.call_args[1]
        assert call_kwargs["hotword"] == "热词1 热词2"

    @patch("video_sum_core.transcribe_funasr_subprocess.configure_runtime_library_dirs")
    def test_transcribe_empty_result_raises(self, mock_configure, tmp_path):
        audio_path = tmp_path / "test.wav"
        audio_path.write_text("dummy audio")
        progress_path = tmp_path / "progress.jsonl"
        output_path = tmp_path / "output.json"

        mock_model = MagicMock()
        mock_model.generate.return_value = []
        mock_automodel = MagicMock(return_value=mock_model)

        mock_funasr = MagicMock()
        mock_funasr.AutoModel = mock_automodel
        with patch.dict(sys.modules, {"funasr": mock_funasr}):
            with pytest.raises(RuntimeError, match="empty output"):
                transcribe_funasr(
                    audio_path=audio_path,
                    model_name="paraformer-zh",
                    device="cpu",
                    vad_model="",
                    punc_model="",
                    spk_model="",
                    hub="ms",
                    hotword="",
                    progress_path=progress_path,
                    output_path=output_path,
                    duration=None,
                )

    @patch("video_sum_core.transcribe_funasr_subprocess.configure_runtime_library_dirs")
    def test_transcribe_model_loading_error(self, mock_configure, tmp_path):
        audio_path = tmp_path / "test.wav"
        audio_path.write_text("dummy audio")
        progress_path = tmp_path / "progress.jsonl"
        output_path = tmp_path / "output.json"

        mock_automodel = MagicMock(side_effect=RuntimeError("Model loading failed"))

        mock_funasr = MagicMock()
        mock_funasr.AutoModel = mock_automodel
        with patch.dict(sys.modules, {"funasr": mock_funasr}):
            with pytest.raises(RuntimeError, match="Model loading failed"):
                transcribe_funasr(
                    audio_path=audio_path,
                    model_name="invalid-model",
                    device="cpu",
                    vad_model="",
                    punc_model="",
                    spk_model="",
                    hub="ms",
                    hotword="",
                    progress_path=progress_path,
                    output_path=output_path,
                    duration=None,
                )
