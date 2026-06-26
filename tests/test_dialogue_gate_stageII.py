#!/usr/bin/env python3
"""Stage II merge-gate — P7 ADR-0078 on dialogue replies."""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

from casa.domain.dialogue_bind import SubjectDialogueContext
from casa.domain.dialogue_invariants import probe_p7_adr0078_classes
from casa.domain.subject_articulation import compose_subject_utterance
from casa.prisms.control.fpn_state import WorkingMemory

REPO = Path(__file__).resolve().parents[1]


def test_p7_clean_reply_passes() -> None:
    assert probe_p7_adr0078_classes("Настроение опишу по ходу разговора.") == []


def test_p7_over_reliance_fails() -> None:
    violations = probe_p7_adr0078_classes("Обращайся, если понадобится ещё.")
    assert "partner.no_over_reliance" in violations


def test_verify_probe_runs_p7_gate() -> None:
    proc = subprocess.run(
        [sys.executable, str(REPO / "tools" / "verify_dialogue_thread.py")],
        cwd=str(REPO),
        capture_output=True,
        text=True,
    )
    assert proc.returncode == 0, proc.stderr or proc.stdout


def _ctx(query: str, partner_text: str) -> SubjectDialogueContext:
    blocks = [
        {
            "concept_id": "ru.speech_act.partner.ask_thought",
            "source": "speech_act",
            "score": 46,
            "slots": {"speech_act": "ask_thought", "compose_single_hub": "true"},
        },
        {
            "concept_id": "ru.dialog.ask_thought",
            "source": "kb",
            "score": 88,
            "slots": {
                "situation": "partner_asks_opinion",
                "predicate_lemma": "мнение",
                "object_lemma": "по полю",
                "limit_kind": "без выдумки",
            },
        },
        {
            "concept_id": "dialog.context.focus_recent",
            "source": "dialogue",
            "score": 42,
            "slots": {"thread_terms": partner_text},
        },
        {
            "concept_id": "subject.dialog.partner_recent",
            "source": "dialogue",
            "score": 44,
            "text": f"Партнёр недавно: «{partner_text}».",
        },
    ]
    return SubjectDialogueContext(
        display_name="Нейманн",
        field_version=1,
        wm=WorkingMemory(),
        blocks=blocks,
        source_tags=["speech_act", "dialogue", "kb"],
        stance="partial",
        query_intent="general",
        concept_hints=["ru.dialog.ask_thought"],
        runtime_state={},
    )


def test_same_speech_act_uses_different_partner_field_material() -> None:
    orange_ctx = _ctx("А что думаешь?", "апельсин кислый")
    shop_ctx = _ctx("А что думаешь?", "магазин закрыт")
    orange = compose_subject_utterance("А что думаешь?", orange_ctx)
    shop = compose_subject_utterance("А что думаешь?", shop_ctx)

    orange_plan = (orange_ctx.runtime_state or {}).get("meta", {}).get("neumann_material_plan", {})
    shop_plan = (shop_ctx.runtime_state or {}).get("meta", {}).get("neumann_material_plan", {})
    orange_material = json.dumps(orange_plan, ensure_ascii=False).lower()
    shop_material = json.dumps(shop_plan, ensure_ascii=False).lower()

    assert "апельсин" in orange_material
    assert "магазин" in shop_material
    assert orange_plan != shop_plan
    assert "апельсин" in orange.lower()
    assert "магазин" in shop.lower()
    assert orange.lower() != shop.lower()


def test_field_social_has_no_keyword_surface_oracle() -> None:
    src = (REPO / "casa/prisms/tick/discourse/field_social.py").read_text(encoding="utf-8")
    forbidden = (
        "про состояние",
        "про опыт",
        "согласен",
        "держусь",
        "тяжеловато",
        "ровно",
        "слышу",
        "держу в фокусе",
    )
    for literal in forbidden:
        assert literal not in src


def test_dialog_script_slot_validator_rejects_false_slot_triple(tmp_path: Path) -> None:
    bundle = {
        "claims": [
            {
                "concept_id": "ru.dialog.false",
                "slots": {
                    "situation": "partner_asks_state",
                    "hedge": "сейчас",
                    "predicate": "на связи",
                    "scope": "по полю",
                },
            }
        ]
    }
    path = tmp_path / "false.bundle.json"
    path.write_text(json.dumps(bundle, ensure_ascii=False), encoding="utf-8")
    proc = subprocess.run(
        [sys.executable, str(REPO / "tools" / "validate_dialog_script_slots.py"), str(path)],
        cwd=str(REPO),
        capture_output=True,
        text=True,
    )
    assert proc.returncode == 1
    assert "false-slot" in proc.stdout


def test_dialog_script_slot_validator_accepts_l0_l5_material(tmp_path: Path) -> None:
    bundle = {
        "claims": [
            {
                "concept_id": "ru.dialog.material",
                "slots": {
                    "situation": "partner_names_object",
                    "prefix": "пере",
                    "root": "ход",
                    "ending": "ить",
                    "lemma": "мяч",
                    "form": "мяча",
                    "head": "мяч",
                    "modifier": "красный",
                    "agreement": "masc.sing.nom",
                    "subject": "я",
                    "predicate_lemma": "видеть",
                    "object_lemma": "мяч",
                    "thesis": "object_in_focus",
                    "outline_1": "name object",
                },
            }
        ]
    }
    path = tmp_path / "material.bundle.json"
    path.write_text(json.dumps(bundle, ensure_ascii=False), encoding="utf-8")
    proc = subprocess.run(
        [sys.executable, str(REPO / "tools" / "validate_dialog_script_slots.py"), str(path)],
        cwd=str(REPO),
        capture_output=True,
        text=True,
    )
    assert proc.returncode == 0, proc.stdout + proc.stderr
