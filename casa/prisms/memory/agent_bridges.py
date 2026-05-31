#!/usr/bin/env python3
"""Agent-owned bridges — self-tier links from prism_agent to profile lattices."""

from __future__ import annotations

from casa._paths import ensure_import_paths

ensure_import_paths()

import argparse
import json
import re
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from casa.prisms.control.sn_cen_runtime import FieldDigest
from casa.prisms.memory.agent_prism import agent_lattices, ensure_agent_prism, safe_agent_lattice_id
from casa.prisms.memory.memory_prisms import ensure_prisms
from casa.prisms.shared.field_write import load_field_state, save_field_state
from casa.prisms.shared.prism_state import (
    PRISM_AGENT,
    PRISM_CONTROL,
    PRISM_HIPPO,
    PRISM_MEMORY,
    active_prism_id,
    prism_agent,
    prism_control,
    prism_hippo,
    prism_memory,
)
from casa.prisms.shared.store_layout import agent_bridges_path, field_state_path

AGENT_BRIDGES_VERSION = 1
_BRIDGE_ID_RE = re.compile(r"^ab-[a-z0-9_-]{1,56}$")
_TARGET_PRISMS = frozenset({PRISM_CONTROL, PRISM_MEMORY, PRISM_HIPPO})
_BRIDGE_KINDS = frozenset({"agent_bridge", "agent_edge"})


def _utc_now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def _prism_block(state: dict, prism_id: str) -> dict:
    if prism_id == PRISM_AGENT:
        return prism_agent(state)
    if prism_id == PRISM_CONTROL:
        return prism_control(state)
    if prism_id == PRISM_MEMORY:
        return prism_memory(state)
    if prism_id == PRISM_HIPPO:
        return prism_hippo(state)
    raise ValueError(f"unknown prism: {prism_id!r}")


def _lattice_exists(state: dict, prism_id: str, lattice_id: str) -> bool:
    lats = _prism_block(state, prism_id).get("lattices") or {}
    return lattice_id in lats


def safe_bridge_id(bridge_id: str) -> str:
    bid = str(bridge_id or "").strip()
    if not _BRIDGE_ID_RE.fullmatch(bid):
        raise ValueError(f"bridge id must match ab-{{slug}}: {bridge_id!r}")
    return bid


def _default_bridge_id(from_lattice: str, to_prism: str, to_lattice: str) -> str:
    slug = re.sub(r"[^a-z0-9]+", "-", f"{from_lattice}-{to_prism}-{to_lattice}".lower()).strip("-")
    return safe_bridge_id(f"ab-{slug[:48]}")


def agent_bridges(state: dict) -> list[dict[str, Any]]:
    ensure_agent_prism(state)
    raw = prism_agent(state).get("bridges")
    if not isinstance(raw, list):
        return []
    return list(raw)


def _set_agent_bridges(state: dict, bridges: list[dict[str, Any]], *, touch_field_version: bool = True) -> None:
    ensure_agent_prism(state)
    prism_agent(state)["bridges"] = bridges
    if touch_field_version:
        state["field_version"] = int(state.get("field_version") or 0) + 1


def _normalize_endpoint(raw: dict[str, Any], *, role: str) -> dict[str, str]:
    if not isinstance(raw, dict):
        raise ValueError(f"{role} must be an object with prism and lattice_id")
    prism = str(raw.get("prism") or "").strip()
    lattice_id = str(raw.get("lattice_id") or "").strip()
    if not prism or not lattice_id:
        raise ValueError(f"{role} requires prism and lattice_id")
    return {"prism": prism, "lattice_id": lattice_id}


