#!/usr/bin/env python3
"""Subject mode profile — von-neumann as interlocutor (ADR-0045)."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any


def store_profile_path(store_dir: Path) -> Path:
    return store_dir.resolve() / "store_profile.json"


def load_store_profile(store_dir: Path) -> dict[str, Any]:
    path = store_profile_path(store_dir)
    if not path.is_file():
        return {}
    try:
        raw = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {}
    return raw if isinstance(raw, dict) else {}


def apply_subject_profile(store_dir: Path, state: dict) -> None:
    """Merge store_profile into runtime state.subject flags."""
    profile = load_store_profile(store_dir)
    subject = state.setdefault("subject", {})
    if not isinstance(subject, dict):
        return
    if profile.get("subject_mode") is True:
        subject["subject_mode"] = True
    name = profile.get("display_name") or profile.get("agent_display_name")
    if name:
        subject["display_name"] = str(name)
    if profile.get("locale"):
        store = state.setdefault("store", {})
        if isinstance(store, dict):
            store.setdefault("locale", str(profile["locale"]))


def is_subject_mode(state: dict, store_dir: Path | None = None) -> bool:
    subject = state.get("subject")
    if isinstance(subject, dict) and subject.get("subject_mode"):
        return True
    if store_dir is not None:
        profile = load_store_profile(store_dir)
        if profile.get("subject_mode") is True:
            return True
    store = state.get("store")
    if isinstance(store, dict) and store.get("store_id") == "von-neumann":
        if store_dir is not None and load_store_profile(store_dir).get("subject_mode") is not False:
            return True
    return False


def subject_display_name(state: dict, store_dir: Path | None = None) -> str:
    subject = state.get("subject")
    if isinstance(subject, dict) and subject.get("display_name"):
        return str(subject["display_name"])
    if store_dir is not None:
        profile = load_store_profile(store_dir)
        if profile.get("display_name"):
            return str(profile["display_name"])
    store = state.get("store")
    if isinstance(store, dict) and store.get("store_id"):
        return str(store["store_id"])
    return "subject"
