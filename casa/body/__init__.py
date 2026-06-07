"""Body extension points — motor/tools outside agent store (ADR-0046)."""

from casa.body.catalog_ingest import run_catalog_auto_ingest
from casa.body.catalog_sync import CatalogDiff, catalog_digest, diff_catalog, sync_catalog
from casa.body.contracts import (
    FunctionCallBackend,
    FunctionCallIntent,
    FunctionCallResult,
    FunctionSpec,
)
from casa.body.extension import BodyFunctionExtension, parse_function_spec
from casa.body.tool_card import tool_card_to_mm_event

__all__ = [
    "BodyFunctionExtension",
    "CatalogDiff",
    "FunctionCallBackend",
    "FunctionCallIntent",
    "FunctionCallResult",
    "FunctionSpec",
    "catalog_digest",
    "diff_catalog",
    "parse_function_spec",
    "run_catalog_auto_ingest",
    "sync_catalog",
    "tool_card_to_mm_event",
]
