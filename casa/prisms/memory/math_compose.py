#!/usr/bin/env python3
"""Compose quantities: dim.count + entity/category homogeneity and category lift."""

from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Any, Literal

Aggregate = Literal["entity", "category"]

QTY_RE = re.compile(r"^M:qty:(\d+)×(entity|category|unit):([a-z0-9_]+)$")


@dataclass(frozen=True)
class Quantity:
    n: int
    sort: str  # entity | category | unit
    name: str  # cow, livestock, m

    @property
    def token(self) -> str:
        return f"M:qty:{self.n}×{self.sort}:{self.name}"

    @property
    def concept_id(self) -> str:
        if self.sort == "entity":
            return f"math.entity.{self.name}"
        if self.sort == "category":
            return f"math.category.{self.name}"
        return f"math.unit.{self.name}"


def parse_qty(token: str) -> Quantity:
    m = QTY_RE.match(str(token).strip())
    if not m:
        raise ValueError(f"bad qty token: {token!r}")
    return Quantity(int(m.group(1)), m.group(2), m.group(3))


def format_qty(q: Quantity) -> str:
    return q.token


def _is_a_map(edges: list[dict[str, Any]]) -> dict[str, set[str]]:
    out: dict[str, set[str]] = {}
    for e in edges:
        if str(e.get("relation")) != "is_a":
            continue
        src, dst = str(e.get("src") or ""), str(e.get("dst") or "")
        if src and dst:
            out.setdefault(src, set()).add(dst)
    return out


def entity_lift_categories(entity_concept: str, is_a: dict[str, set[str]]) -> set[str]:
    return is_a.get(entity_concept, set())


def add_quantities(
    left: Quantity,
    right: Quantity,
    *,
    aggregate: Aggregate,
    lift_category: str | None = None,
    graph_edges: list[dict[str, Any]] | None = None,
) -> dict[str, Any]:
    """Add two qty; entity-level requires same entity; category-level lifts via is_a."""
    if left.n < 0 or right.n < 0:
        raise ValueError("negative qty")

    is_a = _is_a_map(graph_edges or [])

    if aggregate == "entity":
        if left.sort != "entity" or right.sort != "entity":
            return {"ok": False, "error": "heterogeneous_sort", "detail": "entity aggregate needs entity×entity"}
        if left.name != right.name:
            return {"ok": False, "error": "heterogeneous_sort", "detail": f"{left.name}!={right.name}"}
        out = Quantity(left.n + right.n, "entity", left.name)
        return {"ok": True, "result": out, "token": out.token, "concept_id": out.concept_id}

    if aggregate == "category":
        if not lift_category:
            return {"ok": False, "error": "missing_lift_category"}
        cat_suffix = lift_category.removeprefix("math.category.")
        allowed: set[str] = set()
        for q in (left, right):
            if q.sort == "category":
                if q.concept_id != lift_category:
                    return {"ok": False, "error": "heterogeneous_sort", "detail": "category mismatch"}
                allowed.add(lift_category)
            elif q.sort == "entity":
                parents = entity_lift_categories(q.concept_id, is_a)
                if lift_category not in parents:
                    return {
                        "ok": False,
                        "error": "heterogeneous_sort",
                        "detail": f"{q.concept_id} not under {lift_category}",
                    }
                allowed.add(lift_category)
            else:
                return {"ok": False, "error": "heterogeneous_sort", "detail": f"bad sort {q.sort}"}
        if len(allowed) != 1:
            return {"ok": False, "error": "heterogeneous_sort"}
        out = Quantity(left.n + right.n, "category", cat_suffix)
        return {
            "ok": True,
            "result": out,
            "token": out.token,
            "concept_id": out.concept_id,
            "decomposes_to": [left.token, right.token],
        }

    return {"ok": False, "error": "unknown_aggregate"}


def run_compose_scenario(bundle: dict, scenario: dict) -> dict[str, Any]:
    left = parse_qty(str(scenario["left"]))
    right = parse_qty(str(scenario["right"]))
    aggregate = str(scenario.get("aggregate") or "entity")
    rep = add_quantities(
        left,
        right,
        aggregate=aggregate,  # type: ignore[arg-type]
        lift_category=scenario.get("lift_category"),
        graph_edges=(bundle.get("graph") or {}).get("edges") or [],
    )
    row: dict[str, Any] = {
        "id": scenario.get("id"),
        "left": left.token,
        "right": right.token,
        "aggregate": aggregate,
        "lift_category": scenario.get("lift_category"),
        "got": rep.get("token"),
        "error": rep.get("error"),
        "detail": rep.get("detail"),
    }
    if scenario.get("expect_error"):
        row["ok"] = not rep.get("ok") and rep.get("error") == scenario["expect_error"]
        row["expect_error"] = scenario["expect_error"]
    else:
        expect = str(scenario.get("expect") or "")
        row["expect"] = expect
        row["ok"] = bool(rep.get("ok")) and rep.get("token") == expect
    if scenario.get("decomposes_to") and rep.get("ok"):
        row["decomposes_ok"] = rep.get("decomposes_to") == scenario["decomposes_to"]
        row["ok"] = row["ok"] and row["decomposes_ok"]
    return row


def run_compose_bench(bundle: dict) -> dict[str, Any]:
    scenarios = bundle.get("compose_scenarios") or []
    rows = [run_compose_scenario(bundle, s) for s in scenarios]
    passed = sum(1 for r in rows if r.get("ok"))
    return {
        "bench": "math_compose",
        "passed": passed,
        "total": len(rows),
        "pass_rate": round(passed / max(1, len(rows)), 3),
        "items": rows,
    }
