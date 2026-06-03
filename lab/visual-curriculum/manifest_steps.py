"""Manifest frame → moment steps (vis↔lex / grapheme)."""

from __future__ import annotations

from collections.abc import Callable, Sequence
from typing import Any

from curriculum_lab import IngestJob, jobs_from_steps


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

    tools = Path(__file__).resolve().parents[2] / "lessons" / "literacy-cards" / "tools"
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


def frame_by_id(manifest: dict[str, Any], frame_id: str) -> dict[str, Any]:
    for f in manifest.get("frames") or []:
        if str(f.get("id")) == frame_id:
            return f
    raise KeyError(frame_id)


def letter_frame_id(cue: str, register: str, *, face: str = "sans") -> str:
    return f"letter-{cue}-{register}-{face}"


def jobs_manifest_frame_rounds(
    manifest: dict[str, Any],
    cues: Sequence[str],
    *,
    register: str,
    rounds: int,
    moment_id_fmt: str,
    face: str = "sans",
    step_builder: Callable[[dict[str, Any]], list[dict[str, Any]]] = steps_for_frame,
) -> list[IngestJob]:
    items: list[tuple[str, list[dict[str, Any]]]] = []
    for r in range(1, rounds + 1):
        for cue in cues:
            frame = frame_by_id(manifest, letter_frame_id(cue, register, face=face))
            items.append((moment_id_fmt.format(round=r, cue=cue)[:80], step_builder(frame)))
    return jobs_from_steps(items)
