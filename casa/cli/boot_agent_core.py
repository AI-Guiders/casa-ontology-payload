#!/usr/bin/env python3
"""Boot immutable agent core into a living store: alphabet L0, syllables L1, VK layouts."""

from __future__ import annotations

from casa._paths import REPO_ROOT, ensure_import_paths

ensure_import_paths()

import argparse
import json
from pathlib import Path
from typing import Any

from casa.domain.prism_ids import PRISM_MEMORY
from casa.prisms.memory.alphabet_core import ru_cyrl_alphabet, en_latn_alphabet
from casa.prisms.memory.grapheme_ingest import GRAPHEME_CYRL_PREFIX, GRAPHEME_LATN_PREFIX
from casa.prisms.memory.boot_core_ltm import merge_core_ltm_stack
from casa.prisms.memory.memory_manifest import build_manifest, render_memory_md
from casa.prisms.memory.memory_prisms import ensure_prisms, import_lattice_into_prism, memory_lattices
from casa.prisms.memory.stack import decode_lattice
from casa.prisms.memory.vocab import apply_story_compose
from casa.prisms.memory.vk_layout_field import VK_CORE_LATTICE_IDS
from casa.prisms.shared.ltm_pack import read_ltm
from casa.prisms.shared.store_boot import boot_store
from casa.prisms.shared.store_layout import default_agent_store
from casa.prisms.shared.store_persist import mark_runtime_dirty, save_runtime_state


def default_syllable_l1_ltm(*, root: Path | None = None) -> Path:
    """Open RU syllable lattice from ingest reference pack (bukvar-full coverage)."""
    root = (root or REPO_ROOT).resolve()
    return (
        root
        / "lab/snapshots/legacy-agent-stores/ingest-ref-afan/ltm/memory/syllable/L1_syllable.ltm"
    )


def default_bukvar_bundle(*, root: Path | None = None) -> Path:
    root = (root or REPO_ROOT).resolve()
    return root / "lab/kb/kb-bukvar-ru-full-v1.payload.json"


def _normalize_bukvar_bundle(bundle: dict) -> dict:
    """Map legacy ``grapheme.а`` edges to ``grapheme.cyrl.а`` for z_compose vs agent-core L0."""
    out = json.loads(json.dumps(bundle, ensure_ascii=False))

    def fix_cid(cid: str) -> str:
        if cid.startswith("grapheme.") and not cid.startswith(GRAPHEME_CYRL_PREFIX) and not cid.startswith(
            GRAPHEME_LATN_PREFIX
        ):
            return f"{GRAPHEME_CYRL_PREFIX}{cid[len('grapheme.') :]}"
        return cid

    for claim in out.get("claims") or []:
        if claim.get("concept_id"):
            claim["concept_id"] = fix_cid(str(claim["concept_id"]))
    for edge in (out.get("graph") or {}).get("edges") or []:
        for key in ("src", "dst"):
            if edge.get(key):
                edge[key] = fix_cid(str(edge[key]))
    return out


def _verify_grapheme_lattices(state: dict) -> dict[str, Any]:
    """Verify RU/EN letters on field (legacy L0_grapheme_* or v1 alphabet-*)."""
    state = ensure_prisms(state)
    lattices = memory_lattices(state)
    specs: dict[str, list[tuple[str, str, set[str]]]] = {
        "ru": [
            ("L0_grapheme_cyrl", GRAPHEME_CYRL_PREFIX, set(ru_cyrl_alphabet())),
            ("alphabet-ru", GRAPHEME_CYRL_PREFIX, set(ru_cyrl_alphabet())),
        ],
        "en": [
            ("L0_grapheme_latn", GRAPHEME_LATN_PREFIX, set(en_latn_alphabet())),
            ("alphabet-en", GRAPHEME_LATN_PREFIX, set(en_latn_alphabet())),
        ],
    }
    report: dict[str, Any] = {}
    ok = True
    for lang, candidates in specs.items():
        on_field: set[str] = set()
        used_lid: str | None = None
        expected = candidates[0][2]
        for lid, prefix, exp in candidates:
            lat = lattices.get(lid)
            if not lat:
                continue
            dec = decode_lattice(lat, min_votes=1)
            found = {
                str(c.get("concept_id", ""))[len(prefix) :]
                for c in dec.get("concepts") or []
                if str(c.get("concept_id", "")).startswith(prefix)
            }
            if found:
                on_field = found
                used_lid = lid
            if found >= exp:
                expected = exp
                break
        missing = sorted(expected - on_field)
        lang_ok = not missing
        report[lang] = {
            "lattice_id": used_lid,
            "on_field": len(on_field),
            "expected": len(expected),
            "missing": missing[:8],
            "pass": lang_ok,
        }
        ok = ok and lang_ok
    report["pass"] = ok
    return report


