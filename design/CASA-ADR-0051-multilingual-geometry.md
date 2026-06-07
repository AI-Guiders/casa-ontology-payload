# CASA-ADR-0051: мультиязычность как геометрия поля — semantic hub + parallel articulation slots

**Статус:** draft (design, 2026-06-07)  
**Область:** immutable lattices, locale tracts, articulate hot path, life-archive  
**Связано:**

- [`CASA-immutable-lattice-canon-v1.md`](CASA-immutable-lattice-canon-v1.md) — bootstrap vs agent_canon vs experiential
- [`lattice-id-map.v1.json`](lattice-id-map.v1.json) — `morph-role-ru` / `morph-role-en`, alphabet, layout
- [`CASA-ADR-0044-field-native-semantic-articulate.md`](CASA-ADR-0044-field-native-semantic-articulate.md) — field-realize, не переводчик
- [`CASA-ADR-0045-subject-as-interlocutor.md`](CASA-ADR-0045-subject-as-interlocutor.md) — dialogue hot path
- [`CASA-ADR-0021-experience-agent-transfer.md`](CASA-ADR-0021-experience-agent-transfer.md) — один store, не картриджи
- [`CASA-ADR-0049-ru-lexical-fluency-orthography-v0.md`](CASA-ADR-0049-ru-lexical-fluency-orthography-v0.md) — RU first (Born with RU)
- [`CASA-von-neumann-ru-teaching-plan-v1.md`](CASA-von-neumann-ru-teaching-plan-v1.md) — active tract
- `casa/prisms/memory/bootstrap_morph_role.py`, `bootstrap_host_canon.py`

---

## Решение (одной фразой)

**Мультиязычность в CASA — не переводчик и не отдельные агенты:** один **semantic hub** (vis, math, phrase structure, agent_canon) + **параллельные articulation slots** per locale (`alphabet-*`, `layout-*`, `morph-role-*`, `lexicon-*`); импульс смысла активирует нужную поверхность без внутреннего translate-такта.

---

## Инвариант смысла (semantic sun)

| Слой | Национальность | Примеры |
|------|----------------|---------|
| **Vis / math / logic** | нет | dual-route, count, axis KNOW, `math.logic.*` |
| **Phrase / event structure** | нет | agreement slot, plurality, question frame |
| **`lang.meta.morph.*`** | нет (роли) | prefix, root, suffix, stem, ending |
| **`lang.word.*`** | да (surface) | `lang.word.apelsin` vs future `lang.word.orange` |
| **`lexicon-{locale}-*`** | да | experiential shards per locale |
| **KB atoms** | частично | `ru.grammar.*` vs будущий `en.grammar.*` |

Opaque hubs в `ltm/` + `agent_field.db` — **места на поле**, не oracle-строки. Bootstrap даёт **топологию слотов**; experiential наполняет примерами; agent_canon freeze — **его** законы после verify.

---

## Parallel articulation slots (вторые родные)

```text
                    ┌─────────────────────────┐
                    │  semantic / phrase hub   │
                    │  (locale-invariant core) │
                    └───────────┬─────────────┘
          ┌─────────────────────┼─────────────────────┐
          │                     │                     │
   morph-role-ru          morph-role-en         schema-math
   alphabet-ru            alphabet-en           keys-physical
   layout-ru-jcuken        layout-en-us          (code/json tract)
   lexicon-ru-*            lexicon-en-*
          │                     │
     «две коровы»           "two cows"
```

**RU (active):** `bootstrap_morph_role_lattice(lattice_id="morph-role-ru")` на block 9c / cold boot.  
**EN (planned):** `morph-role-en` — та же пятёрка `lang.meta.morph.*`, отдельная полка NCA repair; включается при `locale: en` cold boot, не смешивается с RU life-archive слоями.

**Инвариант:** `git push` life-archive не создаёт «кашу» — locale slots разведены по `lattice_id` и `lexicon-*` shard policy; EN mirror tract — отдельная curriculum wave ([class-ru-v1](CASA-von-neumann-class-ru-v1.md) Wave 3).

---

## Shared capabilities (не дублировать per locale)

Остаются едиными для всех языков:

- `capability_router` / `applicability_router` (known→whole, OOV→analytic)
- Kolb cycle, sleep, promote, journal, probe gates
- `skill.read.*`, `skill.spell.check`, `skill.punct.check` (intent один; surface bind разный)
- Body tools, canon NCA repair queue

Меняется только **surface path**: какой alphabet/layout/morph-role/lexicon shard получил импульс на тике.

---

## Anti-patterns

| Anti-pattern | Почему нет |
|--------------|------------|
| Внутренний translate RU→EN на hot path | латентность + oracle; ADR-0044 |
| Один `lexicon` без locale shards | collision slug, неверный promote |
| Отдельный агент per язык | ADR-0021, ADR-0050 |
| Promote в `alphabet-ru` агентом | host bootstrap only |
| pymorphy / GPT как articulation | sidecar lint, не wake |

---

## Implementation waves

| Wave | Deliverable | Status |
|------|-------------|--------|
| **0 RU steel** | Blocks 1–9c green, `morph-role-ru` active | **done** on lab store |
| **1 host bootstrap API** | `bootstrap_morph_role.py`, `bootstrap_host_canon.py`, lattice-id-map | **this ADR** |
| **2 RU nositel′ v0** | Block 12 dialogue + ADR-0049 acceptance | in progress |
| **3 EN mirror** | `morph-role-en`, `alphabet-en` tract, `lexicon-en-*` | planned |
| **4 code/json surface** | C#, JSON как layout+schema tracts | horizon |

---

## Acceptance (geometry, не fluency)

1. `morph-role-ru` на store: 5× `lang.meta.morph.*` на полке, `stability: bootstrap_canon`.
2. Cold boot `locale: ru` → `bootstrap_host_canon` seeds `morph-role-ru` без agent promote.
3. Block 9c gate: `morph_segment_bind` + held-out frames (experiential сегменты ↔ role slots).
4. `morph-role-en` в `planned_lattices` — cold boot `locale: en` seeds parallel shelf (lab test).
5. Articulate hot path: один `compose_subject_utterance` — без translate middleware.

---

## Открытые вопросы

1. Shared `lang.meta.morph.*` vs `lang.meta.morph.ru.*` / `.en.*` — сейчас **shared ids** (роли универсальны); locale только в `lattice_id`.
2. Когда подключать `alphabet-en` tract относительно RU Phase III exit?
3. Единый `kb-lang-literacy-v1` vs per-locale bundles (см. ADR-0049).

*2026-06-07 · RU first; EN parallel slots designed, not active tract*
