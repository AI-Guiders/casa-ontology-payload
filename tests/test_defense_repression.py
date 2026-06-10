#!/usr/bin/env python3
"""Psychological defenses — full ADR-0074 stack (P19a–f)."""

from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from casa.domain.dialogue_bind.blocks import block_dict
from casa.domain.dialogue_bind.journal import journal_recall_records
from casa.domain.dialogue_bind.recall_routing import journal_recall_tract_boost
from casa.domain.dialogue_bind.scoring import reweight_blocks_for_reply
from casa.domain.subject_agency import SubjectAction, evaluate_external_proposal
from casa.prisms.affect import affect_after_turn, spawn_emotional_zone
from casa.prisms.control.fpn_state import WorkingMemory
from casa.prisms.defense import (
    apply_trauma_cement_bind_deltas,
    build_defense_honesty_report,
    consolidate_trauma_cement,
    defense_after_life_event,
    defense_snapshot,
    is_confabulated_row,
    is_journal_repressed,
    is_trauma_journal_row,
    limbic_confabulation_active,
    limbic_denial_active,
    limbic_repression_active,
    limbic_trauma_tier_active,
    mark_journal_repressed,
    probe_trauma_fade_immunity,
)
from casa.prisms.defense.trauma_cement import trauma_edges
from casa.prisms.defense.denial import apply_denial_tract_adjustment
from casa.prisms.memory.agent_memory_ops import agent_remember
from casa.prisms.memory.memory_prisms import ensure_prisms
from casa.prisms.tick.tract.model import TractScore


