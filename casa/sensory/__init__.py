"""Sensory host layer: capture → codec → imprint plan (ADR-0027/0028)."""

from casa.sensory.rgb_frame import RgbFrame
from casa.sensory.load_rgb_frame import load_rgb_frame

__all__ = ["RgbFrame", "load_rgb_frame"]
