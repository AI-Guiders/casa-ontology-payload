#!/usr/bin/env python3
"""Canonical agent-store paths (structure ≠ corpus source name)."""

from __future__ import annotations

from casa._paths import ensure_import_paths

ensure_import_paths()

from dataclasses import dataclass
from pathlib import Path
from typing import Literal

# Dev corpus, CI snapshots (legacy). Pedagogy: LESSONS_DATA_DIR.
LAB_DATA_DIR = "lab"
LESSONS_DATA_DIR = "lessons"
AGENTS_DATA_DIR = "agents"
LAB_LEGACY_STORES_DIR = "snapshots/legacy-agent-stores"

# Default living agent (one store, own experience). Display: «Нейманн» (John von Neumann).
# CA / self-reproducing automata lineage — aligns with NCA regrow (Constitution § NCA).
STORE_AGENT_DEFAULT = "von-neumann"
STORE_AGENT_DISPLAY_NAME = "Нейманн"  # bootstrap label only; agent may choose identity in self/journal

# Planned additional agents (separate store_id each; ADR-0021 naming canon).
STORE_AGENT_LOVELACE = "lovelace"
STORE_AGENT_LOVELACE_DISPLAY = "Ловлейс"
STORE_AGENT_HAMILTON = "hamilton"
STORE_AGENT_HAMILTON_DISPLAY = "Гамильтон"  # Margaret Hamilton (Apollo software)

CANONICAL_AGENT_IDS: frozenset[str] = frozenset(
    {
        STORE_AGENT_DEFAULT,
        STORE_AGENT_LOVELACE,
        STORE_AGENT_HAMILTON,
    }
)

# Agent lexicon stores (corpus → ingest → field/ltm; no sss- prefix).
STORE_LEXICON_RU_ARCHAIC = "lexicon-ru-archaic"  # Afan lab, not prod T9
STORE_LEXICON_RU_GENERAL = "lexicon-ru-general"  # prod modern RU
STORE_LEXICON_RU_TECH = "lexicon-ru-tech"
STORE_LEXICON_EN_FOLK = "lexicon-en-folk"
STORE_LEXICON_EN_GENERAL = "lexicon-en-general"
STORE_LEXICON_EN_TECH = "lexicon-en-tech"
STORE_INGEST_REF_AFAN = "ingest-ref-afan"  # monolith ingest reference only

# Deprecated aliases — remove after migration
STORE_RU_LEXICON_V0 = STORE_LEXICON_RU_ARCHAIC
STORE_EN_FOLK_V0 = STORE_LEXICON_EN_FOLK
STORE_EN_GENERAL_V0 = STORE_LEXICON_EN_GENERAL
STORE_EN_TECH_V0 = STORE_LEXICON_EN_TECH
STORE_RU_GENERAL_V0 = STORE_LEXICON_RU_GENERAL
STORE_RU_TECH_V0 = STORE_LEXICON_RU_TECH
STORE_INGEST_REF_AFAN_V0 = STORE_INGEST_REF_AFAN

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
        STORE_LEXICON_EN_GENERAL,
        "en",
        "general",
        "en-general",
        f"{LAB_DATA_DIR}/corpus/en-general/headwords.v1.txt",
    ),
    "en-tech": CorpusSpec(
        STORE_LEXICON_EN_TECH,
        "en",
        "tech",
        "en-tech",
        f"{LAB_DATA_DIR}/corpus/en-tech/headwords.v1.txt",
    ),
    "ru-general": CorpusSpec(
        STORE_LEXICON_RU_GENERAL,
        "ru",
        "general",
        "ru-general",
        f"{LAB_DATA_DIR}/corpus/ru-general/headwords.v1.txt",
    ),
    "ru-tech": CorpusSpec(
        STORE_LEXICON_RU_TECH,
        "ru",
        "tech",
        "ru-tech",
        f"{LAB_DATA_DIR}/corpus/ru-tech/headwords.v1.txt",
    ),
}


LEXICON_STORE_ID_RENAMES: dict[str, str] = {
    "sss-ru-general-v0": STORE_LEXICON_RU_GENERAL,
    "sss-ru-general": STORE_LEXICON_RU_GENERAL,
    "sss-ru-lexicon": STORE_LEXICON_RU_ARCHAIC,
    "sss-ru-archaic": STORE_LEXICON_RU_ARCHAIC,
    "sss-ru-literary": STORE_LEXICON_RU_ARCHAIC,
    "sss-ru-tech-v0": STORE_LEXICON_RU_TECH,
    "sss-ru-tech": STORE_LEXICON_RU_TECH,
    "sss-en-general-v0": STORE_LEXICON_EN_GENERAL,
    "sss-en-general": STORE_LEXICON_EN_GENERAL,
    "sss-en-folk-v0": STORE_LEXICON_EN_FOLK,
    "sss-en-folk": STORE_LEXICON_EN_FOLK,
    "sss-en-tech-v0": STORE_LEXICON_EN_TECH,
    "sss-en-tech": STORE_LEXICON_EN_TECH,
    "sss-afan-v0": STORE_INGEST_REF_AFAN,
    "sss-afan": STORE_INGEST_REF_AFAN,
    "sss-phases-abc": "lexicon-phases-abc",
    "sss-shard-smoke": "lexicon-shard-smoke",
    "sss-afan-iii": "lexicon-afan-iii",
    "sss-afan-test": "lexicon-afan-test",
    "sss-heldout": "lexicon-heldout",
    "sss-hypothesis": "lexicon-hypothesis",
    "sss-self": "lexicon-self",
    "sss-segment": "lexicon-segment",
    "sss-phase-a": "lexicon-phase-a",
    "sss-listen-mass": "lexicon-listen-mass",
    "sss-lab": "lexicon-lab",
    "sss-full": "lexicon-full",
    "sss-kolb": "lexicon-kolb",
    "sss-bench": "lexicon-bench",
    "sss-text": "lexicon-text",
    "sss-vocab": "lexicon-vocab",
}


