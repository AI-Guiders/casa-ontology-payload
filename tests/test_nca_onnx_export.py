"""ONNX export for NCA checkpoints."""

from __future__ import annotations

from pathlib import Path

import pytest
import torch

from casa.cli.train_dmn_nca import UpdateRule
from casa.prisms.shared.nca_onnx_export import export_nca_onnx

pytest.importorskip("onnx")


def _write_minimal_ckpt(path: Path, *, channel_n: int = 8, h: int = 8, w: int = 8, steps: int = 3) -> None:
    rule = UpdateRule(channel_n=channel_n, hidden=16)
    torch.save(
        {
            "schema_version": 1,
            "kind": "sss_lattice_nca",
            "lattice_id": "test-lattice",
            "channel_n": channel_n,
            "token_ids": [f"T:{i}" for i in range(channel_n - 6)],
            "width": w,
            "height": h,
            "hidden": 16,
            "steps": steps,
            "state_dict": rule.state_dict(),
        },
        path,
    )


def test_export_rollout_and_step(tmp_path: Path) -> None:
    import onnx

    pt = tmp_path / "model.pt"
    _write_minimal_ckpt(pt)

    rollout_out = tmp_path / "rollout.onnx"
    rep = export_nca_onnx(pt, rollout_out, mode="rollout")
    assert rollout_out.is_file()
    assert Path(rep["meta"]).is_file()
    onnx.checker.check_model(str(rollout_out))

    step_out = tmp_path / "step.onnx"
    export_nca_onnx(pt, step_out, mode="step")
    assert step_out.is_file()


def test_export_dynamo_step(tmp_path: Path) -> None:
    pytest.importorskip("onnxscript")
    import onnx

    pt = tmp_path / "model.pt"
    _write_minimal_ckpt(pt)
    out = tmp_path / "step.dynamo.onnx"
    rep = export_nca_onnx(pt, out, mode="step", dynamo=True, verify=True)
    assert rep["export_backend"] == "dynamo"
    assert out.is_file()
    onnx.checker.check_model(str(out))
    assert rep.get("verify", {}).get("ok") is True
