#!/usr/bin/env python3
"""Per-lemma axes: era, usage_band, active_for_t9 (modern prod vs archaic lab)."""

from __future__ import annotations

from casa._paths import ensure_import_paths

ensure_import_paths()

import json
from pathlib import Path
from typing import Any, Literal

from casa.prisms.memory.vocab import norm_word

Era = Literal["modern", "archaic", "dialect", "unknown"]
UsageBand = Literal["active", "rare", "ultra_rare", "unused"]
T9Policy = Literal["prod", "lab", "modern_all"]

# DetCorpus rank thresholds (v0) — see design/lexicon-usage-axes.md
ACTIVE_MAX_RANK = 8_000
ACTIVE_MIN_IPM = 15.0
RARE_MAX_RANK = 25_000
RARE_MIN_IPM = 2.0

SOURCE_DETCORPUS = "detcorpus-50k-cc0"
SOURCE_OPENSUB_EN = "opensubtitles-en-50k"
SOURCE_AFAN = "afanasyev-sharded"


def en_general_frequency_path(*, root: Path | None = None) -> Path:
    base = root or Path(__file__).resolve().parent.parent
    return base / "lab/corpus/en-general/frequency.ipm.v1.jsonl"


def ru_general_frequency_path(*, root: Path | None = None) -> Path:
    base = root or Path(__file__).resolve().parent.parent
    return base / "lab/corpus/ru-general/frequency.ipm.v1.jsonl"


def usage_band_from_freq(*, rank: int, ipm: float) -> UsageBand:
    if rank <= ACTIVE_MAX_RANK or ipm >= ACTIVE_MIN_IPM:
        return "active"
    if rank <= RARE_MAX_RANK or ipm >= RARE_MIN_IPM:
        return "rare"
    return "ultra_rare"


def default_active_for_t9(*, era: Era, usage_band: UsageBand) -> bool:
    if era != "modern":
        return False
    return usage_band in ("active", "rare")


def axis_record(
    lemma: str,
    *,
    era: Era = "modern",
    usage_band: UsageBand = "active",
    active_for_t9: bool | None = None,
    ipm: float | None = None,
    rank: int | None = None,
    sources: list[str] | None = None,
) -> dict[str, Any]:
    w = norm_word(lemma)
    band = usage_band
    if active_for_t9 is None:
        active_for_t9 = default_active_for_t9(era=era, usage_band=band)
    row: dict[str, Any] = {
        "lemma": w,
        "era": era,
        "usage_band": band,
        "active_for_t9": bool(active_for_t9),
        "sources": list(sources or []),
    }
    if ipm is not None:
        row["ipm"] = round(float(ipm), 4)
    if rank is not None:
        row["rank"] = int(rank)
    return row


def build_modern_axes_from_frequency_jsonl(
    path: Path,
    *,
    source: str = SOURCE_DETCORPUS,
) -> dict[str, dict[str, Any]]:
    """One axis row per frequency-jsonl lemma."""
    out: dict[str, dict[str, Any]] = {}
    for line in path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line:
            continue
        row = json.loads(line)
        lemma = norm_word(str(row.get("lemma") or ""))
        if not lemma:
            continue
        rank = int(row.get("rank") or len(out) + 1)
        ipm = float(row.get("ipm") or 0)
        band = usage_band_from_freq(rank=rank, ipm=ipm)
        out[lemma] = axis_record(
            lemma,
            era="modern",
            usage_band=band,
            ipm=ipm,
            rank=rank,
            sources=[source],
        )
    return out


def merge_locale_axes(*parts: dict[str, dict[str, Any]]) -> dict[str, dict[str, Any]]:
    """Merge RU + EN sidecars (disjoint alphabets in v0). Later keys win on collision."""
    merged: dict[str, dict[str, Any]] = {}
    for block in parts:
        merged.update(block)
    return merged


