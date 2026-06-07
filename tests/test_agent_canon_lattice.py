#!/usr/bin/env python3
"""Agent canon lattice promote/demote — agent act, not teacher."""

from __future__ import annotations

import shutil
import tempfile
from pathlib import Path

import pytest

from casa.prisms.memory.agent_canon_lattice import (
    agent_demote_canon_lattice,
    agent_promote_canon_lattice,
    list_agent_canon_lattices,
)
from casa.prisms.memory.agent_memory_ops import agent_remember
from casa.prisms.memory.memory_prisms import ensure_prisms


def test_agent_promote_and_demote_logic_law():
    tmp = Path(tempfile.mkdtemp(prefix="casa-canon-"))
    try:
        state = ensure_prisms({"schema_version": "multi_prism_v1", "field_version": 0})
        src = agent_remember(
            tmp,
            state,
            {
                "kind": "hypothesis",
                "text": "NOT (A AND B) ↔ (NOT A) OR (NOT B).",
                "concepts": ["math.logic.de_morgan"],
                "tags": ["logic-lab"],
                "status": "confirmed",
                "test_cues": ["de morgan", "demorgan"],
            },
        )
        rep = agent_promote_canon_lattice(
            tmp,
            state,
            {
                "lattice_id": "logic-laws",
                "concept_ids": ["math.logic.de_morgan"],
                "source_journal_id": src.get("journal_id"),
                "reason": "held-out 3/3 на truth-table",
            },
        )
        assert rep.get("promoted")
        listing = list_agent_canon_lattices(tmp)
        assert listing["count"] == 1
        assert "math.logic.de_morgan" in listing["entries"][0]["concept_ids"]

        dem = agent_demote_canon_lattice(
            tmp,
            state,
            {"lattice_id": "logic-laws", "reason": "переформулировал закон"},
        )
        assert dem.get("demoted")
        assert list_agent_canon_lattices(tmp)["count"] == 0
    finally:
        shutil.rmtree(tmp, ignore_errors=True)


def test_agent_cannot_promote_bootstrap_alphabet():
    tmp = Path(tempfile.mkdtemp(prefix="casa-canon-boot-"))
    try:
        state = ensure_prisms({"schema_version": "multi_prism_v1", "field_version": 0})
        with pytest.raises(ValueError, match="host-only"):
            agent_promote_canon_lattice(
                tmp,
                state,
                {
                    "lattice_id": "alphabet-ru",
                    "concept_ids": ["grapheme.cyrl.a.lower"],
                },
                allow_unconfirmed=True,
            )
    finally:
        shutil.rmtree(tmp, ignore_errors=True)
