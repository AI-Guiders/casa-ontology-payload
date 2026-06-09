#!/usr/bin/env python3
"""Memory forgetting hooks — speed-1 priming @ tick (ADR-0070 P15b / ADR-0068 P12d)."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from casa.prisms.memory.zone import ensure_memory_zone

DEFAULT_PRIMING_ALPHA = 0.2
PRIMING_FLOOR = 0.01
PRIMING_BOOST_SCALE = 10

DEFAULT_EPISODIC_BETA = 0.08
DEFAULT_EPISODIC_FADE_EVERY_N = 8
DEFAULT_EPISODIC_SALIENCE_FLOOR = 0.05
DEFAULT_HIPPO_CAP = 240
DEFAULT_DIALOGUE_RING_CAP = 256
DEFAULT_NCA_EROSION_EPSILON = 0.02


def _priming_block(state: dict) -> dict[str, Any]:
    zone = ensure_memory_zone(state)
    implicit = zone.setdefault("implicit", {})
    prim = implicit.setdefault("priming", {})
    if not isinstance(prim.get("cells"), dict):
        prim["cells"] = {}
    prim.setdefault("alpha_retain", DEFAULT_PRIMING_ALPHA)
    prim.setdefault("bind_decay_halflife_ticks", 6)
    return prim


def _genetic_priming_alpha(state: dict) -> float | None:
    try:
        from casa.prisms.genetic.zone import genetic_constant

        for path in (
            "forgetting_genotype.implicit.priming_alpha_retain",
            "forgetting.implicit.priming_alpha_retain",
        ):
            val = genetic_constant(state, path)
            if val is not None:
                return float(val)
    except (ImportError, AttributeError, TypeError, ValueError):
        pass
    return None


def priming_alpha_retain(state: dict) -> float:
    """α for speed-1 decay — genome prior via genetic_constant (P6c)."""
    prim = (ensure_memory_zone(state).get("implicit") or {}).get("priming") or {}
    raw = prim.get("alpha_retain")
    if raw is not None:
        return float(raw)
    genetic = _genetic_priming_alpha(state)
    if genetic is not None:
        return genetic
    return DEFAULT_PRIMING_ALPHA


def memory_priming_decay(state: dict, *, tick: int | None = None) -> dict[str, Any]:
    """Speed-1: activation[t+1] = α × activation[t] on implicit priming cells."""
    prim = _priming_block(state)
    alpha = priming_alpha_retain(state)
    prim["alpha_retain"] = alpha
    cells: dict[str, float] = {str(k): float(v) for k, v in (prim.get("cells") or {}).items() if k}
    decayed = 0
    kept: dict[str, float] = {}
    for cid, act in cells.items():
        new_act = act * alpha
        if new_act >= PRIMING_FLOOR:
            kept[cid] = round(new_act, 6)
        else:
            decayed += 1
    prim["cells"] = kept
    fv = int(tick if tick is not None else state.get("field_version") or 0)
    prim["last_decay_tick"] = fv
    prim["decayed_last"] = decayed
    prim["active_count"] = len(kept)
    rep = {
        "alpha_retain": alpha,
        "decayed": decayed,
        "active_count": len(kept),
        "tick": fv,
    }
    forget = state.setdefault("forgetting", {})
    forget["speed1_last"] = rep
    return rep


def memory_priming_touch(
    state: dict,
    concept_ids: list[str],
    *,
    tick: int | None = None,
    weight: float = 1.0,
) -> dict[str, Any]:
    """Refresh priming activation after bind (re-bind resets flash)."""
    prim = _priming_block(state)
    cells: dict[str, float] = dict(prim.get("cells") or {})
    touched = 0
    w = max(0.0, float(weight))
    for raw in concept_ids:
        cid = str(raw or "").strip()
        if not cid:
            continue
        cells[cid] = max(float(cells.get(cid) or 0), w)
        touched += 1
    prim["cells"] = cells
    fv = int(tick if tick is not None else state.get("field_version") or 0)
    prim["last_activation_tick"] = fv
    prim["active_count"] = len(cells)
    return {"touched": touched, "active_count": len(cells), "tick": fv}


def memory_priming_boost_block_scores(state: dict, blocks: list[dict[str, Any]]) -> int:
    """Apply residual priming as bind score boost (implicit flash → explicit bind)."""
    prim = (ensure_memory_zone(state).get("implicit") or {}).get("priming") or {}
    cells = prim.get("cells") or {}
    if not cells:
        return 0
    boosted = 0
    for row in blocks:
        if not isinstance(row, dict):
            continue
        cid = str(row.get("concept_id") or "")
        act = float(cells.get(cid) or 0)
        if act < PRIMING_FLOOR:
            continue
        base = int(row.get("score") or 0)
        row["score"] = base + int(act * PRIMING_BOOST_SCALE)
        row["priming_boost"] = round(act, 4)
        boosted += 1
    return boosted


def memory_implicit_gains(state: dict, *, tract: str = "general") -> dict[str, Any]:
    """Tract-scoped scales for priming / procedural bind (P12d)."""
    tract_key = str(tract or "general").strip().lower()
    alpha = priming_alpha_retain(state)
    gains: dict[str, Any] = {
        "tract": tract_key,
        "priming_alpha_retain": alpha,
        "priming_scale": 1.0,
        "procedural_scale": 1.0,
    }
    if tract_key in ("math", "schema", "predict"):
        gains["procedural_scale"] = 1.15
    if tract_key in ("social", "discuss", "recall", "journal", "general"):
        gains["priming_scale"] = 1.2
    if tract_key == "math":
        gains["priming_scale"] = 0.9
    meta = state.setdefault("meta", {})
    meta["memory_implicit_gains"] = gains
    return gains


def memory_priming_record_bind(
    state: dict,
    blocks: list[dict[str, Any]],
    *,
    tick: int | None = None,
    top_n: int = 12,
    min_score: int = 5,
) -> dict[str, Any]:
    """After bind: boost from prior priming, then touch winners for next tick."""
    boosted = memory_priming_boost_block_scores(state, blocks)
    ranked = sorted(
        [b for b in blocks if isinstance(b, dict) and int(b.get("score") or 0) >= min_score],
        key=lambda r: int(r.get("score") or 0),
        reverse=True,
    )
    cids = [str(r.get("concept_id") or "") for r in ranked[:top_n] if r.get("concept_id")]
    touch = memory_priming_touch(state, cids, tick=tick, weight=1.0)
    return {"boosted": boosted, **touch}


def _pathology_mode(state: dict) -> str:
    zone = ensure_memory_zone(state)
    forget_cfg = zone.get("forgetting") if isinstance(zone.get("forgetting"), dict) else {}
    raw = str(forget_cfg.get("pathology_mode") or "none").strip().lower()
    return raw or "none"


def _genetic_forgetting_float(state: dict, path: str, default: float) -> float:
    try:
        from casa.prisms.genetic.zone import genetic_constant

        val = genetic_constant(state, path)
        if val is not None:
            return float(val)
    except (ImportError, AttributeError, TypeError, ValueError):
        pass
    return default


def _genetic_forgetting_int(state: dict, path: str, default: int) -> int:
    return int(_genetic_forgetting_float(state, path, float(default)))


def episodic_beta_fade(state: dict) -> float:
    zone = ensure_memory_zone(state)
    fg = (zone.get("forgetting") or {}) if isinstance(zone.get("forgetting"), dict) else {}
    raw = fg.get("episodic_beta_fade")
    if raw is not None:
        return float(raw)
    return _genetic_forgetting_float(state, "forgetting_genotype.episodic.beta_fade", DEFAULT_EPISODIC_BETA)


def episodic_fade_every_n_ticks(state: dict) -> int:
    zone = ensure_memory_zone(state)
    fg = (zone.get("forgetting") or {}) if isinstance(zone.get("forgetting"), dict) else {}
    raw = fg.get("episodic_fade_every_n_ticks")
    if raw is not None:
        return max(1, int(raw))
    return max(1, _genetic_forgetting_int(state, "forgetting_genotype.episodic.fade_every_n_ticks", DEFAULT_EPISODIC_FADE_EVERY_N))


def episodic_salience_floor(state: dict) -> float:
    zone = ensure_memory_zone(state)
    fg = (zone.get("forgetting") or {}) if isinstance(zone.get("forgetting"), dict) else {}
    raw = fg.get("episodic_salience_floor")
    if raw is not None:
        return float(raw)
    return _genetic_forgetting_float(
        state,
        "forgetting_genotype.episodic.salience_floor",
        DEFAULT_EPISODIC_SALIENCE_FLOOR,
    )


def episodic_hippo_cap(state: dict) -> int:
    zone = ensure_memory_zone(state)
    fg = (zone.get("forgetting") or {}) if isinstance(zone.get("forgetting"), dict) else {}
    raw = fg.get("hippo_cap")
    if raw is not None:
        return max(1, int(raw))
    return max(1, _genetic_forgetting_int(state, "forgetting_genotype.episodic.hippo_cap", DEFAULT_HIPPO_CAP))


def dialogue_ring_cap(state: dict) -> int:
    zone = ensure_memory_zone(state)
    fg = (zone.get("forgetting") or {}) if isinstance(zone.get("forgetting"), dict) else {}
    raw = fg.get("dialogue_ring_cap")
    if raw is not None:
        return max(1, int(raw))
    return max(1, _genetic_forgetting_int(state, "forgetting_genotype.episodic.dialogue_ring_cap", DEFAULT_DIALOGUE_RING_CAP))


def _metabolic_load_factor(state: dict) -> float:
    meta = state.get("meta") or {}
    for key in ("metabolic_last", "metabolic_tick", "metabolic"):
        block = meta.get(key)
        if not isinstance(block, dict):
            continue
        for fat_key in ("fatigue", "fatigue_ema", "load"):
            raw = block.get(fat_key)
            if raw is not None:
                return min(1.0, max(0.0, float(raw)))
    zone = ensure_memory_zone(state)
    fg = zone.get("forgetting") if isinstance(zone.get("forgetting"), dict) else {}
    override = fg.get("metabolic_load_override")
    if override is not None:
        return min(1.0, max(0.0, float(override)))
    return 0.0


def _episode_salience(ep: dict[str, Any]) -> float:
    raw = ep.get("salience")
    if raw is None:
        return 1.0
    return max(0.0, float(raw))


def _hub_cooccurrence(state: dict, concept_id: str | None) -> float:
    cid = str(concept_id or "").strip()
    if not cid:
        return 0.0
    prim = (ensure_memory_zone(state).get("implicit") or {}).get("priming") or {}
    act = float((prim.get("cells") or {}).get(cid) or 0)
    if act < PRIMING_FLOOR:
        return 0.0
    return min(1.0, act)


def forget_should_episodic_fade(state: dict, *, tick: int | None = None) -> bool:
    """Speed-2: fade every N ticks or when metabolic load is elevated."""
    n = episodic_fade_every_n_ticks(state)
    fv = int(tick if tick is not None else state.get("field_version") or 0)
    if n > 0 and fv % n == 0:
        return True
    return _metabolic_load_factor(state) >= 0.5


def forget_episodic_fade(state: dict, *, tick: int | None = None) -> dict[str, Any]:
    """Speed-2: salience decay on hippo episodes (ADR-0070 P15c)."""
    from casa.domain.prism_wire import prism_hippo

    beta = episodic_beta_fade(state)
    load = _metabolic_load_factor(state)
    floor = episodic_salience_floor(state)
    multiplier = 1.0 + load
    hippo = prism_hippo(state)
    episodes = list(hippo.get("episodes") or [])
    faded = 0
    below_floor = 0
    fv = int(tick if tick is not None else state.get("field_version") or 0)
    for ep in episodes:
        if not isinstance(ep, dict) or ep.get("consolidated"):
            continue
        hub_boost = _hub_cooccurrence(state, str(ep.get("concept_id") or "") or None)
        decay = beta * multiplier * (1.0 - hub_boost)
        new_sal = max(0.0, _episode_salience(ep) - decay)
        ep["salience"] = round(new_sal, 6)
        faded += 1
        if new_sal < floor:
            below_floor += 1
    hippo["episodes"] = episodes
    rep = {
        "beta_fade": beta,
        "metabolic_load": round(load, 4),
        "multiplier": round(multiplier, 4),
        "faded": faded,
        "below_floor": below_floor,
        "salience_floor": floor,
        "tick": fv,
    }
    forget = state.setdefault("forgetting", {})
    forget["speed2_last"] = rep
    return rep


def forget_episodic_trim(state: dict) -> dict[str, Any]:
    """Post-sleep: drop low-salience / consolidated episodes; cap hippo queue (P15e)."""
    from casa.domain.prism_wire import prism_hippo

    floor = episodic_salience_floor(state)
    cap = episodic_hippo_cap(state)
    hippo = prism_hippo(state)
    episodes = list(hippo.get("episodes") or [])
    before = len(episodes)
    kept: list[dict[str, Any]] = []
    trimmed_low = 0
    trimmed_consolidated = 0
    for ep in episodes:
        if not isinstance(ep, dict):
            continue
        if ep.get("consolidated"):
            trimmed_consolidated += 1
            continue
        if _episode_salience(ep) < floor:
            trimmed_low += 1
            continue
        kept.append(ep)
    overflow = max(0, len(kept) - cap)
    if overflow:
        kept.sort(key=_episode_salience, reverse=True)
        kept = kept[:cap]
    hippo["episodes"] = kept
    rep = {
        "before": before,
        "after": len(kept),
        "trimmed_low_salience": trimmed_low,
        "trimmed_consolidated": trimmed_consolidated,
        "trimmed_overflow": overflow,
        "hippo_cap": cap,
        "salience_floor": floor,
    }
    forget = state.setdefault("forgetting", {})
    forget["episodic_trim_last"] = rep
    return rep


def trim_dialogue_ring(store_dir, state: dict | None = None) -> dict[str, Any]:
    """Cap session dialogue ring (ADR-0070 speed-2 post-sleep)."""
    from casa.domain.dialogue_turn import DIALOGUE_RING_MAX, load_dialogue_turns
    from casa.prisms.control.fpn_state import read_session_meta, write_session_meta

    cap = dialogue_ring_cap(state) if state is not None else DIALOGUE_RING_MAX
    store_dir = Path(store_dir).resolve()
    turns = load_dialogue_turns(store_dir)
    before = len(turns)
    if before <= cap:
        return {"before": before, "after": before, "trimmed": 0, "cap": cap}
    meta = read_session_meta(store_dir)
    trimmed_turns = turns[-cap:]
    meta["dialogue_turns"] = [t.to_dict() for t in trimmed_turns]
    write_session_meta(store_dir, meta)
    return {"before": before, "after": len(trimmed_turns), "trimmed": before - len(trimmed_turns), "cap": cap}


def nca_erosion_pass(state: dict) -> dict[str, Any]:
    """Speed-3 @ sleep: concept edge decay; immutable lattices skipped (P15d)."""
    from casa.prisms.memory.agent_prism import agent_lattices
    from casa.prisms.memory.write_gate import is_immutable_lattice

    immutable_skipped = sorted(
        lid for lid in agent_lattices(state) if is_immutable_lattice(state, str(lid))
    )
    concept_rep: dict[str, Any] = {"skipped": True, "reason": "import"}
    try:
        from casa.prisms.memory.concept_index import apply_concept_nca_edge_decay

        concept_rep = apply_concept_nca_edge_decay(state)
    except ImportError:
        pass
    epsilon = _genetic_forgetting_float(
        state,
        "forgetting_genotype.nca.erosion_epsilon",
        DEFAULT_NCA_EROSION_EPSILON,
    )
    rep = {
        "epsilon": epsilon,
        "immutable_lattices_skipped": immutable_skipped,
        "immutable_skipped_count": len(immutable_skipped),
        "concept_core": concept_rep,
        "mutable_lattice_count": len(agent_lattices(state)) - len(immutable_skipped),
    }
    forget = state.setdefault("forgetting", {})
    forget["nca_erosion_last"] = rep
    return rep


def probe_episodic_fade_runs(state: dict) -> dict[str, Any]:
    """Speed-2 hook should be configured and salience floor sane (P15f)."""
    n = episodic_fade_every_n_ticks(state)
    beta = episodic_beta_fade(state)
    floor = episodic_salience_floor(state)
    return {
        "pass": n >= 1 and 0.0 < beta < 1.0 and 0.0 < floor < 1.0,
        "fade_every_n_ticks": n,
        "beta_fade": beta,
        "salience_floor": floor,
    }


def probe_episodic_trim_cap(state: dict) -> dict[str, Any]:
    """Hippo queue must respect cap after trim (P15f)."""
    from casa.domain.prism_wire import prism_hippo

    cap = episodic_hippo_cap(state)
    count = len(prism_hippo(state).get("episodes") or [])
    return {
        "pass": count <= cap,
        "hippo_episode_count": count,
        "hippo_cap": cap,
    }


def count_canon_immutable_touched(state: dict) -> int:
    """Merged sleep items or blocked hot writes that touched immutable lattices."""
    from casa.prisms.memory.write_gate import is_immutable_lattice

    touches = 0
    last = (state.get("consolidation") or {}).get("last_sleep") or {}
    for item in last.get("items") or []:
        if not isinstance(item, dict):
            continue
        lid = str(item.get("lattice_id") or "")
        if lid and is_immutable_lattice(state, lid):
            touches += 1
    meta = state.get("meta") or {}
    touches += int(meta.get("immutable_write_blocked") or 0)
    return touches


def probe_canon_immutable_touched(state: dict) -> dict[str, Any]:
    """Honesty probe — immutable canon must not be mutated @ pathology_mode=none (P15f)."""
    touched = count_canon_immutable_touched(state)
    pathology = _pathology_mode(state)
    allowed = pathology != "none"
    return {
        "pass": allowed or touched == 0,
        "canon_immutable_touched": touched,
        "pathology_mode": pathology,
    }


def probe_priming_alpha(state: dict, *, tolerance: float = 0.08) -> dict[str, Any]:
    """Speed-1 α should track genome prior (default allele) within band (P15f)."""
    alpha = priming_alpha_retain(state)
    expected = _genetic_priming_alpha(state) or DEFAULT_PRIMING_ALPHA
    delta = abs(alpha - expected)
    alive = 0.0 < alpha < 1.0
    return {
        "pass": alive and delta <= tolerance,
        "alpha_retain": alpha,
        "expected_prior": expected,
        "delta": round(delta, 6),
    }


def forget_snapshot(state: dict) -> dict[str, Any]:
    """REPL digest: speed-1 counters + immutable touch audit (ADR-0070 P15f)."""
    zone = ensure_memory_zone(state)
    prim = (zone.get("implicit") or {}).get("priming") or {}
    forget = state.get("forgetting") or {}
    cons = state.get("consolidation") or {}
    last_sleep = cons.get("last_sleep") or {}
    consolidate = zone.get("consolidate") or {}
    touched = count_canon_immutable_touched(state)
    pathology = _pathology_mode(state)
    return {
        "speed1_last": forget.get("speed1_last"),
        "speed2_last": forget.get("speed2_last"),
        "episodic_trim_last": forget.get("episodic_trim_last"),
        "nca_erosion_last": forget.get("nca_erosion_last"),
        "priming_active_count": int(prim.get("active_count") or 0),
        "alpha_retain": priming_alpha_retain(state),
        "episodic_beta_fade": episodic_beta_fade(state),
        "hippo_cap": episodic_hippo_cap(state),
        "last_sleep": {
            "merged": int(last_sleep.get("merged") or 0),
            "pending": int(last_sleep.get("pending") or 0),
            "immutable_skipped_count": len(last_sleep.get("immutable_skipped") or []),
        },
        "consolidate_last_report": consolidate.get("last_report"),
        "canon_immutable_touched": touched,
        "pathology_mode": pathology,
    }


def build_forget_honesty_report(state: dict) -> dict[str, Any]:
    """Pre-registered forgetting honesty battery (ADR-0070 §Honesty gate)."""
    from casa.prisms.memory.consolidate_report import (
        probe_math_habit_implicit,
        probe_post_sleep_hippo_pending_down,
        probe_recall_uses_episodic_scope,
    )

    probes = {
        "canon_immutable_touched": probe_canon_immutable_touched(state),
        "priming_alpha": probe_priming_alpha(state),
        "episodic_fade": probe_episodic_fade_runs(state),
        "episodic_trim_cap": probe_episodic_trim_cap(state),
        "recall_episodic": probe_recall_uses_episodic_scope(state),
        "math_implicit": probe_math_habit_implicit(state),
        "post_sleep": probe_post_sleep_hippo_pending_down(state),
    }
    snapshot = forget_snapshot(state)
    gate_pass = all(bool(p.get("pass")) for p in probes.values())
    report = {
        "schema_version": 1,
        "snapshot": snapshot,
        "probes": probes,
        "gate_pass": gate_pass,
    }
    forget = state.setdefault("forgetting", {})
    forget["honesty_last"] = report
    return report


def write_forget_honesty_report(store_dir, report: dict[str, Any]) -> Path:
    """Persist forget_honesty_report.json under agent store (P15f artifact)."""
    from casa.prisms.memory.consolidate_report import FORGET_HONESTY_JSON

    path = Path(store_dir) / FORGET_HONESTY_JSON
    path.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return path


def finalize_memory_sleep_reports(
    state: dict,
    sleep_report: dict[str, Any],
    *,
    store_dir=None,
) -> dict[str, Any]:
    """P12e consolidate mirror + P15f honesty report after run_sleep."""
    from casa.prisms.memory.consolidate_report import memory_consolidate_snapshot

    nca_rep = nca_erosion_pass(state)
    if nca_rep.get("concept_core"):
        sleep_report["concept_nca"] = nca_rep["concept_core"]
    trim_rep = forget_episodic_trim(state)
    sleep_report["episodic_trim"] = trim_rep
    dialogue_trim: dict[str, Any] = {}
    if store_dir is not None:
        dialogue_trim = trim_dialogue_ring(store_dir, state)
        sleep_report["dialogue_ring_trim"] = dialogue_trim
    digest = memory_consolidate_snapshot(state, sleep_report)
    honesty = build_forget_honesty_report(state)
    sleep_report["forget_honesty"] = {
        "gate_pass": honesty["gate_pass"],
        "canon_immutable_touched": honesty["probes"]["canon_immutable_touched"]["canon_immutable_touched"],
        "pathology_mode": honesty["snapshot"]["pathology_mode"],
    }
    if store_dir is not None:
        write_forget_honesty_report(store_dir, honesty)
    return {
        "consolidate": digest,
        "honesty": honesty,
        "nca_erosion": nca_rep,
        "episodic_trim": trim_rep,
        "dialogue_ring_trim": dialogue_trim,
    }
