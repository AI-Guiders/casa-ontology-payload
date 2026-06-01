#!/usr/bin/env python3
"""Ingest episodic policy (CASA-ADR-0023 §4) — hippo is queue, not corpus mirror."""

from __future__ import annotations

from typing import Any, Literal

IngestEpisodicMode = Literal["off", "surprise_only", "full"]

_VALID: frozenset[str] = frozenset({"off", "surprise_only", "full"})


def resolve_ingest_episodic_mode(state: dict) -> IngestEpisodicMode:
    store = state.get("store")
    if isinstance(store, dict):
        raw = store.get("ingest_episodic_mode")
        if isinstance(raw, str) and raw in _VALID:
            return raw  # type: ignore[return-value]
    return "full"


def should_record_ingest_episode(
    state: dict,
    *,
    correction_kind: str | None = None,
    scene: str | None = None,
    surprise: bool = False,
) -> bool:
    """Whether listen/ingest may append a surface episode to hippo."""
    mode = resolve_ingest_episodic_mode(state)
    if mode == "full":
        return True
    if mode == "off":
        return False
    if surprise:
        return True
    if correction_kind:
        return True
    sc = (scene or "").strip().lower()
    if sc in ("predict_surprise", "teacher_correct", "teacher", "correction"):
        return True
    return False


def set_ingest_episodic_mode(state: dict, mode: IngestEpisodicMode) -> None:
    if mode not in _VALID:
        raise ValueError(f"ingest_episodic_mode must be one of {sorted(_VALID)}")
    state.setdefault("store", {})["ingest_episodic_mode"] = mode


def record_listen_surface(
    state: dict,
    *,
    cue: str,
    surface_attempt: str,
    correct: str,
    lattice_id: str,
    concept_id: str | None = None,
    bundle: dict | None = None,
    scene: str = "listen",
    correction_kind: str | None = None,
    force: bool = False,
    **kwargs: Any,
) -> dict | None:
    """Lab listen hook: respect ``ingest_episodic_mode`` unless ``force``."""
    from casa.prisms.memory.memory_prisms import append_episode

    if not force and not should_record_ingest_episode(
        state,
        correction_kind=correction_kind,
        scene=scene,
    ):
        return None
    return append_episode(
        state,
        cue=cue,
        surface_attempt=surface_attempt,
        correct=correct,
        lattice_id=lattice_id,
        concept_id=concept_id,
        bundle=bundle,
        scene=scene,
        correction_kind=correction_kind,
        episode_source="ingest",
        **kwargs,
    )
