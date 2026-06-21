"""Impulse trace — substrate-wide nervous observability (CASA-ADR-0080)."""

from __future__ import annotations

import json
import os
import time
import uuid
from contextlib import contextmanager
from dataclasses import dataclass, field
from enum import StrEnum
from pathlib import Path
from typing import Any, Iterator

from casa.nervous.channels import ImpulseChannel, ImpulseOutcome

_SCHEMA = "casa.impulse.v1"
_RING_MAX = int(os.environ.get("CASA_IMPULSE_RING", "1000") or "1000")


class DebugLevel(StrEnum):
    OFF = "off"
    SUMMARY = "summary"
    FULL = "full"


def resolve_debug_level(explicit: str | None = None) -> DebugLevel:
    raw = (explicit or os.environ.get("CASA_IMPULSE_TRACE") or "off").strip().lower()
    try:
        return DebugLevel(raw)
    except ValueError:
        return DebugLevel.OFF


@dataclass
class SynapticEvent:
    seq: int
    node: str
    kind: str
    zone: str = ""
    inputs: dict[str, Any] = field(default_factory=dict)
    potentials: list[dict[str, Any]] = field(default_factory=list)
    selected: list[str] = field(default_factory=list)
    rejected_above_floor: int = 0
    reason: str = ""

    def to_dict(self) -> dict[str, Any]:
        out: dict[str, Any] = {
            "seq": self.seq,
            "node": self.node,
            "kind": self.kind,
        }
        if self.zone:
            out["zone"] = self.zone
        if self.inputs:
            out["inputs"] = self.inputs
        if self.potentials:
            out["potentials"] = self.potentials
        if self.selected:
            out["selected"] = self.selected
        if self.rejected_above_floor:
            out["rejected_above_floor"] = self.rejected_above_floor
        if self.reason:
            out["reason"] = self.reason
        return out


@dataclass
class ImpulseRecord:
    header: dict[str, Any]
    events: list[SynapticEvent] = field(default_factory=list)
    summary: dict[str, Any] = field(default_factory=dict)

    def to_dict(self, *, debug_level: DebugLevel) -> dict[str, Any]:
        payload = dict(self.header)
        payload["summary"] = dict(self.summary)
        if debug_level == DebugLevel.FULL:
            payload["events"] = [event.to_dict() for event in self.events]
        elif debug_level == DebugLevel.SUMMARY:
            payload["events"] = [
                event.to_dict()
                for event in self.events
                if event.kind in {"select", "threshold", "budget", "route"}
            ]
        return payload


