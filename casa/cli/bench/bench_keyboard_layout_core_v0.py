#!/usr/bin/env python3
"""Bench split keyboard core: QWERTY + JCUKEN decode from field."""

from __future__ import annotations

from casa._paths import ensure_import_paths

ensure_import_paths()

import argparse
import json
from pathlib import Path

from casa.prisms.shared.field_write import load_field_state
from casa.prisms.shared.import_ltm_pack_v0 import import_pack
from casa.prisms.memory.sss_cylinders_v0 import ensure_prisms
from casa.prisms.memory.vk_decode_v0 import decode_branches
from casa.prisms.memory.vk_layout_field_v0 import verify_keyboard_core_on_field


def main() -> None:
    root = Path(__file__).resolve().parent.parent
    p = argparse.ArgumentParser()
    p.add_argument("--core-dir", type=Path, default=root / "lab/agent-core/vk-layouts-v0")
    args = p.parse_args()
    core = args.core_dir.resolve()
    ltm = core / "ltm"
    manifest = json.loads((ltm / "pack.manifest.json").read_text(encoding="utf-8"))
    state = ensure_prisms(load_field_state(core / "field_state.json") if (core / "field_state.json").is_file() else {})
    import_pack(state, ltm, manifest=manifest)
    verify = verify_keyboard_core_on_field(state)
    events = [
        {"key_id": "KeyH", "action": "down"},
        {"key_id": "KeyE", "action": "down"},
        {"key_id": "KeyL", "action": "down"},
        {"key_id": "KeyL", "action": "down"},
        {"key_id": "KeyO", "action": "down"},
    ]
    ru_events = [
        {"key_id": "KeyR", "action": "down"},
        {"key_id": "KeyU", "action": "down"},
    ]
    en = decode_branches(events, ["qwerty_us"], state=state)
    ru = decode_branches(ru_events, ["jcuken_ru"], state=state)
    report = {
        "bench": "keyboard_layout_core_v0",
        "verify": verify,
        "decode_en": en,
        "decode_ru": ru,
        "pass": bool(verify.get("pass")) and en.get("qwerty_us") == "hello" and ru.get("jcuken_ru") == "кг",
    }
    print(json.dumps(report, ensure_ascii=False, indent=2))
    raise SystemExit(0 if report["pass"] else 1)


if __name__ == "__main__":
    main()
