#!/usr/bin/env python3
"""Dialogue turns — session ring buffer (ADR-0045)."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from casa.prisms.control.fpn_state import read_session_meta, write_session_meta

DIALOGUE_RING_MAX = 256
SESSION_KEY = "dialogue_turns"


@dataclass(frozen=True, slots=True)
class DialogueTurn:
    at: str
    speaker: str  # subject | partner | system
    text: str
    kind: str  # reply | initiate | defer | refuse | clarify | retro
    disposition: str | None = None
    provenance: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        out: dict[str, Any] = {
            "at": self.at,
            "speaker": self.speaker,
            "text": self.text,
            "kind": self.kind,
            "provenance": dict(self.provenance or {}),
        }
        if self.disposition:
            out["disposition"] = self.disposition
        return out

    @classmethod
    def from_dict(cls, raw: dict[str, Any]) -> DialogueTurn:
        return cls(
            at=str(raw.get("at") or _utc_now()),
            speaker=str(raw.get("speaker") or "system"),
            text=str(raw.get("text") or ""),
            kind=str(raw.get("kind") or "reply"),
            disposition=str(raw["disposition"]) if raw.get("disposition") else None,
            provenance=dict(raw.get("provenance") or {}),
        )


def _utc_now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def load_dialogue_turns(store_dir: Path) -> list[DialogueTurn]:
    meta = read_session_meta(store_dir)
    raw = meta.get(SESSION_KEY)
    if not isinstance(raw, list):
        return []
    out: list[DialogueTurn] = []
    for item in raw:
        if isinstance(item, dict) and item.get("text"):
            out.append(DialogueTurn.from_dict(item))
    return out


def _persist_turns(store_dir: Path, turns: list[DialogueTurn]) -> None:
    meta = read_session_meta(store_dir)
    meta[SESSION_KEY] = [t.to_dict() for t in turns[-DIALOGUE_RING_MAX:]]
    write_session_meta(store_dir, meta)


def append_dialogue_turn(store_dir: Path, turn: DialogueTurn) -> DialogueTurn:
    turns = load_dialogue_turns(store_dir)
    turns.append(turn)
    _persist_turns(store_dir, turns)
    return turn


def append_partner_turn(
    store_dir: Path,
    text: str,
    *,
    kind: str = "reply",
    provenance: dict[str, Any] | None = None,
) -> DialogueTurn:
    return append_dialogue_turn(
        store_dir,
        DialogueTurn(
            at=_utc_now(),
            speaker="partner",
            text=text.strip(),
            kind=kind,
            provenance=provenance or {},
        ),
    )


def append_subject_turn(
    store_dir: Path,
    text: str,
    *,
    kind: str,
    disposition: str | None = None,
    provenance: dict[str, Any] | None = None,
) -> DialogueTurn:
    return append_dialogue_turn(
        store_dir,
        DialogueTurn(
            at=_utc_now(),
            speaker="subject",
            text=text.strip(),
            kind=kind,
            disposition=disposition,
            provenance=provenance or {},
        ),
    )


def last_outbound_turn(store_dir: Path) -> DialogueTurn | None:
    for turn in reversed(load_dialogue_turns(store_dir)):
        if turn.speaker == "subject":
            return turn
    return None


def recent_dialogue(store_dir: Path, *, limit: int = 8) -> list[DialogueTurn]:
    return load_dialogue_turns(store_dir)[-max(1, limit) :]
