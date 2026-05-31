#!/usr/bin/env python3
"""
End-to-end SN + CEN infer: DMN repair OR field_state hot path -> digest -> SN -> CEN.

Modes:
  default     — damage + NCA repair (~3s)
  --from-field — decode agent field_state.json directly (~ms)
"""

from __future__ import annotations

from casa._paths import ensure_import_paths

ensure_import_paths()

import argparse
import json
import time
from pathlib import Path

import torch

from casa.prisms.shared.agent_card import read_agent_card, resolve_checkpoint
from casa.cli.bench.bench_dmn_nca_union import _grid_to_union_tensor, _threshold_grid_from_union_state
from casa.prisms.shared.canonical import CANONICAL_CONCEPT_MODE, CANONICAL_FIELD_MIN_VOTES, CANONICAL_MIN_VOTES, CANONICAL_THRESHOLD
from casa.prisms.shared.codec_grid import decode_grid, score_recovery
from casa.prisms.shared.field_write import bundle_from_field_state, decode_field_grid, field_state_stale, load_field_state
from casa.prisms.shared.layout_apply import _get_region_rect, damage_region_patches, mask_outside_region
from casa.prisms.control.sn_cen_runtime import cen_plan, digest_from_decoded, sn_route, task_to_dict
from casa.cli.train_dmn_nca import UpdateRule, nca_rollout_eval, sobel_kernels


def _read_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def _load_dmn(path: Path, device: torch.device) -> tuple[UpdateRule, list[str], int]:
    ckpt = torch.load(path, map_location="cpu", weights_only=False)
    token_ids = list(ckpt["token_ids"])
    ch = int(ckpt["channel_n"])
    rule = UpdateRule(channel_n=ch, hidden=int(ckpt["hidden"])).to(device)
    rule.load_state_dict(ckpt["state_dict"])
    rule.eval()
    return rule, token_ids, ch


def _run_dmn_repair(
    bundle: dict,
    model_path: Path,
    *,
    layout: dict,
    damage_patches: int,
    seed: int,
    steps: int,
    device: torch.device,
) -> tuple[dict, dict]:
    from casa.prisms.shared.codec_grid_v3 import encode_bundle_to_grid

    rect = _get_region_rect(layout, "dmn_ontology")
    full = encode_bundle_to_grid(bundle, width=64, height=64, copies=7, concept_mode=CANONICAL_CONCEPT_MODE)
    target = mask_outside_region(full, rect)
    damaged = damage_region_patches(target, rect, patch_w=8, patch_h=8, count=damage_patches, seed=seed)

    rule, token_ids, ch = _load_dmn(model_path, device)
    token_count = len(token_ids)
    token_to_i = {t: i for i, t in enumerate(token_ids)}
    inp = _grid_to_union_tensor(damaged, token_to_i, device)
    x0 = torch.zeros(1, ch, 64, 64, device=device)
    x0[:, :token_count] = inp
    kx, ky = sobel_kernels(device)
    with torch.no_grad():
        xT = nca_rollout_eval(rule, x0, kx, ky, steps=steps)
    grid_logits = _threshold_grid_from_union_state(xT, token_ids=token_ids, threshold=CANONICAL_THRESHOLD)
    decoded = decode_grid(grid_logits, min_votes=CANONICAL_MIN_VOTES)
    score = score_recovery(bundle, decoded)
    return decoded, score


def _run_from_field(
    field_path: Path,
    store_dir: Path,
    *,
    min_votes: int,
) -> tuple[str, dict, dict, dict, float, dict]:
    t0 = time.perf_counter()
    state = load_field_state(field_path)
    bundle_name, bundle = bundle_from_field_state(state, store_dir=store_dir)
    decoded = decode_field_grid(state, min_votes=min_votes)
    score = score_recovery(bundle, decoded)
    ms = (time.perf_counter() - t0) * 1000
    return bundle_name, bundle, decoded, score, ms, state


