"""Font-size legibility sweep: ephemeral 32x32 imprint + lex predict (no store write)."""

from __future__ import annotations

import copy
import json
import re
import sys
from collections import defaultdict
from collections.abc import Sequence
from dataclasses import dataclass
from pathlib import Path
from typing import Any

_REPO = Path(__file__).resolve().parents[2]
_CURRICULUM = Path(__file__).resolve().parent
_LITERACY_TOOLS = _REPO / "lessons" / "literacy-cards" / "tools"
_MANIFEST = _REPO / "lessons" / "literacy-cards" / "class.manifest.json"

DEFAULT_FONT_SIZES_PT = (
    20,
    24,
    28,
    32,
    40,
    48,
    56,
    64,
    80,
    96,
    112,
    128,
    150,
    180,
    200,
    220,
    240,
)

PILOT_SLUGS = ("mama", "papa", "kot", "dom", "sok", "mir", "ruka", "voda")


@dataclass(frozen=True)
class WordSpec:
    frame_id: str
    surface: str
    concept_id: str
    production_font_pt: int


def _ensure_imports() -> None:
    for entry in (_REPO, _CURRICULUM, _LITERACY_TOOLS):
        s = str(entry)
        if s not in sys.path:
            sys.path.insert(0, s)
    from casa._paths import ensure_import_paths

    ensure_import_paths()


def production_font_pt(surface: str) -> int:
    _ensure_imports()
    from build_word_cards import _font_size  # noqa: E402

    return int(_font_size(surface))


def parse_font_sizes(spec: str) -> tuple[int, ...]:
    out: list[int] = []
    for part in re.split(r"[,;\s]+", spec.strip()):
        if not part:
            continue
        out.append(int(part))
    return tuple(sorted(set(out)))


def load_manifest() -> dict[str, Any]:
    return json.loads(_MANIFEST.read_text(encoding="utf-8"))


def word_specs_from_manifest(
    *,
    frame_ids: Sequence[str] | None = None,
    slugs: Sequence[str] | None = None,
    lesson_ids: set[str] | None = None,
) -> list[WordSpec]:
    _ensure_imports()
    manifest = load_manifest()
    want_ids: set[str] | None = set(frame_ids) if frame_ids else None
    want_slugs = set(slugs) if slugs else None
    out: list[WordSpec] = []
    for fr in manifest.get("frames") or []:
        fid = str(fr.get("id") or "")
        if want_ids is not None and fid not in want_ids:
            continue
        lid = str(fr.get("lesson_id") or "")
        if lesson_ids and lid not in lesson_ids:
            continue
        cid = str(fr.get("concept_id") or "")
        if not cid.startswith("lang.word."):
            continue
        slug = cid.removeprefix("lang.word.")
        if want_slugs is not None and slug not in want_slugs:
            continue
        from manifest_steps import lexical_spec_from_frame  # noqa: E402

        surface = lexical_spec_from_frame(fr)["correct"]
        out.append(
            WordSpec(
                frame_id=fid,
                surface=surface,
                concept_id=cid,
                production_font_pt=production_font_pt(surface),
            )
        )
    if want_slugs:
        order = {s: i for i, s in enumerate(slugs)}
        out.sort(key=lambda w: order.get(w.concept_id.rsplit(".", 1)[-1], 999))
    else:
        out.sort(key=lambda w: w.frame_id)
    return out


def render_word_rgb(surface: str, font_pt: int) -> Any:
    """RgbFrame через канонический literacy_render (не дублируем PIL-разметку)."""
    import tempfile

    _ensure_imports()
    from literacy_render import draw_text_centered  # noqa: E402

    from casa.sensory.load_rgb_frame import load_rgb_frame

    with tempfile.NamedTemporaryFile(suffix=".jpg", delete=False) as tmp:
        path = Path(tmp.name)
    try:
        draw_text_centered(surface, path, size=font_pt)
        return load_rgb_frame(path)
    finally:
        path.unlink(missing_ok=True)


