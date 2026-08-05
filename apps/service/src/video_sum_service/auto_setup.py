from __future__ import annotations

from collections.abc import Iterable
import json
import shutil
import subprocess
import sys
import threading
from pathlib import Path
from typing import TYPE_CHECKING

from fastapi import HTTPException

import httpx
from pydantic import BaseModel, Field

from video_sum_infra.config import ServiceSettings

from video_sum_service.context import settings_manager
from video_sum_service.runtime_startup import mark_runtime_worker_ready
from video_sum_service.runtime_support import (
    build_worker,
    detect_environment,
    download_embedding_model,
    install_cuda_support,
    install_funasr,
    install_knowledge_dependencies,
    replace_task_worker,
    run_command,
    run_host_command,
    runtime_python_executable,
    serialize_settings,
    uses_current_service_python,
    verify_embedding_model,
)
from video_sum_service.settings_manager import SettingsUpdatePayload

if TYPE_CHECKING:
    from video_sum_service.repository import SqliteTaskRepository


OLLAMA_BASE_URL = "http://127.0.0.1:11434/v1"
OLLAMA_API_URL = "http://127.0.0.1:11434/api/tags"
DEFAULT_EMBEDDING_MODEL = "BAAI/bge-small-zh-v1.5"
SUPPORTED_CUDA_VARIANTS = {"cu124", "cu126", "cu128"}
_AUTO_SETUP_LOCK = threading.Lock()


class AutoSetupPayload(BaseModel):
    cuda_variant: str | None = Field(default=None)
    install_cuda: bool = True
    install_funasr: bool = True
    install_knowledge: bool = True
    download_embedding: bool = True
    download_funasr_models: bool = True
    configure_defaults: bool = True


def choose_cuda_variant(requested: str | None, *, nvidia_available: bool) -> str | None:
    if not nvidia_available:
        return None
    normalized = str(requested or "").strip().lower()
    return normalized if normalized in SUPPORTED_CUDA_VARIANTS else "cu128"


def detect_ollama_models() -> set[str]:
    try:
        response = httpx.get(OLLAMA_API_URL, timeout=2.0)
        response.raise_for_status()
        payload = response.json()
    except (httpx.HTTPError, ValueError, TypeError):
        return set()

    models = payload.get("models") if isinstance(payload, dict) else None
    if not isinstance(models, list):
        return set()
    names: set[str] = set()
    for item in models:
        if isinstance(item, dict) and str(item.get("name") or "").strip():
            names.add(str(item["name"]).strip())
    return names


def _first_available_model(models: Iterable[str], candidates: Iterable[str]) -> str | None:
    available = set(models)
    for candidate in candidates:
        if candidate in available:
            return candidate
    return None