def _validate_bridge_record(state: dict, record: dict[str, Any]) -> dict[str, Any]:
    kind = str(record.get("kind") or "agent_bridge").strip()
    if kind not in _BRIDGE_KINDS:
        raise ValueError(f"unsupported bridge kind: {kind!r}")

    from_ep = _normalize_endpoint(record.get("from") or {}, role="from")
    if from_ep["prism"] != PRISM_AGENT:
        raise ValueError("agent bridge from.prism must be prism_agent")
    safe_agent_lattice_id(from_ep["lattice_id"])
    if not _lattice_exists(state, PRISM_AGENT, from_ep["lattice_id"]):
        raise KeyError(f"unknown agent lattice: {from_ep['lattice_id']}")

    to_ep = _normalize_endpoint(record.get("to") or {}, role="to")
    if to_ep["prism"] not in _TARGET_PRISMS:
        raise ValueError(f"bridge to.prism must be one of {sorted(_TARGET_PRISMS)}")
    if not _lattice_exists(state, to_ep["prism"], to_ep["lattice_id"]):
        raise KeyError(f"unknown target lattice: {to_ep['prism']}.{to_ep['lattice_id']}")

    relation = str(record.get("relation") or "routes_to").strip() or "routes_to"
    tokens = [str(t).strip() for t in (record.get("tokens") or []) if str(t).strip()]

    bid = record.get("id")
    if bid:
        bid = safe_bridge_id(str(bid))
    else:
        bid = _default_bridge_id(from_ep["lattice_id"], to_ep["prism"], to_ep["lattice_id"])

    return {
        "id": bid,
        "kind": kind,
        "from": from_ep,
        "to": to_ep,
        "relation": relation,
        "tokens": tokens,
        "updated_at": record.get("updated_at") or _utc_now(),
    }


def list_agent_bridges(state: dict) -> list[dict[str, Any]]:
    return [dict(b) for b in agent_bridges(state)]


def add_agent_bridge(
    state: dict,
    *,
    from_lattice: str,
    to_prism: str,
    to_lattice: str,
    relation: str = "routes_to",
    tokens: list[str] | None = None,
    bridge_id: str | None = None,
    kind: str = "agent_bridge",
) -> dict[str, Any]:
    record = _validate_bridge_record(
        state,
        {
            "id": bridge_id,
            "kind": kind,
            "from": {"prism": PRISM_AGENT, "lattice_id": from_lattice},
            "to": {"prism": to_prism, "lattice_id": to_lattice},
            "relation": relation,
            "tokens": tokens or [],
        },
    )
    bridges = agent_bridges(state)
    bridges = [b for b in bridges if b.get("id") != record["id"]]
    bridges.append(record)
    _set_agent_bridges(state, bridges)
    return record


def remove_agent_bridge(state: dict, bridge_id: str) -> bool:
    bid = safe_bridge_id(bridge_id)
    bridges = agent_bridges(state)
    kept = [b for b in bridges if b.get("id") != bid]
    if len(kept) == len(bridges):
        return False
    _set_agent_bridges(state, kept)
    return True


def _load_bridges_file(store_dir: Path) -> list[dict[str, Any]]:
    path = agent_bridges_path(store_dir)
    if not path.is_file():
        return []
    data = json.loads(path.read_text(encoding="utf-8"))
    if isinstance(data, dict):
        return list(data.get("bridges") or [])
    if isinstance(data, list):
        return data
    return []


