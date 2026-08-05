from __future__ import annotations

import json
import subprocess
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from video_sum_core.errors import TranscriptionConfigurationError, VideoSumError
from video_sum_core.pipeline.real import PipelineSettings, RealPipelineRunner


class TestFunasrProvider:
    def test_funasr_routing(self, tmp_path):
        settings = PipelineSettings(
            tasks_dir=tmp_path,
            transcription_provider="funasr",
            local_asr_available=True,
            funasr_model="paraformer-zh",
            funasr_device="cpu",
        )
        runner = RealPipelineRunner(settings)

        audio_path = tmp_path / "test.wav"
        audio_path.write_text("dummy")

        with patch.object(runner, "_transcribe_with_funasr") as mock_funasr:
            mock_funasr.return_value = ("transcript", [{"start": 0, "end": 1, "text": "test"}])
            result = runner._transcribe(audio_path, None, lambda *args: None)
            mock_funasr.assert_called_once()
            assert result[0] == "transcript"

    def test_auto_model_resolves_by_language(self, tmp_path):
        from video_sum_infra.config import resolve_funasr_model

        # English maps to the multilingual SenseVoiceSmall: FunASR's
        # "paraformer-en" alias actually points at a Chinese model whose
        # README describes Mandarin training data, so it transcribes English
        # into nonsense.
        assert resolve_funasr_model("zh", "auto") == "paraformer-zh"
        assert resolve_funasr_model("en", "auto") == "iic/SenseVoiceSmall"
        assert resolve_funasr_model("zh-CN", "auto") == "paraformer-zh"
        assert resolve_funasr_model("en-US", "auto") == "iic/SenseVoiceSmall"
        assert resolve_funasr_model("en", "") == "iic/SenseVoiceSmall"
        assert resolve_funasr_model("ja", "auto") == "iic/SenseVoiceSmall"
        assert resolve_funasr_model(None, "auto") == "paraformer-zh"
        # Explicit configured model wins over language detection
        assert resolve_funasr_model("en", "paraformer-zh") == "paraformer-zh"

    def test_funasr_aux_models_preserve_vad_and_punc(self):
        from video_sum_infra.config import resolve_funasr_aux_models

        # VAD MUST be preserved for every model: without it the whole audio
        # file is fed to the GPU in one pass and crashes with CUDA OOM.
        # PUNC (ct-punc) is preserved too so transcripts keep punctuation —
        # SenseVoiceSmall does NOT emit punctuation on its own.
        assert resolve_funasr_aux_models(
            "iic/SenseVoiceSmall",
            vad_model="fsmn-vad",
            punc_model="ct-punc",
            spk_model="cam++",
        ) == ("fsmn-vad", "ct-punc", "cam++")
        assert resolve_funasr_aux_models(
            "SenseVoiceSmall",
            vad_model="fsmn-vad",
            punc_model="ct-punc",
            spk_model="",
        ) == ("fsmn-vad", "ct-punc", "")
        assert resolve_funasr_aux_models(
            "paraformer-zh",
            vad_model="fsmn-vad",
            punc_model="ct-punc",
            spk_model="cam++",
        ) == ("fsmn-vad", "ct-punc", "cam++")

    def test_language_detection_from_metadata(self, tmp_path):
        settings = PipelineSettings(tasks_dir=tmp_path)
        runner = RealPipelineRunner(settings)

        assert runner._detect_video_language({"language": "en"}, "Some English title") == "en"
        assert runner._detect_video_language({"language": "zh-CN"}, "某中文标题") == "zh"
        assert runner._detect_video_language({"languages": ["en"]}, "Title") == "en"
        # CJK title fallback
        assert runner._detect_video_language(None, "这是一个中文视频的标题") == "zh"
        assert runner._detect_video_language(None, "How Blender builds animation systems") == "en"
        assert runner._detect_video_language(None, "") == "other"

    def test_funasr_auto_model_passed_to_subprocess(self, tmp_path):
        settings = PipelineSettings(
            tasks_dir=tmp_path,
            transcription_provider="funasr",
            local_asr_available=True,
            funasr_available=True,
            funasr_model="auto",
            funasr_device="cpu",
            funasr_vad_model="fsmn-vad",
            funasr_punc_model="ct-punc",
        )
        runner = RealPipelineRunner(settings)

        audio_path = tmp_path / "test.wav"
        audio_path.write_text("dummy")

        with patch.object(runner, "_run_funasr_subprocess") as mock_run:
            mock_run.return_value = ("transcript", [{"start": 0, "end": 3, "text": "transcript"}])
            transcript, segments = runner._transcribe_with_funasr(
                audio_path, None, lambda *args: None, language="en"
            )
            assert transcript == "transcript"
            called_kwargs = mock_run.call_args.kwargs
            assert called_kwargs["model_name"] == "iic/SenseVoiceSmall"
            # SenseVoice uses native ITN for an explicitly detected language;
            # VAD stays enabled, while the slow full-text punc pass is skipped.
            assert called_kwargs["vad_model"] == "fsmn-vad"
            assert called_kwargs["punc_model"] == ""
            assert called_kwargs["language"] == "en"

    def test_funasr_not_available_raises(self, tmp_path):
        settings = PipelineSettings(
            tasks_dir=tmp_path,
            transcription_provider="funasr",
            local_asr_available=True,
            funasr_model="paraformer-zh",
            funasr_device="cpu",
        )
        runner = RealPipelineRunner(settings)

        audio_path = tmp_path / "test.wav"
        audio_path.write_text("dummy")

        with patch.object(runner, "_transcribe_with_funasr") as mock_funasr:
            mock_funasr.return_value = ("transcript", [{"start": 0, "end": 1, "text": "test"}])
            result = runner._transcribe(audio_path, None, lambda *args: None)
            mock_funasr.assert_called_once()
            assert result[0] == "transcript"

    def test_funasr_not_available_raises(self, tmp_path):
        settings = PipelineSettings(
            tasks_dir=tmp_path,
            transcription_provider="funasr",
            local_asr_available=False,
        )
        runner = RealPipelineRunner(settings)

        audio_path = tmp_path / "test.wav"
        audio_path.write_text("dummy")

        with pytest.raises(TranscriptionConfigurationError, match="not installed"):
            runner._transcribe_with_funasr(audio_path, None, lambda *args: None)

    def test_funasr_subprocess_success(self, tmp_path):
        settings = PipelineSettings(
            tasks_dir=tmp_path,
            transcription_provider="funasr",
            local_asr_available=True,
            funasr_available=True,
            funasr_model="paraformer-zh",
            funasr_device="cpu",
            funasr_vad_model="fsmn-vad",
            funasr_punc_model="ct-punc",
        )
        runner = RealPipelineRunner(settings)

        audio_path = tmp_path / "test.wav"
        audio_path.write_text("dummy")

        with patch.object(runner, "_run_funasr_subprocess") as mock_run:
            mock_run.return_value = ("测试转写", [{"start": 0, "end": 3, "text": "测试转写"}])
            transcript, segments = runner._transcribe_with_funasr(audio_path, None, lambda *args: None)
            assert transcript == "测试转写"
            assert len(segments) == 1
            mock_run.assert_called_once()

    def test_funasr_subprocess_retry_on_error(self, tmp_path):
        settings = PipelineSettings(
            tasks_dir=tmp_path,
            transcription_provider="funasr",
            local_asr_available=True,
            funasr_available=True,
            funasr_model="paraformer-zh",
            funasr_device="cpu",
            funasr_vad_model="fsmn-vad",
        )
        runner = RealPipelineRunner(settings)

        audio_path = tmp_path / "test.wav"
        audio_path.write_text("dummy")

        call_count = 0

        def mock_run_side_effect(*args, **kwargs):
            nonlocal call_count
            call_count += 1
            if call_count == 1:
                raise VideoSumError("native library level crash")
            return ("成功", [{"start": 0, "end": 2, "text": "成功"}])

        with patch.object(runner, "_run_funasr_subprocess") as mock_run:
            mock_run.side_effect = mock_run_side_effect
            transcript, segments = runner._transcribe_with_funasr(audio_path, None, lambda *args: None)
            assert transcript == "成功"
            assert call_count == 2

    def test_funasr_subprocess_no_retry_on_config_error(self, tmp_path):
        settings = PipelineSettings(
            tasks_dir=tmp_path,
            transcription_provider="funasr",
            local_asr_available=True,
            funasr_available=True,
            funasr_model="paraformer-zh",
            funasr_device="cpu",
        )
        runner = RealPipelineRunner(settings)

        audio_path = tmp_path / "test.wav"
        audio_path.write_text("dummy")

        with patch.object(runner, "_run_funasr_subprocess") as mock_run:
            mock_run.side_effect = TranscriptionConfigurationError("Invalid config")
            with pytest.raises(TranscriptionConfigurationError):
                runner._transcribe_with_funasr(audio_path, None, lambda *args: None)
            assert mock_run.call_count == 1

    def test_build_funasr_command(self, tmp_path):
        settings = PipelineSettings(
            tasks_dir=tmp_path,
            runtime_channel="base",
            funasr_model="paraformer-zh",
            funasr_device="cpu",
            funasr_vad_model="fsmn-vad",
            funasr_punc_model="ct-punc",
            funasr_spk_model="cam++",
            funasr_hub="ms",
            funasr_hotword="热词1 热词2",
        )
        runner = RealPipelineRunner(settings)

        audio_path = tmp_path / "test.wav"
        progress_path = tmp_path / "progress.jsonl"
        output_path = tmp_path / "output.json"

        with patch("video_sum_core.pipeline.real.runtime_python_executable") as mock_python:
            mock_python.return_value = Path("/usr/bin/python")
            command = runner._build_funasr_command(
                audio_path=audio_path,
                model_name="paraformer-zh",
                device="cpu",
                vad_model="fsmn-vad",
                punc_model="ct-punc",
                spk_model="cam++",
                hub="ms",
                hotword="热词1 热词2",
                progress_path=progress_path,
                output_path=output_path,
            )

        assert command[0] == str(Path("/usr/bin/python"))
        assert "-m" in command
        assert "video_sum_core.transcribe_funasr_subprocess" in command
        assert "--audio-path" in command
        assert "--model" in command
        assert "paraformer-zh" in command
        assert "--device" in command
        assert "cpu" in command
        assert "--vad-model" in command
        assert "fsmn-vad" in command
        assert "--punc-model" in command
        assert "ct-punc" in command
        assert "--spk-model" in command
        assert "cam++" in command
        assert "--hub" in command
        assert "ms" in command
        assert "--hotword" in command
        assert "热词1 热词2" in command

    def test_run_funasr_subprocess_timeout(self, tmp_path):
        settings = PipelineSettings(
            tasks_dir=tmp_path,
            runtime_channel="base",
            funasr_model="paraformer-zh",
            funasr_device="cpu",
        )
        runner = RealPipelineRunner(settings)

        audio_path = tmp_path / "test.wav"
        audio_path.write_text("dummy")

        with patch.object(runner, "_build_funasr_command") as mock_build:
            mock_build.return_value = ["sleep", "9999"]
            with patch("video_sum_core.pipeline.real.subprocess.Popen") as mock_popen:
                mock_process = MagicMock()
                mock_process.poll.return_value = None
                mock_process.communicate.return_value = ("", "")
                mock_popen.return_value = mock_process

                with patch("video_sum_core.pipeline.real.time.monotonic") as mock_time:
                    mock_time.side_effect = [0, 0, 9999]

                    # ``_kill_process_tree`` invokes ``subprocess.run(["taskkill", ...])``
                    # on Windows, which must be tolerated even though
                    # ``subprocess.Popen`` is mocked here.
                    with patch("video_sum_core.pipeline.real.subprocess.run", return_value=subprocess.CompletedProcess([], 1)):
                        with pytest.raises(VideoSumError, match="timed out|no progress"):
                            runner._run_funasr_subprocess(
                                audio_path=audio_path,
                                duration=1.0,
                                emit=lambda *args: None,
                                model_name="paraformer-zh",
                                device="cpu",
                                vad_model="",
                                punc_model="",
                                spk_model="",
                                hub="ms",
                                hotword="",
                            )
                    mock_process.kill.assert_called_once()

    def test_run_funasr_subprocess_crash_with_valid_output(self, tmp_path):
        settings = PipelineSettings(
            tasks_dir=tmp_path,
            runtime_channel="base",
            funasr_model="paraformer-zh",
            funasr_device="cpu",
        )
        runner = RealPipelineRunner(settings)

        audio_path = tmp_path / "test.wav"
        audio_path.write_text("dummy")
        output_path = audio_path.with_name("funasr_worker_result.json")

        # _run_funasr_subprocess deletes any existing output file on entry,
        # so we MUST NOT pre-write it.  Instead, the poll side-effect writes
        # it on the second invocation (simulating a crashed subprocess that
        # produced output before dying).
        call_count = [0]

        def poll_side_effect() -> int | None:
            call_count[0] += 1
            if call_count[0] == 1:
                return None  # process still running
            # Subprocess crashed mid-cleanup; write valid output then fail.
            if not output_path.exists():
                output_path.write_text(
                    json.dumps(
                        {"transcript": "[00:00] 测试", "segments": [{"start": 0, "end": 2, "text": "测试"}]},
                        ensure_ascii=False,
                    ),
                    encoding="utf-8",
                )
            return 3221226505  # native crash exit code
        with patch.object(runner, "_build_funasr_command") as mock_build:
            mock_build.return_value = ["echo", "test"]
            with patch("video_sum_core.pipeline.real.subprocess.Popen") as mock_popen:
                mock_process = MagicMock()
                mock_process.poll.side_effect = poll_side_effect
                mock_process.returncode = 3221226505
                mock_process.communicate.return_value = ("", "")
                mock_popen.return_value = mock_process

                transcript, segments = runner._run_funasr_subprocess(
                    audio_path=audio_path,
                    duration=None,
                    emit=lambda *args: None,
                    model_name="paraformer-zh",
                    device="cpu",
                    vad_model="",
                    punc_model="",
                    spk_model="",
                    hub="ms",
                    hotword="",
                )

                assert transcript == "[00:00] 测试"
                assert len(segments) == 1

    def test_run_funasr_subprocess_crash_without_output(self, tmp_path):
        settings = PipelineSettings(
            tasks_dir=tmp_path,
            runtime_channel="base",
            funasr_model="paraformer-zh",
            funasr_device="cpu",
        )
        runner = RealPipelineRunner(settings)

        audio_path = tmp_path / "test.wav"
        audio_path.write_text("dummy")

        with patch.object(runner, "_build_funasr_command") as mock_build:
            mock_build.return_value = ["false"]
            with patch("video_sum_core.pipeline.real.subprocess.Popen") as mock_popen:
                mock_process = MagicMock()
                mock_process.poll.return_value = 1
                mock_process.returncode = 1
                mock_process.communicate.return_value = ("", "error")
                mock_popen.return_value = mock_process

                with pytest.raises(VideoSumError, match="failed with exit code"):
                    runner._run_funasr_subprocess(
                        audio_path=audio_path,
                        duration=None,
                        emit=lambda *args: None,
                        model_name="paraformer-zh",
                        device="cpu",
                        vad_model="",
                        punc_model="",
                        spk_model="",
                        hub="ms",
                        hotword="",
                    )
