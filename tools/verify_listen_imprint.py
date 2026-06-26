#!/usr/bin/env python3
"""Stage 0 gate — sensory listen/imprint (no efferent, words optional).

Default path: wav (+ optional frame) + scene anchor — like pre-literate listening.
Explicit words[] only for reading-lesson bootstrap (--with-words).
"""

from __future__ import annotations

import argparse
import os
import sys
import tempfile
from pathlib import Path
from typing import Any

REPO = Path(__file__).resolve().parents[1]
if str(REPO) not in sys.path:
    sys.path.insert(0, str(REPO))

from casa.cli.ingest_state import resolve_ingest_state
from casa.prisms.memory.listen_moment import listen_moment
from casa.prisms.memory.memory_prisms import ensure_prisms, memory_lattices
from casa.prisms.memory.prism_spawn import spawn_content_lattice
from casa.prisms.shared.store_layout import default_agent_store
from casa.prisms.visual.imprint import scene_visual_token
from casa.sensory.load_wav import write_synthetic_contour_wav
from casa.sensory.sample_ppm import write_synthetic_room_ppm

STAGE_LABEL = "STAGE 0 — sensory listen/imprint"

SCENE: dict[str, Any] = {
    "id": "stage0_masha_moment",
    "speaker": "masha",
}


def _scene_for_probe(*, with_words: bool) -> dict[str, Any]:
    scene = dict(SCENE)
    if with_words:
        scene.update(
            {
                "caption": "Маша сказала",
                "words": ["маша", "сказала"],
                "punctuation": ["."],
            }
        )
    return scene


def _minimal_listen_state() -> dict:
    state = ensure_prisms({"schema_version": "multi_prism_v1", "field_version": 0})
    spawn_content_lattice(state, "prism_memory", "L3_phrase", z_level=3)
    spawn_content_lattice(state, "prism_memory", "L2_word", z_level=2)
    return state


def _assert_l3_ready(state: dict) -> None:
    lattices = memory_lattices(ensure_prisms(state))
    if "L3_phrase" not in lattices:
        raise AssertionError("L3_phrase lattice missing — cannot imprint scene links")


def run_probe(
    *,
    state: dict | None = None,
    isolated: bool = True,
    impulse: bool = False,
    store_dir: Path | None = None,
    wav_path: Path | None = None,
    frame_path: Path | None = None,
    require_audio: bool = True,
    require_visual: bool = False,
    with_words: bool = False,
) -> dict[str, Any]:
    if impulse:
        os.environ["CASA_IMPULSE_TRACE"] = "summary"
    store = store_dir or default_agent_store()
    scene = _scene_for_probe(with_words=with_words)
    if state is None:
        if isolated:
            state = _minimal_listen_state()
        else:
            state = resolve_ingest_state(store, None)
    _assert_l3_ready(state)

    sid = str(scene["id"])
    expected = [str(w).strip().lower() for w in (scene.get("words") or []) if str(w).strip()]
    fv_before = int(state.get("field_version") or 0)

    tmp_wav: tempfile.NamedTemporaryFile[str] | None = None
    audio_path = wav_path
    if require_audio and audio_path is None:
        tmp_wav = tempfile.NamedTemporaryFile(suffix=".wav", delete=False)
        tmp_wav.close()
        audio_path = Path(tmp_wav.name)
        write_synthetic_contour_wav(audio_path)

    tmp_frame: tempfile.NamedTemporaryFile[str] | None = None
    visual_path = frame_path
    if require_visual and visual_path is None:
        tmp_frame = tempfile.NamedTemporaryFile(suffix=".ppm", delete=False)
        tmp_frame.close()
        visual_path = Path(tmp_frame.name)
        write_synthetic_room_ppm(visual_path, width=64, height=48)

    try:
        moment = listen_moment(
            state,
            scene,
            wav_path=audio_path if require_audio else None,
            frame_path=visual_path if require_visual else None,
            copies=3,
        )
    finally:
        if tmp_wav is not None:
            audio_path.unlink(missing_ok=True)
        if tmp_frame is not None:
            visual_path.unlink(missing_ok=True)

    fv_after = int(state.get("field_version") or 0)
    recalled = list(moment.get("recalled_words") or [])
    recalled_words = [str(row.get("word") or "") for row in recalled]
    auditory_tokens = list(moment.get("auditory_tokens") or [])
    visual_tokens = list(moment.get("visual_tokens") or [])
    audio_rep = moment.get("audio") if isinstance(moment.get("audio"), dict) else None
    visual_rep = moment.get("visual") if isinstance(moment.get("visual"), dict) else None
    lexical = moment.get("lexical") if isinstance(moment.get("lexical"), dict) else {}

    errors: list[str] = []
    if fv_after <= fv_before:
        errors.append(f"field_version did not bump: {fv_before} → {fv_after}")
    if lexical.get("kind") != "anchor" and not with_words:
        errors.append(f"expected scene anchor without words, got: {lexical!r}")
    if with_words:
        if not lexical.get("words"):
            errors.append(f"listen_moment lexical empty: {moment!r}")
        missing = [w for w in expected if w not in recalled_words]
        if missing:
            errors.append(f"recall_words_for_scene missing {missing!r}; got {recalled_words!r}")
    elif recalled_words:
        errors.append(f"unexpected recalled words without explicit words[]: {recalled_words!r}")
    if require_audio:
        if not audio_rep or not (audio_rep.get("placements") or {}).get("A0_spectrum"):
            errors.append(f"auditory imprint missing on A0_spectrum: {audio_rep!r}")
        if not any(t.startswith("A:energy:") for t in auditory_tokens):
            errors.append(f"no energy envelope tokens: {auditory_tokens!r}")
        if not any(t.startswith("A:dyn:") for t in auditory_tokens):
            errors.append(f"no dynamics tokens (prosody seed): {auditory_tokens!r}")
        scene_tok = f"A:scene:{sid}"
        if scene_tok not in auditory_tokens:
            errors.append(f"missing scene audio anchor {scene_tok!r}")
    if require_visual:
        if not visual_rep or not (visual_rep.get("placements") or {}).get("V1_lum"):
            errors.append(f"visual imprint missing on V1_lum: {visual_rep!r}")
        vis_scene = scene_visual_token(sid)
        if vis_scene not in visual_tokens:
            errors.append(f"missing scene visual anchor {vis_scene!r}")
    if errors:
        raise AssertionError("; ".join(errors))

    impulse_summary: dict[str, Any] | None = None
    if impulse:
        from casa.nervous.listen_hooks import record_listen_imprint_impulse

        impulse_summary = record_listen_imprint_impulse(
            store_dir=store,
            scene_id=sid,
            caption=str(scene.get("caption") or ""),
            words_expected=expected,
            heard=list(lexical.get("words") or []),
            recalled=recalled,
            field_version_before=fv_before,
            field_version_after=fv_after,
            auditory=audio_rep,
            auditory_tokens=auditory_tokens,
            visual=visual_rep,
            visual_tokens=visual_tokens,
        )
        if not impulse_summary or not impulse_summary.get("event_count"):
            raise AssertionError(f"missing listen_imprint impulse: {impulse_summary!r}")

    return {
        "scene_id": sid,
        "field_version_before": fv_before,
        "field_version_after": fv_after,
        "recalled": recalled,
        "auditory_tokens": auditory_tokens,
        "visual_tokens": visual_tokens,
        "visual": visual_rep,
        "impulse": impulse_summary,
    }


