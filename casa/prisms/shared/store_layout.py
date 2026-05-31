#!/usr/bin/env python3
"""Canonical agent-store paths (structure ≠ corpus source name)."""

from __future__ import annotations

from casa._paths import ensure_import_paths

ensure_import_paths()

from dataclasses import dataclass
from pathlib import Path
from typing import Literal

# Lab data root (stores, profiles, corpus, experiments). Formerly `examples/`.
LAB_DATA_DIR = "lab"

# Lab archaic Afan lexicon (not prod T9). Prod modern → STORE_RU_GENERAL_V0.
STORE_RU_LEXICON_V0 = "sss-ru-lexicon"

# English folk-tale lexicon (separate store; L2_en_word_* shards).
STORE_EN_FOLK_V0 = "sss-en-folk"

# Quad corpora v0: general vs tech × ru vs en (batch imprint + per-store NCA).
STORE_EN_GENERAL_V0 = "sss-en-general"
STORE_EN_TECH_V0 = "sss-en-tech"
STORE_RU_GENERAL_V0 = "sss-ru-general"
STORE_RU_TECH_V0 = "sss-ru-tech"

# Read-only monolith built from Afanasyev ingest (corpus reference only).
STORE_INGEST_REF_AFAN_V0 = "sss-afan"

# Role-based lab stores (no corpus in name — see agent-store-catalog.md)
STORE_MATH_L0_LAB = "math-l0-lab"
STORE_LANGUAGE_AGENT_LAB = "language-agent-lab"
STORE_CONTROL_LAB = "control-lab"
STORE_CODE_AGENT_LAB = "code-agent-lab"
STORE_BUKVAR_LAB = "bukvar-lab"
STORE_RESEARCH_AGENT_LAB = "research-agent-lab"

Locale = Literal["en", "ru"]
Tier = Literal["general", "tech"]

# --- Store tiers (canon) ---
# Shipped  = profile pack in distro (ltm/ + nca/)
# Runtime  = checkpoint on disk — survives process restart, NOT in profile tar
# Self     = agent-owned (agent/, journal/) — no auto-export to ltm/
STORE_TIER_SHIPPED = "shipped"
STORE_TIER_RUNTIME = "runtime"
STORE_TIER_SELF = "self"

