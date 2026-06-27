# CASA Design Navigator v1

**Status:** living index — **вход в `design/`** (не ADR)  
**Date:** 2026-06-21  
**Provenance:** Света + агент — после feedback Димы Ратнера: «с агентом не разобрались в документах, их слишком много» (Concept Zone не использовали)

**Связано:** [CASA-PROJECT-CONSTITUTION.md](CASA-PROJECT-CONSTITUTION.md), [agent-existence-north-star.md](agent-existence-north-star.md), [TECH-DEBT-INDEX.md](TECH-DEBT-INDEX.md), [CASA-scratch-track-integration-v1.md](CASA-scratch-track-integration-v1.md)

---

## С чего начать (60 секунд)

| Вопрос | Читай первым | Не читай сначала |
|--------|--------------|------------------|
| **Зачем CASA вообще?** | [CASA-PROJECT-CONSTITUTION.md](CASA-PROJECT-CONSTITUTION.md) | 200 файлов ADR подряд |
| **Что такое «живой агент»?** | [agent-existence-north-star.md](agent-existence-north-star.md) | философия квалиа |
| **Два трека в репо (listen vs meaning)?** | [CASA-scratch-track-integration-v1.md](CASA-scratch-track-integration-v1.md) | только `develop` diff |
| **Concept Zone vs понятийная сеть Димы?** | **§ ниже** + [CASA-ADR-0085](CASA-ADR-0085-concept-zone-built-in-vs-earned-theories.md) | [CASA-ADR-0073](CASA-ADR-0073-concept-layer-lexicalization.md) **в одиночку** |
| **Listen / Lalabook pilot?** | [CASA-scratch-listen-wire-gap-v1.md](CASA-scratch-listen-wire-gap-v1.md) | curriculum ROADMAP |
| **Связность эпизодов / понимание после FSR?** | [CASA-ADR-0088](CASA-ADR-0088-hippocampus-quad-mode-episodic-connectivity.md) | только `run_sleep` без wake/integrate |
| **Субстрат / impulse — картина, не JSON?** | [CASA-ADR-0087](CASA-ADR-0087-substrate-visualizer-v1.md) + [0080](CASA-ADR-0080-impulse-trace-v1.md) | сырой `impulse_trace.jsonl` |
| **Геном / размножение / погода?** | [CASA-ADR-0084](CASA-ADR-0084-wild-genome-donor-single-agent-reproduction.md), [0086](CASA-ADR-0086-epigenome-expression-layer.md) (epigenome) | весь 0061–0076 |
| **Техдолг / M* / R* id?** | [TECH-DEBT-INDEX.md](TECH-DEBT-INDEX.md) | случайные ADR |

**Правило для агента:** если задача про **X**, открой **одну** строку таблицы выше → только Related из того файла → не grep весь `design/`.

---

## Классификация документов

| Тип | Имя / префикс | Сила | Когда устаревает |
|-----|----------------|------|------------------|
| **Constitution / north star** | `CASA-PROJECT-CONSTITUTION`, `agent-existence-north-star` | **зачем** проект | редко |
| **ADR** | `CASA-ADR-NNNN-*.md` | normative **как** (если accepted) | supersede новым ADR |
| **Scratch** | `CASA-scratch-*` | рабочий план, wire-gap, интеграция треков | после закрытия — архив / ссылка в ADR |
| **Navigator / index** | `CASA-DESIGN-NAVIGATOR`, `TECH-DEBT-INDEX` | карта | при новом треке |
| **Dima / curriculum RU** | `ПОНЯТИЙНАЯ-*`, `КУРРИКУЛУМ-*`, `ВАЛИДАТОР-*`, `ROADMAP-понятийная-*` | lab + teach **meaning** | sync с `develop` |
| **School / RU class** | `CASA-von-neumann-*-ru-*`, `CASA-cefr-*` | педагогика оператора | отдельно от hot path |
| **JSON / manifest** | `agent-bootstrap-manifest`, `kb-*.json`, `genetic-*-points` | machine contract | с ADR |
| **Audit / debt** | `CASA-code-audit`, `РЕКОМЕНДАЦИИ-Von-Neumann` | внешний взгляд | point-in-time |

**Не смешивать:** scratch ≠ ADR. RU roadmap Димы ≠ Concept Zone ADR.

---

## Concept Zone ≠ Curriculum — главная путаница (postmortem)

Три разных слоя; **имена похожи — роли разные**:

| Слой | Документ / код | Что это | Что **не** это |
|------|----------------|---------|----------------|
| **Concept Zone** | ADR-0073, **0085**, `concept_layer.py` | **полка** `domains.concept`: **Built-In** + **Self-Earned** theories | **не** 4-hub glue как финал; **не** отдельная OntologyZone |
| **Built-In (curriculum)** | `concept_net.py`, ADR-0083, **0085** | species `concept.*` @ T=0 + type graph | **не** earned agency; **не** `schema-math` |
| **Self-Earned** | promote_canon, **0085** §4 supersede | novel hub + исправление Built-In после gate | **не** hot_write bootstrap |
| **Chat `/meaning` lab** | `build_meaning_state()` | ephemeral demo | **не** life tick; **не** character store default |

**Почему Дима не «использовал Concept Zone» — часто норма:** curriculum teach шёл в **lab harness** (`LATTICE = schema-math`) — это **ошибка placement**, не «забыли 0073». См. ADR-0083 § Postmortem.

**Куда teach curriculum на store (normative):** Built-In tier @ `domains.concept` — [ADR-0085](CASA-ADR-0085-concept-zone-built-in-vs-earned-theories.md); C0 lattice: ADR-0083 § Decision.