def _assert_impulse_trace(store: Path, *, require_audio: bool, require_visual: bool = False) -> None:
    from casa.nervous.impulse import read_impulse_trace

    rows = read_impulse_trace(store, channel="listen_imprint", limit=5)
    if not rows:
        raise AssertionError("impulse_trace.jsonl has no listen_imprint rows")
    row = rows[-1]
    summary = row.get("summary") if isinstance(row.get("summary"), dict) else {}
    if not summary.get("event_count"):
        raise AssertionError(f"listen_imprint impulse row missing events: {row!r}")
    events = row.get("events") if isinstance(row.get("events"), list) else []
    nodes = {str(event.get("node") or "") for event in events if isinstance(event, dict)}
    missing = {"field_delta", "listen_imprint"} - nodes
    if require_audio:
        missing |= {"auditory_imprint"} - nodes
    if require_visual:
        missing |= {"visual_imprint"} - nodes
    if missing:
        raise AssertionError(f"listen_imprint impulse missing {sorted(missing)}: {row!r}")


def main() -> int:
    parser = argparse.ArgumentParser(description=f"{STAGE_LABEL} verification")
    parser.add_argument("--store", action="store_true")
    parser.add_argument(
        "--with-words",
        action="store_true",
        help="Also imprint explicit words[] (reading lesson path)",
    )
    parser.add_argument("--visual", action="store_true")
    parser.add_argument("--wav", type=Path, default=None)
    parser.add_argument("--impulse", action="store_true")
    args = parser.parse_args()
    store = default_agent_store()
    try:
        result = run_probe(
            isolated=not args.store,
            impulse=args.impulse,
            store_dir=store,
            wav_path=args.wav,
            require_audio=True,
            require_visual=args.visual,
            with_words=args.with_words,
        )
        if args.impulse:
            _assert_impulse_trace(store, require_audio=True, require_visual=args.visual)
    except AssertionError as err:
        print(f"FAIL: {err}", file=sys.stderr)
        return 1

    print(STAGE_LABEL)
    print(f"scene: {result.get('scene_id')}")
    print(f"field_version: {result.get('field_version_before')} → {result.get('field_version_after')}")
    if args.with_words:
        for row in result.get("recalled") or []:
            print(f"  recall: {row.get('word')} score={row.get('score')}")
    else:
        print("  lexical: scene anchor only (no word cards)")
    dyn = [t for t in (result.get("auditory_tokens") or []) if t.startswith("A:dyn:")]
    print(f"  auditory: {len(result.get('auditory_tokens') or [])} tokens, dynamics={dyn}")
    if args.visual:
        print(f"  visual: {len(result.get('visual_tokens') or [])} tokens")
    print("SMOKE: sensory listen/imprint (no efferent required)")
    if args.impulse:
        print("SMOKE: listen_imprint impulse trace available (summary)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
