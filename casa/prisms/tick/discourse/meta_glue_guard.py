"""Dialog script guard — situation template hubs are not field substance (ADR-0081)."""



from __future__ import annotations



from typing import Any



from casa.domain.dialogue_bind.dialog_bind_policy import _slots

from casa.domain.dialogue_bind.partner_scoring import (

    continuer_active,

    field_routed_dialog_slot,

    partner_field_overlap,

)

from casa.prisms.memory.concept_layer import discourse_concept_id

from casa.prisms.tick.discourse.slots import BlockSlots



_TEMPLATE_KEYS = ("hedge", "predicate", "scope", "limit")





def meta_glue_situation_keys(bundle: dict[str, Any] | None = None) -> frozenset[str]:

    raw = _slots("ru.meta.dialog.meta_glue", bundle).get("situation_keys") or (

        "partner_asks_opinion|partner_asks_state|defer_out_of_field"

    )

    return frozenset(p.strip() for p in str(raw).split("|") if p.strip())





def _has_minimal_act_slots(slots: dict[str, str]) -> bool:

    """stimulus+response pairs — short formula exchange, not situation script."""

    stimulus = str(slots.get("stimulus") or slots.get("word") or "").strip()

    response = str(slots.get("response") or slots.get("response_informal") or "").strip()

    return bool(stimulus and response)





def _has_clause_script_slots(slots: dict[str, str]) -> bool:

    for key in ("phrase", "clause_1", "clause_2", "clause_3"):

        if str(slots.get(key) or "").strip():

            return True

    return False





def is_situation_script_block(

    block: dict[str, Any],

    bundle: dict[str, Any] | None = None,

) -> bool:

    """ADR-0081: situation + template pieces = canned reply, not lexical compose."""

    cid = discourse_concept_id(block)

    if not cid.startswith("ru.dialog."):

        return False

    slots = BlockSlots.read(block)

    if _has_minimal_act_slots(slots) or _has_clause_script_slots(slots):

        return False

    situation = str(slots.get("situation") or "").strip()

    if not situation:

        return False

    template_count = sum(1 for key in _TEMPLATE_KEYS if str(slots.get(key) or "").strip())

    if template_count >= 2:

        return True

    if template_count == 0 and situation in meta_glue_situation_keys(bundle):

        return True

    return False





def is_meta_glue_dialog_block(

    block: dict[str, Any],

    bundle: dict[str, Any] | None = None,

) -> bool:

    return is_situation_script_block(block, bundle)





def referent_prop_from_blocks(blocks: list[dict[str, Any]]) -> str:

    for row in blocks:

        cid = str(row.get("concept_id") or "")

        slots = row.get("slots") if isinstance(row.get("slots"), dict) else {}

        if cid == "dialog.context.referent":

            ref = str(slots.get("referent_prop") or "").strip()

            if ref:

                return ref

        if cid == "dialog.context.focus_recent":

            ref = str(slots.get("referent_prop") or "").strip()

            if ref:

                return ref

    return ""





def referent_field_active(blocks: list[dict[str, Any]]) -> bool:

    return bool(referent_prop_from_blocks(blocks))





def dialogue_thread_carries(blocks: list[dict[str, Any]]) -> bool:

    """Live partner thread on field — scripts must not paste over it."""

    if referent_field_active(blocks):

        return True

    if not continuer_active(blocks):

        return False

    return any(str(row.get("concept_id") or "") == "subject.dialog.partner_recent" for row in blocks)





def _hub_family(cid: str) -> str:

    parts = cid.split(".")

    return ".".join(parts[:3]) if len(parts) >= 3 else cid





def should_suppress_dialog_script_efferent(

    block: dict[str, Any],

    blocks: list[dict[str, Any]],

    *,

    query: str = "",

    concept_hints: list[str] | None = None,

    bundle: dict[str, Any] | None = None,

) -> bool:

    """Suppress ru.dialog situation scripts unless field evidence authorizes them."""

    if not is_situation_script_block(block, bundle):

        return False

    if dialogue_thread_carries(blocks):

        return True

    cid = discourse_concept_id(block)

    if partner_field_overlap(query, block) >= 8:

        return False

    return not field_routed_dialog_slot(

        cid,

        hint_prefix=_hub_family(cid),

        concept_hints=concept_hints,

        query=query,

        block=block,

    )





def should_suppress_meta_glue_efferent(

    block: dict[str, Any],

    blocks: list[dict[str, Any]],

    *,

    bundle: dict[str, Any] | None = None,

    query: str = "",

    concept_hints: list[str] | None = None,

) -> bool:

    return should_suppress_dialog_script_efferent(

        block,

        blocks,

        query=query,

        concept_hints=concept_hints,

        bundle=bundle,

    )


