#!/usr/bin/env python3
"""ADR-0081 wire tests — lexical dialog slots, bundle gate, oracle audit."""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

from casa.prisms.tick.discourse.model import DiscourseContext
from casa.prisms.tick.discourse.realizers.blocks import DialogBlockRealizer

REPO = Path(__file__).resolve().parents[1]


def test_dialog_realizer_lexical_thanks_not_clause_script() -> None:
    block = {
        "concept_id": "ru.dialog.thanks",
        "text": "x",
        "score": 40,
        "slots": {
            "stimulus": "спасибо",
            "response": "пожалуйста",
            "clause_1": "обращайся если понадобится ещё",
        },
    }
    ctx = DiscourseContext.bind(
        query="Спасибо!",
        blocks=[block],
        query_intent="social",
        stance="confident",
    )
    clauses = DialogBlockRealizer().realize(block, ctx)
    text = " ".join(" ".join(c.pieces) for c in clauses).lower()
    assert "пожалуйста" in text
    assert "обращайся" not in text


def test_bundle_script_slot_gate_passes() -> None:
    proc = subprocess.run(
        [sys.executable, "tools/validate_dialog_script_slots.py"],
        cwd=REPO,
        capture_output=True,
        text=True,
        check=False,
    )
    assert proc.returncode == 0, proc.stdout + proc.stderr


def test_oracle_audit_strict_passes() -> None:
    proc = subprocess.run(
        [sys.executable, "tools/oracle_audit.py", "--strict"],
        cwd=REPO,
        capture_output=True,
        text=True,
        check=False,
    )
    assert proc.returncode == 0, proc.stdout + proc.stderr


def test_how_are_you_hub_has_no_clause_scripts_in_bundle() -> None:
    bundle = json.loads(
        (REPO / "agents/von-neumann/bundles/kb-lang-ru-grammar-dialog-v1.bundle.json").read_text(
            encoding="utf-8"
        )
    )
    hub = next(c for c in bundle["claims"] if c["concept_id"] == "ru.dialog.how_are_you")
    slots = hub.get("slots") or {}
    assert "clause_1" not in slots
    assert slots.get("situation") == "partner_asks_state"
