#!/usr/bin/env python3
"""Smoke: py_compile + import main modules (без load store)."""

from __future__ import annotations

import importlib.util
import py_compile
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent
errors: list[str] = []

for py in ("curriculum_lab.py", "lex_steps.py", "lab_paths.py"):
    try:
        py_compile.compile(ROOT / py, doraise=True)
    except py_compile.PyCompileError as e:
        errors.append(f"compile {py}: {e}")

for sub in ("micro-literacy", "micro-geom"):
    d = ROOT / sub
    for py in sorted(d.glob("*.py")):
        if py.name.startswith("_"):
            continue
        try:
            py_compile.compile(py, doraise=True)
        except py_compile.PyCompileError as e:
            errors.append(f"compile {sub}/{py.name}: {e}")
        if not py.name.startswith("run_") and not py.name.startswith("reinforce_"):
            continue
        spec = importlib.util.spec_from_file_location(f"{sub}.{py.stem}", py)
        if spec is None or spec.loader is None:
            errors.append(f"spec {py.name}")
            continue
        mod = importlib.util.module_from_spec(spec)
        try:
            sys.modules[spec.name] = mod
            spec.loader.exec_module(mod)
        except Exception as e:
            errors.append(f"import {sub}/{py.name}: {e}")

if errors:
    print("\n".join(errors))
    sys.exit(1)
print("ok", flush=True)
