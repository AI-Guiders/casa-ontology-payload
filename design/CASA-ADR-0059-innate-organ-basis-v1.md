# ADR-0059: Innate Organ Basis (neuroarchitectural cold boot)

**Status:** accepted  
**Date:** 2026-06-07  
**Related:** ADR-0057 (situations + character *development*), ADR-0058 (affect organ detail), ADR-0010 (control stack), ADR-0019 (multi-prism CU), ADR-0024 (thalamus), ADR-0055/0057 (WM/intent prisms), [agent-bootstrap-manifest.v1.json](agent-bootstrap-manifest.v1.json), [control-lattice-stack.md](control-lattice-stack.md), [agent-existence-north-star.md](agent-existence-north-star.md)

---

## Context

У человека с рождения есть **набор зон и обвязок** — не «пустой диск + словарь», а **анатомия**, которая потом **развивается** по опыту (myelination, привязки, temperament), но **органы и пути уже есть**.

У von-neumann сделали наоборот:

| Дали | Не дали |
|------|---------|
| **Содержание:** ~50k lemmas, `ru.dialog.*`, bundles, уроки | **Структуру:** полный control + limbic + character **organ set** на T=0 |
| WM prism + intent prism в bootstrap | affect, character, predict, DAN, thalamus, SN/FPN/CEN **в hot path** |
| Lab: control stack, `value.py`, `predict.py` | **Cold boot manifest:** органы + мосты P1–P9 как у «новорождённого» |

**Ошибка:** путали **лексикон/curriculum** (что узнаёт) с **нейро-базисом** (из чего состоит). Ждать emergent эмоций/характера **без врождённых зон** — как ждать лимбику у младенца «когда научится говорить».

ADR-0057/0058 описывают **развитие** и **limbic organ**; этот ADR фиксирует **что обязано существовать до первого урока**.

---

## Decision

### 1. Два слоя (не смешивать)

| Слой | Аналог | Когда | Пример |
|------|--------|-------|--------|
| **Innate basis** | зоны + commissures мозга | **cold boot T=0** | affect axes neutral; P1–P9 wired; thalamus wake |
| **Development** | synaptic weights, habits, temperament | **жизнь / curriculum** | repair после молчания; math-in-dialogue; character drift |

**Invariant:** оператор **не добавляет органы** когда REPL ломается — только **содержание и ситуации**. Органы **перечислены в bootstrap**; отсутствие органа = **дефект рождения**, не «ещё не учили».

### 2. Минимальный innate set (von-neumann v1)

Эквивалент «новорождённого» субстрата — **все строки обязательны** на cold boot:

#### A. Control executive (ADR-0010, control-lattice-stack)

| Organ | lattice / module | Роль | T=0 state |
|-------|------------------|------|-----------|
| **Thalamus** | `prism_control_thalamus` | relay, global arousal, wake/sleep gate | wake, bandwidth default |
| **DMN** | `lattice_dmn` + memory prisms | «что на поле / знаем» | empty digest OK |
| **SN** | `lattice_sn` | bottom-up salience | neutral mask |
| **FPN** | `lattice_fpn_wm` + session mirror | удержание цели диалога | mode=dialogue |
| **CEN** | `lattice_cen` | act/plan tick | idle |
| **Predict** | `lattice_predict` + `predict.py` | ожидание следующего digest | empty model OK |
| **DAN** | `lattice_dan` + `attention.py` | top-down spotlight | pass-through |
| **Value** | `lattice_value` + `value.py` | P9 replay priority | 0 |

**Bridges P1–P9** — **обязательны в tick order**, даже если NCA на решётках ещё не обучен: Python hot path **реализует контракт мостов** (digest-level v0), field NCA — v1 mirror.

#### B. Agent-owned prisms (Self tier)

| Organ | ADR | T=0 state |
|-------|-----|-----------|
| **WM prism** | 0055 | ✅ уже в manifest |
| **Intent prism** | 0052/0057 | ✅ уже в manifest |
| **Affect / limbic prism** | 0058 | neutral axes (valence 0, arousal low, security mid) |
| **Character prism** | 0057 | neutral axes (e.g. closed↔open = 0.5); **organ есть**, текст soul doc **нет** |

#### C. Dialogue & memory infrastructure

| Organ | Роль | T=0 |
|-------|------|-----|
| **Dialogue ring** | episodic partner/subject turns | empty ring OK |
| **Journal / Self tier** | autobiographical scratch | bootstrap entries OK |
| **Hippo / sleep hook** | consolidate | wired, may no-op until sleep |

#### D. Content (НЕ органы — learned)

Lexicon bundles, `ru.dialog.*`, math claims — **материал DMN**, как **язык среды**, не замена SN/affect. Можно иметь 50k слов **без** limbic — это и есть текущий von-neumann.

