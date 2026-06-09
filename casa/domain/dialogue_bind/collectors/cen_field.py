"""CEN, field snapshot, digest, and capability block collection."""

from __future__ import annotations

from typing import Any

from casa.domain.dialogue_bind.blocks import answer_block_to_dict, block_dict
from casa.domain.dialogue_bind.field import capability_block, field_snapshot_block
from casa.prisms.control.fpn_state import WorkingMemory
from casa.prisms.control.sn_cen_runtime import TaskEmit


def collect_cen_blocks(
    task: TaskEmit | None,
    intent: str,
) -> tuple[list[dict[str, Any]], list[str]]:
    blocks: list[dict[str, Any]] = []
    sources: list[str] = []

    if task and task.answer_blocks:
        for b in task.answer_blocks:
            row = answer_block_to_dict(b)
            row["score"] = int(row.get("score") or 0) + (4 if intent != "social" else 0)
            blocks.append(row)
        sources.append("cen")

    return blocks, sources


def collect_field_blocks(
    state: dict,
    wm: WorkingMemory,
    task: TaskEmit | None,
    intent: str,
) -> tuple[list[dict[str, Any]], list[str]]:
    blocks: list[dict[str, Any]] = []
    sources: list[str] = []

    blocks.append(field_snapshot_block(state, wm, intent=intent))
    sources.append("field")

    if task and task.concepts and intent == "social":
        blocks.append(capability_block(state, wm, task))
        sources.append("capability")

    if task and task.concepts:
        for i, cid in enumerate(task.concepts[:5]):
            if str(cid).startswith("module:"):
                continue
            base = 12 - i if intent in ("math", "grammar", "recall") else 7 - i
            blocks.append(
                block_dict(
                    f"subject.digest.{cid}",
                    f"Digest: на поле {cid}.",
                    source="digest",
                    score=base,
                )
            )
        sources.append("digest")

    return blocks, sources
