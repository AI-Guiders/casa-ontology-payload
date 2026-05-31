# Context axis v0 — ось контекста и цепочка вывода

**Date:** 2026-05-30  
**Status:** accepted (design; частично в lab)  
**Parent:** [`understanding-contract-v0.md`](understanding-contract-v0.md), [`CASA-ADR-0006-t9-predictive-text.md`](CASA-ADR-0006-t9-predictive-text.md), [`CASA-ADR-0008-layout-parity-bilingual-t9.md`](CASA-ADR-0008-layout-parity-bilingual-t9.md), [`agent-existence-north-star-v0.md`](agent-existence-north-star-v0.md)

---

## Позиция (Хомский / L0)

Естественные языки на уровне L0 **не формализуемы** полностью: нет одной функции «контекст → значение».

CASA **не** строит полную грамматику сверху. Контекст — **ось в модели мира агента**:

- конкурирующие гипотезы на поле (anchors, branches);
- episodic / hippo следы;
- L3 сущности и `R:` правила;
- FPN как удержание **плана между тиками** на решётке `lattice_fpn_wm` (см. [`control-lattice-stack-v0.md`](control-lattice-stack-v0.md)), не oracle.

**Слово с многими значениями** = одна лемма `lang.word.X` + **разные привязки** (`entity.*`, `R:context.*`, scene, segment), которые **выдвигаются** в зависимости от активного контекста, а не хранятся как 47 отдельных L2-слов.

---

## Что такое «контекст» у нас (не один тип)

| Вид | Где живёт | Пример |
|-----|-----------|--------|
| **Script / alphabet** | L0 basins latn/cyrl | `а` vs `a` |
| **Intent segment** | router v0 | `prose` \| `command` \| `toml` |
| **Layout branch** | L1 decode qwerty/jcuken | `/attach` vs `.феее` |
| **Homoglyph fork** | pre-commit latn/cyrl | `co` → merged preview (freq RU + EN homoglyph) |
| **Phrase / collocation** | L3 + `R:` (roadmap) | `согласно пр` → `приказу` |
| **Entity frame** | L3 `entity.*` | cow ↔ корова |
| **Episodic** | prism_hippo | «в прошлом тике печатали IDE» |
| **Domain tier** | store profile | tech vs general lexicon |
| **Lexicon usage** | `lexicon_axes` on state | `era`, `usage_band`, `active_for_t9` — см. [`lexicon-usage-axes-v0.md`](lexicon-usage-axes-v0.md) |

**Контекст** — **композиция** этих сигналов на тике, не одно поле в JSON.

---

## Цепочка вывода контекста (v0, не формула)

Не «алгоритм из учебника», а **UC-цепочка** на каждом macro-tick:

```text
  INPUT (physical keys | unicode stream | listen)
       │
       ▼
  L0/L1  script + layout branches     ← ADR-0008, homoglyph
       │
       ▼
  SEGMENT classifier (heuristic v0)    ← prose / command / toml
       │   сигналы: leading /, ratio cyrl/latn, keyboard cues
       ▼
  STORE bias (profile roles)           ← какой lexicon shard family
       │
       ▼
  PREDICT  predict_t9 / unified_tick   ← anchors[], multi-branch
       │   конкуренция votes на L2 + опц. L3 prior
       ▼
  CRITIC   commitment vs fork           ← homoglyph: wait; segment: verify
       │
       ▼
  ACT      preview chip / surface       ← «выпрямленный интент»
       │
       ▼
  SLEEP    consolidate + explain meta   ← kb meta.freq, entity edges
```

**Вывод контекста** = какой **branch выиграл argmax** + **commitment** (`committed` \| `ambiguous` \| `layout_mismatch`), с trace в ответе tick (для IDE / log).

### Что отдаём наружу (контракт tick)

Расширение JSON ответа `unified_tick` / layout-parity (roadmap поля):

```json
{
  "context": {
    "segment": "command",
    "script": "latn",
    "layout_winner": "qwerty_us",
    "store_bias": ["en_lexicon", "en_command"],
    "homoglyph_fork": false
  },
  "reasoning_trace": [
    "layout: qwerty /attach beats jcuken .феее",
    "segment: leading slash → command",
    "t9: top anchor attach (votes=12)"
  ],
  "commitment": "committed"
}
```

`reasoning_trace` — **читаемая цепочка для человека и отладки**, не доказательство формальной правильности.

---

## Многозначность слова

| Механизм | Роль |
|----------|------|
| **Одна лемма L2** | `lang.word.банк` одна сеть на полке |
| **L3 entity / meta** | `entity.bank_finance` vs `entity.bank_river` через hub |
| **R:context.*** (roadmap) | dative, domain, «в этой фразе» |
| **Hippo episode** | недавний домен disambiguates на sleep |
| **Cold ingest** | новый смысл → новые edges на sleep, не новый оргран |

Не плодим 10 L2 для омонимов — плодим **связи и episodic**, как в ADR-0003 entity hub.

---

## Связь с частотой (meta)

`meta.freq.*` на L3 объясняет **почему** при неоднозначном префиксе чаще всплывает частое слово; это **не** контекст смысла, а **prior на L2**.

Контекст смысла → segment + entity + L3 `R:`; частота → prior при равном префиксе.

---

## Lab vs roadmap

| Кирпич | Статус |
|--------|--------|
| segment prose/command (ADR-0008) | design + частично unified |
| homoglyph fork | green |
| context L3 T9 (`согласно пр`) | ADR-0006 roadmap |
| `reasoning_trace` в tick JSON | **roadmap** |
| `context.*` concept namespace на L3 | **roadmap** (ingest как kb bundle) |
| wake/sleep / Extract vs batch L3 | **concept:** [`casa-wake-sleep-concept-v0.md`](casa-wake-sleep-concept-v0.md) |

---

## Анти-паттерны

| Нельзя | Почему |
|--------|--------|
| Один LLM «угадай контекст» на hot path | latency, UC, не поле |
| Полная формальная грамматика в core | L0 не формализуем |
| Отдельный store на каждое значение слова | взрыв картриджей; нужны edges |
| Путать store и context | store = память; context = tick inference |

---

## Связанные документы

- [`agent-store-catalog-v0.md`](agent-store-catalog-v0.md) — куда какой store подключать
- [`CASA-ADR-0003-emergent-forms-tags-predictor.md`](CASA-ADR-0003-emergent-forms-tags-predictor.md) — entity, emergent tags
- [`predictor-v0.md`](predictor-v0.md) — anchors, votes
