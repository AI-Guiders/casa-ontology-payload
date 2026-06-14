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


def test_promote_with_passing_gate_report_records_provenance():
    from casa.eval.held_out_gate import promote_candidate_id

    tmp = Path(tempfile.mkdtemp(prefix="casa-canon-gate-"))
    try:
        state = ensure_prisms({"schema_version": "multi_prism_v1", "field_version": 0})
        concept_ids = ["math.logic.de_morgan"]
        report = {
            "passed": True,
            "candidate_id": promote_candidate_id("logic-laws", concept_ids),
            "held_out_score": 1.0,
            "neg_pass_rate": 0.0,
            "negative_control_passed": True,
        }
        rep = agent_promote_canon_lattice(
            tmp,
            state,
            {"lattice_id": "logic-laws", "concept_ids": concept_ids},
            gate_report=report,
            allow_unconfirmed=True,  # no confirmed source: the held-out gate is the authority
        )
        assert rep.get("promoted")
        assert rep["gate"]["authority"] == "held_out_gate"
        assert rep["gate"]["gated"] is True
        assert rep["gate"]["candidate_id"] == report["candidate_id"]
    finally:
        shutil.rmtree(tmp, ignore_errors=True)


def test_promote_rejects_mismatched_gate_report():
    tmp = Path(tempfile.mkdtemp(prefix="casa-canon-gate-bad-"))
    try:
        state = ensure_prisms({"schema_version": "multi_prism_v1", "field_version": 0})
        report = {"passed": True, "candidate_id": "cand-deadbeefdeadbeef"}  # not for these concepts
        with pytest.raises(ValueError, match="does not match this promotion"):
            agent_promote_canon_lattice(
                tmp,
                state,
                {"lattice_id": "logic-laws", "concept_ids": ["math.logic.de_morgan"]},
                gate_report=report,
                allow_unconfirmed=True,
            )
    finally:
        shutil.rmtree(tmp, ignore_errors=True)


def test_promote_rejects_failing_gate_report():
    tmp = Path(tempfile.mkdtemp(prefix="casa-canon-gate-fail-"))
    try:
        state = ensure_prisms({"schema_version": "multi_prism_v1", "field_version": 0})
        report = {"passed": False, "candidate_id": "x"}
        with pytest.raises(ValueError, match="not passing"):
            agent_promote_canon_lattice(
                tmp,
                state,
                {"lattice_id": "logic-laws", "concept_ids": ["math.logic.de_morgan"]},
                gate_report=report,
                allow_unconfirmed=True,
            )
    finally:
        shutil.rmtree(tmp, ignore_errors=True)
