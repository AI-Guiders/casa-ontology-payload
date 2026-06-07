"""Subject dialogue bind — OOA&D package (ADR pattern like discourse/)."""

from __future__ import annotations

from casa.domain.dialogue_bind.binder import (
    SubjectDialogueBinder,
    build_subject_plan,
    gather_subject_dialogue_blocks,
)
from casa.domain.dialogue_bind.blocks import (
    JOURNAL_BOOTSTRAP_MARKERS,
    WAKE_JOURNAL_MARKERS,
    answer_block_to_dict,
    block_dict,
    is_journal_bootstrap_text,
    is_wake_journal_text,
    score_text,
    tokenize,
)
from casa.domain.dialogue_bind.dialogue import dialogue_continuity_blocks, infer_stance
from casa.domain.dialogue_bind.field import (
    capability_block,
    field_snapshot_block,
    looks_like_field_recall,
    salient_recall_tokens,
)
from casa.domain.dialogue_bind.journal import (
    journal_cap_for_intent,
    journal_confirmed_blocks,
    journal_identity_blocks,
    journal_recall_records,
    journal_skip_on_dialogue,
)
from casa.domain.dialogue_bind.model import SubjectDialogueContext
from casa.domain.dialogue_bind.scoring import (
    intent_affinity_delta,
    kb_hit_allowed,
    kb_reply_present,
    reweight_blocks_for_reply,
    text_passage_overlap,
)

__all__ = [
    "JOURNAL_BOOTSTRAP_MARKERS",
    "WAKE_JOURNAL_MARKERS",
    "SubjectDialogueBinder",
    "SubjectDialogueContext",
    "answer_block_to_dict",
    "block_dict",
    "build_subject_plan",
    "capability_block",
    "dialogue_continuity_blocks",
    "field_snapshot_block",
    "gather_subject_dialogue_blocks",
    "infer_stance",
    "intent_affinity_delta",
    "is_journal_bootstrap_text",
    "is_wake_journal_text",
    "journal_cap_for_intent",
    "journal_confirmed_blocks",
    "journal_identity_blocks",
    "journal_recall_records",
    "journal_skip_on_dialogue",
    "kb_hit_allowed",
    "kb_reply_present",
    "looks_like_field_recall",
    "reweight_blocks_for_reply",
    "salient_recall_tokens",
    "score_text",
    "text_passage_overlap",
    "tokenize",
]
