#!/usr/bin/env python3
"""Interactive English console over the curriculum (NOT the dialogue chat).

This is a deterministic generator/translator, not free conversation: you give words
or role-tagged triples and it translates / inflects / builds an English clause using
exactly what was taught (glossary + morphology rules + clause grammar). It does not
understand meaning or parse free Russian — that is the architecture's ceiling.

Run:  python -m casa.curriculum.demo_repl      (or chat-en.cmd)

Commands (type ? for this help):
  t <слово>                 translate one word RU<->EN
  pl|past|cmp|3sg <word>    inflect an English word by a learned rule
  rupl <слово>              Russian plural (masculine, then neuter)
  s <subj> <verb> <obj> [flags]   build an English clause from a RU triple
       flags: past  neg  q  pl  num=<число>  adj=<прил>
       e.g.  s кот пить вода            -> The cat drinks the water.
             s кот пить вода pl q       -> Do the cats drink the water?
             s кот пить вода past neg   -> The cat did not drink the water.
             s кот пить вода num=два adj=большой -> Two big cats drink the water.
  sru <subj> <verb> <obj>   build a RUSSIAN clause (conjugation + accusative)
       e.g.  sru девочка читать книга -> Девочка читает книгу.
  b <subj> <verb> <obj>     one meaning -> BOTH languages (source auto-detected)
       e.g.  b девочка читать книга -> RU «Девочка читает книгу.» EN "The girl reads the book."
  val <rel> <x> <y>         validate a relation in the conceptual network (cross-lingual)
       rel in on/in/eat/drink/wear/ride/read/use; e.g.  val on яблоко стол -> valid
  g <subj> <verb> <obj>     grounded: validate the meaning, THEN render (or refuse)
       e.g.  g студент читать книга -> ok; g стол читать книга -> refused (not an agent)
  map <rel> <x> <y>         build the meaning map (nodes+typed edge); same for RU/EN
       e.g.  map on яблоко стол   ==   map on apple table
  graph <rel x y> ; <rel x y> ...   multi-edge meaning graph (semicolon-separated)
       e.g.  graph on яблоко стол ; near стол окно
  fp <pred x y> ; <pred x y> ...    situation fingerprint (synonyms/order/language -> one id)
       e.g.  fp лежит яблоко стол  ==  fp на яблоко стол  ==  fp on apple table
  parse <text>              parse a controlled clause -> graph + fingerprint
       e.g.  parse яблоко лежит на столе   ==   parse на столе яблоко   ==   parse apple on the table
  words                     list the words the field knows
  ?                         help        quit / exit / q!    leave
"""

from __future__ import annotations

import json
import sys

from casa._paths import REPO_ROOT
from casa.prisms.memory.f0_math_ingest import ingest_math_bundle
from casa.prisms.memory.memory_prisms import ensure_prisms
from casa.curriculum import (
    apply_conditioned_rule,
    bilingual_clause,
    compose_full_clause,
    compose_ru_clause,
    teach_clause_constructions,
    teach_conditioned_rule,
    teach_glossary,
    teach_np_order,
    teach_sentence_order,
    translate_term,
)
from casa.curriculum.translate import script_of

LAT = "schema-math"
BUNDLE = REPO_ROOT / "lab/exp_l/kb-math-concrete-schemas-l0.bundle.v1.json"
IRREGULAR_PAST = {
    "drink": "drank", "see": "saw", "know": "knew", "eat": "ate", "give": "gave",
    "read": "read", "take": "took", "make": "made", "find": "found", "say": "said",
}
EXTRA_WORDS = [
    ("один", "one"), ("два", "two"), ("три", "three"), ("четыре", "four"), ("пять", "five"),
    ("человек", "man"), ("женщина", "woman"), ("ребёнок", "child"), ("друг", "friend"),
    ("есть", "eat"), ("знать", "know"), ("давать", "give"), ("читать", "read"),
    ("хороший", "good"), ("белый", "white"), ("новый", "new"),
]


