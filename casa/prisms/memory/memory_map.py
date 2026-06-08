#!/usr/bin/env python3
"""Generate MEMORY.md (human map) and optional JSON summary/inventory."""

from __future__ import annotations

from casa._paths import ensure_import_paths

ensure_import_paths()

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from casa.prisms.shared.field_write import load_field_state
from casa.prisms.memory.memory_prisms import ensure_prisms, memory_lattices
from casa.prisms.memory.lexicon_shard import LEGACY_L2, is_l2_word_lattice, l2_word_lattice_ids, nca_model_registry, shard_stats
from casa.prisms.memory.phrase_shard import LEGACY_L3, is_l3_phrase_lattice, phrase_shard_stats
from casa.prisms.memory.agent_journal import journal_stats
from casa.prisms.memory.nca_codec import tokens_from_lattice
from casa.prisms.shared.memory_layer_names import (
    layer_sort_key,
    memory_layer_for_lattice_id,
    memory_layer_heading,
    z_level_for_memory_layer,
)
from casa.prisms.shared.store_layout import rel_to_repo
from casa.prisms.shared.store_paths_v1 import manifest_layout_block

MEMORY_MAP_MD = "MEMORY.md"
MEMORY_MAP_SUMMARY_JSON = "memory_map.summary.json"
MEMORY_MAP_INVENTORY_JSON = "memory_map.inventory.json"
LEGACY_MANIFEST_JSON = "memory_manifest.json"


def _dir_size(path: Path) -> int:
    if not path.exists():
        return 0
    if path.is_file():
        return path.stat().st_size
    total = 0
    for p in path.rglob("*"):
        if p.is_file():
            try:
                total += p.stat().st_size
            except OSError:
                pass
    return total


def _fmt_bytes(n: int) -> str:
    if n >= 1 << 30:
        return f"{n / (1 << 30):.2f} GiB"
    if n >= 1 << 20:
        return f"{n / (1 << 20):.1f} MiB"
    if n >= 1 << 10:
        return f"{n / (1 << 10):.1f} KiB"
    return f"{n} B"


def _shard_tier_summary(block: dict[str, Any] | None) -> dict[str, Any]:
    sh = block or {}
    lattices = list(sh.get("lattices") or [])
    return {
        "enabled": sh.get("enabled"),
        "mode": sh.get("mode"),
        "lex_plan": sh.get("lex_plan"),
        "num_shards": sh.get("num_shards"),
        "indexed_words": sh.get("indexed_words"),
        "indexed_tokens": sh.get("indexed_tokens"),
        "active_shard_lattices": len(lattices),
        "shard_naming": sh.get("shard_naming"),
    }


def build_memory_map(store_dir: Path, state: dict) -> dict[str, Any]:
    """Full in-memory map (feeds MEMORY.md and optional inventory JSON)."""
    store_dir = store_dir.resolve()
    state = ensure_prisms(state)
    lattices = memory_lattices(state)
    fs_path = store_dir / "field_state.json"
    fs_bytes = fs_path.stat().st_size if fs_path.is_file() else 0

    layers: list[dict[str, Any]] = []
    for lid in sorted(lattices.keys(), key=lambda x: (lattices[x].get("z_level", 0), x)):
        lat = lattices[lid]
        toks = tokens_from_lattice(lat)
        nca_path = nca_model_registry(state).get(lid)
        nca_bytes = Path(nca_path).stat().st_size if nca_path and Path(nca_path).is_file() else 0
        mem_layer = memory_layer_for_lattice_id(lid)
        layers.append(
            {
                "id": lid,
                "z_level": lat.get("z_level") if lat.get("z_level") is not None else z_level_for_memory_layer(mem_layer),
                "memory_layer": mem_layer,
                "role": "L2_shard" if is_l2_word_lattice(lid) and lid != LEGACY_L2 else (
                    "L3_shard" if is_l3_phrase_lattice(lid) and lid not in (LEGACY_L3, "phrases") else "core"
                ),
                "width": lat.get("width"),
                "height": lat.get("height"),
                "token_count": len(toks),
                "word_concepts": sum(1 for t in toks if t.startswith("C:lang.word.")),
                "nca_model": rel_to_repo(nca_path),
                "nca_bytes": nca_bytes,
            }
        )

    nca_dir = store_dir / "nca"
    parallel = store_dir / "_parallel_shards"
    disk = {
        "field_state_json": fs_bytes,
        "field_state_human": _fmt_bytes(fs_bytes),
        "store_total": _dir_size(store_dir),
        "store_total_human": _fmt_bytes(_dir_size(store_dir)),
        "nca_dir": _dir_size(nca_dir),
        "parallel_shards_dir": _dir_size(parallel),
        "examples_exp_reports": _dir_size(store_dir.parent.parent / "exp_lexicon_v1"),
    }

    return {
        "schema_version": 1,
        "kind": "lexicon_memory_map",
        **manifest_layout_block(),
        "store_id": store_dir.name,
        "store_path": rel_to_repo(store_dir),
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "field_version": state.get("field_version"),
        "schema": state.get("schema_version"),
        "l2_sharding": shard_stats(state),
        "l3_sharding": phrase_shard_stats(state),
        "prisms": ["prism_memory", "prism_hippo"],
        "lattice_stack": layers,
        "l2_network_ids": l2_word_lattice_ids(state),
        "journal": journal_stats(store_dir),
        "disk": disk,
    }


