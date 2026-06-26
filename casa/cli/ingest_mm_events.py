#!/usr/bin/env python3
"""Ingest canonical multimodal events (mm_event) into an agent store.

Offline path: read events.jsonl (one JSON object per line) and convert into:
- L3 scene links for words/punctuation (via listen_scene)
- L2 word strengthening (via listen_scene/listen_word)
- schema-math episodes for math glyph cues (via append_episode)

This is intentionally small and "format-first": vision/audio perception is out of scope.
"""

from __future__ import annotations

from casa._paths import REPO_ROOT, ensure_import_paths

ensure_import_paths()

import argparse
import json
import re
from pathlib import Path
from typing import Any, Iterable

from casa.prisms.memory.memory_prisms import append_episode, ensure_prisms, memory_lattices, run_sleep
from casa.prisms.memory.listen_moment import listen_moment
from casa.prisms.shared.lattice_names_v1 import SCHEMA_MATH
from casa.prisms.shared.store_boot import boot_store
from casa.prisms.shared.store_layout import default_agent_store
from casa.prisms.shared.store_persist import mark_runtime_dirty, save_runtime_state


def _norm_words(words: Iterable[str]) -> list[str]:
    out: list[str] = []
    for w in words:
        w = str(w or "").strip().lower()
        if w:
            out.append(w)
    # de-dup while preserving order
    return list(dict.fromkeys(out))


_PUNCT_CHARS = set(list("+-−×*/÷=→()[]«»,.!?;:—…"))


def _extract_punctuation(items: Iterable[str]) -> list[str]:
    marks: list[str] = []
    for s in items:
        for ch in str(s or ""):
            if ch in _PUNCT_CHARS:
                marks.append(ch)
    # stable de-dup
    return list(dict.fromkeys(marks))


_RE_NUM_FRAC = re.compile(r"\b\d+\s*/\s*\d+\b")
_RE_STICK_HEAP = re.compile(r"\(\|+\)")


def _extract_math_glyphs(texts: Iterable[str]) -> list[str]:
    """Best-effort canonical glyphs from OCR/ASR text."""
    out: list[str] = []
    for t in texts:
        t = str(t or "")
        out.extend(m.group(0).replace(" ", "") for m in _RE_NUM_FRAC.finditer(t))
        out.extend(m.group(0) for m in _RE_STICK_HEAP.finditer(t))
    return list(dict.fromkeys([x for x in out if x]))


def _event_scene_id(ev: dict) -> str:
    eid = str(ev.get("event_id") or ev.get("id") or "").strip()
    if not eid:
        raise ValueError("mm_event missing event_id")
    return f"mm:{eid}"