def save_agent_bridges(store_dir: Path, state: dict) -> dict[str, Any]:
    store_dir = store_dir.resolve()
    ensure_agent_prism(state)
    bridges = agent_bridges(state)
    doc = {
        "schema_version": AGENT_BRIDGES_VERSION,
        "kind": "agent_bridges",
        "updated_at": _utc_now(),
        "bridges": bridges,
    }
    path = agent_bridges_path(store_dir)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(doc, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return doc


def load_agent_bridges(store_dir: Path, state: dict, *, validate: bool = True) -> dict[str, Any]:
    store_dir = store_dir.resolve()
    ensure_prisms(state)
    raw = _load_bridges_file(store_dir)
    loaded: list[dict[str, Any]] = []
    skipped: list[dict[str, str]] = []
    for item in raw:
        try:
            if validate:
                loaded.append(_validate_bridge_record(state, item))
            else:
                loaded.append(dict(item))
        except (KeyError, ValueError) as exc:
            skipped.append({"id": str(item.get("id") or ""), "reason": str(exc)})
    _set_agent_bridges(state, loaded, touch_field_version=False)
    return {"loaded": len(loaded), "skipped": skipped}


def _concept_from_edge_token(token: str) -> str | None:
    text = token.strip()
    if not text.startswith("E:"):
        return None
    body = text[2:]
    parts = body.split("|")
    if len(parts) >= 3:
        return parts[2].strip() or None
    return None


def merge_digest_with_agent_bridges(
    digest: FieldDigest,
    state: dict,
    *,
    hybrid: bool = True,
) -> FieldDigest:
    """Merge agent bridge tokens into digest when agent prism is active or hybrid."""
    active = active_prism_id(state)
    if not hybrid and active != PRISM_AGENT:
        return digest
    bridges = agent_bridges(state)
    if not bridges:
        return digest

    edge_tokens = list(digest.edge_tokens)
    present = list(digest.present_tokens)
    concept_ids = list(digest.concept_ids)
    concept_scores = dict(digest.concept_scores)
    modules = list(digest.modules_active)

    for bridge in bridges:
        bid = str(bridge.get("id") or "")
        modules.append(f"agent_bridge:{bid}" if bid else "agent_bridge")
        for token in bridge.get("tokens") or []:
            tok = str(token).strip()
            if not tok:
                continue
            if tok not in edge_tokens:
                edge_tokens.append(tok)
            if tok not in present:
                present.append(tok)
            cid = _concept_from_edge_token(tok)
            if cid and cid not in concept_ids:
                concept_ids.append(cid)
                concept_scores[cid] = max(concept_scores.get(cid, 0.0), 0.55)

        to_ep = bridge.get("to") or {}
        to_lat = str(to_ep.get("lattice_id") or "")
        if to_lat and to_lat not in concept_ids:
            concept_ids.append(to_lat)
            concept_scores[to_lat] = max(concept_scores.get(to_lat, 0.0), 0.5)

    return FieldDigest(
        concept_ids=concept_ids,
        edge_tokens=edge_tokens,
        concept_scores=concept_scores,
        digest_vector=list(digest.digest_vector),
        modules_active=modules,
        present_tokens=present,
    )


def main() -> None:
    p = argparse.ArgumentParser(description="Agent-owned bridges — links from prism_agent to profile")
    sub = p.add_subparsers(dest="cmd", required=True)

    def add_store(sp: argparse.ArgumentParser) -> None:
        sp.add_argument("--store-dir", type=Path, required=True)

    sp_add = sub.add_parser("add-bridge")
    add_store(sp_add)
    sp_add.add_argument("--from-lattice", required=True)
    sp_add.add_argument("--to-prism", required=True, choices=sorted(_TARGET_PRISMS))
    sp_add.add_argument("--to-lattice", required=True)
    sp_add.add_argument("--relation", default="routes_to")
    sp_add.add_argument("--token", action="append", dest="tokens", default=[])
    sp_add.add_argument("--id", dest="bridge_id", default=None)
    sp_add.add_argument("--kind", default="agent_bridge", choices=sorted(_BRIDGE_KINDS))
    sp_add.add_argument("--write", action="store_true")

    sp_list = sub.add_parser("list-bridges")
    add_store(sp_list)

    sp_rm = sub.add_parser("remove-bridge")
    add_store(sp_rm)
    sp_rm.add_argument("--id", dest="bridge_id", required=True)
    sp_rm.add_argument("--write", action="store_true")

    sp_save = sub.add_parser("save")
    add_store(sp_save)

    sp_load = sub.add_parser("load")
    add_store(sp_load)

    args = p.parse_args()
    store_dir = args.store_dir.resolve()
    fs = field_state_path(store_dir)
    state = ensure_prisms(load_field_state(fs)) if fs.is_file() else ensure_prisms({"schema_version": "multi_prism_v1", "field_version": 0})

    from casa.prisms.memory.agent_prism import load_agent_prism

    load_agent_prism(store_dir, state)
    load_agent_bridges(store_dir, state)

    out: Any = None

    if args.cmd == "add-bridge":
        out = add_agent_bridge(
            state,
            from_lattice=args.from_lattice,
            to_prism=args.to_prism,
            to_lattice=args.to_lattice,
            relation=args.relation,
            tokens=args.tokens,
            bridge_id=args.bridge_id,
            kind=args.kind,
        )
    elif args.cmd == "list-bridges":
        out = {"bridges": list_agent_bridges(state), "count": len(agent_bridges(state))}
    elif args.cmd == "remove-bridge":
        ok = remove_agent_bridge(state, args.bridge_id)
        out = {"removed": ok, "id": args.bridge_id}
        if not ok:
            raise SystemExit(1)
    elif args.cmd == "save":
        out = save_agent_bridges(store_dir, state)
    elif args.cmd == "load":
        out = load_agent_bridges(store_dir, state)

    write = getattr(args, "write", False) or args.cmd in ("save",)
    if write and args.cmd != "load":
        save_agent_bridges(store_dir, state)
        if fs.parent.exists():
            save_field_state(fs, state, compact=True)

    print(json.dumps(out, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