def merge_syllable_l1_from_ltm(state: dict, ltm_path: Path) -> dict[str, Any]:
    """Import immutable/open syllable lattice onto prism_memory."""
    state = ensure_prisms(state)
    ltm_path = ltm_path.resolve()
    if not ltm_path.is_file():
        raise FileNotFoundError(f"L1 syllable ltm missing: {ltm_path}")
    lat = read_ltm(ltm_path)
    import_lattice_into_prism(state, PRISM_MEMORY, "L1_syllable", lat)
    dec = decode_lattice(memory_lattices(state).get("L1_syllable") or {}, min_votes=1)
    syllables = [
        str(c.get("concept_id") or "")
        for c in dec.get("concepts") or []
        if str(c.get("concept_id") or "").startswith("syllable.")
    ]
    return {
        "lattice_id": "L1_syllable",
        "path": str(ltm_path),
        "syllable_concepts": len(syllables),
        "sample": sorted(s.replace("syllable.", "") for s in syllables)[:12],
    }


def boot_agent_core(
    store_dir: Path,
    *,
    root: Path | None = None,
    include_syllables: bool = True,
    include_bukvar_compose: bool = True,
    syllable_ltm: Path | None = None,
    bukvar_bundle: Path | None = None,
    persist: bool = True,
) -> dict[str, Any]:
    """Merge agent-core ltm (alphabet + keyboard) and syllable L1 into store runtime + ltm/."""
    root = (root or REPO_ROOT).resolve()
    store_dir = store_dir.resolve()
    boot = boot_store(store_dir, prefer_field_state=False)
    state = boot["state"]
    store = state.setdefault("store", {})
    store["store_id"] = store_dir.name
    store["locale"] = store.get("locale") or "ru"

    core = merge_core_ltm_stack(
        state,
        root=root,
        include_alphabet=True,
        include_vk=True,
    )
    syllable_rep: dict[str, Any] | None = None
    if include_syllables:
        syllable_rep = merge_syllable_l1_from_ltm(
            state,
            syllable_ltm or default_syllable_l1_ltm(root=root),
        )

    compose_rep: dict[str, Any] | None = None
    bundle_path = bukvar_bundle or default_bukvar_bundle(root=root)
    if include_bukvar_compose and bundle_path.is_file():
        bundle = _normalize_bukvar_bundle(json.loads(bundle_path.read_text(encoding="utf-8")))
        compose_rep = apply_story_compose(state, bundle)

    lattices = memory_lattices(state)
    vk_present = [lid for lid in VK_CORE_LATTICE_IDS if lid in lattices]
    alphabet_verify = _verify_grapheme_lattices(state)

    report: dict[str, Any] = {
        "store_dir": str(store_dir),
        "boot_source": boot.get("source"),
        "l2_shard_count": boot.get("l2_shard_count"),
        "core_ltm": core,
        "syllables": syllable_rep,
        "z_compose": compose_rep,
        "alphabet_verify": alphabet_verify,
        "vk_lattices": vk_present,
        "lattice_count": len(lattices),
        "field_version": state.get("field_version"),
    }

    if persist:
        mark_runtime_dirty(state)
        report["persist"] = save_runtime_state(
            store_dir,
            state,
            force=True,
            thin=True,
            sync_ltm_on_save=True,
        )
        manifest = build_manifest(store_dir, state)
        manifest["store_id"] = store_dir.name
        manifest["store_path"] = str(store_dir)
        (store_dir / "memory_manifest.json").write_text(
            json.dumps(manifest, ensure_ascii=False, indent=2) + "\n",
            encoding="utf-8",
        )
        (store_dir / "MEMORY.md").write_text(render_memory_md(manifest), encoding="utf-8")
        report["manifest_layer_count"] = len(manifest.get("lattice_stack") or [])

    return report


def main() -> None:
    p = argparse.ArgumentParser(description="Boot alphabet + syllables + VK layouts into agent store")
    p.add_argument("--store-dir", type=Path, default=None, help="Default: agents/von-neumann")
    p.add_argument("--syllable-ltm", type=Path, default=None)
    p.add_argument("--bukvar", type=Path, default=None)
    p.add_argument("--no-syllables", action="store_true")
    p.add_argument("--no-compose", action="store_true")
    p.add_argument("--dry-run", action="store_true", help="Merge in memory only; do not persist")
    args = p.parse_args()

    store = args.store_dir or default_agent_store()
    rep = boot_agent_core(
        store,
        syllable_ltm=args.syllable_ltm,
        bukvar_bundle=args.bukvar,
        include_syllables=not args.no_syllables,
        include_bukvar_compose=not args.no_compose,
        persist=not args.dry_run,
    )
    print(json.dumps(rep, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
