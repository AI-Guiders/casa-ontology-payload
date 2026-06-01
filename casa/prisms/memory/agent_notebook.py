#!/usr/bin/env python3
"""Agent-owned notebooks (journal domains) — create/list without teacher ingest."""

from __future__ import annotations

from casa._paths import ensure_import_paths

ensure_import_paths()

from pathlib import Path
from typing import Any

from casa.prisms.memory.agent_journal import (
    append_journal_entry,
    journal_stats,
    list_journal_domains,
    notebook_tag,
    safe_journal_domain,
)
from casa.prisms.shared.store_layout import journal_entries_path


def notebook_exists(store_dir: Path, notebook_id: str) -> bool:
    store_dir = store_dir.resolve()
    domain = safe_journal_domain(notebook_id)
    return journal_entries_path(store_dir, domain).is_file()


def list_agent_notebooks(store_dir: Path) -> list[dict[str, Any]]:
    """Notebooks = journal domain shards with index metadata."""
    store_dir = store_dir.resolve()
    stats = journal_stats(store_dir)
    by_domain = {d["domain"]: d for d in stats.get("domains") or []}
    out: list[dict[str, Any]] = []
    for domain in list_journal_domains(store_dir):
        meta = by_domain.get(domain) or {}
        out.append(
            {
                "notebook_id": domain,
                "domain": domain,
                "entry_count": int(meta.get("entry_count") or 0),
                "updated_at": meta.get("updated_at"),
            }
        )
    return out


def create_agent_notebook(
    store_dir: Path,
    notebook_id: str,
    *,
    title: str = "",
    intro: str | None = None,
    tags: list[str] | None = None,
    created_by: str = "agent",
    if_exists: str = "skip",
) -> dict[str, Any]:
    """Open a new workbook shard under journal/<notebook_id>/.

    `if_exists`: skip | error | append_intro (add intro note even if shard exists).
    """
    store_dir = store_dir.resolve()
    domain = safe_journal_domain(notebook_id)
    exists = notebook_exists(store_dir, domain)
    if exists and if_exists == "error":
        raise ValueError(f"notebook already exists: {domain}")
    if exists and if_exists == "skip" and not intro:
        return {
            "created": False,
            "notebook_id": domain,
            "domain": domain,
            "reason": "already_exists",
            "entry_count": next(
                (n["entry_count"] for n in list_agent_notebooks(store_dir) if n["notebook_id"] == domain),
                0,
            ),
        }

    journal_entries_path(store_dir, domain).parent.mkdir(parents=True, exist_ok=True)
    if not journal_entries_path(store_dir, domain).is_file():
        journal_entries_path(store_dir, domain).write_text("", encoding="utf-8")

    label = (title or notebook_id).strip()
    bootstrap = None
    if intro and (not exists or if_exists == "append_intro"):
        row_tags = ["notebook:bootstrap", notebook_tag(domain), *(tags or [])]
        bootstrap = append_journal_entry(
            store_dir,
            {
                "kind": "note",
                "text": intro.strip(),
                "tags": row_tags,
                "meta": {
                    "notebook": domain,
                    "status": "open",
                    "created_by": created_by,
                    "title": label,
                },
            },
            domain=domain,
        )

    books = list_agent_notebooks(store_dir)
    entry_count = next((b["entry_count"] for b in books if b["notebook_id"] == domain), 0)
    return {
        "created": not exists,
        "notebook_id": domain,
        "domain": domain,
        "title": label,
        "bootstrap_entry": bootstrap,
        "entry_count": entry_count,
        "created_by": created_by,
    }


def ensure_agent_notebook(
    store_dir: Path,
    notebook_id: str,
    *,
    title: str = "",
    intro: str | None = None,
) -> dict[str, Any]:
    if notebook_exists(store_dir, notebook_id):
        domain = safe_journal_domain(notebook_id)
        entry_count = next(
            (n["entry_count"] for n in list_agent_notebooks(store_dir) if n["notebook_id"] == domain),
            0,
        )
        return {
            "created": False,
            "notebook_id": domain,
            "domain": domain,
            "reason": "already_exists",
            "entry_count": entry_count,
        }
    return create_agent_notebook(
        store_dir,
        notebook_id,
        title=title,
        intro=intro,
        if_exists="skip",
    )
