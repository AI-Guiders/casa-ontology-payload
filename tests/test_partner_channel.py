"""Partner channel IPC — enqueue / complete / wait."""

from __future__ import annotations

from pathlib import Path

from casa.body.text_tract import reactor_alive, write_pulse
from casa.domain.partner_channel import (
    complete_partner_cue,
    cue_path,
    enqueue_partner_cue,
    read_partner_cue,
    wait_for_partner_reply,
)


def test_partner_cue_roundtrip(tmp_path: Path) -> None:
    store = tmp_path / "agent"
    store.mkdir()
    cue_id = enqueue_partner_cue(store, "Привет?")
    cue = read_partner_cue(store)
    assert cue is not None
    assert cue["id"] == cue_id
    assert cue["status"] == "pending"
    assert cue["text"] == "Привет?"

    complete_partner_cue(store, cue_id, reply_text="Здравствуй.", tick=7)
    done = wait_for_partner_reply(store, cue_id, timeout_s=1.0, poll_s=0.01)
    assert done["reply_text"] == "Здравствуй."
    assert done["tick"] == 7
    assert cue_path(store).is_file()


def test_reactor_alive_while_partner_cue_pending(tmp_path: Path) -> None:
    store = tmp_path / "agent"
    store.mkdir()
    write_pulse(store, macro_tick=3, holder="test")
    assert reactor_alive(store, max_age_s=0.001) is False
    enqueue_partner_cue(store, "2+2")
    assert reactor_alive(store, max_age_s=0.001) is True


def test_reactor_alive_while_boot_loading(tmp_path: Path) -> None:
    store = tmp_path / "agent"
    store.mkdir()
    write_pulse(store, macro_tick=0, sn_mode="boot", extra={"phase": "loading"})
    assert reactor_alive(store, max_age_s=0.001) is True


def test_wait_on_life_tick_callback_signature(tmp_path: Path) -> None:
    from casa.cli.life_tick_bar import LifeTickBar

    store = tmp_path / "agent"
    store.mkdir()
    write_pulse(store, macro_tick=1)
    bar = LifeTickBar(store, screen_row=1)
    seen: list[int] = []

    def _on(t: int, pulse: dict) -> None:
        seen.append(t)
        bar.bump_life_tick(t, pulse)

    cue_id = enqueue_partner_cue(store, "x")
    complete_partner_cue(store, cue_id, reply_text="y", tick=2)
    write_pulse(store, macro_tick=2)
    wait_for_partner_reply(store, cue_id, timeout_s=1.0, poll_s=0.01, on_life_tick=_on)
    assert seen
