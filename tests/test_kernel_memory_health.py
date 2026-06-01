"""Kernel memory health — multi-aspect scan and maintain."""

from __future__ import annotations

from casa.prisms.memory.kernel_memory_health import (
    maintain_memory_kernel,
    memory_kernel_checks,
    scan_memory_kernel_health,
)
from casa.prisms.memory.memory_prisms import ensure_prisms
from casa.prisms.memory.prism_spawn import ensure_default_router_and_hot


def test_kernel_scan_has_all_aspects():
    state = ensure_prisms({"schema_version": "multi_prism_v1", "field_version": 0})
    ensure_default_router_and_hot(state)
    rep = scan_memory_kernel_health(state)
    ids = set(rep["aspects"])
    assert "hot_context" in ids
    assert "ltm_layout" in ids
    assert "router" in ids
    assert "hippo" in ids


def test_kernel_checks_tag_aspect():
    state = ensure_prisms({"schema_version": "multi_prism_v1", "field_version": 0})
    ensure_default_router_and_hot(state)
    checks = memory_kernel_checks(state)
    assert all("aspect" in c for c in checks)
    assert any(c["id"] == "router_resolves" for c in checks)


def test_maintain_memory_kernel_noop_without_pressure():
    state = ensure_prisms({"schema_version": "multi_prism_v1", "field_version": 0})
    ensure_default_router_and_hot(state)
    rep = maintain_memory_kernel(state, repair=True)
    assert rep["status"] in ("noop", "repaired")
