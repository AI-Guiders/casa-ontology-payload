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
# UI actions apply broadly (you can show / configure / copy / move almost any item), so the
# common capabilities sit on digital_object and every software concept inherits them; the
# narrow ones (savable on files, clickable on controls, installable on apps) stay specific.
# positionable too: a digital object can be located/placed (a file «in» a folder), which
# is what an action's destination («сохрани файл в папку») needs.
_BROAD = ["viewable", "selectable", "configurable", "copyable", "movable", "creatable", "renamable", "positionable"]

SOFTWARE_PACK: dict = {
    "categories": [
        {"id": "digital_object", "isa": [], "affords": _BROAD},
        {"id": "file_item", "isa": ["digital_object"], "affords": ["openable", "savable", "deletable", "editable", "printable"]},
        {"id": "folder_item", "isa": ["digital_object"], "affords": ["openable", "deletable", "containment"]},
        {"id": "ui_control", "isa": ["digital_object"], "affords": ["clickable"]},
        {"id": "window_item", "isa": ["digital_object"], "affords": ["openable", "closable"]},
        {"id": "app_item", "isa": ["digital_object"], "affords": ["openable", "closable", "usable", "installable", "downloadable"]},
        {"id": "toggle_item", "isa": ["digital_object"], "affords": ["toggleable"]},
        {"id": "store_item", "isa": ["digital_object"], "affords": ["containment"]},  # action destinations
        {"id": "addressee", "isa": [], "affords": ["agent"]},  # implicit «you» of an imperative
    ],
    "concepts": {
        "file_item": [["файл", "file"], ["документ", "document"], ["изображение", "image"],
                      ["картинка", "image"], ["палитра", "palette"]],
        "folder_item": [["папка", "folder"], ["каталог", "directory"]],
        "store_item": [["буфер", "clipboard"], ["диск", "disk"], ["корзина", "trash"]],
        "ui_control": [["кнопка", "button"], ["значок", "icon"], ["пиктограмма", "icon"], ["меню", "menu"],
                       ["вкладка", "tab"], ["ссылка", "link"], ["флажок", "checkbox"], ["панель", "toolbar"],
                       ["список", "list"], ["элемент", "item"], ["ярлык", "shortcut"], ["сетка", "grid"]],
        "window_item": [["окно", "window"], ["редактор", "editor"]],
        "app_item": [["приложение", "application"], ["программа", "program"]],
        "toggle_item": [["прокси", "proxy"], ["кэш", "cache"], ["настройка", "setting"],
                        ["опция", "option"], ["параметр", "parameter"]],
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
        {"rel": "show", "arg1": "agent", "arg2": "viewable"},
        {"rel": "configure", "arg1": "agent", "arg2": "configurable"},
        {"rel": "copy", "arg1": "agent", "arg2": "copyable"},
        {"rel": "move", "arg1": "agent", "arg2": "movable"},
        {"rel": "create", "arg1": "agent", "arg2": "creatable"},
        {"rel": "rename", "arg1": "agent", "arg2": "renamable"},
        {"rel": "print", "arg1": "agent", "arg2": "printable"},
        {"rel": "enable", "arg1": "agent", "arg2": "toggleable"},
        {"rel": "install", "arg1": "agent", "arg2": "installable"},
        {"rel": "download", "arg1": "agent", "arg2": "downloadable"},
    ],
}


def teach_software_domain(state: dict, lattice_id: str, *, bundle: dict | None = None) -> dict:
    """Layer the software/UI concepts, affordances and action constraints onto ``state``."""
    from casa.curriculum.concept_net import teach_concept_net

    return teach_concept_net(state, lattice_id, SOFTWARE_PACK, bundle=bundle)
