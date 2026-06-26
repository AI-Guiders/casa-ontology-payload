#!/usr/bin/env python3
"""Subject phrase compose — builds surface from slots, not claim paste."""

from __future__ import annotations

from casa.domain.subject_articulation import compose_subject_utterance
from casa.domain.dialogue_bind import SubjectDialogueContext, gather_subject_dialogue_blocks
from casa.prisms.control.fpn_state import WorkingMemory
from casa.prisms.tick.phrase_compose import discourse_budget_from_blocks, paste_ratio_against_blocks


def _ctx(query: str, blocks: list[dict]) -> SubjectDialogueContext:
    return SubjectDialogueContext(
        display_name="Нейманн",
        field_version=1,
        wm=WorkingMemory(),
        blocks=sorted(blocks, key=lambda b: int(b.get("score") or 0), reverse=True),
        source_tags=["kb"],
        stance="confident",
        query_intent="social",
    )


def test_thanks_composes_response_from_slots() -> None:
    claim = "«Спасибо» — благодарность; «пожалуйста» — ответ на спасибо или просьба."
    blocks = [
        {
            "concept_id": "agent.self.journal.boot",
            "text": "Я — Нейманн. Это мой журнал (Self tier).",
            "source": "journal",
            "score": 30,
        },
        {
            "concept_id": "ru.dialog.thanks",
            "text": claim,
            "source": "kb",
            "score": 40,
            "slots": {"stimulus": "спасибо", "response": "пожалуйста"},
        },
    ]
    reply = compose_subject_utterance("Спасибо за помощь", _ctx("Спасибо за помощь", blocks))
    low = reply.lower()
    assert "пожалуйста" in low
    assert "это мой журнал" not in low
    assert claim.lower() not in low
    assert paste_ratio_against_blocks(reply, blocks) < 0.35


def test_greeting_composes_surface_from_slots() -> None:
    blocks = [
        {
            "concept_id": "ru.dialog.greeting",
            "text": "«Привет» — неформальное приветствие при встрече знакомых.",
            "source": "kb",
            "score": 40,
            "slots": {"surface": "привет"},
        },
    ]
    reply = compose_subject_utterance("Привет!", _ctx("Привет!", blocks))
    assert "привет" in reply.lower()
    assert "неформальное приветствие" not in reply.lower()


def test_thanks_builds_connected_discourse() -> None:
    blocks = [
        {
            "concept_id": "ru.dialog.thanks",
            "text": "«Спасибо» — благодарность; «пожалуйста» — ответ.",
            "source": "kb",
            "score": 40,
            "slots": {
                "stimulus": "спасибо",
                "response": "пожалуйста",
            },
        },
    ]
    q = "Спасибо за помощь — это было очень важно для меня сегодня"
    reply = compose_subject_utterance(q, _ctx(q, blocks))
    low = reply.lower()
    assert "пожалуйста" in low
    assert "обращайся" not in low


def test_grammar_builds_multi_sentence_discourse() -> None:
    ctx = SubjectDialogueContext(
        display_name="Нейманн",
        field_version=1,
        wm=WorkingMemory(),
        blocks=[
            {
                "concept_id": "ru.grammar.punct.comma",
                "text": "Правильно: запятая перед придаточным с «что»: «Я знаю, что он придёт».",
                "source": "kb",
                "score": 40,
            }
        ],
        source_tags=["kb"],
        stance="confident",
        query_intent="grammar",
    )
    reply = compose_subject_utterance(
        "Нужна ли запятая в «я знаю что он придёт»?",
        ctx,
    )
    low = reply.lower()
    assert "запят" in low
    assert "я знаю" in low


def test_confident_stance_includes_more_clauses_than_unknown() -> None:
    blocks = [
        {
            "concept_id": "ru.dialog.thanks",
            "text": "x",
            "source": "kb",
            "score": 40,
            "slots": {"stimulus": "спасибо", "response": "пожалуйста"},
        },
        {
            "concept_id": "ru.grammar.punct.comma",
            "text": "Правильно: запятая перед «что».",
            "source": "kb",
            "score": 22,
        },
        {
            "concept_id": "lang.word.мама",
            "text": "«мама»",
            "source": "kb",
            "score": 12,
            "slots": {"word": "мама"},
        },
    ]
    q = "Спасибо за помощь с задачей, это правда выручило меня"
    confident = compose_subject_utterance(
        q,
        SubjectDialogueContext(
            display_name="Н",
            field_version=1,
            wm=WorkingMemory(),
            blocks=blocks,
            source_tags=["kb"],
            stance="confident",
            query_intent="social",
        ),
    )
    unknown = compose_subject_utterance(
        q,
        SubjectDialogueContext(
            display_name="Н",
            field_version=1,
            wm=WorkingMemory(),
            blocks=blocks,
            source_tags=["kb"],
            stance="unknown",
            query_intent="social",
        ),
    )
    assert len(confident) >= len(unknown)
    assert discourse_budget_from_blocks(blocks, stance="confident").score_floor < (
        discourse_budget_from_blocks(blocks, stance="unknown").score_floor
    )


