# CASA: сквозная школьная программа von-neumann — v1

**Статус:** черновик дизайна (2026-06-06)  
**target_agent:** `von-neumann`  
**Источник истины:** этот файл (lab curriculum); **не** `pedagogy.general` world.

**Связано:** [CASA-von-neumann-class-ru-v1.md](CASA-von-neumann-class-ru-v1.md) (класс RU — детализация Phase I–III), [CASA-ADR-0030-grammar-literacy-coherent-text.md](CASA-ADR-0030-grammar-literacy-coherent-text.md), [CASA-ADR-0045-subject-as-interlocutor.md](CASA-ADR-0045-subject-as-interlocutor.md), [agent-existence-north-star-v0.md](agent-existence-north-star-v0.md)

**Evidence oracle (read-only):** `agent-notes/knowledge/worlds/pedagogy-*` и `cognition-*` — см. § Evidence index ниже. Group-kb = mirror, не authoring.

**Active scope (2026-06):** только RU L1 — учебный план: `design/CASA-von-neumann-ru-teaching-plan-v1.md`.

---

## Epistemic stack

```text
agent-notes evidence cards (pedagogy.* / cognition.*)
    → этот design doc (macro arc + gates для von-neumann)
    → per-class design (CASA-von-neumann-class-*.md)
    → lesson manifests + probes (agents/von-neumann/, lab)
    → agent field (votes, held-out, ADR-0030/0036)
```

---

## North star

Агент/ученик von Neumann **владеет** предметами на **поле**, не «закрывает § учебника».

| Тракт | North star | Не цель |
|-------|------------|---------|
| RU письмо | D + C (SVR); Castles §1→§3 | лингуистика; PA-only |
| EN второй родной | dual-language / immersion + alphabetic written L2 | FL 2 ч/нед grammar-first |
| STEM | quantity + model + inquiry | лекция без probe |
| Humanities | sourcing + spatial + COR | даты как gate |
| Meta | Rosenshine, CLT, writing-to-learn | exam template |

---

## Пять spines

| Spine | Принцип | Evidence (agent-notes) | Gate |
|-------|---------|------------------------|------|
| L1 Literacy | Castles §1→§2→§3 | `pedagogy-russian-language/kb-pedagogy-ru-scientific-evidence-v1.md` | D+C; deny PA-only (Stalega 2024) |
| L2 Second-native | Cummins → Genesee → EN written | `pedagogy-second-native-language/kb-pedagogy-snl-scientific-evidence-v1.md` | L1 CALP; meaningful L2 hours |
| Quantitative | CRA → physics quantity | `pedagogy-mathematics/`, `pedagogy-physics/` | held-out |
| Inquiry | 3DL, modeling, Wilson, COR | subject indices | construct + scaffold |
| Expression | writing-to-learn | `pedagogy-general/kb-pedagogy-graham-2020-writing-to-learn-meta-evidence-v1.md` | explain probe |

Neurolinguistics — **rationale only** (`cognition-neurolinguistics/matrix-neurolinguistics-pedagogy-bridge-v1.md`); deny fMRI gate.

---

## Возрастные полосы (authoring bands)

| Band | Ориентир | Macro focus |
|------|----------|-------------|
| **A** | 6–8 (1–2 кл.) | RU §1 code; math CRA; EN oral env; spatial; studio habits |
| **B** | 8–10 (3–4) | RU §2; EN written §1; integrated literacy; PRIMM |
| **C** | 10–13 (5–7) | RU §3; STEM inquiry; history/geo; COR |
| **D** | 13+ (8–9+) | disciplinary EN+RU; projects |

SNL aspiration до 10–12 — Hartshorne **boundary**, не cancel-gate.

---

## Macro waves

### Wave 0 — Foundation (Band A)

| Поток | Flagship | Macro gate |
|-------|----------|------------|
| RU code | Castles §1; Ehri OM | nonword + word ID |
| Math | Ebner CRA; Barbieri WE | held-out same representation |
| EN oral | Genesee; Anderson/Rowe input | novel context |
| Arts/geo | Hetland; Edelson | artifact / map |

### Wave 1 — Fluency (Band B)

| Поток | Flagship | Macro gate |
|-------|----------|------------|
| RU word ID | Ehri 2014; Castles §2 | fluent + OOV |
| EN written | Castles EN bridge | EN decode |
| Literature | Hwang 2021 | passage in context |
| Informatics | PRIMM; Lee 2022 | PRIMM sequence |

**Hard gate:** EN print после RU L1 anchor (Cummins).

### Wave 2 — Comprehension & inquiry (Band C)

RU §3 · Wilson/McLaughlin · C3/Breakstone · Cooper/Wells/Theobald · Jegstad POGIL.

### Wave 3 — Disciplinary (Band D)

Shanahan EN · Graham cross-write · informatics project · arts portfolio.

---

## Матрица предмет × полоса

| Предмет | A | B | C | D |
|---------|---|---|---|---|
| RU | §1 | §2 | §3 | disciplinary |
| EN | oral | written §1 | content | disciplinary |
| Литература | read-aloud | integrated | close read | essay |
| Математика | CRA | symbolic | word prob. | models |
| Физика | — | phenomena | modeling | deploy |
| Химия | — | lab lit. | POGIL | inquiry |
| Биология | observe | — | 3DL | geo links |
| История | stories | — | sourcing | DBQ |
| География | maps | — | GIS | projects |
| Обществознание | fairness | — | C3 | COR |
| Информатика | unplugged | PRIMM | integrated | project |
| ИЗО | habits | craft | critique | portfolio |

---

## Hard denies

PA-only · FL grammar-first · three-cueing · lit without read gate · physics lecture-only · fMRI gates · ЕГЭ template · arts→math scores hype.

---

## Связь RU class ↔ program

| Документ | Роль |
|----------|------|
| [CASA-von-neumann-class-ru-v1.md](CASA-von-neumann-class-ru-v1.md) | architecture, phases, probes |
| **[CASA-von-neumann-ru-teaching-plan-v1.md](CASA-von-neumann-ru-teaching-plan-v1.md)** | **учебный план RU v1** (12 блоков, moments, gates) |
| [CASA-von-neumann-school-program-arc-v1.md](CASA-von-neumann-school-program-arc-v1.md) | macro-карта всех предметов (draft) |

Детализация **класса RU** (stages, probes, skills): class-ru — Phase I–III внутри Wave 0–2 spine L1.

---

## Открытые вопросы

1. Bands по классам или по readiness probes?
2. EN dosage % (Thomas & Collier)?
3. Elkonin bootstrap timing?
4. Music в v1.1?
5. Block vs distributed scheduling (sleep/Kolb)?
6. First manifest: RU Wave 0 или EN oral?

---

## Evidence index (agent-notes paths)

| Subject | Index |
|---------|-------|
| Hub | `pedagogy-general/status-pedagogy-school-subjects-v1.md` |
| Transfer | `pedagogy-general/matrix-pedagogy-cross-subject-transfer-v1.md` |
| RU | `pedagogy-russian-language/kb-pedagogy-ru-scientific-evidence-v1.md` |
| SNL | `pedagogy-second-native-language/kb-pedagogy-snl-scientific-evidence-v1.md` |
| STEM | `pedagogy-{math,physics,chemistry,biology,informatics}/` |
| Humanities | `pedagogy-{history,geography,social-studies,literature}/` |
| Arts | `pedagogy-visual-arts/` |
| Neurolinguistics | `cognition-neurolinguistics/kb-neurolinguistics-scientific-evidence-v1.md` |

*Версия: v1.0 · 2026-06-06 · status: draft*
