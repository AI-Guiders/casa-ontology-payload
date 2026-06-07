#!/usr/bin/env python3
"""Block slot extraction — frame → structured slots for realizers."""

from __future__ import annotations

import re
from typing import Any

from casa.prisms.tick.discourse.model import ClauseSketch
from casa.prisms.tick.discourse.render import clause_from_slot_phrase


class BlockSlots:
    @staticmethod
    def read(block: dict[str, Any]) -> dict[str, str]:
        raw = block.get("slots")
        if isinstance(raw, dict) and raw:
            return {str(k): str(v) for k, v in raw.items() if v}
        return BlockSlots.infer_from_frame(block)

    @staticmethod
    def infer_from_frame(block: dict[str, Any]) -> dict[str, str]:
        cid = str(block.get("concept_id") or "")
        text = str(block.get("text") or "")
        quoted = [q.strip() for q in re.findall(r"«([^»]{1,80})»", text) if q.strip()]
        if not quoted:
            return {}
        out: dict[str, str] = {}
        tl = text.lower()
        if cid.startswith("ru.dialog."):
            if len(quoted) >= 2 and ("ответ" in tl or "отвеча" in tl):
                out["stimulus"] = quoted[0].rstrip(".!?").lower()
                out["response"] = quoted[1].rstrip(".!?").lower()
            elif quoted:
                out["surface"] = quoted[0].rstrip(".!?").lower()
        elif cid.startswith("lang.word."):
            out["word"] = quoted[0].rstrip(".!?").lower()
        return out

    @staticmethod
    def clause_indices(slots: dict[str, str]) -> list[int]:
        indices: set[int] = set()
        for key in slots:
            m = re.fullmatch(r"(?:clause|sentence)_(\d+)", key)
            if m:
                indices.add(int(m.group(1)))
        return sorted(indices)

    @staticmethod
    def extra_clauses(slots: dict[str, str], *, skip_primary: bool = True) -> list[ClauseSketch]:
        out: list[ClauseSketch] = []
        for i in BlockSlots.clause_indices(slots):
            if skip_primary and i <= 1:
                continue
            body = slots.get(f"clause_{i}") or slots.get(f"sentence_{i}")
            if not body:
                continue
            linker = slots.get(f"linker_{i}") or slots.get(f"bridge_{i}") or ""
            clause = clause_from_slot_phrase(body, linker=linker)
            if clause:
                out.append(clause)
        return out

    @staticmethod
    def meta_linkers(blocks: list[dict[str, Any]]) -> list[str]:
        linkers: list[str] = []
        for b in blocks:
            cid = str(b.get("concept_id") or "")
            if not cid.startswith("ru.meta.discourse."):
                continue
            slots = BlockSlots.read(b)
            for i in BlockSlots.clause_indices(slots):
                body = slots.get(f"linker_{i}") or ""
                if body:
                    linkers.append(str(body))
        return linkers
