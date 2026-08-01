# Product Vision

## Purpose

BiliSum Research turns technical videos into accurate, traceable knowledge. It processes local media in batches, prefers existing subtitles over transcription, uses video frames only where text needs verification, resolves mentioned tools to verified resources, and publishes durable notes into Obsidian.

The longer-term product can execute bounded Research Campaigns such as “research open-source virtual-human projects”: discover relevant videos, select useful sources, analyze them locally, verify project facts against official sources, and synthesize a Topic Report.

## Primary Users

- Developers converting tutorials, technical news, talks, and demonstrations into reference notes.
- Researchers comparing projects across Chinese and English video sources.
- Obsidian users building a long-lived, linked knowledge base from media.
- Teams processing a controlled directory, URL list, playlist, or channel backlog.

## Product Principles

1. **Text first, vision on demand.** Resolve subtitles or audio before spending visual-model compute. Inspect frames and clips for Text Anchors, not for decorative summaries.
2. **Local by default.** Media and derived artifacts remain local. Cloud providers require explicit opt-in and disclose what leaves the machine.
3. **Evidence before fluency.** Preserve raw text, record every correction, and prefer an uncertain result over a confident invention.
4. **Batch is a product behavior.** Work must be resumable, deduplicated, resource-aware, and observable.
5. **Obsidian is a knowledge target.** Publish linked Source Notes, Entity Notes, Topic Reports, and Topic Indexes rather than isolated Markdown exports.
6. **Research is bounded.** Every Research Campaign has scope, budgets, source rules, and stop conditions.

## Core Workflows

### Analyze Local Media

1. Select a file, directory, URL list, or playlist.
2. Resolve the best Transcript Source.
3. Extract chapters, Tool References, Claims, and uncertain text.
4. Build Text Anchors and inspect only relevant frames or clips.
5. Produce a Corrected Transcript with an audit trail.
6. Resolve tools and publish evidence-backed notes to Obsidian.

### Find Visual Evidence From Text

1. Search for an entity, command, claim, or phrase.
2. Locate timed transcript segments.
3. Select clear frames or short clips in the surrounding interval.
4. Return the media, OCR, transcript context, and support status.

### Run A Topic Investigation

1. Submit a Research Brief.
2. Generate multilingual queries and source-selection criteria.
3. Discover and rank videos using metadata and available subtitles.
4. Download only selected audio or video.
5. Run Analysis Jobs under campaign budgets.
6. Verify project facts against official repositories and documentation.
7. Publish a Topic Report and linked supporting notes.

## Non-Goals

- Editing, translating, dubbing, or republishing videos.
- Continuous high-frame-rate analysis of every video.
- Circumventing access controls or platform restrictions.
- Treating a video author’s opinion as an official project fact.
- Silently rewriting user-authored Obsidian content.
- Requiring cloud AI for baseline operation.

## Success Measures

- Technical entity, command, and URL exact-match F1 of at least 95% on the project corpus.
- Automatic correction precision of at least 98%; fabricated verified URLs are not acceptable.
- Every material report claim links to a timestamp, frame, clip, or official external source.
- A restarted process resumes a Batch Run without repeating completed stages.
- Generated Obsidian wikilinks and attachment links have no broken targets.
