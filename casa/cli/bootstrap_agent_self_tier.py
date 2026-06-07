#!/usr/bin/env python3
"""Bootstrap Self tier only: journal + agent/ prism on an existing store (lab / cold shell).

Not a life restore — use restore_agent_life for snapshot from life-archive.
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

from casa.prisms.memory.agent_journal import append_journal_entry, journal_stats
from casa.prisms.memory.agent_memory_ops import agent_remember
from casa.prisms.memory.agent_prism import create_agent_lattice, load_agent_prism, save_agent_prism
from casa.prisms.memory.memory_prisms import ensure_prisms
from casa.prisms.shared.store_boot import boot_store
from casa.prisms.shared.store_layout import default_agent_store
from casa.prisms.shared.store_persist import save_runtime_state


def bootstrap_agent_self_tier(
    store_dir: Path,
    *,
    display_name: str = "Нейманн",
    notebooks: list[str] | None = None,
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
        }

    notebooks = notebooks or ["math-palochki", "kolb", "self"]

    boot = boot_store(store_dir, prefer_field_state=True)
    state = boot["state"]
    state.setdefault("store", {})["store_id"] = store_dir.name

    load_agent_prism(store_dir, state)
    create_agent_lattice(state, "agent-self-default", width=32, height=32, concept_prefix="agent.self.")
    save_agent_prism(store_dir, state)

    journal_rows: list[str] = []
    append_journal_entry(
        store_dir,
        {
            "kind": "note",
            "text": (
                f"Я — {display_name}. Это мой журнал (Self tier). "
                "Сюда — черновики, гипотезы, рабочая тетрадь. "
                "Уроки учителя лежат в lessons/; после занятий факты уходят в ltm/ через sleep."
            ),
            "tags": ["notebook:self", "bootstrap"],
            "meta": {"notebook": "self", "status": "open"},
        },
        domain="self",
    )
    journal_rows.append("self/bootstrap")

    for nb in notebooks:
        if nb == "self":
            continue
        append_journal_entry(
            store_dir,
            {
                "kind": "note",
                "text": f"Тетрадь «{nb}»: сюда записываю свои попытки, ошибки и выводы по классу.",
                "tags": ["draft", f"notebook:{nb}"],
                "meta": {"notebook": nb, "status": "open", "class_id": nb},
            },
            domain=nb.replace("_", "-"),
        )
        journal_rows.append(f"{nb}/bootstrap")

    agent_remember(
        store_dir,
        state,
        {
            "kind": "observation",
            "text": "agent-self-default lattice ready",
            "notebook": "self",
            "concepts": ["agent.self.bootstrap"],
        },
        scope="self",
        persist=False,
    )
    save_agent_prism(store_dir, state)

    persist = save_runtime_state(store_dir, state, force=True, thin=True, save_agent=True)

    return {
        "store_dir": str(store_dir),
        "skipped": False,
        "journal": journal_stats(store_dir),
        "bootstrapped_notebooks": journal_rows,
        "agent_prism": str(store_dir / "agent"),
        "persist": persist,
    }


def main() -> None:
    p = argparse.ArgumentParser(
        description="Bootstrap Self tier (journal + agent/) on existing store — not life restore"
    )
    p.add_argument("--store-dir", type=Path, default=None)
    p.add_argument("--display-name", default="Нейманн")
    p.add_argument("--notebook", action="append", default=[], help="Extra notebook id (repeatable)")
    p.add_argument(
        "--force",
        action="store_true",
        help="Run even if journal/ already exists",
    )
    args = p.parse_args()

    notebooks = ["math-palochki", "kolb", "self", *(args.notebook or [])]
    rep = bootstrap_agent_self_tier(
        args.store_dir or default_agent_store(),
        display_name=args.display_name,
        notebooks=notebooks,
        skip_if_journal_exists=not args.force,
    )
    print(json.dumps(rep, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
