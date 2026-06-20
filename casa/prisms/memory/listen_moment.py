#!/usr/bin/env python3

"""Multimodal listen moment — sensory imprint first; words only if explicit."""



from __future__ import annotations



from pathlib import Path

from typing import Any



from casa.domain.listen_beat_model import resolve_scene_beat_timeline

from casa.domain.listen_moment_policy import (

    moment_has_sensory_input,

    scene_speakers,

    scene_words,

    wants_lexical_imprint,

)

from casa.prisms.auditory.imprint import auditory_tokens_on_field, imprint_auditory_window

from casa.prisms.memory.vocab import listen_scene, listen_scene_anchor, recall_words_for_scene

from casa.prisms.visual.imprint import imprint_visual_scene_frame, visual_tokens_on_field

from casa.sensory.load_rgb_frame import load_rgb_frame





def _resolve_media_path(ref: str, bases: tuple[Path | None, ...]) -> Path | None:

    path = Path(ref)

    if path.is_file():

        return path

    for base in bases:

        if base is None:

            continue

        candidate = base / ref

        if candidate.is_file():

            return candidate

    return None





def resolve_scene_frame(store_dir: Path | None, scene: dict[str, Any]) -> Path | None:

    entries = resolve_scene_frames(store_dir, scene)

    return entries[0][0] if entries else None





def resolve_scene_beats(

    store_dir: Path | None,

    scene: dict[str, Any],

    *,

    manifest_dir: Path | None = None,

) -> list[tuple[Path, str, float, float]]:

    """Legacy: first visual per beat — (path, beat_id, t0_rel, t1_rel)."""

    bases = (manifest_dir, store_dir)

    out: list[tuple[Path, str, float, float]] = []

    for plan in resolve_scene_beat_timeline(scene, bases):

        if not plan["visuals"]:

            continue

        path, _suffix = plan["visuals"][0]

        out.append((path, plan["beat_id"], plan["t0"], plan["t1"]))

    return out





def resolve_scene_frames(

    store_dir: Path | None,

    scene: dict[str, Any],

    *,

    manifest_dir: Path | None = None,

) -> list[tuple[Path, str, float | None]]:

    """Return (path, frame_id_suffix, t_rel_sec) — legacy frames[] or single frame."""

    bases = (manifest_dir, store_dir)

    beat_plans = resolve_scene_beat_timeline(scene, bases)

    if beat_plans:

        out: list[tuple[Path, str, float | None]] = []

        for plan in beat_plans:

            for path, suffix in plan["visuals"]:

                out.append((path, suffix, plan["t0"]))

        return out



    raw: list[tuple[str, str, float | None]] = []

    frames = scene.get("frames")

    if isinstance(frames, list) and frames:

        for i, item in enumerate(frames):

            if isinstance(item, dict):

                ref = str(item.get("path") or item.get("file") or "").strip()

                fid = str(item.get("id") or f"v{i:03d}").strip() or f"v{i:03d}"

                t_raw = item.get("t")

                t_val = float(t_raw) if t_raw is not None else None

            elif isinstance(item, str):

                ref = item.strip()

                fid = f"v{i:03d}"

                t_val = None

            else:

                continue

            if ref:

                raw.append((ref, fid, t_val))



    if not raw:

        single = str(scene.get("frame") or scene.get("frame_path") or "").strip()

        if single:

            raw.append((single, "v000", None))



    out = []

    for ref, fid, t_val in raw:

        path = _resolve_media_path(ref, bases)

        if path is not None:

            out.append((path, fid, t_val))

    return out