def build_local_setup_updates(
    settings: ServiceSettings,
    *,
    cuda_variant: str | None,
    nvidia_available: bool,
    ollama_models: Iterable[str],
) -> dict[str, object]:
    variant = choose_cuda_variant(cuda_variant, nvidia_available=nvidia_available)
    knowledge_provider = (
        str(settings.knowledge_embedding_provider or "local_huggingface")
        if settings.knowledge_enabled
        else "local_huggingface"
    )
    updates: dict[str, object] = {
        "runtime_channel": f"gpu-{variant}" if variant else "base",
        "transcription_provider": "funasr",
        "funasr_device": "cuda" if variant else "cpu",
        "device_preference": "cuda" if variant else "cpu",
        "knowledge_enabled": True,
        "knowledge_embedding_provider": knowledge_provider,
        "knowledge_embedding_model": settings.knowledge_embedding_model or DEFAULT_EMBEDDING_MODEL,
        "knowledge_llm_mode": "same_as_main",
        "task_concurrency": 1,
        "summary_chunk_concurrency": 1,
    }
    if variant:
        updates["cuda_variant"] = variant

    model_names = set(ollama_models)
    if "qwen3:8b" in model_names or "qwen3:4b" in model_names:
        # Chunk summaries can use the smaller model in parallel while the
        # final merge and knowledge note stay on the main model.
        updates["summary_chunk_concurrency"] = 2
    qwen_model = _first_available_model(model_names, ("qwen3:14b", "qwen3:8b", "qwen3:4b"))
    main_llm_ready = bool(
        settings.llm_enabled
        and settings.llm_base_url
        and settings.llm_model
        and settings.llm_api_key
    )
    if qwen_model and not main_llm_ready:
        updates.update(
            {
                "llm_enabled": True,
                "llm_provider": "openai-compatible",
                "llm_base_url": OLLAMA_BASE_URL,
                "llm_model": qwen_model,
                "llm_api_key": "ollama",
                "knowledge_llm_enabled": True,
            }
        )

    visual_model = _first_available_model(model_names, ("minicpm-v:8b", "qwen2.5vl:7b", "qwen2.5vl:3b"))
    visual_llm_ready = bool(
        settings.visual_multimodal_enabled
        and settings.visual_evidence_base_url
        and settings.visual_evidence_model
    )
    if visual_model and not visual_llm_ready:
        updates.update(
            {
                "visual_evidence_enabled": True,
                "visual_multimodal_enabled": True,
                "visual_note_mode": "vlm_integrated",
                "visual_vlm_provider": "openai-compatible",
                "visual_evidence_base_url": OLLAMA_BASE_URL,
                "visual_evidence_model": visual_model,
                "visual_evidence_api_key": "ollama",
            }
        )

    return updates


def _step(steps: list[dict[str, object]], step_id: str, label: str, status: str, detail: str = "") -> None:
    steps.append({"id": step_id, "label": label, "status": status, "detail": detail[:2000]})


def _replace_worker_for_setup(app_state, repository: SqliteTaskRepository, environment: dict[str, object]) -> None:
    current_settings = settings_manager.current
    worker = build_worker(repository, current_settings, environment_info=environment)
    replace_task_worker(app_state, worker)
    mark_runtime_worker_ready(app_state, environment, "自动安装完成后运行环境已刷新。")


def preload_funasr_models(settings: ServiceSettings) -> str:
    runtime_channel = settings.runtime_channel
    python_executable = (
        Path(sys.executable)
        if uses_current_service_python(runtime_channel)
        else runtime_python_executable(runtime_channel)
    )
    if python_executable is None:
        raise RuntimeError("FunASR runtime Python 不可用。")

    models_to_preload = ["paraformer-zh", "paraformer-en"] if settings.funasr_model == "auto" else [settings.funasr_model]
    outputs: list[str] = []
    for model_name in models_to_preload:
        kwargs = {
            "model": model_name,
            "device": settings.funasr_device,
            "hub": settings.funasr_hub,
        }
        if settings.funasr_vad_model:
            kwargs["vad_model"] = settings.funasr_vad_model
        if settings.funasr_punc_model:
            kwargs["punc_model"] = settings.funasr_punc_model
        if settings.funasr_spk_model:
            kwargs["spk_model"] = settings.funasr_spk_model
        script = (
            "from funasr import AutoModel\n"
            f"AutoModel(**{json.dumps(kwargs, ensure_ascii=False)})\n"
            f"print('FunASR model ready: {model_name}')\n"
        )
        command = [str(python_executable), "-c", script]
        if uses_current_service_python(runtime_channel):
            result = run_host_command(command, timeout=3600)
        else:
            result = run_command(command, runtime_channel=runtime_channel, timeout=3600)
        outputs.append(((result.stdout or "") + "\n" + (result.stderr or "")).strip()[-2000:])
    return "\n".join(outputs)


def run_auto_setup(payload: AutoSetupPayload, app_state) -> dict[str, object]:
    if not _AUTO_SETUP_LOCK.acquire(blocking=False):
        raise HTTPException(status_code=409, detail="自动安装正在进行中，请等待当前流程完成。")
    try:
        return _run_auto_setup(payload, app_state)
    finally:
        _AUTO_SETUP_LOCK.release()


