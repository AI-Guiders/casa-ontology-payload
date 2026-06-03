import sys
from pathlib import Path

_vc = Path(__file__).resolve().parents[1]
if str(_vc) not in sys.path:
    sys.path.insert(0, str(_vc))
from vc_paths import install  # noqa: E402

install(__file__)
