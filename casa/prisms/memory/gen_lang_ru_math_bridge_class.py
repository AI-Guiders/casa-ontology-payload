#!/usr/bin/env python3
"""Generate lang-ru-math-bridge class: narrow RU text for math-palochki roles."""

from __future__ import annotations

import sys
from pathlib import Path

_REPO = Path(__file__).resolve().parents[3]
if str(_REPO) not in sys.path:
    sys.path.insert(0, str(_REPO))

from casa._paths import REPO_ROOT, ensure_import_paths

ensure_import_paths()

import argparse
import json
from typing import Any

CLASS_DIR = REPO_ROOT / "lessons/lang-ru-math-bridge"

# math.role|denotes|lang.word — same convention as math-palochki bundle graph
ROLE_LINKS: list[tuple[str, str]] = [
    ("math.role.addend", "слагаемое"),
    ("math.role.sum", "сумма"),
    ("math.role.minuend", "уменьшаемое"),
    ("math.role.subtrahend", "вычитаемое"),
    ("math.role.difference", "разность"),
    ("math.role.factor", "множитель"),
    ("math.role.product", "произведение"),
    ("math.role.dividend", "делимое"),
    ("math.role.divisor", "делитель"),
    ("math.role.quotient", "частное"),
    ("math.role.heap", "кучка"),
    ("math.entity.stick", "палочка"),
]

FRAC_ROLE_LINKS: list[tuple[str, str]] = [
    ("math.concept.fraction", "дробь"),
    ("math.role.numerator", "числитель"),
    ("math.role.denominator", "знаменатель"),
]

OP_LINKS: list[tuple[str, str]] = [
    ("math.op.add", "плюс"),
    ("math.op.sub", "минус"),
    ("math.op.mul", "умножить"),
    ("math.op.div", "делить"),
]

VOCAB_ONLY: list[str] = ["сколько", "равно", "сложить", "вычесть", "разделить", "поровну"]

# Те же формулы, что lesson-10 recap и lesson-17 в math-palochki (cue → роль результата).
FORMULA_SCENES: list[dict[str, Any]] = [
    {
        "id": "math_formula_add",
        "caption": "слагаемое + слагаемое = сумма",
        "words": ["слагаемое", "сумма", "равно"],
        "punctuation": ["+", "="],
        "math_episode": {
            "cue": "слагаемое + слагаемое = сумма",
            "correct": "сумма",
            "concept_id": "math.role.sum",
            "scene": "lang_bridge_formula_add",
        },
    },
    {
        "id": "math_formula_sub",
        "caption": "уменьшаемое − вычитаемое = разность",
        "words": ["уменьшаемое", "вычитаемое", "разность", "равно"],
        "punctuation": ["−", "="],
        "math_episode": {
            "cue": "уменьшаемое − вычитаемое = разность",
            "correct": "разность",
            "concept_id": "math.role.difference",
            "scene": "lang_bridge_formula_sub",
        },
    },
    {
        "id": "math_formula_mul",
        "caption": "множитель × множитель = произведение",
        "words": ["множитель", "произведение", "равно"],
        "punctuation": ["×", "="],
        "math_episode": {
            "cue": "множитель × множитель = произведение",
            "correct": "произведение",
            "concept_id": "math.role.product",
            "scene": "lang_bridge_formula_mul",
        },
    },
    {
        "id": "math_formula_div",
        "caption": "делимое ÷ делитель = частное",
        "words": ["делимое", "делитель", "частное", "равно"],
        "punctuation": ["÷", "="],
        "math_episode": {
            "cue": "делимое ÷ делитель = частное",
            "correct": "частное",
            "concept_id": "math.role.quotient",
            "scene": "lang_bridge_formula_div",
        },
    },
]

