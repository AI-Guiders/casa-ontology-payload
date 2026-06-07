#!/usr/bin/env python3
"""Bootstrap Self tier only: journal + agent/ prism on an existing store (lab / cold shell).

Not a life restore — use restore_agent_life for snapshot from life-archive.
Declarative steps: design/agent-bootstrap-manifest.v1.json
"""

from __future__ import annotations

from casa._paths import ensure_import_paths

ensure_import_paths()

import argparse
import json
import sys
from pathlib import Path

_REPO = Path(__file__).resolve().parents[2]
if str(_REPO) not in sys.path:
    sys.path.insert(0, str(_REPO))

from casa.prisms.memory.agent_journal import journal_stats
from casa.prisms.memory.bootstrap_agent_manifest import (
    bootstrap_agent_from_manifest,
    default_manifest_path,
    load_agent_bootstrap_manifest,
)
from casa.prisms.shared.store_boot import boot_store
from casa.prisms.shared.store_layout import default_agent_store
from casa.prisms.shared.store_persist import save_runtime_state


def bootstrap_agent_self_tier(
    store_dir: Path,
    *,
    display_name: str = "Нейманн",
    manifest_path: Path | None = None,
    skip_if_journal_exists: bool = True,
) -> dict:
    store_dir = store_dir.resolve()
    journal_dir = store_dir / "journal"
    if skip_if_journal_exists and journal_dir.is_dir() and any(journal_dir.rglob("entries.jsonl")):
        return {
            "store_dir": str(store_dir),
            "skipped": True,
            "reason": "journal_already_present",
            "journal": journal_stats(store_dir),
            "manifest": str(manifest_path or default_manifest_path()),
        }

    manifest = load_agent_bootstrap_manifest(manifest_path)
    boot = boot_store(store_dir, prefer_field_state=True)
    state = boot["state"]
    state.setdefault("store", {})["store_id"] = store_dir.name

    applied = bootstrap_agent_from_manifest(
        store_dir,
        state,
        manifest,
        display_name=display_name,
    )
    persist = save_runtime_state(store_dir, state, force=True, thin=True, save_agent=True)

    return {
        "store_dir": str(store_dir),
        "skipped": False,
        "manifest": str(manifest_path or default_manifest_path()),
        "journal": journal_stats(store_dir),
        "bootstrapped_notebooks": applied.get("journal_bootstrapped"),
        "agent_prisms": applied.get("agent_prisms"),
        "agent_prism": str(store_dir / "agent"),
        "persist": persist,
    }


def main() -> None:
    p = argparse.ArgumentParser(
        description="Bootstrap Self tier (journal + agent/) on existing store — not life restore"
    )
    p.add_argument("--store-dir", type=Path, default=None)
    p.add_argument("--display-name", default="Нейманн")
    p.add_argument("--manifest", type=Path, default=None, help="Override agent-bootstrap-manifest.v1.json")
    p.add_argument(
        "--force",
        action="store_true",
        help="Run even if journal/ already exists",
    )
    args = p.parse_args()

    rep = bootstrap_agent_self_tier(
        args.store_dir or default_agent_store(),
        display_name=args.display_name,
        manifest_path=args.manifest,
        skip_if_journal_exists=not args.force,
    )
    print(json.dumps(rep, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
