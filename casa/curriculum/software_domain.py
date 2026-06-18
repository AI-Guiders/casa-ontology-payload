#!/usr/bin/env python3
"""Software / UI domain pack — layered on top of the general conceptual network.

The general ontology has ~4500 everyday nouns but no software concepts and no UI actions.
This pack adds them as a SEPARATE additive layer (teach_concept_net is additive), so the
round-trip / question demo can handle instruction-style sentences — «пользователь
открывает файл», «Открой файл», «Сохрани документ» — and validate them (a button is
clickable, not savable). Domain-by-domain is the deliberate architecture: each real domain
gets its own pack; the general layer is untouched.

The action verbs (open/save/delete/…) live in two canonical places shared with the rest of
the system: surface→relation in ``situation.PREDICATE_RELATION`` and relation→verb (with
Russian 3sg + imperative as a given lexicon) in ``roundtrip._TRANS_VERB``. This module
owns only the ontology (concepts, types/affordances, relation constraints).
"""

from __future__ import annotations

# data shape matches teach_concept_net: {categories:[{id,isa,affords}], concepts:{cat:[[ru,en]]},
# relations:[{rel,arg1,arg2}]}. Affordances are software-specific capabilities.
SOFTWARE_PACK: dict = {
    "categories": [
        {"id": "digital_object", "isa": [], "affords": []},
        {"id": "file_item", "isa": ["digital_object"], "affords": ["openable", "savable", "deletable", "editable"]},
        {"id": "folder_item", "isa": ["digital_object"], "affords": ["openable", "deletable"]},
        {"id": "ui_control", "isa": ["digital_object"], "affords": ["clickable", "selectable"]},
        {"id": "window_item", "isa": ["digital_object"], "affords": ["openable", "closable"]},
        {"id": "app_item", "isa": ["digital_object"], "affords": ["openable", "closable", "usable"]},
        {"id": "addressee", "isa": [], "affords": ["agent"]},  # implicit «you» of an imperative
    ],
    "concepts": {
        "file_item": [["файл", "file"], ["документ", "document"], ["изображение", "image"]],
        "folder_item": [["папка", "folder"], ["каталог", "directory"]],
        "ui_control": [["кнопка", "button"], ["значок", "icon"], ["меню", "menu"],
                       ["вкладка", "tab"], ["ссылка", "link"], ["флажок", "checkbox"]],
        "window_item": [["окно", "window"]],
        "app_item": [["приложение", "application"], ["программа", "program"]],
        "addressee": [["ты", "you"]],
        "person": [["пользователь", "user"]],  # adds isa(user, person); person already affords agent
    },
    "relations": [
        {"rel": "open", "arg1": "agent", "arg2": "openable"},
        {"rel": "close", "arg1": "agent", "arg2": "closable"},
        {"rel": "save", "arg1": "agent", "arg2": "savable"},
        {"rel": "delete", "arg1": "agent", "arg2": "deletable"},
        {"rel": "click", "arg1": "agent", "arg2": "clickable"},
        {"rel": "select", "arg1": "agent", "arg2": "selectable"},
        {"rel": "edit", "arg1": "agent", "arg2": "editable"},
    ],
}


def teach_software_domain(state: dict, lattice_id: str, *, bundle: dict | None = None) -> dict:
    """Layer the software/UI concepts, affordances and action constraints onto ``state``."""
    from casa.curriculum.concept_net import teach_concept_net

    return teach_concept_net(state, lattice_id, SOFTWARE_PACK, bundle=bundle)