def _layered_gate_digest(
    bundle: dict,
    dmn_path: Path,
    digest_path: Path | None,
    gate_path: Path | None,
    *,
    layout: dict,
    damage_patches: int,
    seed: int,
    device: torch.device,
) -> tuple[list[float], list[float]]:
    from casa.prisms.shared.layered_nca_core import grid_to_layered_state, load_dmn_rule, run_piston_pipeline
    from casa.prisms.shared.codec_grid_v3 import encode_bundle_to_grid

    rect = _get_region_rect(layout, "dmn_ontology")
    full = encode_bundle_to_grid(bundle, width=64, height=64, copies=7, concept_mode=CANONICAL_CONCEPT_MODE)
    target = mask_outside_region(full, rect)
    damaged = damage_region_patches(target, rect, patch_w=8, patch_h=8, count=damage_patches, seed=seed)

    dmn_rule, token_ids, dm_c, field_layout = load_dmn_rule(dmn_path, device)
    digest_rule = gate_rule = None
    if digest_path and digest_path.is_file():
        dck = torch.load(digest_path, map_location="cpu", weights_only=False)
        digest_rule = UpdateRule(channel_n=int(dck["channel_n"]), hidden=int(dck["hidden"])).to(device)
        digest_rule.load_state_dict(dck["state_dict"])
        digest_rule.eval()
    if gate_path and gate_path.is_file():
        gck = torch.load(gate_path, map_location="cpu", weights_only=False)
        gate_rule = UpdateRule(channel_n=int(gck["channel_n"]), hidden=int(gck["hidden"])).to(device)
        gate_rule.load_state_dict(gck["state_dict"])
        gate_rule.eval()

    x = grid_to_layered_state(damaged, token_ids, field_layout, device)
    with torch.no_grad():
        x = run_piston_pipeline(
            x,
            field_layout=field_layout,
            layout_json=layout,
            dmn_rule=dmn_rule,
            dm_channel_n=dm_c,
            digest_rule=digest_rule,
            gate_rule=gate_rule,
            run_gate=True,
        )
    dv = x[0, field_layout.digest_slice].mean(dim=(1, 2)).detach().cpu().tolist()
    gv = x[0, field_layout.gate_slice].mean(dim=(1, 2)).detach().cpu().tolist()
    return dv, gv


