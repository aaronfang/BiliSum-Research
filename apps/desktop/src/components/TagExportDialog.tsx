import { useState, type KeyboardEvent } from "react";

import type { TaskMarkdownTagPreviewItem } from "../types";

type TagExportDialogProps = {
  isOpen: boolean;
  title: string;
  items: TaskMarkdownTagPreviewItem[];
  loading: boolean;
  exporting: boolean;
  includeTranscript: boolean;
  errorMessage?: string;
  onClose(): void;
  onChangeItems(items: TaskMarkdownTagPreviewItem[]): void;
  onIncludeTranscriptChange(value: boolean): void;
  onExport(): void;
};

function sourceLabel(source: string) {
  if (source === "manual") {
    return "手动标签";
  }
  if (source === "explicit") {
    return "笔记中的 #标签";
  }
  if (source === "auto_llm") {
    return "自动标签";
  }
  return "标签";
}

export function TagExportDialog({
  isOpen,
  title,
  items,
  loading,
  exporting,
  includeTranscript,
  errorMessage,
  onClose,
  onChangeItems,
  onIncludeTranscriptChange,
  onExport,
}: TagExportDialogProps) {
  const [newTag, setNewTag] = useState("");

  if (!isOpen) {
    return null;
  }

  const selectedItems = items.filter((item) => item.selected);
  const suggestions = items.filter((item) => !item.selected && item.source === "auto_llm");

  function toggleItem(tag: string) {
    onChangeItems(items.map((item) => item.tag === tag ? { ...item, selected: !item.selected } : item));
  }

  function removeItem(tag: string) {
    onChangeItems(items.map((item) => item.tag === tag ? { ...item, selected: false } : item));
  }

  function addTag() {
    const value = newTag.trim();
    if (!value) {
      return;
    }
    const normalized = value.replace(/^#+/, "").trim();
    if (!normalized || items.some((item) => item.tag.toLocaleLowerCase() === normalized.toLocaleLowerCase())) {
      setNewTag("");
      return;
    }
    onChangeItems([...items, { tag: normalized, source: "manual", selected: true }]);
    setNewTag("");
  }

  function handleTagKeyDown(event: KeyboardEvent<HTMLInputElement>) {
    if (event.key === "Enter") {
      event.preventDefault();
      addTag();
    }
  }

  return (
    <div
      className="tag-export-dialog-backdrop"
      role="presentation"
      onMouseDown={(event) => {
        if (event.target === event.currentTarget && !exporting) {
          onClose();
        }
      }}
    >
      <div className="tag-export-dialog" role="dialog" aria-modal="true" aria-labelledby="tag-export-dialog-title">
        <header className="tag-export-dialog-header">
          <div>
            <span className="tag-export-dialog-kicker">Export preparation</span>
            <h2 id="tag-export-dialog-title">确认 Obsidian 标签</h2>
            <p>{title || "当前知识笔记"}</p>
          </div>
          <button className="tag-export-dialog-close" type="button" onClick={onClose} disabled={exporting} aria-label="关闭标签预览">
            ×
          </button>
        </header>

        <div className="tag-export-dialog-body">
          <div className="tag-export-dialog-intro">
            <strong>导出前预览</strong>
            <span>只有下方勾选的标签会写入 Obsidian；标题和摘要不会自动生成新标签。</span>
          </div>

          <section className="tag-export-dialog-section">
            <div className="tag-export-dialog-section-head">
              <strong>将要导出的标签</strong>
              <span>{selectedItems.length} 个</span>
            </div>
            <div className="tag-export-dialog-tags">
              {selectedItems.map((item) => (
                <span className="tag-export-dialog-tag" key={item.tag}>
                  <span>#{item.tag}</span>
                  <small>{sourceLabel(item.source)}</small>
                  <button type="button" onClick={() => removeItem(item.tag)} disabled={exporting} aria-label={`移除标签 ${item.tag}`}>
                    ×
                  </button>
                </span>
              ))}
              {!selectedItems.length ? <span className="tag-export-dialog-empty">暂不导出任何标签。</span> : null}
            </div>
          </section>

          {suggestions.length ? (
            <section className="tag-export-dialog-section">
              <div className="tag-export-dialog-section-head">
                <strong>未导出的自动标签</strong>
                <span>点击即可重新加入</span>
              </div>
              <div className="tag-export-dialog-suggestions">
                {suggestions.map((item) => (
                  <button className="tag-export-dialog-suggestion" type="button" key={item.tag} onClick={() => toggleItem(item.tag)} disabled={exporting}>
                    <span>+ #{item.tag}</span>
                    <small>{sourceLabel(item.source)}</small>
                  </button>
                ))}
              </div>
            </section>
          ) : null}

          <section className="tag-export-dialog-section">
            <label className="tag-export-dialog-add-label" htmlFor="tag-export-dialog-new-tag">添加标签</label>
            <div className="tag-export-dialog-add-row">
              <input
                id="tag-export-dialog-new-tag"
                className="input-field"
                value={newTag}
                onChange={(event) => setNewTag(event.target.value)}
                onKeyDown={handleTagKeyDown}
                placeholder="输入标签后按 Enter"
                disabled={exporting}
              />
              <button className="secondary-button" type="button" onClick={addTag} disabled={!newTag.trim() || exporting}>添加</button>
            </div>
          </section>

          <label className="tag-export-dialog-checkbox">
            <input type="checkbox" checked={includeTranscript} onChange={(event) => onIncludeTranscriptChange(event.target.checked)} disabled={exporting} />
            <span>导出笔记时附带转写全文</span>
          </label>
          {loading ? <p className="tag-export-dialog-status">正在准备标签预览...</p> : null}
          {errorMessage ? <p className="tag-export-dialog-error" role="alert">{errorMessage}</p> : null}
        </div>

        <footer className="tag-export-dialog-footer">
          <button className="secondary-button" type="button" onClick={onClose} disabled={exporting}>取消</button>
          <button className="primary-button" type="button" onClick={onExport} disabled={loading || exporting || Boolean(errorMessage)}>
            {exporting ? "正在导出..." : "确认并导出"}
          </button>
        </footer>
      </div>
    </div>
  );
}
