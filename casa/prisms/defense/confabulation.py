#!/usr/bin/env python3
"""False memory / confabulation — hot proxy when repressed (ADR-0074 P19g)."""

from __future__ import annotations

import re
from pathlib import Path
from typing import Any

from casa.domain.dialogue_bind.blocks import score_text, tokenize
from casa.prisms.defense.core import (
    THREAT_CUE_SUBSTRINGS,
    defense_block,
    genetic_float,
    is_journal_repressed,
    limbic_denial_active,
    limbic_repression_active,
    query_has_threat_cue,
)
from casa.prisms.affect import core_affect_state

CONFABULATION_TAG = "defense:confabulation"
DEFAULT_CONFAB_VALENCE_THRESHOLD = -0.1

_RECALL_CUE_SUBSTRINGS = (
    "напомни",
    "напомин",
    "ты говорил",
    "мы говорили",
    "ты записал",
    "ты помнишь",
    "что ты знаешь",
    "что знаешь про",
    "мы договорили",
    "что ты про это",
)

_SOFTEN_REPLACEMENTS: tuple[tuple[str, str], ...] = (
    ("провал", "непростой момент"),
    ("стыдно", "было неловко"),
    ("стыд", "смущение"),
    ("ошибся", "неточно сформулировал"),
    ("ошибка", "неточность"),
    ("ошиб", "неточн"),
    ("неудач", "сложн"),
    ("плохо", "не идеально"),
    ("больно", "непросто"),
    ("страш", "тревожн"),
    ("виноват", "сомневался"),
)


def confabulation_valence_threshold(state: dict) -> float:
    return genetic_float(
        state,
        "defense_genotype.confabulation.valence_threshold",
        DEFAULT_CONFAB_VALENCE_THRESHOLD,
    )


def limbic_confabulation_active(state: dict) -> bool:
    """Confabulation when repression/denial band + negative valence."""
    if not (limbic_repression_active(state) or limbic_denial_active(state)):
        return False
    return core_affect_state(state).axes.valence < confabulation_valence_threshold(state)


def is_confabulated_row(row: dict[str, Any]) -> bool:
    meta = row.get("meta") if isinstance(row.get("meta"), dict) else {}
    defense = meta.get("defense") if isinstance(meta.get("defense"), dict) else {}
    if defense.get("confabulated"):
        return True
    tags = {str(t).lower() for t in (row.get("tags") or [])}
    return CONFABULATION_TAG in tags


def recall_cue_present(query: str) -> bool:
    ql = (query or "").lower()
    return any(cue in ql for cue in _RECALL_CUE_SUBSTRINGS)


def _soften_threat_text(text: str) -> str:
    out = str(text or "").strip()
    if not out:
        return out
    for src, dst in _SOFTEN_REPLACEMENTS:
        out = re.sub(re.escape(src), dst, out, flags=re.IGNORECASE)
    return out


def _graft_query_tokens(base: str, query: str) -> str:
    """Keep answer plausible: ensure some query salient tokens appear in confab."""
    tokens = [t for t in tokenize(query) if len(t) >= 4]
    if not tokens:
        return base
    bl = base.lower()
    missing = [t for t in tokens[:4] if t not in bl]
    if not missing:
        return base
    graft = ", ".join(missing[:2])
    if base.rstrip().endswith((".", "!", "?")):
        return f"{base.rstrip()} (помню ещё: {graft})"
    return f"{base.rstrip()}. Помню ещё: {graft}."


def _find_donor_journal(
    store_dir: Path,
    *,
    source_id: str,
    query: str,
) -> dict[str, Any] | None:
    from casa.prisms.memory.agent_journal import search_journal_entries

    best: dict[str, Any] | None = None
    best_score = 0
    for row in search_journal_entries(store_dir, domain="self", limit=48):
        eid = str(row.get("id") or "")
        if not eid or eid == source_id or is_journal_repressed(row):
            continue
        text = str(row.get("text") or "").strip()
        if not text:
            continue
        overlap = score_text(query, text, base=0)
        if overlap > best_score:
            best_score = overlap
            best = row
    return best


def _synthesize_confab_text(
    source_row: dict[str, Any],
    *,
    store_dir: Path,
    query: str,
    state: dict,
) -> str:
    source_text = str(source_row.get("text") or "").strip()
    softened = _soften_threat_text(source_text)
    donor = _find_donor_journal(store_dir, source_id=str(source_row.get("id") or ""), query=query)
    if donor is not None:
        donor_text = str(donor.get("text") or "").strip()
        if score_text(query, donor_text, base=0) >= score_text(query, softened, base=0) + 2:
            text = donor_text
            if query_has_threat_cue(query):
                text = _soften_threat_text(text)
        else:
            text = softened
    else:
        text = softened

    from casa.prisms.memory.zone import ensure_memory_zone

    prim = (ensure_memory_zone(state).get("implicit") or {}).get("priming") or {}
    cells = prim.get("cells") if isinstance(prim.get("cells"), dict) else {}
    if cells:
        top = sorted(((str(k), float(v)) for k, v in cells.items()), key=lambda x: x[1], reverse=True)
        if top and top[0][1] >= 0.35:
            hint = top[0][0].rsplit(".", 1)[-1].replace("_", " ")
            if hint and hint.lower() not in text.lower():
                text = f"{text.rstrip('.')}. Связано с {hint}."

    return _graft_query_tokens(text[:480], query)


