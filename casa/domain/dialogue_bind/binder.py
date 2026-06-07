"""Subject dialogue binder — gather orchestrator."""

from __future__ import annotations

import re
from pathlib import Path
from typing import Any

from casa.domain.dialogue_bind.collectors.cen_field import collect_cen_blocks, collect_field_blocks
from casa.domain.dialogue_bind.collectors.journal import collect_journal_blocks
from casa.domain.dialogue_bind.collectors.kb import collect_kb_blocks
from casa.domain.dialogue_bind.collectors.passage import collect_passage_blocks
from casa.domain.dialogue_bind.collectors.wm import collect_wm_blocks
from casa.domain.dialogue_bind.dialogue import infer_stance
from casa.domain.dialogue_bind.field import looks_like_field_recall
from casa.domain.dialogue_bind.model import SubjectDialogueContext
from casa.domain.subject_mode import subject_display_name
from casa.prisms.control.fpn_state import WorkingMemory
from casa.prisms.control.sn_cen_runtime import TaskEmit
from casa.prisms.tick.articulation_realize import build_plan


def _dedupe_blocks(blocks: list[dict[str, Any]]) -> list[dict[str, Any]]:
    deduped: list[dict[str, Any]] = []
    seen_cids: set[str] = set()
    seen_texts: set[tuple[str, str]] = set()
    for row in blocks:
        cid = str(row.get("concept_id") or "")
        if cid and cid in seen_cids:
            continue
        if cid:
            seen_cids.add(cid)
        source = str(row.get("source") or "")
        text_key = re.sub(r"\s+", " ", str(row.get("text") or "").strip().lower())
        if source in {"journal", "dialogue"} and text_key:
            key = (source, text_key)
            if key in seen_texts:
                continue
            seen_texts.add(key)
        deduped.append(row)
    return deduped


class SubjectDialogueBinder:
    """Collect utterance atoms: semantic read → KB, CEN, journal, field."""

    def gather(
        self,
        user_query: str,
        task: TaskEmit | None,
        state: dict,
        wm: WorkingMemory,
        store_dir: Path | None,
        *,
        bundle: dict[str, Any] | None = None,
        compose_mode: str | None = None,
    ) -> SubjectDialogueContext:
        from casa.domain.capability_router import apply_capability_to_wm
        from casa.prisms.memory.intent import is_agent_tract, resolve_compose_profile
        from casa.prisms.shared.store_bundles import load_store_bundles
        from casa.prisms.tick.passage import proposition_bind_blocks
        from casa.prisms.tick.routing import route_kb_read

        q = (user_query or "").strip()
        name = subject_display_name(state, store_dir)
        blocks: list[dict[str, Any]] = []
        sources: list[str] = []

        merged_bundle = bundle
        if merged_bundle is None and store_dir is not None:
            merged_bundle = load_store_bundles(store_dir)

        query_read = route_kb_read(q, merged_bundle, store_dir=store_dir, state=state)
        intent = compose_mode if compose_mode else query_read.intent
        if compose_mode is None and looks_like_field_recall(q):
            intent = "explain"

        resolved_skill = (
            apply_capability_to_wm(
                state, wm, q, locale=(query_read.locales[0] if query_read.locales else "ru")
            )
            or ""
        )

        passage_blocks, passage_sources, pt = collect_passage_blocks(
            q,
            intent=intent,
            compose_mode=compose_mode,
            merged_bundle=merged_bundle,
        )
        blocks.extend(passage_blocks)
        sources.extend(passage_sources)

        meaning_blocks = proposition_bind_blocks(
            q, intent=intent, bundle=merged_bundle, store_dir=store_dir
        )
        if meaning_blocks:
            blocks.extend(meaning_blocks)
            sources.append("meaning")

        kb_blocks, kb_sources = collect_kb_blocks(query_read, intent, pt)
        blocks.extend(kb_blocks)
        sources.extend(kb_sources)

        cen_blocks, cen_sources = collect_cen_blocks(task, intent)
        blocks.extend(cen_blocks)
        sources.extend(cen_sources)

        if store_dir is not None:
            store_dir = store_dir.resolve()
            journal_blocks, journal_sources = collect_journal_blocks(
                store_dir,
                q,
                intent=intent,
                pt=pt,
                kb_hits=query_read.kb_hits,
            )
            blocks.extend(journal_blocks)
            sources.extend(journal_sources)

            from casa.domain.dialogue_bind.dialogue import dialogue_continuity_blocks

            dialogue_blocks = dialogue_continuity_blocks(store_dir, q)
            if dialogue_blocks:
                blocks.extend(dialogue_blocks)
                sources.append("dialogue")

        field_blocks, field_sources = collect_field_blocks(state, wm, task, intent)
        blocks.extend(field_blocks)
        sources.extend(field_sources)

        blocks[:] = _dedupe_blocks(blocks)

        from casa.domain.dialogue_bind.scoring import reweight_blocks_for_reply

        reweight_blocks_for_reply(
            blocks,
            q,
            kb_hits=query_read.kb_hits,
            intent=intent,
            concept_hints=query_read.concept_hints,
            passage_lemmas=pt,
            state=state,
        )

        wm_bind_rep: dict[str, Any] | None = None
        wm_edge_scores: dict[str, float] = {}
        if store_dir is not None:
            wm_extra, wm_sources, wm_bind_rep, wm_edge_scores = collect_wm_blocks(
                store_dir, state, wm, q, blocks, query_read
            )
            blocks.extend(wm_extra)
            sources.extend(wm_sources)

        stance = infer_stance(blocks, task=task, intent=intent)

        agent_tract_profile = None
        if is_agent_tract(intent):
            agent_tract_profile = resolve_compose_profile(state, intent)

        return SubjectDialogueContext(
            display_name=name,
            field_version=int(state.get("field_version") or 0),
            wm=wm,
            blocks=blocks,
            source_tags=list(dict.fromkeys(sources)),
            stance=stance,
            query_intent=intent,
            resolved_skill=resolved_skill,
            query_locales=query_read.locales,
            concept_hints=query_read.concept_hints,
            wm_bind=wm_bind_rep,
            wm_edge_scores=wm_edge_scores,
            agent_tract_profile=agent_tract_profile,
        )


_default_binder = SubjectDialogueBinder()


def gather_subject_dialogue_blocks(
    user_query: str,
    task: TaskEmit | None,
    state: dict,
    wm: WorkingMemory,
    store_dir: Path | None,
    *,
    bundle: dict[str, Any] | None = None,
    compose_mode: str | None = None,
) -> SubjectDialogueContext:
    return _default_binder.gather(
        user_query,
        task,
        state,
        wm,
        store_dir,
        bundle=bundle,
        compose_mode=compose_mode,
    )


def build_subject_plan(
    user_query: str,
    ctx: SubjectDialogueContext,
) -> Any:
    """UtterancePlan from bound blocks + query (extends articulation_realize.build_plan)."""
    return build_plan(user_query, ctx.blocks)
