"""Педагогика literacy ingest (ADR-0030): порядок, probe, reinforce — без правок bridge_lex."""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path
from typing import Any, Literal

_CURRICULUM = Path(__file__).resolve().parent
_REPO = _CURRICULUM.parents[1]

OrderMode = Literal["frame_id", "wordlist", "manifest"]


def surface_from_frame(frame: dict[str, Any]) -> str | None:
    for tag in frame.get("curriculum_tags") or []:
        if isinstance(tag, str) and tag.startswith("word:"):
            return tag[5:]
    return None


def order_frames(
    frames: list[dict[str, Any]],
    *,
    mode: OrderMode = "frame_id",
    wordlist_path: Path | str | None = None,
) -> list[dict[str, Any]]:
    if mode == "manifest":
        return list(frames)
    if mode == "frame_id":
        return sorted(frames, key=lambda f: str(f.get("id")))
    if mode == "wordlist":
        if not wordlist_path:
            raise ValueError("wordlist_path required for order=wordlist")
        path = Path(wordlist_path)
        surfaces = [
            ln.strip()
            for ln in path.read_text(encoding="utf-8").splitlines()
            if ln.strip()
        ]
        by_surface: dict[str, dict[str, Any]] = {}
        for fr in frames:
            surf = surface_from_frame(fr)
            if surf:
                by_surface[surf] = fr
        ordered: list[dict[str, Any]] = []
        seen: set[str] = set()
        for surf in surfaces:
            fr = by_surface.get(surf)
            if fr is None:
                continue
            fid = str(fr.get("id"))
            if fid in seen:
                continue
            seen.add(fid)
            ordered.append(fr)
        for fr in frames:
            fid = str(fr.get("id"))
            if fid not in seen:
                ordered.append(fr)
        return ordered
    raise ValueError(f"unknown order mode: {mode!r}")


def frames_for_stage(
    manifest: dict[str, Any],
    stage_id: str,
    *,
    limit: int = 0,
    offset: int = 0,
    order: OrderMode = "frame_id",
    wordlist_path: Path | str | None = None,
) -> list[dict[str, Any]]:
    lesson_ids: set[str] = set()
    for st in manifest.get("stages") or []:
        if str(st.get("id")) == stage_id:
            lesson_ids = set(st.get("lesson_ids") or [])
            break
    if not lesson_ids:
        raise SystemExit(f"unknown stage: {stage_id!r}")
    frames = [f for f in manifest.get("frames") or [] if str(f.get("lesson_id")) in lesson_ids]
    wl = wordlist_path
    if wl is None and order == "wordlist":
        wl = default_wordlist_for_stage(stage_id)
    frames = order_frames(frames, mode=order, wordlist_path=wl)
    if offset:
        frames = frames[offset:]
    if limit > 0:
        frames = frames[:limit]
    return frames


def default_wordlist_for_stage(stage_id: str) -> Path | None:
    data = _REPO / "lessons" / "literacy-cards" / "data"
    if stage_id == "stage-07-closed-class":
        return data / "ru-closed-class-v1.txt"
    if stage_id == "stage-06-words-cyrl-corpus":
        return data / "ru-wordlist-v1.txt"
    return None


def hippo_pending_surface_episodes(state: dict[str, Any]) -> list[dict[str, Any]]:
    """Lex/math surface episodes still in hippo after sleep — риск cartesian на следующем moment."""
    from casa.prisms.memory.memory_prisms import prism_hippo

    hippo = prism_hippo(state)
    out: list[dict[str, Any]] = []
    for ep in hippo.get("episodes") or []:
        if ep.get("consolidated"):
            continue
        if ep.get("pending") or ep.get("kind") in ("question", "hint"):
            out.append(ep)
            continue
        if str(ep.get("lattice_id") or "") in (
            "lexicon-ru",
            "lexicon-en",
            "alphabet-ru",
            "alphabet-en",
            "syllables-ru",
            "syllables-en",
        ):
            out.append(ep)
    return out


def probe_issues(report: dict[str, Any]) -> list[dict[str, Any]]:
    """Строки probe с verdict empty | ambiguous."""
    bad: list[dict[str, Any]] = []
    for row in report.get("items") or []:
        v = str(row.get("verdict") or "")
        if v in ("empty", "ambiguous", "wrong"):
            bad.append(row)
    return bad


def reinforce_from_probe_report(
    state: dict[str, Any],
    report: dict[str, Any],
    *,
    copies: int = 12,
) -> list[dict[str, Any]]:
    from casa.prisms.visual.bridge_lex import reinforce_vis_lex_bridge

    rows: list[dict[str, Any]] = []
    for item in probe_issues(report):
        fid = str(item.get("frame_id") or "")
        hint = str(item.get("teacher_hint") or "").strip()
        if not fid or not hint:
            continue
        row = reinforce_vis_lex_bridge(
            state,
            frame_id=fid,
            lex_cid=hint,
            copies=copies,
        )
        rows.append(
            {
                "frame_id": fid,
                "lex_cid": hint,
                "verdict": item.get("verdict"),
                "reinforced": row is not None,
            }
        )
    return rows


def run_probe_script(
    probe_script: str,
    *,
    cwd: Path | None = None,
    extra_args: list[str] | None = None,
) -> dict[str, Any]:
    """Запуск probe_*.py из lab/visual-curriculum, вернуть JSON отчёт."""
    cwd = cwd or _CURRICULUM
    script = cwd / probe_script
    proc = subprocess.run(
        [sys.executable, str(script), *(extra_args or [])],
        cwd=str(_REPO),
        capture_output=True,
        text=True,
        encoding="utf-8",
        check=False,
    )
    if proc.returncode != 0:
        raise RuntimeError(
            f"probe failed ({script.name}): {proc.stderr or proc.stdout}"
        )
    summary: dict[str, Any] | None = None
    for line in reversed(proc.stdout.strip().splitlines()):
        stripped = line.strip()
        if stripped.startswith("{"):
            summary = json.loads(stripped)
            break
    if summary is None:
        raise RuntimeError(
            f"probe stdout has no JSON summary ({script.name}): {proc.stderr or proc.stdout!r}"
        )
    report_name = Path(str(summary.get("path") or "")).name
    report = json.loads((cwd / "generated" / report_name).read_text(encoding="utf-8"))
    return report


def promote_emergent_routes_after_probe(
    state: dict[str, Any],
    report: dict[str, Any],
) -> dict[str, Any]:
    """Probe gate → mastery journal only (routes: agent tick)."""
    from casa.domain.emergent_promote import record_probe_gate
    from casa.prisms.shared.store_persist import mark_runtime_dirty

    result = record_probe_gate(state, report)
    if result.passed or result.promoted:
        mark_runtime_dirty(state)
    return {
        "gate": result.gate,
        "passed": result.passed,
        "promoted_count": len(result.promoted),
        "promoted": result.promoted,
        "skipped": result.skipped,
    }


PROBE_BY_STAGE: dict[str, str] = {
    "stage-05-syllable-cyrl": "probe_syllable_quiz.py",
    "stage-06-words-cyrl-corpus": "probe_literacy_corpus_quiz.py",
    "stage-07-closed-class": "probe_literacy_closed_class_quiz.py",
    "stage-04-meta-phonology-vowel-consonant": "probe_meta_phonology_quiz.py",
    "stage-08-meta-grammar-person": "probe_meta_grammar_person_quiz.py",
    "stage-09-grammar-agreement-pilot": "probe_meta_grammar_agreement_quiz.py",
}
