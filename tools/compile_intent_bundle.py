#!/usr/bin/env python3
"""Merge agent pending_tract_claims → KB bundle ru.tract.* claims (ADR-0057)."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

_REPO = Path(__file__).resolve().parents[1]
_DEFAULT_BUNDLE = _REPO / "agents/von-neumann/bundles/kb-lang-ru-grammar-dialog-v1.bundle.json"


def _normalize_claim(raw: dict[str, Any]) -> dict[str, Any] | None:
    cid = str(raw.get("concept_id") or "")
    if not cid.startswith("ru.tract."):
        return None
    slots = dict(raw.get("slots") or {})
    if "cue_words" in slots and "cue_substrings" not in slots:
        words = [w.strip() for w in str(slots.pop("cue_words") or "").replace("|", ",").split(",") if w.strip()]
        if words:
            slots["cue_words"] = ",".join(words)
    claim: dict[str, Any] = {"concept_id": cid, "slots": slots}
    for key in ("text", "section", "doc_path"):
        if raw.get(key):
            claim[key] = raw[key]
    return claim


def compile_pending_claims(
    pending: list[dict[str, Any]],
    bundle_path: Path,
    *,
    clear_manifest_pending: Path | None = None,
) -> dict[str, Any]:
    if bundle_path.is_file():
        bundle = json.loads(bundle_path.read_text(encoding="utf-8"))
    else:
        bundle = {
            "schema_version": 1,
            "bundle_id": "kb-lang-ru-grammar-dialog-v1",
            "title": "RU dialogue + grammar norms v1",
            "claims": [],
        }
    by_id = {str(c.get("concept_id") or ""): c for c in bundle.get("claims") or [] if c.get("concept_id")}
    merged = 0
    for raw in pending:
        claim = _normalize_claim(raw)
        if not claim:
            continue
        by_id[str(claim["concept_id"])] = claim
        merged += 1
    bundle["claims"] = list(by_id.values())
    bundle_path.parent.mkdir(parents=True, exist_ok=True)
    bundle_path.write_text(json.dumps(bundle, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    if clear_manifest_pending is not None and clear_manifest_pending.is_file():
        manifest = json.loads(clear_manifest_pending.read_text(encoding="utf-8"))
        manifest["pending_tract_claims"] = []
        clear_manifest_pending.write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    return {
        "out": str(bundle_path),
        "merged": merged,
        "claims_total": len(bundle["claims"]),
        "cleared_manifest": str(clear_manifest_pending) if clear_manifest_pending else None,
    }


def load_pending_from_manifest(manifest_path: Path) -> list[dict[str, Any]]:
    if not manifest_path.is_file():
        return []
    data = json.loads(manifest_path.read_text(encoding="utf-8"))
    return list(data.get("pending_tract_claims") or [])


def main() -> None:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--manifest", type=Path, default=None, help="Agent manifest with pending_tract_claims")
    p.add_argument("--pending-json", type=Path, default=None, help="Optional JSON file [{concept_id, slots}, ...]")
    p.add_argument("--out", type=Path, default=_DEFAULT_BUNDLE)
    p.add_argument("--clear-pending", action="store_true", help="Clear pending_tract_claims in manifest after merge")
    args = p.parse_args()

    pending: list[dict[str, Any]] = []
    manifest_path = args.manifest
    if args.pending_json and args.pending_json.is_file():
        pending = json.loads(args.pending_json.read_text(encoding="utf-8"))
    elif manifest_path is not None:
        pending = load_pending_from_manifest(manifest_path)
    else:
        raise SystemExit("Provide --manifest or --pending-json")

    clear = manifest_path if args.clear_pending and manifest_path else None
    summary = compile_pending_claims(pending, args.out, clear_manifest_pending=clear)
    print(json.dumps(summary, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
