#!/usr/bin/env python3
"""Concrete block realizers — render bind winners, no slot competition."""

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
_KB_GLOSS_RE = re.compile(r"«[^»]+»\s*[—\-]")
_JOURNAL_BOOTSTRAP_MARKERS = (
    "это мой журнал",
    "я — нейманн",
    "я - нейманн",
)
_FIELD_MATERIAL_STOP = frozenset(
    "партнёр недавно текущий фокус диалога последние намерения как что это ты я мы он она они".split()
)



def _is_journal_bootstrap(text: str) -> bool:
    tl = str(text or "").lower()
    return any(m in tl for m in _JOURNAL_BOOTSTRAP_MARKERS)


def _situation_clauses(slots: dict[str, str], close: str) -> list[ClauseSketch]:
    """L3 pieces for situation hubs — not full-sentence script slots (ADR-0081)."""
    situation = str(slots.get("situation") or "").strip()
    if not situation:
        return []
    pieces = [
        str(slots.get(k) or "").strip()
        for k in (
            "modifier",
            "stance",
            "referent",
            "role",
            "surface",
            "predicate_lemma",
            "object_lemma",
            "limit_kind",
        )
        if str(slots.get(k) or "").strip()
    ]
    if len(pieces) < 2:
        return []
    return [clause_from_pieces(pieces, closing=close)]


def _minimal_formula_active(block: dict[str, Any], ctx: DiscourseContext) -> bool:
    slots = BlockSlots.read(block)
    stimulus = str(slots.get("stimulus") or slots.get("word") or "").strip().lower()
    response = str(slots.get("response") or slots.get("response_informal") or "").strip()
    return bool(stimulus and response and stimulus in ctx.tokens)


def _episode_clauses_from_ctx(ctx: DiscourseContext) -> list[ClauseSketch]:
    """Field/journal/subject evidence — not canned ru.dialog clause_* scripts (ADR-0081)."""
    from casa.domain.dialogue_bind.partner_scoring import partner_quote_from_block

    close = closing_for_query(ctx.query)
    out: list[ClauseSketch] = []
    for block in ctx.blocks:
        cid = str(block.get("concept_id") or "")
        src = block.get("source")
        text = str(block.get("text") or "").strip()
        if len(text) < 8:
            continue
        if src == "journal":
            if _is_journal_bootstrap(text):
                continue
        elif not cid.startswith("subject.dialog."):
            continue
        if cid.startswith("subject.dialog."):
            first = partner_quote_from_block(block)
        else:
            first = re.split(r"(?<=[.!?])\s+", text, maxsplit=1)[0].strip()
        first = first.strip(" .")
        while first.startswith("«") and first.endswith("»"):
            first = first[1:-1].strip(" .")
        if "?" in first:
            continue
        if len(first) < 8:
            continue
        c = clause_from_slot_phrase(first.rstrip(), closing=close)
        if c:
            out.append(c)
        if len(out) >= 2:
            break
    return out


def _materialized_phrase(block: dict[str, Any], slots: dict[str, str]) -> str:
    phrase = str(slots.get("phrase") or "").strip()
    if phrase:
        return phrase
    cid = str(block.get("concept_id") or "")
    if block.get("bind_hub") and ("@" in cid or slots.get("slot_key")):
        return str(block.get("text") or "").strip()
    return ""


def _field_material_active(ctx: DiscourseContext) -> bool:
    """Live dialogue material is present; ru.dialog scripts must not overwrite it."""
    for row in ctx.blocks:
        cid = str(row.get("concept_id") or "")
        slots = row.get("slots") if isinstance(row.get("slots"), dict) else {}
        if cid in ("dialog.context.referent", "dialog.context.focus_recent"):
            if str(slots.get("referent_prop") or "").strip():
                return True
        if cid not in (
            "subject.dialog.partner_recent",
            "dialog.context.focus_recent",
            "dialog.context.referent",
        ):
            continue
        text = " ".join(
            p
            for p in (
                str(row.get("text") or ""),
                " ".join(str(v) for v in slots.values() if v),
            )
            if p
        )
        for raw in re.findall(r"[\w\u0400-\u04FF]+", text, flags=re.UNICODE):
            low = raw.lower()
            if len(low) >= 4 and low not in _FIELD_MATERIAL_STOP:
                return True
    return False


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
        from casa.prisms.memory.concept_layer import discourse_concept_id

        return discourse_concept_id(block).startswith("ru.dialog.")

    def realize(self, block: dict[str, Any], ctx: DiscourseContext) -> list[ClauseSketch]:
        return self._dialog_clauses(block, ctx)

    @staticmethod
    def narrative_clauses(
        block: dict[str, Any],
        query: str,
        *,
        ctx: DiscourseContext | None = None,
    ) -> list[ClauseSketch]:
        """Backward compat — bind already picked phrase; realize as-is."""
        if ctx is not None:
            return DialogBlockRealizer().realize(block, ctx)
        slots = BlockSlots.read(block)
        phrase = _materialized_phrase(block, slots)
        if not phrase:
            return []
        close = closing_for_query(query)
        c = clause_from_slot_phrase(str(phrase), closing=close)
        return [c] if c else []

    def _dialog_clauses(
        self,
        block: dict[str, Any],
        ctx: DiscourseContext,
    ) -> list[ClauseSketch]:
        slots = BlockSlots.read(block)
        brief = partner_turn_is_brief(ctx.query)
        close = closing_for_query(ctx.query)
        body_text = str(block.get("text") or "")
        if (
            _KB_GLOSS_RE.search(body_text)
            and not _materialized_phrase(block, slots)
            and not str(slots.get("situation") or "").strip()
        ):
            stimulus = str(slots.get("stimulus") or slots.get("word") or slots.get("surface") or "").strip().lower()
            if not stimulus or stimulus not in ctx.tokens:
                return []

        live_field_material = _field_material_active(ctx)

        phrase = _materialized_phrase(block, slots)
        if phrase and not live_field_material:
            c = clause_from_slot_phrase(phrase, closing=close)
            return [c] if c else []

        stimulus = str(slots.get("stimulus") or slots.get("word") or "").strip().lower()
        response = str(slots.get("response") or slots.get("response_informal") or "").strip().lower()
        surface = str(slots.get("surface") or "").strip().lower()
        out: list[ClauseSketch] = []

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

        if not out and not live_field_material:
            from casa.prisms.tick.discourse.meta_glue_guard import should_suppress_dialog_script_efferent

            if not should_suppress_dialog_script_efferent(
                block, ctx.blocks, query=ctx.query, concept_hints=ctx.concept_hints
            ):
                out.extend(_situation_clauses(slots, close))

        from casa.prisms.tick.discourse.meta_glue_guard import should_suppress_dialog_script_efferent

        if out and should_suppress_dialog_script_efferent(
            block, ctx.blocks, query=ctx.query, concept_hints=ctx.concept_hints
        ):
            episode = _episode_clauses_from_ctx(ctx)
            return episode if episode else []

        if not out:
            out.extend(_episode_clauses_from_ctx(ctx))

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
