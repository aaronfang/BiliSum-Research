import sqlite3
from datetime import datetime
from pathlib import Path

import pytest
from fastapi import HTTPException
from video_sum_core.markdown_exports import build_export_filename
from video_sum_core.models.tasks import InputType, TaskInput, TaskResult, TaskStatus
from video_sum_infra.config import ServiceSettings
from video_sum_service import task_exports
from video_sum_service.app import app, settings_manager
from video_sum_service.repository import SqliteTaskRepository
from video_sum_service.schemas import VideoAssetRecord
from video_sum_service.task_exports import (
    _build_export_tags,
    export_task_markdown,
    export_task_transcript,
    export_tasks_markdown,
)


def create_repository() -> SqliteTaskRepository:
    connection = sqlite3.connect(":memory:", check_same_thread=False)
    connection.row_factory = sqlite3.Row
    repository = SqliteTaskRepository(connection)
    repository.initialize()
    return repository


def create_completed_task(repository: SqliteTaskRepository) -> str:
    video = repository.upsert_video_asset(
        VideoAssetRecord(
            canonical_id="BV1test",
            platform="bilibili",
            title="测试导出视频",
            source_url="https://www.bilibili.com/video/BV1test",
            cover_url="",
        )
    )
    record = repository.create_task(
        TaskInput(input_type=InputType.URL, source=video.source_url, title=video.title),
        video_id=video.video_id,
    )
    repository.save_result(
        record.task_id,
        TaskResult(
            overview="概览",
            transcript_text="[00:00] 转写内容",
            knowledge_note_markdown="# 测试导出视频\n\n## 核心概览\n\n概览",
            key_points=["要点一"],
            timeline=[{"title": "章节一", "start": 12.0, "summary": "章节摘要"}],
            artifacts={"summary_path": "C:/tmp/summary.json"},
        ),
    )
    repository.update_status(record.task_id, TaskStatus.COMPLETED)
    return record.task_id


@pytest.fixture(autouse=True)
def restore_app_state():
    original_repository = getattr(app.state, "task_repository", None)
    original_settings = settings_manager.current
    yield
    app.state.task_repository = original_repository
    settings_manager._settings = original_settings


def test_export_task_markdown_requires_output_dir(tmp_path: Path) -> None:
    repository = create_repository()
    task_id = create_completed_task(repository)
    app.state.task_repository = repository
    settings = ServiceSettings(
        data_dir=tmp_path / "data",
        cache_dir=tmp_path / "cache",
        tasks_dir=tmp_path / "tasks",
        output_dir="",
    )
    settings_manager._settings = settings

    with pytest.raises(HTTPException, match="输出目录"):
        export_task_markdown(repository, settings, task_id)


def test_export_task_markdown_writes_file_and_persists_artifact(tmp_path: Path) -> None:
    repository = create_repository()
    task_id = create_completed_task(repository)
    app.state.task_repository = repository
    settings = ServiceSettings(
        data_dir=tmp_path / "data",
        cache_dir=tmp_path / "cache",
        tasks_dir=tmp_path / "tasks",
        output_dir=str(tmp_path / "vault"),
    )
    settings_manager._settings = settings

    response = export_task_markdown(repository, settings, task_id)
    refreshed = repository.get_task(task_id)

    assert response.target_format == "obsidian"
    assert response.overwritten is False
    assert Path(response.path).exists()
    assert refreshed is not None
    assert refreshed.result is not None
    assert refreshed.result.artifacts["obsidian_note_path"] == response.path
    content = Path(response.path).read_text(encoding="utf-8")
    assert content.startswith("---\n")
    assert "## 关键要点" in content
    assert "## 转写全文" not in content


def test_export_tags_keep_persisted_tags_without_extracting_summary_terms() -> None:
    repository = create_repository()
    result = TaskResult(
        overview="介绍节点式视频创作工具，重点比较多轨编辑、字幕烧录和视频对比流程。",
        key_points=[
            "通过路径合并、字幕烧录和视频对比完成多轨编辑。",
            "安装 Blender 轻量版并激活官方 MCP 插件。",
        ],
        knowledge_note_markdown="# EasyMedia 节点包基础介绍\n\n正文包含 #视频创作 和 #Blender-插件",
    )
    video = repository.upsert_video_asset(
        VideoAssetRecord(
            canonical_id="BV-tag-preview",
            platform="bilibili",
            title="测试视频",
            source_url="https://www.bilibili.com/video/BV-tag-preview",
        )
    )
    repository.add_video_tag(video.video_id, "  MCP 插件  ", source="manual")
    repository.add_video_tag(video.video_id, "自动候选", source="auto_llm")

    tags = _build_export_tags(
        repository,
        video.video_id,
        title="EasyMedia 节点包基础介绍：支持 Flux3、Bernini 的多轨导演台编辑器",
        result=result,
        note_markdown=result.knowledge_note_markdown,
    )

    assert tags == ["MCP-插件", "视频创作", "Blender-插件", "自动候选"]
    assert "EasyMedia" not in tags
    assert "Flux3" not in tags
    assert "字幕烧录" not in tags


