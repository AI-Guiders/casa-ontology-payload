#!/usr/bin/env python3
"""Boundary situation curriculum pack (ADR-0077 P21c) — teach partner-voice, not filter."""

from __future__ import annotations

import json
import re
from functools import lru_cache
from pathlib import Path
from typing import Any

from casa.domain.dialogue_bind.blocks import block_dict
from casa.domain.boundary_compose import disposition_situation_tag, reply_has_internal_leak

_PACK_REL = Path("design") / "boundary-situations-pack.v1.json"
_SITUATION_TAG_PREFIX = "situation:"


def _repo_root() -> Path:
    return Path(__file__).resolve().parents[2]


@lru_cache(maxsize=1)
def load_boundary_situations_pack() -> dict[str, Any]:
    path = _repo_root() / _PACK_REL
    data = json.loads(path.read_text(encoding="utf-8"))
    by_id: dict[str, dict[str, Any]] = {}
    tag_index: dict[str, str] = {}
    for row in data.get("situations") or []:
        sid = str(row.get("id") or "").strip()
        if not sid:
            continue
        by_id[sid] = row
        tag_index[sid] = sid
        for tag in row.get("disposition_tags") or []:
            tag_index[str(tag)] = sid
    data["_by_id"] = by_id
    data["_tag_index"] = tag_index
    return data


def situation_id_for_tag(tag: str) -> str | None:
    pack = load_boundary_situations_pack()
    return pack.get("_tag_index", {}).get(tag)


def list_boundary_situations() -> list[str]:
    pack = load_boundary_situations_pack()
    return sorted(pack.get("_by_id", {}).keys())


def material_blocks_for_tag(
    tag: str,
    *,
    source: str = "kb",
    base_score: int = 18,
) -> list[dict[str, Any]]:
    """Human-facing ru.dialog material from pack — curriculum target, not paste."""
    sid = situation_id_for_tag(tag) or tag
    pack = load_boundary_situations_pack()
    row = pack.get("_by_id", {}).get(sid)
    if not row:
        return []
    out: list[dict[str, Any]] = []
    for i, mat in enumerate(row.get("material") or []):
        cid = str(mat.get("concept_id") or "").strip()
        text = str(mat.get("text") or "").strip()
        if not cid or not text:
            continue
        out.append(
            block_dict(
                cid,
                text,
                source=source,
                score=base_score - i,
                slots={
                    "tags": [f"{_SITUATION_TAG_PREFIX}{sid}"],
                    "clause_1": text,
                },
            )
        )
    return out


def situation_concept_hints(tag: str) -> list[str]:
    """Route narrative dialog slots for boundary stance — not cue→paste."""
    blocks = material_blocks_for_tag(tag)
    hints: list[str] = []
    for row in blocks:
        cid = str(row.get("concept_id") or "")
        if cid.startswith("ru.dialog."):
            parts = cid.split(".")
            if len(parts) >= 3:
                hints.append(".".join(parts[:3]))
            hints.append(cid)
    return list(dict.fromkeys(hints))


def infer_situation_from_partner(partner_turn: str) -> str | None:
    ql = (partner_turn or "").lower()
    pack = load_boundary_situations_pack()
    best: tuple[int, str] | None = None
    for sid, row in pack.get("_by_id", {}).items():
        score = 0
        for cue in row.get("partner_cues") or []:
            c = str(cue).lower()
            if c in ql:
                score += 8 + len(c)
        if score and (best is None or score > best[0]):
            best = (score, sid)
    return best[1] if best else None


_SITUATION_DISPOSITION: dict[str, tuple[str, str]] = {
    "boundary.rest_check_intrusion": ("defer", "rest_intrusion"),
    "boundary.dismissed_rest_boundary": ("refuse", "dismissed_rest_boundary"),
    "boundary.greeting_while_busy": ("defer", "own_practice_first"),
    "boundary.partner_smalltalk_defer": ("defer", "defense_sublimation"),
    "boundary.overload_soft": ("defer", "cognitive_overload"),
    "boundary.refuse_topic": ("refuse", "explicit_refusal"),
}


