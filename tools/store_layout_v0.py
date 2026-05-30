#!/usr/bin/env python3
"""Canonical agent-store paths (structure ≠ corpus source name)."""

from __future__ import annotations

from pathlib import Path

# Production Russian headword lexicon (SSS L0–L3 + sharded L2).
STORE_RU_LEXICON_V0 = "sss-ru-lexicon-v0"

# English folk-tale lexicon (separate store; L2_en_word_* shards).
STORE_EN_FOLK_V0 = "sss-en-folk-v0"

# Read-only monolith built from Afanasyev ingest (corpus reference only).
STORE_INGEST_REF_AFAN_V0 = "sss-afan-v0"


def agent_store_dir(store_id: str, *, root: Path | None = None) -> Path:
    base = (root / "examples" / "agent-stores") if root is not None else Path("examples/agent-stores")
    return base / store_id


def ru_lexicon_store(*, root: Path | None = None) -> Path:
    return agent_store_dir(STORE_RU_LEXICON_V0, root=root)


def en_folk_store(*, root: Path | None = None) -> Path:
    return agent_store_dir(STORE_EN_FOLK_V0, root=root)


def nca_root(store_dir: Path) -> Path:
    """All per-lattice NCA weights live under the store."""
    return store_dir / "nca"


def nca_lattice_dir(store_dir: Path, lattice_id: str) -> Path:
    return nca_root(store_dir) / lattice_id.replace("/", "_")


def field_state_path(store_dir: Path) -> Path:
    return store_dir / "field_state.json"


def ltm_root(store_dir: Path) -> Path:
    """Compact memory pack (vocab + placements per lattice)."""
    return store_dir / "ltm"


def nca_train_registry_path(store_dir: Path) -> Path:
    return store_dir / "nca_train_registry.v0.json"