def test_export_tag_preview_selects_auto_tags_by_default() -> None:
    repository = create_repository()
    task_id = create_completed_task(repository)
    record = repository.get_task(task_id)
    assert record is not None and record.video_id is not None
    repository.add_video_tag(record.video_id, "MCP", source="manual")
    repository.add_video_tag(record.video_id, "大模型", source="auto_llm")

    items = task_exports.build_export_tag_preview(repository, task_id)

    assert [(item["tag"], item["source"], item["selected"]) for item in items] == [
        ("MCP", "manual", True),
        ("大模型", "auto_llm", True),
    ]


def test_export_task_markdown_includes_manual_tags_without_summary_terms(tmp_path: Path) -> None:
    repository = create_repository()
    task_id = create_completed_task(repository)
    record = repository.get_task(task_id)
    assert record is not None and record.video_id is not None
    repository.add_video_tag(record.video_id, "MCP 插件", source="manual")
    repository.add_video_tag(record.video_id, "note/source", source="system")
    repository.add_video_tag(record.video_id, "has/transcript", source="system")
    app.state.task_repository = repository
    settings = ServiceSettings(
        data_dir=tmp_path / "data",
        cache_dir=tmp_path / "cache",
        tasks_dir=tmp_path / "tasks",
        output_dir=str(tmp_path / "vault"),
    )

    response = export_task_markdown(repository, settings, task_id)
    content = Path(response.path).read_text(encoding="utf-8")

    assert '  - "MCP-插件"' in content
    assert '  - "测试导出视频"' not in content
    assert '  - "source/bilibili"' not in content
    assert '  - "note/source"' not in content
    assert '  - "has/transcript"' not in content


def test_export_task_markdown_uses_explicit_tag_override(tmp_path: Path) -> None:
    repository = create_repository()
    task_id = create_completed_task(repository)
    record = repository.get_task(task_id)
    assert record is not None and record.video_id is not None
    repository.add_video_tag(record.video_id, "数据库标签", source="manual")
    settings = ServiceSettings(
        data_dir=tmp_path / "data",
        cache_dir=tmp_path / "cache",
        tasks_dir=tmp_path / "tasks",
        output_dir=str(tmp_path / "vault"),
    )

    response = export_task_markdown(repository, settings, task_id, tags=["#导出标签"])
    content = Path(response.path).read_text(encoding="utf-8")

    assert '  - "导出标签"' in content
    assert '  - "数据库标签"' not in content


def test_batch_export_includes_auto_tags_by_default(tmp_path: Path) -> None:
    repository = create_repository()
    task_id = create_completed_task(repository)
    record = repository.get_task(task_id)
    assert record is not None and record.video_id is not None
    repository.add_video_tag(record.video_id, "自动主题", source="auto_llm")
    settings = ServiceSettings(
        data_dir=tmp_path / "data",
        cache_dir=tmp_path / "cache",
        tasks_dir=tmp_path / "tasks",
        output_dir=str(tmp_path / "vault"),
    )

    response = export_tasks_markdown(repository, settings, [task_id])
    content = Path(response.exported[0].path).read_text(encoding="utf-8")

    assert '  - "自动主题"' in content


def test_export_tasks_markdown_exports_completed_and_reports_failures(tmp_path: Path) -> None:
    repository = create_repository()
    task_id = create_completed_task(repository)
    settings = ServiceSettings(
        data_dir=tmp_path / "data",
        cache_dir=tmp_path / "cache",
        tasks_dir=tmp_path / "tasks",
        output_dir=str(tmp_path / "vault"),
    )

    response = export_tasks_markdown(repository, settings, [task_id, "missing-task"])

    assert response.requested_count == 2
    assert [item.task_id for item in response.exported] == [task_id]
    assert [(item.task_id, item.error) for item in response.failed] == [("missing-task", "Task not found.")]


