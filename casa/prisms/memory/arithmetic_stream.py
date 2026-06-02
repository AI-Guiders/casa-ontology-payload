#!/usr/bin/env python3
"""Teacher-side arithmetic example stream (ingest only — not agent runtime oracle)."""

from __future__ import annotations

import ast
import operator
import random
import secrets
from typing import Any, Callable

from casa.prisms.memory.f0_pattern_extract import numeral_int_to_concept_id

_OPS: dict[type, Callable[[int, int], int]] = {
    ast.Add: operator.add,
    ast.Sub: operator.sub,
    ast.Mult: operator.mul,
    ast.Div: operator.floordiv,
    ast.FloorDiv: operator.floordiv,
    ast.USub: operator.neg,
    ast.UAdd: operator.pos,
}


def _eval_ast(node: ast.AST) -> int:
    if isinstance(node, ast.Constant) and isinstance(node.value, int):
        return int(node.value)
    if isinstance(node, ast.UnaryOp) and isinstance(node.op, (ast.UAdd, ast.USub)):
        fn = _OPS[type(node.op)]
        return fn(_eval_ast(node.operand))
    if isinstance(node, ast.BinOp) and isinstance(node.op, (ast.Add, ast.Sub, ast.Mult, ast.Div, ast.FloorDiv)):
        fn = _OPS[type(node.op)]
        return fn(_eval_ast(node.left), _eval_ast(node.right))
    raise ValueError(f"unsupported ast: {type(node).__name__}")


def safe_int_eval(expr: str) -> int:
    """Evaluate integer arithmetic only (+ - * / //, parentheses)."""
    expr = str(expr or "").strip().replace("×", "*").replace("÷", "/")
    if not expr:
        raise ValueError("empty expression")
    tree = ast.parse(expr, mode="eval")
    return _eval_ast(tree.body)


def answer_concept_id(value: int) -> str:
    cid = numeral_int_to_concept_id(int(value))
    if not cid:
        raise ValueError(f"no concept for value={value}")
    return cid


def _rand_int(rng: random.Random, lo: int, hi: int) -> int:
    return rng.randint(lo, hi)


def generate_example(
    rng: random.Random,
    *,
    max_value: int = 50,
    ops: tuple[str, ...] = ("add", "sub", "mul", "div"),
    stick_style: bool = False,
) -> dict[str, Any]:
    """Return {cue, correct, concept_id, scene, op, a, b}."""
    max_value = max(1, int(max_value))
    op = rng.choice(ops)

    if op == "add":
        a = _rand_int(rng, 0, max_value)
        b = _rand_int(rng, 0, max(0, max_value - a))
        val = a + b
        sym = "+"
    elif op == "sub":
        a = _rand_int(rng, 0, max_value)
        b = _rand_int(rng, 0, a) if a > 0 else 0
        val = a - b
        sym = "-"
    elif op == "mul":
        a = _rand_int(rng, 0, min(12, max_value))
        b = _rand_int(rng, 0, min(12, max_value))
        val = a * b
        sym = "×"
    elif op == "div":
        b = _rand_int(rng, 1, min(12, max_value))
        val = _rand_int(rng, 0, min(12, max_value))
        a = val * b
        sym = "÷"
    else:
        raise ValueError(f"unknown op={op!r}")

    if stick_style and val <= 4 and a <= 4 and b <= 4 and op in ("add", "sub"):
        stick = lambda n: "|" * n if n > 0 else "0"
        if op == "add":
            cue = f"{stick(a)} {sym} {stick(b)}"
        else:
            cue = f"{stick(a)} {sym} {stick(b)}"
        correct = str(val)
    else:
        cue = f"{a} {sym} {b}"
        correct = str(val)

    cue = f"{cue} = ?"
    return {
        "cue": cue,
        "correct": correct,
        "concept_id": answer_concept_id(val),
        "scene": f"arith_stream:{op}",
        "op": op,
        "a": a,
        "b": b,
        "value": val,
    }


def generate_batch(
    count: int,
    *,
    seed: int | None = None,
    max_value: int = 50,
    stick_fraction: float = 0.15,
) -> list[dict[str, Any]]:
    rng = random.Random(seed if seed is not None else secrets.randbits(64))
    out: list[dict[str, Any]] = []
    for _ in range(max(1, count)):
        ex = generate_example(
            rng,
            max_value=max_value,
            stick_style=rng.random() < stick_fraction,
        )
        out.append(ex)
    return out
