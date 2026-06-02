#!/usr/bin/env python3
"""Teacher inbox layout and file ops for agent reactor."""

from __future__ import annotations

import json
import shutil
import time
from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path
from typing import Any, TYPE_CHECKING

if TYPE_CHECKING:
    from casa.prisms.memory.agent_life import AgentRuntime


@dataclass(frozen=True)
class InboxLayout:
    inbox: Path
    processed: Path
    failed: Path


def inbox_layout(root: Path) -> InboxLayout:
    root = root.resolve()
    return InboxLayout(
        inbox=root,
        processed=root / "_processed",
        failed=root / "_failed",
    )


def ensure_inbox_dirs(layout: InboxLayout) -> None:
    layout.inbox.mkdir(parents=True, exist_ok=True)
    layout.processed.mkdir(parents=True, exist_ok=True)
    layout.failed.mkdir(parents=True, exist_ok=True)


def inbox_json_files(inbox: Path) -> list[Path]:
    return sorted(
        [p for p in inbox.glob("*.json") if p.is_file()],
        key=lambda p: p.stat().st_mtime,
    )


def move_inbox_file(dst_dir: Path, src: Path) -> Path:
    dst_dir.mkdir(parents=True, exist_ok=True)
    target = dst_dir / src.name
    if target.exists():
        target = dst_dir / f"{src.stem}.{int(time.time())}{src.suffix}"
    return Path(shutil.move(str(src), str(target)))


def load_inbox_payload(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def drain_inbox_batch(
    runtime: AgentRuntime,
    layout: InboxLayout,
    *,
    ingest: Callable[..., dict[str, Any]],
    emit: Callable[[dict[str, Any]], None] | None = None,
) -> bool:
    """Process pending inbox JSON files into the live runtime. Returns True if any ran."""
    items = inbox_json_files(layout.inbox)
    if not items:
        return False

    def _log(event: dict[str, Any]) -> None:
        if emit is not None:
            emit(event)

    _log({"inbox_pending": len(items)})
    for path in items:
        try:
            _log({"ingesting": path.name})
            payload = load_inbox_payload(path)
            rep = ingest(
                runtime.store_dir,
                payload,
                state=runtime.state,
                persist=False,
            )
            moved = move_inbox_file(layout.processed, path)
            _log(
                {
                    "ingested": path.name,
                    "moved_to": str(moved),
                    "class_id": rep.get("class_id"),
                    "sleep_mode": rep.get("sleep_mode"),
                    "bridges_emergent": rep.get("bridges_emergent"),
                }
            )
        except Exception as e:  # noqa: BLE001 - operator tool
            move_inbox_file(layout.failed, path)
            _log({"failed": path.name, "error": repr(e)})
    return True
