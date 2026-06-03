"""Helpers: manifest frame → lesson_moment steps."""

from __future__ import annotations

from typing import Any


def lexical_spec_from_frame(frame: dict[str, Any]) -> dict[str, str]:
    cid = str(frame.get("concept_id") or "")
    tags = {t.split(":", 1)[0]: t.split(":", 1)[1] for t in frame.get("curriculum_tags") or [] if ":" in t}
    if cid.startswith("grapheme."):
        parts = cid.split(".")
        cue = parts[-2] if len(parts) >= 4 else tags.get("cue", "")
        register = parts[-1]
        surface = _surface_for_grapheme(cue, register)
        return {
            "cue": cue,
            "correct": surface,
            "register": register,
            "concept_id": cid,
        }
    if cid.startswith("syllable."):
        surface = cid.split(".", 1)[1]
        return {"cue": surface, "correct": surface, "concept_id": cid, "lattice_id": "syllables-ru"}
    if cid.startswith("lang.word.") or cid.startswith("lang.meta."):
        surface = tags.get("surface") or tags.get("word") or cid.rsplit(".", 1)[-1]
        return {
            "cue": cid.rsplit(".", 1)[-1],
            "correct": surface,
            "concept_id": cid,
            "lattice_id": "lexicon-ru",
        }
    raise ValueError(f"unsupported concept_id: {cid}")


def _surface_for_grapheme(cue: str, register: str) -> str:
    import sys
    from pathlib import Path

    import _ensure_paths  # noqa: F401
    from lab_paths import setup_lab_paths

    repo, _ = setup_lab_paths(__file__)
    tools = repo / "lessons" / "literacy-cards" / "tools"
    if str(tools) not in sys.path:
        sys.path.insert(0, str(tools))
    from build_letter_cards import CYRILLIC  # noqa: E402

    for c, lo, up in CYRILLIC:
        if c == cue:
            return lo if register == "lower" else up
    return cue


def steps_for_frame(frame: dict[str, Any]) -> list[dict[str, Any]]:
    fid = str(frame.get("id") or "")
    return [
        {"visual_frame": fid},
        {"lexical": lexical_spec_from_frame(frame)},
    ]
