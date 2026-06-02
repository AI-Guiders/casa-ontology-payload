"""Ingest runtime state reuse."""

from __future__ import annotations

from casa.prisms.memory.memory_prisms import ensure_prisms
from casa.cli.ingest_state import resolve_ingest_state


def test_resolve_ingest_state_reuses_memory() -> None:
    state = ensure_prisms({})
    state["field_version"] = 42
    out = resolve_ingest_state(__import__("pathlib").Path("/tmp/x"), state)
    assert out is state
    assert out["store"]["store_id"] == "x"
    assert out["field_version"] == 42
