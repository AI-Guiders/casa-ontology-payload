#!/usr/bin/env python3
"""Create an untrained agent store shell — no life snapshot, curriculum starts from lessons."""

from __future__ import annotations

from casa._paths import ensure_import_paths

ensure_import_paths()

import argparse
import json
from pathlib import Path

from casa.cli.bootstrap_agent_self_tier import bootstrap_agent_self_tier
from casa.prisms.memory.bootstrap_agent_manifest import default_manifest_path
from casa.prisms.memory.bootstrap_host_canon import bootstrap_host_canon_lattices
from casa.prisms.shared.store_boot import boot_store
from casa.prisms.shared.store_layout import default_agent_store

_DEFAULT_PROFILE = {
    "schema_version": 1,
    "subject_mode": True,
    "display_name": "von-neumann",
    "locale": "ru",
}


def bootstrap_agent_cold_store(
    store_dir: Path,
    *,
    store_id: str | None = None,
    display_name: str = "Нейманн",
    locale: str = "ru",
    seed_self: bool = True,
    force: bool = False,
) -> dict:
    """Empty living-agent directory + profile; optional Self tier bootstrap."""
    store_dir = store_dir.resolve()
    if store_dir.exists() and any(store_dir.iterdir()) and not force:
        raise FileExistsError(f"{store_dir} is not empty — pass --force or pick another path")

    store_dir.mkdir(parents=True, exist_ok=True)
    sid = store_id or store_dir.name
    profile = {
        **_DEFAULT_PROFILE,
        "display_name": sid,
        "locale": locale,
    }
    (store_dir / "store_profile.json").write_text(
        json.dumps(profile, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )

    self_rep: dict | None = None
    canon_rep: dict | None = None
    if seed_self:
        self_rep = bootstrap_agent_self_tier(
            store_dir,
            display_name=display_name,
            skip_if_journal_exists=False,
        )
        boot = boot_store(store_dir, prefer_field_state=True)
        canon_rep = bootstrap_host_canon_lattices(
            store_dir,
            boot["state"],
            locale=locale,
            persist=True,
        )

    return {
        "store_dir": str(store_dir),
        "store_id": sid,
        "trained": False,
        "store_profile": str(store_dir / "store_profile.json"),
        "bootstrap_manifest": str(default_manifest_path()),
        "self_tier": self_rep,
        "host_canon": canon_rep,
        "next": "Run lessons/ingest or restore_agent_life for a trained snapshot",
    }


def main() -> None:
    p = argparse.ArgumentParser(
        description="Untrained agent store shell (no ltm/field from life-archive)"
    )
    p.add_argument("--store-dir", type=Path, default=None)
    p.add_argument("--store-id", default=None, help="Ops id (default: directory name)")
    p.add_argument("--display-name", default="Нейманн")
    p.add_argument("--locale", default="ru")
    p.add_argument("--no-seed-self", action="store_true")
    p.add_argument("--force", action="store_true")
    args = p.parse_args()

    rep = bootstrap_agent_cold_store(
        args.store_dir or default_agent_store(),
        store_id=args.store_id,
        display_name=args.display_name,
        locale=args.locale,
        seed_self=not args.no_seed_self,
        force=args.force,
    )
    print(json.dumps(rep, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
