#!/usr/bin/env python3
"""Move tools/*.py implementations into casa/ and replace with shims (M2 big-bang batches)."""

from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
TOOLS = ROOT / "tools"

SHIM_HEADER = '''#!/usr/bin/env python3
"""Shim → {module} (M2 layout)."""
from _shim_v0 import load_casa

load_casa("{module}")
from {module} import *  # noqa: F403
'''

BOOTSTRAP = """from casa._paths import ensure_import_paths

ensure_import_paths()

"""

SKIP = frozenset({"_shim_v0.py"})

ALREADY_SHIM = re.compile(r'^"""Shim → casa\.', re.M)


def casa_module(casa_path: Path) -> str:
    rel = casa_path.relative_to(ROOT).with_suffix("")
    return ".".join(rel.parts)


def has_main(text: str) -> bool:
    return 'if __name__ == "__main__"' in text


def main_block(text: str) -> str | None:
    m = re.search(r'if __name__ == "__main__":\s*\n(.*)', text, re.S)
    if not m:
        return None
    body = m.group(1).rstrip()
    if "raise SystemExit(main())" in body or "main()" in body:
        return "main"
    return None


def insert_bootstrap(text: str) -> str:
    if "ensure_import_paths()" in text:
        return text
    marker = "from __future__ import annotations\n\n"
    if marker in text:
        return text.replace(marker, marker + BOOTSTRAP, 1)
    return BOOTSTRAP + text


def write_shim(tool_file: Path, module: str, *, main_name: str | None) -> None:
    lines = [SHIM_HEADER.format(module=module).rstrip()]
    if main_name:
        lines.extend(
            [
                "",
                'if __name__ == "__main__":',
                f"    from {module} import {main_name}",
                "",
                f"    raise SystemExit({main_name}())",
            ]
        )
    tool_file.write_text("\n".join(lines) + "\n", encoding="utf-8")


def migrate_one(name: str, casa_rel: str, *, dry_run: bool = False) -> str:
    if name in SKIP:
        return "skip"
    src = TOOLS / name
    if not src.exists():
        return f"missing:{name}"
    text = src.read_text(encoding="utf-8")
    if ALREADY_SHIM.search(text):
        return "shim"

    dst = ROOT / casa_rel
    module = casa_module(dst)

    if dst.exists():
        impl = dst.read_text(encoding="utf-8")
    else:
        impl = insert_bootstrap(text)
        if not dry_run:
            dst.parent.mkdir(parents=True, exist_ok=True)
            dst.write_text(impl, encoding="utf-8")

    main_name = main_block(text)
    if not dry_run:
        write_shim(src, module, main_name=main_name)
    return "moved"


