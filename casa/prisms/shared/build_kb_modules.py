#!/usr/bin/env python3
"""Build manifests/kb-modules.v0.json from kb-clusters + kb-perdoc bundles."""

from __future__ import annotations

from casa._paths import ensure_import_paths

ensure_import_paths()

import argparse
import json
from pathlib import Path

from casa.prisms.shared.module_masks import ModuleSpec, enumerate_sections, section_slug


def _read_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def main() -> None:
    p = argparse.ArgumentParser(description="Generate kb-modules manifest")
    p.add_argument("--clusters", type=Path, default=Path("manifests/kb-clusters.v0.json"))
    p.add_argument("--repo-root", type=Path, default=Path("."))
    p.add_argument("--out", type=Path, default=Path("manifests/kb-modules.v0.json"))
    args = p.parse_args()

    repo = args.repo_root.resolve()
    clusters = _read_json((repo / args.clusters).resolve())
    bundle_dir = repo / clusters["bundle_dir"]

    modules: list[dict] = []
    by_cluster: dict[str, int] = {}

    for cl in clusters["clusters"]:
        cid = cl["id"]
        for bname in cl["bundles"]:
            path = bundle_dir / bname
            if not path.is_file():
                continue
            bundle = _read_json(path)
            stem = path.stem.replace(".bundle.v1", "")
            for doc_path, section in enumerate_sections(bundle):
                sk = f"{doc_path}|{section}"
                slug = section_slug(section)
                mid = f"{cid}/{stem}/{slug}"
                spec = ModuleSpec(
                    cluster=cid,
                    bundle_name=bname,
                    module_id=mid,
                    doc_path=doc_path,
                    section=section,
                    section_key=sk,
                )
                modules.append(
                    {
                        "id": spec.module_id,
                        "cluster": spec.cluster,
                        "bundle": spec.bundle_name,
                        "doc_path": spec.doc_path,
                        "section": spec.section,
                        "section_key": spec.section_key,
                    }
                )
                by_cluster[cid] = by_cluster.get(cid, 0) + 1

    out_obj = {
        "schema_version": 1,
        "module_id_scheme": "{cluster}/{bundle_stem}/{section_slug}",
        "section_key_scheme": "{doc_path}|{section}",
        "clusters_manifest": str(args.clusters).replace("\\", "/"),
        "bundle_dir": clusters["bundle_dir"],
        "concept_mode": "section",
        "codec": "v3",
        "module_count": len(modules),
        "modules_by_cluster": by_cluster,
        "modules": modules,
    }
    out_path = (repo / args.out).resolve()
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(out_obj, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps({"written": str(out_path), "module_count": len(modules), "by_cluster": by_cluster}, indent=2))


if __name__ == "__main__":
    main()
