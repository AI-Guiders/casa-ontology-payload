#!/usr/bin/env python3
"""
Import knowledge_delta v0: verify → merge bundle → online field write → optional checkpoint.

Learning = state written into field (+ optional hard finetune), not full LLM retrain.
"""

from __future__ import annotations

import argparse
import json
import shutil
from datetime import datetime, timezone
from pathlib import Path

from agent_card import read_agent_card, resolve_checkpoint  # type: ignore
from canonical import CANONICAL_CONCEPT_MODE, CANONICAL_MIN_VOTES, CANONICAL_THRESHOLD  # type: ignore
from codec_grid_v0 import decode_grid, score_recovery  # type: ignore
from field_write import (  # type: ignore
    apply_graph_patch,
    bundle_filename_from_ref,
    encode_dmn_grid,
    load_field_state,
    merge_bundles,
    resolve_bundle_path,
    save_field_state,
    write_bundle_to_field,
    _read_json,
    _write_json,
)


def _verify_requires(delta: dict, *, repo: Path, store_dir: Path, search_dirs: list[Path]) -> list[str]:
    missing: list[str] = []
    for req in delta.get("requires") or []:
        name = bundle_filename_from_ref(req)
        if resolve_bundle_path(name, repo=repo, store_dir=store_dir, search_dirs=search_dirs) is None:
            missing.append(name)
    return missing


def _check_epistemic(delta: dict, *, merged: dict, force: bool) -> list[str]:
    conflicts: list[str] = []
    ep = delta.get("epistemic") or {}
    blocked = set(ep.get("conflicts_with") or [])
    if not blocked:
        return conflicts

    added = set(delta.get("digest", {}).get("added_concept_ids") or [])
    for c in merged.get("claims") or []:
        cid = c.get("concept_id")
        if cid and cid in blocked and (not added or cid in added):
            conflicts.append(str(cid))
    if conflicts and not force:
        raise SystemExit(f"L0 conflict: {conflicts} (use --force to override)")
    return conflicts


def _load_incoming_bundle(delta: dict, *, repo: Path) -> tuple[str, dict]:
    bundle_spec = delta.get("bundle") or {}
    action = bundle_spec.get("action") or "replace"
    if bundle_spec.get("inline"):
        provides = delta.get("provides") or []
        if action in ("patch", "add") and provides:
            name = bundle_filename_from_ref(provides[0])
        else:
            name = provides[0] if provides else "inline.bundle.v1.json"
            name = bundle_filename_from_ref(name)
        return name, bundle_spec["inline"]

    path_ref = bundle_spec.get("path")
    if not path_ref:
        raise SystemExit("delta must have bundle.path or bundle.inline")
    path = (repo / path_ref).resolve()
    if not path.is_file():
        raise SystemExit(f"bundle not found: {path}")
    return path.name, _read_json(path)


def _quick_bench(bundle: dict, model_path: Path, *, layout: dict, device) -> dict:
    import torch
    from bench_dmn_nca_union import _grid_to_union_tensor, _threshold_grid_from_union_state  # type: ignore
    from layout_apply import _get_region_rect, damage_region_patches, mask_outside_region  # type: ignore
    from train_dmn_nca import UpdateRule, nca_rollout_eval, sobel_kernels  # type: ignore

    from codec_grid_v3 import encode_bundle_to_grid  # type: ignore

    rect = _get_region_rect(layout, "dmn_ontology")
    full = encode_bundle_to_grid(bundle, width=64, height=64, copies=7, concept_mode=CANONICAL_CONCEPT_MODE)
    target = mask_outside_region(full, rect)
    damaged = damage_region_patches(target, rect, patch_w=8, patch_h=8, count=8, seed=42)

    ckpt = __import__("torch").load(model_path, map_location="cpu", weights_only=False)
    token_ids = list(ckpt["token_ids"])
    ch = int(ckpt["channel_n"])
    rule = UpdateRule(channel_n=ch, hidden=int(ckpt["hidden"])).to(device)
    rule.load_state_dict(ckpt["state_dict"])
    rule.eval()

    k = len(token_ids)
    token_to_i = {t: i for i, t in enumerate(token_ids)}
    inp = _grid_to_union_tensor(damaged, token_to_i, device)
    x0 = torch.zeros(1, ch, 64, 64, device=device)
    x0[:, :k] = inp
    kx, ky = sobel_kernels(device)
    with torch.no_grad():
        xT = nca_rollout_eval(rule, x0, kx, ky, steps=48)
    grid_logits = _threshold_grid_from_union_state(xT, token_ids=token_ids, threshold=CANONICAL_THRESHOLD)
    decoded = decode_grid(grid_logits, min_votes=CANONICAL_MIN_VOTES)
    return score_recovery(bundle, decoded)


