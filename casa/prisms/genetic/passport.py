#!/usr/bin/env python3
"""Genome passport — species_id, hash, allele summary for REPL / MEMORY.md (ADR-0062 P6f)."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from casa.prisms.genetic.zone import genetic_constant, species_passport

GENOME_PASSPORT_JSON = "genome_passport.json"


def _forgetting_priming_alpha(state: dict) -> float:
    for path in (
        "forgetting_genotype.implicit.priming_alpha_retain",
        "forgetting.implicit.priming_alpha_retain",
    ):
        val = genetic_constant(state, path)
        if val is not None:
            return float(val)
    try:
        from casa.prisms.memory.forgetting import priming_alpha_retain

        return float(priming_alpha_retain(state))
    except ImportError:
        return 0.2


def genome_allele_summary(state: dict) -> dict[str, Any]:
    """Resolved allele snapshot — effective wired constants (P6c inventory)."""
    summary: dict[str, Any] = {
        "forgetting_genotype": {
            "priming_alpha_retain": _forgetting_priming_alpha(state),
            "canon_susceptibility": genetic_constant(state, "forgetting_genotype.canon_susceptibility", 0.0),
        },
        "metabolic_policy": {},
        "signal_decay": {},
        "promote_canon": {},
        "ema_limits": {},
        "zone_proportions": {},
        "surprise_gains": {},
    }
    try:
        from casa.prisms.metabolic.zone import metabolic_policy

        mp = metabolic_policy(state)
        summary["metabolic_policy"] = {
            "sleep_threshold": mp.get("sleep_threshold"),
            "atp_per_tick_base": mp.get("atp_per_tick_base"),
            "cost_surprise": mp.get("cost_surprise"),
            "recovery_per_idle_tick": mp.get("recovery_per_idle_tick"),
        }
    except ImportError:
        pass
    try:
        from casa.prisms.memory.wm.policy import get_wm_policy

        summary["signal_decay"]["wm_theta_decay"] = get_wm_policy(state).get("theta_decay")
    except ImportError:
        pass
    try:
        from casa.prisms.memory.intent.policy import get_intent_policy

        summary["signal_decay"]["intent_theta_decay"] = get_intent_policy(state).get("theta_decay")
    except ImportError:
        pass
    for group, prefix in (
        ("promote_canon", "promote_canon"),
        ("ema_limits", "ema_limits"),
        ("zone_proportions", "zone_proportions"),
        ("surprise_gains", "surprise_gains"),
    ):
        block = genetic_constant(state, prefix, {})
        if isinstance(block, dict):
            summary[group] = {k: block[k] for k in sorted(block.keys())}
    return summary


def genome_passport(state: dict) -> dict[str, Any]:
    """Full passport for AiNet / MEMORY.md / REPL (P6f)."""
    base = species_passport(state)
    alleles = genome_allele_summary(state)
    gh = str(base.get("genome_hash") or "")
    return {
        **base,
        "genome_hash_short": gh[:12] if gh else "",
        "allele_summary": alleles,
        "wired_groups": sorted(alleles.keys()),
    }


def format_genome_passport_repl(state: dict) -> str:
    """One-screen REPL digest."""
    doc = genome_passport(state)
    lines = [
        f"species_id: {doc.get('species_id')}",
        f"genome_hash: {doc.get('genome_hash_short')}… valid={doc.get('valid')} sealed@{doc.get('sealed_at_tick')}",
    ]
    alleles = doc.get("allele_summary") or {}
    fg = alleles.get("forgetting_genotype") or {}
    if fg:
        lines.append(
            f"forgetting: α_retain={fg.get('priming_alpha_retain')} "
            f"canon_susceptibility={fg.get('canon_susceptibility')}"
        )
    mp = alleles.get("metabolic_policy") or {}
    if mp:
        lines.append(
            f"metabolic: sleep_threshold={mp.get('sleep_threshold')} "
            f"cost_surprise={mp.get('cost_surprise')}"
        )
    sd = alleles.get("signal_decay") or {}
    if sd:
        lines.append(
            f"signal_decay: wm_θ={sd.get('wm_theta_decay')} intent_θ={sd.get('intent_theta_decay')}"
        )
    pc = alleles.get("promote_canon") or {}
    if pc.get("sandbox_theta") is not None:
        lines.append(f"promote_canon: sandbox_theta={pc.get('sandbox_theta')}")
    return "\n".join(lines)


def write_genome_passport_artifact(store_dir, state: dict) -> dict[str, Any]:
    """Persist genome_passport.json under agent store."""
    doc = genome_passport(state)
    path = Path(store_dir) / GENOME_PASSPORT_JSON
    path.write_text(json.dumps(doc, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    doc["path"] = str(path)
    return doc