def test_export_task_markdown_renders_mindmap_and_copies_json(tmp_path: Path) -> None:
    repository = create_repository()
    task_id = create_completed_task(repository)
    record = repository.get_task(task_id)
    assert record is not None and record.result is not None
    mindmap_path = tmp_path / "tasks" / task_id / "mindmap.json"
    mindmap_path.parent.mkdir(parents=True, exist_ok=True)
    mindmap_path.write_text(
        '{"version":1,"title":"导图","root":"root","nodes":[{"id":"root","label":"导图","type":"root","children":[{"id":"theme","label":"主题","type":"theme","children":[]}]}]}',
        encoding="utf-8",
    )
    repository.save_result(
        task_id,
        record.result.model_copy(
            update={
                "mindmap_status": "ready",
                "mindmap_artifact_path": str(mindmap_path),
                "artifacts": {**record.result.artifacts, "mindmap_path": str(mindmap_path)},
            }
        ),
    )
    app.state.task_repository = repository
    settings = ServiceSettings(
        data_dir=tmp_path / "data",
        cache_dir=tmp_path / "cache",
        tasks_dir=tmp_path / "tasks",
        output_dir=str(tmp_path / "vault"),
    )

    response = export_task_markdown(repository, settings, task_id)
    export_path = Path(response.path)
    content = export_path.read_text(encoding="utf-8")

    assert "## 思维导图" in content
    assert "```mermaid\nmindmap" in content
    assert "root((导图))" in content
    assert (export_path.parent / f"{export_path.stem}.assets" / "mindmap.json").exists()
    assert str(mindmap_path) not in content


def test_export_task_markdown_can_include_transcript_from_configured_output_dir(tmp_path: Path) -> None:
    repository = create_repository()
    task_id = create_completed_task(repository)
    app.state.task_repository = repository
    output_dir = tmp_path / "picked-vault"
    settings = ServiceSettings(
        data_dir=tmp_path / "data",
        cache_dir=tmp_path / "cache",
        tasks_dir=tmp_path / "tasks",
        output_dir=str(output_dir),
    )
    settings_manager._settings = settings

    response = export_task_markdown(repository, settings, task_id, include_transcript=True)

    assert Path(response.path).parent == output_dir
    content = Path(response.path).read_text(encoding="utf-8")
    assert "## 转写全文" in content
    assert "[00:00] 转写内容" in content


def test_export_task_markdown_copies_visual_assets_with_relative_links(tmp_path: Path) -> None:
    repository = create_repository()
    task_id = create_completed_task(repository)
    record = repository.get_task(task_id)
    assert record is not None and record.result is not None
    visual_dir = tmp_path / "tasks" / task_id / "visual_evidence"
    frames_dir = visual_dir / "frames"
    frames_dir.mkdir(parents=True)
    frame_path = frames_dir / "f0001.jpg"
    frame_path.write_bytes(b"fake-jpeg")
    visual_note_path = visual_dir / "visual_enhanced_note.md"
    visual_note_path.write_text("## 知识笔记\n\n这个概念需要对照画面理解。\n\n![00:12 画面](visual://f0001)\n\n画面说明被整合进正文。", encoding="utf-8")
    repository.save_result(
        task_id,
        record.result.model_copy(
            update={
                    "visual_note_status": "ready",
                    "visual_note_artifact_path": str(visual_note_path),
                    "visual_enhanced_note_artifact_path": str(visual_note_path),
                    "visual_frame_count": 1,
                    "artifacts": {**record.result.artifacts, "visual_enhanced_note_path": str(visual_note_path)},
                }
            ),
        )
    settings = ServiceSettings(
        data_dir=tmp_path / "data",
        cache_dir=tmp_path / "cache",
        tasks_dir=tmp_path / "tasks",
        output_dir=str(tmp_path / "vault"),
    )

    response = export_task_markdown(repository, settings, task_id)
    export_path = Path(response.path)
    content = export_path.read_text(encoding="utf-8")

    assert "这个概念需要对照画面理解。" in content
    assert "画面说明被整合进正文。" in content
    assert "## 视觉证据" not in content
    assert f"![[{export_path.stem}.assets/f0001.jpg]]" in content
    assert (export_path.parent / f"{export_path.stem}.assets" / "f0001.jpg").read_bytes() == b"fake-jpeg"
    assert "visual_evidence" not in content


def test_export_task_markdown_copies_visual_asset_by_frame_index(tmp_path: Path) -> None:
    repository = create_repository()
    task_id = create_completed_task(repository)
    record = repository.get_task(task_id)
    assert record is not None and record.result is not None
    visual_dir = tmp_path / "tasks" / task_id / "visual_evidence"
    frames_dir = visual_dir / "frames"
    frames_dir.mkdir(parents=True)
    frame_path = frames_dir / "frame-a.webp"
    frame_path.write_bytes(b"fake-webp")
    (visual_dir / "frame_index.json").write_text(
        '{"frames":[{"frame_id":"f0001","file_name":"frame-a.webp","image_path":"frames/frame-a.webp"}]}',
        encoding="utf-8",
    )
    visual_note_path = visual_dir / "visual_enhanced_note.md"
    visual_note_path.write_text("正文。\n\n![00:12 画面](visual://f0001)", encoding="utf-8")
    repository.save_result(
        task_id,
        record.result.model_copy(
            update={
                "visual_note_status": "ready",
                "visual_enhanced_note_artifact_path": str(visual_note_path),
                "visual_frame_count": 1,
                "artifacts": {**record.result.artifacts, "visual_enhanced_note_path": str(visual_note_path)},
            }
        ),
    )
    settings = ServiceSettings(
        data_dir=tmp_path / "data",
        cache_dir=tmp_path / "cache",
        tasks_dir=tmp_path / "tasks",
        output_dir=str(tmp_path / "vault"),
    )

    response = export_task_markdown(repository, settings, task_id)
    export_path = Path(response.path)
    content = export_path.read_text(encoding="utf-8")

    assert f"![[{export_path.stem}.assets/frame-a.webp]]" in content
    assert (export_path.parent / f"{export_path.stem}.assets" / "frame-a.webp").read_bytes() == b"fake-webp"