def build_memory_map_summary(full: dict[str, Any]) -> dict[str, Any]:
    """Compact JSON for scripts — no per-lattice dump."""
    stack = list(full.get("lattice_stack") or [])
    by_layer: dict[str, int] = {}
    for row in stack:
        layer = str(row.get("memory_layer") or "unknown")
        by_layer[layer] = by_layer.get(layer, 0) + 1
    return {
        "schema_version": 1,
        "kind": "lexicon_memory_map_summary",
        "store_id": full.get("store_id"),
        "store_path": full.get("store_path"),
        "generated_at": full.get("generated_at"),
        "field_version": full.get("field_version"),
        "schema": full.get("schema"),
        "l2": _shard_tier_summary(full.get("l2_sharding")),
        "l3": _shard_tier_summary(full.get("l3_sharding")),
        "lattice_count": len(stack),
        "lattice_count_by_layer": by_layer,
        "l2_network_ids": list(full.get("l2_network_ids") or []),
        "journal": dict(full.get("journal") or {}),
        "disk": dict(full.get("disk") or {}),
        "human_map_file": MEMORY_MAP_MD,
    }


def build_manifest(store_dir: Path, state: dict) -> dict[str, Any]:
    """Deprecated alias — use build_memory_map."""
    return build_memory_map(store_dir, state)


