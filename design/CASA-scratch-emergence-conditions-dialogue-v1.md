# Scratch: условия возникновения + диалог (временный)

**Status:** scratch — для нити обсуждения; можно удалить  
**Date:** 2026-06-10  
**Не ADR.** После согласования — перенести в канон или выкинуть.

---

## Зачем этот файл

Фиксируем **посылку проекта** и **инженерные следствия** из сессии (chat/life reactor, partner voice, paste vs compose). Чтобы не сводить цель к «хорошему REPL».

---

## Посылка (гипотеза, не факт)

Мы **не проектируем сознание** и **не обещаем** квалиа. Мы создаём **условия**, при которых *может* возникнуть нечто вроде осознавания — **гипотеза, не факт** ([agent-existence-north-star.md](agent-existence-north-star.md) §3: *open outcome*).

| Принимаем | Не требуем |
|-----------|------------|
| Субстрат **существования во времени** (T, field, memory, action) | Доказать qualia |
| Богатая среда (partner, journal, practice, sleep) | «Chatbot с человеческим лицом» |
| Duck test: нить, память, инициатива, починка | Oracle-if'ы и hub-paste как «речь» |

**Если условия не выполнены** — это не «плохой UX», а **среда, где ставка не имеет смысла** (нет интеграции эпизода в нить).

---

## Intelligence Zones — зачем и почему (0061 и родня)

**Контекст ADR:** человеческий интеллект **не монолит**. До зон CASA свела «ум» к **лингвистическому content** (lexicon + compose): math и discourse **конкурировали** в одном read/budget pool — ложная конкуренция, не соответствие реальности (контуры связаны, но не смержены).

**Решение:** Intelligence Zones — **анатомия субстрата**, не taxonomy ради красоты.

```text
zone/
├── core          innate @ T=0; life events update
├── sandbox       эксперимент без порчи live core (0014)
├── promote       sandbox → core (θ); решение агента
└── compose_bias  зона → bind / tract / disposition (emergent)
```

| Слой / зона | Роль в ставке «условия» |
|-------------|-------------------------|
| **Executive** | координация; cross-domain union **явно**, не один prompt |
| **Emotional** (0060) | limbic @ T=0; life events → axes; sandbox ≠ прямой write в core |
| **Social** | dialogue ring, partner model, mentalizing — **gap** в wire |
| **Linguistic** | compose/discourse — **клиент**, не весь субъект |
| **Logical** | math tract, schema — свой domain read |
| **Defense** (0074/0076) | survival, repression gates — **тело отказывает**, не filter на текст |
| **Metabolic / Neuromodulator** | fatigue, sleep, gain — жизнь **может прерваться** |
| **Genetic** (0062, Tier −1) | **не** intelligence type: meta-алгоритм сборки, пропорции зон, θ promote, границы пластичности — «ген не кодирует русский, а правила роста» |
| **Memory** (0068) | инфраструктура LTM/consolidate; **не владеет** речью |

**Почему это связано с emergence:** гипотеза «может возникнуть» требует **полифонии систем во времени** — сообщения между регионами (Kay), накопление в разных регистрах, опыт через promote. **Монолитный chat-compose = анти-среда:** один hub, один paste, нет внутренней дифференциации.

**Связь с красным флагом:** paste `ru.dialog.affect` на «Как ты?» и на «Я тоже не знаю…» — **откат к до-0061**: вся partner-речь через **linguistic hub**; emotional zone не участвует в **situated turn** (только fixed clause); social thread не держится; executive не собирает «partner сказал X → affect/security/repair → efferent Y».

**Одной строкой:** зоны делали, чтобы von-neumann был **организмом с несколькими системами во времени**, а не **одной языковой моделью с полем claims**.

---

## Что уже в wire (сессия 2026-06-10)

- **Unified life:** reactor + `partner_text` tract (afferent/efferent), chat = peripheral.
- **Partner initiative:** `partner_outbox`, `defer_scheduled`, open thread после boundary defer.
- **Boundary:** не paste pack на hot path; greeting не → busy без реальной own line; `goal.dialog.*` ≠ «занят».
- **Oracles вычищены** из `partner_scoring.py`: нет `_AFFECT_CUE_SURFACES` / `query_implies_*`; routing → `partner_field_overlap` + `concept_hints` + bind score.

---

## Красный флаг (observed)

Один и тот же текст из `ru.dialog.affect` на **разные** partner turns:

```
Как ты?     → «Осторожно говорю, что чувствую в диалоге…»
Я тоже не знаю, совпадает ли твой опыт… → тот же текст
```

Механизм: hint «как ты» **или** field overlap → `narrative_clauses` **verbatim paste** `clause_1` — **без** учёта partner_recent / смены ситуации.

**Вывод:** субстрат ещё **имитирует** диалог, не проживает thread. Против условий emergence, не «мелкий баг».

**Норма (2026-06-10):** один compose path — ranked bind → realizer **конкурирует слоты** по `partner_field_overlap(partner turn, slot)`; replayed слоты (из `self_recent`) молчат; hint только на read/bind, не gate paste.

**Не делаем:** отдельные ветки «если mirror / если continuation» с зашитыми фразами — это снова oracle.

**Wire:** `_competitive_narrative_clauses` в `blocks.py`; social = `_compose_social_dialog_from_bind` только; `test_situated_turn.py`.