def test_export_task_markdown_avoids_overwriting_existing_file(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    fixed_export_time = datetime.fromisoformat("2026-04-22T12:00:00+08:00")

    class FixedDatetime(datetime):
        @classmethod
        def now(cls, tz=None):
            if tz is None:
                return fixed_export_time
            return fixed_export_time.astimezone(tz)

    monkeypatch.setattr(task_exports, "datetime", FixedDatetime)
    repository = create_repository()
    task_id = create_completed_task(repository)
    output_dir = tmp_path / "vault"
    output_dir.mkdir(parents=True, exist_ok=True)
    existing = output_dir / build_export_filename("测试导出视频", fixed_export_time)
    existing.write_text("old", encoding="utf-8")

    app.state.task_repository = repository
    settings = ServiceSettings(
        data_dir=tmp_path / "data",
        cache_dir=tmp_path / "cache",
        tasks_dir=tmp_path / "tasks",
        output_dir=str(output_dir),
    )
    settings_manager._settings = settings

    response = export_task_markdown(repository, settings, task_id)

    assert response.file_name != existing.name
    assert response.file_name.endswith(".md")
    assert response.overwritten is True


def test_export_task_markdown_rejects_task_without_note(tmp_path: Path) -> None:
    repository = create_repository()
    video = repository.upsert_video_asset(
        VideoAssetRecord(
            canonical_id="BV1empty",
            platform="bilibili",
            title="空笔记视频",
            source_url="https://www.bilibili.com/video/BV1empty",
            cover_url="",
        )
    )
    record = repository.create_task(
        TaskInput(input_type=InputType.URL, source=video.source_url, title=video.title),
        video_id=video.video_id,
    )
    repository.save_result(record.task_id, TaskResult(overview="概览", knowledge_note_markdown="", artifacts={}))
    repository.update_status(record.task_id, TaskStatus.COMPLETED)
    app.state.task_repository = repository
    settings = ServiceSettings(
        data_dir=tmp_path / "data",
        cache_dir=tmp_path / "cache",
        tasks_dir=tmp_path / "tasks",
        output_dir=str(tmp_path / "vault"),
    )
    settings_manager._settings = settings

    with pytest.raises(HTTPException, match="知识笔记"):
        export_task_markdown(repository, settings, record.task_id)


def test_export_task_transcript_writes_file_and_persists_artifact(tmp_path: Path) -> None:
    repository = create_repository()
    task_id = create_completed_task(repository)
    app.state.task_repository = repository
    settings = ServiceSettings(
        data_dir=tmp_path / "data",
        cache_dir=tmp_path / "cache",
        tasks_dir=tmp_path / "tasks",
        output_dir=str(tmp_path / "vault"),
    )
    settings_manager._settings = settings

    response = export_task_transcript(repository, settings, task_id)
    refreshed = repository.get_task(task_id)

    assert response.target_format == "transcript"
    assert response.file_name.endswith(".txt")
    assert Path(response.path).read_text(encoding="utf-8") == "[00:00] 转写内容"
    assert refreshed is not None
    assert refreshed.result is not None
    assert refreshed.result.artifacts["transcript_export_path"] == response.path


def test_export_task_transcript_rejects_task_without_transcript(tmp_path: Path) -> None:
    repository = create_repository()
    task_id = create_completed_task(repository)
    record = repository.get_task(task_id)
    assert record is not None
    repository.save_result(task_id, record.result.model_copy(update={"transcript_text": "", "artifacts": {}}))
    app.state.task_repository = repository
    settings = ServiceSettings(
        data_dir=tmp_path / "data",
        cache_dir=tmp_path / "cache",
        tasks_dir=tmp_path / "tasks",
        output_dir=str(tmp_path / "vault"),
    )

    with pytest.raises(HTTPException, match="转写全文"):
        export_task_transcript(repository, settings, task_id)
