#!/usr/bin/env python3
"""Host cold-boot: seed bootstrap_canon lattices for store locale (RU first)."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from casa.prisms.memory.bootstrap_morph_role import bootstrap_morph_role_lattice, morph_role_lattice_ids
from casa.prisms.shared.store_persist import save_runtime_state

_LOCALE_MORPH_LATTICE: dict[str, str] = {
    "ru": "morph-role-ru",
    "uk": "morph-role-ru",
    "be": "morph-role-ru",
    "en": "morph-role-en",
}


def morph_lattice_for_locale(locale: str) -> str | None:
    loc = str(locale or "ru").strip().lower()
    return _LOCALE_MORPH_LATTICE.get(loc)


def bootstrap_host_canon_lattices(
    store_dir: Path,
    state: dict[str, Any],
    *,
    locale: str = "ru",
    persist: bool = True,
) -> dict[str, Any]:
    """Seed host bootstrap canon shelves appropriate for store locale."""
    store_dir = store_dir.resolve()
    reps: list[dict[str, Any]] = []
    morph_lid = morph_lattice_for_locale(locale)
    if morph_lid:
        reps.append(
            bootstrap_morph_role_lattice(
                store_dir,
                state,
                lattice_id=morph_lid,
                persist=False,
            )
        )
    out = {
        "locale": locale,
        "morph_role_lattices": sorted(morph_role_lattice_ids()),
        "bootstrapped": reps,
    }
    if persist and reps:
        save_runtime_state(store_dir, state, force=True)
    return out
