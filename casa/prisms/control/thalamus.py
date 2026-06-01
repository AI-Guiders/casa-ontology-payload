#!/usr/bin/env python3
"""Thalamic control prism — relay, arousal, bandwidth (ADR-0024)."""

from __future__ import annotations

from casa._paths import REPO_ROOT, ensure_import_paths

ensure_import_paths()

from typing import Any

from casa.prisms.memory.memory_prisms import ensure_prisms
from casa.prisms.memory.prism_spawn import spawn_prism
from casa.domain.prism_ids import PRISM_CONTROL_THALAMUS
from casa.domain.prism_wire import prism_block, set_active_control_prism

_THALAMUS_STACK = "design/prisms/control/thalamus-stack.json"

_MODE_TO_AROUSAL = {
    "wake": "thal.arousal.high",
    "sleep": "thal.arousal.low",
    "rem": "thal.arousal.rem",
}

_BAND_FOR_MODE = {
    "wake": "thal.band.active",
    "sleep": "thal.band.quiescent",
    "rem": "thal.band.active",
}


def ensure_control_thalamus(state: dict) -> dict[str, Any]:
    """Bootstrap `prism_control_thalamus` with lattices from thalamus-stack.json."""
    state = ensure_prisms(state)
    block = prism_block(state, PRISM_CONTROL_THALAMUS)
    if block.get("lattices"):
        return block
    spawn_prism(
        state,
        PRISM_CONTROL_THALAMUS,
        kind="control",
        stack=_THALAMUS_STACK,
    )
    _seed_thalamus_tokens(state)
    return prism_block(state, PRISM_CONTROL_THALAMUS)


def _seed_thalamus_tokens(state: dict) -> None:
    from casa.prisms.shared.config_io import load_config
    from casa.prisms.control.stack import empty_control_lattice  # type: ignore

    stack = load_config(REPO_ROOT / _THALAMUS_STACK)
    seeds = stack.get("seed_tokens") or {}
    lats = prism_block(state, PRISM_CONTROL_THALAMUS).setdefault("lattices", {})
    for lat in stack.get("lattices") or []:
        lid = str(lat.get("legacy_id") or lat.get("lattice_id") or lat.get("id") or "")
        if not lid or lid in lats:
            continue
        grid = empty_control_lattice(lat)
        role_key = "relay"
        if "arousal" in lid:
            role_key = "arousal"
        elif "band" in lid:
            role_key = "bandwidth"
        for tok in seeds.get(role_key) or []:
            grid["cells"][0] = list(grid["cells"][0]) + [f"T:{tok}"]
        lats[lid] = grid


def thalamus_tick_phase(
    state: dict,
    *,
    modality: str = "segment",
    cue: str = "",
) -> dict[str, Any]:
    """Sync SN mode → thalamic tokens; open relay for modality. Run before resolve_route."""
    ensure_control_thalamus(state)
    sn = state.setdefault("sn", {})
    mode = str(sn.get("mode") or "wake").lower()
    if mode not in _MODE_TO_AROUSAL:
        mode = "wake"
    sn["mode"] = mode

    arousal_tok = _MODE_TO_AROUSAL.get(mode, "thal.arousal.high")
    band_tok = _BAND_FOR_MODE.get(mode, "thal.band.active")

    relay_key = "text"
    mod = (modality or "").lower()
    if mod in ("vis", "image"):
        relay_key = "vis"
    elif mod in ("schema", "math"):
        relay_key = "schema"

    forward = {
        "text": "port.thal.forward.text",
        "vis": "port.thal.forward.vis",
        "schema": "port.thal.forward.schema",
    }
    sn["relay_open"] = [relay_key]
    sn["thalamic_prism"] = PRISM_CONTROL_THALAMUS

    set_active_control_prism(state, PRISM_CONTROL_THALAMUS)

    return {
        "prism_id": PRISM_CONTROL_THALAMUS,
        "mode": mode,
        "arousal": arousal_tok,
        "band": band_tok,
        "relay": forward.get(relay_key, "port.thal.forward.text"),
        "relay_open": list(sn["relay_open"]),
        "cue": (cue or "")[:80],
    }
