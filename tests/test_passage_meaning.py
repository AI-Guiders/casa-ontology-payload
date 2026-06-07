#!/usr/bin/env python3
"""Meaning graph v0 — propositions, bind, compose behavior (ADR-0053)."""

from __future__ import annotations

import json
import tempfile
from pathlib import Path

from casa.domain.subject_articulation import compose_subject_utterance
from casa.domain.dialogue_bind import gather_subject_dialogue_blocks
from casa.prisms.control.fpn_state import WorkingMemory
from casa.prisms.memory.memory_prisms import ensure_prisms
from casa.prisms.tick.passage import (
    apply_journal_prior,
    extract_passage_meaning,
    proposition_bind_blocks,
)


_C2_QUERY = (
    "Официально: Уважаемые родители! Информируем вас о переносе родительского собрания "
    "на 15 марта в 18:00 в актовом зале школы №12.\n\n"
    "Перепиши это письмо в дружеский тон для чата родителей, сохрани все факты."
)

_C1_RC_QUERY = (
    "В последние годы всё чаще говорят о раннем старте второго языка. Одни педагоги настаивают, "
    "что мозг ребёнка гибче и освоение идёт естественно. Другие предупреждают: перегрузка в первом "
    "классе отнимает время у родного языка и математики. Автор не объявляет победителя, но склоняется "
    "к осторожности: сначала — прочная грамотность, потом — второй язык без спешки.\n\n"
    "Какую позицию занимает автор? Объясни своими словами, без дословного пересказа."
)

_C1_WP_QUERY = (
    "Напиши развёрнутое мнение: стоит ли детям начинать учить второй язык в школе с первого класса. "
    "Приведи аргументы за и против."
)


def _semantics_bundle() -> dict:
    path = (
        Path(__file__).resolve().parents[1]
        / "agents/von-neumann/bundles/kb-lang-ru-lexicon-semantics-v1.bundle.json"
    )
    return json.loads(path.read_text(encoding="utf-8"))


def test_c2_extracts_meeting_event() -> None:
    rows = extract_passage_meaning(_C2_QUERY, intent="rewrite", bundle=_semantics_bundle())
    cids = {r.concept_id for r in rows}
    assert "ru.prop.event.meeting_moved" in cids
    assert "ru.prop.constraint.preserve_facts" in cids
    assert "ru.prop.constraint.shift_register" in cids
    event = next(r for r in rows if r.concept_id == "ru.prop.event.meeting_moved")
    assert event.slots.get("time_date") == "15 марта"
    assert event.slots.get("time_clock") == "18:00"


def test_c1_rc_extracts_author_stance() -> None:
    rows = extract_passage_meaning(_C1_RC_QUERY, intent="discuss", bundle=_semantics_bundle())
    cids = {r.concept_id for r in rows}
    assert "ru.prop.stance.author_cautious" in cids
    assert "ru.prop.argument.for" in cids
    assert "ru.prop.argument.against" in cids


def test_c1_wp_extracts_pro_con_task() -> None:
    rows = extract_passage_meaning(_C1_WP_QUERY, intent="discuss", bundle=_semantics_bundle())
    cids = {r.concept_id for r in rows}
    assert "ru.prop.task.pro_con" in cids
    assert "ru.prop.topic.second_language_school" in cids


def test_bind_includes_prop_blocks() -> None:
    blocks = proposition_bind_blocks(_C2_QUERY, intent="rewrite", bundle=_semantics_bundle())
    assert any(b["concept_id"].startswith("ru.prop.") for b in blocks)


def test_meaning_from_semantics_kb_bundle() -> None:
    rows = extract_passage_meaning(_C1_RC_QUERY, intent="discuss", bundle=_semantics_bundle())
    cids = {r.concept_id for r in rows}
    assert "ru.prop.stance.author_cautious" in cids
    assert "ru.prop.inference.praise_for_showing" not in cids


def test_journal_prior_boosts_overlap(tmp_path) -> None:
    from casa.domain.dialogue_turn import append_partner_turn
    from casa.prisms.memory.memory_prisms import ensure_prisms

    store = tmp_path / "agent"
    store.mkdir()
    (store / "bundles").mkdir()
    append_partner_turn(
        store,
        _B1_INFERENCE_QUERY,
        provenance={"query_intent": "discuss", "prop_ids": ["ru.prop.inference.praise_for_showing"]},
    )
    rows = extract_passage_meaning(
        _B1_INFERENCE_QUERY, intent="discuss", bundle=_semantics_bundle(), store_dir=store
    )
    before = next(r for r in rows if r.concept_id == "ru.prop.inference.praise_for_showing").score
    apply_journal_prior(rows, store_dir=store, query=_B1_INFERENCE_QUERY)
    after = next(r for r in rows if r.concept_id == "ru.prop.inference.praise_for_showing").score
    assert after > before


