"""Field-materialized reading model — predict without cartridge at runtime."""

from __future__ import annotations

import json
from pathlib import Path

from casa.prisms.memory.f0_field_reading import reading_model_from_decoded
from casa.prisms.memory.f0_stack import decode_f0_lattice, encode_f0_lattice, rank_cue_on_f0
from casa.prisms.memory.memory_prisms import ensure_prisms
from casa.prisms.shared.field_write import load_field_state
from casa.prisms.shared.store_layout import field_state_path
from casa.prisms.tick.predict_tick import predict_tick

ROOT = Path(__file__).resolve().parent.parent
BUNDLE = ROOT / "lab/exp_l/kb-math-concrete-schemas-l0.bundle.v1.json"
STORE = ROOT / "lab/agent-stores/math-l0-lab"


def test_rank_from_field_only_after_encode() -> None:
    bundle = json.loads(BUNDLE.read_text(encoding="utf-8"))
    lat = encode_f0_lattice(bundle)
    dec = decode_f0_lattice(lat)
    model = reading_model_from_decoded(dec)
    assert model.get("reading_contexts")
    assert model.get("symbol_senses")
    assert rank_cue_on_f0(dec, "1+2")[0][0] == "math.op.add"


def test_predict_schema_without_bundle_param() -> None:
    if not (STORE / "ltm/pack.manifest.json").is_file():
        return
    state = ensure_prisms(load_field_state(field_state_path(STORE)))
    tick = predict_tick(state, "1+2", modality="schema")
    assert (tick.get("predict") or {}).get("hypothesis") == "math.op.add"
