#!/usr/bin/env python3
"""Concrete block realizers — Strategy per bind block family."""

from __future__ import annotations

import re
from typing import Any

from casa.prisms.tick.articulation_realize import _extract_grammar_atom
from casa.prisms.tick.discourse.model import ClauseSketch, DiscourseContext
from casa.prisms.tick.discourse.realizers.base import BlockRealizerRegistry
from casa.prisms.tick.discourse.render import (
    clause_from_pieces,
    clause_from_slot_phrase,
    closing_for_query,
    partner_turn_is_brief,
)
from casa.prisms.tick.discourse.slots import BlockSlots
from casa.prisms.tick.discourse.wm import WmBlockRealizer

_MORPH_ROLE_ORDER = ("prefix", "stem", "root", "suffix", "ending")
_NARRATIVE_DIALOG = (
    "ru.dialog.self",
    "ru.dialog.capabilities",
    "ru.dialog.affect",
    "ru.dialog.explain",
    "ru.dialog.clarify.",
    "ru.dialog.honest.",
)
# Content-narrative families whose verbatim paste must be relevance-gated (routed by
# hint or token overlap). Honest/clarify blocks are graceful "I don't know / let me
# clarify" responses and are intentionally NOT gated.
_GATED_NARRATIVE = (
    "ru.dialog.self",
    "ru.dialog.capabilities",
    "ru.dialog.affect",
    "ru.dialog.explain",
)
_BRIEF_DIALOG_PREFIXES = (
    "ru.dialog.greeting",
    "ru.dialog.thanks",
    "ru.dialog.farewell",
)


class MetaSkipRealizer:
    def matches(self, block: dict[str, Any]) -> bool:
        return str(block.get("concept_id") or "").startswith("ru.meta.discourse.")

    def realize(self, block: dict[str, Any], ctx: DiscourseContext) -> list[ClauseSketch]:
        return []


class PropBlockRealizer:
    def matches(self, block: dict[str, Any]) -> bool:
        return str(block.get("concept_id") or "").startswith("ru.prop.")

    def realize(self, block: dict[str, Any], ctx: DiscourseContext) -> list[ClauseSketch]:
        cid = str(block.get("concept_id") or "")
        slots = BlockSlots.read(block)
        close = closing_for_query(ctx.query)
        out: list[ClauseSketch] = []

        if cid.startswith("ru.prop.topic.") and slots.get("clause_for"):
            for key, linker_key in (
                ("clause_for", "linker_for"),
                ("clause_against", "linker_against"),
                ("clause_stance", "linker_stance"),
            ):
                body = slots.get(key)
                if not body:
                    continue
                linker = slots.get(linker_key) or ""
                phrase = f"{linker} {body}" if linker and not out else str(body)
                c = clause_from_slot_phrase(phrase, closing=close)
                if c:
                    if linker and out:
                        c.linker = linker
                    out.append(c)
            return out

        primary = slots.get("clause_1")
        if primary:
            c = clause_from_slot_phrase(str(primary), closing=close)
            if c:
                out.append(c)
        out.extend(BlockSlots.extra_clauses(slots))
        return out


