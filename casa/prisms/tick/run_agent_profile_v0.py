#!/usr/bin/env python3
"""Boot agent profile + dispatch act target (stdio / layout / sleep tick)."""

from __future__ import annotations

from casa._paths import ensure_import_paths

ensure_import_paths()

import argparse
import json
import subprocess
import sys
from pathlib import Path
from typing import Any

from casa.prisms.memory.boot_core_ltm_v0 import core_ltm_from_profile, default_core_ltm_dir, merge_core_ltm
from casa.prisms.memory.boot_linked_stores_v0 import boot_linked_stores
from casa.prisms.shared.store_boot_v0 import boot_store
from casa.prisms.shared.store_layout_v0 import agent_store_dir


def load_profile(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def resolve_store_path(root: Path, store_dir: str) -> Path:
    p = Path(store_dir)
    if p.is_absolute():
        return p
    return (root / p).resolve()


def boot_profile(root: Path, profile: dict[str, Any]) -> dict[str, Any]:
    stores = list(profile.get("stores") or [])
    mode = str((profile.get("boot") or {}).get("mode") or "single")
    if mode == "linked" and len(stores) >= 2:
        ru = resolve_store_path(root, str(stores[0]["store_dir"]))
        en = resolve_store_path(root, str(stores[1]["store_dir"]))
        core_ltm = core_ltm_from_profile(profile, root=root)
        boot = boot_linked_stores(ru, en, core_ltm_dir=core_ltm, merge_vk=True)
        boot["profile_mode"] = "linked"
        boot["stores"] = {"ru": str(ru), "en": str(en)}
        return boot
    if not stores:
        raise ValueError("profile has no stores")
    store = resolve_store_path(root, str(stores[0]["store_dir"]))
    boot = boot_store(store, prefer_field_state=True)
    core_ltm = core_ltm_from_profile(profile, root=root) or default_core_ltm_dir(root=root)
    if (core_ltm / "pack.manifest.json").is_file():
        boot["vk_boot"] = merge_core_ltm(boot["state"], core_ltm)
    boot["profile_mode"] = "single"
    boot["stores"] = {"primary": str(store)}
    return boot


def dispatch_act(root: Path, profile: dict[str, Any], *, extra_args: list[str]) -> int:
    act = profile.get("act") or {}
    kind = str(act.get("kind") or "stdio")
    if kind == "stdio":
        entry = str(act.get("entry") or "tools/t9_runtime_v0.py")
        cmd = [sys.executable, entry, *extra_args]
        return subprocess.call(cmd, cwd=str(root))
    if kind == "cide_stdio":
        entry = str(act.get("entry") or "tools/cide_act_bridge_v0.py")
        cmd = [sys.executable, entry, *extra_args]
        return subprocess.call(cmd, cwd=str(root))
    if kind == "mcp":
        print(
            json.dumps(
                {
                    "error": "mcp act not wired in run_agent_profile_v0 yet",
                    "server": act.get("server"),
                    "target": act.get("target"),
                },
                ensure_ascii=False,
            ),
            file=sys.stderr,
        )
        return 2
    raise ValueError(f"unknown act.kind: {kind!r}")


def main() -> None:
    root = Path(__file__).resolve().parent.parent
    p = argparse.ArgumentParser(description="Run agent profile (boot + act)")
    p.add_argument("--profile", type=Path, required=True)
    p.add_argument("--boot-only", action="store_true")
    p.add_argument("--act-args", nargs=argparse.REMAINDER, help="Passed to act entry")
    args = p.parse_args()

    profile = load_profile(args.profile.resolve())
    boot = boot_profile(root, profile)
    doc = {
        "schema_version": 1,
        "profile_id": profile.get("profile_id"),
        "boot": {k: v for k, v in boot.items() if k != "state"},
        "act": profile.get("act"),
    }
    print(json.dumps(doc, ensure_ascii=False, indent=2))
    if args.boot_only:
        raise SystemExit(0)

    extra = list(args.act_args or [])
    if extra and extra[0] == "--":
        extra = extra[1:]
    raise SystemExit(dispatch_act(root, profile, extra_args=extra))


if __name__ == "__main__":
    main()
