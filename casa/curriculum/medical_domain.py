#!/usr/bin/env python3
"""Medical-label domain pack — the validator's target domain (EMEA/IFU text).

Same additive architecture as the software pack: concepts + types/affordances + relation
constraints for the vocabulary that medicine labels actually use. The scope is DATA-DRIVEN:
the concept list is the frequency head of the filtered EMEA en-es pool (dose/dosis 4.3k,
contains/contiene 2.9k, tablet/comprimido, solution, vial, syringe, patient, doctor, …).

Verb surfaces live in the canonical tables (``situation.PREDICATE_RELATION`` for RU/EN,
``PREDICATE_RELATION_ES`` for Spanish); this module owns the ontology and the Spanish
names of its concepts (tagged edges — see ``concept_net.teach_names``).
"""

from __future__ import annotations

MEDICAL_PACK: dict = {
    "categories": [
        # things one takes/gives: tablets contain substances, so containment sits here too
        {"id": "medicine_item", "isa": ["physical_object"], "affords": ["containment"]},
        {"id": "med_container", "isa": ["physical_object"], "affords": ["containment"]},
        {"id": "med_tool", "isa": ["physical_object"], "affords": []},
        {"id": "med_substance", "isa": ["physical_object"], "affords": []},
        {"id": "body_part", "isa": ["physical_object"], "affords": []},
        # a dose is measured («la dosis es de 75 mg») and taken («tome la dosis»)
        {"id": "dose_item", "isa": ["abstract"], "affords": ["measurable", "ownable"]},
        {"id": "med_event", "isa": ["abstract"], "affords": []},
        # something a product may require («no special storage conditions» boilerplate)
        {"id": "med_condition", "isa": ["abstract"], "affords": ["ownable"]},
    ],
    "concepts": {
        "medicine_item": [["лекарство", "medicine"], ["таблетка", "tablet"], ["капсула", "capsule"],
                          ["препарат", "drug"], ["инсулин", "insulin"], ["раствор", "solution"],
                          ["порошок", "powder"], ["суспензия", "suspension"], ["крем", "cream"],
                          ["мазь", "ointment"], ["капля", "drop"]],
        # NB: «package» is NOT a separate concept — EMEA pairs use package/carton/envase/
        # embalaje interchangeably for the same thing, so one packaging concept (extra
        # names taught below) keeps equivalent pairs equivalent
        "med_container": [["флакон", "vial"], ["шприц", "syringe"], ["упаковка", "carton"],
                          ["бутылка", "bottle"], ["блистер", "blister"], ["холодильник", "refrigerator"]],
        "med_tool": [["игла", "needle"]],
        "med_substance": [["лактоза", "lactose"], ["натрий", "sodium"], ["алкоголь", "alcohol"],
                          ["кальций", "calcium"], ["витамин", "vitamin"]],
        "body_part": [["кровь", "blood"], ["кожа", "skin"], ["рот", "mouth"], ["желудок", "stomach"]],
        "dose_item": [["доза", "dose"]],
        "med_condition": [["условие", "condition"]],
        "med_event": [["лечение", "treatment"], ["беременность", "pregnancy"], ["лактация", "lactation"],
                      ["инъекция", "injection"], ["инфузия", "infusion"], ["введение", "administration"],
                      ["эффект", "effect"], ["реакция", "reaction"], ["симптом", "symptom"],
                      ["болезнь", "disease"]],
        "person": [["пациент", "patient"], ["фармацевт", "pharmacist"], ["медсестра", "nurse"]],
    },
    "relations": [
        # «the vial contains solution», «el comprimido contiene lactosa» — NOT ownership
        # (base «has» wants an agent), a container/composition claim
        {"rel": "contains", "arg1": "containment", "arg2": "positionable"},
        # «store the tablets …», «conserve los comprimidos …» — keeping, label-imperative
        {"rel": "store", "arg1": "agent", "arg2": "positionable"},
        # «this product does not require special storage conditions» — label boilerplate
        {"rel": "require", "arg1": "positionable", "arg2": "ownable"},
    ],
}

# Spanish names of the pack's concepts (tagged lang.word.es.* edges) + the Spanish names
# of a few BASE concepts this domain constantly touches (doctor, child, food are in the
# general layer; their ES surfaces belong to the domain vocabulary).
ES_NAMES_MED: dict[str, list[str]] = {
    "concept.medicine": ["medicamento", "medicina", "producto"], "concept.tablet": ["comprimido", "tableta"],
    "concept.capsule": ["cápsula", "capsula"], "concept.drug": ["fármaco", "farmaco"],
    "concept.insulin": ["insulina"], "concept.solution": ["solución", "solucion"],
    "concept.powder": ["polvo"], "concept.suspension": ["suspensión", "suspension"],
    "concept.cream": ["crema"], "concept.ointment": ["pomada"], "concept.drop": ["gota"],
    "concept.vial": ["vial"], "concept.syringe": ["jeringa", "jeringuilla"],
    "concept.carton": ["envase", "caja", "embalaje", "paquete"], "concept.bottle": ["botella", "frasco"],
    "concept.blister": ["blíster", "blister"], "concept.refrigerator": ["nevera", "refrigerador"],
    "concept.needle": ["aguja"],
    "concept.lactose": ["lactosa"], "concept.sodium": ["sodio"], "concept.alcohol": ["alcohol"],
    "concept.calcium": ["calcio"], "concept.vitamin": ["vitamina"],
    "concept.blood": ["sangre"], "concept.skin": ["piel"], "concept.mouth": ["boca"],
    "concept.stomach": ["estómago", "estomago"],
    "concept.dose": ["dosis"],
    "concept.condition": ["condición", "condicion", "condiciones"],
    "concept.treatment": ["tratamiento"], "concept.pregnancy": ["embarazo"],
    "concept.lactation": ["lactancia"], "concept.injection": ["inyección", "inyeccion"],
    "concept.infusion": ["perfusión", "perfusion", "infusión", "infusion"],
    "concept.administration": ["administración", "administracion"],
    "concept.effect": ["efecto"], "concept.reaction": ["reacción", "reaccion"],
    "concept.symptom": ["síntoma", "sintoma"], "concept.disease": ["enfermedad"],
    "concept.patient": ["paciente"], "concept.pharmacist": ["farmacéutico", "farmaceutico"],
    "concept.nurse": ["enfermera", "enfermero"],
    # base-layer concepts frequent on labels
    "concept.doctor": ["médico", "medico", "doctor", "doctora"],
}


def teach_medical_domain(state: dict, lattice_id: str, *, bundle: dict | None = None) -> dict:
    """Layer the medical-label concepts, affordances and relation constraints onto ``state``,
    plus the Spanish names of the domain vocabulary (tagged edges)."""
    from casa.curriculum.concept_net import teach_concept_net, teach_names

    counts = teach_concept_net(state, lattice_id, MEDICAL_PACK, bundle=bundle)
    teach_names(state, lattice_id,
                [(cid, s) for cid, surfaces in ES_NAMES_MED.items() for s in surfaces], lang="es")
    # EMA register: «(medicinal) product» is the medicine itself — an alias, not a concept;
    # «package/пачка» are extra names of the ONE packaging concept (see MEDICAL_PACK note)
    teach_names(state, lattice_id, [("concept.medicine", "product"),
                                    ("concept.carton", "package"), ("concept.carton", "пачка")])
    return counts