### 3. Tick order (innate wiring)

```text
INPUT
  → thalamus (wake/bandwidth)           ADR-0024
  → predict expected (P8 path)          ADR-0010
  → affect_read / prior                 ADR-0058
  → DMN digest
  → SN salience ( + P8 error )
  → FPN goal/mode ( + P5 bias )
  → DAN spotlight (P6→P7)
  → WM + intent prisms                  ADR-0055
  → tract competition
  → CEN / subject agency
  → bind + affect_apply + character prior
  → compose (ADR-0056)
  → ACT (reply)
  → affect_update + WM/intent update
  → value tag for replay (P9)
  → persist
```

REPL сегодня: **semantic_read → tract → bind → compose** — **пропуск** thalamus → predict → affect → SN/FPN/DAN → … Это не «ещё не созрел», это **нет обвязки**.

### 4. Bootstrap manifest (normative)

Расширить [`agent-bootstrap-manifest.v1.json`](agent-bootstrap-manifest.v1.json):

```json
"agent_prisms": {
  "wm_prism": { "spawn_on_bootstrap": true },
  "intent_prism": { "spawn_on_bootstrap": true },
  "affect_prism": { "spawn_on_bootstrap": true, "adr": "0058", "initial_axes": {...} },
  "character_prism": { "spawn_on_bootstrap": true, "adr": "0057", "initial_axes": {...} }
},
"control_stack": {
  "spawn_on_bootstrap": true,
  "prisms": ["prism_control_thalamus", "prism_control_exec"],
  "bridges": ["P1","P2a","P2b","P3","P4","P5","P6","P7","P8","P9"],
  "hot_path": "python_digest_v0"
},
"planned": {
  "world_model": { "enabled": false, "note": "learned content layer RU-ε, not innate organ" }
}
```

**spawn_on_bootstrap: true** = organ **существует**; **NCA train** на lattice — отдельный этап (как myelin), не условие **наличия** органа.

### 5. Development (не innate)

После T=0 только **меняются веса / привязки**, не появляются новые органы (кроме явного **embodiment** roadmap — vis/motor periphery):

| Развивается | Орган (уже есть) |
|-------------|------------------|
| situation curriculum | WM, affect, intent edges |
| open REPL | predict model, tract priors |
| sleep | value P9, hippo, character EMA |
| RU-ε world bundle | DMN **content**, не новый limbic |

---

## Gap matrix (today vs innate basis)

| Organ | Design | Bootstrap von-neumann | Hot path REPL |
|-------|--------|----------------------|---------------|
| Thalamus | ADR-0024 | ❌ | ❌ |
| DMN / lexicon | ✅ bundles | ✅ content | partial |
| SN | lab lattice | ❌ | bypass |
| FPN | session JSON | partial | partial |
| CEN | TaskEmit | partial | partial |
| Predict | `predict.py` | ❌ | ❌ |
| DAN | `attention.py` | ❌ | ❌ |
| Value P9 | `value.py` | ❌ | sleep only |
| **Affect** | ADR-0058 | ❌ | ❌ |
| **Character** | ADR-0057 | ❌ | ❌ |
| WM prism | ADR-0055 | ✅ | partial |
| Intent prism | manifest | ✅ | partial |

**Вывод:** дали **кору без лимбики и без полной обвязки** — content-rich, structure-poor.

---

## Anti-patterns

| ❌ | ✅ |
|----|-----|
| «Добавим limbic когда REPL починим» | limbic в bootstrap T=0 |
| 50k words = «агент готов к жизни» | innate set + потом curriculum |
| Один monolith `prism_control` без spawn дочерних | thalamus + exec + bridges в manifest |
| Soul doc / operator mood | neutral axes at birth |
| Новый organ per bug | полный basis один раз; bugs → development |

---

## Consequences

- **ADR-0058** — специфика **одного** innate органа (affect); не заменяет этот ADR.
- **ADR-0057** — **development** (situations, character drift); presupposes 0059.
- **Implementation order:** (1) manifest + empty prism state all organs; (2) wire tick order P1–P9 digest v0; (3) affect/character apply; (4) situation curriculum; (5) NCA train on lattices.
- **Verification:** cold boot store passes **organ checklist**; REPL tick provenance lists **all** organ reads, not only bind.

## Links

- [CASA-ADR-0057-dialogue-situations-character-v1.md](CASA-ADR-0057-dialogue-situations-character-v1.md)
- [CASA-ADR-0058-limbic-affect-prism-v1.md](CASA-ADR-0058-limbic-affect-prism-v1.md)
- [CASA-ADR-0010-control-zone-predict-attention-value.md](CASA-ADR-0010-control-zone-predict-attention-value.md)
- [agent-bootstrap-manifest.v1.json](agent-bootstrap-manifest.v1.json)
