#!/usr/bin/env python3
"""
Import knowledge_delta v0/v2: verify → merge bundle → union field write → optional finetune.

Finetune is opt-in (--finetune) or auto when --bench concepts F1 below --finetune-if-below.
"""

from __future__ import annotations

from casa._paths import ensure_import_paths

ensure_import_paths()

import argparse
import json
import shutil
from datetime import datetime, timezone
from pathlib import Path

from casa.prisms.shared.agent_card import read_agent_card, resolve_checkpoint
from casa.prisms.shared.canonical import CANONICAL_CONCEPT_MODE, CANONICAL_MIN_VOTES, CANONICAL_THRESHOLD
from casa.prisms.shared.codec_grid import decode_grid, score_recovery
from casa.prisms.shared.field_write import (
    apply_digest_only_update,
    apply_graph_patch,
    bundle_filename_from_ref,
    load_field_state,
    merge_bundles,
    rebuild_union_field,
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


def _resolve_bundle_name(delta: dict) -> str:
    provides = delta.get("provides") or []
    if provides:
        return bundle_filename_from_ref(provides[0])
    bundle_spec = delta.get("bundle") or {}
    if bundle_spec.get("path"):
        return bundle_filename_from_ref(bundle_spec["path"])
    raise SystemExit("digest_only delta requires provides[] or bundle.path")


def _quick_bench(bundle: dict, model_path: Path, *, layout: dict, device) -> dict:
    import torch
    from casa.cli.bench.bench_dmn_nca_union import _grid_to_union_tensor, _threshold_grid_from_union_state
    from casa.prisms.shared.layout_apply import _get_region_rect, damage_region_patches, mask_outside_region
    from casa.cli.train_dmn_nca import UpdateRule, nca_rollout_eval, sobel_kernels

    from casa.prisms.shared.codec_grid_v3 import encode_bundle_to_grid

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

    token_count = len(token_ids)
    token_to_i = {t: i for i, t in enumerate(token_ids)}
    inp = _grid_to_union_tensor(damaged, token_to_i, device)
    x0 = torch.zeros(1, ch, 64, 64, device=device)
    x0[:, :token_count] = inp
    kx, ky = sobel_kernels(device)
    with torch.no_grad():
        xT = nca_rollout_eval(rule, x0, kx, ky, steps=48)
    grid_logits = _threshold_grid_from_union_state(xT, token_ids=token_ids, threshold=CANONICAL_THRESHOLD)
    decoded = decode_grid(grid_logits, min_votes=CANONICAL_MIN_VOTES)
    return score_recovery(bundle, decoded)


def _concepts_f1(bench: dict | None) -> float | None:
    if not bench:
        return None
    return float(((bench.get("concepts") or {}).get("f1")) or 0.0)


def _run_finetune(
    *,
    repo: Path,
    store: Path,
    store_bundle_path: Path,
    store_ckpt: Path,
    card: dict,
    bundle_name: str,
    tiers_path: Path,
    cluster: str,
    digest: dict,
    action: str,
    epochs: int,
) -> dict | None:
    tier = digest.get("tier", "easy")
    if tier != "hard" or not cluster:
        return None
    if not (digest.get("added_concept_ids") or digest.get("modules_activated") or action in ("patch", "add")):
        return None

    tiers = _read_json(tiers_path)
    init_path = store_ckpt if store_ckpt.is_file() else resolve_checkpoint(card, bundle_name, tiers).resolve()
    if not init_path.is_file():
        return None

    from casa.prisms.shared.module_finetune_util import finetune_after_import

    ft = finetune_after_import(
        repo=repo,
        cluster=str(cluster),
        bundle_name=bundle_name,
        store_bundle_path=store_bundle_path,
        init_ckpt=init_path,
        out_ckpt=store_ckpt,
        module_ids=list(digest.get("modules_activated") or []),
        epochs=epochs,
    )
    return {
        "model": str(ft.model_path.relative_to(repo)),
        "token_count": ft.token_count,
        "epochs": ft.epochs,
        "best_mix": ft.best_mix,
        "modules": ft.modules,
    }


def main() -> None:
    p = argparse.ArgumentParser(description="Import knowledge_delta → union field write")
    p.add_argument("--delta", type=Path, required=True)
    p.add_argument("--agent-card", type=Path, default=Path("lab/agent-cards/research-agent.json"))
    p.add_argument("--store-dir", type=Path, default=Path("lab/agent-stores/research-agent-lab"))
    p.add_argument("--layout", type=Path, default=Path("design/layout.json"))
    p.add_argument("--tiers", type=Path, default=Path("manifests/kb-bundle-tiers.json"))
    p.add_argument("--concept-mode", default=CANONICAL_CONCEPT_MODE)
    p.add_argument("--force", action="store_true", help="Ignore L0 epistemic conflicts")
    p.add_argument("--copy-checkpoint", action="store_true", help="Copy delta checkpoint_hard into store")
    p.add_argument("--bench", action="store_true", help="Quick recovery bench after import")
    p.add_argument("--finetune", action="store_true", help="Run module finetune on hard tier (opt-in)")
    p.add_argument("--finetune-if-below", type=float, default=0.35, help="Auto finetune when bench concepts F1 below")
    p.add_argument("--finetune-epochs", type=int, default=120)
    p.add_argument("--out", type=Path, default=None, help="Import report JSON")
    args = p.parse_args()

    repo = Path.cwd().resolve()
    delta = _read_json(args.delta.resolve())
    delta_type = delta.get("type") or "knowledge_delta"
    if delta_type not in ("knowledge_delta", "bundle_full", "digest_only"):
        raise SystemExit(f"unsupported delta type: {delta_type}")

    store = args.store_dir.resolve()
    bundles_dir = store / "bundles"
    bundles_dir.mkdir(parents=True, exist_ok=True)
    field_path = store / "field_state.json"
    log_path = store / "import_log.ndjson"

    card = read_agent_card(args.agent_card.resolve()) if args.agent_card.is_file() else {}
    agent_id = card.get("agent_id") or delta.get("source_agent_id") or "agent"
    cluster = delta.get("target_cluster") or card.get("cluster")
    layout = _read_json(args.layout.resolve())

    state = load_field_state(field_path)
    if not state:
        state = {"schema_version": 2, "agent_id": agent_id, "cluster": cluster, "bundles": {}, "field_version": 0}
    state["agent_id"] = agent_id
    state["cluster"] = cluster

    if delta_type == "digest_only":
        bundle_name = _resolve_bundle_name(delta)
        digest = delta.get("digest") or {}
        apply_digest_only_update(state, bundle_name=bundle_name, digest=digest, store_dir=store)
        save_field_state(field_path, state)
        report = {
            "schema_version": 2,
            "pipeline": "import_knowledge_delta_v2_digest_only",
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "delta": str(args.delta.resolve()),
            "bundle": bundle_name,
            "field_version": state.get("field_version"),
            "store_dir": str(store),
            "field_state": str(field_path),
        }
        out = args.out or (store / "reports" / f"digest_{bundle_name.replace('.json', '')}.json")
        _write_json(out, report)
        with log_path.open("a", encoding="utf-8") as f:
            f.write(json.dumps(report, ensure_ascii=False) + "\n")
        print(json.dumps(report, ensure_ascii=False, indent=2))
        return

    bundle_dir = repo / (card.get("bundle_dir") or "lab/kb-perdoc")
    search_dirs = [bundle_dir, repo / "lab", repo]

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

    state.setdefault("bundles", {})[bundle_name] = state.get("bundles", {}).get(bundle_name) or {}
    write_bundle_to_field(
        state,
        bundle_name=bundle_name,
        bundle=merged,
        digest=delta.get("digest"),
        store_dir=store,
        layout=layout,
        concept_mode=args.concept_mode,
    )
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

    f1 = _concepts_f1(bench_score)
    should_finetune = args.finetune or (f1 is not None and f1 < args.finetune_if_below)
    if should_finetune and cluster:
        finetune_report = _run_finetune(
            repo=repo,
            store=store,
            store_bundle_path=store_bundle_path,
            store_ckpt=store_ckpt,
            card=card,
            bundle_name=bundle_name,
            tiers_path=args.tiers.resolve(),
            cluster=str(cluster),
            digest=digest,
            action=action,
            epochs=args.finetune_epochs,
        )

    report = {
        "schema_version": 2,
        "pipeline": "import_knowledge_delta_v2",
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "delta": str(args.delta.resolve()),
        "source_agent_id": delta.get("source_agent_id"),
        "target_cluster": cluster,
        "bundle": bundle_name,
        "action": action,
        "store_dir": str(store),
        "field_state": str(field_path),
        "field_version": state.get("field_version"),
        "union_bundles": (state.get("grid") or {}).get("source_bundles"),
        "concept_count": state["bundles"][bundle_name]["concept_count"],
        "digest": delta.get("digest"),
        "checkpoint_copied": checkpoint_note,
        "finetune": finetune_report,
        "bench": bench_score,
        "requires_ok": True,
    }

    out = args.out or (store / "reports" / "import_{}".format(bundle_name.replace(".json", "")))
    _write_json(out, report)

    log_path.parent.mkdir(parents=True, exist_ok=True)
    with log_path.open("a", encoding="utf-8") as f:
        f.write(json.dumps(report, ensure_ascii=False) + "\n")

    print(json.dumps(report, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
