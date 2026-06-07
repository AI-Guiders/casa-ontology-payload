#!/usr/bin/env python3
"""morph-role-en parallel slot bootstrap."""

from __future__ import annotations

import shutil
import tempfile
from pathlib import Path

from casa.prisms.memory.bootstrap_morph_role import MORPH_ROLE_CONCEPTS, bootstrap_morph_role_lattice
from casa.prisms.memory.bootstrap_morph_role_en import bootstrap_morph_role_en_lattice
from casa.prisms.memory.bootstrap_host_canon import bootstrap_host_canon_lattices, morph_lattice_for_locale
from casa.prisms.memory.memory_prisms import ensure_prisms, memory_lattices


def test_morph_lattice_for_locale():
    assert morph_lattice_for_locale("ru") == "morph-role-ru"
    assert morph_lattice_for_locale("en") == "morph-role-en"


def test_bootstrap_morph_role_en_places_concepts():
    tmp = Path(tempfile.mkdtemp(prefix="casa-morph-en-"))
    try:
        state = ensure_prisms({"schema_version": "multi_prism_v1", "field_version": 0})
        rep = bootstrap_morph_role_en_lattice(tmp, state, persist=False)
        assert rep["lattice_id"] == "morph-role-en"
        assert rep["placed"] == len(MORPH_ROLE_CONCEPTS)
        lat = memory_lattices(state)["morph-role-en"]
        assert lat.get("stability") == "bootstrap_canon"
        assert lat.get("locale_slot") == "en"
    finally:
        shutil.rmtree(tmp, ignore_errors=True)


def test_host_canon_en_seeds_morph_en():
    tmp = Path(tempfile.mkdtemp(prefix="casa-host-canon-en-"))
    try:
        state = ensure_prisms({"schema_version": "multi_prism_v1", "field_version": 0})
        rep = bootstrap_host_canon_lattices(tmp, state, locale="en", persist=False)
        assert len(rep["bootstrapped"]) == 1
        assert rep["bootstrapped"][0]["lattice_id"] == "morph-role-en"
        assert "morph-role-en" in memory_lattices(state)
    finally:
        shutil.rmtree(tmp, ignore_errors=True)


def test_ru_and_en_lattices_are_parallel_shelves():
    tmp = Path(tempfile.mkdtemp(prefix="casa-morph-parallel-"))
    try:
        state = ensure_prisms({"schema_version": "multi_prism_v1", "field_version": 0})
        bootstrap_morph_role_lattice(tmp, state, lattice_id="morph-role-ru", persist=False)
        bootstrap_morph_role_lattice(tmp, state, lattice_id="morph-role-en", persist=False)
        lattices = memory_lattices(state)
        assert "morph-role-ru" in lattices
        assert "morph-role-en" in lattices
        assert lattices["morph-role-ru"]["locale_slot"] == "ru"
        assert lattices["morph-role-en"]["locale_slot"] == "en"
    finally:
        shutil.rmtree(tmp, ignore_errors=True)
