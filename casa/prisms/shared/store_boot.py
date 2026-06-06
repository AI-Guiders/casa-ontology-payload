#!/usr/bin/env python3
"""Boot agent store from ltm/ + nca/ without requiring field_state.json."""

from __future__ import annotations

from casa._paths import REPO_ROOT, ensure_import_paths

ensure_import_paths()

import argparse
import json
from pathlib import Path
from typing import Any

from casa.prisms.shared.field_write import load_field_state, save_field_state
from casa.prisms.shared.import_ltm_pack import import_pack
from casa.prisms.memory.surface import surface_from_sss
from casa.prisms.control.cylinders import control_lattices, has_control_stack
from casa.prisms.memory.memory_prisms import ensure_prisms, memory_lattices
from casa.prisms.memory.stack import decode_lattice
from casa.prisms.memory.lexicon_usage_axes import attach_axes_to_state, load_axes_jsonl
from casa.prisms.memory.lexicon_shard import is_l2_word_lattice
from casa.prisms.shared.store_layout import field_state_path, ltm_root, nca_root, agent_prism_root


def apply_store_boot_profile(store_dir: Path, state: dict) -> None:
    """Merge store profile (manifest) into runtime state + router default."""
    store_dir = store_dir.resolve()
    store = state.setdefault("store", {})
    store["store_id"] = store_dir.name

    profile_path = store_dir / "memory_manifest.json"
    if profile_path.is_file():
        try:
            profile = json.loads(profile_path.read_text(encoding="utf-8"))
        except json.JSONDecodeError:
            profile = {}
        if isinstance(profile, dict):
            if profile.get("locale"):
                store["locale"] = str(profile["locale"])
            if profile.get("default_content_prism"):
                store["default_content_prism"] = str(profile["default_content_prism"])
            mode = profile.get("ingest_episodic_mode")
            if isinstance(mode, str) and mode in ("off", "surprise_only", "full"):
                store["ingest_episodic_mode"] = mode
            prisms_block = profile.get("prisms")
            if isinstance(prisms_block, dict) and prisms_block.get("default_content_prism"):
                store["default_content_prism"] = str(prisms_block["default_content_prism"])

    default_prism = store.get("default_content_prism")
    if default_prism:
        from casa.domain.prism_wire import prism_router

        prism_router(state)["default_content_prism"] = str(default_prism)


def boot_store(
    store_dir: Path,
    *,
    prefer_field_state: bool = False,
    ltm_dir: Path | None = None,
) -> dict[str, Any]:
    """Load agent store: **shipped** tier (ltm/) or resume **runtime checkpoint** (field_state)."""
    store_dir = store_dir.resolve()
    from casa.domain.store_recovery import load_ltm_pack_manifest, recover_store_checkpoints

    recovery = recover_store_checkpoints(store_dir, persist_thin=False)
    ltm = ltm_dir or ltm_root(store_dir)
    manifest_path = ltm / "pack.manifest.json"
    if not manifest_path.is_file():
        load_ltm_pack_manifest(ltm, store_dir=store_dir)

    fs_path = field_state_path(store_dir)
    manifest = load_ltm_pack_manifest(ltm, store_dir=store_dir)
    if prefer_field_state and fs_path.is_file():
        state = ensure_prisms(load_field_state(fs_path, store_dir=store_dir))
        source = "field_state"
        # Do not import_pack lattice bodies — stale ltm can overwrite a full field (see ru-lexicon 92-word regression).
        imp = {
            "loaded": [],
            "loaded_control": [],
            "lattice_count": 0,
            "control_lattice_count": 0,
            "skipped_ltm_lattice_import": True,
        }
        if manifest.get("nca"):
            state["nca"] = {**(state.get("nca") or {}), **manifest["nca"]}
    else:
        state = ensure_prisms({"schema_version": "multi_prism_v1", "field_version": 0})
        source = "ltm_only"
        imp = import_pack(state, ltm, manifest=manifest)
    apply_store_boot_profile(store_dir, state)
    state.setdefault("store", {})["boot_source"] = source
    state["store"]["ltm_dir"] = str(ltm)
    state["store"]["nca_root"] = str(nca_root(store_dir))

    axes_path = store_dir / "lexicon_axes.jsonl"
    if axes_path.is_file():
        sidecar = load_axes_jsonl(axes_path)
        attach_axes_to_state(state, sidecar, materialize_field=True)

    nca_manifest = manifest.get("nca") or {}
    if nca_manifest:
        state["nca"] = {**(state.get("nca") or {}), **nca_manifest}

    lattices = memory_lattices(state)
    shard_count = sum(1 for k in lattices if is_l2_word_lattice(k))
    ctrl = control_lattices(state) if has_control_stack(state) else {}

    from casa.prisms.memory.agent_prism import load_agent_prism

    agent_load: dict[str, Any] | None = None
    if agent_prism_root(store_dir).is_dir():
        agent_load = load_agent_prism(store_dir, state)

    from casa.domain.consistency_oracle import (
        apply_repair_homeostasis,
        assess_field_consistency,
        persist_consistency_note,
    )
    from casa.domain.router_boot_probe import run_router_boot_probe

    consistency = assess_field_consistency(store_dir, state)
    router_probe = run_router_boot_probe(state, store_dir=store_dir)
    repair = apply_repair_homeostasis(state, consistency)
    persist_consistency_note(store_dir, consistency)

    return {
        "source": source,
        "import": imp,
        "lattice_count": len(lattices),
        "control_lattice_count": len(ctrl),
        "l2_shard_count": shard_count,
        "field_version": state.get("field_version"),
        "agent_prism": agent_load,
        "state": state,
        "store_recovery": recovery,
        "consistency": consistency,
        "router_probe": router_probe,
        "repair_homeostasis": repair,
    }


