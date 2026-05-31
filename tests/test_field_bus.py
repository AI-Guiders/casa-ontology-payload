"""FieldBus v0 smoke."""

from __future__ import annotations

from casa.field_bus import (
    ConsolidatePhaseEvent,
    FieldVersionDriftEvent,
    TrainCompleteEvent,
    drain_log,
    publish,
    subscribe,
)


def test_publish_subscribe_and_drain():
    seen: list[str] = []

    def on_drift(ev: FieldVersionDriftEvent) -> None:
        seen.append(ev.store_id)

    subscribe(FieldVersionDriftEvent, on_drift)
    publish(FieldVersionDriftEvent("store-a", 1, 1, 2, ("lexicon-ru-00",)))
    publish(TrainCompleteEvent("store-a", "lexicon-ru-00", 1, "nca/x/model.pt"))
    publish(ConsolidatePhaseEvent("store-a", "sleep", 2, shards_trained=3))

    assert seen == ["store-a"]
    log = drain_log()
    assert len(log) == 3
    assert isinstance(log[0], FieldVersionDriftEvent)
    assert log[2].phase == "sleep"
