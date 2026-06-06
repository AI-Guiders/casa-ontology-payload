#!/usr/bin/env python3
"""Subject dialogue bind — field + journal + remember + CEN blocks (ADR-0045)."""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from casa.domain.dialogue_turn import recent_dialogue
from casa.domain.subject_mode import subject_display_name
from casa.prisms.control.fpn_state import WorkingMemory
from casa.prisms.control.sn_cen_runtime import AnswerBlock, TaskEmit
from casa.prisms.memory.agent_journal import search_journal_entries
from casa.prisms.memory.agent_memory_ops import agent_recall
from casa.prisms.memory.memory_prisms import memory_lattices
from casa.prisms.tick.articulation_realize import build_plan


@dataclass
class SubjectDialogueContext:
    display_name: str
    field_version: int
    wm: WorkingMemory
    blocks: list[dict[str, Any]] = field(default_factory=list)
    source_tags: list[str] = field(default_factory=list)
    stance: str = "partial"  # confident | partial | unknown
    query_intent: str = "general"
    query_locales: list[str] = field(default_factory=list)
    concept_hints: list[str] = field(default_factory=list)

    @property
    def top_concept_ids(self) -> list[str]:
        out: list[str] = []
        for b in self.blocks:
            cid = str(b.get("concept_id") or "")
            if cid and cid not in out:
                out.append(cid)
        return out[:8]


def _tokenize(text: str) -> list[str]:
    return [w.lower() for w in re.findall(r"[\w\u0400-\u04FF]+", text, flags=re.UNICODE) if len(w) > 2]


def _score_text(query: str, text: str, *, base: int = 0) -> int:
    score = base
    tl = text.lower()
    for tok in _tokenize(query):
        if tok in tl:
            score += 4
    return score


def _block_dict(
    concept_id: str,
    text: str,
    *,
    source: str,
    score: int = 10,
    section: str = "",
) -> dict[str, Any]:
    t = str(text or "").strip()
    return {
        "concept_id": concept_id,
        "text": t,
        "section": section or source,
        "doc_path": source,
        "score": score,
        "source": source,
    }


def _answer_block_to_dict(b: AnswerBlock | dict[str, Any]) -> dict[str, Any]:
    if isinstance(b, dict):
        return dict(b)
    return _block_dict(
        str(b.concept_id),
        str(b.text),
        source="cen",
        score=int(b.score),
        section=str(b.section or "cen"),
    )


def _social_query(query: str) -> str | None:
    ql = query.strip().lower()
    if any(x in ql for x in ("привет", "здравствуй", "добрый день", "добрый вечер", "hello", "hi", "здарова")):
        return "greeting"
    if any(x in ql for x in ("как дела", "how are you")):
        return "how_are_you"
    if any(x in ql for x in ("что умеешь", "кто ты", "как ты", "who are you")):
        return "intro"
    return None


def _journal_skip_on_social(row: dict[str, Any], social: str | None) -> bool:
    if not social:
        return False
    kind = str(row.get("kind") or "")
    tags = [str(t) for t in (row.get("tags") or [])]
    if kind == "observation" and any(t.startswith("cue:") or t == "surprise" for t in tags):
        return True
    if kind == "hypothesis" and social:
        return True
    return False


def _journal_confirmed_blocks(store_dir: Path, query: str, *, intent: str) -> list[dict[str, Any]]:
    """Field-mastery-first: confirmed hypotheses beat transport-only KB."""
    blocks: list[dict[str, Any]] = []
    seen: set[str] = set()
    ql = query.lower()
    for row in search_journal_entries(store_dir, domain="self", limit=80):
        meta = row.get("meta") if isinstance(row.get("meta"), dict) else {}
        if str(meta.get("status") or "") != "confirmed":
            continue
        eid = str(row.get("id") or "")
        text = str(row.get("text") or "").strip()
        if not text or eid in seen:
            continue
        cues = [str(c) for c in (meta.get("test_cues") or [])]
        concepts = [str(c) for c in (row.get("concepts") or [])]
        matched = any(cue.lower() in ql or ql in cue.lower() for cue in cues if cue)
        if not matched and intent == "math":
            matched = any(tok in ql for tok in cues if tok and len(tok) <= len(ql) + 2)
        if not matched:
            continue
        seen.add(eid)
        cid = concepts[0] if concepts else f"agent.self.journal.{eid}"
        base = 34 if intent == "math" else 28
        blocks.append(
            _block_dict(
                cid,
                text,
                source="journal",
                score=_score_text(query, text, base=base),
                section="confirmed",
            )
        )
    return blocks


