#!/usr/bin/env python3
"""Canonical agent-store paths (structure ≠ corpus source name)."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Literal

# Lab data root (stores, profiles, corpus, experiments). Formerly `examples/`.
LAB_DATA_DIR = "lab"

# Lab archaic Afan lexicon (not prod T9). Prod modern → STORE_RU_GENERAL_V0.
STORE_RU_LEXICON_V0 = "sss-ru-lexicon-v0"

# English folk-tale lexicon (separate store; L2_en_word_* shards).
STORE_EN_FOLK_V0 = "sss-en-folk-v0"

# Quad corpora v0: general vs tech × ru vs en (batch imprint + per-store NCA).
STORE_EN_GENERAL_V0 = "sss-en-general-v0"
STORE_EN_TECH_V0 = "sss-en-tech-v0"
STORE_RU_GENERAL_V0 = "sss-ru-general-v0"
STORE_RU_TECH_V0 = "sss-ru-tech-v0"

# Read-only monolith built from Afanasyev ingest (corpus reference only).
STORE_INGEST_REF_AFAN_V0 = "sss-afan-v0"

Locale = Literal["en", "ru"]
Tier = Literal["general", "tech"]


@dataclass(frozen=True)
class CorpusSpec:
    store_id: str
    locale: Locale
    tier: Tier
    corpus_tag: str
    headwords_rel: str


CORPUS_QUAD: dict[str, CorpusSpec] = {
    "en-general": CorpusSpec(
        STORE_EN_GENERAL_V0,
        "en",
        "general",
        "en-general-v0",
        f"{LAB_DATA_DIR}/corpus/en-general-v0/headwords.v1.txt",
    ),
    "en-tech": CorpusSpec(
        STORE_EN_TECH_V0,
        "en",
        "tech",
        "en-tech-v0",
        f"{LAB_DATA_DIR}/corpus/en-tech-v0/headwords.v1.txt",
    ),
    "ru-general": CorpusSpec(
        STORE_RU_GENERAL_V0,
        "ru",
        "general",
        "ru-general-v0",
        f"{LAB_DATA_DIR}/corpus/ru-general-v0/headwords.v1.txt",
    ),
    "ru-tech": CorpusSpec(
        STORE_RU_TECH_V0,
        "ru",
        "tech",
        "ru-tech-v0",
        f"{LAB_DATA_DIR}/corpus/ru-tech-v0/headwords.v1.txt",
    ),
}


def agent_store_dir(store_id: str, *, root: Path | None = None) -> Path:
    rel = Path(LAB_DATA_DIR) / "agent-stores"
    base = (root / rel) if root is not None else rel
    return base / store_id


def ru_lexicon_store(*, root: Path | None = None) -> Path:
    """Legacy name: archaic Afan store (lab). Prefer ru_general_store() for prod."""
    return agent_store_dir(STORE_RU_LEXICON_V0, root=root)


def ru_general_store(*, root: Path | None = None) -> Path:
    return agent_store_dir(STORE_RU_GENERAL_V0, root=root)


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
