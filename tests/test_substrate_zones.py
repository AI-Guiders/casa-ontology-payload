#!/usr/bin/env python3
"""Substrate zones P6–P9: genetic, perceptual, metabolic, linguistic."""

from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from casa.prisms.genetic import build_genome_spec, genetic_constant, seal_genetic_zone, species_passport
from casa.prisms.metabolic import (
    metabolic_begin_tick,
    metabolic_end_tick,
    metabolic_should_sleep,
    spawn_metabolic_zone,
)
from casa.prisms.perceptual import perceptual_prepare_turn, spawn_perceptual_zone
from casa.prisms.intelligence.linguistic import linguistic_tract_boosts, spawn_linguistic_zone
from casa.prisms.intelligence.migrate import INTELLIGENCE_ZONES_VERSION, migrate_intelligence_zones
from casa.prisms.memory.agent_prism import agent_lattices, load_agent_prism
from casa.prisms.memory.memory_prisms import ensure_prisms
from casa.prisms.shared.store_boot import boot_store


class SubstrateZonesTests(unittest.TestCase):
    def test_genetic_seal_and_constants(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            store = Path(tmp)
            (store / "agent" / "lattices").mkdir(parents=True)
            state: dict = {}
            ensure_prisms(state)
            rep = seal_genetic_zone(store, state, {"species_id": "test.species.v1"}, tick=0)
            self.assertTrue(rep.get("sealed"))
            self.assertEqual(genetic_constant(state, "species_id"), "test.species.v1")
            passport = species_passport(state)
            self.assertTrue(passport.get("valid"))
            self.assertTrue((store / "agent" / "genome.v1.json").is_file())

    def test_metabolic_fatigue_and_sleep_pressure(self) -> None:
        state: dict = {}
        seal_in_memory = build_genome_spec()
        from casa.prisms.genetic.zone import ensure_genetic_zone

        ensure_genetic_zone(state)["spec"] = seal_in_memory
        ensure_genetic_zone(state)["immutable"] = True
        spawn_metabolic_zone(state, config={"initial_atp": 0.25})
        metabolic_begin_tick(state, tick=1)
        rep = metabolic_end_tick(
            state,
            surprise_n=5,
            compose_tokens=40,
            bind_blocks=80,
            had_partner_input=True,
        )
        self.assertLess(float(rep["atp_current"]), 0.25)
        self.assertGreater(float(rep["sleep_pressure"]), 0.0)

    def test_perceptual_prepare_turn_adds_hints(self) -> None:
        state: dict = {}
        spawn_perceptual_zone(state)
        rep = perceptual_prepare_turn(state, "привет, 5+7", modality="text_stream")
        hints = rep.get("concept_hints") or []
        self.assertTrue(any(str(h).startswith("percept.") for h in hints))
        self.assertTrue(any("lang.word.привет" == h for h in hints))

    def test_perceptual_prepare_life_sensory_coactive(self) -> None:
        from casa.prisms.perceptual import merge_digest_with_perceptual_turn, perceptual_prepare_life_sensory

        state: dict = {}
        spawn_perceptual_zone(state)
        rep = perceptual_prepare_life_sensory(
            state,
            stream_id="ch00-kolgotki",
            seq=3,
            t_rel=9.5,
            visual_delta=0.25,
            audio_active=True,
            audio_placements=4,
        )
        hints = rep.get("concept_hints") or []
        self.assertIn("percept.av.coactive", hints)
        self.assertIn("percept.vis.motion", hints)
        self.assertIn("percept.listen.active", hints)
        from casa.prisms.control.sn_cen_runtime import FieldDigest

        digest = merge_digest_with_perceptual_turn(
            FieldDigest(concept_ids=["field.seed"], edge_tokens=[], concept_scores={"field.seed": 1.0}),
            state,
        )
        self.assertIn("percept.av.coactive", digest.concept_ids)

    def test_affect_after_listen_scene_theme(self) -> None:
        from casa.prisms.affect import affect_after_listen_scene, core_affect_state, spawn_emotional_zone

        state: dict = {}
        spawn_emotional_zone(state)
        before = core_affect_state(state).axes.arousal
        affect_after_listen_scene(
            state,
            "lalabook-ch00",
            scene={"collection": "emotions", "caption": "Колготки"},
        )
        after = core_affect_state(state).axes.arousal
        self.assertGreater(after, before)

    def test_perceptual_prepare_life_tick_merges_text_and_sensory(self) -> None:
        from casa.prisms.perceptual import perceptual_prepare_life_sensory, perceptual_prepare_life_tick

        state: dict = {}
        spawn_perceptual_zone(state)
        perceptual_prepare_life_sensory(
            state,
            stream_id="ch00",
            seq=1,
            t_rel=9.0,
            visual_delta=0.3,
            audio_active=True,
            aud_window_id="w1",
            vis_frame_id="f1",
        )
        rep = perceptual_prepare_life_tick(state, user_query="привет", preserve_existing=True)
        assert rep is not None
        hints = rep.get("concept_hints") or []
        self.assertIn("percept.av.coactive", hints)
        self.assertTrue(any(str(h).startswith("lang.word.") for h in hints))
        mods = rep.get("modalities") or []
        self.assertIn("text_stream", mods)
        self.assertIn("visual_stream", mods)

    def test_linguistic_tract_boosts_with_lang_hints(self) -> None:
        state: dict = {}
        spawn_linguistic_zone(state)
        boosts = linguistic_tract_boosts(state, concept_hints=["lang.word.привет"])
        self.assertGreater(boosts.get("social", 0), 0)

    def test_migrate_v4_spawns_substrate_zones(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            store = Path(tmp)
            (store / "bundles").mkdir(parents=True)
            rep = migrate_intelligence_zones(store, tick=1)
            self.assertEqual(rep["intelligence_zones_version"], INTELLIGENCE_ZONES_VERSION)
            self.assertGreaterEqual(INTELLIGENCE_ZONES_VERSION, 4)  # substrate zones introduced at v4
            self.assertTrue(rep["zones"]["genetic"].get("sealed") or rep["zones"]["genetic"].get("loaded"))
            boot = boot_store(store, prefer_field_state=True)
            load_agent_prism(store, boot["state"])
            lats = agent_lattices(boot["state"])
            for lid in (
                "agent-metabolic-core",
                "agent-percept-core",
                "agent-linguistic-core",
            ):
                self.assertIn(lid, lats, lid)
            genome = store / "agent" / "genome.v1.json"
            self.assertTrue(genome.is_file())
            data = json.loads(genome.read_text(encoding="utf-8"))
            self.assertIn("genome_hash", data)


if __name__ == "__main__":
    unittest.main()