def _journal_cap_for_intent(intent: str) -> int:
    if intent == "social":
        return 24
    if intent == "math":
        return 10
    if intent == "grammar":
        return 8
    return 14


def _journal_identity_blocks(
    store_dir: Path,
    query: str,
    *,
    social: str | None,
    intent: str,
) -> list[dict[str, Any]]:
    blocks: list[dict[str, Any]] = []
    seen_rows: dict[str, dict[str, Any]] = {}
    for tag in ("bootstrap", "wake", "notebook:self"):
        for row in search_journal_entries(store_dir, tags=[tag], limit=6):
            eid = str(row.get("id") or "")
            if eid and eid not in seen_rows:
                seen_rows[eid] = row
    if not seen_rows:
        for row in search_journal_entries(store_dir, domain="self", limit=10):
            eid = str(row.get("id") or "")
            if eid:
                seen_rows[eid] = row
    recall = agent_recall(store_dir, query=query, limit=6)
    seen: set[str] = set()
    cap = _journal_cap_for_intent(intent)
    for hit in recall.get("entries") or []:
        eid = str(hit.get("id") or "")
        text = str(hit.get("text") or "").strip()
        if not text or eid in seen:
            continue
        if _journal_skip_on_social(hit, social):
            continue
        seen.add(eid)
        blocks.append(
            _block_dict(
                f"agent.self.journal.{eid}",
                text,
                source="journal",
                score=min(cap, _score_text(query, text, base=14 if social else 8)),
            )
        )
    for row in seen_rows.values():
        eid = str(row.get("id") or "")
        text = str(row.get("text") or "").strip()
        if not text or eid in seen:
            continue
        if _journal_skip_on_social(row, social):
            continue
        if row.get("kind") == "hypothesis" and social:
            continue
        seen.add(eid)
        row_tags = [str(t) for t in (row.get("tags") or [])]
        base = min(cap, 18 if "bootstrap" in row_tags else 12)
        if social == "greeting" and any(t in row_tags for t in ("wake", "bootstrap")):
            base += 6
        blocks.append(
            _block_dict(
                f"agent.self.journal.{eid}",
                text,
                source="journal",
                score=_score_text(query, text, base=base),
            )
        )
    return blocks


def _field_snapshot_block(state: dict, wm: WorkingMemory) -> dict[str, Any]:
    fv = int(state.get("field_version") or 0)
    goal = (wm.goal_id or wm.goal or "").strip()
    active = ""
    mem = memory_lattices(state)
    if mem:
        from casa.domain.prism_wire import prism_memory

        active = str(prism_memory(state).get("active_lattice") or next(iter(mem.keys()), ""))
    parts = [f"field_version {fv}", f"tick {wm.tick}"]
    if goal:
        parts.append(f"goal {goal[:80]}")
    if active:
        parts.append(f"active_lattice {active}")
    return _block_dict(
        "subject.field.snapshot",
        "; ".join(parts) + ".",
        source="field",
        score=9,
    )


def _capability_block(state: dict, wm: WorkingMemory, task: TaskEmit | None) -> dict[str, Any]:
    caps: list[str] = []
    subject = state.get("subject")
    if isinstance(subject, dict):
        disp = subject.get("last_disposition")
        if isinstance(disp, dict) and disp.get("action"):
            caps.append(f"agency:{disp['action']}")
    if wm.step_capability:
        caps.append(str(wm.step_capability))
    if task and task.concepts:
        caps.extend(str(c) for c in task.concepts[:3] if not str(c).startswith("module:"))
    if not caps:
        caps = ["literacy RU/EN", "dialogue", "autonomy", "field memory"]
    return _block_dict(
        "subject.self.capability",
        "На поле веду: " + ", ".join(dict.fromkeys(caps)) + ".",
        source="field",
        score=11,
    )


def _dialogue_continuity_blocks(store_dir: Path | None, query: str) -> list[dict[str, Any]]:
    if store_dir is None:
        return []
    blocks: list[dict[str, Any]] = []
    for turn in recent_dialogue(store_dir, limit=6):
        if turn.speaker == "partner":
            blocks.append(
                _block_dict(
                    "subject.dialog.partner_recent",
                    f"Партнёр недавно: «{turn.text[:120]}».",
                    source="dialogue",
                    score=_score_text(query, turn.text, base=6),
                )
            )
        elif turn.speaker == "subject" and turn.kind in ("reply", "initiate"):
            blocks.append(
                _block_dict(
                    "subject.dialog.self_recent",
                    f"Я недавно: «{turn.text[:100]}».",
                    source="dialogue",
                    score=4,
                )
            )
    return blocks


