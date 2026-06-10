"""Body extension points — motor/tools + partner text tract (ADR-0046 / ADR-0028)."""

from casa.body.catalog_ingest import run_catalog_auto_ingest
from casa.body.catalog_sync import CatalogDiff, catalog_digest, diff_catalog, sync_catalog
from casa.body.contracts import (
    FunctionCallBackend,
    FunctionCallIntent,
    FunctionCallResult,
    FunctionSpec,
)
from casa.body.extension import BodyFunctionExtension, parse_function_spec
from casa.body.text_tract import (
    AFFERENT_FUNCTION,
    DIRECTION_AFFERENT,
    DIRECTION_EFFERENT,
    EFFERENT_FUNCTION,
    PARTNER_TEXT_TRACT_ID,
    TEXT_WIRE_CONSOLE,
    TRACT_KIND_SYMBOLIC,
    poll_pending_afferent,
    text_dir,
)
from casa.body.tool_card import tool_card_to_mm_event

__all__ = [
    "AFFERENT_FUNCTION",
    "BodyFunctionExtension",
    "CatalogDiff",
    "DIRECTION_AFFERENT",
    "DIRECTION_EFFERENT",
    "EFFERENT_FUNCTION",
    "FunctionCallBackend",
    "FunctionCallIntent",
    "FunctionCallResult",
    "FunctionSpec",
    "PARTNER_TEXT_TRACT_ID",
    "TEXT_WIRE_CONSOLE",
    "TRACT_KIND_SYMBOLIC",
    "catalog_digest",
    "diff_catalog",
    "parse_function_spec",
    "poll_pending_afferent",
    "run_catalog_auto_ingest",
    "sync_catalog",
    "text_dir",
    "tool_card_to_mm_event",
]