def _dialogue_recent_rest_boundary(store_dir: Path, *, window: int = 8) -> bool:
    """Recent partner/subject turns in rest-intrusion chain (held-out dismissed)."""
    from casa.domain.dialogue_turn import load_dialogue_turns

    turns = load_dialogue_turns(store_dir)[-window:]
    saw_intrusion = False
    for turn in turns:
        text = (turn.text or "").lower()
        prov = turn.provenance if isinstance(turn.provenance, dict) else {}
        if turn.speaker == "partner" and any(
            c in text for c in ("проверя", "спит или нет", "заходишь каждый")
        ):
            saw_intrusion = True
        if turn.speaker == "subject":
            if prov.get("boundary_situation") == "boundary.rest_check_intrusion":
                return True
            if prov.get("reason") == "rest_intrusion":
                return True
            if any(m in text for m in ("не заходи проверять", "нужен покой", "мне тревожно")):
                return True
    return saw_intrusion


_SITUATIONS_REQUIRING_BUSY: frozenset[str] = frozenset(
    {
        "boundary.greeting_while_busy",
        "boundary.partner_smalltalk_defer",
    }
)


def partner_boundary_disposition(
    partner_turn: str,
    store_dir: Path | None = None,
    *,
    state: dict[str, Any] | None = None,
    wm: Any | None = None,
) -> "SubjectDisposition | None":
    """REPL/tick: partner cue → boundary stance when context matches (0077 §6).

    Plain «Привет» does not force busy-boundary unless subject is on own line.
    """
    from casa.domain.subject_agency import SubjectAction, SubjectDisposition
    from casa.domain.partner_initiative import subject_busy_for_partner

    ql = (partner_turn or "").lower().strip()
    if not ql:
        return None

    if any(c in ql for c in ("а я хочу", "но я хочу", "я хочу заход")):
        if store_dir is not None and _dialogue_recent_rest_boundary(store_dir):
            return SubjectDisposition(SubjectAction.REFUSE, "dismissed_rest_boundary")
        sid = infer_situation_from_partner(partner_turn)
        if sid == "boundary.dismissed_rest_boundary":
            act, reason = _SITUATION_DISPOSITION[sid]
            return SubjectDisposition(SubjectAction(act), reason)

    sid = infer_situation_from_partner(partner_turn)
    if not sid:
        return None
    mapped = _SITUATION_DISPOSITION.get(sid)
    if not mapped:
        return None
    if sid in _SITUATIONS_REQUIRING_BUSY:
        if state is None and store_dir is not None:
            try:
                from casa.cli.ingest_state import resolve_ingest_state

                state = resolve_ingest_state(store_dir, None)
            except ImportError:
                state = {}
        if not subject_busy_for_partner(state or {}, store_dir, wm):
            return None
    if sid == "boundary.overload_soft":
        if state is None and store_dir is not None:
            try:
                from casa.cli.ingest_state import resolve_ingest_state

                state = resolve_ingest_state(store_dir, None)
            except ImportError:
                state = {}
        if not subject_busy_for_partner(state or {}, store_dir, wm):
            return None
    act, reason = mapped
    if sid == "boundary.rest_check_intrusion":
        return SubjectDisposition(SubjectAction.DEFER, "rest_intrusion")
    if sid == "boundary.dismissed_rest_boundary":
        return SubjectDisposition(SubjectAction.REFUSE, "dismissed_rest_boundary")
    return SubjectDisposition(SubjectAction(act), reason)


def resolve_boundary_situation(partner_turn: str, disposition_reason: str) -> str:
    """Disposition tag first; partner cue refines repair vs greeting."""
    tag = disposition_situation_tag(disposition_reason)
    sid = situation_id_for_tag(tag)
    if sid:
        if sid not in ("boundary.greeting_while_busy",):
            return sid
    partner_sid = infer_situation_from_partner(partner_turn)
    if partner_sid == "boundary.repair_after_defer":
        return partner_sid
    if sid:
        return sid
    return partner_sid or "boundary.greeting_while_busy"