def ingest_mm_events(
    store_dir: Path,
    *,
    events_jsonl: Path,
    sleep_every: int = 10,
    persist: bool = True,
) -> dict[str, Any]:
    store_dir = store_dir.resolve()
    events_jsonl = events_jsonl.resolve()

    boot = boot_store(store_dir, prefer_field_state=True)
    state = ensure_prisms(boot["state"])
    state.setdefault("store", {})["store_id"] = store_dir.name
    state["store"]["last_class"] = "mm-events"

    # require schema-math to exist (curriculum math-palochki installs it)
    lats = memory_lattices(state)
    if not (lats.get(SCHEMA_MATH) or {}).get("cells"):
        raise RuntimeError(f"schema-math missing on {store_dir}; ingest math class first")

    ingested = 0
    scenes = 0
    word_count = 0
    glyph_eps = 0
    sleep_reports: list[dict[str, Any]] = []

    for line in events_jsonl.read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        ev = json.loads(line)
        canon = dict(ev.get("canon") or {})
        audio = dict(ev.get("audio") or {})
        vision = dict(ev.get("vision") or {})

        sid = _event_scene_id(ev)
        asr_text = str(audio.get("asr_text") or "").strip()
        ocr_text = str(vision.get("ocr_text") or "").strip()

        words = _norm_words(canon.get("words") or [])
        if not words and canon.get("include_text_as_words"):
            words = _norm_words(re.findall(r"[\w\-]+", asr_text, flags=re.UNICODE))

        glyphs = [str(x) for x in (canon.get("math_glyphs") or []) if str(x).strip()]
        if not glyphs:
            glyphs = _extract_math_glyphs([ocr_text, asr_text])

        punct = [str(x) for x in (canon.get("punctuation") or []) if str(x).strip()]
        if not punct:
            punct = _extract_punctuation(list(glyphs) + [asr_text, ocr_text])

        caption = " / ".join([x for x in [asr_text, ocr_text] if x])
        if not caption:
            caption = "mm_event"

        wav_ref = str(audio.get("wav") or audio.get("path") or "").strip()
        wav_path = Path(wav_ref) if wav_ref else None
        if wav_path and not wav_path.is_file():
            candidate = store_dir / wav_ref
            wav_path = candidate if candidate.is_file() else None

        frame_ref = ""
        for img in vision.get("images") or []:
            if isinstance(img, dict):
                frame_ref = str(img.get("path") or img.get("file") or "").strip()
            elif isinstance(img, str):
                frame_ref = img.strip()
            if frame_ref:
                break
        frame_path = Path(frame_ref) if frame_ref else None
        if frame_path and not frame_path.is_file():
            candidate = store_dir / frame_ref
            frame_path = candidate if candidate.is_file() else None

        moment = listen_moment(
            state,
            {
                "id": sid,
                "caption": caption[:240] if caption != "mm_event" else "",
                "words": words,
                "punctuation": punct if words else [],
                "speaker": str(canon.get("speaker") or audio.get("speaker") or "").strip() or None,
                "speakers": canon.get("speakers"),
                "t0": audio.get("t0"),
                "t1": audio.get("t1"),
                "frame": frame_ref,
            },
            wav_path=wav_path,
            frame_path=frame_path,
            store_dir=store_dir,
            copies=3,
            bundle={"claims": [], "graph": {"edges": []}},
        )
        scenes += 1
        word_count += len(words)
        if moment.get("audio"):
            pass  # auditory imprint counted with scene

        # Each glyph cue becomes an episode on schema-math.
        # We do not assume concept_id (no runtime oracle): perception can supply it later.
        for g in glyphs:
            ep = append_episode(
                state,
                cue=g,
                surface_attempt="",
                correct=g,
                lattice_id=SCHEMA_MATH,
                concept_id=None,
                scene=sid,
                bundle={"claims": [], "graph": {"edges": []}},
                episode_source="ingest",
            )
            if ep:
                glyph_eps += 1

        ingested += 1
        if sleep_every > 0 and ingested % sleep_every == 0:
            sleep_reports.append(run_sleep(state, bundle={"claims": [], "graph": {"edges": []}}))

    if sleep_every == 0 or ingested % max(sleep_every, 1) != 0:
        # final consolidation pass for the tail batch
        sleep_reports.append(run_sleep(state, bundle={"claims": [], "graph": {"edges": []}}))

    rep: dict[str, Any] = {
        "store_dir": str(store_dir),
        "events_jsonl": str(events_jsonl),
        "events_ingested": ingested,
        "scenes": scenes,
        "words": word_count,
        "glyph_episodes": glyph_eps,
        "sleep": sleep_reports,
        "field_version": state.get("field_version"),
    }

    if persist:
        mark_runtime_dirty(state)
        rep["persist"] = save_runtime_state(
            store_dir,
            state,
            force=True,
            thin=True,
            sync_ltm_on_save=True,
        )
    return rep


def main() -> None:
    p = argparse.ArgumentParser(description="Ingest canonical multimodal events into agent store")
    p.add_argument("--store-dir", type=Path, default=None)
    p.add_argument("--events-jsonl", type=Path, required=True)
    p.add_argument("--sleep-every", type=int, default=10)
    p.add_argument("--no-persist", action="store_true")
    args = p.parse_args()

    rep = ingest_mm_events(
        args.store_dir or default_agent_store(),
        events_jsonl=args.events_jsonl,
        sleep_every=max(0, int(args.sleep_every)),
        persist=not args.no_persist,
    )
    print(json.dumps(rep, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()

