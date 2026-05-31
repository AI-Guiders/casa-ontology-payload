#!/usr/bin/env python3
"""Digest-level control extensions: predict / DAN / value (CASA-ADR-0010).

Runs after DMN decode on each macro tick T. Field NCA rollout is roadmap; this
module is the deterministic digest contract wired into SN/CEN tick reports.
"""

from __future__ import annotations

from casa._paths import ensure_import_paths

ensure_import_paths()

from dataclasses import asdict, dataclass
from typing import Any, Iterable

from casa.prisms.control import attention_v0 as dan
from casa.prisms.control import predict_v0 as predict
from casa.prisms.control import value_v0 as value


@dataclass(frozen=True, slots=True)
class ControlExtensions:
    predicted: tuple[str, ...]
    surprise: tuple[str, ...]
    prediction_error: float
    dan_mask: tuple[str, ...]
    sparse_ratio: float
    masked_digest: tuple[str, ...]
    value: float

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


def run_control_extensions(
    *,
    prior_digest: Iterable[str],
    current_digest: Iterable[str],
    goal: Iterable[str],
    predict_model: dict[str, Any] | None = None,
    fit_trajectory: list[Iterable[str]] | None = None,
    correction_kind: str | None = None,
    task_relevant: bool = False,
) -> ControlExtensions:
    """P6–P9 digest pipeline: predict error → DAN mask → value tag."""
    prior = predict.as_digest(prior_digest)
    current = predict.as_digest(current_digest)
    universe = current | prior | predict.as_digest(goal)

    model = predict_model
    if model is None and fit_trajectory:
        model = predict.fit_transitions(list(fit_trajectory))

    predicted = predict.predict_next(prior or current, model or {"succ": {}, "seen": {}})
    surprise = predict.surprise(predicted, current)
    err = predict.prediction_error(predicted, current)

    salience = surprise | ({f"surprise.{correction_kind}"} if correction_kind and surprise else set())
    mask = dan.spotlight(goal, universe, salience=salience)
    masked = dan.apply_mask(current, mask)
    sparse = dan.sparse_ratio(current, mask)

    v = value.episode_value(
        surprise=surprise,
        correction_kind=correction_kind,
        task_relevant=task_relevant or bool(goal),
        goal_match=bool(goal) and bool(predict.as_digest(goal) & current),
    )

    return ControlExtensions(
        predicted=tuple(sorted(predicted)),
        surprise=tuple(sorted(surprise)),
        prediction_error=round(float(err), 4),
        dan_mask=tuple(sorted(mask)),
        sparse_ratio=round(float(sparse), 4),
        masked_digest=tuple(sorted(masked)),
        value=round(float(v), 3),
    )
