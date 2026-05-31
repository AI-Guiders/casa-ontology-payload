#!/usr/bin/env python3
"""Export PyTorch NCA checkpoint (model.pt) to ONNX for C# / ORT inference."""

from __future__ import annotations

from casa._paths import ensure_import_paths

ensure_import_paths()

import json
from pathlib import Path
from typing import Any, Literal

import torch
import torch.nn as nn
import torch.nn.functional as F

from casa.cli.train_dmn_nca import UpdateRule, sobel_kernels

ExportMode = Literal["step", "rollout"]


def _perceive_fixed(state: torch.Tensor, kx: torch.Tensor, ky: torch.Tensor, channel_n: int) -> torch.Tensor:
    """Sobel perceive with channel count fixed at export time (ONNX-safe)."""
    gx = F.conv2d(state, kx, padding=1, groups=channel_n)
    gy = F.conv2d(state, ky, padding=1, groups=channel_n)
    return torch.cat([state, gx, gy], dim=1)


class NcaStepOnnx(nn.Module):
    """One CA step: perceive → UpdateRule → state + dx (eval fire_rate=1)."""

    def __init__(self, rule: UpdateRule, channel_n: int) -> None:
        super().__init__()
        self.rule = rule
        self.channel_n = int(channel_n)
        kx, ky = sobel_kernels(torch.device("cpu"))
        self.register_buffer("kx", kx.repeat(self.channel_n, 1, 1, 1))
        self.register_buffer("ky", ky.repeat(self.channel_n, 1, 1, 1))

    def forward(self, state: torch.Tensor) -> torch.Tensor:
        perception = _perceive_fixed(state, self.kx, self.ky, self.channel_n)
        delta = self.rule(perception)
        return (state + delta).clamp(0.0, 1.0)


class NcaRolloutOnnx(nn.Module):
    """Fixed-step rollout (steps baked into graph)."""

    def __init__(self, rule: UpdateRule, channel_n: int, steps: int) -> None:
        super().__init__()
        self.step = NcaStepOnnx(rule, channel_n)
        self.steps = int(steps)

    def forward(self, state: torch.Tensor) -> torch.Tensor:
        x = state
        for _ in range(self.steps):
            x = self.step(x)
        return x


def load_nca_checkpoint(path: Path) -> dict[str, Any]:
    ckpt = torch.load(path, map_location="cpu", weights_only=False)
    if not isinstance(ckpt, dict) or "state_dict" not in ckpt:
        raise ValueError(f"not an NCA checkpoint: {path}")
    return ckpt


def build_rule_from_checkpoint(ckpt: dict[str, Any]) -> UpdateRule:
    channel_n = int(ckpt["channel_n"])
    hidden = int(ckpt.get("hidden") or 96)
    rule = UpdateRule(channel_n=channel_n, hidden=hidden)
    rule.load_state_dict(ckpt["state_dict"])
    rule.eval()
    return rule


