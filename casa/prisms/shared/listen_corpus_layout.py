#!/usr/bin/env python3
"""Listen mass media layout — outside repo by default (no git bloat)."""

from __future__ import annotations

import os
from pathlib import Path

from casa._paths import REPO_ROOT

DEFAULT_EXTERNAL_DIRNAME = "casa-listen-corpus"
LISTEN_CORPUS_DOC_DIR = "listen_corpus"


def listen_corpus_root(*, root: Path | None = None) -> Path:
    """Root for wav/mp4/frames/manifests (gitignored or separate repo/LFS).

    Priority:
    1. ``CASA_LISTEN_CORPUS`` env (absolute path recommended)
    2. ``<repo-parent>/casa-listen-corpus`` — sibling of casa-ontology-payload
    """
    env = (os.environ.get("CASA_LISTEN_CORPUS") or "").strip()
    if env:
        return Path(env).expanduser().resolve()
    base = root if root is not None else REPO_ROOT
    return (base.parent / DEFAULT_EXTERNAL_DIRNAME).resolve()


def source_bundle_dir(
    corpus_root: Path,
    *,
    publisher: str,
    collection: str,
    video_id: str,
) -> Path:
    pub = _slug(publisher)
    coll = _slug(collection)
    vid = _slug(video_id)
    return corpus_root / pub / coll / vid


def _slug(text: str) -> str:
    out: list[str] = []
    for ch in str(text or "").strip().lower():
        if ch.isalnum():
            out.append(ch)
        elif ch in "._-":
            out.append(ch)
        else:
            out.append("_")
    slug = "".join(out).strip("_")
    while "__" in slug:
        slug = slug.replace("__", "_")
    return slug or "unknown"