def render_memory_md(memory_map: dict[str, Any]) -> str:
    lines = [
        f"# Memory map: `{memory_map['store_id']}`",
        "",
        f"Generated: {memory_map['generated_at']}",
        f"field_version: **{memory_map.get('field_version')}**",
        "",
        "> Human-readable map of the agent store. Machine summary: `memory_map.summary.json`.",
        "",
        "## Disk",
        "",
        "| Path | Size |",
        "|------|------|",
        f"| `field_state.json` | {memory_map['disk']['field_state_human']} |",
        f"| store total | {memory_map['disk']['store_total_human']} |",
        f"| `nca/` | {_fmt_bytes(memory_map['disk']['nca_dir'])} |",
        f"| `_parallel_shards/` | {_fmt_bytes(memory_map['disk']['parallel_shards_dir'])} |",
        "",
        "## Hierarchy (prism_memory)",
        "",
        "Слои: **memory.grapheme** (T0) → **memory.syllable** (T1) → **memory.lexicon** (T2) → **memory.phrase** (T3).",
        "Legacy L0…L3 / lattice_id в скобках — только для migrate.",
        "",
        "```text",
        "prism_memory",
    ]
    l3_by_id = {
        str(r.get("lattice_id")): r
        for r in (memory_map.get("l3_sharding") or {}).get("lattices") or []
    }
    by_layer: dict[str, list[dict[str, Any]]] = {}
    for row in memory_map["lattice_stack"]:
        r = dict(row)
        l3 = l3_by_id.get(str(r.get("id") or ""))
        if l3:
            r.setdefault("token_range", l3.get("token_range"))
            r.setdefault("token_hint", l3.get("token_hint"))
            r.setdefault("shard_index", l3.get("shard_index"))
        layer = str(r.get("memory_layer") or memory_layer_for_lattice_id(str(r.get("id") or "")))
        by_layer.setdefault(layer, []).append(r)
    for shard_row in (memory_map.get("l2_sharding") or {}).get("lattices") or []:
        lid = str(shard_row.get("lattice_id") or "")
        if not lid or any(r.get("id") == lid for r in memory_map["lattice_stack"]):
            continue
        layer = memory_layer_for_lattice_id(lid)
        by_layer.setdefault(layer, []).append(
            {
                "id": lid,
                "token_count": shard_row.get("token_count", 0),
                "nca_model": None,
                "lex_range": shard_row.get("lex_range"),
            }
        )
    for shard_row in (memory_map.get("l3_sharding") or {}).get("lattices") or []:
        lid = str(shard_row.get("lattice_id") or "")
        if not lid or any(r.get("id") == lid for r in memory_map["lattice_stack"]):
            continue
        layer = memory_layer_for_lattice_id(lid)
        by_layer.setdefault(layer, []).append(
            {
                "id": lid,
                "token_count": shard_row.get("token_count", 0),
                "nca_model": None,
                "token_range": shard_row.get("token_range"),
                "token_hint": shard_row.get("token_hint"),
            }
        )

    def _shard_row_sort(row: dict[str, Any]) -> tuple:
        sid = row.get("shard_index")
        if sid is not None:
            return (0, int(sid), str(row.get("id") or ""))
        return (1, str(row.get("id") or ""))

    for layer in sorted(by_layer.keys(), key=layer_sort_key):
        lines.append(f"  {memory_layer_heading(layer)}")
        for row in sorted(by_layer[layer], key=_shard_row_sort):
            nca = " + NCA" if row.get("nca_model") else ""
            extra = f" · {row['lex_range']}" if row.get("lex_range") else ""
            if row.get("token_range"):
                hint = row.get("token_hint") or "entity/word tokens"
                extra = f" · {row['token_range']} ({hint})"
            idx = row.get("shard_index")
            idx_s = f" [#{idx:02d}]" if idx is not None else ""
            lines.append(f"    {row['id']}{idx_s}  (tokens={row.get('token_count', 0)}){nca}{extra}")
    lines.append("```")
    lines.append("")
    journal = memory_map.get("journal") or {}
    if journal.get("entry_count"):
        lines.append("## Agent journal (not in ltm/)")
        lines.append("")
        lines.append(f"- entries: **{journal.get('entry_count')}** across {journal.get('domain_count')} domain(s)")
        for row in journal.get("domains") or []:
            lines.append(f"- `{row.get('domain')}`: {row.get('entry_count')} entries")
        lines.append("")
    sh = memory_map.get("l2_sharding") or {}
    lines.append("## memory.lexicon — sharding")
    lines.append("")
    lines.append(f"- enabled: {sh.get('enabled')}")
    lines.append(f"- mode: **{sh.get('mode', 'lexicographic')}**")
    lines.append(f"- lex_plan: **{sh.get('lex_plan', 'corpus_quantile')}**")
    lines.append(f"- shards: {sh.get('num_shards')}")
    lines.append(f"- indexed words: {sh.get('indexed_words')}")
    initials = sh.get("attested_initial_letters") or []
    if initials:
        preview = ", ".join(str(c) for c in initials[:24])
        suffix = "…" if len(initials) > 24 else ""
        lines.append(f"- attested word-initial letters ({len(initials)}): {preview}{suffix}")
    active = [
        x
        for x in (sh.get("lattices") or [])
        if is_l2_word_lattice(str(x.get("lattice_id", "")))
        and str(x.get("lattice_id", "")) not in (LEGACY_L2, "lexicon-ru", "lexicon-en")
    ]
    lines.append(f"- active shard lattices: {len(active)}")
    if sh.get("mode") == "lexicographic":
        lines.append("")
        naming = sh.get("shard_naming") or "numeric"
        lines.append(f"- shard naming: **{naming}**")
        lines.append("")
        lines.append("| Shard id | Headword range (lex) | words in plan | tokens on grid |")
        lines.append("|----------|----------------------|---------------|----------------|")
        for row in active:
            lid = str(row.get("lattice_id", ""))
            label = row.get("lex_range") or "?"
            wc = row.get("lex_word_count")
            wc_s = str(wc) if wc is not None else "?"
            lines.append(f"| `{lid}` | {label} | {wc_s} | {row.get('token_count', 0)} |")
    l3 = memory_map.get("l3_sharding") or {}
    if l3.get("lattices"):
        lines.append("")
        lines.append("## memory.phrase — sharding")
        lines.append("")
        lines.append(f"- enabled: {l3.get('enabled')}")
        lines.append(f"- mode: **{l3.get('mode', 'lexicographic')}**")
        lines.append(f"- plan: **{l3.get('lex_plan', 'corpus_quantile')}**")
        lines.append(f"- shards: {l3.get('num_shards')}")
        lines.append(f"- indexed tokens: {l3.get('indexed_tokens')}")
        lines.append(f"- shard naming: **{l3.get('shard_naming') or 'numeric'}**")
        lines.append(f"- hint: field **entity / word / meta** tokens (not headwords)")
        active_l3 = [
            x
            for x in (l3.get("lattices") or [])
            if is_l3_phrase_lattice(str(x.get("lattice_id", "")))
            and str(x.get("lattice_id", "")) not in (LEGACY_L3, "phrases")
        ]
        lines.append(f"- active shard lattices: {len(active_l3)}")
        lines.append("")
        lines.append("| idx | Shard id | Token range (label) | kind | plan | on grid |")
        lines.append("|-----|----------|---------------------|------|------|---------|")
        for row in sorted(active_l3, key=lambda r: int(r.get("shard_index") if r.get("shard_index") is not None else 999)):
            lid = str(row.get("lattice_id", ""))
            idx = row.get("shard_index")
            idx_s = f"{idx:02d}" if idx is not None else "?"
            label = row.get("token_range") or "?"
            hint = row.get("token_hint") or "entity/word"
            plan = row.get("plan_token_count")
            plan_s = str(plan) if plan is not None else "?"
            lines.append(
                f"| {idx_s} | `{lid}` | {label} | {hint} | {plan_s} | {row.get('token_count', 0)} |"
            )
    lines.append("")
    lines.append(
        "Regenerate: `python -m casa.prisms.memory.memory_map --store-dir ... --write` "
        f"(writes {MEMORY_MAP_MD} + {MEMORY_MAP_SUMMARY_JSON})"
    )
    lines.append("")
    return "\n".join(lines)


