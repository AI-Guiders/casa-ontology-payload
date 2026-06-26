#!/usr/bin/env python3
"""Field-native motor unit selection — not text→TTS (ADR-0082)."""

from __future__ import annotations

import hashlib
import re
from typing import Any

_MOTOR_UNIT_PREFIXES = (
    "A:",
    "aud.window.",
    "motor.unit.",
    "motor.plan.",
    "motor.lex.",
    "lang.word.",
)


def _is_motor_unit_token(token: str) -> bool:
    tok = str(token or "").strip()
    return bool(tok) and tok.startswith(_MOTOR_UNIT_PREFIXES)


def _listen_scenes_from_state(state: dict) -> list[str]:
    scenes: list[str] = []
    block = state.get("_perceptual_turn")
    if isinstance(block, dict):
        stream = str(block.get("stream_id") or block.get("listen_stream_id") or "").strip()
        if stream:
            scenes.append(stream)
        wid = str(block.get("aud_window_id") or "").strip()
        if wid and "-" in wid:
            scenes.append(wid.rsplit("-", 1)[0])
    echo = state.get("_motor_self_listen")
    if isinstance(echo, dict):
        scene = str(echo.get("scene_id") or "").strip()
        if scene:
            scenes.append(scene)
    return list(dict.fromkeys(scenes))


def _all_auditory_lattice_tokens(state: dict) -> list[str]:
    from casa.domain.auditory_tract import LATTICE_AUDIO_BINAURAL, LATTICE_AUDIO_SPECTRUM
    from casa.domain.prism_ids import PRISM_AUDITORY
    from casa.domain.prism_wire import prism_block
    from casa.prisms.auditory.bootstrap import ensure_prism_auditory

    ensure_prism_auditory(state)
    lats = (prism_block(state, PRISM_AUDITORY).get("lattices") or {})
    found: list[str] = []
    for lid in (LATTICE_AUDIO_SPECTRUM, LATTICE_AUDIO_BINAURAL):
        lat = lats.get(lid) or {}
        for cell in lat.get("cells") or []:
            if not isinstance(cell, list):
                continue
            for tok in cell:
                if isinstance(tok, str) and tok.startswith("A:"):
                    found.append(tok)
    return list(dict.fromkeys(found))


def collect_field_motor_candidates(state: dict, concept_hints: list[str] | None = None) -> list[str]:
    """Motor plan material must already live on field or percept hints — no Python menu."""
    hints = [h for h in (concept_hints or []) if _is_motor_unit_token(str(h))]
    scenes = _listen_scenes_from_state(state)
    auditory: list[str] = []
    if scenes:
        from casa.prisms.auditory.imprint import auditory_tokens_on_field

        for scene_id in scenes:
            auditory.extend(auditory_tokens_on_field(state, scene_id))
    if not auditory:
        auditory = _all_auditory_lattice_tokens(state)
    prior = state.get("_motor_self_listen")
    if isinstance(prior, dict):
        auditory.extend(str(u) for u in (prior.get("units") or []) if _is_motor_unit_token(str(u)))
    merged = list(dict.fromkeys(hints + auditory))
    return [t for t in merged if _is_motor_unit_token(t)]


def _select_from_field(
    candidates: list[str],
    *,
    tick: int,
    intent: str,
    salt: str,
    cap: int,
) -> list[str]:
    if not candidates:
        return []
    ordered = sorted(candidates)
    seed = f"{tick}:{intent}:{salt}"
    digest = hashlib.sha256(seed.encode()).hexdigest()
    picked: list[str] = []
    idx = 0
    while len(picked) < cap and idx < len(digest):
        slot = int(digest[idx : idx + 2], 16) % len(ordered)
        token = ordered[slot]
        if token not in picked:
            picked.append(token)
        idx += 2
    return picked


def compose_motor_units(
    state: dict,
    *,
    tick: int,
    intent: str = "babble",
    reply_text: str | None = None,
    concept_hints: list[str] | None = None,
    max_units: int = 4,
) -> list[str]:
    """Pick motor units from field evidence; empty list = no phonation material."""
    cap = max(1, min(int(max_units), 8))
    hints = list(concept_hints or [])
    block = state.get("motor_speech")
    salt = ""
    if isinstance(block, dict):
        cap = max(1, min(int(block.get("max_units") or cap), 8))
        salt = str(block.get("babble_salt") or "")

    candidates = collect_field_motor_candidates(state, hints)

    if intent == "echo_field":
        picked = [h for h in hints if _is_motor_unit_token(h)][:cap]
        return picked or _select_from_field(candidates, tick=tick, intent=intent, salt=salt, cap=cap)

    if intent == "parallel_compose":
        bind_hints = [h for h in hints if h.startswith(("lang.word.", "A:ph:", "motor.unit.", "motor.lex."))][:cap]
        if bind_hints:
            return bind_hints
        if (reply_text or "").strip():
            words = re.findall(r"[\w\u0400-\u04FF]+", (reply_text or "").lower())
            reply_hints = [f"lang.word.{w}" for w in words if f"lang.word.{w}" in set(candidates)]
            if reply_hints:
                return reply_hints[:cap]
        return _select_from_field(candidates, tick=tick, intent=intent, salt=salt, cap=cap)

    return _select_from_field(candidates, tick=tick, intent=intent, salt=salt, cap=cap)