def lum_imprint_metrics(frame_rgb: Any, *, grid_size: int = 32) -> dict[str, Any]:
    """Stats on 32x32 lum downsample (ink footprint), independent of store."""
    from casa.domain.visual_tract import LATTICE_V1_LUM
    from casa.sensory.codecs.retinal_lrgb import encode_retinal_lrgb

    plan = encode_retinal_lrgb(frame_rgb, frame_id="_metrics", grid_size=grid_size)
    placements = plan.placements_by_lattice.get(LATTICE_V1_LUM) or ()
    levels: list[tuple[int, int, int]] = []
    for p in placements:
        if not p.token.startswith("V:lum:"):
            continue
        lvl = int(p.token.split(":")[-1], 16)
        levels.append((p.x, p.y, lvl))
    if not levels:
        return {
            "grid_size": grid_size,
            "lum_ink_cells": 0,
            "lum_bbox_w": 0,
            "lum_bbox_h": 0,
            "lum_min_level": None,
            "lum_max_level": None,
        }
    ink = [t for t in levels if t[2] <= 5]
    xs = [t[0] for t in ink] or [t[0] for t in levels]
    ys = [t[1] for t in ink] or [t[1] for t in levels]
    lvls = [t[2] for t in levels]
    return {
        "grid_size": grid_size,
        "lum_ink_cells": len(ink),
        "lum_bbox_w": max(xs) - min(xs) + 1 if xs else 0,
        "lum_bbox_h": max(ys) - min(ys) + 1 if ys else 0,
        "lum_min_level": min(lvls),
        "lum_max_level": max(lvls),
    }


def snapshot_visual_cells(state: dict[str, Any]) -> dict[str, list[list[str]]]:
    """Copy all V1_* cells — rollback ephemeral imprint between font_pt / words."""
    _ensure_imports()
    from casa.domain.prism_ids import PRISM_VISUAL
    from casa.domain.prism_wire import prism_block
    from casa.domain.visual_tract import VISUAL_LATTICE_IDS

    lats = (prism_block(state, PRISM_VISUAL).get("lattices") or {})
    snap: dict[str, list[list[str]]] = {}
    for lid in VISUAL_LATTICE_IDS:
        cells = (lats.get(lid) or {}).get("cells")
        if isinstance(cells, list):
            snap[lid] = copy.deepcopy(cells)
    return snap


def restore_visual_cells(state: dict[str, Any], snap: dict[str, list[list[str]]]) -> None:
    if not snap:
        return
    _ensure_imports()
    from casa.domain.prism_ids import PRISM_VISUAL
    from casa.domain.prism_wire import prism_block

    lats = (prism_block(state, PRISM_VISUAL).get("lattices") or {})
    for lid, cells in snap.items():
        lat = lats.get(lid)
        if lat is not None:
            lat["cells"] = copy.deepcopy(cells)


def snapshot_lum_cells(state: dict[str, Any]) -> list[list[str]] | None:
    return snapshot_visual_cells(state).get("V1_lum")


def restore_lum_cells(state: dict[str, Any], cells: list[list[str]] | None) -> None:
    if cells is None:
        return
    restore_visual_cells(state, {"V1_lum": cells})


def predict_after_ephemeral_imprint(
    state: dict[str, Any],
    *,
    frame_id: str,
    surface: str,
    font_pt: int,
    top_k: int = 5,
) -> tuple[list[tuple[str, int]], dict[str, Any]]:
    from casa.prisms.visual.bridge_lex import predict_lex_for_vis_cue
    from casa.prisms.visual.imprint import imprint_visual_frame

    rgb = render_word_rgb(surface, font_pt)
    metrics = lum_imprint_metrics(rgb)
    return predict_after_ephemeral_imprint_variant(
        state,
        frame_id=frame_id,
        surface=surface,
        font_pt=font_pt,
        top_k=top_k,
        bridges="full",
    )


def predict_stored_bridge(state: dict[str, Any], frame_id: str, *, top_k: int = 5) -> list[tuple[str, int]]:
    return predict_lex_variant(state, frame_id, top_k=top_k, bridges="full")


