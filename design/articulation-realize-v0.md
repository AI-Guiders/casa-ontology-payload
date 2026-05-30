# Articulation realize v0 — речь из слотов, не вставка claims

**Status:** implemented (lab v0)  
**Date:** 2026-05-28  
**Replaces (hot path):** paste `claim.text` в `compose_answer_text_sketch`  
**See also:** [`experiment-j-language-complete-v1.md`](experiment-j-language-complete-v1.md), [`casa-glossary-v0.md`](casa-glossary-v0.md) § Articulation

## Проблема

`answer_text` = «Понял…» + **цитата** top-2 claims — это **retrieval**, не **речь**.  
Dialogue KB не лечит: больше карточек ≠ операции над словами.

## Контракт v0

```text
claims (память)  →  UtterancePlan (слоты)  →  realize()  →  answer_text (новая фраза)
```

| Слой | Что хранит | Что НЕ делает |
|------|------------|----------------|
| **DMN / KB** | `concept_id`, короткий атом, provenance | Не обязан быть готовым ответом |
| **CEN** | intent, top concepts | Не копирует `claim.text` в ответ |
| **Articulation** | слоты + лексемы + шаблоны реализации | Не LLM на hot path (v0) |

## UtterancePlan (слоты)

```python
@dataclass
class UtterancePlan:
    act: str          # greeting | how_are_you | intro | phrase_call_mama | explain_rule | ...
    intent: str       # из query (объяснение, проверка нормы, …)
    lexemes: dict     # role -> surface: addressee="мама", ...
    atoms: list       # GrammarAtom: норма в 1 коротком предложении, не абзац claim
    concept_ids: list # опора для provenance / bench
```

**Lexeme** — из `ru.lang.word.*` или явного `lemma` в claim (будущее). v0: парсинг `concept_id` + dialogue map.

## Реализация (realize)

Шаблоны **генерируют** русское, опираясь только на:

- слот `act`;
- лексемы (`мама`, `я`, `ты`);
- **atoms** — выжимка нормы (regex / первое правило), ≤ ~120 символов, **перефраз** в шаблоне.

Пример:

| Вход (atoms) | Выход (новая фраза) |
|--------------|---------------------|
| `запятая+что+придаточное` | «В придаточном с «что» запятая обычно ставится.» |
| `addressee=мама, evening_call` | «Можно написать маме: …» (не абзац из KB) |

## Маршрутизация act ← concept_id

| concept_id prefix | act |
|-------------------|-----|
| `ru.dialog.greeting` | `greeting` |
| `ru.dialog.how_are_you` | `how_are_you` |
| `ru.dialog.self` / `ru.dialog.capabilities` | `intro` |
| `ru.dialog.call_mama` | `phrase_call_mama` |
| `ru.dialog.phrase_help` | `phrase_help` |
| `ru.dialog.soft_miss` | `soft_miss` |
| `ru.lang.word.mama` | lexeme only |
| `ru.grammar.*` | `explain_rule` / `compare_forms` (по intent query) |

## Что запрещено в v0

- Вставка **двух подряд** полных `claim.text` в ответ.
- Подмена болтовни уроком C# (code-guard в CEN остаётся).
- Выдача себя за человека с биографией.

## Bench

`tools/bench_articulation_realize.py`:

- те же queries, что write/sketch;
- **paste_ratio** — доля ответа, совпадающая с claim (должна падать vs sketch);
- `realize_act` в отчёте.

## Roadmap

| v | Добавление |
|---|------------|
| **v0** | шаблоны + grammar atoms + dialogue acts (этот doc) |
| **v0.5** | **acquisition loop** — listen → babble → correct; см. [`language-acquisition-loop-v0.md`](language-acquisition-loop-v0.md) |
| v0.1 | `lemma` / `slots` в claim JSON (KB), не regex |
| v1 | MoE: grammar-expert / dialogue-expert / code-bridge-expert |
| v2 | опциональный локальный LM **после** плана слотов (не на hot path по умолчанию) |

**Важно:** v0 — ранний **лепет** (продукция с поля/KB), не внутреннее понимание. Понимание падежей — через [`language-acquisition-loop-v0.md`](language-acquisition-loop-v0.md), не через лекции пользователю.

## Код

| Файл | Роль |
|------|------|
| `tools/articulation_realize_v0.py` | `build_plan`, `realize`, `compose_answer_text` |
| `tools/articulation_grammar_v0.py` | re-export; `sketch` legacy |
| `tools/sn_cen_runtime.py` | `compose_answer_text` на hot path |

## Smoke

```powershell
python tools/bench_articulation_realize.py `
  --queries examples/exp_j_ru_v1/queries_oral_exam.jsonl `
  --store-dir examples/agent-stores/language-agent-lab-v0
```
