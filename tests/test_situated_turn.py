#!/usr/bin/env python3

"""Situated turn — partner mirror must not replay prior affect preamble."""



from __future__ import annotations



from casa.domain.dialogue_bind import SubjectDialogueContext

from casa.domain.subject_articulation import compose_subject_utterance

from casa.prisms.control.fpn_state import WorkingMemory





def _ctx(query: str, blocks: list[dict]) -> SubjectDialogueContext:

    return SubjectDialogueContext(

        display_name="Нейманн",

        field_version=1,

        wm=WorkingMemory(),

        blocks=sorted(blocks, key=lambda b: int(b.get("score") or 0), reverse=True),

        source_tags=["kb", "dialogue"],

        stance="partial",

        query_intent="social",

        concept_hints=["ru.dialog.self"],

    )





def test_partner_mirror_does_not_replay_affect_preamble() -> None:

    mirror = "Хорошо, я тоже не знаю, но он не обязан совпадать"

    prior_subject = "Осторожно говорю, что чувствую в диалоге."

    blocks = [

        {

            "concept_id": "ru.speech_act.partner.mirror_ack",

            "text": "mirror",

            "source": "speech_act",

            "score": 36,

            "slots": {"speech_act": "mirror_ack", "cue_score": 4},

        },

        {

            "concept_id": "ru.dialog.self",

            "text": "Self hub.",

            "source": "kb",

            "score": 58,

            "slots": {

                "situation": "mirror_ack",

                "hedge": "согласен",

                "predicate": "не знаю",

                "scope": "не обязан совпадать",

            },

        },

        {

            "concept_id": "subject.dialog.partner_recent",

            "text": f"Партнёр недавно: «{mirror}».",

            "source": "dialogue",

            "score": 44,

        },

        {

            "concept_id": "subject.dialog.self_recent",

            "text": f"Я недавно: «{prior_subject}».",

            "source": "dialogue",

            "score": 20,

        },

    ]

    reply = compose_subject_utterance(mirror, _ctx(mirror, blocks))

    low = reply.lower()



    assert "да —" not in low

    assert "осторожно говорю" not in low

    assert "не знаю" in low or "совпада" in low





def test_continuer_active_when_focus_recent_present() -> None:
    from casa.domain.dialogue_bind.partner_scoring import continuer_active, thread_continuer_turn

    blocks = [
        {
            "concept_id": "dialog.context.focus_recent",
            "text": "Текущий фокус диалога: ru.dialog.how_are_you.",
            "source": "dialogue",
            "score": 40,
        }
    ]
    assert continuer_active(blocks)
    assert thread_continuer_turn(blocks, "любая реплика")


def test_fresh_how_are_you_uses_situation_pieces_not_affect_script() -> None:

    query = "Как ты?"

    blocks = [

        {

            "concept_id": "ru.dialog.how_are_you",

            "text": "«Как дела?» — разговорный вопрос о самочувствии.",

            "source": "kb",

            "score": 50,

            "slots": {

                "situation": "partner_asks_state",

                "modifier": "сейчас",

                "surface": "на связи",

                "object_lemma": "с полем",

            },

        },

    ]

    reply = compose_subject_utterance(query, _ctx(query, blocks))

    low = reply.lower()

    assert "осторожно говорю" not in low

    assert "(пока не могу собрать ответ)" in low