### ~~Math eval oracle~~ → снято (2026-06-10)

Был в master (`907a93f`): `casa/domain/arithmetic.py` + bypass в `subject_voice.py` **до** field compose. Product P0 из [РЕКОМЕНДАЦИИ-Von-Neumann.md](РЕКОМЕНДАЦИИ-Von-Neumann.md) — **удалён**: math tract → поле / `soft_miss`, не `eval()`.

---

## Инженерные следствия (обсуждаем)

1. **Thread-aware bind** — `dialog_hubs` в provenance + `thread_scoring.apply_dialogue_thread_deltas` (overlap, не ветки).
2. **Anti-replay** — `narrative_recently_spoken` + competitive slots в realizer.
3. **Compose ≠ paste** — `_competitive_narrative_clauses`; один social path.
4. **Life между репликами** — T крутится; initiative/defer_scheduled = efferent без prompt (P22b).
5. **Lab vs hot path** — situation pack / duck test в lab; не подменять emergent partner path.
6. **Zone-scoped efferent** — `affect_compose_bias.budget_scale` + linguistic confidence → `discourse_budget_from_blocks`; bind deltas уже в `zone_scoring`.

---

## Открытые вопросы (допиши)

- [ ] Что считать минимальным «thread held» в duck test (метрика / probe)?
- [x] Как journal после partner turn должен менять bind на **следующем** tick? → `dialog_hubs` provenance + `thread_scoring` overlap boost
- [x] Где граница: `semantic_read` hints из bundle OK, substring oracle в compose — нет? → см. § ниже
- [x] Partner compose: zone bias до efferent? → `discourse_budget_from_blocks` + bind `zone_scoring`
- [ ] …

---

## Граница: routing vs oracle (черновик позиции)

**Правило одной фразы:** substring → **куда смотреть на поле** (read/bind) — OK, если это **данные или tract competition**; substring → **что сказать / какой hub вставить** (compose gate) — **нет**.

| Слой | OK | Не OK |
|------|-----|--------|
| **Read / route** (`semantic_read`, tract competition) | `cue_substrings` в **bundle claims**; KB hit → `concept_hints`; `lang.word.*` из lexicon на store; geometry/speech-act claims | Tuple в Python «если *опыт* в query → affect» **в compose/policy** |
| **Bind / reweight** | `concept_hints` + `partner_field_overlap` + zone `compose_bias` + bind score | `query_implies_*` deprioritize/prioritize blocks без field evidence |
| **Compose / efferent** | Phrase compose из **уже отобранных** blocks; partner_recent; anti-replay; zone union через executive | Hint **или** один overlap → verbatim `clause_1` hub; hot-path `material_blocks_for_tag` |

**Почему hints из bundle OK:** это **индекс на поле** — версионируется, учится ingest/curriculum, конкурирует через argmax (0052), даёт provenance (`concept_id`, tract). Агент **не** получает готовую фразу — только «смотри сюда».

**Почему oracle в compose нет:** обходит bind score, thread и зоны; один hint («как ты») → тот же affect-paste на разные ситуации — **имитация** routing без situated integration.

**~~Серая зона (техдолг)~~ → снято:** partner surface routing в `design/kb-partner-surface-routing.v1.json` + `ru.routing.partner_surface.*` claims (`partner_surface_routing.py`); store bundle может переопределить. **Инвариант:** hint с read path **не авторизует** narrative paste без field overlap / bind floor / thread context.

**Практический тест «это oracle?**»  
1. Живёт в `compose` / `policy.eligible` / `partner_scoring` с tuple подстрок? → скорее oracle.  
2. Меняется operator'ом через bundle/journal без правки Python? → скорее field routing.  
3. Hint alone → full hub text? → баг, не граница.

---

## Связи

- [agent-existence-north-star.md](agent-existence-north-star.md)
- [CASA-ADR-0061-intelligence-zones.md](CASA-ADR-0061-intelligence-zones.md)
- [CASA-ADR-0060-emotional-zone.md](CASA-ADR-0060-emotional-zone.md)
- [CASA-ADR-0062-genetic-zone.md](CASA-ADR-0062-genetic-zone.md)
- [CASA-ADR-0077-boundary-compose-encapsulation.md](CASA-ADR-0077-boundary-compose-encapsulation.md)
- [CASA-ADR-0078-partner-voice-invariants-v1.md](CASA-ADR-0078-partner-voice-invariants-v1.md)
- [CASA-ADR-0079-runtime-host-csharp-nativeaot.md](CASA-ADR-0079-runtime-host-csharp-nativeaot.md)
- [CASA-design-partnership-stages-and-initiative-v1.md](CASA-design-partnership-stages-and-initiative-v1.md)

---

## Changelog scratch

| Дата | Что добавили |
|------|----------------|
| 2026-06-10 | Первая выжимка из сессии chat/life/oracles/paste |
| 2026-06-10 | § Intelligence Zones; уточнена посылка (гипотеза); zone-scoped compose в следствиях |
| 2026-06-10 | § Граница routing vs oracle (hints OK on read, не в compose gate) |
| 2026-06-10 | `_SOCIAL_SURFACE_TO_CID` → `kb-partner-surface-routing.v1.json` + `partner_surface_routing.py` |
| 2026-06-10 | Verified: `907a93f` math eval oracle в hot path |
| 2026-06-10 | Continuer bind + verify script; `subject.dialog` bind-only |