def is_lexicon_store_id(store_id: str) -> bool:
    """Agent lexicon store folder id (compact field_state default)."""
    return store_id.startswith("lexicon-")


def use_compact_field_state(store_dir: Path | str) -> bool:
    name = store_dir.name if isinstance(store_dir, Path) else Path(store_dir).name
    return is_lexicon_store_id(name)


def legacy_agent_stores_root(*, root: Path | None = None) -> Path:
    rel = Path(LAB_DATA_DIR) / LAB_LEGACY_STORES_DIR
    return (root / rel) if root is not None else rel


def rename_legacy_lexicon_store_dirs(*, root: Path | None = None) -> list[dict[str, str]]:
    """Rename lab/snapshots/legacy-agent-stores/sss-* → lexicon-* (one-time migration)."""
    stores_root = legacy_agent_stores_root(root=root)
    reports: list[dict[str, str]] = []
    for old_id, new_id in LEXICON_STORE_ID_RENAMES.items():
        src = stores_root / old_id
        dst = stores_root / new_id
        if not src.is_dir():
            continue
        if dst.exists():
            reports.append({"old": old_id, "new": new_id, "status": "skipped_dst_exists"})
            continue
        src.rename(dst)
        fs = field_state_path(dst)
        if fs.is_file():
            try:
                import json

                state = json.loads(fs.read_text(encoding="utf-8"))
                if isinstance(state.get("store"), dict):
                    state["store"]["store_id"] = new_id
                    fs.write_text(json.dumps(state, ensure_ascii=False, indent=2), encoding="utf-8")
            except (OSError, json.JSONDecodeError):
                pass
        reports.append({"old": old_id, "new": new_id, "status": "renamed"})
    return reports


def agents_agent_store_dir(
    store_id: str = STORE_AGENT_DEFAULT, *, root: Path | None = None
) -> Path:
    """Canonical living agent home (ADR-0021 R5)."""
    rel = Path(AGENTS_DATA_DIR) / store_id
    base = (root / rel) if root is not None else rel
    return base


def agent_store_dir(store_id: str, *, root: Path | None = None) -> Path:
    if store_id in CANONICAL_AGENT_IDS:
        return agents_agent_store_dir(store_id, root=root)
    return legacy_agent_stores_root(root=root) / store_id


def default_agent_store(*, root: Path | None = None) -> Path:
    """Living agent store (`agents/von-neumann/` by default)."""
    return agents_agent_store_dir(STORE_AGENT_DEFAULT, root=root)


def lexicon_ru_archaic_store(*, root: Path | None = None) -> Path:
    """Archaic Afan lab lexicon — not prod T9."""
    return agent_store_dir(STORE_LEXICON_RU_ARCHAIC, root=root)


def lexicon_ru_general_store(*, root: Path | None = None) -> Path:
    """Modern RU lexicon (prod)."""
    return agent_store_dir(STORE_LEXICON_RU_GENERAL, root=root)


def ru_lexicon_store(*, root: Path | None = None) -> Path:
    return lexicon_ru_archaic_store(root=root)


def ru_general_store(*, root: Path | None = None) -> Path:
    return lexicon_ru_general_store(root=root)


def math_l0_lab_store(*, root: Path | None = None) -> Path:
    return agent_store_dir(STORE_MATH_L0_LAB, root=root)


def language_agent_lab_store(*, root: Path | None = None) -> Path:
    return agent_store_dir(STORE_LANGUAGE_AGENT_LAB, root=root)


def control_lab_store(*, root: Path | None = None) -> Path:
    return agent_store_dir(STORE_CONTROL_LAB, root=root)


def lexicon_en_folk_store(*, root: Path | None = None) -> Path:
    return agent_store_dir(STORE_LEXICON_EN_FOLK, root=root)


def en_folk_store(*, root: Path | None = None) -> Path:
    return lexicon_en_folk_store(root=root)


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


def agent_canon_registry_path(store_dir: Path) -> Path:
    """Agent-owned canon tier registry (promote/demote decisions, not profile ltm/)."""
    return agent_prism_root(store_dir) / "canon_registry.v1.json"


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
