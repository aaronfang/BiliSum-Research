---
status: accepted
---

# Use transcript-first visual verification

Resolve subtitles or local ASR before invoking visual models, then inspect only time ranges identified by Text Anchors. This reduces local compute and preserves accuracy for long technical videos; continuous full-video visual analysis remains an explicit user option rather than the default.
