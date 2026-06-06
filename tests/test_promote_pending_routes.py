#!/usr/bin/env python3
"""Bootstrap route promote after probe mastery streak."""

from __future__ import annotations

from casa.domain.emergent_promote import (
    promote_from_probe_report,
    promote_pending_bootstrap_routes,
    promote_routes_from_probe_report,
)
from casa.domain.routing import ROUTE_KIND_APPLICABILITY, ROUTE_KIND_CAPABILITY, Router
from casa.prisms.memory.memory_prisms import ensure_prisms


def test_promote_pending_after_streak():
    state = ensure_prisms({"schema_version": "multi_prism_v1", "field_version": 0, "store": {"store_id": "von-neumann"}})
    report = {
        "probe": "phrase-agent-store",
        "phrase_know": True,
        "verdict": "phrase_know",
        "total_words": 3,
        "know_words": 3,
        "events": [{"phrase_know": True, "total_words": 3, "know_words": 3}],
    }
    promote_from_probe_report(state, report, tick=1)
    pending = promote_pending_bootstrap_routes(state, min_mastery_streak=2)
    assert not pending or all(not r.promoted for r in pending)

    promote_from_probe_report(state, report, tick=2)
    rows = promote_pending_bootstrap_routes(state, min_mastery_streak=2)
    assert rows and rows[0].promoted

    router = Router.bind(state)
    caps = router.routes(route_kind=ROUTE_KIND_CAPABILITY)
    apps = router.routes(route_kind=ROUTE_KIND_APPLICABILITY)
    assert any(r.target_skill == "skill.read.phrase" for r in caps)
    assert any(r.target_plan.startswith("plan.phrase_compose_") for r in apps)

    # idempotent
    again = promote_routes_from_probe_report(state, report, min_mastery_streak=2)
    assert again.skipped