def main() -> None:
    p = argparse.ArgumentParser(description="SN + CEN infer v1")
    p.add_argument("--bundle", type=Path, default=None, help="Bundle JSON (optional with --from-field)")
    p.add_argument("--from-field", action="store_true", help="Hot path: decode field_state, skip NCA")
    p.add_argument("--field-state", type=Path, default=None)
    p.add_argument("--store-dir", type=Path, default=Path("lab/agent-stores/research-agent-lab"))
    p.add_argument("--agent-card", type=Path, default=Path("lab/agent-cards/research-agent.json"))
    p.add_argument("--tiers", type=Path, default=Path("manifests/kb-bundle-tiers.json"))
    p.add_argument("--layout", type=Path, default=Path("design/layout.json"))
    p.add_argument("--dmn-model", type=Path, default=None)
    p.add_argument("--layered", action="store_true", help="Use layered digest/gate channel means")
    p.add_argument("--cluster-root", type=Path, default=Path("lab/exp_e_clusters_v1"))
    p.add_argument("--query", default=None, help="User query for CEN planner")
    p.add_argument("--llm-enable", action="store_true", help="Enable CEN LLM probe stub")
    p.add_argument("--damage-patches", type=int, default=8)
    p.add_argument("--seed", type=int, default=42)
    p.add_argument("--dmn-steps", type=int, default=48)
    p.add_argument("--out", type=Path, default=Path("lab/sn_cen_out/infer_v1.json"))
    p.add_argument(
        "--session",
        action="store_true",
        help="Load/save FPN agent_session.json in store-dir",
    )
    args = p.parse_args()

    store = args.store_dir.resolve()
    field_path = (args.field_state or store / "field_state.json").resolve()
    layout = _read_json(args.layout)
    tiers = _read_json(args.tiers.resolve())

    wall_ms: float | None = None
    dmn_path: Path | None = None
    bundle_path: Path | None = None

    field_meta: dict = {}
    if args.from_field:
        if not field_path.is_file():
            raise SystemExit(f"field_state not found: {field_path}")
        bundle_name, bundle, decoded, recovery, wall_ms, state = _run_from_field(
            field_path, store, min_votes=CANONICAL_FIELD_MIN_VOTES
        )
        bundle_path = store / "bundles" / bundle_name
        store_ckpt = store / "checkpoints" / "model_hard.pt"
        dmn_path = store_ckpt if store_ckpt.is_file() else None
        field_meta = {
            "field_version": state.get("field_version"),
            "stale": field_state_stale(state, store),
            "union_bundles": (state.get("grid") or {}).get("source_bundles"),
        }
    else:
        if not args.bundle:
            raise SystemExit("--bundle required unless --from-field")
        bundle_path = args.bundle.resolve()
        bundle = _read_json(bundle_path)
        device = torch.device("cuda" if torch.cuda.is_available() else "cpu")

        store_ckpt = store / "checkpoints" / "model_hard.pt"
        if args.dmn_model:
            dmn_path = args.dmn_model.resolve()
        elif store_ckpt.is_file() and store.is_dir():
            dmn_path = store_ckpt
        elif args.agent_card.is_file():
            card = read_agent_card(args.agent_card.resolve())
            dmn_path = resolve_checkpoint(card, bundle_path.name, tiers).resolve()
        else:
            raise SystemExit("Provide --dmn-model or --agent-card")

        t0 = time.perf_counter()
        decoded, recovery = _run_dmn_repair(
            bundle,
            dmn_path,
            layout=layout,
            damage_patches=args.damage_patches,
            seed=args.seed,
            steps=args.dmn_steps,
            device=device,
        )
        wall_ms = (time.perf_counter() - t0) * 1000

    digest_vec: list[float] = []
    gate_vec: list[float] = []
    if args.layered and dmn_path and dmn_path.is_file() and not args.from_field:
        device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
        cluster = None
        name = bundle_path.name if bundle_path else ""
        for r in tiers["bundles"]:
            if r["bundle"] == name:
                cluster = r["cluster"]
                break
        base = args.cluster_root / cluster if cluster else args.cluster_root
        digest_vec, gate_vec = _layered_gate_digest(
            bundle,
            dmn_path,
            base / "digest_model.pt" if cluster else None,
            base / "gate_model.pt" if cluster else None,
            layout=layout,
            damage_patches=args.damage_patches,
            seed=args.seed,
            device=device,
        )

    wm = None
    if args.session:
        from casa.prisms.control.fpn_state import fpn_after_cen, load_session, salience_mode_bias, save_session

        wm = load_session(store)

    digest = digest_from_decoded(decoded, digest_vector=digest_vec)
    wm_bias = salience_mode_bias(wm, digest.concept_ids) if wm else None
    gated = sn_route(
        digest,
        bundle=bundle,
        gate_vector=gate_vec or None,
        wm_mode=wm.mode if wm else None,
        wm_salience_bias=wm_bias,
    )
    from casa.prisms.control.fpn_state import effective_user_query

    q = effective_user_query(wm, args.query) if wm else args.query
    task = cen_plan(gated, bundle=bundle, user_query=q, llm_enable=args.llm_enable)
    if wm is not None:
        wm = fpn_after_cen(wm, task, user_query=q)
        save_session(store, wm)

    control_stack = False
    if args.from_field:
        try:
            from casa.prisms.control.cylinders import has_control_stack

            control_stack = has_control_stack(state)
        except Exception:
            control_stack = False

    pipeline = (
        "sn_cen_control_stack"
        if args.from_field and control_stack
        else ("sn_cen_field_v2" if args.from_field else "sn_cen_v2")
    )
    report = {
        "schema_version": 2,
        "pipeline": pipeline,
        "bundle": str(bundle_path) if bundle_path else None,
        "field_state": str(field_path) if args.from_field else None,
        "field": field_meta if args.from_field else None,
        "control_stack": control_stack if args.from_field else None,
        "dmn_model": str(dmn_path) if dmn_path else None,
        "wall_ms": round(wall_ms or 0, 2),
        "recovery": recovery,
        "digest": {
            "concept_ids": digest.concept_ids,
            "edge_count": len(digest.edge_tokens),
            "mean_confidence": digest.mean_confidence,
            "digest_vector": digest.digest_vector,
        },
        "sn": {
            "mode": gated.gate.mode,
            "gate_vector": gated.gate.gate_vector,
            "ports": gated.gate.ports,
            "cen_open": gated.gate.cen_open,
            "salience_top": sorted(gated.salience.items(), key=lambda kv: kv[1], reverse=True)[:5],
        },
        "cen": task_to_dict(task, fpn=wm.to_dict() if wm else None),
    }
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps(report, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
