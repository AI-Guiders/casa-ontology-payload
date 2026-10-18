#!/usr/bin/env python3
"""Extract BANC reference subgraphs for Control Zone grounding (note-casa-control-zone-banc-grounding).

Fly = structural prior; CASA = own field data on top. Evolution builds — does not delete.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

DEFAULT_CONNECTOME_ROOT = Path(r"D:\Experiments\casa-data\connectomes\banc-v888")


def _require_pandas():
    try:
        import pandas as pd
    except ImportError as exc:
        raise SystemExit("pandas required: pip install pandas pyarrow") from exc
    return pd


def _as_id(series):
    """BANC meta + edgelist both use uint64 root ids; keep as str for joins."""
    return series.astype(str)


def load_banc_tables(root: Path):
    pd = _require_pandas()
    meta_path = root / "banc_888_meta.feather"
    edge_path = root / "banc_888_edgelist_simple_v2.feather"
    if not meta_path.exists() or not edge_path.exists():
        raise FileNotFoundError(f"BANC tier-1 missing under {root}")
    meta = pd.read_feather(meta_path)
    edges = pd.read_feather(edge_path)
    node_col = _node_col(meta)
    meta[node_col] = _as_id(meta[node_col])
    edges["pre"] = _as_id(edges["pre"])
    edges["post"] = _as_id(edges["post"])
    return meta, edges


def _node_col(meta) -> str:
    for col in ("banc_888_id", "root_id", "root_888"):
        if col in meta.columns:
            return col
    raise KeyError("no neuron id column in meta")


def subgraph_cz_s1(meta, edges, *, node_col: str, max_nodes: int = 5000):
    """Visual afferent → intrinsic → descending → motor efferent."""
    sc = meta["super_class"].astype(str)
    visual = sc.str.contains("visual|optic", case=False, na=False) | meta.get("flow", sc).astype(str).eq("afferent")
    motor = sc.eq("motor")
    descending = sc.eq("descending")
    intrinsic = sc.str.contains("intrinsic", case=False, na=False)
    node_set = set(meta.loc[visual | motor | descending | intrinsic, node_col].tolist())
    sub = edges[edges["pre"].isin(node_set) & edges["post"].isin(node_set)]
    if len(sub) > max_nodes * 4:
        weight = "count" if "count" in sub.columns else sub.columns[-1]
        top_pre = sub.groupby("pre")[weight].sum().nlargest(max_nodes // 2).index
        top_post = sub.groupby("post")[weight].sum().nlargest(max_nodes // 2).index
        keep = set(top_pre).union(set(top_post))
        sub = sub[sub["pre"].isin(keep) & sub["post"].isin(keep)]
    return sub, meta[meta[node_col].isin(set(sub["pre"]).union(sub["post"]))]


def subgraph_cz_s3_neck(meta, edges, *, node_col: str):
    """Neck / bridging neurons — bottleneck prior for lattice_dan."""
    if "region" in meta.columns:
        neck = meta["region"].astype(str).str.contains("neck|cervical", case=False, na=False)
    else:
        neck = meta["super_class"].isin(["ascending", "descending"])
    nodes = set(meta.loc[neck, node_col].tolist())
    sub = edges[edges["pre"].isin(nodes) | edges["post"].isin(nodes)]
    return sub, meta[meta[node_col].isin(set(sub["pre"]).union(sub["post"]))]


def subgraph_cz_s5_betweenness(root: Path, meta, edges, *, node_col: str, top_k: int = 20):
    """Top-K afferent→efferent betweenness chokepoints on current edge set."""
    pd = _require_pandas()
    bt_path = root / "banc_888_betweenness_afferent_to_efferent_v2.csv"
    if not bt_path.exists():
        raise FileNotFoundError(bt_path)
    bt = pd.read_csv(bt_path)
    id_col = "banc_888_id" if "banc_888_id" in bt.columns else bt.columns[0]
    score_col = "betweenness" if "betweenness" in bt.columns else bt.columns[-1]
    top_ids = set(_as_id(bt.nlargest(top_k, score_col)[id_col]).tolist())
    sub = edges[edges["pre"].isin(top_ids) | edges["post"].isin(top_ids)]
    return sub, meta[meta[node_col].isin(set(sub["pre"]).union(sub["post"]))]


EXTRACTORS = {
    "CZ-S1": subgraph_cz_s1,
    "CZ-S3": subgraph_cz_s3_neck,
    "CZ-S5": subgraph_cz_s5_betweenness,
}


def export_subgraph(name: str, edges, meta, out: Path) -> dict[str, Any]:
    payload = {
        "id": name,
        "n_edges": int(len(edges)),
        "n_nodes": int(len(set(edges["pre"]).union(edges["post"]))),
        "edges": edges[["pre", "post", "count"]].head(5000).to_dict(orient="records"),
    }
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(payload, indent=2), encoding="utf-8")
    return payload


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="BANC Control Zone subgraph extractor")
    parser.add_argument("--root", type=Path, default=DEFAULT_CONNECTOME_ROOT)
    parser.add_argument("--subgraph", choices=sorted(EXTRACTORS), default="CZ-S1")
    parser.add_argument("--out", type=Path, default=None)
    parser.add_argument("--max-nodes", type=int, default=5000)
    args = parser.parse_args(argv)

    meta, edges = load_banc_tables(args.root)
    node_col = _node_col(meta)
    fn = EXTRACTORS[args.subgraph]
    if args.subgraph == "CZ-S1":
        sub_e, sub_m = fn(meta, edges, node_col=node_col, max_nodes=args.max_nodes)
    elif args.subgraph == "CZ-S5":
        sub_e, sub_m = fn(args.root, meta, edges, node_col=node_col)
    else:
        sub_e, sub_m = fn(meta, edges, node_col=node_col)

    out = args.out or Path(__file__).resolve().parent / "fixtures" / f"banc_{args.subgraph.lower()}.json"
    summary = export_subgraph(args.subgraph, sub_e, sub_m, out)
    print(json.dumps({k: summary[k] for k in ("id", "n_edges", "n_nodes", "edges") if k in summary or k == "edges"}, indent=2))
    print(f"wrote {out}", file=sys.stderr)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