def classify(name: str) -> str | None:
    """Return casa relative path or None to leave in tools/."""
    if name in SKIP or name.startswith("test_"):
        return None

    n = name

    # --- shared ---
    shared = {
        "config_io_v0.py",
        "codec_grid_v0.py",
        "codec_grid_v1.py",
        "codec_grid_v2.py",
        "codec_grid_v3.py",
        "field_write.py",
        "field_version_v0.py",
        "field_window.py",
        "field_planner_v0.py",
        "store_layout_v0.py",
        "prism_state_v0.py",
        "canonical.py",
        "semantic_payload.py",
        "nca_registry_v0.py",
        "nca_stale_shards_v0.py",
        "nca_train_core_v0.py",
        "nca_train_defaults_v0.py",
        "nca_train_util.py",
        "layered_nca_core.py",
        "module_finetune_util.py",
        "module_masks.py",
        "import_ltm_pack_v0.py",
        "export_ltm_pack_v0.py",
        "ltm_pack_v0.py",
        "store_boot_v0.py",
        "rebuild_field_from_ltm_v0.py",
        "rebuild_agent_store.py",
        "migrate_lattice_ids_v1.py",
        "migrate_prism_keys_v0.py",
        "migrate_l0_grapheme_split_v0.py",
        "migrate_l2_monolith_v0.py",
        "strip_legacy_l0_monolith_v0.py",
        "remigrate_l2_lex_v0.py",
        "build_bundle.py",
        "build_kb_bundle_tiers.py",
        "build_kb_bundles.py",
        "build_kb_modules.py",
        "extract_md_graph.py",
        "import_knowledge_delta.py",
        "kb_field_watcher.py",
        "kb_sync.py",
        "embeddings_layout.py",
        "layout_apply.py",
        "layered_infer.py",
        "llm_hook.py",
        "cide_act_bridge_v0.py",
        "agent_card.py",
        "ci_smoke_bench.py",
    }
    if n in shared:
        return f"casa/prisms/shared/{n}"

    # control (already under casa/prisms/control for some)
    control = {
        "control_stack_v0.py",
        "control_cylinders_v0.py",
        "control_tick_v0.py",
        "control_predict_v0.py",
        "control_attention_v0.py",
        "control_value_v0.py",
        "train_control_nca_stack_v0.py",
        "migrate_control_stack_v0.py",
        "migrate_control_all_stores_v0.py",
        "agent_sn_cen_tick.py",
        "sn_cen_infer.py",
        "sn_cen_runtime.py",
        "fpn_state.py",
        "init_control_lab_v0.py",
    }
    if n in control:
        return f"casa/prisms/control/{n}"

    if n.startswith("bench_control") or n in {"bench_predict_error_v0.py", "bench_predict_tick_v0.py"}:
        return f"casa/cli/bench/{n}"

    # hippo
    hippo_prefixes = (
        "sss_wake",
        "sss_sleep",
        "sleep_replay",
        "replay_buffer",
        "sss_episode",
        "sss_damage",
        "sss_repair",
        "sss_internal_repair",
        "sss_kolb",
        "sss_hypothesis",
        "run_sleep",
    )
    if any(n.startswith(p) for p in hippo_prefixes):
        return f"casa/prisms/hippo/{n}"

    # memory: sss_* (not hippo)
    if n.startswith("sss_"):
        return f"casa/prisms/memory/{n}"

    memory_patterns = (
        "grapheme_",
        "ortho_",
        "alphabet_",
        "keyboard_",
        "vk_",
        "bukvar_",
        "script_",
        "layout_tick",
        "lexicon_",
        "en_lexicon",
        "ru_lexicon",
        "entity_",
        "pos_",
        "f0_",
        "ingest_",
        "homoglyph",
        "hub_neighbors",
        "semantic_prior",
        "merge_preview",
        "input_modality",
        "extract_en_headwords",
        "extract_ru_headwords",
        "extract_lexicon",
        "split_ru_headwords",
        "normalize_afanasyev",
        "sanitize_afanasyev",
        "audit_afanasyev",
        "boot_alphabet",
        "boot_core_ltm",
        "boot_linked",
        "build_alphabet",
        "build_keyboard",
        "build_lexicon",
        "build_pos_bundle",
        "build_quad_headwords",
        "build_tech_headwords",
        "fetch_",
        "gen_kb_",
    )
    if any(n.startswith(p) for p in memory_patterns):
        return f"casa/prisms/memory/{n}"

    # tick / runtime
    tick = {
        "predictor_v0.py",
        "predict_tick_v0.py",
        "unified_tick_v0.py",
        "t9_runtime_v0.py",
        "surface_error_v0.py",
        "preflight_teacher_v0.py",
        "agent_autonomous_tick_v0.py",
        "run_agent_profile_v0.py",
        "run_t9_demo_cycle_v0.py",
        "critic_v0.py",
        "preview_critic_v0.py",
        "ortho_critic_v0.py",
        "ambiguous_prefix_v0.py",
        "articulation_grammar_v0.py",
        "articulation_realize_v0.py",
    }
    if n in tick:
        return f"casa/prisms/tick/{n}"

    if n.startswith("train_sss_nca"):
        return f"casa/prisms/memory/{n}"

    if n.startswith("bench_"):
        return f"casa/cli/bench/{n}"

    if n.startswith(("init_", "run_", "train_", "exp_", "compare_", "demo_", "repair_dmn")):
        return f"casa/cli/{n}"

    return None