def attach_en_frequency_axes(
    state: dict,
    *,
    root: Path | None = None,
    store_dir: Path | None = None,
    freq_path: Path | None = None,
) -> dict[str, Any] | None:
    """Load OpenSubtitles EN freq sidecar → state + optional store lexicon_axes.jsonl."""
    path = freq_path or en_general_frequency_path(root=root)
    if not path.is_file():
        return None
    axes = build_modern_axes_from_frequency_jsonl(path, source=SOURCE_OPENSUB_EN)
    if store_dir is not None:
        write_axes_jsonl(store_dir / "lexicon_axes.jsonl", axes)
    attach_axes_to_state(state, axes)
    return axes_report(axes)


def overlay_archaic_lemmas(
    axes: dict[str, dict[str, Any]],
    archaic_words: set[str],
    *,
    source: str = SOURCE_AFAN,
) -> int:
    n = 0
    for raw in archaic_words:
        w = norm_word(raw)
        if not w:
            continue
        axes[w] = axis_record(
            w,
            era="archaic",
            usage_band="unused",
            active_for_t9=False,
            sources=[source],
        )
        n += 1
    return n


def write_axes_jsonl(path: Path, axes: dict[str, dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    lines = [json.dumps(axes[w], ensure_ascii=False) for w in sorted(axes)]
    path.write_text("\n".join(lines) + ("\n" if lines else ""), encoding="utf-8")


def load_axes_jsonl(path: Path) -> dict[str, dict[str, Any]]:
    if not path.is_file():
        return {}
    out: dict[str, dict[str, Any]] = {}
    for line in path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line:
            continue
        row = json.loads(line)
        w = norm_word(str(row.get("lemma") or ""))
        if w:
            out[w] = row
    return out


def attach_axes_to_state(state: dict, axes: dict[str, dict[str, Any]]) -> None:
    state["lexicon_axes"] = axes
    state.setdefault("store", {})["lexicon_axes_path"] = "lexicon_axes.jsonl"
    active = sum(1 for r in axes.values() if r.get("active_for_t9"))
    state["store"]["lexicon_axes_summary"] = {
        "lemma_count": len(axes),
        "active_for_t9": active,
        "schema": "lexicon_usage_axes",
    }


def lemma_axis(axes: dict[str, dict[str, Any]], word: str) -> dict[str, Any] | None:
    w = norm_word(word)
    return axes.get(w) if w else None


def t9_allows_word(
    axes: dict[str, dict[str, Any]],
    word: str,
    *,
    policy: T9Policy = "prod",
) -> bool:
    if policy == "lab" or not axes:
        return True
    ax = lemma_axis(axes, word)
    if ax is None:
        # RU sidecar does not list EN / out-of-corpus lemmas — do not block BiT9 or EN L2.
        if policy == "lab":
            return True
        if policy == "modern_all":
            return True
        return True
    if policy == "modern_all":
        return str(ax.get("era") or "") == "modern"
    return bool(ax.get("active_for_t9"))


def filter_ranked_for_t9(
    ranked: list[tuple[str, int]],
    axes: dict[str, dict[str, Any]],
    *,
    policy: T9Policy = "prod",
    top_k: int = 8,
) -> list[tuple[str, int]]:
    if policy == "lab" or not axes:
        return ranked[:top_k]
    out: list[tuple[str, int]] = []
    for word, votes in ranked:
        if t9_allows_word(axes, word, policy=policy):
            out.append((word, votes))
        if len(out) >= top_k:
            break
    return out


def axes_report(axes: dict[str, dict[str, Any]]) -> dict[str, Any]:
    by_era: dict[str, int] = {}
    by_band: dict[str, int] = {}
    active = 0
    for row in axes.values():
        by_era[str(row.get("era") or "unknown")] = by_era.get(str(row.get("era")), 0) + 1
        by_band[str(row.get("usage_band") or "unknown")] = by_band.get(str(row.get("usage_band")), 0) + 1
        if row.get("active_for_t9"):
            active += 1
    return {
        "lemma_count": len(axes),
        "active_for_t9": active,
        "by_era": by_era,
        "by_usage_band": by_band,
    }