def _run_auto_setup(payload: AutoSetupPayload, app_state) -> dict[str, object]:
    repository = getattr(app_state, "task_repository", None)
    if repository is None:
        raise RuntimeError("任务仓库尚未初始化，无法执行自动安装。")

    steps: list[dict[str, object]] = []
    current_settings = settings_manager.current
    nvidia_available = detect_nvidia_gpu()
    requested_variant = payload.cuda_variant or current_settings.cuda_variant
    cuda_variant = choose_cuda_variant(requested_variant, nvidia_available=nvidia_available)

    if payload.install_cuda and cuda_variant:
        active_environment = detect_environment(current_settings.runtime_channel)
        gpu_ready = bool(
            current_settings.runtime_channel == f"gpu-{cuda_variant}"
            and active_environment.get("cudaAvailable")
        )
        if gpu_ready:
            _step(steps, "cuda", "GPU 运行环境", "skipped", "已检测到可用的 CUDA 运行环境。")
        else:
            try:
                _result, worker = install_cuda_support(cuda_variant, repository)
                if worker is not None:
                    replace_task_worker(app_state, worker)
                _step(steps, "cuda", "GPU 运行环境", "installed", f"CUDA {cuda_variant} 已安装。")
            except Exception as exc:
                _step(steps, "cuda", "GPU 运行环境", "failed", str(exc))
    elif payload.install_cuda:
        _step(steps, "cuda", "GPU 运行环境", "skipped", "未检测到 NVIDIA GPU，使用 CPU 运行模式。")

    current_settings = settings_manager.current
    active_channel = current_settings.runtime_channel
    environment = detect_environment(active_channel)

    if payload.install_funasr:
        if environment.get("funasrAvailable"):
            _step(steps, "funasr", "FunASR 语音识别", "skipped", "FunASR 已安装。")
        else:
            try:
                result, worker = install_funasr(False, repository)
                if worker is not None:
                    replace_task_worker(app_state, worker)
                environment = (
                    result.get("environment")
                    if isinstance(result.get("environment"), dict)
                    else detect_environment(active_channel)
                )
                _step(steps, "funasr", "FunASR 语音识别", "installed", "FunASR 依赖已安装。")
            except Exception as exc:
                _step(steps, "funasr", "FunASR 语音识别", "failed", str(exc))

    if payload.install_funasr and payload.download_funasr_models:
        current_settings = settings_manager.current
        active_channel = current_settings.runtime_channel
        environment = detect_environment(active_channel)
        gpu_runtime_ready = bool(
            cuda_variant
            and active_channel == f"gpu-{cuda_variant}"
            and environment.get("cudaAvailable")
        )
        if environment.get("funasrAvailable"):
            preload_settings = current_settings.model_copy(
                update=build_local_setup_updates(
                    current_settings,
                    cuda_variant=cuda_variant if gpu_runtime_ready else None,
                    nvidia_available=gpu_runtime_ready,
                    ollama_models=(),
                )
            )
            try:
                detail = preload_funasr_models(preload_settings)
                _step(steps, "funasr-models", "FunASR 模型", "installed", detail or "FunASR 模型已准备完成。")
            except Exception as exc:
                _step(steps, "funasr-models", "FunASR 模型", "failed", str(exc))

    current_settings = settings_manager.current
    active_channel = current_settings.runtime_channel
    environment = detect_environment(active_channel)
    if environment.get("ffmpegLocation"):
        _step(steps, "ffmpeg", "FFmpeg", "skipped", "已检测到 FFmpeg。")
    else:
        _step(steps, "ffmpeg", "FFmpeg", "failed", "未检测到 FFmpeg，请安装后重新运行自动配置。")

    provider = str(current_settings.knowledge_embedding_provider or "local_huggingface")
    if payload.install_knowledge:
        if environment.get("knowledgeDependenciesReady"):
            _step(steps, "knowledge", "知识库依赖", "skipped", "知识库依赖已安装。")
        else:
            try:
                result, worker = install_knowledge_dependencies(
                    False,
                    repository,
                    runtime_channel=active_channel,
                    provider=provider,
                )
                if worker is not None:
                    replace_task_worker(app_state, worker)
                environment = (
                    result.get("environment")
                    if isinstance(result.get("environment"), dict)
                    else detect_environment(active_channel)
                )
                if result.get("installed") or environment.get("knowledgeDependenciesReady"):
                    _step(steps, "knowledge", "知识库依赖", "installed", "知识库依赖已安装。")
                else:
                    _step(steps, "knowledge", "知识库依赖", "failed", str(result.get("detail") or "知识库依赖未完全就绪。"))
            except Exception as exc:
                _step(steps, "knowledge", "知识库依赖", "failed", str(exc))

    current_settings = settings_manager.current
    active_channel = current_settings.runtime_channel
    environment = detect_environment(active_channel)
    if payload.download_embedding and provider in {"local_huggingface", "local_modelscope"}:
        try:
            verified = verify_embedding_model(
                repository,
                provider=provider,
                model_name=current_settings.knowledge_embedding_model,
                hf_endpoint=current_settings.hf_endpoint,
            )
            if verified.get("verified"):
                _step(steps, "embedding", "Embedding 模型", "skipped", str(verified.get("detail") or "Embedding 模型已就绪。"))
            else:
                downloaded = download_embedding_model(
                    repository,
                    provider=provider,
                    model_name=current_settings.knowledge_embedding_model,
                    hf_endpoint=current_settings.hf_endpoint,
                )
                if downloaded.get("downloaded"):
                    _step(steps, "embedding", "Embedding 模型", "installed", "Embedding 模型已下载。")
                else:
                    _step(
                        steps,
                        "embedding",
                        "Embedding 模型",
                        "failed",
                        str(downloaded.get("detail") or "Embedding 模型下载失败。"),
                    )
        except Exception as exc:
            _step(steps, "embedding", "Embedding 模型", "failed", str(exc))
    elif payload.download_embedding:
        _step(steps, "embedding", "Embedding 模型", "skipped", f"当前 Embedding provider={provider}，不执行本地模型下载。")

    if payload.configure_defaults:
        current_settings = settings_manager.current
        active_channel = current_settings.runtime_channel
        current_environment = detect_environment(active_channel)
        gpu_runtime_ready = bool(
            cuda_variant
            and active_channel == f"gpu-{cuda_variant}"
            and current_environment.get("cudaAvailable")
        )
        ollama_models = detect_ollama_models()
        updates = build_local_setup_updates(
            current_settings,
            cuda_variant=cuda_variant if gpu_runtime_ready else None,
            nvidia_available=gpu_runtime_ready,
            ollama_models=ollama_models,
        )
        settings_manager.save(SettingsUpdatePayload.model_validate(updates))
        _step(steps, "settings", "默认设置", "installed", "已根据本机硬件和本地模型自动保存设置。")

    current_settings = settings_manager.current
    active_channel = current_settings.runtime_channel
    environment = detect_environment(active_channel)
    _replace_worker_for_setup(app_state, repository, environment)
    settings_payload = serialize_settings(current_settings, environment_info=environment)
    failed = [step for step in steps if step.get("status") == "failed"]
    return {
        "ok": not failed,
        "message": "自动安装完成。" if not failed else "自动安装已完成部分步骤，请查看失败步骤。",
        "steps": steps,
        "failedStep": failed[0]["id"] if failed else None,
        "settings": settings_payload,
        "environment": environment,
    }


def detect_nvidia_gpu() -> bool:
    executable = shutil.which("nvidia-smi")
    if not executable:
        return False
    try:
        result = subprocess.run(
            [executable, "--query-gpu=name", "--format=csv,noheader"],
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            timeout=5,
            check=False,
        )
    except (OSError, subprocess.SubprocessError):
        return False
    return result.returncode == 0 and bool(result.stdout.strip())