def listen_moment(

    state: dict,

    scene: dict[str, Any],

    *,

    wav_path: Path | str | None = None,

    frame_path: Path | str | None = None,

    store_dir: Path | None = None,

    manifest_dir: Path | None = None,

    t0_sec: float | None = None,

    t1_sec: float | None = None,

    copies: int = 3,

    bundle: dict | None = None,

) -> dict[str, Any]:

    """One moment on scene_id: beat timeline (paired or motion) or legacy visual + audio."""

    sid = str(scene.get("id") or "")

    words = scene_words(scene)

    caption = str(scene.get("caption") or "")

    punct = [str(p) for p in (scene.get("punctuation") or []) if str(p).strip()]



    chapter_t0 = float(t0_sec if t0_sec is not None else scene.get("t0") or 0.0)

    bases = (manifest_dir, store_dir)

    beat_plans = resolve_scene_beat_timeline(scene, bases)



    if frame_path:

        fp = Path(frame_path)

        frame_entries = [(fp, "v000", None)] if fp.is_file() else []

        beat_plans = []

    elif beat_plans:

        frame_entries = []

    else:

        frame_entries = resolve_scene_frames(store_dir, scene, manifest_dir=manifest_dir)



    has_wav = bool(wav_path)

    has_frame = bool(beat_plans or frame_entries)

    if sid and not moment_has_sensory_input(wav=has_wav, frame=has_frame):

        raise ValueError(f"listen moment {sid!r} needs wav and/or frame")

    field_version_before = int(state.get("field_version") or 0)



    lexical: dict[str, Any] | None = None

    if sid and wants_lexical_imprint(words):

        lexical = listen_scene(

            state,

            {"id": sid, "caption": caption, "words": words, "punctuation": punct},

            copies=copies,

            bundle=bundle,

        )

    elif sid:

        lexical = listen_scene_anchor(

            state,

            sid,

            caption,

            copies=max(2, copies - 1),

            punctuation=punct,

        )



    audio: dict[str, Any] | None = None

    audio_beats: list[dict[str, Any]] = []

    if wav_path and sid and beat_plans:

        for plan in beat_plans:

            window_id = f"{sid}-{plan['beat_id']}"

            audio_beats.append(

                imprint_auditory_window(

                    state,

                    wav_path,

                    scene_id=sid,

                    window_id=window_id,

                    t0_sec=chapter_t0 + plan["t0"],

                    t1_sec=chapter_t0 + plan["t1"],

                    speaker=str(scene.get("speaker") or "") or None,

                    speakers=scene_speakers(scene),

                )

            )

        audio = audio_beats[0] if audio_beats else None

    elif wav_path and sid:

        audio = imprint_auditory_window(

            state,

            wav_path,

            scene_id=sid,

            window_id=sid,

            t0_sec=t0_sec if t0_sec is not None else scene.get("t0"),

            t1_sec=t1_sec if t1_sec is not None else scene.get("t1"),

            speaker=str(scene.get("speaker") or "") or None,

            speakers=scene_speakers(scene),

        )



    visual_frames: list[dict[str, Any]] = []

    if beat_plans and sid:

        for plan in beat_plans:

            window_id = f"{sid}-{plan['beat_id']}"

            for path, frame_suffix in plan["visuals"]:

                frame_id = f"{sid}-{frame_suffix}"

                visual_frames.append(

                    imprint_visual_scene_frame(

                        state,

                        load_rgb_frame(path),

                        scene_id=sid,

                        frame_id=frame_id,

                        audio_window_id=window_id,

                    )

                )

    else:

        for path, fid_suffix, _t_rel in frame_entries:

            frame_id = f"{sid}-{fid_suffix}" if sid else fid_suffix

            visual_frames.append(

                imprint_visual_scene_frame(

                    state,

                    load_rgb_frame(path),

                    scene_id=sid,

                    frame_id=frame_id,

                )

            )



    has_explicit_words = wants_lexical_imprint(words)

    visual = visual_frames[0] if visual_frames else None

    motion_beats = sum(1 for p in beat_plans if p.get("kind") == "motion")

    if sid and (audio or visual_frames):
        from casa.prisms.affect import affect_after_listen_scene

        affect_after_listen_scene(state, sid, scene=scene)

    result = {

        "scene_id": sid,

        "lexical": lexical,

        "audio": audio,

        "audio_beats": audio_beats,

        "visual": visual,

        "visual_frames": visual_frames,

        "visual_frame_count": len(visual_frames),

        "paired_beats": bool(beat_plans),

        "motion_beats": motion_beats,

        "recalled_words": recall_words_for_scene(state, sid) if sid and has_explicit_words else [],

        "auditory_tokens": auditory_tokens_on_field(state, sid) if sid and (audio or audio_beats) else [],

        "visual_tokens": visual_tokens_on_field(state, sid) if sid and visual_frames else [],

    }

    if store_dir is not None and sid:
        from casa.nervous.listen_hooks import record_listen_imprint_impulse

        record_listen_imprint_impulse(
            store_dir=store_dir,
            scene_id=sid,
            caption=caption,
            words_expected=words,
            heard=[],
            recalled=result.get("recalled_words") or [],
            field_version_before=field_version_before,
            field_version_after=int(state.get("field_version") or 0),
            auditory=audio,
            auditory_tokens=result.get("auditory_tokens") or [],
            visual=visual,
            visual_tokens=result.get("visual_tokens") or [],
        )

    return result


