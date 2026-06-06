#!/usr/bin/env python3
"""Router boot probe — RouteContext smoke on wake (ADR-0041 / ADR-0035)."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any

from casa.domain.prism_ids import PRISM_LANG_RU
from casa.domain.routing import (
    ROUTE_KIND_CAPABILITY,
    ROUTE_KIND_KNOWLEDGE,
    RouteContext,
    Router,
)
from casa.prisms.memory.lexicon_shard import is_l2_word_lattice
from casa.prisms.memory.memory_prisms import memory_lattices
from casa.prisms.shared.store_layout import ltm_root


@dataclass(frozen=True, slots=True)
class BootProbe:
    name: str
    ctx: RouteContext
    required: bool = True
    expect_prism: str = ""
    expect_skill: str = ""
    expect_resolved: bool = True


def _default_probes(store_id: str) -> tuple[BootProbe, ...]:
    return (
        BootProbe(
            name="knowledge_t9_ru",
            ctx=RouteContext(route_kind=ROUTE_KIND_KNOWLEDGE, modality="t9", locale="ru", store_id=store_id),
            expect_prism="",
        ),
        BootProbe(
            name="knowledge_vis_word_novel",
            ctx=RouteContext(
                route_kind=ROUTE_KIND_KNOWLEDGE,
                modality="vis",
                locale="ru",
                surface_class="word",
                novel="true",
                store_id=store_id,
            ),
            required=False,
            expect_resolved=True,
        ),
        BootProbe(
            name="capability_analytic_read",
            ctx=RouteContext(
                route_kind=ROUTE_KIND_CAPABILITY,
                modality="vis",
                locale="ru",
                surface_class="word",
                novel="true",
                store_id=store_id,
            ),
            required=False,
            expect_skill="skill.read.analytic",
        ),
        BootProbe(
            name="capability_math_count",
            ctx=RouteContext(
                route_kind=ROUTE_KIND_CAPABILITY,
                modality="schema",
                locale="ru",
                surface_class="drawing",
                store_id=store_id,
            ),
            required=False,
            expect_skill="skill.math.count",
        ),
    )


def _l2_sample_ok(state: dict, store_dir: Path) -> dict[str, Any]:
    from casa.domain.store_recovery import load_ltm_pack_manifest

    ltm = ltm_root(store_dir)
    manifest = load_ltm_pack_manifest(ltm, store_dir=store_dir)
    lattices_manifest = manifest.get("lattices") or {}
    if not any(str(k).startswith("L2_word") for k in lattices_manifest):
        return {"ok": True, "skipped": True, "reason": "no_l2_in_manifest"}

    lattices = memory_lattices(state)
    shard_ids = [k for k in lattices if is_l2_word_lattice(k)]
    if shard_ids:
        sample = sorted(shard_ids)[0]
        cells = (lattices.get(sample) or {}).get("cells")
        return {"ok": True, "sample": sample, "via": "state", "has_cells": bool(cells)}

    ltm = ltm_root(store_dir)
    for i in range(64):
        lid = f"L2_word_{i:02d}"
        path = ltm / f"{lid}.ltm"
        if path.is_file() and path.stat().st_size > 64:
            return {"ok": True, "sample": lid, "via": "ltm_file", "bytes": path.stat().st_size}
    return {"ok": False, "sample": None, "via": "missing"}


def _run_probe(router: Router, probe: BootProbe) -> dict[str, Any]:
    if probe.ctx.route_kind == ROUTE_KIND_KNOWLEDGE:
        tgt = router.resolve(probe.ctx)
    else:
        tgt = router.resolve_layer(probe.ctx)
    if tgt is None:
        ok = not probe.expect_resolved
        return {
            "name": probe.name,
            "required": probe.required,
            "ok": ok if probe.required else True,
            "skipped": not probe.required and probe.expect_resolved,
            "reason": "unresolved",
        }

    matched = tgt.matched or {}
    if matched.get("source") == "unresolved":
        ok = not probe.expect_resolved
        return {
            "name": probe.name,
            "required": probe.required,
            "ok": ok if probe.required else True,
            "skipped": not probe.required,
            "reason": "unresolved",
        }

    ok = True
    reasons: list[str] = []
    if not tgt.prism_id and not tgt.target_skill and not tgt.target_plan:
        ok = not probe.expect_resolved
    if probe.expect_prism and tgt.prism_id != probe.expect_prism:
        # knowledge resolve may fallback to memory — accept logical match
        logical = str(matched.get("logical_prism") or "")
        if logical != probe.expect_prism and tgt.prism_id != probe.expect_prism:
            ok = False
            reasons.append(f"prism:{tgt.prism_id}!={probe.expect_prism}")
    if probe.expect_skill and tgt.target_skill != probe.expect_skill:
        ok = False
        reasons.append(f"skill:{tgt.target_skill}!={probe.expect_skill}")

    return {
        "name": probe.name,
        "required": probe.required,
        "ok": ok,
        "target": tgt.to_dict(),
        "reasons": reasons,
    }


def run_router_boot_probe(
    state: dict,
    *,
    store_dir: Path | None = None,
    store_id: str = "",
) -> dict[str, Any]:
    store_id = store_id or str((state.get("store") or {}).get("store_id") or "")
    router = Router.bind(state)
    probes = [_run_probe(router, p) for p in _default_probes(store_id)]

    l2: dict[str, Any] | None = None
    if store_dir is not None:
        from casa.prisms.shared.runtime_checkpoint import ltm_pack_ready

        if ltm_pack_ready(store_dir):
            l2 = _l2_sample_ok(state, store_dir.resolve())
            if l2 and not l2.get("ok"):
                probes.append(
                    {
                        "name": "l2_word_shard_sample",
                        "required": True,
                        "ok": False,
                        "reason": "no_l2_shard",
                    }
                )

    required_fail = [p for p in probes if p.get("required") and not p.get("ok")]
    optional_fail = [p for p in probes if not p.get("required") and not p.get("ok") and not p.get("skipped")]

    return {
        "schema_version": 1,
        "tool": "router_boot_probe",
        "ok": len(required_fail) == 0 and (l2 is None or l2.get("ok", True)),
        "probes": probes,
        "l2_sample": l2,
        "required_failures": [p.get("name") for p in required_fail],
        "optional_failures": [p.get("name") for p in optional_fail],
    }
