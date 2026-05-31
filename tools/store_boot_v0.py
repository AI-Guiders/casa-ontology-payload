#!/usr/bin/env python3
"""Boot agent store from ltm/ + nca/ without requiring field_state.json."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

from field_write import load_field_state, save_field_state  # type: ignore
from import_ltm_pack_v0 import import_pack  # type: ignore
from sss_surface_v0 import surface_from_sss  # type: ignore
from control_cylinders_v0 import control_lattices, has_control_stack  # type: ignore
from sss_cylinders_v0 import ensure_prisms, memory_lattices  # type: ignore
from sss_stack_v0 import decode_lattice  # type: ignore
from lexicon_usage_axes_v0 import attach_axes_to_state, load_axes_jsonl  # type: ignore
from store_layout_v0 import field_state_path, ltm_root, nca_root  # type: ignore


def boot_store(
    store_dir: Path,
    *,
    prefer_field_state: bool = False,
    ltm_dir: Path | None = None,
) -> dict[str, Any]:
    """Load runtime state: ltm pack required; optional merge from field_state."""
    store_dir = store_dir.resolve()
    ltm = ltm_dir or ltm_root(store_dir)
    manifest_path = ltm / "pack.manifest.json"
    if not manifest_path.is_file():
        raise FileNotFoundError(f"ltm pack missing: {manifest_path}")

    fs_path = field_state_path(store_dir)
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    if prefer_field_state and fs_path.is_file():
        state = ensure_prisms(load_field_state(fs_path))
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
    state.setdefault("store", {})["boot_source"] = source
    state["store"]["store_id"] = store_dir.name
    state["store"]["ltm_dir"] = str(ltm)
    state["store"]["nca_root"] = str(nca_root(store_dir))

    axes_path = store_dir / "lexicon_axes.v0.jsonl"
    if axes_path.is_file():
        attach_axes_to_state(state, load_axes_jsonl(axes_path))

    nca_manifest = manifest.get("nca") or {}
    if nca_manifest:
        state["nca"] = {**(state.get("nca") or {}), **nca_manifest}

    lattices = memory_lattices(state)
    shard_count = sum(1 for k in lattices if k.startswith("L2_word_"))
    ctrl = control_lattices(state) if has_control_stack(state) else {}
    return {
        "source": source,
        "import": imp,
        "lattice_count": len(lattices),
        "control_lattice_count": len(ctrl),
        "l2_shard_count": shard_count,
        "field_version": state.get("field_version"),
        "state": state,
    }


def smoke_report(state: dict, *, lattice_id: str = "L2_word_00") -> dict[str, Any]:
    from predict_tick_v0 import predict_tick  # type: ignore

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
        bundle_path = Path(__file__).resolve().parent.parent / "lab/exp_l_v0/kb-math-concrete-schemas-l0.bundle.v1.json"
        if bundle_path.is_file():
            bundle = json.loads(bundle_path.read_text(encoding="utf-8"))
            st = predict_tick(state, "||", modality="schema", expect="math.two", bundle=bundle)
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
    if args.smoke:
        out["smoke"] = smoke_report(boot["state"], lattice_id=args.sample_lattice)

    if args.write:
        save_field_state(field_state_path(args.store_dir), boot["state"], compact=True)
        out["written"] = str(field_state_path(args.store_dir))

    print(json.dumps(out, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