def smoke_report(state: dict, *, lattice_id: str = "L2_word_00") -> dict[str, Any]:
    from casa.prisms.tick.predict_tick import predict_tick

    lattices = memory_lattices(state)
    rep: dict[str, Any] = {"lattices": len(lattices)}
    if lattice_id in lattices:
        dec = decode_lattice(lattices[lattice_id], min_votes=1)
        rep["sample_lattice"] = lattice_id
        rep["sample_concepts"] = len(dec.get("concept_ids") or [])
        rep["sample_seen_tokens"] = dec.get("seen_tokens")
        try:
            surf = surface_from_sss(state, lattice_id=lattice_id, prompt="мама")
            rep["surface_ok"] = bool(surf.get("active"))
            rep["surface_sample"] = surf.get("surface_text", "")[:120]
        except Exception as ex:
            rep["surface_ok"] = False
            rep["surface_error"] = str(ex)
    try:
        tick = predict_tick(state, "мам", modality="t9", expect="мама")
        rep["predict_tick_ok"] = tick["verdict"] in ("pass", "provisional")
        rep["predict_tick_anchors"] = [
            a.get("word") for a in (tick.get("predict") or {}).get("anchors") or []
        ][:6]
    except Exception as ex:
        rep["predict_tick_ok"] = False
        rep["predict_tick_error"] = str(ex)
    try:
        bundle_path = REPO_ROOT / "lab/exp_l/kb-math-concrete-schemas-l0.bundle.v1.json"
        if bundle_path.is_file():
            bundle = json.loads(bundle_path.read_text(encoding="utf-8"))
            st = predict_tick(state, "||", modality="schema", expect="math.num.two", bundle=bundle)
            rep["schema_tick_ok"] = st["verdict"] in ("pass", "provisional")
            rep["schema_tick_hypothesis"] = (st.get("predict") or {}).get("hypothesis")
    except Exception as ex:
        rep["schema_tick_ok"] = False
        rep["schema_tick_error"] = str(ex)
    return rep


def main() -> None:
    p = argparse.ArgumentParser(description="Boot store from ltm/ (+ optional field_state)")
    p.add_argument("--store-dir", type=Path, required=True)
    p.add_argument("--ltm-dir", type=Path, default=None)
    p.add_argument("--prefer-field-state", action="store_true")
    p.add_argument("--write", action="store_true", help="Write merged state to field_state.json")
    p.add_argument("--smoke", action="store_true")
    p.add_argument("--sample-lattice", default="L2_word_00")
    args = p.parse_args()

    boot = boot_store(
        args.store_dir,
        prefer_field_state=args.prefer_field_state,
        ltm_dir=args.ltm_dir,
    )
    out: dict[str, Any] = {
        "source": boot["source"],
        "import": boot["import"],
        "lattice_count": boot["lattice_count"],
        "l2_shard_count": boot["l2_shard_count"],
        "field_version": boot["field_version"],
    }
    if boot.get("agent_prism"):
        out["agent_prism"] = boot["agent_prism"]
    if args.smoke:
        out["smoke"] = smoke_report(boot["state"], lattice_id=args.sample_lattice)

    if args.write:
        save_field_state(field_state_path(args.store_dir), boot["state"], compact=True)
        out["written"] = str(field_state_path(args.store_dir))

    print(json.dumps(out, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
