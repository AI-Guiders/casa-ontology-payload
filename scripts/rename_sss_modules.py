#!/usr/bin/env python3
"""Rename sss_* modules to semantic names; rewrite imports across repo."""

from __future__ import annotations

import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent

# old_stem → new_stem (file rename only; casa package path follows)
RENAMES: dict[str, str] = {
    # memory
    "memory_prisms": "memory_prisms",
    "surface": "surface",
    "lexicon_shard": "lexicon_shard",
    "stack": "stack",
    "vocab": "vocab",
    "vocab_surface": "vocab_surface",
    "memory_field": "memory_field",
    "field_decode": "field_decode",
    "field_hypotheses": "field_hypotheses",
    "field_intuition": "field_intuition",
    "field_words": "field_words",
    "segment": "segment",
    "segment_en": "segment_en",
    "segment_candidates": "segment_candidates",
    "text_stream": "text_stream",
    "text_ingest": "text_ingest",
    "text_listen_field": "text_listen_field",
    "text_tokenize": "text_tokenize",
    "read": "read",
    "read_batch": "read_batch",
    "read_batch_parallel": "read_batch_parallel",
    "word_candidates": "word_candidates",
    "self_correct_session": "self_correct_session",
    "nca_codec": "nca_codec",
    "nca_repair": "nca_repair",
    "memory_manifest": "memory_manifest",
    "merge_field_states": "merge_field_states",
    "train_memory_nca": "train_memory_nca",
    "train_memory_nca_shards": "train_memory_nca_shards",
    # hippo
    "wake": "wake",
    "wake_util": "wake_util",
    "wake_batch": "wake_batch",
    "sleep": "sleep",
    "sleep_all_nca": "sleep_all_nca",
    "sleep_nca_hook": "sleep_nca_hook",
    "episode": "episode",
    "hypothesis": "hypothesis",
    "kolb_cycle": "kolb_cycle",
    "kolb_reflect": "kolb_reflect",
    "damage": "damage",
    "repair": "repair",
    "repair_cli": "repair_cli",
    "internal_repair": "internal_repair",
    # bench
    "bench_corpus_coverage": "bench_corpus_coverage",
    "bench_damage_repair": "bench_damage_repair",
    "bench_heldout": "bench_heldout",
    "bench_hypothesis_compete": "bench_hypothesis_compete",
    "bench_kolb": "bench_kolb",
    "bench_lexicon_shard": "bench_lexicon_shard",
    "bench_lattice": "bench_lattice",
    "bench_nca_repair": "bench_nca_repair",
    "bench_segment_generalize": "bench_segment_generalize",
    "bench_sleep": "bench_sleep",
    "bench_text_ingest": "bench_text_ingest",
    "bench_vocab": "bench_vocab",
    "bench_vocab_growth": "bench_vocab_growth",
}


def _module_paths(stem: str) -> list[str]:
    """All casa.* module paths that end with .{stem}."""
    out: list[str] = []
    for py in (ROOT / "casa").rglob(f"{stem}.py"):
        rel = py.relative_to(ROOT / "casa").with_suffix("")
        out.append("casa." + ".".join(rel.parts))
    return out


def build_replace_map() -> dict[str, str]:
    """Map old module path fragments to new ones."""
    repl: dict[str, str] = {}
    for old, new in RENAMES.items():
        old_paths = _module_paths(old)
        new_paths = _module_paths(new)
        if not old_paths:
            # file not renamed yet — infer from first old path pattern
            for py in (ROOT / "casa").rglob(f"{old}.py"):
                rel = py.relative_to(ROOT / "casa").with_suffix("")
                old_mod = "casa." + ".".join(rel.parts)
                new_mod = old_mod.rsplit(".", 1)[0] + "." + new
                repl[old_mod] = new_mod
        else:
            for op in old_paths:
                parent = op.rsplit(".", 1)[0]
                repl[op] = f"{parent}.{new}"
    return repl


def rename_files() -> list[tuple[Path, Path]]:
    moved: list[tuple[Path, Path]] = []
    for old, new in RENAMES.items():
        for path in list((ROOT / "casa").rglob(f"{old}.py")):
            dest = path.with_name(f"{new}.py")
            if dest.is_file():
                print(f"skip exists: {dest.relative_to(ROOT)}", file=sys.stderr)
                continue
            path.rename(dest)
            moved.append((path, dest))
            print(f"rename {path.relative_to(ROOT)} → {dest.name}")
    return moved


def rewrite_text(content: str, repl: dict[str, str]) -> str:
    # longest keys first to avoid partial replacements
    for old, new in sorted(repl.items(), key=lambda x: -len(x[0])):
        content = content.replace(old, new)
    # CLI module names in strings/docs (legacy manifest keys)
    for old, new in sorted(RENAMES.items(), key=lambda x: -len(x[0])):
        content = re.sub(rf"\b{re.escape(old)}\b", new, content)
    return content


def rewrite_tree(root: Path, repl: dict[str, str], *, globs: tuple[str, ...]) -> int:
    changed = 0
    for pattern in globs:
        for path in root.rglob(pattern):
            if not path.is_file():
                continue
            if ".git" in path.parts:
                continue
            try:
                text = path.read_text(encoding="utf-8")
            except UnicodeDecodeError:
                continue
            new_text = rewrite_text(text, repl)
            if new_text != text:
                path.write_text(new_text, encoding="utf-8")
                changed += 1
    return changed


def main() -> int:
    repl_before = build_replace_map()
    # rename_files()  # already done
    repl = build_replace_map()
    repl.update(repl_before)
    n = rewrite_tree(ROOT, repl, globs=("*.py", "*.md", "*.json", "*.yml", "*.yaml", "*.toml"))
    print(f"rewrote {n} files")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
