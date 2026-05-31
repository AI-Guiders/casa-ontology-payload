#!/usr/bin/env python3
"""Generate MEMORY.md + memory_manifest.json (KB-like hierarchy) and disk usage."""

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
from casa.prisms.memory.agent_journal import journal_stats
from casa.prisms.memory.nca_codec import tokens_from_lattice
from casa.prisms.shared.store_layout import rel_to_repo
from casa.prisms.shared.store_paths_v1 import manifest_layout_block


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


def build_manifest(store_dir: Path, state: dict) -> dict[str, Any]:
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
        layers.append(
            {
                "id": lid,
                "z_level": lat.get("z_level"),
                "role": "L2_shard" if is_l2_word_lattice(lid) and lid != LEGACY_L2 else "core",
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
        "examples_exp_reports": _dir_size(store_dir.parent.parent / "exp_sss_v1"),
    }

    return {
        "schema_version": 1,
        "kind": "sss_memory_manifest",
        **manifest_layout_block(),
        "store_id": store_dir.name,
        "store_path": rel_to_repo(store_dir),
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "field_version": state.get("field_version"),
        "schema": state.get("schema_version"),
        "l2_sharding": shard_stats(state),
        "prisms": ["prism_memory", "prism_hippo"],
        "lattice_stack": layers,
        "l2_network_ids": l2_word_lattice_ids(state),
        "journal": journal_stats(store_dir),
        "disk": disk,
    }


def render_memory_md(manifest: dict[str, Any]) -> str:
    lines = [
        f"# Memory map: `{manifest['store_id']}`",
        "",
        f"Generated: {manifest['generated_at']}",
        f"field_version: **{manifest.get('field_version')}**",
        "",
        "## Disk",
        "",
        f"| Path | Size |",
        f"|------|------|",
        f"| `field_state.json` | {manifest['disk']['field_state_human']} |",
        f"| store total | {manifest['disk']['store_total_human']} |",
        f"| `nca/` | {_fmt_bytes(manifest['disk']['nca_dir'])} |",
        f"| `_parallel_shards/` | {_fmt_bytes(manifest['disk']['parallel_shards_dir'])} |",
        "",
        "## Hierarchy (prism_memory)",
        "",
        "```text",
        "prism_memory",
    ]
    for row in manifest["lattice_stack"]:
        indent = "  " * (int(row.get("z_level") or 0) + 1)
        nca = " + NCA" if row.get("nca_model") else ""
        lines.append(f"{indent}{row['id']}  (tokens={row['token_count']}){nca}")
    lines.append("```")
    lines.append("")
    journal = manifest.get("journal") or {}
    if journal.get("entry_count"):
        lines.append("## Agent journal (not in ltm/)")
        lines.append("")
        lines.append(f"- entries: **{journal.get('entry_count')}** across {journal.get('domain_count')} domain(s)")
        for row in journal.get("domains") or []:
            lines.append(f"- `{row.get('domain')}`: {row.get('entry_count')} entries")
        lines.append("")
    sh = manifest.get("l2_sharding") or {}
    lines.append("## L2 sharding")
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
    active = [x for x in (sh.get("lattices") or []) if str(x.get("lattice_id", "")).startswith("L2_word_")]
    lines.append(f"- active shard lattices: {len(active)}")
    if sh.get("mode") == "lexicographic":
        lines.append("")
        lines.append("| Shard | Headword range (lex) | words in plan | tokens on grid |")
        lines.append("|-------|----------------------|---------------|----------------|")
        for row in active:
            lid = str(row.get("lattice_id", ""))
            if lid == "L2_word":
                continue
            label = row.get("lex_range") or "?"
            wc = row.get("lex_word_count")
            wc_s = str(wc) if wc is not None else "?"
            lines.append(f"| `{lid}` | {label} | {wc_s} | {row.get('token_count', 0)} |")
    lines.append("")
    lines.append("Regenerate: `python tools/memory_manifest.py --store-dir ... --write`")
    lines.append("")
    return "\n".join(lines)


def main() -> None:
    p = argparse.ArgumentParser()
    p.add_argument("--store-dir", type=Path, required=True)
    p.add_argument("--write", action="store_true", help="Write MEMORY.md + memory_manifest.json")
    p.add_argument("--compare-dir", type=Path, action="append", default=[], help="Extra stores for disk table")
    args = p.parse_args()

    path = args.store_dir / "field_state.json"
    state = ensure_prisms(load_field_state(path))
    manifest = build_manifest(args.store_dir, state)

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
        manifest["disk_compare"] = compare

    if args.write:
        (args.store_dir / "memory_manifest.json").write_text(
            json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8"
        )
        (args.store_dir / "MEMORY.md").write_text(render_memory_md(manifest), encoding="utf-8")

    print(json.dumps(manifest, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
