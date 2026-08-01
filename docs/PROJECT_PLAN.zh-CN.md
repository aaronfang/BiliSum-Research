# BiliSum Research 项目开发总览

## 仓库决策

本项目采用 BiliSum 的具名 GitHub fork，而不是新建空仓库：

- 复用现有的视频导入、ASR、任务队列、SQLite、桌面端、知识库和 Obsidian 导出；
- 保留与 `lycohana/BiliSum` 的上游关系，方便持续同步修复和功能；
- 把新增能力放入独立模块，减少上游合并冲突；
- fork 名称使用 `BiliSum-Research`，明确它不是原项目的官方版本。

## 产品目标

系统分为两层：

1. **视频分析层**：批量处理本地视频或 URL，优先使用字幕/音频，只在关键技术信息处根据文字定位帧或短片段，完成证据约束的纠错，并写入 Obsidian。
2. **主题调研层**：接收“调研开源虚拟人项目”之类目标，自动规划查询、搜索和筛选视频、批量分析、核验官方资料、比较多来源结论，最终生成主题报告。

核心原则：本地优先、字幕优先、视觉按需、证据优先、批量可恢复、研究有预算、Obsidian 原生。

## 推荐阅读顺序

1. [产品愿景](product/vision.md)：目标用户、核心流程和非目标。
2. [领域词汇](../CONTEXT.md)：Transcript、Text Anchor、Evidence、Batch Run、Research Campaign 等统一定义。
3. [架构总览](architecture/overview.md)：模块接口、数据流、存储和部署方式。
4. [MVP 规格](specs/mvp.md)：第一版必须实现和明确延期的内容。
5. [实施路线图](roadmap.md)：按依赖关系排列的里程碑。
6. [开发环境](development/getting-started.md)：如何安装、运行、测试以及从哪里开始搭框架。
7. [架构决策](adr/)：fork、文字优先视觉验证、Obsidian 发布和任务模型的原因。

## 目标架构

```text
本地文件 / 目录 / URL / 播放列表 / Research Brief
  -> TranscriptResolver（sidecar/平台字幕优先，本地 ASR 回退）
  -> TextAnalyzer（章节、工具、主张、不确定项、Text Anchor）
  -> EvidenceEngine（定向选帧、OCR、短片段、视觉验证）
  -> FusionEngine（生成可审计的 Corrected Transcript）
  -> LinkResolver（查找并验证官网、仓库和包注册表）
  -> NotePublisher（Source Note、Entity Note、Topic Report、Topic Index）

BatchRunner 负责已知输入集合。
ResearchCampaignEngine 负责发现和筛选来源，并把选中的视频交给 BatchRunner。
```

## MVP 范围

第一版只完成一条可靠闭环：

> 输入一个本地技术视频目录及可选字幕，生成可写入 Obsidian 的来源笔记；笔记包含带时间戳的准确文字、关键技术词的视觉证据、保守纠错、截图和批次状态。

MVP 包含：

- 非递归本地目录批量输入；
- 同名 `.srt`/`.vtt` 字幕优先，本地 ASR 回退；
- 工具名、命令、URL、版本号和数字的 Text Anchor；
- 在文字对应时间附近定向选帧、OCR 和验证；
- 原始 transcript 永久保留，纠错逐条记录证据；
- 内容哈希去重、单视频失败隔离、重启后续跑；
- Obsidian `export`、`dry-run`、`sync`；
- 稳定 YAML、wikilink、附件路径和用户内容保护。

MVP 不包含自动搜索视频、跨视频综合和 Research Campaign。这些能力依赖稳定的单视频分析与 BatchRunner，放在后续里程碑。

## 实施顺序

1. 给当前本地视频、B 站字幕、任务持久化和 Markdown 导出补特征测试。
2. 建立数据库迁移机制。
3. 提取 `TranscriptResolver`，先实现 sidecar 字幕。
4. 实现可恢复 `BatchRunner` 和目录输入。
5. 实现 `TextAnalyzer`、`TextAnchor` 和 `EvidenceEngine`。
6. 实现保守的 `FusionEngine` 与纠错审计。
7. 实现 Obsidian 原生发布。
8. 实现链接核验和远程播放列表批量。
9. 最后实现 `ResearchCampaignEngine`。

## 第一次搭框架的边界

第一次开发不要一次创建所有空包。只做一个纵向切片：

1. 特征测试锁定当前本地视频处理行为；
2. 新建 Transcript 和 Transcript Source 模型；
3. 新建 sidecar 字幕 adapter；
4. 用 `TranscriptResolver.resolve(source, policy) -> Transcript` 包住现有字幕/ASR 分支；
5. 保存 provenance，但暂时不改变现有 UI 输出。

完成后，这个 interface 同时成为调用入口和测试表面。后续 B 站、YouTube、Qwen3-ASR、FunASR 和 Whisper 都只是内部 adapter。

## 质量底线

- 技术实体、命令、URL exact-match F1 不低于 95%；
- 自动纠错 precision 不低于 98%；
- 虚构 verified URL 为 0；
- 关键结论全部能回溯到时间戳、帧、片段或官方来源；
- 重启后不重复执行已经完成且缓存键一致的阶段；
- 生成的 Obsidian wikilink 和附件链接无断链；
- 核心测试不依赖联网、云模型或真实凭据。

## 下一步

按 [Milestone 0](roadmap.md#milestone-0-preserve-upstream-behavior) 开始：先建立特征测试与迁移基础，再进入 TranscriptResolver。不要直接从自动主题调研或 UI 页面开始。
