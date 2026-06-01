"""OOA&D domain layer (ADR-0020): objects over field_state dict wire format."""

from casa.domain.field_state import FieldState, SessionFocus
from casa.domain.lattice import Lattice
from casa.domain.persistence import field_state_from_dict, field_state_to_dict
from casa.domain.prism import (
    PRISM_KIND_CONTENT,
    PRISM_KIND_CONTROL,
    PRISM_KIND_HOT_CONTEXT,
    PRISM_KIND_ROUTER,
    Prism,
    PrismCatalog,
    PrismKind,
    prism_from_block,
)
from casa.domain.prism_ids import PRISM_MEMORY, PRISM_ROUTER
from casa.domain.prism_wire import infer_prism_kind, normalize_prisms
from casa.domain.routing import Route, RouteContext, RouteTarget, Router
from casa.domain.stack import StackSpec, load_stack

__all__ = [
    "FieldState",
    "SessionFocus",
    "Lattice",
    "field_state_from_dict",
    "field_state_to_dict",
    "PRISM_KIND_CONTENT",
    "PRISM_KIND_HOT_CONTEXT",
    "PRISM_KIND_ROUTER",
    "PRISM_KIND_CONTROL",
    "PRISM_MEMORY",
    "PRISM_ROUTER",
    "infer_prism_kind",
    "normalize_prisms",
    "Prism",
    "PrismCatalog",
    "PrismKind",
    "prism_from_block",
    "Route",
    "RouteContext",
    "RouteTarget",
    "Router",
    "StackSpec",
    "load_stack",
]
