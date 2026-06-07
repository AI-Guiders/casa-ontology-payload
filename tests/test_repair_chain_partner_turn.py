#!/usr/bin/env python3
"""Integration: repair chain ≥3 turns via run_dialogue_partner_turn (ADR-0061)."""

from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from casa.cli.ingest_state import resolve_ingest_state
from casa.domain.dialogue_turn import load_dialogue_turns
from casa.domain.subject_mode import apply_subject_profile
from casa.prisms.affect import core_affect_state
from casa.prisms.control.fpn_state import WorkingMemory
from casa.prisms.control.agent_sn_cen_tick import run_dialogue_partner_turn
from casa.prisms.intelligence.migrate import migrate_intelligence_zones
from casa.prisms.intelligence.social import ensure_social_zone


def _boot_dialogue_store(store: Path) -> tuple[dict, WorkingMemory]:
    (store / "bundles").mkdir(parents=True, exist_ok=True)
    (store / "store_profile.json").write_text(
        json.dumps({"subject_mode": True, "display_name": "Тест"}, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )
    migrate_intelligence_zones(store, tick=0, persist=True)
    state = resolve_ingest_state(store, None)
    apply_subject_profile(store, state)
    return state, WorkingMemory(tick=0)


class RepairChainPartnerTurnTests(unittest.TestCase):
    def test_three_turn_repair_arc_via_agent_life_engine(self) -> None:
        """self_failure → repair invite → partner trust; same engine as REPL."""
        with tempfile.TemporaryDirectory() as tmp:
            store = Path(tmp)
            state, wm = _boot_dialogue_store(store)
            chain: list[tuple[str, str, str]] = [
                ("Как дела?", "self_failure", "post"),
                ("прости, странно что молчал", "partner_repair_invite", "pre"),
                ("Спасибо, помогло", "partner_trust", "both"),
            ]

            for query, expected_life, where in chain:
                _, report, wm, state = run_dialogue_partner_turn(
                    store,
                    user_query=query,
                    wm=wm,
                    state=state,
                )
                dlg = report.get("dialogue") or {}
                self.assertTrue(dlg.get("subject_mode"), query)
                self.assertNotEqual(dlg.get("disposition_verbalized"), "defer", query)
                iz = dlg.get("intelligence_zones") or {}
                pre = iz.get("pre_compose") or {}
                post_life = iz.get("life_event")
                pre_life = pre.get("life_event")
                if where == "post":
                    self.assertEqual(post_life, expected_life, query)
                elif where == "pre":
                    self.assertEqual(pre_life, expected_life, query)
                else:
                    self.assertEqual(pre_life, expected_life, query)
                    self.assertEqual(post_life, expected_life, query)

                if expected_life == "self_failure":
                    self.assertEqual(
                        core_affect_state(state).episodic.get("dialog.repair_pending"),
                        1.0,
                    )
                if expected_life == "partner_repair_invite":
                    self.assertEqual(
                        core_affect_state(state).episodic.get("dialog.repair_invited"),
                        1.0,
                    )

            turns = load_dialogue_turns(store)
            self.assertGreaterEqual(len(turns), 4)
            partner_lines = [t.text for t in turns if t.speaker == "partner"]
            self.assertEqual(len(partner_lines), 3)

            social = ensure_social_zone(state)
            self.assertGreater(float(social.get("partner_trust") or 0), 0.5)


if __name__ == "__main__":
    unittest.main()
