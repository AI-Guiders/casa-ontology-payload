#!/usr/bin/env python3
"""Agent canon tick promote + field materialize."""

from __future__ import annotations

import shutil
import tempfile
from pathlib import Path

from casa.domain.mastery_gate import record_gate_attempt
from casa.prisms.memory.agent_canon_field import sync_agent_canon_to_field
from casa.prisms.memory.agent_canon_lattice import agent_promote_canon_lattice, load_canon_registry
from casa.prisms.memory.agent_memory_ops import agent_remember
from casa.prisms.memory.memory_prisms import ensure_prisms, memory_lattices
from casa.prisms.tick.agent_canon_tick import maybe_promote_canon_on_tick, verify_canon_candidate


def test_sync_agent_canon_creates_lattice_on_field():
    tmp = Path(tempfile.mkdtemp(prefix="casa-canon-field-"))
    try:
        state = ensure_prisms({"schema_version": "multi_prism_v1", "field_version": 0})
        src = agent_remember(
            tmp,
            state,
            {
                "kind": "hypothesis",
                "text": "∫ k·f dx = k·∫ f dx",
                "concepts": ["math.calc.integral.linear"],
                "tags": ["logic-lab"],
                "status": "confirmed",
                "test_cues": ["линейность интеграла"],
            },
        )
        agent_promote_canon_lattice(
            tmp,
            state,
            {
                "lattice_id": "math-calculus-rules",
                "concept_ids": ["math.calc.integral.linear"],
                "source_journal_id": src.get("journal_id"),
                "reason": "smoke",
            },
            persist=False,
        )
        rep = sync_agent_canon_to_field(state, tmp)
        assert rep.get("synced")
        lats = memory_lattices(state)
        assert "math-calculus-rules" in lats
        dec_cells = sum(1 for row in lats["math-calculus-rules"]["cells"] if row)
        assert dec_cells > 0
    finally:
        shutil.rmtree(tmp, ignore_errors=True)


def test_tick_does_not_promote_without_held_out_gate():
    tmp = Path(tempfile.mkdtemp(prefix="casa-canon-tick-"))
    try:
        state = ensure_prisms({"schema_version": "multi_prism_v1", "field_version": 0})
        src = agent_remember(
            tmp,
            state,
            {
                "kind": "hypothesis",
                "text": "De Morgan: NOT (A AND B) ↔ (NOT A) OR (NOT B)",
                "concepts": ["math.logic.de_morgan"],
                "tags": ["logic-lab"],
                "status": "confirmed",
                "test_cues": ["de morgan"],
            },
        )
        jid = str(src.get("journal_id"))
        # a self-granted mastery streak no longer authorizes promotion (bypass closed):
        # with too few held-out probes the tick must NOT promote (no ungated canon)
        record_gate_attempt(state, f"canon:{jid}", passed=True, tick=1, store_dir=tmp)
        record_gate_attempt(state, f"canon:{jid}", passed=True, tick=2, store_dir=tmp)

        rep = maybe_promote_canon_on_tick(tmp, state)
        assert not (rep or {}).get("count")
        reg = load_canon_registry(tmp)
        assert not any("math.logic.de_morgan" in (e.get("concept_ids") or []) for e in reg.get("entries") or [])
    finally:
        shutil.rmtree(tmp, ignore_errors=True)


def test_canon_ready_tag_no_longer_bypasses_gate():
    tmp = Path(tempfile.mkdtemp(prefix="casa-canon-tag-"))
    try:
        state = ensure_prisms({"schema_version": "multi_prism_v1", "field_version": 0})
        row = agent_remember(
            tmp,
            state,
            {
                "kind": "hypothesis",
                "text": "Peano: 0 is a natural number.",
                "concepts": ["math.axiom.peano.zero"],
                "tags": ["logic-lab", "canon-ready"],
                "status": "confirmed",
                "test_cues": ["peano"],
            },
        )
        cand = {
            "journal_id": row.get("journal_id"),
            "concepts": ["math.axiom.peano.zero"],
            "test_cues": ["peano"],
            "suggested_lattices": ["math-axiom"],
        }
        # the canon-ready tag no longer fast-tracks; the held-out gate is required and
        # a single self-chosen cue is not enough probes to verify
        verify = verify_canon_candidate(state, tmp, cand, tick=3)
        assert not verify.get("ready")
        assert verify.get("reason") == "insufficient_probes"
    finally:
        shutil.rmtree(tmp, ignore_errors=True)
