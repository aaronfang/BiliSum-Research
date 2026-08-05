from __future__ import annotations

from types import SimpleNamespace

from video_sum_infra.config import ServiceSettings
import video_sum_service.routers.system as system_router
from video_sum_service.auto_setup import (
    build_local_setup_updates,
    choose_cuda_variant,
)


def test_choose_cuda_variant_uses_existing_supported_choice() -> None:
    assert choose_cuda_variant("cu126", nvidia_available=True) == "cu126"
    assert choose_cuda_variant("cu999", nvidia_available=True) == "cu128"


def test_choose_cuda_variant_disables_gpu_without_nvidia() -> None:
    assert choose_cuda_variant("cu128", nvidia_available=False) is None


def test_build_local_setup_updates_selects_gpu_asr_knowledge_and_ollama() -> None:
    settings = ServiceSettings(
        transcription_provider="siliconflow",
        llm_enabled=False,
        knowledge_enabled=False,
        visual_multimodal_enabled=False,
    )

    updates = build_local_setup_updates(
        settings,
        cuda_variant="cu128",
        nvidia_available=True,
        ollama_models={"qwen3:14b", "minicpm-v:8b"},
    )

    assert updates["runtime_channel"] == "gpu-cu128"
    assert updates["cuda_variant"] == "cu128"
    assert updates["transcription_provider"] == "funasr"
    assert updates["funasr_device"] == "cuda"
    assert updates["device_preference"] == "cuda"
    assert updates["knowledge_enabled"] is True
    assert updates["knowledge_embedding_provider"] == "local_huggingface"
    assert updates["knowledge_embedding_model"] == "BAAI/bge-small-zh-v1.5"
    assert updates["llm_enabled"] is True
    assert updates["llm_base_url"] == "http://127.0.0.1:11434/v1"
    assert updates["llm_model"] == "qwen3:14b"
    assert updates["visual_multimodal_enabled"] is True
    assert updates["visual_evidence_model"] == "minicpm-v:8b"
    assert updates["summary_chunk_concurrency"] == 1


def test_build_local_setup_updates_enables_parallel_chunks_with_small_qwen() -> None:
    settings = ServiceSettings(llm_enabled=False, knowledge_enabled=False)

    updates = build_local_setup_updates(
        settings,
        cuda_variant="cu128",
        nvidia_available=True,
        ollama_models={"qwen3:14b", "qwen3:8b"},
    )

    assert updates["llm_model"] == "qwen3:14b"
    assert updates["summary_chunk_concurrency"] == 2


def test_build_local_setup_updates_does_not_replace_existing_cloud_llm() -> None:
    settings = ServiceSettings(
        transcription_provider="siliconflow",
        llm_enabled=True,
        llm_base_url="https://api.example.com/v1",
        llm_model="existing-model",
        llm_api_key="secret",
        knowledge_enabled=False,
    )

    updates = build_local_setup_updates(
        settings,
        cuda_variant=None,
        nvidia_available=False,
        ollama_models={"qwen3:14b"},
    )

    assert updates["runtime_channel"] == "base"
    assert updates["transcription_provider"] == "funasr"
    assert "llm_base_url" not in updates
    assert "llm_model" not in updates
    assert "llm_api_key" not in updates


def test_auto_setup_route_validates_and_delegates_payload(monkeypatch) -> None:
    captured = {}

    def fake_run(payload, app_state):
        captured["payload"] = payload
        captured["app_state"] = app_state
        return {"ok": True}

    monkeypatch.setattr(system_router, "run_auto_setup", fake_run)
    app_state = SimpleNamespace(task_repository=object())
    request = SimpleNamespace(app=SimpleNamespace(state=app_state))

    response = system_router.post_auto_setup(
        request,
        {"install_cuda": False, "download_embedding": False},
    )

    assert response == {"ok": True}
    assert captured["app_state"] is app_state
    assert captured["payload"].install_cuda is False
    assert captured["payload"].download_embedding is False
    assert captured["payload"].install_funasr is True
