#!/usr/bin/env python3
"""Persistence boundary: wire dict ↔ FieldState."""

from __future__ import annotations

from typing import Any

from casa.domain.field_state import FieldState


def field_state_from_dict(state: dict[str, Any]) -> FieldState:
    return FieldState.bind(state)


def field_state_to_dict(field: FieldState) -> dict[str, Any]:
    return field.wire
