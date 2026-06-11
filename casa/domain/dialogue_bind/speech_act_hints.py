"""Speech act overrides surface routing hints — specific act wins over broad cue."""

from __future__ import annotations

from typing import Any

# Read-route targets when partner speech act is resolved (ADR-0057: situation, not cue→affect paste).
_ACT_ROUTE_HINTS: dict[str, tuple[str, ...]] = {
    "how_are_you": ("ru.dialog.how_are_you", "ru.dialog.self"),
    "greeting": ("ru.dialog.greeting",),
    "thanks": ("ru.dialog.thanks",),
    "farewell": ("ru.dialog.farewell",),
    "ask_thought": ("ru.dialog.self", "ru.dialog.honest."),
    "mirror_ack": ("ru.dialog.self", "subject.dialog.partner_recent"),
}

# Broad surface hints suppressed when a specific speech act is active.
_ACT_SUPPRESS_HINTS: dict[str, frozenset[str]] = {
    "how_are_you": frozenset({"ru.dialog.affect"}),
    "thanks": frozenset({"ru.dialog.affect", "ru.dialog.capabilities"}),
    "greeting": frozenset({"ru.dialog.affect"}),
}


def speech_act_route_hints(act: str | None) -> list[str]:
    if not act:
        return []
    return list(_ACT_ROUTE_HINTS.get(act, ()))


def reconcile_speech_act_hints(
    hints: list[str],
    act: str | None,
    *,
    query: str = "",
) -> list[str]:
    """Drop stale percept/broad hints; prefer speech-act dialog hubs."""
    ql = (query or "").strip().lower()
    out: list[str] = []
    for hint in hints:
        if hint.startswith("percept.text_stream.word."):
            word = hint.rsplit(".", 1)[-1].lower()
            if ql and word not in ql:
                continue
        if hint.startswith("percept.") and ql:
            # Drop percept line hints unless query is a continuer referencing prior stream.
            if not any(m in ql for m in ("про это", "про то", "продолж", "с этим", "контекст")):
                continue
        out.append(hint)

    suppress = _ACT_SUPPRESS_HINTS.get(act or "", frozenset())
    if suppress:
        out = [h for h in out if h not in suppress and not any(h.startswith(s) for s in suppress)]

    if act:
        for hint in reversed(speech_act_route_hints(act)):
            if hint not in out:
                out.insert(0, hint)

    return list(dict.fromkeys(out))


def refresh_kb_hits(
    query_read: Any,
    bundle: dict[str, Any] | None,
    *,
    speech_act: str | None,
) -> None:
    """Insert dialog hub claims for reconciled hints; drop hubs suppressed by speech act."""
    if not bundle:
        return
    by_id: dict[str, dict[str, Any]] = {
        str(c.get("concept_id") or ""): c
        for c in (bundle.get("claims") or [])
        if c.get("concept_id")
    }
    suppress = _ACT_SUPPRESS_HINTS.get(speech_act or "", frozenset())
    hits: list[tuple[dict[str, Any], int]] = []
    seen: set[str] = set()
    for hint in query_read.concept_hints or []:
        if hint in suppress:
            continue
        claim = by_id.get(hint)
        if not claim:
            continue
        cid = str(claim.get("concept_id") or "")
        if cid in seen:
            continue
        seen.add(cid)
        hits.append((claim, 34))
    for claim, score in query_read.kb_hits or []:
        cid = str(claim.get("concept_id") or "")
        if cid in seen:
            continue
        if suppress and (cid in suppress or any(cid.startswith(s) for s in suppress)):
            continue
        seen.add(cid)
        hits.append((claim, int(score)))
    hits.sort(key=lambda row: -row[1])
    query_read.kb_hits = hits[:8]
