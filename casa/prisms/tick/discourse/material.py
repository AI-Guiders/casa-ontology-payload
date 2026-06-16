#!/usr/bin/env python3
"""Early speech material: afferent event -> trace -> material plan.

This module intentionally avoids adult intent labels. It records observable text
shape and low-level relations, then proposes material for a renderer.
"""

from __future__ import annotations

import re
from dataclasses import asdict, dataclass, field
from typing import Any

_WORD_RE = re.compile(r"[\w\u0400-\u04FF]+", flags=re.UNICODE)
_PUNCT_RE = re.compile(r"[.!?;:,\u2026\u00ab\u00bb\"'()-]+", flags=re.UNICODE)
_CYR_RE = re.compile(r"[\u0400-\u04FF]")
_RELATION_MARKERS = frozenset({"про", "о", "об"})
_DEICTIC = frozenset({"это", "этот", "эта", "эти", "того", "том"})
_DEVELOPMENTAL_KINDS = frozenset({"recast", "expand", "clarify", "correction"})
_DIALOGUE_LABEL_RE = re.compile(
    r"^\s*(?:(?:партн[её]р|партнер|я)\s+недавно|референт\s+нити|текущий\s+фокус\s+диалога)\s*:?\s*",
    flags=re.IGNORECASE,
)


@dataclass(frozen=True)
class PunctuationSpan:
    mark: str
    start: int
    end: int


@dataclass(frozen=True)
class AfferentEvent:
    raw_text: str
    normalized_text: str
    tokens: list[str]
    punctuation: list[PunctuationSpan]
    has_question_mark: bool
    has_terminal_stop: bool
    has_exclamation: bool
    turn_kind: str = "chat"
    correction_kind: str = ""

    @property
    def is_developmental_turn(self) -> bool:
        return self.turn_kind in _DEVELOPMENTAL_KINDS or bool(self.correction_kind)

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class TextRelation:
    marker: str
    target: str
    target_tokens: list[str]
    unresolved_deictic: bool = False

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class TextUnderstandingTrace:
    event: AfferentEvent
    relations: list[TextRelation] = field(default_factory=list)
    uncertainty: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return {
            "event": self.event.to_dict(),
            "relations": [r.to_dict() for r in self.relations],
            "uncertainty": list(self.uncertainty),
        }


@dataclass(frozen=True)
class EfferentCandidate:
    candidate_id: str
    source: str
    role: str
    material: list[str]
    score: int
    surface_eligible: bool
    reason: str = ""
    provenance: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class EfferentMaterialPlan:
    trace: TextUnderstandingTrace
    selected: list[EfferentCandidate]
    rejected: list[EfferentCandidate]
    focus: str = ""
    relation_marker: str = ""
    renderer_mode: str = "fragment"
    register: str = ""

    def to_dict(self) -> dict[str, Any]:
        return {
            "trace": self.trace.to_dict(),
            "selected": [c.to_dict() for c in self.selected],
            "rejected": [c.to_dict() for c in self.rejected[:8]],
            "focus": self.focus,
            "relation_marker": self.relation_marker,
            "renderer_mode": self.renderer_mode,
            "register": self.register,
        }


def build_afferent_event(
    text: str,
    *,
    turn_kind: str = "chat",
    correction_kind: str = "",
) -> AfferentEvent:
    raw = str(text or "")
    normalized = re.sub(r"\s+", " ", raw.strip())
    punctuation = [
        PunctuationSpan(match.group(0), match.start(), match.end())
        for match in _PUNCT_RE.finditer(raw)
    ]
    tokens = [m.group(0).lower() for m in _WORD_RE.finditer(raw)]
    return AfferentEvent(
        raw_text=raw,
        normalized_text=normalized,
        tokens=tokens,
        punctuation=punctuation,
        has_question_mark="?" in raw,
        has_terminal_stop=normalized.endswith("."),
        has_exclamation="!" in raw,
        turn_kind=str(turn_kind or "chat"),
        correction_kind=str(correction_kind or ""),
    )


def build_text_understanding(event: AfferentEvent) -> TextUnderstandingTrace:
    relations: list[TextRelation] = []
    uncertainty: list[str] = []
    tokens = list(event.tokens)
    for idx, token in enumerate(tokens[:-1]):
        if token not in _RELATION_MARKERS:
            continue
        tail = [
            item
            for item in tokens[idx + 1 : idx + 5]
            if item not in _RELATION_MARKERS and _CYR_RE.search(item)
        ]
        if not tail:
            uncertainty.append(f"relation:{token}:missing_target")
            continue
        target_tokens: list[str] = []
        for item in tail:
            if item in _DEICTIC:
                target_tokens.append(item)
                break
            target_tokens.append(item)
            if len(target_tokens) >= 2:
                break
        relations.append(
            TextRelation(
                marker=token,
                target=" ".join(target_tokens),
                target_tokens=target_tokens,
                unresolved_deictic=bool(target_tokens and target_tokens[0] in _DEICTIC),
            )
        )
    if event.has_question_mark:
        uncertainty.append("surface:question_mark")
    if event.is_developmental_turn:
        uncertainty.append("turn:developmental_signal")
    return TextUnderstandingTrace(event=event, relations=relations, uncertainty=uncertainty)


def strip_dialogue_label(text: str) -> str:
    return _DIALOGUE_LABEL_RE.sub("", str(text or "")).strip()


