"""Function call backends (wire adapters)."""

from casa.body.backends.in_process import InProcessFunctionBackend
from casa.body.backends.registry import build_backend
from casa.body.backends.stub import StubFunctionBackend

__all__ = ["InProcessFunctionBackend", "StubFunctionBackend", "build_backend"]