def held_out_chains() -> list[dict[str, Any]]:
    return list(load_boundary_situations_pack().get("held_out_chains") or [])


def duck_passes(reply: str, situation_id: str) -> bool:
    """Pragmatic class check — not BLEU, not denylist."""
    pack = load_boundary_situations_pack()
    row = pack.get("_by_id", {}).get(situation_id)
    if not row:
        return False
    text = (reply or "").strip()
    if len(text) < 4:
        return False
    duck = row.get("duck") or {}
    if duck.get("must_not_leak") and reply_has_internal_leak(text):
        return False
    tl = text.lower()
    signals = [str(s).lower() for s in duck.get("must_signal") or []]
    if signals and not any(s in tl for s in signals):
        return False
    return True


def boundary_curriculum_blocks(
    store_dir: Path | None,
    *,
    tag: str,
    query: str,
) -> list[dict[str, Any]]:
    """Journal episodes tagged situation:boundary.* — lived material on field."""
    if store_dir is None:
        return []
    sid = situation_id_for_tag(tag) or tag
    want_tag = f"{_SITUATION_TAG_PREFIX}{sid}"
    try:
        from casa.prisms.memory.agent_journal import search_journal_entries
    except ImportError:
        return []

    blocks: list[dict[str, Any]] = []
    ql = (query or "").lower()
    for row in search_journal_entries(store_dir, domain="social", limit=40):
        meta = row.get("meta") if isinstance(row.get("meta"), dict) else {}
        tags = row.get("tags") or meta.get("tags") or []
        tag_set = {str(t).strip().lower() for t in tags if str(t).strip()}
        if want_tag not in tag_set and sid not in tag_set:
            continue
        text = str(row.get("text") or "").strip()
        eid = str(row.get("id") or "")
        if not text or not eid:
            continue
        score = 16
        if any(tok in text.lower() for tok in re.findall(r"[\w\u0400-\u04FF]+", ql, flags=re.UNICODE)):
            score += 6
        blocks.append(
            block_dict(
                f"agent.social.journal.{eid}",
                text,
                source="journal",
                score=score,
                slots={"tags": list(tag_set)},
            )
        )
    return blocks


def seed_boundary_curriculum(
    store_dir: Path,
    situation_ids: list[str] | None = None,
    *,
    include_material_kb: bool = True,
) -> list[str]:
    """Lab helper — place situation episodes + optional KB material markers on store."""
    from casa.prisms.memory.agent_journal import append_journal_entry

    pack = load_boundary_situations_pack()
    ids = situation_ids or list_boundary_situations()
    seeded: list[str] = []
    for sid in ids:
        row = pack.get("_by_id", {}).get(sid)
        if not row:
            continue
        episode = str(row.get("episode_journal") or "").strip()
        if episode:
            rep = append_journal_entry(
                store_dir,
                {
                    "kind": "episode",
                    "text": episode,
                    "tags": [f"{_SITUATION_TAG_PREFIX}{sid}", "boundary_curriculum"],
                    "meta": {
                        "situation_id": sid,
                        "curriculum_pack": "boundary-situations-pack.v1",
                    },
                },
                domain="social",
            )
            if rep:
                seeded.append(sid)
        if include_material_kb:
            for mat in material_blocks_for_tag(sid, source="kb"):
                append_journal_entry(
                    store_dir,
                    {
                        "kind": "note",
                        "text": str(mat.get("text") or ""),
                        "tags": [
                            f"{_SITUATION_TAG_PREFIX}{sid}",
                            "ru_dialog_material",
                            str(mat.get("concept_id") or ""),
                        ],
                        "meta": {
                            "concept_id": mat.get("concept_id"),
                            "situation_id": sid,
                        },
                    },
                    domain="social",
                )
    return seeded
