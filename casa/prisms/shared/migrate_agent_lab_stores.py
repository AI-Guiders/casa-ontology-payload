#!/usr/bin/env python3
"""One-shot: math-l0-lab init, agent journal → language-agent-lab, clean sss-ru-general runtime."""

from __future__ import annotations

from casa._paths import REPO_ROOT, ensure_import_paths

ensure_import_paths()

import argparse
import json
import shutil
from pathlib import Path
from typing import Any

from casa.prisms.memory.init_math_l0_lab import init_math_l0_lab
from casa.prisms.shared.field_write import save_field_state
from casa.prisms.shared.store_boot import boot_store
from casa.prisms.shared.store_layout import (
    STORE_LANGUAGE_AGENT_LAB,
    STORE_MATH_L0_LAB,
    STORE_RU_GENERAL_V0,
    agent_store_dir,
    journal_root,
)


def _copy_journal(src: Path, dst: Path) -> dict[str, Any]:
    if not journal_root(src).is_dir():
        return {"copied": False, "reason": "no journal on source"}
    dst_journal = journal_root(dst)
    if dst_journal.exists():
        backup = dst.parent / f"{dst.name}.journal.bak"
        if backup.exists():
            shutil.rmtree(backup)
        shutil.copytree(dst_journal, backup)
    if dst_journal.exists():
        shutil.rmtree(dst_journal)
    shutil.copytree(journal_root(src), dst_journal)
    return {"copied": True, "from": str(journal_root(src)), "to": str(dst_journal)}


def _clean_lexicon_runtime(store_dir: Path) -> dict[str, Any]:
    rep = boot_store(store_dir, prefer_field_state=False)
    save_field_state(store_dir / "field_state.json", rep["state"], compact=True)
    removed: list[str] = []
    for name in ("agent_session.json",):
        p = store_dir / name
        if p.is_file():
            p.unlink()
            removed.append(name)
    jroot = journal_root(store_dir)
    if jroot.is_dir():
        shutil.rmtree(jroot)
        removed.append("journal/")
    return {
        "field_rebuilt_from": "ltm",
        "shard_count": rep.get("shard_count"),
        "removed": removed,
    }


def migrate_agent_lab_stores(
    *,
    bundle: Path,
    skip_math_init: bool = False,
    skip_journal_move: bool = False,
    skip_ru_clean: bool = False,
) -> dict[str, Any]:
    math_dir = agent_store_dir(STORE_MATH_L0_LAB, root=REPO_ROOT)
    lang_dir = agent_store_dir(STORE_LANGUAGE_AGENT_LAB, root=REPO_ROOT)
    ru_dir = agent_store_dir(STORE_RU_GENERAL_V0, root=REPO_ROOT)

    out: dict[str, Any] = {"stores": {}}

    if not skip_math_init:
        out["stores"][STORE_MATH_L0_LAB] = init_math_l0_lab(math_dir, bundle)

    if not skip_journal_move:
        lang_dir.mkdir(parents=True, exist_ok=True)
        out["stores"][STORE_LANGUAGE_AGENT_LAB] = {
            "journal": _copy_journal(ru_dir, lang_dir),
        }
        mem = lang_dir / "MEMORY.md"
        if not mem.is_file():
            mem.write_text(
                "\n".join(
                    [
                        f"# {STORE_LANGUAGE_AGENT_LAB}",
                        "",
                        "Agent learning lab: dialogue, grammar KB, journal/self, ortho teacher, learning tick.",
                        "Default store for `agent_sn_cen_tick`. **Not** prod DetCorpus T9.",
                        "",
                        f"Journal migrated from `{STORE_RU_GENERAL_V0}` — see `migrate_agent_lab_stores`.",
                        "",
                    ]
                ),
                encoding="utf-8",
            )

    if not skip_ru_clean:
        out["stores"][STORE_RU_GENERAL_V0] = _clean_lexicon_runtime(ru_dir)

    return out


def main() -> None:
    p = argparse.ArgumentParser(description="Migrate agent lab stores (math / language / ru-general clean)")
    p.add_argument(
        "--bundle",
        type=Path,
        default=REPO_ROOT / "lab/exp_l/kb-math-concrete-schemas-l0.bundle.v1.json",
    )
    p.add_argument("--skip-math-init", action="store_true")
    p.add_argument("--skip-journal-move", action="store_true")
    p.add_argument("--skip-ru-clean", action="store_true")
    args = p.parse_args()
    print(
        json.dumps(
            migrate_agent_lab_stores(
                bundle=args.bundle,
                skip_math_init=args.skip_math_init,
                skip_journal_move=args.skip_journal_move,
                skip_ru_clean=args.skip_ru_clean,
            ),
            ensure_ascii=False,
            indent=2,
        )
    )


if __name__ == "__main__":
    main()
