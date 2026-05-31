#!/usr/bin/env python3
"""BiT9 merged preview chip: freq-ranked EN + RU + optional hub surfaces."""

from __future__ import annotations

import math
from typing import Any, Literal

from entity_taxonomy_lookup_v0 import taxonomy_bonus  # type: ignore
from hub_neighbors_v0 import neighbor_surfaces  # type: ignore
from lexicon_usage_axes_v0 import T9Policy, lemma_axis, t9_allows_word  # type: ignore
from sss_vocab_v0 import norm_word  # type: ignore


def _branch_anchor_items(tb: dict[str, Any], *, max_word_len: int | None = None) -> list[dict[str, Any]]:
    lang = tb.get("language")
    script = tb.get("script")
    gstr = str(tb.get("grapheme_string") or "")
    if max_word_len is None and len(gstr) <= 2:
        max_word_len = len(gstr) + 1
    raw = tb.get("anchors") or []
    pred = tb.get("predict") or {}
    if not raw and pred.get("anchors"):
        raw = pred.get("anchors") or []
    items: list[dict[str, Any]] = []
    for i, a in enumerate(raw):
        if isinstance(a, dict):
            word = norm_word(str(a.get("word") or ""))
            votes = int(a.get("votes") or 0)
        else:
            word = norm_word(str(a))
            votes = 0
        if not word:
            continue
        if max_word_len is not None and len(word) > max_word_len:
            continue
        items.append(
            {
                "word": word,
                "language": lang,
                "script": script,
                "branch_rank": i + 1,
                "votes": votes,
            }
        )
    return items


def _is_ultra_low_freq_short(word: str, axes: dict[str, dict[str, Any]] | None) -> bool:
    """Drop 2–3 char fragments with ipm < 5 when richer pool exists (e.g. сол vs сон/сок)."""
    if not axes or len(word) > 3:
        return False
    ax = lemma_axis(axes, word)
    if not ax:
        return False
    ipm = float(ax.get("ipm") or 0)
    return 0 < ipm < 5.0


def _filter_preview_pool(items: list[dict[str, Any]], axes: dict[str, dict[str, Any]] | None) -> list[dict[str, Any]]:
    if not items or not axes:
        return items
    strong = [x for x in items if not _is_ultra_low_freq_short(str(x.get("word") or ""), axes)]
    return strong if len(strong) >= 2 else items


def _ipm_bonus(word: str, axes: dict[str, dict[str, Any]] | None) -> float:
    if not axes:
        return 0.0
    ax = lemma_axis(axes, word)
    if not ax:
        return 0.0
    ipm = float(ax.get("ipm") or 0)
    if ipm > 0:
        return math.log1p(ipm) * 12.0
    rank = int(ax.get("rank") or 0)
    if rank > 0:
        return max(0.0, 10.0 - math.log10(rank + 1) * 2.5)
    return 0.0


def _preview_item_score(
    item: dict[str, Any],
    *,
    axes: dict[str, dict[str, Any]] | None,
    state: dict[str, Any] | None = None,
    semantic_prior: bool = False,
    source: str = "t9",
    via_hub: str | None = None,
) -> float:
    rank = int(item.get("branch_rank") or 99)
    word = str(item.get("word") or "")
    score = 500.0 - rank * 8.0 + _ipm_bonus(word, axes)
    score += int(item.get("votes") or 0) * 2.0
    if source == "hub":
        score += 35.0
    if semantic_prior and state is not None:
        score += taxonomy_bonus(state, word)
    return score


def _hub_injections(
    state: dict[str, Any] | None,
    en_words: list[str],
    *,
    axes: dict[str, dict[str, Any]] | None,
    t9_policy: T9Policy = "prod",
) -> list[dict[str, Any]]:
    if state is None:
        return []
    out: list[dict[str, Any]] = []
    seen: set[str] = set()
    for en_w in en_words[:4]:
        for cid in neighbor_surfaces(state, en_w):
            if not cid.startswith("lang.word."):
                continue
            ru_w = norm_word(cid[len("lang.word.") :])
            if not ru_w or ru_w in seen:
                continue
            if axes and not t9_allows_word(axes, ru_w, policy=t9_policy):
                continue
            seen.add(ru_w)
            out.append(
                {
                    "word": ru_w,
                    "language": "ru",
                    "script": "cyrl",
                    "branch_rank": 0,
                    "via_hub": en_w,
                    "source": "hub",
                }
            )
    return out


def merge_preview_anchors(
    branches: list[dict[str, Any]],
    *,
    state: dict[str, Any] | None = None,
    top_k: int = 8,
    min_per_lang: int = 2,
    hub_boost: bool = True,
    semantic_prior: bool = False,
    t9_policy: T9Policy = "prod",
) -> list[dict[str, Any]]:
    """Balanced EN/RU preview sorted by ipm within each language + hub surfaces."""
    if semantic_prior and state is None:
        semantic_prior = False
    axes = (state or {}).get("lexicon_axes") or {}

    by_lang: dict[str, list[dict[str, Any]]] = {"en": [], "ru": []}
    for tb in branches:
        lang = str(tb.get("language") or "")
        if lang not in by_lang:
            continue
        for item in _branch_anchor_items(tb):
            if axes and lang == "ru" and not t9_allows_word(axes, item["word"], policy=t9_policy):
                continue
            scored = dict(item)
            scored["_score"] = _preview_item_score(
                scored, axes=axes or None, state=state, semantic_prior=semantic_prior
            )
            scored["source"] = "t9"
            by_lang[lang].append(scored)

    for lang in by_lang:
        by_lang[lang] = _filter_preview_pool(by_lang[lang], axes or None)
        by_lang[lang].sort(key=lambda x: (-float(x["_score"]), len(x["word"]), x["word"]))

    en_top = [x["word"] for x in by_lang["en"][:4]]
    hub_items = _hub_injections(state, en_top, axes=axes or None, t9_policy=t9_policy) if hub_boost else []
    for hi in hub_items:
        hi["_score"] = _preview_item_score(
            hi,
            axes=axes or None,
            state=state,
            semantic_prior=semantic_prior,
            source="hub",
            via_hub=str(hi.get("via_hub") or ""),
        )

    merged: list[dict[str, Any]] = []
    seen: set[tuple[str | None, str]] = set()

    def _add(item: dict[str, Any]) -> bool:
        if len(merged) >= top_k:
            return False
        key = (item.get("language"), item["word"])
        if key in seen:
            return False
        seen.add(key)
        row = {k: v for k, v in item.items() if k != "_score"}
        row["preview_rank"] = len(merged) + 1
        row["score"] = round(float(item.get("_score") or 0), 2)
        merged.append(row)
        return True

    dual = bool(by_lang["en"]) and bool(by_lang["ru"])
    if dual:
        for item in by_lang["en"][:min_per_lang]:
            _add(item)
        for item in by_lang["ru"][:min_per_lang]:
            _add(item)
        for item in sorted(hub_items, key=lambda x: -float(x["_score"])):
            _add(item)

    rest = sorted(
        by_lang["en"][min_per_lang if dual else 0 :]
        + by_lang["ru"][min_per_lang if dual else 0 :]
        + hub_items,
        key=lambda x: -float(x["_score"]),
    )
    for item in rest:
        _add(item)

    return merged


def preview_words(preview: list[dict[str, Any]]) -> list[str]:
    return [str(p.get("word") or "") for p in preview]


def preview_words_for_lang(preview: list[dict[str, Any]], lang: str) -> list[str]:
    return [str(p.get("word") or "") for p in preview if p.get("language") == lang]