def test_brief_greeting_is_surface_only() -> None:
    blocks = [
        {
            "concept_id": "ru.dialog.greeting",
            "text": "x",
            "source": "kb",
            "score": 50,
            "slots": {
                "surface": "привет",
                "clause_2": "рад слышать",
                "clause_3": "продолжим когда захочешь",
                "linker_2": "и",
                "linker_3": "и",
            },
        },
    ]
    reply = compose_subject_utterance("Привет!", _ctx("Привет!", blocks)).lower()
    assert reply.strip() in {"привет.", "привет!"}


def test_extended_greeting_surface_only_on_long_cue() -> None:
    blocks = [
        {
            "concept_id": "ru.dialog.greeting",
            "text": "x",
            "source": "kb",
            "score": 50,
            "slots": {
                "surface": "привет",
                "clause_2": "рад слышать",
                "clause_3": "продолжим когда захочешь",
                "linker_2": "и",
                "linker_3": "и",
            },
        },
    ]
    q = "Привет, давно не виделись, рад что ты написал снова"
    reply = compose_subject_utterance(q, _ctx(q, blocks)).lower()
    assert "привет" in reply
    assert "рад слышать" not in reply


def test_self_narrative_from_journal_not_script_slots() -> None:
    blocks = [
        {
            "concept_id": "agent.self.journal.note",
            "text": "Я Нейманн — субъект на поле. Говорю из bind и журнала.",
            "source": "journal",
            "score": 48,
        },
        {
            "concept_id": "ru.dialog.self",
            "text": "meta",
            "source": "kb",
            "score": 52,
            "slots": {"situation": "partner_asks_identity"},
        },
    ]
    reply = compose_subject_utterance(
        "Кто ты? Расскажи о себе.",
        SubjectDialogueContext(
            display_name="Нейманн",
            field_version=1,
            wm=WorkingMemory(),
            blocks=blocks,
            source_tags=["kb", "journal"],
            stance="confident",
            query_intent="social",
            concept_hints=["ru.dialog.self"],
        ),
    ).lower()
    assert "нейманн" in reply
    assert "поле" in reply or "журнал" in reply
    assert "говорю из bind" not in reply


def test_explain_privet_compose() -> None:
    blocks = [
        {
            "concept_id": "lang.word.привет",
            "text": "«привет» — приветствие.",
            "source": "kb",
            "score": 40,
            "slots": {"word": "привет"},
        },
        {
            "concept_id": "ru.dialog.greeting",
            "text": "«Привет» — неформальное приветствие.",
            "source": "kb",
            "score": 35,
            "slots": {"surface": "привет"},
        },
    ]
    reply = compose_subject_utterance(
        "Объясни, что такое «привет».",
        SubjectDialogueContext(
            display_name="Н",
            field_version=1,
            wm=WorkingMemory(),
            blocks=blocks,
            source_tags=["kb"],
            stance="confident",
            query_intent="explain",
        ),
    ).lower()
    assert "привет" in reply
    assert "—" in reply or "приветств" in reply
    assert "опираюсь" not in reply


def test_gather_passes_slots_and_prefers_dialog(tmp_path) -> None:
    from casa.prisms.memory.memory_prisms import ensure_prisms

    store = tmp_path / "agent"
    store.mkdir()
    journal = store / "journal" / "self"
    journal.mkdir(parents=True)
    (journal / "entries.jsonl").write_text(
        '{"id":"boot1","kind":"note","text":"Я — Нейманн. Это мой журнал.","tags":["bootstrap"]}\n',
        encoding="utf-8",
    )
    bundle = {
        "claims": [
            {
                "concept_id": "ru.dialog.thanks",
                "text": "«Спасибо» — благодарность; «пожалуйста» — ответ.",
                "slots": {"stimulus": "спасибо", "response": "пожалуйста"},
            },
            {
                "concept_id": "lang.word.спасибо",
                "text": "«спасибо» — благодарность.",
                "slots": {"word": "спасибо"},
            },
        ]
    }
    state = ensure_prisms({"schema_version": "multi_prism_v1", "field_version": 0})
    ctx = gather_subject_dialogue_blocks(
        "Спасибо",
        None,
        state,
        WorkingMemory(),
        store,
        bundle=bundle,
    )
    top = str(ctx.blocks[0].get("concept_id") or "")
    assert top.startswith("ru.dialog.")
    dialog = next(b for b in ctx.blocks if b.get("concept_id") == "ru.dialog.thanks")
    assert dialog.get("slots", {}).get("response") == "пожалуйста"
