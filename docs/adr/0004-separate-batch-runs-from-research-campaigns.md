---
status: accepted
---

# Separate Batch Runs from Research Campaigns

A Batch Run executes a known bounded set of Media Sources, while a Research Campaign decides which sources to discover and analyze under a Research Brief. Keeping these concepts separate prevents search and synthesis policy from leaking into reliable media processing, and lets Research Campaigns delegate selected sources through the same tested BatchRunner interface used by local directories and playlists.