def write_memory_map_artifacts(
    store_dir: Path,
    memory_map: dict[str, Any],
    *,
    write_inventory: bool = False,
) -> dict[str, str]:
    store_dir = store_dir.resolve()
    summary = build_memory_map_summary(memory_map)
    paths = {
        "md": str(store_dir / MEMORY_MAP_MD),
        "summary": str(store_dir / MEMORY_MAP_SUMMARY_JSON),
    }
    (store_dir / MEMORY_MAP_MD).write_text(render_memory_md(memory_map), encoding="utf-8")
    (store_dir / MEMORY_MAP_SUMMARY_JSON).write_text(
        json.dumps(summary, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    legacy = store_dir / LEGACY_MANIFEST_JSON
    if legacy.is_file():
        legacy.unlink()
    if write_inventory:
        inv_path = store_dir / MEMORY_MAP_INVENTORY_JSON
        inv_path.write_text(json.dumps(memory_map, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        paths["inventory"] = str(inv_path)
    return paths


def main() -> None:
    p = argparse.ArgumentParser(description="Memory map — MEMORY.md + optional JSON")
    p.add_argument("--store-dir", type=Path, required=True)
    p.add_argument(
        "--write",
        action="store_true",
        help=f"Write {MEMORY_MAP_MD} + {MEMORY_MAP_SUMMARY_JSON}",
    )
    p.add_argument(
        "--inventory-json",
        action="store_true",
        help=f"With --write, also dump full lattice inventory to {MEMORY_MAP_INVENTORY_JSON}",
    )
    p.add_argument("--compare-dir", type=Path, action="append", default=[], help="Extra stores for disk table")
    args = p.parse_args()

    path = args.store_dir / "field_state.json"
    state = ensure_prisms(load_field_state(path, store_dir=args.store_dir))
    memory_map = build_memory_map(args.store_dir, state)

    compare: list[dict[str, Any]] = []
    for d in args.compare_dir:
        dp = Path(d)
        compare.append(
            {
                "store_id": dp.name,
                "store_total": _dir_size(dp),
                "store_total_human": _fmt_bytes(_dir_size(dp)),
                "field_state": (dp / "field_state.json").stat().st_size if (dp / "field_state.json").is_file() else 0,
            }
        )
    if compare:
        memory_map["disk_compare"] = compare

    if args.write:
        write_memory_map_artifacts(args.store_dir, memory_map, write_inventory=args.inventory_json)

    print(json.dumps(build_memory_map_summary(memory_map), ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
