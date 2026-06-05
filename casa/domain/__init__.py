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
from casa.domain.edge_relink import (
    RelinkResult,
    agent_relink_crosslink,
    relink_vis_lex_bridge,
    supersede_emergent_route,
)
from casa.domain.emergent_promote import (
    PromoteResult,
    TrialPlan,
    capabilities_on_field,
    fill_trial_plan_if_needed,
    probe_gate_passed,
    promote_from_probe_report,
    promote_goal_route,
    record_probe_gate,
    suggest_trial_plan,
)
from casa.domain.plan_tick import PlanTick, promote_applicability_route, promote_capability_route
from casa.domain.routing import (
    ROUTE_KIND_APPLICABILITY,
    ROUTE_KIND_CAPABILITY,
    ROUTE_KIND_GOAL,
    ROUTE_KIND_KNOWLEDGE,
    Route,
    RouteContext,
    RouteKind,
    RouteTarget,
    Router,
    RoutingChain,
)
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
    "ROUTE_KIND_APPLICABILITY",
    "ROUTE_KIND_CAPABILITY",
    "ROUTE_KIND_GOAL",
    "ROUTE_KIND_KNOWLEDGE",
    "Route",
    "RouteContext",
    "RouteKind",
    "RouteTarget",
    "Router",
    "RoutingChain",
    "PlanTick",
    "PromoteResult",
    "RelinkResult",
    "agent_relink_crosslink",
    "relink_vis_lex_bridge",
    "supersede_emergent_route",
    "TrialPlan",
    "capabilities_on_field",
    "fill_trial_plan_if_needed",
    "probe_gate_passed",
    "promote_applicability_route",
    "promote_capability_route",
    "promote_from_probe_report",
    "promote_goal_route",
    "record_probe_gate",
    "suggest_trial_plan",
    "StackSpec",
    "load_stack",
]
