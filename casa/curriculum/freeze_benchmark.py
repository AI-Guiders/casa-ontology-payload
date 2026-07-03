#!/usr/bin/env python3
"""NUN-Bench freeze — turn a verified draft into an immutable, hash-pinned version.

A freeze is three artifacts, written only after ``verify_benchmark`` passes:

  <dir>/nunbench-<ver>-public.jsonl   — the public split, the file reviewers get;
  <heldout dir>/nunbench-<ver>-heldout.jsonl — canaries + held-out records; NEVER committed
                                        to the public repo, pinned by hash in the manifest;
  <dir>/manifest.json                 — counts, generator version, sha256 of both splits
                                        and of the source pool: the freeze IS this manifest.

Records keep their draft order (already hash-shuffled by the generator); files end with a
newline; hashes are over raw bytes — re-freezing the same draft is byte-identical, and any
later drift is a one-line diff of the manifest.
"""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any

from casa.curriculum.verify_benchmark import verify_benchmark


def _sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def freeze_benchmark(bench_path: str | Path, pool_path: str | Path, *, version: str,
                     public_dir: str | Path, heldout_dir: str | Path,
                     source_corpus: str = "OPUS EMEA (en-es), quality-filtered pool") -> dict[str, Any]:
    """Verify the draft and write the frozen artifacts; refuses on verification failure."""
    report = verify_benchmark(bench_path, pool_path)
    if report["verdict"] != "PASS":
        raise SystemExit("freeze refused — verification failed:\n"
                         + "\n".join(report["failures"][:20]))

    bench_path = Path(bench_path)
    rows = [json.loads(ln) for ln in bench_path.read_text(encoding="utf-8").splitlines() if ln.strip()]

    public_dir, heldout_dir = Path(public_dir), Path(heldout_dir)
    public_dir.mkdir(parents=True, exist_ok=True)
    heldout_dir.mkdir(parents=True, exist_ok=True)
    pub_path = public_dir / f"nunbench-{version}-public.jsonl"
    held_path = heldout_dir / f"nunbench-{version}-heldout.jsonl"
    for path, split in ((pub_path, "public"), (held_path, "heldout")):
        with path.open("w", encoding="utf-8", newline="\n") as f:
            for r in rows:
                if r["split"] == split:
                    f.write(json.dumps(r, ensure_ascii=False) + "\n")

    manifest = {
        "name": "NUN-Bench", "version": version,
        "generator": rows[0]["generator"],
        "language_pair": "en-es", "source_corpus": source_corpus,
        "counts": {k: report[k] for k in ("total", "errors", "controls", "canaries", "heldout")},
        "per_class": report["per_class"],
        "parseable_errors": report["parseable_errors"],
        "verification": {"verdict": report["verdict"], "remarks": len(report["remarks"])},
        "sha256": {
            pub_path.name: _sha256(pub_path),
            held_path.name: _sha256(held_path),  # file itself stays private
            "pool": _sha256(Path(pool_path)),
        },
    }
    (public_dir / "manifest.json").write_text(
        json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return manifest


def main(argv: list[str] | None = None) -> int:
    import argparse

    from casa.curriculum.render import ensure_utf8_console

    ensure_utf8_console()
    ap = argparse.ArgumentParser(description="Freeze a verified NUN-Bench draft.")
    ap.add_argument("--bench", default=".scratch/opus/nunbench-v0.1-draft.jsonl")
    ap.add_argument("--pool", default=".scratch/opus/emea-pairs-v1.jsonl")
    ap.add_argument("--version", default="v0.1")
    ap.add_argument("--public-dir", default="lab/nunbench/v0.1",
                    help="committed to the repo (public split + manifest)")
    ap.add_argument("--heldout-dir", default=".scratch/opus",
                    help="NOT committed — the private split lives outside the repo tree")
    ap.add_argument("--source-corpus", default="OPUS EMEA (en-es), quality-filtered pool")
    args = ap.parse_args(argv)

    manifest = freeze_benchmark(args.bench, args.pool, version=args.version,
                                public_dir=args.public_dir, heldout_dir=args.heldout_dir,
                                source_corpus=args.source_corpus)
    print(json.dumps(manifest, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