class _ImpulseChannelWriter:
    __slots__ = ("_recorder", "_record", "_finished")

    def __init__(self, recorder: "ImpulseRecorder", record: ImpulseRecord) -> None:
        self._recorder = recorder
        self._record = record
        self._finished = False

    @property
    def impulse_id(self) -> str:
        return str(self._record.header["impulse_id"])

    def _append(
        self,
        *,
        node: str,
        kind: str,
        zone: str = "",
        inputs: dict[str, Any] | None = None,
        potentials: list[dict[str, Any]] | None = None,
        selected: list[str] | None = None,
        rejected_above_floor: int = 0,
        reason: str = "",
    ) -> None:
        if self._finished or self._recorder.level == DebugLevel.OFF:
            return
        seq = len(self._record.events) + 1
        self._record.events.append(
            SynapticEvent(
                seq=seq,
                node=node,
                kind=kind,
                zone=zone,
                inputs=dict(inputs or {}),
                potentials=list(potentials or []),
                selected=list(selected or []),
                rejected_above_floor=rejected_above_floor,
                reason=reason,
            )
        )

    def activate(
        self,
        node: str,
        *,
        zone: str = "",
        inputs: dict[str, Any] | None = None,
    ) -> None:
        self._append(node=node, kind="activate", zone=zone, inputs=inputs)

    def score(
        self,
        node: str,
        *,
        zone: str = "",
        potentials: list[dict[str, Any]] | None = None,
        inputs: dict[str, Any] | None = None,
    ) -> None:
        self._append(
            node=node,
            kind="score",
            zone=zone,
            potentials=potentials,
            inputs=inputs,
        )

    def suppress(
        self,
        node: str,
        *,
        zone: str = "",
        reason: str = "",
        inputs: dict[str, Any] | None = None,
    ) -> None:
        self._append(node=node, kind="suppress", zone=zone, reason=reason, inputs=inputs)

    def threshold(
        self,
        node: str,
        *,
        zone: str = "",
        reason: str = "",
        inputs: dict[str, Any] | None = None,
    ) -> None:
        self._append(node=node, kind="threshold", zone=zone, reason=reason, inputs=inputs)

    def select(
        self,
        node: str,
        *,
        zone: str = "",
        selected: list[str] | None = None,
        potentials: list[dict[str, Any]] | None = None,
        inputs: dict[str, Any] | None = None,
        rejected_above_floor: int = 0,
    ) -> None:
        self._append(
            node=node,
            kind="select",
            zone=zone,
            selected=selected,
            potentials=potentials,
            inputs=inputs,
            rejected_above_floor=rejected_above_floor,
        )

    def budget(
        self,
        node: str,
        *,
        zone: str = "",
        reason: str = "",
        inputs: dict[str, Any] | None = None,
    ) -> None:
        self._append(node=node, kind="budget", zone=zone, reason=reason, inputs=inputs)

    def route(
        self,
        node: str,
        *,
        zone: str = "executive",
        inputs: dict[str, Any] | None = None,
        selected: list[str] | None = None,
    ) -> None:
        self._append(
            node=node,
            kind="route",
            zone=zone,
            inputs=inputs,
            selected=selected,
        )

    def record_bind_ranked(self, ranked: dict[str, Any]) -> None:
        winner = ranked.get("winner") if isinstance(ranked.get("winner"), dict) else {}
        runners = ranked.get("runner_up") if isinstance(ranked.get("runner_up"), list) else []
        potentials: list[dict[str, Any]] = []
        if winner:
            potentials.append(
                {
                    "id": str(winner.get("winner_bind_hub") or winner.get("winner_concept_id") or ""),
                    "score": int(winner.get("winner_score") or 0),
                    "delta": 0,
                    "reason": str(winner.get("winner_source") or "bind_winner"),
                }
            )
        for row in runners[:3]:
            if not isinstance(row, dict):
                continue
            potentials.append(
                {
                    "id": str(row.get("winner_bind_hub") or row.get("winner_concept_id") or ""),
                    "score": int(row.get("winner_score") or 0),
                    "delta": 0,
                    "reason": "runner_up",
                }
            )
        selected = [
            str(winner.get("winner_bind_hub") or winner.get("winner_concept_id") or "")
        ] if winner else []
        self.select(
            "dialogue_bind.speech_act_scoring",
            zone="social",
            selected=[item for item in selected if item],
            potentials=potentials,
            rejected_above_floor=max(0, int(ranked.get("candidate_count") or 0) - len(selected)),
            inputs={"candidate_count": int(ranked.get("candidate_count") or 0)},
        )

    def finish(
        self,
        outcome: ImpulseOutcome | str,
        *,
        zones_touched: list[str] | None = None,
    ) -> dict[str, Any]:
        if self._finished:
            return self._record.summary
        self._finished = True
        if self._recorder.level == DebugLevel.OFF:
            return self._record.summary
        finished_ms = int(time.time() * 1000)
        self._record.header["finished_at_ms"] = finished_ms
        self._record.header["outcome"] = str(outcome)
        if zones_touched:
            self._record.header["zones_touched"] = list(zones_touched)
        self._record.summary = self._recorder._build_summary(self._record)
        self._recorder._commit(self._record)
        return self._record.summary