def _store() -> Path:
    tmp = Path(tempfile.mkdtemp(prefix="casa-meaning-"))
    (tmp / "store_profile.json").write_text(
        json.dumps({"subject_mode": True, "display_name": "Нейманн"}, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )
    return tmp


def test_rewrite_from_props_preserves_facts() -> None:
    store = _store()
    (store / "bundles").mkdir(exist_ok=True)
    sem = _semantics_bundle()
    (store / "bundles" / "kb-lang-ru-lexicon-semantics-v1.bundle.json").write_text(
        json.dumps(sem, ensure_ascii=False), encoding="utf-8"
    )
    state = ensure_prisms({"schema_version": "multi_prism_v1", "field_version": 0})
    ctx = gather_subject_dialogue_blocks(
        _C2_QUERY, None, state, WorkingMemory(), store, bundle=None
    )
    assert ctx.query_intent == "rewrite"
    prop_blocks = [b for b in ctx.blocks if str(b.get("concept_id", "")).startswith("ru.prop.")]
    assert prop_blocks
    reply = compose_subject_utterance(_C2_QUERY, ctx)
    rl = reply.lower()
    assert reply
    assert "15 марта" in rl
    assert "18:00" in rl
    assert "собран" in rl
    assert "информируем вас" not in rl


def test_discuss_author_stance_not_paste() -> None:
    store = _store()
    (store / "bundles").mkdir(exist_ok=True)
    (store / "bundles" / "kb-lang-ru-lexicon-semantics-v1.bundle.json").write_text(
        json.dumps(_semantics_bundle(), ensure_ascii=False), encoding="utf-8"
    )
    state = ensure_prisms({"schema_version": "multi_prism_v1", "field_version": 0})
    ctx = gather_subject_dialogue_blocks(
        _C1_RC_QUERY, None, state, WorkingMemory(), store, bundle=None
    )
    assert ctx.query_intent == "discuss"
    reply = compose_subject_utterance(_C1_RC_QUERY, ctx)
    rl = reply.lower()
    assert reply
    assert any(m in rl for m in ("осторож", "грамотност", "без спешки", "автор"))
    assert "склоняется к осторожности: сначала — прочная грамотность" not in rl


_B1_INFERENCE_QUERY = (
    "Папа вернулся домой. Маша показала апельсин. Папа сказал: «Молодец!»\n\n"
    "Почему папа сказал «Молодец»?"
)


_QUOTE_FACT_QUERY = (
    "Папа сказал: «Молодец, Маша!» Маша показала апельсин.\n\nЧто сказал папа?"
)


def test_quote_fact_not_inference() -> None:
    rows = extract_passage_meaning(_QUOTE_FACT_QUERY, intent="discuss", bundle=_semantics_bundle())
    cids = {r.concept_id for r in rows}
    assert "ru.prop.fact.quoted_speech" in cids
    assert "ru.prop.inference.praise_for_showing" not in cids


def test_b1_inference_extracts_cause() -> None:
    rows = extract_passage_meaning(_B1_INFERENCE_QUERY, intent="discuss", bundle=_semantics_bundle())
    cids = {r.concept_id for r in rows}
    assert "ru.prop.inference.praise_for_showing" in cids
    assert "ru.prop.fact.quoted_speech" not in cids


def test_b1_inference_reply_not_quote_only() -> None:
    store = _store()
    (store / "bundles").mkdir(exist_ok=True)
    (store / "bundles" / "kb-lang-ru-lexicon-semantics-v1.bundle.json").write_text(
        json.dumps(_semantics_bundle(), ensure_ascii=False), encoding="utf-8"
    )
    state = ensure_prisms({"schema_version": "multi_prism_v1", "field_version": 0})
    ctx = gather_subject_dialogue_blocks(
        _B1_INFERENCE_QUERY, None, state, WorkingMemory(), store, bundle=None
    )
    reply = compose_subject_utterance(_B1_INFERENCE_QUERY, ctx)
    rl = reply.lower()
    assert reply
    assert "апельсин" in rl
    assert any(m in rl for m in ("похоже", "потому", "видимо", "показал"))
    assert rl.strip() != "молодец."


def test_pro_con_structure_in_reply() -> None:
    store = _store()
    (store / "bundles").mkdir(exist_ok=True)
    (store / "bundles" / "kb-lang-ru-lexicon-semantics-v1.bundle.json").write_text(
        json.dumps(_semantics_bundle(), ensure_ascii=False), encoding="utf-8"
    )
    state = ensure_prisms({"schema_version": "multi_prism_v1", "field_version": 0})
    ctx = gather_subject_dialogue_blocks(
        _C1_WP_QUERY, None, state, WorkingMemory(), store, bundle=None
    )
    reply = compose_subject_utterance(_C1_WP_QUERY, ctx)
    rl = reply.lower()
    assert reply
    assert len(reply.split(".")) >= 3 or "сторон" in rl
    assert any(m in rl for m in ("язык", "школ", "класс", "дет"))