# Стрелочные варианты — как presentation в lesson-17 math-palochki.
FORMULA_ARROW_SCENES: list[dict[str, Any]] = [
    {
        "id": "math_formula_add_arrow",
        "caption": "слагаемое + слагаемое → сумма",
        "words": ["слагаемое", "сумма"],
        "punctuation": ["+", "→"],
        "math_episode": {
            "cue": "слагаемое + слагаемое → сумма",
            "correct": "сумма",
            "concept_id": "math.role.sum",
            "scene": "lang_bridge_formula_add_arrow",
        },
    },
    {
        "id": "math_formula_sub_arrow",
        "caption": "уменьшаемое − вычитаемое → разность",
        "words": ["уменьшаемое", "вычитаемое", "разность"],
        "punctuation": ["−", "→"],
        "math_episode": {
            "cue": "уменьшаемое − вычитаемое → разность",
            "correct": "разность",
            "concept_id": "math.role.difference",
            "scene": "lang_bridge_formula_sub_arrow",
        },
    },
    {
        "id": "math_formula_mul_arrow",
        "caption": "множитель × множитель → произведение",
        "words": ["множитель", "произведение"],
        "punctuation": ["×", "→"],
        "math_episode": {
            "cue": "множитель × множитель → произведение",
            "correct": "произведение",
            "concept_id": "math.role.product",
            "scene": "lang_bridge_formula_mul_arrow",
        },
    },
    {
        "id": "math_formula_div_arrow",
        "caption": "делимое ÷ делитель → частное",
        "words": ["делимое", "делитель", "частное"],
        "punctuation": ["÷", "→"],
        "math_episode": {
            "cue": "делимое ÷ делитель → частное",
            "correct": "частное",
            "concept_id": "math.role.quotient",
            "scene": "lang_bridge_formula_div_arrow",
        },
    },
]


def _role_edges() -> list[dict[str, str]]:
    edges: list[dict[str, str]] = []
    for role, word in ROLE_LINKS + OP_LINKS + FRAC_ROLE_LINKS:
        edges.append(
            {
                "src": role,
                "relation": "denotes",
                "dst": f"lang.word.{word}",
            }
        )
    return edges


def _scenes() -> list[dict[str, Any]]:
    return [
        {
            "id": "math_sticks",
            "caption": "Палочки и кучки: одна палочка, кучка палочек, сколько палочек",
            "words": ["палочка", "кучка", "сколько"],
        },
        {
            "id": "math_ops_ru",
            "caption": "Четыре действия: плюс минус умножить делить",
            "words": ["плюс", "минус", "умножить", "делить"],
        },
        {
            "id": "math_add_roles",
            "caption": "Сложение: слагаемое плюс слагаемое равно сумма",
            "words": ["слагаемое", "плюс", "сумма", "сложить", "равно"],
        },
        {
            "id": "math_sub_roles",
            "caption": "Вычитание: уменьшаемое минус вычитаемое равно разность",
            "words": ["уменьшаемое", "минус", "вычитаемое", "разность", "вычесть", "равно"],
        },
        {
            "id": "math_mul_roles",
            "caption": "Умножение: множитель умножить множитель равно произведение",
            "words": ["множитель", "умножить", "произведение", "равно"],
        },
        {
            "id": "math_div_roles",
            "caption": "Деление: делимое делить делитель равно частное поровну",
            "words": ["делимое", "делить", "делитель", "частное", "поровну", "равно"],
        },
        *FORMULA_SCENES,
        *FORMULA_ARROW_SCENES,
        {
            "id": "math_frac_roles",
            "caption": "числитель / знаменатель = дробь",
            "words": ["числитель", "знаменатель", "дробь"],
            "punctuation": ["/", "="],
            "math_episode": {
                "cue": "числитель / знаменатель = дробь",
                "correct": "дробь",
                "concept_id": "math.concept.fraction",
                "scene": "lang_bridge_frac_roles",
            },
        },
        {
            "id": "math_frac_roles_short",
            "caption": "числитель / знаменатель",
            "words": ["числитель", "знаменатель"],
            "punctuation": ["/"],
            "math_episode": {
                "cue": "числитель / знаменатель",
                "correct": "дробь",
                "concept_id": "math.concept.fraction",
                "scene": "lang_bridge_frac_roles_short",
            },
        },
    ]


