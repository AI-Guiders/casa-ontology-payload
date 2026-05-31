"""Tests for prism layout v1 store path aliases (M1)."""

from __future__ import annotations

import json
import tempfile
from pathlib import Path

from casa.prisms.shared.export_ltm_pack_v0 import export_pack
from casa.prisms.shared.ltm_pack_v0 import read_ltm
from casa.prisms.shared.store_paths_v1 import (
    canonical_ltm_subdir,
    legacy_ltm_tier,
    manifest_layout_block,
    nca_dir_candidates,
    resolve_ltm_file,
)


def test_lexicon_canonical_subdir():
    assert canonical_ltm_subdir("lexicon-ru-07").as_posix() == "memory/lexicon"
    assert legacy_ltm_tier("lexicon-ru-07") == "l2"


def test_control_paths():
    assert canonical_ltm_subdir("control-dmn").as_posix() == "control"
    assert legacy_ltm_tier("control-dmn") == "ctrl"


def test_nca_candidates_prefer_canonical():
    store = Path("/tmp/store")
    cands = nca_dir_candidates(store, "lexicon-ru-00")
    assert cands[0].as_posix().endswith("nca/memory/lexicon/lexicon-ru-00")
    assert cands[1].as_posix().endswith("nca/lexicon-ru-00")


def test_export_dual_write_ltm_aliases():
    lat = {"width": 2, "height": 2, "cells": [["a"], [], [], []]}
    state = {
        "schema_version": "multi_prism_v1",
        "field_version": 1,
        "prisms": {"prism_memory": {"lattices": {"lexicon-ru-00": lat}}},
    }
    with tempfile.TemporaryDirectory() as tmp:
        store = Path(tmp)
        out = store / "ltm"
        manifest = export_pack(state, out, lattice_ids=["lexicon-ru-00"])
        assert manifest.get("prism_layout_version") == 1
        canon = out / "memory" / "lexicon" / "lexicon-ru-00.ltm"
        legacy_l2 = out / "l2" / "lexicon-ru-00.ltm"
        legacy_lat = out / "lat" / "lexicon-ru-00.ltm"
        assert canon.is_file()
        assert legacy_l2.is_file()
        assert legacy_lat.is_file()
        assert read_ltm(canon)["cells"] == lat["cells"]
        found = resolve_ltm_file(out, "lexicon-ru-00", manifest["lattices"]["lexicon-ru-00"])
        assert found.is_file()


def test_manifest_layout_block():
    block = manifest_layout_block()
    assert block["prism_layout_version"] == 1
    assert "ltm/l2" in block["path_aliases"]
