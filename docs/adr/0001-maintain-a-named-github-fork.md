---
status: accepted
---

# Maintain a named GitHub fork

Maintain `aaronfang/BiliSum-Research` as a GitHub fork of `lycohana/BiliSum` instead of starting a greenfield repository. The target product reuses BiliSum’s ingestion, task persistence, desktop app, knowledge base, exporters, and packaging; preserving the fork relationship makes attribution and upstream synchronization explicit, while new behavior is isolated behind focused module interfaces to contain merge cost.
