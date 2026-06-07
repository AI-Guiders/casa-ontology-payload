"""Педагогика literacy ingest (ADR-0030): порядок, probe, reinforce — без правок bridge_lex."""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path
from typing import Any, Literal

_CURRICULUM = Path(__file__).resolve().parent
from vc_paths import repo_root  # noqa: E402

_REPO = repo_root(__file__)

from teacher_pedagogy import (  # noqa: E402
    LITERACY_STAGE_PROBES,
    LEXICAL_STAGE_PROBES,
    PROBE_BY_STAGE,
    STAGE_PROBE_SPECS,
    VISUAL_STAGE_PROBES,
    stage_probe_for,
)

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


def ingest_probe_failure_frames(
    session: Any,
    spec: dict[str, Any],
    report: dict[str, Any],
    *,
    moment_copies: int = 3,
) -> list[dict[str, Any]]:
    """JPEG ingest for probe failures — lab remediation after held-out gate (not train waves)."""
    from manifest_steps import frame_by_id, steps_for_frame
    from teacher_pedagogy import load_class_manifest

    manifest = load_class_manifest(str(spec.get("class_rel") or "lessons/literacy-cards"))
    rows: list[dict[str, Any]] = []
    seen: set[str] = set()
    for item in probe_issues(report):
        fid = str(item.get("frame_id") or "")
        if not fid or fid in seen:
            continue
        seen.add(fid)
        frame = frame_by_id(manifest, fid)
        steps = steps_for_frame(frame)
        for i in range(max(1, moment_copies)):
            mid = f"remediate-{fid}-{i + 1}"[:80]
            row = session.ingest(mid, steps, frame_id=fid, remediate=i + 1)
            rows.append(
                {
                    "frame_id": fid,
                    "moment_id": mid,
                    "verdict": item.get("verdict"),
                    "bridges_emergent": row.get("bridges_emergent"),
                }
            )
    return rows


def reinforce_from_probe_report(
    state: dict[str, Any],
    report: dict[str, Any],
    *,
    copies: int = 12,
) -> list[dict[str, Any]]:
    from casa.prisms.memory.f0_stack import weaken_graph_edge
    from casa.prisms.memory.lexical_lattice_bootstrap import lattice_for_lex_concept
    from casa.prisms.memory.memory_prisms import memory_lattices, persist_content_lattices
    from casa.prisms.visual.bridge_lex import reinforce_vis_lex_bridge
    from casa.prisms.visual.bridge_math import (
        DEFAULT_RELATION,
        _weaken_on_visual_lum,
        vis_frame_concept_id,
    )

    rows: list[dict[str, Any]] = []
    for item in probe_issues(report):
        fid = str(item.get("frame_id") or "")
        hint = str(item.get("teacher_hint") or "").strip()
        if not fid or not hint:
            continue
        weakened: list[str] = []
        if str(item.get("verdict") or "") == "ambiguous":
            vis_cid = vis_frame_concept_id(fid)
            for leader in item.get("leaders") or []:
                lex_cid = str(leader or "").strip()
                if not lex_cid or lex_cid == hint:
                    continue
                _weaken_on_visual_lum(
                    state,
                    src=vis_cid,
                    relation=DEFAULT_RELATION,
                    dst=lex_cid,
                    copies=copies,
                )
                lat_id = lattice_for_lex_concept(lex_cid)
                if lat_id:
                    lats = memory_lattices(state)
                    weaken_graph_edge(
                        lats,
                        lat_id,
                        vis_cid,
                        DEFAULT_RELATION,
                        lex_cid,
                        copies=copies,
                    )
                    persist_content_lattices(state, lats)
                weakened.append(lex_cid)
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
                "weakened": weakened,
            }
        )
    return rows


def run_probe_script(
    probe_script: str,
    *,
    cwd: Path | None = None,
    extra_args: list[str] | None = None,
    allow_gate_fail: bool = False,
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
    if proc.returncode != 0 and not allow_gate_fail:
        raise RuntimeError(
            f"probe failed ({script.name}): {proc.stderr or proc.stdout}"
        )
    summary: dict[str, Any] | None = None
    tail: dict[str, Any] | None = None
    for line in proc.stdout.strip().splitlines():
        stripped = line.strip()
        if not stripped.startswith("{"):
            continue
        row = json.loads(stripped)
        if row.get("path"):
            summary = row
        else:
            tail = row
    if summary is None:
        summary = tail
    if summary is None:
        raise RuntimeError(
            f"probe stdout has no JSON summary ({script.name}): {proc.stderr or proc.stdout!r}"
        )
    report_name = Path(str(summary.get("path") or "")).name
    if not report_name:
        raise RuntimeError(
            f"probe stdout JSON has no report path ({script.name}): {summary!r}"
        )
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