def _infer_stance(blocks: list[dict[str, Any]], *, task: TaskEmit | None, intent: str) -> str:
    if not blocks:
        return "unknown"
    top = max(int(b.get("score") or 0) for b in blocks)
    has_kb = any(str(b.get("source")) == "kb" for b in blocks)
    has_journal = any(str(b.get("source")) == "journal" for b in blocks)
    has_cen = bool(task and task.answer_blocks)
    if intent == "math" and has_kb and top >= 18:
        return "confident"
    if intent == "social" and has_kb and top >= 20:
        return "confident"
    if intent == "grammar" and has_kb and top >= 18:
        return "confident"
    if top >= 16 and (has_journal or has_cen or has_kb):
        return "confident"
    if top >= 8 or has_journal or has_kb:
        return "partial"
    return "unknown"


def gather_subject_dialogue_blocks(
    user_query: str,
    task: TaskEmit | None,
    state: dict,
    wm: WorkingMemory,
    store_dir: Path | None,
    *,
    bundle: dict[str, Any] | None = None,
) -> SubjectDialogueContext:
    """Collect utterance atoms: semantic read → KB, CEN, journal, field."""
    from casa.prisms.shared.store_bundles import load_store_bundles
    from casa.prisms.tick.semantic_read import classify_query_intent, route_kb_read

    q = (user_query or "").strip()
    name = subject_display_name(state, store_dir)
    intent = classify_query_intent(q)
    social = _social_query(q)
    blocks: list[dict[str, Any]] = []
    sources: list[str] = []

    merged_bundle = bundle
    if merged_bundle is None and store_dir is not None:
        merged_bundle = load_store_bundles(store_dir)

    query_read = route_kb_read(q, merged_bundle)

    for claim, score in query_read.kb_hits:
        cid = str(claim.get("concept_id") or "")
        text = str(claim.get("text") or "").strip()
        if not cid or not text:
            continue
        blocks.append(
            _block_dict(
                cid,
                text,
                source="kb",
                score=score,
                section=str(claim.get("_bundle_id") or claim.get("section") or "kb"),
            )
        )
    if query_read.kb_hits:
        sources.append("kb")
    elif query_read.concept_hints and intent == "math":
        for hint in query_read.concept_hints[:4]:
            blocks.append(
                _block_dict(hint, f"Surface hint → {hint}.", source="field", score=14)
            )
        sources.append("field")

    if task and task.answer_blocks:
        for b in task.answer_blocks:
            row = _answer_block_to_dict(b)
            row["score"] = int(row.get("score") or 0) + (4 if intent != "social" else 0)
            blocks.append(row)
        sources.append("cen")

    if store_dir is not None:
        store_dir = store_dir.resolve()
        confirmed = _journal_confirmed_blocks(store_dir, q, intent=intent)
        blocks.extend(confirmed)
        if confirmed:
            sources.append("journal")
        jblocks = _journal_identity_blocks(store_dir, q, social=social, intent=intent)
        blocks.extend(jblocks)
        if jblocks:
            sources.append("journal")
        blocks.extend(_dialogue_continuity_blocks(store_dir, q))
        if any(b.get("source") == "dialogue" for b in blocks):
            sources.append("dialogue")

    blocks.append(_field_snapshot_block(state, wm))
    sources.append("field")

    if social in ("intro", "greeting") or (task and task.concepts and intent == "social"):
        blocks.append(_capability_block(state, wm, task))
        sources.append("capability")

    if task and task.concepts:
        for i, cid in enumerate(task.concepts[:5]):
            if str(cid).startswith("module:"):
                continue
            base = 12 - i if intent in ("math", "grammar", "recall") else 7 - i
            blocks.append(
                _block_dict(
                    f"subject.digest.{cid}",
                    f"Digest: на поле {cid}.",
                    source="digest",
                    score=base,
                )
            )
        sources.append("digest")

    blocks.sort(key=lambda b: int(b.get("score") or 0), reverse=True)
    stance = _infer_stance(blocks, task=task, intent=intent)

    return SubjectDialogueContext(
        display_name=name,
        field_version=int(state.get("field_version") or 0),
        wm=wm,
        blocks=blocks,
        source_tags=list(dict.fromkeys(sources)),
        stance=stance,
        query_intent=intent,
        query_locales=query_read.locales,
        concept_hints=query_read.concept_hints,
    )


def build_subject_plan(
    user_query: str,
    ctx: SubjectDialogueContext,
) -> Any:
    """UtterancePlan from bound blocks + query (extends articulation_realize.build_plan)."""
    return build_plan(user_query, ctx.blocks)