RUNTIME_CHECKPOINT_FILES: tuple[str, ...] = ("field_state.json", "agent_session.json")
SELF_TIER_DIR_NAMES: tuple[str, ...] = ("agent", "journal")


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
        "en-general",
        f"{LAB_DATA_DIR}/corpus/en-general/headwords.v1.txt",
    ),
    "en-tech": CorpusSpec(
        STORE_EN_TECH_V0,
        "en",
        "tech",
        "en-tech",
        f"{LAB_DATA_DIR}/corpus/en-tech/headwords.v1.txt",
    ),
    "ru-general": CorpusSpec(
        STORE_RU_GENERAL_V0,
        "ru",
        "general",
        "ru-general",
        f"{LAB_DATA_DIR}/corpus/ru-general/headwords.v1.txt",
    ),
    "ru-tech": CorpusSpec(
        STORE_RU_TECH_V0,
        "ru",
        "tech",
        "ru-tech",
        f"{LAB_DATA_DIR}/corpus/ru-tech/headwords.v1.txt",
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


def math_l0_lab_store(*, root: Path | None = None) -> Path:
    return agent_store_dir(STORE_MATH_L0_LAB, root=root)


def language_agent_lab_store(*, root: Path | None = None) -> Path:
    return agent_store_dir(STORE_LANGUAGE_AGENT_LAB, root=root)


def control_lab_store(*, root: Path | None = None) -> Path:
    return agent_store_dir(STORE_CONTROL_LAB, root=root)


def en_folk_store(*, root: Path | None = None) -> Path:
    return agent_store_dir(STORE_EN_FOLK_V0, root=root)


def nca_root(store_dir: Path) -> Path:
    """All per-lattice NCA weights live under the store."""
    return store_dir / "nca"


def nca_lattice_dir(store_dir: Path, lattice_id: str) -> Path:
    """Primary write target for per-lattice NCA weights (canonical layout v1)."""
    from casa.prisms.shared.store_paths_v1 import resolve_nca_lattice_dir as _resolve

    return _resolve(store_dir, lattice_id)


def resolve_nca_lattice_dir(store_dir: Path, lattice_id: str) -> Path:
    return nca_lattice_dir(store_dir, lattice_id)


def canonical_lattice_id(lattice_id: str) -> str:
    return str(lattice_id)


def field_state_path(store_dir: Path) -> Path:
    return store_dir / "field_state.json"


def ltm_root(store_dir: Path) -> Path:
    """Compact memory pack (vocab + placements per lattice)."""
    return store_dir / "ltm"


def journal_root(store_dir: Path) -> Path:
    """Agent-owned journal — not exported in ltm/ cartridges."""
    return store_dir / "journal"


def journal_index_path(store_dir: Path) -> Path:
    return journal_root(store_dir) / "index.json"


def journal_domain_dir(store_dir: Path, domain: str) -> Path:
    return journal_root(store_dir) / domain


def journal_entries_path(store_dir: Path, domain: str) -> Path:
    return journal_domain_dir(store_dir, domain) / "entries.jsonl"


def agent_prism_root(store_dir: Path) -> Path:
    """Agent-owned prism on disk — separate from profile ltm/."""
    return store_dir / "agent"


def agent_manifest_path(store_dir: Path) -> Path:
    return agent_prism_root(store_dir) / "manifest.json"


def agent_bridges_path(store_dir: Path) -> Path:
    """Agent-owned control bridges — not exported in profile ltm/."""
    return agent_prism_root(store_dir) / "bridges.json"


def agent_lattices_dir(store_dir: Path) -> Path:
    return agent_prism_root(store_dir) / "lattices"


def agent_lattice_path(store_dir: Path, lattice_id: str) -> Path:
    return agent_lattices_dir(store_dir) / f"{lattice_id}.json"


def agent_nca_root(store_dir: Path) -> Path:
    return agent_prism_root(store_dir) / "nca"


def agent_nca_lattice_dir(store_dir: Path, lattice_id: str) -> Path:
    return agent_nca_root(store_dir) / lattice_id


def nca_train_registry_path(store_dir: Path) -> Path:
    return store_dir / "nca_train_registry.json"


def repo_root() -> Path:
    """Repository root (tools/ lives directly under it)."""
    return Path(__file__).resolve().parents[1]


def rel_to_repo(path: Path | str | None) -> str | None:
    """Repo-relative POSIX path for manifests/registries (never leak absolute paths).

    Falls back to the path as-is when it lies outside the repo (e.g. an external
    out-dir); callers store this for bookkeeping only, not for loading.
    """
    if path is None:
        return None
    p = Path(path)
    try:
        return p.resolve().relative_to(repo_root()).as_posix()
    except ValueError:
        return p.as_posix()


def runtime_checkpoint_paths(store_dir: Path) -> dict[str, Path]:
    """On-disk **runtime checkpoint** tier (not shipped in profile tar)."""
    store_dir = store_dir.resolve()
    return {
        "field_state": field_state_path(store_dir),
        "agent_session": store_dir / "agent_session.json",
    }


def shipped_tier_roots(store_dir: Path) -> dict[str, Path]:
    """Profile pack paths (ship in distro)."""
    store_dir = store_dir.resolve()
    return {"ltm": ltm_root(store_dir), "nca": nca_root(store_dir)}


def self_tier_roots(store_dir: Path) -> dict[str, Path]:
    """Agent-owned tier (no auto-export to ltm/)."""
    store_dir = store_dir.resolve()
    return {"journal": journal_root(store_dir), "agent": agent_prism_root(store_dir)}