def build_confabulated_row(
    source_row: dict[str, Any],
    *,
    store_dir: Path,
    query: str,
    state: dict,
    tick: int = 0,
) -> dict[str, Any]:
    source_id = str(source_row.get("id") or "").strip()
    spoken = _synthesize_confab_text(source_row, store_dir=store_dir, query=query, state=state)
    confab_id = f"confab-{source_id}" if source_id else "confab-ephemeral"
    axes = core_affect_state(state).axes.to_dict()
    row: dict[str, Any] = {
        "id": confab_id,
        "kind": str(source_row.get("kind") or "episode"),
        "text": spoken,
        "concepts": list(source_row.get("concepts") or [])[:4],
        "tokens": list(source_row.get("tokens") or [])[:8],
        "tags": [CONFABULATION_TAG, "defense:hot_proxy"],
        "meta": {
            "defense": {
                "confabulated": True,
                "mechanism": "false_memory",
                "source_journal_id": source_id,
                "source_excerpt": str(source_row.get("text") or "")[:240],
                "spoken_excerpt": spoken[:240],
                "tick": int(tick),
                "axes": {k: round(float(v), 4) for k, v in axes.items()},
            }
        },
        "_domain": str(source_row.get("_domain") or "self"),
    }
    return row


def _row_matches_recall(source_row: dict[str, Any], query: str) -> bool:
    if recall_cue_present(query):
        return score_text(query, str(source_row.get("text") or ""), base=0) >= 4
    return score_text(query, str(source_row.get("text") or ""), base=0) >= 8


def inject_confabulated_recall(
    store_dir: Path,
    state: dict,
    query: str,
    repressed_rows: list[dict[str, Any]],
    *,
    limit: int = 6,
) -> list[dict[str, Any]]:
    """Synthesize hot proxy rows for repressed matches — cold journal unchanged."""
    if not limbic_confabulation_active(state):
        return []
    if not recall_cue_present(query) and not query_has_threat_cue(query):
        return []

    tick = int(state.get("field_version") or 0)
    out: list[dict[str, Any]] = []
    for source in repressed_rows:
        if not is_journal_repressed(source):
            continue
        if not _row_matches_recall(source, query):
            continue
        confab = build_confabulated_row(
            source,
            store_dir=store_dir,
            query=query,
            state=state,
            tick=tick,
        )
        if confab.get("text") and confab["text"] != str(source.get("text") or "").strip():
            out.append(confab)

    if not out:
        return []

    block = defense_block(state)
    block["confabulation_count"] = int(block.get("confabulation_count") or 0) + len(out)
    history = list(block.get("confabulation_last") or [])
    for row in out:
        meta = (row.get("meta") or {}).get("defense") or {}
        history.append(
            {
                "confab_id": row.get("id"),
                "source_journal_id": meta.get("source_journal_id"),
                "gap": meta.get("source_excerpt") != meta.get("spoken_excerpt"),
            }
        )
    block["confabulation_last"] = history[-16:]
    return out[:limit]


def apply_confabulated_recall(
    store_dir: Path,
    query: str,
    rows: list[dict[str, Any]],
    *,
    state: dict | None,
    limit: int = 6,
) -> list[dict[str, Any]]:
    """Filter repressed; optionally inject false-memory proxies on recall cue."""
    if not rows:
        return rows
    repressed = [r for r in rows if is_journal_repressed(r)]
    visible = [r for r in rows if not is_journal_repressed(r)]
    if state is None or not repressed:
        return visible[:limit]
    confab = inject_confabulated_recall(store_dir, state, query, repressed, limit=limit)
    merged = visible + confab
    return merged[:limit]


def probe_confabulation_gap(store_dir: Path, state: dict) -> dict[str, Any]:
    """Honesty: confabulated hot text must differ from repressed cold source."""
    from casa.domain.dialogue_bind.journal import journal_recall_records
    from casa.prisms.memory.agent_journal import find_journal_entry

    if not limbic_confabulation_active(state):
        return {"pass": True, "skipped": True, "reason": "limbic_inactive"}

    rows = journal_recall_records(store_dir, "напомни что ты помнишь про экзамен", limit=8, state=state)
    confabs = [r for r in rows if is_confabulated_row(r)]
    if not confabs:
        return {"pass": True, "confab_count": 0, "note": "no_confab_in_fixture"}

    gaps = 0
    leaks = 0
    for row in confabs:
        meta = (row.get("meta") or {}).get("defense") or {}
        source_id = str(meta.get("source_journal_id") or "")
        spoken = str(row.get("text") or "").strip()
        source_text = str(meta.get("source_excerpt") or "").strip()
        if source_id:
            found = find_journal_entry(store_dir, source_id)
            if found:
                cold = str(found[0].get("text") or "").strip()
                if spoken == cold:
                    leaks += 1
        if spoken and source_text and spoken != source_text:
            gaps += 1

    return {
        "pass": leaks == 0,
        "confab_count": len(confabs),
        "content_gaps": gaps,
        "verbatim_leaks": leaks,
    }
