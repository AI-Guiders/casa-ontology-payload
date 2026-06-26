#!/usr/bin/env python3
"""Sensory stack contracts — ADR-0027 layer boundaries (host side, not agent store)."""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

BACKEND_FILE_REPLAY = "file_replay"
BACKEND_FILE_REPLAY_STREAM = "file_replay_stream"


@dataclass(frozen=True)
class RawCapture:
    """Adapter output: normalized peripheral session, no imprint."""

    capture_id: str
    ts_ms: int
    session_dir: Path
    modalities_present: frozenset[str]
    provenance: dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class ListenCorpusCapture:
    """Resolved listen manifest scene — corpus file_replay backend (cold ingest / moment)."""

    backend_id: str
    scene_id: str
    scene: dict[str, Any]
    wav_path: Path | None
    frame_entries: list[tuple[Path, str, float | None]]
    beat_plans: list[dict[str, Any]]
    store_dir: Path | None
    manifest_dir: Path | None

    @property
    def bases(self) -> tuple[Path | None, ...]:
        return (self.manifest_dir, self.store_dir)


@dataclass(frozen=True)
class ListenStreamCapture:
    """Chapter video + wav for wall-clock stream driver (file_replay_stream)."""

    backend_id: str
    scene_id: str
    stream_id: str
    scene: dict[str, Any]
    video_path: Path
    wav_path: Path | None
    chapter_t0: float
    chapter_t1: float
    store_dir: Path | None
    manifest_dir: Path | None
