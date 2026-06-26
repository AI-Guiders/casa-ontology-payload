#!/usr/bin/env python3
"""Agent wire JSONL protocol — no life reactor required."""

from __future__ import annotations

import tempfile
import time
import unittest
from pathlib import Path

from casa.body.agent_wire import (
    append_agent_inbox,
    bridge_alive,
    drain_pending_outbox,
    enqueue_agent_outbox,
    find_inbox_reply,
    mark_outbox_done,
    outbox_in_flight,
    reclaim_stale_outbox,
    try_claim_bridge,
    wait_inbox_reply,
    write_bridge_pulse,
)


class AgentWireProtocolTest(unittest.TestCase):
    def test_outbox_inbox_roundtrip(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            store = Path(tmp)
            req = enqueue_agent_outbox(store, "Привет")
            pending = drain_pending_outbox(store)
            self.assertEqual(len(pending), 1)
            self.assertEqual(pending[0]["id"], req)
            append_agent_inbox(
                store,
                direction="reply",
                text="Привет.",
                request_id=req,
            )
            mark_outbox_done(store, req)
            row = wait_inbox_reply(store, req, timeout_s=0.5, poll_s=0.05)
            self.assertEqual(row["text"], "Привет.")
            self.assertEqual(find_inbox_reply(store, req)["direction"], "reply")

    def test_single_flight_outbox(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            store = Path(tmp)
            a = enqueue_agent_outbox(store, "one")
            b = enqueue_agent_outbox(store, "two")
            first = drain_pending_outbox(store)
            self.assertEqual(len(first), 1)
            self.assertEqual(outbox_in_flight(store)["id"], first[0]["id"])
            second = drain_pending_outbox(store)
            self.assertEqual(second, [])
            mark_outbox_done(store, str(first[0]["id"]))
            third = drain_pending_outbox(store)
            self.assertEqual(len(third), 1)
            self.assertIn(third[0]["id"], {a, b})

    def test_reclaim_stale_processing(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            store = Path(tmp)
            from casa.body.agent_wire import _rewrite_jsonl, outbox_path

            req = "abc123"
            _rewrite_jsonl(
                outbox_path(store),
                [
                    {
                        "id": req,
                        "text": "stuck",
                        "status": "processing",
                        "claimed_at": "2000-01-01T00:00:00Z",
                    }
                ],
            )
            reclaimed = reclaim_stale_outbox(store, stale_s=1.0)
            self.assertEqual(reclaimed, [req])
            self.assertIsNone(outbox_in_flight(store))

    def test_bridge_pulse_waiting_phase(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            store = Path(tmp)
            self.assertTrue(try_claim_bridge(store))
            write_bridge_pulse(store, extra={"phase": "waiting_efferent"})
            time.sleep(0.05)
            self.assertTrue(bridge_alive(store, max_age_s=0.01))


if __name__ == "__main__":
    unittest.main()