def _load_glossary() -> list[tuple[str, str]]:
    pairs: dict[str, str] = {}
    # curated lists first (verbs/adjectives win on setdefault), then the open
    # dictionary sample (~3000 nouns) so `t` covers far more words
    for name in ("en-np-clause-v1", "en-clause-v1", "en-sentence-v1", "en-vocab-v1", "bilingual-v1", "en-glossary-v1", "en-glossary-ru-open"):
        p = REPO_ROOT / f"lab/curriculum/{name}.json"
        if not p.exists():
            continue
        data = json.loads(p.read_text(encoding="utf-8"))
        rows = data.get("glossary") if isinstance(data, dict) else data
        for row in rows or []:
            if isinstance(row, (list, tuple)) and len(row) >= 2:
                pairs.setdefault(str(row[0]), str(row[1]))
    for ru, en in EXTRA_WORDS:
        pairs.setdefault(ru, en)
    return list(pairs.items())


def build_state() -> dict:
    bundle = json.loads(BUNDLE.read_text(encoding="utf-8"))
    state = ensure_prisms({})
    ingest_math_bundle(state, bundle)
    teach_glossary(state, _load_glossary(), bundle=bundle)
    rules = json.loads((REPO_ROOT / "lab/curriculum/en-rules-v1.json").read_text(encoding="utf-8"))["rules"]
    for rid, pairs in rules.items():
        teach_conditioned_rule(state, LAT, rid, [tuple(p) for p in pairs])
    ru = json.loads((REPO_ROOT / "lab/curriculum/ru-rules-v1.json").read_text(encoding="utf-8"))["rules"]
    for rid, pairs in ru.items():
        teach_conditioned_rule(state, LAT, rid, [tuple(p) for p in pairs])
    teach_clause_constructions(state, LAT)
    teach_np_order(state, LAT)
    teach_sentence_order(state, LAT, [({"subj": "кот", "verb": "читает", "obj": "книгу"}, ["кот", "читает", "книгу"])], rule_id="lang.sentence.svo.ru")
    net = REPO_ROOT / "lab/curriculum/concept-net-base-v1.json"
    if net.exists():
        from casa.curriculum.concept_net import teach_concept_net

        teach_concept_net(state, LAT, json.loads(net.read_text(encoding="utf-8")))
    return state


def _translate(state: dict, word: str) -> str:
    to = "latn" if script_of(word) == "cyrl" else "cyrl"
    hits = translate_term(state, LAT, word, to_script=to)
    return ", ".join(hits) if hits else "(не знаю этого слова)"


def _say(state: dict, args: list[str]) -> str:
    roles = [a for a in args if "=" not in a and a not in ("past", "neg", "q", "pl")]
    if len(roles) < 3:
        return "нужно: s <подлежащее> <глагол> <дополнение> [past neg q pl num=.. adj=..]"
    subj, verb, obj = roles[0], roles[1], roles[2]
    flags = {a for a in args if a in ("past", "neg", "q", "pl")}
    kv = dict(a.split("=", 1) for a in args if "=" in a)
    subject: dict = {"noun": subj}
    if "pl" in flags:
        subject["plural"] = True
    if "num" in kv:
        subject["number"] = kv["num"]
        subject["determiner"] = None
    if "adj" in kv:
        subject["adj"] = kv["adj"]
    out = compose_full_clause(
        state, LAT,
        subject=subject, obj={"noun": obj}, verb=verb,
        tense="past" if "past" in flags else "present",
        polarity="negative" if "neg" in flags else "affirmative",
        mood="interrogative" if "q" in flags else "declarative",
        irregular_past=IRREGULAR_PAST,
    )
    return out or "(не хватает слова в словаре — см. команду words)"


_RULES = {"pl": "lang.rule.plural.en", "past": "lang.rule.past.en", "cmp": "lang.rule.comparative.en", "3sg": "lang.rule.present3sg.en"}


