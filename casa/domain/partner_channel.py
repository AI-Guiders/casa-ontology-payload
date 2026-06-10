#!/usr/bin/env python3
"""Re-exports from casa.body.text_tract."""

from __future__ import annotations

from casa.body import text_tract as _t

AFFERENT_FUNCTION = _t.AFFERENT_FUNCTION
DIRECTION_AFFERENT = _t.DIRECTION_AFFERENT
DIRECTION_EFFERENT = _t.DIRECTION_EFFERENT
EFFERENT_FUNCTION = _t.EFFERENT_FUNCTION
PARTNER_TEXT_TRACT_ID = _t.PARTNER_TEXT_TRACT_ID
TEXT_WIRE_CONSOLE = _t.TEXT_WIRE_CONSOLE
TRACT_KIND_SYMBOLIC = _t.TRACT_KIND_SYMBOLIC
complete_efferent = _t.complete_efferent
complete_partner_cue = _t.complete_partner_cue
cue_path = _t.cue_path
enqueue_afferent = _t.enqueue_afferent
enqueue_partner_cue = _t.enqueue_partner_cue
extract_dialogue_reply = _t.extract_dialogue_reply
fail_afferent_cue = _t.fail_afferent_cue
fail_partner_cue = _t.fail_partner_cue
poll_pending_afferent = _t.poll_pending_afferent
pulse_path = _t.pulse_path
read_afferent_cue = _t.read_afferent_cue
read_partner_cue = _t.read_partner_cue
read_pulse = _t.read_pulse
reactor_alive = _t.reactor_alive
text_dir = _t.text_dir
wait_for_efferent = _t.wait_for_efferent
wait_for_partner_reply = _t.wait_for_partner_reply
write_pulse = _t.write_pulse

__all__ = [
    "AFFERENT_FUNCTION",
    "DIRECTION_AFFERENT",
    "DIRECTION_EFFERENT",
    "EFFERENT_FUNCTION",
    "PARTNER_TEXT_TRACT_ID",
    "TEXT_WIRE_CONSOLE",
    "TRACT_KIND_SYMBOLIC",
    "complete_efferent",
    "complete_partner_cue",
    "cue_path",
    "enqueue_afferent",
    "enqueue_partner_cue",
    "extract_dialogue_reply",
    "fail_afferent_cue",
    "fail_partner_cue",
    "poll_pending_afferent",
    "pulse_path",
    "read_afferent_cue",
    "read_partner_cue",
    "read_pulse",
    "reactor_alive",
    "text_dir",
    "wait_for_efferent",
    "wait_for_partner_reply",
    "write_pulse",
]