def build_bundle() -> dict[str, Any]:
    scenes = _scenes()
    claims: list[dict[str, str]] = []
    seen: set[str] = set()
    for role, word in ROLE_LINKS + OP_LINKS + FRAC_ROLE_LINKS:
        cid = f"lang.word.{word}"
        if cid not in seen:
            claims.append({"concept_id": cid, "text": f"RU math bridge → {role}"})
            seen.add(cid)
    for word in VOCAB_ONLY:
        cid = f"lang.word.{word}"
        if cid not in seen:
            claims.append({"concept_id": cid, "text": "RU math bridge vocabulary"})
            seen.add(cid)
    for scene in scenes:
        for word in scene.get("words") or []:
            cid = f"lang.word.{word}"
            if cid not in seen:
                claims.append({"concept_id": cid, "text": "RU math bridge scene word"})
                seen.add(cid)

    return {
        "bundle_id": "kb-lang-ru-math-bridge-v1",
        "title": "RU text bridge for math-palochki (roles, ops, sticks)",
        "doc": "lessons/lang-ru-math-bridge/README.md",
        "schema_version": 1,
        "scenes": scenes,
        "claims": claims,
        "graph": {"edges": _role_edges()},
        "math_role_links": _role_edges(),
    }


def _words_for_scene(scene_id: str, scenes: list[dict]) -> list[str]:
    for s in scenes:
        if s.get("id") == scene_id:
            return list(s.get("words") or [])
    return []


def _links_for_words(words: set[str]) -> list[dict[str, str]]:
    out: list[dict[str, str]] = []
    for role, word in ROLE_LINKS + OP_LINKS + FRAC_ROLE_LINKS:
        if word in words:
            out.append({"src": role, "relation": "denotes", "dst": f"lang.word.{word}"})
    return out


