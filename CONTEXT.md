# BiliSum Research

BiliSum Research turns videos into evidence-backed knowledge and coordinates bounded research across multiple videos. This glossary defines the language shared by product documents, code, tests, and generated artifacts.

## Inputs And Text

**Media Source**:
A local media file or a remote video reference accepted for processing.
_Avoid_: Video input, asset

**Transcript Source**:
The origin of timed text, such as a sidecar subtitle, platform subtitle, automatic subtitle, or ASR result.
_Avoid_: Transcript provider

**Transcript**:
Immutable timed text resolved from one Transcript Source, including provenance and quality metadata.
_Avoid_: Raw text, subtitles

**Corrected Transcript**:
A derived Transcript whose edits are individually backed by Evidence and retained in a correction audit.
_Avoid_: Clean transcript, polished transcript

**Text Anchor**:
A time-bound request to inspect media for a specific entity, claim, command, URL, number, or uncertain phrase.
_Avoid_: Keyframe request, visual query

## Evidence And Knowledge

**Evidence**:
A timestamped observation derived from audio, subtitle text, a frame, a clip, OCR, or an official external source.
_Avoid_: Context, data point

**Claim**:
A normalized statement that can be supported, contradicted, or left uncertain by Evidence.
_Avoid_: Fact, finding

**Correction**:
A proposed change from a Transcript to a Corrected Transcript, with its Evidence, confidence, and decision status.
_Avoid_: Fix, rewrite

**Tool Reference**:
A time-bound mention of a tool, library, model, service, protocol, or repository before its canonical identity is resolved.
_Avoid_: Tool, link

**Verified Resource**:
A canonical external resource whose identity and URL passed deterministic validation.
_Avoid_: Search result, official link

## Work Coordination

**Analysis Job**:
One resumable processing run for a single Media Source.
_Avoid_: Task, video job

**Batch Run**:
A bounded collection of Analysis Jobs sharing resource limits, retry policy, and completion status.
_Avoid_: Batch task, queue

**Research Brief**:
A user goal, scope, constraints, evidence rules, and budgets for a topic investigation.
_Avoid_: Prompt, query

**Research Campaign**:
A resumable execution of a Research Brief that discovers, selects, analyzes, and synthesizes multiple sources.
_Avoid_: Deep research, research job

## Obsidian Outputs

**Source Note**:
An Obsidian note representing one analyzed Media Source with timestamps and Evidence links.
_Avoid_: Video note

**Entity Note**:
An Obsidian note representing one canonical project, tool, model, or organization across sources.
_Avoid_: Tool note

**Topic Report**:
An evidence-backed synthesis produced by a Research Campaign.
_Avoid_: Summary, final note

**Topic Index**:
An Obsidian map-of-content note linking a Topic Report, its Source Notes, and Entity Notes.
_Avoid_: Folder index, MOC file