```text
Concept Zone (0085)     = Built-In (curriculum concept.*) + Self-Earned (promote/supersede)
Curriculum teach        = Built-In neurons + agent-concept-graph (не side-lex forever)
Listen imprint (0028)   = A/V опыт → позже edges на concept.*
```

---

## Треки (параллельные ветки / команды)

```text
                    CASA-PROJECT-CONSTITUTION
                              │
        ┌─────────────────────┼─────────────────────┐
        ▼                     ▼                     ▼
   Substrate/zones      Listen/motor           Meaning/curriculum
   0061–0076, 0062      scratch-listen-*       ADR-0083, ПОНЯТИЙНАЯ-*,
   north-star            ADR-0028, 0081         ВАЛИДАТОР-*, develop
        │                     │                     │
        └─────────────────────┴─────────────────────┘
                              │
                    merge gate: placement checklist
                    (ADR-0083, playbook process-debt)
```

| Трек | Владелец (типично) | Entry doc |
|------|-------------------|-----------|
| **Life tick / sensory** | оператор + listen | [CASA-scratch-listen-wire-gap-v1.md](CASA-scratch-listen-wire-gap-v1.md) |
| **Motor / speech** | оператор | [CASA-scratch-motor-speech-wire-gap-v1.md](CASA-scratch-motor-speech-wire-gap-v1.md) |
| **Meaning / validator** | Дима + агент | [ВАЛИДАТОР-СМЫСЛА-статус-и-план.md](ВАЛИДАТОР-СМЫСЛА-статус-и-план.md) |
| **Curriculum / Concept @ store** | оператор + Дима | [CASA-ADR-0085](CASA-ADR-0085-concept-zone-built-in-vs-earned-theories.md) → [0083](CASA-ADR-0083-curriculum-ontology-agent-store.md) |
| **Genetics / fork** | оператор | [CASA-ADR-0062](CASA-ADR-0062-genetic-zone.md) → [0084](CASA-ADR-0084-wild-genome-donor-single-agent-reproduction.md) → [0086](CASA-ADR-0086-epigenome-expression-layer.md) |
| **Integration / git** | оба | [CASA-scratch-track-integration-v1.md](CASA-scratch-track-integration-v1.md) |

---

## ADR по «этажам» (укороченный каталог)

Полный список: `design/CASA-ADR-*.md`. Ниже — **этажи**, не хронология.

| Этаж | ADR (примеры) | Тема |
|------|---------------|------|
| **0 — память / поле** | 0002, 0014, 0016 | LTM, agent prism |
| **1 — tick / control** | 0010, 0024, 0055, 0057 | executive, WM, intent |
| **2 — zones** | 0061, 0060, 0063, 0064, 0068–0071 | intelligence zones |
| **3 — genetic** | 0062, 0065, 0072, **0084**, **0086** | genome, fork, epigenome, entropy |
| **3b — observability** | **0080**, **0087** | impulse trace, substrate dashboard |
| **4 — partner / speech** | 0078, 0081, 0056 | efferent, slots |
| **5 — sensory** | 0028, scratch-listen | imprint, stream |
| **6 — concept / curriculum** | 0073, **0085**, 0083 | Built-In / Self-Earned; teach @ store |
| **7 — episodic connectivity** | **0088**, 0047, 0009, 0023 | hippo_wake + consolidate + integrate + idle_micro |
| **7 — runtime** | 0079, 0025 | host, engine tier |

---

## Scratch-реестр (активные)

| Файл | Назначение |
|------|------------|
| [CASA-scratch-track-integration-v1.md](CASA-scratch-track-integration-v1.md) | мы / Дима / develop / cherry-pick |
| [CASA-scratch-listen-wire-gap-v1.md](CASA-scratch-listen-wire-gap-v1.md) | listen Phase B checklist |
| [CASA-scratch-listen-0027-layer-map-v1.md](CASA-scratch-listen-0027-layer-map-v1.md) | sensory layers |
| [CASA-scratch-motor-speech-wire-gap-v1.md](CASA-scratch-motor-speech-wire-gap-v1.md) | motor efferent |
| [CASA-scratch-digital-biology-borrowings-v1.md](CASA-scratch-digital-biology-borrowings-v1.md) | evo-biology ideas (обсудить) |

---

## KB (agent-notes) — зеркало для людей

| Тема | Путь |
|------|------|
| Operator thesis: проживание, СТОП | `ca-substrate-agent/note-casa-lived-experience-stop-continuity-v1.md` |
| Wild genome / entropy | `note-casa-synthetic-genome-donor-v1.md` |
| Process debt @ merge | `domains/agent-operations/playbook-agent-process-debt-amplifier-v1.md` |
| Цели CASA | `ca-substrate-agent/casa-goals-and-roadmap-v1.md` |

---

## Как не утонуть (для человека + агента)

1. **Один вопрос → один entry** из таблицы «С чего начать».
2. **Related** в ADR — лимит расширения контекста (не transitive closure всего design/).
3. **Scratch** для процесса; **ADR** для решений; не повышать scratch до канона без ADR.
4. **Merge / teach** — checklist ADR-0083 + process-debt playbook **до** «зелёные тесты».
5. Новый документ → **добавить строку** в этот navigator (PR habit).

---

## Open

- [ ] Авто-генерация списка ADR из `design/` (script) — optional
- [ ] `design/README.md` stub → только ссылка сюда
- [ ] Dima sync: пройти § Concept Zone вместе с `ВАЛИДАТОР` + 0083