def predict_lex_variant(
    state: dict[str, Any],
    cue: str,
    *,
    top_k: int = 5,
    bridges: str = "full",
) -> list[tuple[str, int]]:
    """full = lum E:-tokens + lexicon edges (учебный мост); cells_only / edges_only — разложение."""
    _ensure_imports()
    from casa.domain.prism_ids import PRISM_VISUAL
    from casa.domain.prism_wire import prism_block
    from casa.prisms.memory.f0_stack import decode_f0_lattice
    from casa.prisms.memory.memory_prisms import memory_lattices
    from casa.prisms.memory.meta_concept_aliases import canonical_lex_concept_id
    from casa.prisms.shared.lattice_names_v1 import (
        ALPHABET_EN,
        ALPHABET_RU,
        LEXICON_EN,
        LEXICON_RU,
        SYLLABLES_EN,
        SYLLABLES_RU,
    )
    from casa.prisms.visual.bootstrap import ensure_prism_visual
    from casa.prisms.visual.bridge_lex import _LEX_DST_PREFIXES, vis_frame_concept_id
    from casa.prisms.visual.bridge_math import frame_id_from_vis_cue

    ensure_prism_visual(state)
    lats = memory_lattices(state)
    lum = (prism_block(state, PRISM_VISUAL).get("lattices") or {}).get("V1_lum") or {}
    if not lum.get("cells"):
        return []
    vis_cid = vis_frame_concept_id(frame_id_from_vis_cue(str(cue or "")))
    prefix = f"E:{vis_cid}|"
    scores: dict[str, int] = {}

    def bump(dst: str, n: int) -> None:
        if dst.startswith(_LEX_DST_PREFIXES):
            canon = canonical_lex_concept_id(dst)
            scores[canon] = scores.get(canon, 0) + n

    if bridges in ("full", "cells_only"):
        for cell in lum.get("cells") or []:
            if not isinstance(cell, list):
                continue
            for tok in cell:
                if not isinstance(tok, str) or not tok.startswith(prefix):
                    continue
                parts = tok.split("|", 2)
                if len(parts) == 3:
                    bump(parts[2], 1)
    if bridges in ("full", "edges_only"):
        for lat_id in (ALPHABET_RU, LEXICON_RU, SYLLABLES_RU, ALPHABET_EN, LEXICON_EN, SYLLABLES_EN):
            lat = lats.get(lat_id) or {}
            if not lat.get("cells"):
                continue
            dec = decode_f0_lattice(lat)
            for es in dec.get("edges") or []:
                if isinstance(es, str) and es.startswith(prefix):
                    parts = es.split("|", 2)
                    if len(parts) == 3:
                        bump(parts[2], 2)
    return sorted(scores.items(), key=lambda x: (-x[1], x[0]))[:top_k]


def novel_probe_frame_id(word: WordSpec) -> str:
    """frame_id без учебного ingest — нет E:vis.lum.frame.<id> в lexicon."""
    slug = word.concept_id.rsplit(".", 1)[-1][:40]
    return f"legibility-novel-{slug}"


def predict_after_ephemeral_imprint_variant(
    state: dict[str, Any],
    *,
    frame_id: str,
    surface: str,
    font_pt: int,
    top_k: int = 5,
    bridges: str = "full",
) -> tuple[list[tuple[str, int]], dict[str, Any]]:
    from casa.prisms.visual.imprint import imprint_visual_frame

    rgb = render_word_rgb(surface, font_pt)
    metrics = lum_imprint_metrics(rgb)
    imprint_visual_frame(state, rgb, frame_id=frame_id, record_episode=False)
    preds = predict_lex_variant(state, frame_id, top_k=top_k, bridges=bridges)
    return preds, metrics


def top_grapheme_syllable(preds: list[tuple[str, int]]) -> list[dict[str, Any]]:
    out: list[dict[str, Any]] = []
    for cid, score in preds:
        if cid.startswith("grapheme.") or cid.startswith("syllable."):
            out.append({"concept_id": cid, "score": score})
    return out[:5]


def summarize_by_font(items: list[dict[str, Any]]) -> list[dict[str, Any]]:
    by_font: dict[int, list[str]] = defaultdict(list)
    for it in items:
        if it.get("mode") != "ephemeral":
            continue
        by_font[int(it["font_pt"])].append(str(it.get("verdict") or ""))
    rows: list[dict[str, Any]] = []
    for font_pt in sorted(by_font):
        verdicts = by_font[font_pt]
        n = len(verdicts)
        rows.append(
            {
                "font_pt": font_pt,
                "n": n,
                "know": sum(1 for v in verdicts if v == "know"),
                "ambiguous": sum(1 for v in verdicts if v == "ambiguous"),
                "wrong": sum(1 for v in verdicts if v == "wrong"),
                "empty": sum(1 for v in verdicts if v == "empty"),
                "know_rate": round(sum(1 for v in verdicts if v == "know") / n, 3) if n else 0.0,
            }
        )
    return rows


def estimate_threshold_pt(
    by_font: list[dict[str, Any]],
    *,
    know_rate_floor: float = 0.5,
) -> dict[str, Any]:
    """Largest font_pt where know_rate still >= floor; first drop below = legibility cliff (heuristic)."""
    if not by_font:
        return {"last_strong_font_pt": None, "first_weak_font_pt": None}
    strong: int | None = None
    first_weak: int | None = None
    for row in by_font:
        pt = int(row["font_pt"])
        if float(row["know_rate"]) >= know_rate_floor:
            strong = pt
        elif first_weak is None:
            first_weak = pt
    return {
        "last_strong_font_pt": strong,
        "first_weak_font_pt": first_weak,
        "know_rate_floor": know_rate_floor,
    }

