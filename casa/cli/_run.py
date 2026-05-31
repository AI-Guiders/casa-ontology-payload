"""Run a legacy CLI module by name: python -m casa.cli store_boot_v0 --help."""

from __future__ import annotations

import sys

from casa.legacy import import_legacy, manifest


def main(argv: list[str] | None = None) -> int:
    args = list(argv if argv is not None else sys.argv[1:])
    if not args or args[0] in ("-h", "--help"):
        names = ", ".join(sorted(manifest())[:12])
        print(f"usage: python -m casa.cli <legacy_module> [args...]\nknown modules: {len(manifest())} (e.g. {names}, …)")
        return 0 if args and args[0] in ("-h", "--help") else 2
    legacy = args[0].removesuffix(".py")
    mod = import_legacy(legacy)
    sys.argv = [f"{legacy}.py", *args[1:]]
    if hasattr(mod, "main"):
        return int(mod.main() or 0)
    raise SystemExit(f"{legacy} has no main()")


if __name__ == "__main__":
    raise SystemExit(main())