def main() -> None:
    p = argparse.ArgumentParser(description="Import knowledge_delta → field write")
    p.add_argument("--delta", type=Path, required=True)
    p.add_argument("--agent-card", type=Path, default=Path("examples/agent-cards/research-agent.v0.json"))
    p.add_argument("--store-dir", type=Path, default=Path("examples/agent-stores/research-agent-lab-v0"))
    p.add_argument("--layout", type=Path, default=Path("design/layout.v0.json"))
    p.add_argument("--tiers", type=Path, default=Path("manifests/kb-bundle-tiers.v0.json"))
    p.add_argument("--concept-mode", default=CANONICAL_CONCEPT_MODE)
    p.add_argument("--force", action="store_true", help="Ignore L0 epistemic conflicts")
    p.add_argument("--copy-checkpoint", action="store_true", help="Copy delta checkpoint_hard into store")
    p.add_argument("--bench", action="store_true", help="Quick recovery bench after import")
    p.add_argument("--no-finetune", action="store_true", help="Skip auto module finetune on hard tier")
    p.add_argument("--finetune-epochs", type=int, default=120)
    p.add_argument("--out", type=Path, default=None, help="Import report JSON")
    args = p.parse_args()

    repo = Path.cwd().resolve()
    delta = _read_json(args.delta.resolve())
    if delta.get("type") not in (None, "knowledge_delta", "bundle_full"):
        raise SystemExit(f"unsupported delta type: {delta.get('type')}")

    store = args.store_dir.resolve()
    bundles_dir = store / "bundles"
    bundles_dir.mkdir(parents=True, exist_ok=True)
    field_path = store / "field_state.json"
    log_path = store / "import_log.ndjson"

    card = read_agent_card(args.agent_card.resolve()) if args.agent_card.is_file() else {}
    agent_id = card.get("agent_id") or delta.get("source_agent_id") or "agent"
    cluster = delta.get("target_cluster") or card.get("cluster")

    bundle_dir = repo / (card.get("bundle_dir") or "examples/kb-perdoc")
    search_dirs = [bundle_dir, repo / "examples", repo]

    missing = _verify_requires(delta, repo=repo, store_dir=store, search_dirs=search_dirs)
    if missing:
        raise SystemExit(f"requires missing bundles: {missing}")

    bundle_name, incoming = _load_incoming_bundle(delta, repo=repo)
    bundle_spec = delta.get("bundle") or {}
    action = bundle_spec.get("action") or "replace"

    store_bundle_path = bundles_dir / bundle_name
    existing = _read_json(store_bundle_path) if store_bundle_path.is_file() else None
    merged = merge_bundles(existing, incoming, action=action, graph_patch=delta.get("graph_patch"))
    merged = apply_graph_patch(merged, delta.get("graph_patch"))
    _check_epistemic(delta, merged=merged, force=args.force)

    _write_json(store_bundle_path, merged)

    layout = _read_json(args.layout.resolve())
    grid = encode_dmn_grid(merged, layout=layout, concept_mode=args.concept_mode)

    state = load_field_state(field_path)
    if not state:
        state = {"schema_version": 1, "agent_id": agent_id, "cluster": cluster, "bundles": {}}
    state["agent_id"] = agent_id
    state["cluster"] = cluster
    write_bundle_to_field(state, bundle_name=bundle_name, bundle=merged, grid=grid, digest=delta.get("digest"))
    save_field_state(field_path, state)

    checkpoint_note = None
    if args.copy_checkpoint and delta.get("checkpoint_hard"):
        src = (repo / delta["checkpoint_hard"]).resolve()
        if src.is_file():
            ckpt_dir = store / "checkpoints"
            ckpt_dir.mkdir(parents=True, exist_ok=True)
            dst = ckpt_dir / "model_hard.pt"
            shutil.copy2(src, dst)
            checkpoint_note = str(dst.relative_to(repo))
        else:
            checkpoint_note = f"missing: {src}"

    bench_score = None
    finetune_report = None
    ckpt_dir = store / "checkpoints"
    ckpt_dir.mkdir(parents=True, exist_ok=True)
    store_ckpt = ckpt_dir / "model_hard.pt"

    digest = delta.get("digest") or {}
    tier = digest.get("tier", "easy")
    should_finetune = (
        not args.no_finetune
        and tier == "hard"
        and cluster
        and (digest.get("added_concept_ids") or digest.get("modules_activated") or action in ("patch", "add"))
    )

    if should_finetune:
        tiers = _read_json(args.tiers.resolve())
        init_path = store_ckpt if store_ckpt.is_file() else resolve_checkpoint(card, bundle_name, tiers).resolve()
        if init_path.is_file():
            from module_finetune_util import finetune_after_import  # type: ignore

            ft = finetune_after_import(
                repo=repo,
                cluster=str(cluster),
                bundle_name=bundle_name,
                store_bundle_path=store_bundle_path,
                init_ckpt=init_path,
                out_ckpt=store_ckpt,
                module_ids=list(digest.get("modules_activated") or []),
                epochs=args.finetune_epochs,
            )
            finetune_report = {
                "model": str(ft.model_path.relative_to(repo)),
                "token_count": ft.token_count,
                "epochs": ft.epochs,
                "best_mix": ft.best_mix,
                "modules": ft.modules,
            }

    if args.bench:
        import torch

        device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
        tiers = _read_json(args.tiers.resolve())
        if card:
            model_path = store_ckpt if store_ckpt.is_file() else resolve_checkpoint(card, bundle_name, tiers).resolve()
        else:
            model_path = store_ckpt
        if model_path.is_file():
            bench_score = _quick_bench(merged, model_path, layout=layout, device=device)

    report = {
        "schema_version": 1,
        "pipeline": "import_knowledge_delta_v1",
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "delta": str(args.delta.resolve()),
        "source_agent_id": delta.get("source_agent_id"),
        "target_cluster": cluster,
        "bundle": bundle_name,
        "action": action,
        "store_dir": str(store),
        "field_state": str(field_path),
        "concept_count": state["bundles"][bundle_name]["concept_count"],
        "digest": delta.get("digest"),
        "checkpoint_copied": checkpoint_note,
        "finetune": finetune_report,
        "bench": bench_score,
        "requires_ok": True,
    }

    out = args.out or (store / "reports" / f"import_{bundle_name.replace('.json', '')}.json")
    _write_json(out, report)

    log_path.parent.mkdir(parents=True, exist_ok=True)
    with log_path.open("a", encoding="utf-8") as f:
        f.write(json.dumps(report, ensure_ascii=False) + "\n")

    print(json.dumps(report, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
