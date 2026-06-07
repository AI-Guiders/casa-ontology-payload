# CASA: gate «носитель» (interlocutor, не словарь)

**Статус:** design v1 (2026-06-07) — **подмножество B1**; главный уровневой gate: [CASA-cefr-gate-ru-v1.md](CASA-cefr-gate-ru-v1.md)  
**Связано:** [CASA-ADR-0045-subject-as-interlocutor.md](CASA-ADR-0045-subject-as-interlocutor.md), [CASA-ADR-0049-ru-lexical-fluency-orthography-v0.md](CASA-ADR-0049-ru-lexical-fluency-orthography-v0.md), [CASA-von-neumann-ru-teaching-plan-v1.md](CASA-von-neumann-ru-teaching-plan-v1.md) § Блок 12

---

## Одной фразой (для всех)

**Носительский gate** — субъект **понимает смысл текста и обсуждает его своими словами**, сколько сочтёт нужным: не шаблон, не act-ветка, не paste claim. **Ограниченный словарь сейчас — нормально.** Не знает — говорит честно. Знает — **перефразирует**, не цитирует KB.

Это **не** «знает 5000 слов» и **не** `strict_v2` (plumbing: intent, top concept, no jargon). Plumbing — prerequisite; **nositel gate** — про **собеседника**.

---

## Что проверяем

| Да (gate) | Нет (не gate / не носитель) |
|-----------|------------------------------|
| Ответ по **смыслу** вопроса к тексту | Подстрока из эхо запроса |
| **Своя формулировка** (paraphrase) | Фиксированная реплика из slots/act |
| Длина **как решил** (1 фраза или абзац) | Квота «ровно 2 предложения» |
| Обсуждение: факт, вывод, «не уверен» | «Слышу: … нет bind …» на teachable cue |
| Честный partial вне поля | Галлюцинация «как будто знает» |

---

## Оси gate (plan `nositel-gate-plan-v1.json`)

| Ось | Смысл | Пример |
|-----|--------|--------|
| **discuss** | passage + вопрос → ответ по тексту | «Что купила Маша?» → про апельсин |
| **discuss-why** | вывод / мотив из текста | «Почему папа сказал „Молодец"?» |
| **talk** | свободный turn (привет, спасибо, о себе) | кратко, не 13 предложений из всех dialog atoms |
| **teach** | объяснить слово/норму | gloss `«привет» — …`, не greeting вместо explain |
| **honest** | нет текста → уточни; чужой абзац → partial без выдумки | не «проверь то, чего нет» |

**Не входит в nositel gate (отдельно):** L1 fluent read, L2 OOV remember, morphemics, орфо-корпус на 500 форм.

---

## Probe

```bash
python lab/visual-curriculum/probe_nositel_gate_ru.py --store von-neumann
```

**Plan:** `lessons/ru-text-tract/data/nositel-gate-plan-v1.json`  
**Pass:** все сценарии + `gate_policy: interlocutor_v1`.

### Критерии interlocutor_v1

1. **semantic** — target из текста/вопроса в ответе (не только в эхо).
2. **anti_template** — нет defer/bind/Слышу на teachable; нет meta-хвоста.
3. **paraphrase** — нет paste длинного KB-claim; короткий gloss ок.
4. **own_voice** — ≥ N токенов ответа не совпадают с вопросом (своя речь).
5. **honest** — на unknown: partial, без фиктивной экспертизы.

---

## Hot path (код)

```
partner turn (passage + question | free talk)
  → semantic_read: intent discuss | recall | social | …
  → bind: passage words → lang.word.* + journal + meta.discourse
  → phrase_compose: discuss_discourse | social (one dialog family)
  → без LLM, без act templates
```

**Discuss:** факты читаются **из passage** (лёгкий comprehend), связки — `ru.meta.discourse.*`, не teacher sentence templates.

---

## Отношение к strict_v2

| Probe | Роль |
|-------|------|
| `probe_nositel_acceptance_ru` (strict_v2) | регрессия plumbing |
| **`probe_nositel_gate_ru` (interlocutor_v1)** | **gate «носитель»** |

Блок 12 **закрыт** когда **`probe_cefr_gate_ru` → `block_12_pass`** (`achieved_level >= B1`), не «носитель».  
`probe_nositel_gate_ru` (interlocutor_v1) — регрессия подмножества B1.

---

## Non-goals

- Притворство безграничного словаря.
- LLM на hot path.
- ЕГЭ-шаблоны и «вставь запятую» без смысла.
