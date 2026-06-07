#!/usr/bin/env python3
"""Anti-paste metric for probe gates."""

from __future__ import annotations

from typing import Any


def paste_ratio_against_blocks(answer_text: str, blocks: list[dict[str, Any]]) -> float:
    if not answer_text:
        return 0.0
    at = answer_text.lower()
    pasted = 0
    for b in blocks:
        if b.get("source") in {"dialogue", "journal"}:
            continue
        t = str(b.get("text") or "")
        if len(t) < 80:
            continue
        chunk = t.lower()[: min(72, len(t))]
        if chunk in at:
            pasted += len(chunk)
    return min(1.0, pasted / max(len(at), 1))