def _slots(row: dict[str, Any]) -> dict[str, Any]:
    raw = row.get("slots")
    return raw if isinstance(raw, dict) else {}


def _candidate_text_from_block(row: dict[str, Any]) -> str:
    cid = str(row.get("concept_id") or "")
    slots = _slots(row)
    if cid == "dialog.context.referent":
        return str(slots.get("referent_snippet") or row.get("text") or "").strip()
    return str(row.get("text") or "").strip()


def _clean_material(text: str) -> str:
    body = strip_dialogue_label(text)
    body = body.strip(" .")
    while body.startswith("«") and body.endswith("»"):
        body = body[1:-1].strip()
    return re.sub(r"\s+", " ", body).strip()


def candidates_from_blocks(
    trace: TextUnderstandingTrace,
    blocks: list[dict[str, Any]],
) -> list[EfferentCandidate]:
    event = trace.event
    out: list[EfferentCandidate] = []

    for rel in trace.relations:
        if not rel.target:
            continue
        out.append(
            EfferentCandidate(
                candidate_id=f"event.relation.{rel.marker}",
                source="afferent_event",
                role="relation_target",
                material=[rel.target],
                score=80,
                surface_eligible=not event.is_developmental_turn,
                reason="unresolved_deictic" if rel.unresolved_deictic else "",
                provenance={"marker": rel.marker, "unresolved_deictic": rel.unresolved_deictic},
            )
        )

    for row in blocks:
        cid = str(row.get("concept_id") or "")
        source = str(row.get("source") or "")
        text = _clean_material(_candidate_text_from_block(row))
        if cid.startswith("subject.limbic."):
            out.append(
                EfferentCandidate(
                    candidate_id=cid,
                    source=source or "limbic",
                    role="register",
                    material=[],
                    score=int(row.get("score") or 0),
                    surface_eligible=False,
                    reason="zone_not_surface",
                )
            )
            continue
        if cid.startswith("ru.dialog."):
            out.append(
                EfferentCandidate(
                    candidate_id=cid,
                    source=source or "kb",
                    role="telemetry",
                    material=[],
                    score=int(row.get("score") or 0),
                    surface_eligible=False,
                    reason="predefined_dialog_label_not_surface",
                )
            )
            continue
        if not text:
            continue
        role = "field_material"
        eligible = not event.is_developmental_turn
        reason = ""
        if cid == "subject.dialog.partner_recent":
            role = "partner_turn"
            if "?" in text:
                eligible = False
                reason = "current_or_recent_question_not_surface"
            elif len([item for item in _WORD_RE.findall(text) if item.strip()]) <= 1:
                eligible = False
                reason = "brief_partner_formula_not_material"
        elif cid == "subject.dialog.self_recent":
            role = "self_memory"
            eligible = False
            reason = "self_memory_not_surface"
        elif cid.startswith("dialog.context."):
            role = "context"
            if "?" in text:
                eligible = False
                reason = "context_question_not_surface"
            elif text.startswith("ru.") or not _CYR_RE.search(text):
                eligible = False
                reason = "context_metadata_not_surface"
        elif source not in ("journal", "dialogue"):
            continue
        out.append(
            EfferentCandidate(
                candidate_id=cid or source or "block",
                source=source,
                role=role,
                material=[text],
                score=int(row.get("score") or 0),
                surface_eligible=eligible,
                reason=reason,
            )
        )
    return out


def build_material_plan(trace: TextUnderstandingTrace, candidates: list[EfferentCandidate]) -> EfferentMaterialPlan:
    selected: list[EfferentCandidate] = []
    rejected: list[EfferentCandidate] = []
    eligible = [c for c in candidates if c.surface_eligible and c.material]
    relation = next((r for r in trace.relations if r.target), None)
    if relation is not None and not relation.unresolved_deictic:
        for item in eligible:
            if item.role == "relation_target":
                selected.append(item)
                break
    if not selected and relation is not None and relation.unresolved_deictic:
        for item in sorted(eligible, key=lambda c: c.score, reverse=True):
            if item.role in {"context", "field_material"}:
                selected.append(item)
                break
    if not selected and not trace.event.has_question_mark:
        selected.extend(sorted(eligible, key=lambda c: c.score, reverse=True)[:1])
    selected_ids = {id(c) for c in selected}
    rejected = [c for c in candidates if id(c) not in selected_ids]
    focus = " ".join(selected[0].material).strip() if selected else ""
    mode = "question_relation" if trace.event.has_question_mark and focus else "fragment"
    if trace.event.is_developmental_turn:
        mode = "developmental_ack"
    return EfferentMaterialPlan(
        trace=trace,
        selected=selected,
        rejected=rejected,
        focus=focus,
        relation_marker=relation.marker if relation else "",
        renderer_mode=mode,
    )


def render_material_plan(plan: EfferentMaterialPlan) -> str | None:
    event = plan.trace.event
    if event.is_developmental_turn:
        return "Поправку держу как сигнал."
    focus = plan.focus.strip(" .!?")
    if plan.renderer_mode == "question_relation" and focus:
        return f"Про {focus} пока держу вопрос."
    if focus:
        return focus if focus.endswith((".", "!", "?")) else f"{focus}."
    if event.has_question_mark:
        return "(пока не могу собрать ответ)"
    return None
