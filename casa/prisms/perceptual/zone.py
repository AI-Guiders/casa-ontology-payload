#!/usr/bin/env python3
"""Perceptual Zone — sensory gate / thalamic input (ADR-0063)."""

from __future__ import annotations

import re
from typing import TYPE_CHECKING, Any

from casa.prisms.intelligence.model import DEFAULT_ZONE_POLICY, intelligence_root
from casa.prisms.intelligence.zone_spawner import spawn_zone_lattices_from_config

if TYPE_CHECKING:
    from casa.prisms.control.sn_cen_runtime import FieldDigest

CORE_LATTICE = "agent-percept-core"
SANDBOX_LATTICE = "agent-percept-sandbox"
CORE_PREFIX = "agent.percept."

DEFAULT_FAN_OUT: dict[str, dict[str, float]] = {
    "text_stream": {"linguistic": 0.85, "social": 0.15},
    "keyboard": {"linguistic": 0.7, "executive": 0.3},
    "visual_stream": {"spatial": 0.55, "executive": 0.45},
    "listen_stream": {"linguistic": 0.5, "emotional": 0.35, "executive": 0.15},
    "motor_stream": {"executive": 0.55, "linguistic": 0.25, "emotional": 0.2},
}


def _stream_slug(value: str) -> str:
    slug = re.sub(r"[^\w\u0400-\u04FF]+", "_", (value or "").strip().lower())
    return (slug[:48] or "stream").strip("_")


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


def _combined_stream_fan_out(state: dict, *, coactive: bool) -> dict[str, float]:
    zone = ensure_perceptual_zone(state)
    weights = dict(zone.get("fan_out_weights") or DEFAULT_FAN_OUT)
    vis_row = dict(weights.get("visual_stream") or DEFAULT_FAN_OUT["visual_stream"])
    listen_row = dict(weights.get("listen_stream") or DEFAULT_FAN_OUT["listen_stream"])
    combined: dict[str, float] = {}
    for key in set(vis_row) | set(listen_row):
        combined[key] = max(float(vis_row.get(key, 0.0)), float(listen_row.get(key, 0.0)))
    if coactive:
        combined["executive"] = max(combined.get("executive", 0.0), 0.5)
    return combined


def perceptual_prepare_life_sensory(
    state: dict,
    *,
    stream_id: str,
    seq: int,
    t_rel: float,
    visual_delta: float,
    audio_active: bool,
    audio_placements: int = 0,
    visual_motion: bool | None = None,
    aud_window_id: str | None = None,
    vis_frame_id: str | None = None,
) -> dict[str, Any]:
    """Joint visual+listen percept on one life tick (ADR-0063 + listen/visual streams)."""
    zone = ensure_perceptual_zone(state)
    active = set(zone.get("active_modalities") or [])
    active.update(["visual_stream", "listen_stream"])
    zone["active_modalities"] = sorted(active)

    motion = visual_motion if visual_motion is not None else float(visual_delta) >= 0.08
    tokens: list[str] = [
        "percept.life.tick",
        f"percept.stream.{_stream_slug(stream_id)}",
        f"percept.stream.seq.{int(seq)}",
        f"percept.time.{float(t_rel):.2f}",
    ]
    if motion:
        tokens.append("percept.vis.motion")
    if visual_delta >= 0.2:
        tokens.append("percept.vis.delta.high")
    elif visual_delta > 0:
        tokens.append("percept.vis.delta.low")
    if audio_active:
        tokens.append("percept.listen.active")
    if audio_placements > 0:
        tokens.append("percept.listen.energy")
    coactive = bool(motion and audio_active)
    if coactive:
        tokens.append("percept.av.coactive")

    concept_hints = list(tokens)
    if motion:
        concept_hints.append("vis.motion.scene")
    if audio_active:
        concept_hints.append("aud.event.cartoon")
    wid = str(aud_window_id or "").strip()
    fid = str(vis_frame_id or "").strip()
    if coactive and wid and fid:
        from casa.prisms.visual.bridge_math import vis_frame_concept_id

        concept_hints.append(f"aud.window.{wid}")
        concept_hints.append(vis_frame_concept_id(fid))

    rep = {
        "tokens": tokens,
        "concept_hints": list(dict.fromkeys(concept_hints)),
        "fan_out": _combined_stream_fan_out(state, coactive=coactive),
        "modalities": ["visual_stream", "listen_stream"],
        "visual_delta": float(visual_delta),
        "audio_active": bool(audio_active),
        "coactive": coactive,
        "aud_window_id": wid or None,
        "vis_frame_id": fid or None,
    }
    state["_perceptual_turn"] = rep
    zone["last_tokens"] = tokens[-16:]
    return rep


