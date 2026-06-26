#!/usr/bin/env python3
"""Encode wav window → auditory lattice; hippo episode bound to scene_id."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from casa.domain.auditory_imprint import AuditoryImprintPlan
from casa.domain.auditory_tract import LATTICE_AUDIO_BINAURAL, LATTICE_AUDIO_SPECTRUM
from casa.domain.listen_moment_policy import is_multi_speaker
from casa.domain.prism_ids import PRISM_AUDITORY
from casa.domain.prism_wire import prism_block
from casa.prisms.auditory.bootstrap import ensure_prism_auditory
from casa.prisms.memory.memory_prisms import append_episode, ensure_prisms, persist_content_lattices
from casa.prisms.visual.imprint import _apply_placements
from casa.sensory.codecs.cochlear_stub import encode_cochlear_stub
from casa.sensory.load_wav import load_wav_slice

_AUDITORY_LATTICES = (LATTICE_AUDIO_SPECTRUM, LATTICE_AUDIO_BINAURAL)


def _audio_concept_id(window_id: str) -> str:
    return f"aud.window.{window_id}"


def _slug(speaker: str) -> str:
    return "".join(ch if ch.isalnum() or ch in "._-" else "_" for ch in speaker.strip().lower()) or "unknown"


def _voice_token(speaker: str) -> str:
    return f"T:voice.{_slug(speaker)}"


def apply_auditory_imprint(state: dict, plan: AuditoryImprintPlan) -> dict[str, Any]:
    ensure_prism_auditory(state)
    block = prism_block(state, PRISM_AUDITORY)
    lats = block.setdefault("lattices", {})
    per_lattice: dict[str, int] = {}
    for lid, placements in plan.placements_by_lattice.items():
        lat = lats.get(lid)
        if not lat:
            continue
        w = int(lat.get("width") or plan.grid_size)
        h = int(lat.get("height") or plan.grid_size)
        per_lattice[lid] = _apply_placements(lat, placements, width=w, height=h)
    persist_content_lattices(state, {lid: lats[lid] for lid in per_lattice if lid in lats})
    state["field_version"] = int(state.get("field_version") or 0) + 1
    return {
        "window_id": plan.window_id,
        "scene_id": plan.scene_id,
        "audio_hash": plan.audio_hash[:16],
        "codec_id": plan.codec_id,
        "duration_ms": plan.duration_ms,
        "placements": per_lattice,
    }


def imprint_auditory_window(
    state: dict,
    wav_path: Path | str,
    *,
    scene_id: str,
    window_id: str | None = None,
    t0_sec: float | None = None,
    t1_sec: float | None = None,
    speaker: str | None = None,
    speakers: list[str] | None = None,
    record_episode: bool = True,
) -> dict[str, Any]:
    """Encode wav slice → auditory lattices + episodic audio/voice links."""
    state = ensure_prisms(state)
    wid = window_id or scene_id
    wav = load_wav_slice(wav_path, t0_sec=t0_sec, t1_sec=t1_sec)
    plan = encode_cochlear_stub(wav, window_id=wid, scene_id=scene_id)
    applied = apply_auditory_imprint(state, plan)
    ep = None
    if record_episode:
        aud_cid = _audio_concept_id(wid)
        links: list[dict[str, Any]] = [
            {"src": aud_cid, "relation": "imprint", "dst": LATTICE_AUDIO_SPECTRUM},
            {"src": f"T:audio.{scene_id}", "relation": "heard_in", "dst": f"scene.{scene_id}"},
        ]
        if LATTICE_AUDIO_BINAURAL in (plan.placements_by_lattice or {}):
            links.append(
                {"src": aud_cid, "relation": "binaural", "dst": LATTICE_AUDIO_BINAURAL}
            )
        spk = list(speakers or [])
        if speaker and speaker.lower() not in [s.lower() for s in spk]:
            spk.insert(0, speaker)
        if is_multi_speaker(spk):
            links.append(
                {
                    "src": f"T:dialogue.{scene_id}",
                    "relation": "turn_in",
                    "dst": f"scene.{scene_id}",
                }
            )
            for sp in spk:
                links.append(
                    {
                        "src": _voice_token(sp),
                        "relation": "interlocutor_of",
                        "dst": f"T:dialogue.{scene_id}",
                    }
                )
        elif speaker:
            links.append(
                {
                    "src": _voice_token(speaker),
                    "relation": "speaker_of",
                    "dst": f"scene.{scene_id}",
                }
            )
        ep = append_episode(
            state,
            cue=f"audio:{scene_id}",
            surface_attempt="",
            correct=plan.audio_hash[:48],
            lattice_id=LATTICE_AUDIO_SPECTRUM,
            concept_id=aud_cid,
            scene=scene_id,
            links=links,
            episode_source="ingest",
        )
    return {
        **applied,
        "episode_id": ep.get("id") if ep else None,
        "speaker": speaker,
        "speakers": speakers,
    }


def auditory_tokens_on_field(state: dict, scene_id: str) -> list[str]:
    """Tokens on auditory lattices (spectrum + binaural) for diagnostics."""
    ensure_prism_auditory(state)
    block = prism_block(state, PRISM_AUDITORY)
    lats = block.get("lattices") or {}
    needle = f"A:scene:{scene_id}"
    found: list[str] = []
    for lid in _AUDITORY_LATTICES:
        lat = lats.get(lid) or {}
        for cell in lat.get("cells") or []:
            for tok in cell:
                if tok == needle or tok.startswith("A:"):
                    found.append(tok)
    return list(dict.fromkeys(found))
