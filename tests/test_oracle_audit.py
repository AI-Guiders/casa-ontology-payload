#!/usr/bin/env python3
"""oracle_audit — regression on dialogue hot path."""

from __future__ import annotations

from tools.oracle_audit import audit


def test_hot_path_passes_default_rules() -> None:
    assert audit(strict=False) == []


def test_ack_span_would_fail() -> None:
    from tools import oracle_audit as mod

    rule = next(r for r in mod.RULES if r.rule_id == "no_ack_span")
    assert rule.pattern.search("acknowledgment_span(query, block)")
