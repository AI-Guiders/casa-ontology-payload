#!/usr/bin/env python3
"""Answer a domain clause through the conceptual network (deep routing for the chat).

If a line is a clean domain clause (parses to a meaning graph over known concepts), the
agent answers via the network INSTEAD of the statistical dialogue engine: it validates
the situation, confirms the normalised meaning (in both languages), notes similarity to
remembered situations, and stores it — or, on a category error, explains why it cannot
hold. Anything that is not a clean domain clause returns None (the caller falls through
to the normal engine), so casual conversation is untouched. Deterministic, auditable.
"""

from __future__ import annotations

# short closed sets used only as a cheap pre-filter (avoid building the network for chit-chat)
_DOMAIN_HINTS = {
    "на", "в", "у", "около", "рядом", "под", "лежит", "стоит", "находится",
    "ест", "есть", "пьёт", "пить", "читает", "читать", "носит",
    "из", "сделан", "сделана", "сделано", "сделаны",
    "открой", "закрой", "сохрани", "удали", "нажми", "выбери", "измени",  # UI imperatives
    "открывает", "закрывает", "сохраняет", "удаляет", "нажимает", "выбирает", "изменяет",
    "покажи", "настрой", "скопируй", "перемести", "создай", "переименуй", "распечатай", "включи", "установи", "скачай",
    "показать", "настроить", "копировать", "создать", "распечатать", "включить", "установить", "скачать",
    "on", "in", "near", "by", "under", "eats", "reads", "drinks", "made",
    "open", "close", "save", "delete", "click", "select", "edit",
    "show", "configure", "copy", "move", "create", "rename", "print", "enable", "install", "download", "set", "display",
    "to", "into",  # action destination
    "красный", "красная", "красное", "белый", "белая", "белое", "чёрный", "чёрная", "чёрное",  # predicative colour
    "зелёный", "зелёная", "зелёное", "red", "white", "black", "green",
    "синий", "синяя", "синее", "жёлтый", "жёлтая", "жёлтое", "серый", "серая", "серое",
    "коричневый", "коричневая", "коричневое", "blue", "yellow", "grey", "brown",
    "больше", "bigger",  # comparison
    "носит", "использует", "пишет", "готовит", "моет", "даёт", "берёт",  # everyday verbs
    "надень", "напиши", "приготовь", "помой", "дай", "возьми", "используй",
    "wear", "use", "write", "cook", "wash", "give", "take",
    "живёт", "живут", "lives", "live",  # habitat
}


def looks_domain(text: str) -> bool:
    """Cheap check (no network) — short line containing a locative/transitive hint."""
    toks = text.lower().split()
    return 1 <= len(toks) <= 6 and any(t.strip(".,!?") in _DOMAIN_HINTS for t in toks)


_FUNCTION_OK = {"the", "a", "an", "лежит", "стоит", "находится", "is", "lies", "stands"}


def _is_clean_clause(state: dict, lattice_id: str, text: str) -> bool:
    """Every token must be a known concept, a preposition, a known verb, or an article —
    so casual sentences with unknown words (e.g. «у меня нет времени») are NOT routed."""
    from casa.curriculum.attributes import attr_of_token
    from casa.curriculum.parse import _POSITIONAL, _PREPS, _name_index, resolve_token
    from casa.curriculum.situation import PREDICATE_RELATION

    names = _name_index(state, lattice_id)
    for raw in text.split():
        t = raw.strip(".,!?").lower()
        if not t:
            continue
        if t in _PREPS or t in _POSITIONAL or t in PREDICATE_RELATION or t in _FUNCTION_OK:
            continue
        if attr_of_token(t) is not None:  # an adjective modifier (красное …) is fine
            continue
        if resolve_token(state, lattice_id, t, names) is None:
            return False
    return True


def answer_clause(state: dict, lattice_id: str, text: str) -> str | None:
    """Answer a domain clause via the conceptual network, or None if it is not one."""
    from casa.curriculum.parse import parse_graph
    from casa.curriculum.roundtrip import realize_graph
    from casa.curriculum.situation_memory import recall_similar
    from casa.curriculum.situation_store import load_memory, persist_situation

    if not _is_clean_clause(state, lattice_id, text):
        return None  # unknown words -> not a clean domain clause -> normal engine
    graph = parse_graph(state, lattice_id, text)  # includes adjective attrs on nodes
    if not graph.get("edges"):
        return None  # not a clean domain clause -> let the normal engine handle it
    bad = next((e for e in graph["edges"] if not e.get("satisfied")), None)
    if bad:
        miss = (bad.get("reason") or "").replace("missing:", "").strip("/")
        return f"Так не получается: «{bad['rel']}» здесь не подходит (не хватает: {miss})."

    ru = realize_graph(state, lattice_id, graph, lang="ru")
    en = realize_graph(state, lattice_id, graph, lang="en")
    sim = [r["label"] for r, s in recall_similar(load_memory(state, lattice_id), graph, top=2)
           if s >= 0.5 and r.get("label")]
    persist_situation(state, lattice_id, graph, label=text)  # remember the situation on the field
    note = f" Похоже на: «{sim[0]}»." if sim else ""
    tail = f" (EN: {en})" if en else ""
    return f"Понял: «{ru}».{tail}{note}"
