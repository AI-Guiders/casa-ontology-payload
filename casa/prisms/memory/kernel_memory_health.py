#!/usr/bin/env python3
"""Kernel memory health — scan, checks, and in-process maintenance (extensible aspects).

Vocab/u16 and L2 sharding are one aspect (`ltm_layout`). Hot-context prune, router/kind
integrity, hippo budget are separate aspects. Sleep and health call the same kernel API.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any, Protocol

from casa.prisms.memory.memory_prisms import content_prism_lattices, ensure_prisms, hippo_episodes
from casa.prisms.memory.prism_hot_context import hot_edges, prune_hot_context
from casa.prisms.memory.prism_router import RouteContext, resolve_route
from casa.prisms.shared.prism_state import (
    PRISM_KIND_HOT_CONTEXT,
    PRISM_KIND_ROUTER,
    PRISM_MEMORY,
    active_prism_id,
    prism_kind,
    prisms,
)

# Re-export aspect implementation for tests and thin wrappers.
from casa.prisms.memory.ltm_vocab_health import (  # noqa: E402
    maintain_ltm_layout,
    scan_ltm_layout,
    ltm_layout_checks,
)

HOT_SOFT_EDGE_COUNT = 1024
HOT_HARD_EDGE_COUNT = 4096
HIPPO_EPISODE_SOFT_CAP = 512
SLEEP_HOT_PRUNE_MAX = 2048


@dataclass(frozen=True)
class MaintainContext:
    """Where maintenance runs (thresholds may differ)."""

    phase: str = "sleep"  # sleep | health | manual


class MemoryKernelAspect(Protocol):
    """One inspectable/repairable dimension of prism memory."""

    id: str

    def scan(self, state: dict) -> dict[str, Any]: ...

    def checks(self, state: dict, scan: dict[str, Any] | None = None) -> list[dict[str, Any]]: ...

    def maintain(
        self,
        state: dict,
        store_dir: Path | None,
        *,
        repair: bool,
        ctx: MaintainContext,
        report: dict[str, Any] | None,
    ) -> dict[str, Any] | None: ...


class _HotContextAspect:
    id = "hot_context"

    def scan(self, state: dict) -> dict[str, Any]:
        n = len(hot_edges(state))
        return {
            "edge_count": n,
            "soft": HOT_SOFT_EDGE_COUNT,
            "hard": HOT_HARD_EDGE_COUNT,
            "over_soft": n > HOT_SOFT_EDGE_COUNT,
            "over_hard": n > HOT_HARD_EDGE_COUNT,
        }

    def checks(self, state: dict, scan: dict[str, Any] | None = None) -> list[dict[str, Any]]:
        s = scan or self.scan(state)
        out: list[dict[str, Any]] = [
            {
                "id": "hot_budget",
                "aspect": self.id,
                "ok": not s["over_hard"],
                "detail": s,
            }
        ]
        if s["over_soft"]:
            out.append(
                {
                    "id": "hot_soft_warning",
                    "aspect": self.id,
                    "ok": True,
                    "warn": True,
                    "detail": s,
                }
            )
        return out

    def maintain(
        self,
        state: dict,
        store_dir: Path | None,
        *,
        repair: bool,
        ctx: MaintainContext,
        report: dict[str, Any] | None,
    ) -> dict[str, Any] | None:
        if not repair:
            return None
        s = self.scan(state)
        limit = HOT_HARD_EDGE_COUNT - 1 if ctx.phase == "health" else SLEEP_HOT_PRUNE_MAX - 1
        if s["edge_count"] <= limit:
            return None
        pr = prune_hot_context(state, max_edges=limit)
        rep = {
            "aspect": self.id,
            "status": "pruned",
            "ok": True,
            "before": s,
            "after": self.scan(state),
            "prune_report": pr,
        }
        if report is not None:
            report["hot_prune"] = pr
        return rep


class _RouterAspect:
    id = "router"

    def scan(self, state: dict) -> dict[str, Any]:
        target = resolve_route(state, RouteContext())
        pid = target.prism_id
        lats = content_prism_lattices(state, pid)
        return {
            "target_prism": pid,
            "lattice_count": len(lats),
            "ok": bool(lats) or pid == PRISM_MEMORY,
        }

    def checks(self, state: dict, scan: dict[str, Any] | None = None) -> list[dict[str, Any]]:
        s = scan or self.scan(state)
        return [
            {
                "id": "router_resolves",
                "aspect": self.id,
                "ok": s["ok"],
                "detail": s,
            }
        ]

    def maintain(
        self,
        state: dict,
        store_dir: Path | None,
        *,
        repair: bool,
        ctx: MaintainContext,
        report: dict[str, Any] | None,
    ) -> dict[str, Any] | None:
        return None


class _HippoAspect:
    id = "hippo"

    def __init__(self, cap: int = HIPPO_EPISODE_SOFT_CAP) -> None:
        self.cap = cap

    def scan(self, state: dict) -> dict[str, Any]:
        n = len(hippo_episodes(state))
        return {"episode_count": n, "cap": self.cap, "over_cap": n > self.cap}

    def checks(self, state: dict, scan: dict[str, Any] | None = None) -> list[dict[str, Any]]:
        s = scan or self.scan(state)
        checks = [
            {
                "id": "hippo_cap",
                "aspect": self.id,
                "ok": not s["over_cap"],
                "detail": s,
            }
        ]
        if s["over_cap"]:
            checks.append(
                {
                    "id": "hippo_soft_warning",
                    "aspect": self.id,
                    "ok": True,
                    "warn": True,
                    "detail": {**s, "kernel_op": "kernel.run_sleep_consolidate"},
                }
            )
        return checks

    def maintain(
        self,
        state: dict,
        store_dir: Path | None,
        *,
        repair: bool,
        ctx: MaintainContext,
        report: dict[str, Any] | None,
    ) -> dict[str, Any] | None:
        # Consolidation is run_sleep itself; no separate trim here in v0.
        return None


class _NcaRegistryAspect:
    id = "nca_registry"

    def scan(self, state: dict) -> dict[str, Any]:
        target = resolve_route(state, RouteContext())
        lats = content_prism_lattices(state, target.prism_id)
        nca = state.get("nca") or {}
        models = nca.get("models") if isinstance(nca.get("models"), dict) else {}
        has_models = bool(models) or bool(nca.get("model_path"))
        return {
            "active_prism": active_prism_id(state),
            "model_entries": len(models),
            "has_global_path": bool(nca.get("model_path")),
            "ok": has_models or not lats,
        }

    def checks(self, state: dict, scan: dict[str, Any] | None = None) -> list[dict[str, Any]]:
        s = scan or self.scan(state)
        return [{"id": "nca_registry", "aspect": self.id, "ok": s["ok"], "detail": s}]

    def maintain(
        self,
        state: dict,
        store_dir: Path | None,
        *,
        repair: bool,
        ctx: MaintainContext,
        report: dict[str, Any] | None,
    ) -> dict[str, Any] | None:
        return None


class _KindIntegrityAspect:
    id = "kind_integrity"

    def scan(self, state: dict) -> dict[str, Any]:
        issues: list[str] = []
        for prism_id, block in prisms(state).items():
            if not isinstance(block, dict):
                continue
            kind = prism_kind(state, prism_id)
            if kind == PRISM_KIND_HOT_CONTEXT and block.get("lattices"):
                issues.append(f"{prism_id}: hot_context must not have lattices")
            if kind == PRISM_KIND_ROUTER and block.get("lattices"):
                issues.append(f"{prism_id}: router must not have lattices")
        return {"issues": issues, "ok": not issues}

    def checks(self, state: dict, scan: dict[str, Any] | None = None) -> list[dict[str, Any]]:
        s = scan or self.scan(state)
        return [{"id": "kind_integrity", "aspect": self.id, "ok": s["ok"], "detail": s}]

    def maintain(
        self,
        state: dict,
        store_dir: Path | None,
        *,
        repair: bool,
        ctx: MaintainContext,
        report: dict[str, Any] | None,
    ) -> dict[str, Any] | None:
        return None


class _LtmLayoutAspect:
    id = "ltm_layout"

    def scan(self, state: dict) -> dict[str, Any]:
        return scan_ltm_layout(state)

    def checks(self, state: dict, scan: dict[str, Any] | None = None) -> list[dict[str, Any]]:
        return ltm_layout_checks(state, scan)

    def maintain(
        self,
        state: dict,
        store_dir: Path | None,
        *,
        repair: bool,
        ctx: MaintainContext,
        report: dict[str, Any] | None,
    ) -> dict[str, Any] | None:
        if not repair:
            return None
        return maintain_ltm_layout(state, store_dir, report=report)


def memory_kernel_aspects() -> list[MemoryKernelAspect]:
    return [
        _RouterAspect(),
        _HotContextAspect(),
        _HippoAspect(),
        _NcaRegistryAspect(),
        _KindIntegrityAspect(),
        _LtmLayoutAspect(),
    ]


def kernel_memory_maintain_on_sleep_enabled(state: dict) -> bool:
    store = state.get("store")
    if not isinstance(store, dict):
        return True
    if "kernel_memory_maintain_on_sleep" in store:
        return bool(store["kernel_memory_maintain_on_sleep"])
    if "ltm_vocab_maintain_on_sleep" in store:
        return bool(store["ltm_vocab_maintain_on_sleep"])
    return True


def scan_memory_kernel_health(
    state: dict,
    *,
    aspect_ids: list[str] | None = None,
) -> dict[str, Any]:
    state = ensure_prisms(state)
    aspects = memory_kernel_aspects()
    if aspect_ids is not None:
        want = set(aspect_ids)
        aspects = [a for a in aspects if a.id in want]
    scans: dict[str, Any] = {}
    for a in aspects:
        scans[a.id] = a.scan(state)
    return {"aspects": scans, "field_version": state.get("field_version")}


def memory_kernel_checks(
    state: dict,
    *,
    scans: dict[str, Any] | None = None,
    aspect_ids: list[str] | None = None,
) -> list[dict[str, Any]]:
    state = ensure_prisms(state)
    full = scans or scan_memory_kernel_health(state, aspect_ids=aspect_ids)["aspects"]
    aspects = memory_kernel_aspects()
    if aspect_ids is not None:
        want = set(aspect_ids)
        aspects = [a for a in aspects if a.id in want]
    checks: list[dict[str, Any]] = []
    for a in aspects:
        checks.extend(a.checks(state, full.get(a.id)))
    return checks


def run_memory_kernel_health(
    state: dict,
    *,
    repair: bool = False,
    store_dir: Path | None = None,
    ctx: MaintainContext | None = None,
    aspect_ids: list[str] | None = None,
    hippo_cap: int = HIPPO_EPISODE_SOFT_CAP,
) -> dict[str, Any]:
    """Full kernel health report; optional in-process repair across aspects."""
    state = ensure_prisms(state)
    ctx = ctx or MaintainContext(phase="health" if repair else "manual")
    scans = scan_memory_kernel_health(state, aspect_ids=aspect_ids)
    checks = memory_kernel_checks(state, scans=scans["aspects"], aspect_ids=aspect_ids)

    # Hippo cap override via custom aspect list only in full registry — keep simple:
    if hippo_cap != HIPPO_EPISODE_SOFT_CAP and aspect_ids is None:
        for c in checks:
            if c.get("id") == "hippo_cap":
                n = len(hippo_episodes(state))
                c["ok"] = n <= hippo_cap
                c["detail"]["cap"] = hippo_cap

    ok = all(c.get("ok", True) for c in checks if not c.get("warn"))
    maintained: list[dict[str, Any]] = []
    if repair:
        for a in memory_kernel_aspects():
            if aspect_ids is not None and a.id not in aspect_ids:
                continue
            rep = a.maintain(state, store_dir, repair=True, ctx=ctx, report=None)
            if rep:
                maintained.append(rep)
        checks = memory_kernel_checks(state, aspect_ids=aspect_ids)
        ok = all(c.get("ok", True) for c in checks if not c.get("warn"))

    out: dict[str, Any] = {
        "ok": ok,
        "checks": checks,
        "scans": scans["aspects"],
        "field_version": state.get("field_version"),
    }
    if maintained:
        out["maintained"] = maintained
    layout = scans["aspects"].get("ltm_layout")
    if layout and (layout.get("near_cap") or layout.get("over_cap") or layout.get("needs_l2_remigrate")):
        out["ltm_layout"] = layout
    return out


def maintain_memory_kernel(
    state: dict,
    store_dir: Path | None = None,
    *,
    repair: bool = True,
    ctx: MaintainContext | None = None,
    report: dict[str, Any] | None = None,
    aspect_ids: list[str] | None = None,
) -> dict[str, Any]:
    """Run repair hooks for all aspects (sleep entry point)."""
    state = ensure_prisms(state)
    ctx = ctx or MaintainContext(phase="sleep")
    aspects = memory_kernel_aspects()
    if aspect_ids is not None:
        want = set(aspect_ids)
        aspects = [a for a in aspects if a.id in want]

    before = scan_memory_kernel_health(state, aspect_ids=aspect_ids)
    repaired: list[dict[str, Any]] = []
    for a in aspects:
        if not repair:
            continue
        rep = a.maintain(state, store_dir, repair=True, ctx=ctx, report=report)
        if rep:
            rep.setdefault("aspect", a.id)
            repaired.append(rep)

    after = scan_memory_kernel_health(state, aspect_ids=aspect_ids)
    checks = memory_kernel_checks(state, scans=after["aspects"], aspect_ids=aspect_ids)
    ok = all(c.get("ok", True) for c in checks if not c.get("warn"))

    out: dict[str, Any] = {
        "status": "repaired" if repaired else "noop",
        "ok": ok,
        "before": before["aspects"],
        "after": after["aspects"],
        "repaired": repaired,
        "checks": checks,
    }
    if report is not None:
        report["kernel_memory_maintain"] = out
    return out


# Backward-compatible aliases (vocab-named API → ltm_layout aspect).
def ltm_vocab_shard_health(state: dict) -> dict[str, Any]:
    return scan_ltm_layout(state)


def maintain_ltm_vocab_health(
    state: dict,
    store_dir: Path | None = None,
    **kwargs: Any,
) -> dict[str, Any]:
    return maintain_ltm_layout(state, store_dir, **kwargs)


def ltm_vocab_maintain_on_sleep_enabled(state: dict) -> bool:
    return kernel_memory_maintain_on_sleep_enabled(state)
