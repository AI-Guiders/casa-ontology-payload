"""Speech-act hint reconciliation from bundle claim slots — not Python act tables."""

from __future__ import annotations

from typing import Any


def _split_pipe(raw: str) -> list[str]:
    return [p.strip() for p in str(raw or "").split("|") if p.strip()]


def _claim_slots_for_act(
    act: str | None,
    *,
    bundle: dict[str, Any] | None,
    blocks: list[dict[str, Any]] | None,
) -> dict[str, str]:
    if not act:
        return {}
    if blocks:
        for row in blocks:
            cid = str(row.get("concept_id") or "")
            if not cid.startswith("ru.speech_act.partner."):
                continue
            slots = row.get("slots") if isinstance(row.get("slots"), dict) else {}
            if str(slots.get("speech_act") or "") == act:
                return {str(k): str(v) for k, v in slots.items() if v is not None}
    if bundle:
        for claim in bundle.get("claims") or []:
            if not isinstance(claim, dict):
                continue
            slots = claim.get("slots") if isinstance(claim.get("slots"), dict) else {}
            if str(slots.get("speech_act") or "") == act:
                return {str(k): str(v) for k, v in slots.items() if v is not None}
    from casa.prisms.tick.partner_speech_act import partner_speech_act_claims

    for claim in partner_speech_act_claims(bundle):
        slots = claim.get("slots") if isinstance(claim.get("slots"), dict) else {}
        if str(slots.get("speech_act") or "") == act:
            return {str(k): str(v) for k, v in slots.items() if v is not None}
    return {}


def speech_act_route_hints(
    act: str | None,
    *,
    bundle: dict[str, Any] | None = None,
    blocks: list[dict[str, Any]] | None = None,
) -> list[str]:
    slots = _claim_slots_for_act(act, bundle=bundle, blocks=blocks)
    return _split_pipe(slots.get("route_hints") or "")


def speech_act_suppress_hints(
    act: str | None,
    *,
    bundle: dict[str, Any] | None = None,
    blocks: list[dict[str, Any]] | None = None,
) -> frozenset[str]:
    slots = _claim_slots_for_act(act, bundle=bundle, blocks=blocks)
    return frozenset(_split_pipe(slots.get("suppress_hints") or ""))


def reconcile_speech_act_hints(
    hints: list[str],
    act: str | None,
    *,
    query: str = "",
    bundle: dict[str, Any] | None = None,
) -> list[str]:
    """Drop stale percept/broad hints; prefer speech-act route_hints from bundle."""
    ql = (query or "").strip().lower()
    out: list[str] = []
    for hint in hints:
        if hint.startswith("percept.text_stream.word."):
            word = hint.rsplit(".", 1)[-1].lower()
            if ql and word not in ql:
                continue
        if hint.startswith("percept.") and ql:
            if not any(m in ql for m in ("про это", "про то", "продолж", "с этим", "контекст")):
                continue
        out.append(hint)

    suppress = speech_act_suppress_hints(act, bundle=bundle)
    if suppress:
        out = [h for h in out if h not in suppress and not any(h.startswith(s) for s in suppress)]

    if act:
        for hint in reversed(speech_act_route_hints(act, bundle=bundle)):
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
    suppress = speech_act_suppress_hints(speech_act, bundle=bundle)
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