def build_manifest(bundle: dict[str, Any]) -> dict[str, Any]:
    scenes = list(bundle.get("scenes") or [])
    scene_by_id = {s["id"]: s for s in scenes}

    lessons: list[dict[str, Any]] = [
        {
            "id": "lesson-00-sticks",
            "title": "Палочки и кучки",
            "scene_ids": ["math_sticks"],
        },
        {
            "id": "lesson-01-ops",
            "title": "Слова для + − × ÷",
            "scene_ids": ["math_ops_ru"],
        },
        {
            "id": "lesson-02-add",
            "title": "Роли сложения",
            "scene_ids": ["math_add_roles"],
        },
        {
            "id": "lesson-03-sub",
            "title": "Роли вычитания",
            "scene_ids": ["math_sub_roles"],
        },
        {
            "id": "lesson-04-mul",
            "title": "Роли умножения",
            "scene_ids": ["math_mul_roles"],
        },
        {
            "id": "lesson-05-div",
            "title": "Роли деления",
            "scene_ids": ["math_div_roles"],
        },
        {
            "id": "lesson-06-formulas",
            "title": "Формулы ролей (=), как в math-palochki",
            "scene_ids": [s["id"] for s in FORMULA_SCENES],
        },
        {
            "id": "lesson-07-formulas-arrow",
            "title": "Формулы ролей (→), как lesson-17",
            "scene_ids": [s["id"] for s in FORMULA_ARROW_SCENES],
        },
        {
            "id": "lesson-08-fractions",
            "title": "Дробь: числитель / знаменатель",
            "scene_ids": ["math_frac_roles", "math_frac_roles_short"],
        },
    ]
    for lesson in lessons:
        words: set[str] = set()
        for sid in lesson.get("scene_ids") or []:
            words.update(_words_for_scene(sid, scenes))
        lesson["role_links"] = _links_for_words(words)

    probe: list[dict[str, Any]] = []
    for role, word in ROLE_LINKS:
        probe.append(
            {
                "kind": "l2",
                "word": word,
                "expect": f"lang.word.{word}",
                "min_votes": 2,
            }
        )
        probe.append(
            {
                "kind": "math_f0",
                "cue": word,
                "expect": role,
            }
        )
    for op, word in OP_LINKS:
        probe.append({"kind": "l2", "word": word, "expect": f"lang.word.{word}", "min_votes": 2})
        probe.append({"kind": "math_f0", "cue": word, "expect": op})
    for role, word in FRAC_ROLE_LINKS:
        probe.append({"kind": "l2", "word": word, "expect": f"lang.word.{word}", "min_votes": 2})
        probe.append({"kind": "math_f0", "cue": word, "expect": role})
    probe.append(
        {
            "kind": "math_f0",
            "cue": "числитель / знаменатель = дробь",
            "expect": "math.concept.fraction",
        }
    )
    probe.append(
        {
            "kind": "math_f0",
            "cue": "числитель / знаменатель",
            "expect": "math.concept.fraction",
        }
    )

    probe.append(
        {
            "kind": "scene",
            "scene_id": "math_add_roles",
            "expect_words": ["слагаемое", "сумма", "плюс"],
            "min_c_votes": 1,
        }
    )
    probe.append(
        {
            "kind": "scene",
            "scene_id": "math_div_roles",
            "expect_words": ["делимое", "частное", "делить"],
            "min_c_votes": 1,
        }
    )

    for scene in FORMULA_SCENES + FORMULA_ARROW_SCENES:
        me = scene.get("math_episode") or {}
        cue = str(me.get("cue") or scene.get("caption") or "")
        expect = str(me.get("concept_id") or "")
        if cue and expect:
            probe.append({"kind": "math_f0", "cue": cue, "expect": expect, "tier": "formula"})
            probe.append(
                {
                    "kind": "scene",
                    "scene_id": scene["id"],
                    "expect_words": list(scene.get("words") or [])[:3],
                    "min_c_votes": 1,
                }
            )

    return {
        "schema_version": 1,
        "class_id": "lang-ru-math-bridge",
        "target_agent": "von-neumann",
        "requires_math_class": "math-palochki",
        "bundle": "kb-lang-ru-math-bridge-v1.bundle.json",
        "lessons": lessons,
        "probe": probe,
        "probe_threshold": 0.75,
    }


def write_class(*, out_dir: Path | None = None) -> dict[str, Path]:
    out = (out_dir or CLASS_DIR).resolve()
    out.mkdir(parents=True, exist_ok=True)
    bundle = build_bundle()
    manifest = build_manifest(bundle)
    bundle_path = out / "kb-lang-ru-math-bridge-v1.bundle.json"
    manifest_path = out / "class.manifest.json"
    bundle_path.write_text(json.dumps(bundle, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    manifest_path.write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    readme = out / "README.md"
    if not readme.exists():
        readme.write_text(
            "# lang-ru-math-bridge\n\n"
            "Узкий русский текстовый мост к **math-palochki**: роли операндов, слова операций, "
            "сцены «палочки/кучки», **формулы** `слагаемое + слагаемое = сумма` и т.д. — те же cue, "
            "что lesson-10/17 math-palochki. Ingest **после** math-palochki на том же agent store.\n\n"
            "```bash\n"
            "python tools/ingest_lang_lesson_class.py --store-dir agents/von-neumann\n"
            "python tools/check_lang_math_bridge.py --store-dir agents/von-neumann\n"
            "```\n",
            encoding="utf-8",
        )
    return {"bundle": bundle_path, "manifest": manifest_path, "readme": readme}


def main() -> None:
    p = argparse.ArgumentParser(description="Generate lang-ru-math-bridge lesson class")
    p.add_argument("--out-dir", type=Path, default=CLASS_DIR)
    args = p.parse_args()
    paths = write_class(out_dir=args.out_dir)
    print(json.dumps({k: str(v) for k, v in paths.items()}, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