def _merge_percept_turns(base: dict[str, Any], extra: dict[str, Any]) -> dict[str, Any]:
    """Combine sensory + text percept blocks on one macro tick."""
    tokens = list(dict.fromkeys(list(base.get("tokens") or []) + list(extra.get("tokens") or [])))
    hints = list(dict.fromkeys(list(base.get("concept_hints") or []) + list(extra.get("concept_hints") or [])))
    modalities = sorted(
        set(list(base.get("modalities") or []) + list(extra.get("modalities") or []) + ["text_stream"])
    )
    fan_base = dict(base.get("fan_out") or {})
    fan_extra = dict(extra.get("fan_out") or {})
    fan_out = {
        key: max(float(fan_base.get(key, 0.0)), float(fan_extra.get(key, 0.0)))
        for key in set(fan_base) | set(fan_extra)
    }
    merged = dict(base)
    merged.update(
        {
            "tokens": tokens,
            "concept_hints": hints,
            "modalities": modalities,
            "fan_out": fan_out,
            "text_active": True,
        }
    )
    return merged


def perceptual_merge_motor_self_echo(
    state: dict,
    *,
    plan_id: str,
    units: list[str] | tuple[str, ...] | None = None,
    base: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Fold self-listen motor echo into current tick percept (ADR-0082)."""
    from casa.domain.motor_speech_plan import motor_plan_concept_id, self_listen_aud_concept_id

    zone = ensure_perceptual_zone(state)
    active = set(zone.get("active_modalities") or [])
    active.add("motor_stream")
    zone["active_modalities"] = sorted(active)

    pid = str(plan_id or "").strip()
    tokens = [
        "percept.self.speech",
        "percept.motor.active",
        f"percept.motor.plan.{pid}",
    ]
    hints = list(tokens)
    if pid:
        hints.append(motor_plan_concept_id(pid))
        hints.append(self_listen_aud_concept_id(pid))
    for unit in units or ():
        u = str(unit).strip()
        if u:
            hints.append(u)

    block = base if isinstance(base, dict) else state.get("_perceptual_turn")
    base_block = dict(block) if isinstance(block, dict) else {}
    rep = _merge_percept_turns(
        base_block,
        {
            "tokens": tokens,
            "concept_hints": hints,
            "fan_out": dict(DEFAULT_FAN_OUT.get("motor_stream") or {}),
            "modalities": ["motor_stream"],
            "motor_active": True,
            "motor_plan_id": pid or None,
            "aud_self_window_id": f"self-{pid}" if pid else None,
        },
    )
    rep["motor_active"] = True
    rep["motor_plan_id"] = pid or None
    rep["aud_self_window_id"] = f"self-{pid}" if pid else None
    state["_perceptual_turn"] = rep
    zone["last_tokens"] = list(rep.get("tokens") or [])[-16:]
    return rep


def _merge_motor_echo_from_state(state: dict, rep: dict[str, Any]) -> dict[str, Any]:
    echo = state.get("_motor_self_listen")
    if not isinstance(echo, dict):
        return rep
    pid = str(echo.get("plan_id") or "").strip()
    if not pid:
        return rep
    return perceptual_merge_motor_self_echo(
        state,
        plan_id=pid,
        units=list(echo.get("units") or []),
        base=rep,
    )


def perceptual_prepare_life_tick(
    state: dict,
    *,
    user_query: str | None = None,
    preserve_existing: bool = True,
) -> dict[str, Any] | None:
    """T=0 percept gate — all active channels on this macro tick (ADR-0063)."""
    zone = ensure_perceptual_zone(state)
    existing = state.get("_perceptual_turn") if preserve_existing else None
    existing_block = existing if isinstance(existing, dict) else None

    q = (user_query or "").strip()
    text_rep: dict[str, Any] | None = None
    if q:
        tokens = perceptual_ingest(q, modality="text_stream")
        text_rep = perceptual_fan_out(state, tokens, modality="text_stream")
        active = set(zone.get("active_modalities") or [])
        active.add("text_stream")
        zone["active_modalities"] = sorted(active)

    if text_rep and existing_block:
        rep = _merge_percept_turns(existing_block, text_rep)
    elif text_rep:
        rep = {**text_rep, "modalities": ["text_stream"], "text_active": True}
    elif existing_block:
        rep = dict(existing_block)
    else:
        rep = None

    if rep is not None:
        rep = _merge_motor_echo_from_state(state, rep)
        state["_perceptual_turn"] = rep
        zone["last_tokens"] = list(rep.get("tokens") or [])[-16:]
        return rep

    echo_only = _merge_motor_echo_from_state(state, {})
    if echo_only.get("motor_active"):
        state["_perceptual_turn"] = echo_only
        zone["last_tokens"] = list(echo_only.get("tokens") or [])[-16:]
        return echo_only
    return None


def merge_digest_with_perceptual_turn(digest: "FieldDigest", state: dict) -> "FieldDigest":
    """Fold joint percept hints into SN/CEN digest for the current macro tick."""
    hints = perceptual_turn_hints(state)
    if not hints:
        return digest
    from casa.prisms.control.sn_cen_runtime import FieldDigest

    concept_ids = list(dict.fromkeys(list(digest.concept_ids) + hints))
    concept_scores = dict(digest.concept_scores)
    for hint in hints:
        concept_scores.setdefault(hint, 0.85)
    present = list(dict.fromkeys(list(digest.present_tokens) + hints))
    return FieldDigest(
        concept_ids=concept_ids,
        edge_tokens=list(digest.edge_tokens),
        concept_scores=concept_scores,
        digest_vector=list(digest.digest_vector),
        modules_active=list(digest.modules_active),
        present_tokens=present,
    )


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
