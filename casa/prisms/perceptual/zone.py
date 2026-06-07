#!/usr/bin/env python3
"""Perceptual Zone — sensory gate / thalamic input (ADR-0063)."""

from __future__ import annotations

import re
from typing import Any

from casa.prisms.intelligence.model import DEFAULT_ZONE_POLICY, intelligence_root
from casa.prisms.intelligence.zone_spawner import spawn_zone_lattices_from_config

CORE_LATTICE = "agent-percept-core"
SANDBOX_LATTICE = "agent-percept-sandbox"
CORE_PREFIX = "agent.percept."

DEFAULT_FAN_OUT: dict[str, dict[str, float]] = {
    "text_stream": {"linguistic": 0.85, "social": 0.15},
    "keyboard": {"linguistic": 0.7, "executive": 0.3},
}


def ensure_perceptual_zone(state: dict) -> dict[str, Any]:
    root = intelligence_root(state)
    zone = root.setdefault("perceptual", {})
    zone.setdefault("active_modalities", ["text_stream", "keyboard"])
    zone.setdefault("last_tokens", [])
    zone.setdefault("noise_floor", 0.0)
    zone.setdefault("fan_out_weights", dict(DEFAULT_FAN_OUT))
    zone.setdefault("core_lattice_id", CORE_LATTICE)
    zone.setdefault("sandbox_lattice_id", SANDBOX_LATTICE)
    zone.setdefault("zone_policy", dict(DEFAULT_ZONE_POLICY))
    return zone


def spawn_perceptual_zone(state: dict, *, config: dict[str, Any] | None = None) -> dict[str, Any]:
    cfg = config or {}
    zone = ensure_perceptual_zone(state)
    rep = spawn_zone_lattices_from_config(
        state,
        zone,
        cfg,
        default_core=CORE_LATTICE,
        default_sandbox=SANDBOX_LATTICE,
        default_core_prefix=CORE_PREFIX,
        default_sandbox_prefix="agent.percept.lab.",
    )
    if cfg.get("active_modalities"):
        zone["active_modalities"] = list(cfg["active_modalities"])
    if isinstance(cfg.get("fan_out"), dict):
        zone["fan_out_weights"] = {**DEFAULT_FAN_OUT, **cfg["fan_out"]}
    return rep


def perceptual_ingest(raw: str, *, modality: str = "text_stream") -> list[str]:
    text = (raw or "").strip()
    if not text:
        return ["percept.empty"]
    tokens = [f"percept.{modality}.line"]
    words = re.findall(r"[\w\u0400-\u04FF]+", text.lower())
    for word in words[:24]:
        tokens.append(f"percept.{modality}.word.{word}")
    if modality == "text_stream" and any(ch in text for ch in "+−-×*/÷="):
        tokens.append("percept.text.math_cue")
    return list(dict.fromkeys(tokens))


def perceptual_fan_out(state: dict, tokens: list[str], *, modality: str = "text_stream") -> dict[str, Any]:
    zone = ensure_perceptual_zone(state)
    weights = dict(zone.get("fan_out_weights") or DEFAULT_FAN_OUT)
    row = dict(weights.get(modality) or DEFAULT_FAN_OUT.get("text_stream") or {})
    concept_hints: list[str] = list(tokens)
    for token in tokens:
        if token.startswith("percept.text.word.") or token.startswith("percept.text_stream.word."):
            lemma = token.rsplit(".", 1)[-1]
            concept_hints.append(f"lang.word.{lemma}")
        if token.endswith(".math_cue"):
            concept_hints.append("math.surface.arithmetic")
    if float(row.get("social", 0.0)) > 0.4 and any("lang.word.привет" in h for h in concept_hints):
        concept_hints.append("ru.dialog.affect")
    return {
        "tokens": tokens,
        "concept_hints": list(dict.fromkeys(concept_hints)),
        "fan_out": row,
    }


def perceptual_prepare_turn(state: dict, raw: str, *, modality: str = "text_stream") -> dict[str, Any]:
    zone = ensure_perceptual_zone(state)
    if modality not in (zone.get("active_modalities") or []):
        modality = "text_stream"
    tokens = perceptual_ingest(raw, modality=modality)
    rep = perceptual_fan_out(state, tokens, modality=modality)
    zone["last_tokens"] = tokens[-16:]
    state["_perceptual_turn"] = rep
    return rep


def perceptual_turn_hints(state: dict | None) -> list[str]:
    if not state:
        return []
    block = state.get("_perceptual_turn")
    if not isinstance(block, dict):
        return []
    hints = block.get("concept_hints")
    return list(hints) if isinstance(hints, list) else []
