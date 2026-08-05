from __future__ import annotations

import re
import unicodedata


def normalize_tag(value: object, *, max_length: int = 80) -> str:
    tag = unicodedata.normalize("NFKC", str(value or "")).strip().lstrip("#")
    tag = re.sub(r"\s+", "-", tag)
    tag = tag.strip(" -*_`~.,!?;：，。；！？")
    return tag[:max_length]


def tag_key(value: object) -> str:
    return normalize_tag(value).casefold()