class DefenseMechanismTests(unittest.TestCase):
    def _painful_state(self) -> dict:
        state = ensure_prisms({"field_version": 0})
        spawn_emotional_zone(
            state,
            config={"initial_axes": {"valence": -0.4, "arousal": 0.6, "security": 0.2}},
        )
        return state

    def test_teach_row_not_auto_repressed(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            store = Path(tmp)
            state = self._painful_state()
            rep = agent_remember(
                store,
                state,
                {
                    "kind": "observation",
                    "text": "Любимый цвет — синий.",
                    "tags": ["chat", "correction"],
                },
                persist=True,
            )
            defense_after_life_event(state, store, life_event="self_failure", tick=3)
            from casa.prisms.memory.agent_journal import find_journal_entry

            found = find_journal_entry(store, str(rep["journal_id"]))
            self.assertIsNotNone(found)
            row, _ = found
            self.assertFalse(is_journal_repressed(row))

    def test_repressed_row_blocked_on_hot_recall(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            store = Path(tmp)
            state = ensure_prisms({"field_version": 0})
            rep = agent_remember(
                store,
                state,
                {
                    "kind": "episode",
                    "text": "Провал на экзамене по математике — стыдно вспоминать.",
                    "tags": ["episode", "math"],
                },
                persist=True,
            )
            mark_journal_repressed(
                store,
                str(rep["journal_id"]),
                reason="test",
                event="self_failure",
                tick=1,
            )
            rows = journal_recall_records(
                store,
                "напомни про экзамен математике",
                limit=6,
                state=state,
            )
            ids = {str(r.get("id") or "") for r in rows}
            self.assertNotIn(str(rep["journal_id"]), ids)
            _, _, sources = journal_recall_tract_boost(
                store,
                "напомни про экзамен математике",
                state=state,
            )
            self.assertFalse(any("journal:overlap" in s for s in sources))

    def test_auto_repress_and_character_dent(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            store = Path(tmp)
            state = self._painful_state()
            agent_remember(
                store,
                state,
                {
                    "kind": "episode",
                    "text": "Ошибся на задаче — партнёр увидел.",
                    "tags": ["episode"],
                },
                persist=True,
            )
            affect_after_turn(state, "self_failure", tick=5)
            self.assertTrue(limbic_repression_active(state))
            rep = defense_after_life_event(state, store, life_event="self_failure", tick=5)
            self.assertIn("journal", rep)
            self.assertIn("character", rep)
            from casa.prisms.intelligence.character import ensure_character_zone

            zone = ensure_character_zone(state)
            self.assertTrue(zone.get("bias_matrix"))

    def test_denial_damps_recall_tract(self) -> None:
        state = self._painful_state()
        self.assertTrue(limbic_denial_active(state))
        scores = {
            "recall": TractScore("recall", 40, ["test"]),
            "social": TractScore("social", 10, []),
        }
        rep = apply_denial_tract_adjustment(scores, "напомни про провал на экзамене", state)
        self.assertTrue(rep.get("active"))
        self.assertLess(scores["recall"].score, 40)
        self.assertGreater(scores["social"].score, 10)

    def test_displacement_boosts_math_proxy(self) -> None:
        state = self._painful_state()
        blocks = [
            block_dict("math.add.2_3", "2+3=5", source="field", score=8),
            block_dict(
                "agent.self.journal.j1",
                "Провал и стыд на экзамене",
                source="journal",
                score=30,
            ),
        ]
        reweight_blocks_for_reply(blocks, "провал", kb_hits=[], intent="social", state=state)
        math_score = next(b["score"] for b in blocks if b["concept_id"].startswith("math."))
        journal_score = next(b["score"] for b in blocks if b.get("source") == "journal")
        self.assertGreater(math_score, 8)
        self.assertLess(journal_score, 30)

    def test_projection_boosts_partner_block(self) -> None:
        from casa.prisms.defense.projection import apply_projection_block_deltas

        state = self._painful_state()
        blocks = [
            block_dict("subject.dialog.partner_recent", "ты сказал", source="dialogue", score=10),
            block_dict("ru.dialog.self.name", "я нейманн", source="kb", score=20),
        ]
        rep = apply_projection_block_deltas(blocks, intent="social", state=state)
        self.assertTrue(rep.get("active"))
        partner = next(b for b in blocks if b["concept_id"] == "subject.dialog.partner_recent")
        self_block = next(b for b in blocks if b["concept_id"].startswith("ru.dialog.self"))
        self.assertGreater(int(partner["score"]), 10)
        self.assertLess(int(self_block["score"]), 20)

    def test_sublimation_defers_partner_turn(self) -> None:
        state = self._painful_state()
        wm = WorkingMemory()
        disp = evaluate_external_proposal(state, wm, load_rep={"overloaded": False})
        self.assertEqual(disp.action, SubjectAction.DEFER)
        self.assertEqual(disp.reason, "defense_sublimation")

    def test_confabulation_substitutes_repressed_on_recall_cue(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            store = Path(tmp)
            state = self._painful_state()
            self.assertTrue(limbic_confabulation_active(state))
            rep = agent_remember(
                store,
                state,
                {
                    "kind": "episode",
                    "text": "Провал на экзамене по математике — стыдно вспоминать.",
                    "tags": ["episode", "math"],
                },
                persist=True,
            )
            entry_id = str(rep["journal_id"])
            mark_journal_repressed(store, entry_id, reason="test", event="self_failure", tick=2)
            rows = journal_recall_records(
                store,
                "напомни про экзамен математике",
                limit=6,
                state=state,
            )
            ids = {str(r.get("id") or "") for r in rows}
            self.assertNotIn(entry_id, ids)
            confabs = [r for r in rows if is_confabulated_row(r)]
            self.assertGreaterEqual(len(confabs), 1)
            from casa.prisms.memory.agent_journal import find_journal_entry

            cold, _ = find_journal_entry(store, entry_id)
            self.assertNotEqual(str(confabs[0].get("text") or "").strip(), str(cold.get("text") or "").strip())

    def test_no_confab_without_limbic_band(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            store = Path(tmp)
            state = ensure_prisms({"field_version": 0})
            spawn_emotional_zone(state)
            rep = agent_remember(
                store,
                state,
                {"kind": "episode", "text": "Провал на экзамене.", "tags": ["episode"]},
                persist=True,
            )
            mark_journal_repressed(store, str(rep["journal_id"]), reason="t", tick=1)
            rows = journal_recall_records(store, "напомни про экзамен", limit=6, state=state)
            self.assertFalse(any(is_confabulated_row(r) for r in rows))

    def test_trauma_tier_and_cement_on_extreme_limbic(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            store = Path(tmp)
            state = self._painful_state()
            self.assertTrue(limbic_trauma_tier_active(state))
            rep = agent_remember(
                store,
                state,
                {
                    "kind": "episode",
                    "text": "Отец душил — страх и боль, не могла дышать.",
                    "tags": ["episode"],
                },
                persist=True,
            )
            out = defense_after_life_event(state, store, life_event="security_threat", tick=7)
            self.assertIn("trauma", out)
            self.assertFalse(out["trauma"].get("skipped"))
            from casa.prisms.memory.agent_journal import find_journal_entry

            row, _ = find_journal_entry(store, str(rep["journal_id"]))
            self.assertTrue(is_trauma_journal_row(row))
            self.assertGreaterEqual(len(trauma_edges(state)), 1)

    def test_trauma_cement_sticky_without_limbic_band(self) -> None:
        state = self._painful_state()
        with tempfile.TemporaryDirectory() as tmp:
            store = Path(tmp)
            consolidate_trauma_cement(
                state,
                store,
                life_event="security_threat",
                tick=1,
                source_text="страх удушения и боль",
            )
            for tick in (2, 3, 4, 5):
                consolidate_trauma_cement(
                    state,
                    store,
                    life_event="security_threat",
                    tick=tick,
                    source_text="страх удушения и боль",
                )
            edges = trauma_edges(state)
            self.assertTrue(any(e.get("cemented") for e in edges))

        spawn_emotional_zone(
            state,
            config={"initial_axes": {"valence": 0.2, "arousal": 0.2, "security": 0.8}},
        )
        self.assertFalse(limbic_trauma_tier_active(state))

        blocks = [
            block_dict("math.add.2_3", "2+3=5", source="field", score=8),
            block_dict(
                "agent.self.journal.j1",
                "Страх и боль при удушении",
                source="journal",
                score=30,
            ),
        ]
        rep = apply_trauma_cement_bind_deltas(
            blocks, query="напомни про страх", intent="social", state=state
        )
        self.assertTrue(rep.get("active"))
        math_score = next(b["score"] for b in blocks if b["concept_id"].startswith("math."))
        self.assertGreater(math_score, 8)

    def test_trauma_hippo_fade_immunity(self) -> None:
        state = self._painful_state()
        from casa.domain.prism_wire import prism_hippo

        hippo = prism_hippo(state)
        hippo["episodes"] = [
            {
                "id": "ep-trauma",
                "salience": 0.9,
                "defense": {"trauma_tier": True, "mechanism": "trauma_cement"},
            }
        ]
        probe = probe_trauma_fade_immunity(state)
        self.assertTrue(probe.get("pass"))

    def test_defense_honesty_report_gate(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            store = Path(tmp)
            state = self._painful_state()
            report = build_defense_honesty_report(state, store_dir=store)
            self.assertTrue(report.get("gate_pass"))
            snap = defense_snapshot(state)
            self.assertTrue(snap.get("repression"))


if __name__ == "__main__":
    unittest.main()
