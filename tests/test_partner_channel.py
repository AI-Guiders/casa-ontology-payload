"""Partner channel IPC — enqueue / complete / wait."""

from __future__ import annotations

from pathlib import Path

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