class PassageBlockRealizer:
    def matches(self, block: dict[str, Any]) -> bool:
        return str(block.get("concept_id") or "").startswith("passage.sent.")

    def realize(self, block: dict[str, Any], ctx: DiscourseContext) -> list[ClauseSketch]:
        c = self._clause(block, ctx)
        return [c] if c else []

    @staticmethod
    def _activated_lemmas(blocks: list[dict[str, Any]]) -> set[str]:
        out: set[str] = set()
        for b in blocks:
            cid = str(b.get("concept_id") or "")
            if cid.startswith(("lang.word.", "passage.surface.")):
                out.add(cid.rsplit(".", 1)[-1].lower())
        return out

    def _clause(self, block: dict[str, Any], ctx: DiscourseContext) -> ClauseSketch | None:
        from casa.prisms.tick.discourse.policy import BlockDiscoursePolicy
        from casa.prisms.tick.passage import _RU_STOP

        text = str(block.get("text") or "").strip()
        if not text:
            return None
        score = int(block.get("score") or 0)
        if ctx.query_intent == "rewrite" and BlockDiscoursePolicy._is_formal_passage_sentence(text):
            return None
        if score >= 28:
            return ClauseSketch([text.rstrip(".!?")], closing=".")
        activated = self._activated_lemmas(ctx.blocks)
        tokens = re.findall(r"«[^»]+»|[\w\u0400-\u04FF]+", text, flags=re.UNICODE)
        picked: list[str] = []
        for raw in tokens:
            if raw.startswith("«"):
                picked.append(raw)
                continue
            low = raw.lower()
            if low in activated or low in ctx.tokens:
                picked.append(raw)
            elif len(low) > 4 and low not in _RU_STOP:
                picked.append(raw)
            if len(picked) >= 16:
                break
        if len(picked) < 3:
            picked = [
                raw
                for raw in tokens
                if raw.startswith("«") or (len(raw) > 2 and raw.lower() not in _RU_STOP)
            ][:14]
        if not picked:
            return None
        picked_text = " ".join(picked).lower()
        for anchor in re.findall(
            r"\d{1,2}:\d{2}|\d{1,2}\s+(?:января|февраля|марта|апреля|мая|июня|июля|августа|сентября|октября|ноября|декабря)|№\s*\d+",
            text,
            flags=re.IGNORECASE,
        ):
            if anchor.lower() not in picked_text:
                picked.append(anchor.replace(" ", ""))
        content_tokens = [
            raw
            for raw in tokens
            if not raw.startswith("«") and raw.lower() not in _RU_STOP and len(raw) > 1
        ]
        if content_tokens and len(picked) < max(4, len(content_tokens) * 2 // 3):
            return ClauseSketch([text.rstrip(".!?")], closing=".")
        return ClauseSketch(picked, closing=".")


class DialogBlockRealizer:
    def matches(self, block: dict[str, Any]) -> bool:
        return str(block.get("concept_id") or "").startswith("ru.dialog.")

    def realize(self, block: dict[str, Any], ctx: DiscourseContext) -> list[ClauseSketch]:
        return self._dialog_clauses(block, ctx, allow_tail=True)

    @staticmethod
    def narrative_clauses(block: dict[str, Any], query: str) -> list[ClauseSketch]:
        cid = str(block.get("concept_id") or "")
        if not any(cid.startswith(p) for p in _NARRATIVE_DIALOG):
            return []
        slots = BlockSlots.read(block)
        close = closing_for_query(query)
        out: list[ClauseSketch] = []
        primary = slots.get("clause_1") or slots.get("sentence_1")
        if primary:
            c = clause_from_slot_phrase(str(primary), closing=close)
            if c:
                out.append(c)
        out.extend(BlockSlots.extra_clauses(slots))
        return out

    @staticmethod
    def _narrative_relevant(
        cid: str, clauses: list[ClauseSketch], ctx: DiscourseContext
    ) -> bool:
        """Narrative dialog paste is on-topic: routed by hint, self-cue, or token overlap."""
        for h in ctx.concept_hints or []:
            if cid == h or cid.startswith(f"{h}.") or str(h).startswith(cid):
                return True
        if cid.startswith("ru.dialog.self"):
            from casa.domain.dialogue_bind.partner_scoring import query_implies_self

            if query_implies_self(ctx.query):
                return True
        qtokens = {t for t in (ctx.tokens or set()) if len(t) > 3}
        if not qtokens:
            return False
        for c in clauses:
            for piece in c.pieces:
                for w in re.findall(r"\w+", str(piece).lower(), flags=re.UNICODE):
                    if len(w) > 3 and w in qtokens:
                        return True
        return False

    def _dialog_clauses(
        self,
        block: dict[str, Any],
        ctx: DiscourseContext,
        *,
        allow_tail: bool = True,
    ) -> list[ClauseSketch]:
        cid = str(block.get("concept_id") or "")
        brief = partner_turn_is_brief(ctx.query) and any(cid.startswith(p) for p in _BRIEF_DIALOG_PREFIXES)
        if brief:
            allow_tail = False

        if any(cid.startswith(p) for p in _NARRATIVE_DIALOG):
            narrative = self.narrative_clauses(block, ctx.query)
            if narrative:
                # Content-narrative blocks paste verbatim only when routed (hint) or they
                # share a content token with the turn — otherwise stay silent rather than
                # paste off-topic. Honest/clarify blocks always pass (graceful fallback).
                if cid.startswith(_GATED_NARRATIVE) and not self._narrative_relevant(
                    cid, narrative, ctx
                ):
                    return []
                return narrative

        slots = BlockSlots.read(block)
        close = closing_for_query(ctx.query)
        stimulus = str(slots.get("stimulus") or slots.get("word") or "").strip().lower()
        response = str(slots.get("response") or "").strip().lower()
        surface = str(slots.get("surface") or "").strip().lower()
        out: list[ClauseSketch] = []

        primary = slots.get("clause_1") or slots.get("sentence_1")
        if primary and not brief:
            c = clause_from_slot_phrase(str(primary), closing=close)
            if c:
                out.append(c)

        if not out:
            if stimulus and response and stimulus in ctx.tokens:
                c = clause_from_slot_phrase(response, closing=close)
                if c:
                    out.append(c)
            elif surface and surface in ctx.tokens:
                c = clause_from_slot_phrase(surface, closing=close)
                if c:
                    out.append(c)
            elif surface and not stimulus and not brief:
                c = clause_from_slot_phrase(surface, closing=close)
                if c:
                    out.append(c)
            elif response and not stimulus and not brief:
                c = clause_from_slot_phrase(response, closing=close)
                if c:
                    out.append(c)

        if allow_tail:
            out.extend(BlockSlots.extra_clauses(slots))
        return out


class GrammarBlockRealizer:
    def matches(self, block: dict[str, Any]) -> bool:
        return str(block.get("concept_id") or "").startswith("ru.grammar.")

    def realize(self, block: dict[str, Any], ctx: DiscourseContext) -> list[ClauseSketch]:
        text = str(block.get("text") or "")
        atom = _extract_grammar_atom(text)
        if not atom:
            return []
        out: list[ClauseSketch] = []
        head = atom.headline.strip()
        if head:
            c = clause_from_pieces(head.split())
            if c:
                out.append(c)
        if atom.detail:
            c = clause_from_pieces(atom.detail.split())
            if c:
                c.linker = "При этом"
                out.append(c)
        quoted = [q.strip() for q in re.findall(r"«([^»]{1,120})»", text) if q.strip()]
        for q in quoted:
            c = clause_from_pieces(q.rstrip(".!?").split(), closing=".")
            if c:
                c.linker = "Например" if out else ""
                out.append(c)
        return out


class JournalBlockRealizer:
    def matches(self, block: dict[str, Any]) -> bool:
        return block.get("source") in ("journal", "dialogue")

    def realize(self, block: dict[str, Any], ctx: DiscourseContext) -> list[ClauseSketch]:
        text = str(block.get("text") or "").strip()
        if not text or len(text) < 8:
            return []
        slots = BlockSlots.read(block)
        slot_clauses = BlockSlots.extra_clauses(slots, skip_primary=False)
        if slot_clauses:
            return slot_clauses
        sents = [s.strip() for s in re.split(r"(?<=[.!?])\s+", text) if s.strip()]
        out: list[ClauseSketch] = []
        for sent in sents:
            words = sent.rstrip(".!?").split()
            if len(words) < 2:
                continue
            c = clause_from_pieces(words, closing=".")
            if c:
                out.append(c)
        return out


class LexemeBlockRealizer:
    def matches(self, block: dict[str, Any]) -> bool:
        cid = str(block.get("concept_id") or "")
        return cid.startswith("lang.word.") or cid.startswith("passage.surface.")

    def realize(self, block: dict[str, Any], ctx: DiscourseContext) -> list[ClauseSketch]:
        c = self._lexeme_clause(block, ctx)
        return [c] if c else []

    @staticmethod
    def gloss_clause(block: dict[str, Any]) -> ClauseSketch | None:
        text = str(block.get("text") or "")
        m = re.search(r"«([^»]{1,60})»\s*[—\-]\s*([^.;]{4,120})", text)
        if not m:
            return None
        surface = m.group(1).strip()
        gloss = m.group(2).strip().rstrip(".")
        return clause_from_pieces([f"«{surface}» — {gloss}"])

    def _lexeme_clause(self, block: dict[str, Any], ctx: DiscourseContext) -> ClauseSketch | None:
        cid = str(block.get("concept_id") or "")
        if not cid.startswith(("lang.word.", "passage.surface.")):
            return None
        slots = BlockSlots.read(block)
        surface = str(slots.get("word") or cid.rsplit(".", 1)[-1]).strip().lower()
        if not surface or surface in ctx.tokens:
            return None
        return clause_from_pieces(surface.split())


class MorphBlockRealizer:
    def matches(self, block: dict[str, Any]) -> bool:
        return str(block.get("concept_id") or "").startswith("lang.meta.morph.")

    def realize(self, block: dict[str, Any], ctx: DiscourseContext) -> list[ClauseSketch]:
        c = self.morph_clause(ctx.blocks)
        return [c] if c else []

    @staticmethod
    def morph_clause(blocks: list[dict[str, Any]]) -> ClauseSketch | None:
        roles: dict[str, str] = {}
        for b in blocks:
            cid = str(b.get("concept_id") or "")
            if not cid.startswith("lang.meta.morph."):
                continue
            role = cid.rsplit(".", 1)[-1]
            slots = BlockSlots.read(b)
            surface = str(slots.get("surface") or slots.get("word") or "").strip()
            if surface:
                roles[role] = surface
        word = "".join(roles.get(r, "") for r in _MORPH_ROLE_ORDER)
        if not word:
            return None
        return clause_from_pieces([word])


def default_block_realizer_registry() -> BlockRealizerRegistry:
    return BlockRealizerRegistry(
        [
            MetaSkipRealizer(),
            PropBlockRealizer(),
            PassageBlockRealizer(),
            DialogBlockRealizer(),
            GrammarBlockRealizer(),
            JournalBlockRealizer(),
            LexemeBlockRealizer(),
            MorphBlockRealizer(),
            WmBlockRealizer(),
        ]
    )