def handle(state: dict, line: str) -> str | None:
    line = line.strip()
    if not line:
        return ""
    if line in ("quit", "exit", "q!", ":q"):
        return None
    if line in ("?", "help", "h"):
        return __doc__
    parts = line.split()
    cmd, args = parts[0], parts[1:]
    if cmd == "t" and args:
        return _translate(state, args[0])
    if cmd in _RULES and args:
        return apply_conditioned_rule(state, LAT, _RULES[cmd], args[0]) or "(правило не дало формы)"
    if cmd == "rupl" and args:
        w = args[0]
        if w[-1:] in ("о", "е"):  # neuter by ending
            return apply_conditioned_rule(state, LAT, "lang.rule.plural-nom-n.ru", w) or "(нет формы)"
        if w[-1:] in ("а", "я", "ь", "й"):
            return "(женский род / мягкая основа — вне области правила)"
        return apply_conditioned_rule(state, LAT, "lang.rule.plural-nom-m.ru", w) or "(нет формы)"  # masculine
    if cmd == "s":
        return _say(state, args)
    if cmd == "sru" and len(args) >= 3:
        return compose_ru_clause(state, LAT, subj=args[0], verb=args[1], obj=args[2]) or "(нет правила/формы)"
    if cmd == "b" and len(args) >= 3:
        src = "en" if script_of(args[0]) == "latn" else "ru"
        out = bilingual_clause(state, LAT, subj=args[0], verb=args[1], obj=args[2], source=src)
        return f"RU: {out['ru'] or '(?)'}\nEN: {out['en'] or '(?)'}"
    if cmd == "val" and len(args) >= 3:
        from casa.curriculum.concept_net import validate

        v = validate(state, LAT, args[0], args[1], args[2])
        mark = "✓ valid" if v["valid"] else "✗ invalid"
        return f"{mark}  [{v.get('reason')}]  ({v.get('x_concept')} {args[0]} {v.get('y_concept')})"
    if cmd == "g" and len(args) >= 3:
        from casa.curriculum.grounded import guarded_clause

        src = "en" if script_of(args[0]) == "latn" else "ru"
        r = guarded_clause(state, LAT, subj=args[0], verb=args[1], obj=args[2], source=src)
        if not r["valid"]:
            return f"✗ бессмыслица [{r['reason']}] — не порождаю"
        return f"✓\nRU: {r['ru'] or '(?)'}\nEN: {r['en'] or '(?)'}"
    if cmd == "map" and len(args) >= 3:
        from casa.curriculum.concept_net import relation_map, render_map

        m = relation_map(state, LAT, args[0], args[1], args[2])
        s = m["subject"] or {}
        return (
            f"{render_map(m)}\n"
            f"  {args[1]}: типы={s.get('types')} аффордансы={s.get('affords')}\n"
            f"  ребро: {m['edge']}"
        )
    if cmd == "graph" and args:
        from casa.curriculum.concept_net import meaning_graph, render_graph

        triples = [tuple(seg.split()) for seg in " ".join(args).split(";") if len(seg.split()) == 3]
        if not triples:
            return "нужно: graph <rel x y> ; <rel x y> ...  напр. graph on яблоко стол ; near стол окно"
        g = meaning_graph(state, LAT, triples)
        return render_graph(g) + f"\n  граф валиден: {g['valid']}  узлов: {len(g['nodes'])}"
    if cmd == "fp" and args:
        from casa.curriculum.situation import situation_fingerprint

        raw = [tuple(seg.split()) for seg in " ".join(args).split(";") if len(seg.split()) == 3]
        if not raw:
            return "нужно: fp <pred x y> ; <pred x y> ...  напр. fp лежит яблоко стол ; у стол окно"
        f = situation_fingerprint(state, LAT, raw)
        return f"отпечаток ситуации: id={f['id']}\n  карта: {f['key']}"
    if cmd == "parse" and args:
        from casa.curriculum.parse import parse_graph, parse_triples
        from casa.curriculum.concept_net import render_graph
        from casa.curriculum.situation import fingerprint

        text = " ".join(args)
        triples = parse_triples(state, LAT, text)
        if not triples:
            return "(не разобрал — нет известных понятий/отношений)"
        g = parse_graph(state, LAT, text)
        return f"{render_graph(g)}\n  отпечаток: id={fingerprint(g)['id']}"
    if cmd == "words":
        from casa.curriculum.translate import _name_edges

        ws = sorted({e.split("|names|lang.word.")[1] for e in _name_edges(state, LAT)})
        return " ".join(ws)
    return "не понял команду — нажми ? для справки"


def main() -> None:
    print("Загружаю поле и обучаю словарю/правилам…", file=sys.stderr)
    state = build_state()
    print("Готово. Английская консоль над куррикулумом. Нажми ? для справки, quit — выход.", file=sys.stderr)
    for raw in sys.stdin:
        out = handle(state, raw)
        if out is None:
            break
        if out:
            print(out)
        sys.stdout.flush()


if __name__ == "__main__":
    main()
