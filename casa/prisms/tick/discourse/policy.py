#!/usr/bin/env python3
"""Which bind blocks may enter discourse for a given query intent."""

from __future__ import annotations

import re
from typing import Any

from casa.prisms.tick.discourse.model import DiscourseContext


class BlockDiscoursePolicy:
    _EXPLAIN_DIALOG_DENY = (
        "ru.dialog.greeting",
        "ru.dialog.thanks",
        "ru.dialog.farewell",
        "ru.dialog.how_are_you",
    )
    _SOCIAL_DIALOG_DENY = ("ru.dialog.explain",)

    def eligible(self, block: dict[str, Any], ctx: DiscourseContext) -> bool:
        from casa.prisms.memory.intent import is_agent_tract

        cid = str(block.get("concept_id") or "")
        query_intent = ctx.query_intent
        blocks = ctx.blocks
        query = ctx.query

        if is_agent_tract(query_intent):
            profile = ctx.agent_tract_profile or {}
            mode = str(profile.get("compose_mode") or "field")
            if block.get("source") == "wm_prism":
                return mode in ("explain", "discuss", "recall", "general", "journal", "social", "field")
            if cid.startswith("ru.prop."):
                return mode in ("discuss", "rewrite", "journal", "field")
            if cid.startswith("ru.dialog."):
                return mode in ("social", "general", "field")
            if block.get("source") == "journal":
                return mode in ("explain", "journal", "recall", "field", "discuss")
            return mode in ("field", "general", "discuss", "explain")

        if cid.startswith("subject."):
            return False
        if cid.startswith("ru.dialog."):
            return self._dialog_eligible(cid, query_intent, blocks)
        if block.get("source") == "journal":
            return self._journal_eligible(block, query, query_intent)
        if cid.startswith("ru.prop."):
            return query_intent in ("discuss", "rewrite", "journal")
        if block.get("source") == "wm_prism":
            return query_intent in ("explain", "discuss", "recall", "general", "journal", "social")
        if query_intent in ("discuss", "rewrite") and cid.startswith("passage.surface."):
            return False
        if query_intent == "rewrite" and cid.startswith("passage.sent."):
            if any(str(b.get("concept_id") or "").startswith("ru.prop.event.") for b in blocks):
                return False
            if self._is_formal_passage_sentence(str(block.get("text") or "")):
                return False
        if query_intent == "discuss" and cid.startswith("passage.sent."):
            if any(str(b.get("concept_id") or "").startswith("ru.prop.") for b in blocks):
                return False
        return True

    def _dialog_eligible(self, cid: str, query_intent: str, blocks: list[dict[str, Any]]) -> bool:
        if query_intent in ("explain", "grammar"):
            return not any(cid.startswith(p) for p in self._EXPLAIN_DIALOG_DENY)
        if query_intent == "social":
            top = self._top_dialog_cid(blocks)
            if not top:
                return True
            if any(cid.startswith(p) for p in self._SOCIAL_DIALOG_DENY):
                return False
            return self._dialog_family(cid) == self._dialog_family(top) or cid == top
        if query_intent == "rewrite":
            return cid.startswith(("ru.dialog.greeting", "ru.dialog.thanks", "ru.dialog.farewell"))
        return query_intent in ("social", "general")

    @staticmethod
    def _journal_eligible(block: dict[str, Any], query: str, query_intent: str) -> bool:
        if query_intent == "explain":
            return BlockDiscoursePolicy._journal_explain_overlap(block, query)
        if query_intent in ("grammar", "discuss", "rewrite"):
            return False
        if query_intent == "journal":
            tl = str(block.get("text") or "").lower()
            if any(
                m in tl
                for m in (
                    "это мой журнал",
                    "я — нейманн",
                    "проснулся",
                    "lattice ready",
                    "agent-self-default",
                )
            ):
                return False
            return True
        return False

    @staticmethod
    def _journal_explain_overlap(block: dict[str, Any], query: str) -> bool:
        tl = str(block.get("text") or "").lower()
        ql = (query or "").lower()
        if not tl or not ql:
            return False
        for tok in re.findall(r"[\w\u0400-\u04FF]+", ql, flags=re.UNICODE):
            if len(tok) >= 5 and tok in tl:
                return True
        return False

    @staticmethod
    def _top_dialog_cid(blocks: list[dict[str, Any]]) -> str | None:
        for b in blocks:
            cid = str(b.get("concept_id") or "")
            if cid.startswith("ru.dialog."):
                return cid
        return None

    @staticmethod
    def _dialog_family(cid: str) -> str:
        parts = cid.split(".")
        if len(parts) >= 3:
            return ".".join(parts[:3])
        return cid

    @staticmethod
    def _is_formal_passage_sentence(text: str) -> bool:
        tl = text.lower()
        return any(m in tl for m in ("уважаем", "информируем вас", "настоящим сообщаем"))