class ImpulseRecorder:
    """Per-macro-tick impulse recorder; no-op when debug level is off."""

    def __init__(self, *, level: DebugLevel | None = None) -> None:
        self.level = level or resolve_debug_level()
        self._tick_id: int | None = None
        self._store_dir: Path | None = None
        self._impulses: list[ImpulseRecord] = []

    @property
    def is_active(self) -> bool:
        return self.level != DebugLevel.OFF

    def begin_tick(self, tick_id: int, store_dir: Path) -> None:
        if not self.is_active:
            return
        tid = int(tick_id)
        resolved = store_dir.resolve()
        if self._tick_id == tid and self._store_dir == resolved:
            return
        self._tick_id = tid
        self._store_dir = resolved
        self._impulses = []

    @contextmanager
    def channel(
        self,
        channel: ImpulseChannel | str,
        *,
        store_dir: Path | None = None,
    ) -> Iterator[_ImpulseChannelWriter]:
        if store_dir is not None and self._store_dir is None:
            self._store_dir = store_dir.resolve()
        if not self.is_active:
            yield _ImpulseChannelWriter(self, ImpulseRecord(header={}))
            return
        tick_id = self._tick_id if self._tick_id is not None else 0
        store = str(self._store_dir or store_dir or "")
        started_ms = int(time.time() * 1000)
        record = ImpulseRecord(
            header={
                "schema": _SCHEMA,
                "impulse_id": str(uuid.uuid4()),
                "tick_id": tick_id,
                "channel": str(channel),
                "store_dir": store,
                "debug_level": self.level.value,
                "started_at_ms": started_ms,
                "finished_at_ms": 0,
                "outcome": ImpulseOutcome.NO_OP.value,
                "zones_touched": [],
            }
        )
        writer = _ImpulseChannelWriter(self, record)
        try:
            yield writer
        finally:
            if self.is_active and not writer._finished:
                writer.finish(ImpulseOutcome.NO_OP)

    def end_tick(self) -> list[dict[str, Any]]:
        if not self.is_active:
            return []
        summaries = [dict(item.summary) for item in self._impulses if item.summary]
        self._tick_id = None
        self._store_dir = None
        self._impulses = []
        return summaries

    def last_impulses(self) -> list[ImpulseRecord]:
        return list(self._impulses)

    def _build_summary(self, record: ImpulseRecord) -> dict[str, Any]:
        winners: list[str] = []
        thresholds: list[str] = []
        routes: list[str] = []
        for event in record.events:
            if event.kind == "select" and event.selected:
                winners.extend(event.selected)
            elif event.kind == "threshold" and event.reason:
                thresholds.append(event.reason)
            elif event.kind == "route" and event.selected:
                routes.extend(event.selected)
        return {
            "impulse_id": record.header.get("impulse_id"),
            "tick_id": record.header.get("tick_id"),
            "channel": record.header.get("channel"),
            "outcome": record.header.get("outcome"),
            "winners": winners[:6],
            "thresholds": thresholds[:4],
            "routes": routes[:4],
            "event_count": len(record.events),
        }

    def _commit(self, record: ImpulseRecord) -> None:
        self._impulses.append(record)
        if self._store_dir is None:
            return
        trace_dir = self._store_dir / "nervous"
        trace_dir.mkdir(parents=True, exist_ok=True)
        trace_path = trace_dir / "impulse_trace.jsonl"
        line = json.dumps(record.to_dict(debug_level=self.level), ensure_ascii=False, separators=(",", ":"))
        with trace_path.open("a", encoding="utf-8") as handle:
            handle.write(line + "\n")
        self._rotate(trace_path)
        try:
            from casa.field_bus.bus import publish
            from casa.field_bus.events import ImpulseSummaryEvent

            publish(
                ImpulseSummaryEvent(
                    store_id=str(self._store_dir.name),
                    tick_id=int(record.header.get("tick_id") or 0),
                    impulse_id=str(record.header.get("impulse_id") or ""),
                    channel=str(record.header.get("channel") or ""),
                    outcome=str(record.header.get("outcome") or ""),
                    summary=dict(record.summary),
                )
            )
        except ImportError:
            pass

    @staticmethod
    def _rotate(trace_path: Path) -> None:
        if _RING_MAX <= 0 or not trace_path.is_file():
            return
        try:
            lines = trace_path.read_text(encoding="utf-8").splitlines()
        except OSError:
            return
        if len(lines) <= _RING_MAX:
            return
        trimmed = lines[-_RING_MAX:]
        trace_path.write_text("\n".join(trimmed) + "\n", encoding="utf-8")


_GLOBAL = ImpulseRecorder()


def impulse_recorder(*, level: DebugLevel | None = None) -> ImpulseRecorder:
    if level is not None:
        return ImpulseRecorder(level=level)
    resolved = resolve_debug_level()
    _GLOBAL.level = resolved
    return _GLOBAL


def read_impulse_trace(
    store_dir: Path,
    *,
    impulse_id: str | None = None,
    tick_id: int | None = None,
    channel: str | None = None,
    limit: int = 50,
) -> list[dict[str, Any]]:
    path = store_dir.resolve() / "nervous" / "impulse_trace.jsonl"
    if not path.is_file():
        return []
    rows: list[dict[str, Any]] = []
    for line in path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line:
            continue
        try:
            doc = json.loads(line)
        except json.JSONDecodeError:
            continue
        if impulse_id and doc.get("impulse_id") != impulse_id:
            continue
        if tick_id is not None and int(doc.get("tick_id") or -1) != tick_id:
            continue
        if channel and doc.get("channel") != channel:
            continue
        rows.append(doc)
    return rows[-limit:]