BATCHES: dict[str, list[str]] = {
    "shared-core": [
        "config_io_v0.py",
        "codec_grid_v0.py",
        "codec_grid_v1.py",
        "codec_grid_v2.py",
        "codec_grid_v3.py",
        "field_write.py",
        "field_version_v0.py",
        "field_window.py",
        "field_planner_v0.py",
        "store_layout_v0.py",
        "prism_state_v0.py",
        "canonical.py",
        "semantic_payload.py",
    ],
    "shared-nca-store": [
        "nca_registry_v0.py",
        "nca_stale_shards_v0.py",
        "nca_train_core_v0.py",
        "nca_train_defaults_v0.py",
        "nca_train_util.py",
        "layered_nca_core.py",
        "module_finetune_util.py",
        "module_masks.py",
        "import_ltm_pack_v0.py",
        "export_ltm_pack_v0.py",
        "ltm_pack_v0.py",
        "store_boot_v0.py",
        "rebuild_field_from_ltm_v0.py",
        "rebuild_agent_store.py",
    ],
    "shared-migrate-kb": [
        "migrate_lattice_ids_v1.py",
        "migrate_prism_keys_v0.py",
        "migrate_l0_grapheme_split_v0.py",
        "migrate_l2_monolith_v0.py",
        "strip_legacy_l0_monolith_v0.py",
        "remigrate_l2_lex_v0.py",
        "build_bundle.py",
        "build_kb_bundle_tiers.py",
        "build_kb_bundles.py",
        "build_kb_modules.py",
        "extract_md_graph.py",
        "import_knowledge_delta.py",
        "kb_field_watcher.py",
        "kb_sync.py",
        "embeddings_layout.py",
        "layout_apply.py",
        "layered_infer.py",
        "llm_hook.py",
        "cide_act_bridge_v0.py",
        "agent_card.py",
        "ci_smoke_bench.py",
    ],
    "memory-sss-core": [
        "sss_cylinders_v0.py",
        "sss_stack_v0.py",
        "sss_l2_shard_v0.py",
        "sss_surface_v0.py",
        "sss_field.py",
        "sss_field_decode_v0.py",
        "sss_field_hypotheses_v0.py",
        "sss_field_intuition_v0.py",
        "sss_field_words_v0.py",
        "sss_read_v0.py",
        "sss_read_batch_v0.py",
        "sss_read_batch_parallel_v0.py",
        "sss_vocab_v0.py",
        "sss_vocab_surface_v0.py",
        "sss_word_candidates_v0.py",
        "sss_segment_v0.py",
        "sss_segment_en_v0.py",
        "sss_segment_candidates_v0.py",
        "sss_text_ingest_v0.py",
        "sss_text_listen_field_v0.py",
        "sss_text_stream_v0.py",
        "sss_text_tokenize_v0.py",
        "sss_nca_codec_v0.py",
        "sss_nca_repair_v0.py",
        "sss_memory_manifest_v0.py",
        "sss_merge_field_states_v0.py",
        "sss_self_correct_session_v0.py",
        "train_sss_nca_v0.py",
        "train_sss_nca_shards_v0.py",
    ],
    "hippo": [],  # filled below
    "memory-ortho-lexicon": [],  # filled below
    "control-cli": [],  # filled below
    "cli-bench": [],  # filled below
    "cli-misc": [],  # filled below
}

# Fill dynamic batches
for py in sorted(p.name for p in TOOLS.glob("*.py")):
    dest = classify(py)
    if not dest:
        continue
    if py in BATCHES["shared-core"] or py in BATCHES["shared-nca-store"] or py in BATCHES["shared-migrate-kb"] or py in BATCHES["memory-sss-core"]:
        continue
    if dest.startswith("casa/prisms/hippo/"):
        BATCHES["hippo"].append(py)
    elif dest.startswith("casa/prisms/memory/"):
        BATCHES["memory-ortho-lexicon"].append(py)
    elif dest.startswith("casa/prisms/control/") and py not in {
        "control_stack_v0.py",
        "control_cylinders_v0.py",
        "control_tick_v0.py",
        "control_predict_v0.py",
        "control_attention_v0.py",
        "control_value_v0.py",
    }:
        BATCHES["control-cli"].append(py)
    elif dest.startswith("casa/cli/bench/"):
        BATCHES["cli-bench"].append(py)
    elif dest.startswith("casa/cli/"):
        BATCHES["cli-misc"].append(py)
    elif dest.startswith("casa/prisms/tick/"):
        BATCHES["control-cli"].append(py)


def run_batch(batch: str, *, dry_run: bool = False) -> int:
    names = BATCHES.get(batch)
    if names is None:
        print(f"unknown batch: {batch}", file=sys.stderr)
        return 1
    moved = 0
    for name in names:
        dest = classify(name)
        if not dest:
            print(f"  skip (unclassified): {name}")
            continue
        status = migrate_one(name, dest, dry_run=dry_run)
        print(f"  {name} -> {dest} [{status}]")
        if status == "moved":
            moved += 1
    print(f"batch {batch}: {moved} moved")
    return 0


def main() -> int:
    p = argparse.ArgumentParser()
    p.add_argument("batch", choices=[*BATCHES.keys(), "all", "list"])
    p.add_argument("--dry-run", action="store_true")
    args = p.parse_args()
    if args.batch == "list":
        for k, v in BATCHES.items():
            print(f"{k}: {len(v)} files")
        return 0
    if args.batch == "all":
        for b in BATCHES:
            run_batch(b, dry_run=args.dry_run)
        return 0
    return run_batch(args.batch, dry_run=args.dry_run)


if __name__ == "__main__":
    raise SystemExit(main())