def export_nca_onnx(
    model_pt: Path,
    out_path: Path | None = None,
    *,
    mode: ExportMode = "rollout",
    opset: int = 17,
    verify: bool = False,
    dynamo: bool = False,
) -> dict[str, Any]:
    """Export model.pt → ONNX (+ sidecar JSON). Requires `onnx` package."""
    try:
        import onnx
    except ImportError as exc:
        raise ImportError("install onnx: pip install onnx (optional: onnxruntime for --verify)") from exc

    if dynamo:
        try:
            import onnxscript  # noqa: F401
        except ImportError as exc:
            raise ImportError("dynamo export requires: pip install onnxscript") from exc

    model_pt = model_pt.resolve()
    ckpt = load_nca_checkpoint(model_pt)
    rule = build_rule_from_checkpoint(ckpt)

    channel_n = int(ckpt["channel_n"])
    width = int(ckpt.get("width") or 32)
    height = int(ckpt.get("height") or 32)
    steps = int(ckpt.get("steps") or 24)

    if mode == "step":
        wrapper: nn.Module = NcaStepOnnx(rule, channel_n)
        input_name = "state"
        output_name = "state_next"
    else:
        wrapper = NcaRolloutOnnx(rule, channel_n, steps)
        input_name = "state"
        output_name = "state_out"

    wrapper.eval()
    dummy = torch.zeros(1, channel_n, height, width)

    out_path = (out_path or model_pt.with_name("model.onnx")).resolve()
    out_path.parent.mkdir(parents=True, exist_ok=True)

    dynamic_axes = {
        input_name: {0: "batch", 2: "height", 3: "width"},
        output_name: {0: "batch", 2: "height", 3: "width"},
    }

    torch.onnx.export(
        wrapper,
        dummy,
        str(out_path),
        input_names=[input_name],
        output_names=[output_name],
        dynamic_axes=dynamic_axes,
        opset_version=opset,
        do_constant_folding=True,
        dynamo=dynamo,
    )

    if dynamo:
        onnx.checker.check_model(str(out_path))
    else:
        onnx.checker.check_model(out_path.read_bytes())

    sidecar = out_path.with_suffix(out_path.suffix + ".meta.json")
    meta = {
        "schema_version": 1,
        "kind": "nca_onnx_export",
        "mode": mode,
        "source_pt": str(model_pt),
        "onnx_path": str(out_path),
        "opset": opset,
        "lattice_id": ckpt.get("lattice_id"),
        "channel_n": channel_n,
        "hidden": int(ckpt.get("hidden") or 96),
        "width": width,
        "height": height,
        "steps": steps if mode == "rollout" else 1,
        "export_backend": "dynamo" if dynamo else "torchscript",
        "token_ids": list(ckpt.get("token_ids") or []),
        "inputs": [{input_name: ["batch", channel_n, "height", "width"]}],
        "outputs": [{output_name: ["batch", channel_n, "height", "width"]}],
    }
    sidecar.write_text(json.dumps(meta, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    report: dict[str, Any] = {
        "exported": str(out_path),
        "meta": str(sidecar),
        "mode": mode,
        "export_backend": meta["export_backend"],
        "channel_n": channel_n,
        "steps": meta["steps"],
        "token_count": len(meta["token_ids"]),
    }

    if verify:
        report["verify"] = _verify_ort(wrapper, dummy, out_path, input_name, output_name)

    return report


def _verify_ort(
    torch_model: nn.Module,
    dummy: torch.Tensor,
    onnx_path: Path,
    input_name: str,
    output_name: str,
) -> dict[str, Any]:
    try:
        import numpy as np
        import onnxruntime as ort
    except ImportError:
        return {"skipped": True, "reason": "onnxruntime not installed"}

    with torch.no_grad():
        expected = torch_model(dummy).numpy()

    sess = ort.InferenceSession(str(onnx_path), providers=["CPUExecutionProvider"])
    got = sess.run([output_name], {input_name: dummy.numpy()})[0]
    max_abs = float(np.max(np.abs(expected - got)))
    return {"max_abs_diff": max_abs, "ok": max_abs < 1e-4}


def main() -> None:
    import argparse

    p = argparse.ArgumentParser(description="Export NCA model.pt to ONNX (manual step)")
    p.add_argument("--model", type=Path, required=True, help="Path to model.pt")
    p.add_argument("--out", type=Path, default=None, help="Output .onnx (default: beside model.pt)")
    p.add_argument("--mode", choices=("step", "rollout"), default="rollout", help="step=one CA tick; rollout=full steps from ckpt")
    p.add_argument("--opset", type=int, default=17)
    p.add_argument("--dynamo", action="store_true", help="Use torch.export ONNX backend (needs onnxscript)")
    p.add_argument("--verify", action="store_true", help="Compare ORT vs PyTorch on dummy grid")
    args = p.parse_args()

    report = export_nca_onnx(
        args.model,
        args.out,
        mode=args.mode,
        opset=args.opset,
        verify=args.verify,
        dynamo=args.dynamo,
    )
    print(json.dumps(report, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
