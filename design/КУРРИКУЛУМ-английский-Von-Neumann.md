# Как фон Нейман выучил английский (обзор куррикулума)

Документ для команды. Описывает, что и как было выучено через авто-куррикулум:
от отдельных слов до целых английских предложений с согласованием — **детерминированно,
без LLM, с проверкой held-out гейтом, без галлюцинаций.**

Всё лежит в `casa/curriculum/` (модули) и `lab/curriculum/` (данные). Тесты — `tests/test_*.py`.
Вся связка зелёная (49 тестов на момент написания).

---

## 1. Главная идея

Знание живёт в поле как рёбра на латтисе. Учитель **индуцирует правило из примеров**,
**кладёт его в поле** как рёбра, а производство **читает правило обратно из поля**.
Поэтому:

- если убрать ребро (ablation) — производство падает (правило реально в поле, а не в Python);
- правило проверяется на **отложенных (held-out)** примерах — зубрёжка их провалит, обобщение пройдёт;
- **negative control** (ложная метка / перепутанный порядок) не должен проходить.

Это и есть анти-тавтология: гейт не штампует, а требует доказательства обобщения.

---

## 2. Слои способности (снизу вверх)

| Слой | Модуль | Что умеет | Данные | Тест |
|---|---|---|---|---|
| Перевод слов | `translate.py` | RU↔EN по рёбрам `concept\|names\|word` (два прыжка) | — | `test_translate.py` |
| Словарь оптом | `glossary.py` | тысячи пар за ОДИН сон; загрузка словарного файла | `en-glossary-*.json` | `test_glossary.py` |
| Морфология | `compose.py` | индукция класс-обусловленных правил (суффиксы, удвоение) | `en-rules-v1.json` | `test_compose.py` |
| Фраза | `compose.py` | прилагательное+существительное, именная группа (число/артикль/мн.) | — | `test_compose.py` |
| Предложение | `sentence.py` | порядок S-V-O, индуцированный из примеров | `en-sentence-v1.json` | `test_sentence.py` |
| Клауза | `clause.py` | время / отрицание / вопрос (do-support) | `en-clause-v1.json` | `test_clause.py` |
| Всё вместе | `clause.py` | NP + согласование по числу подлежащего | `en-np-clause-v1.json` | `test_np_clause.py` |

---

## 3. Что именно выучено

**Словарь.** 32 237 чистых пар RU↔EN из открытого словаря OpenRussian (CC BY-SA),
загружены за один сон (~39 с офлайн после линеаризации минтинга), перевод 100% в обе
стороны на выборке.
Сборка: `python scripts/build_open_glossary.py --out lab/curriculum/en-glossary-ru-open.json`.

**Морфология (4 правила, индуцированы из данных, единственный данный примитив — гласные):**

| Правило | Классы | Примеры обобщения (никогда не виданные слова) |
|---|---|---|
| Множественное | согл.+y→ies, шипящие→es, иначе→s | `fly→flies`, `church→churches`, `phone→phones` |
| Прошедшее | согл.+y→ied, гласн.→+d, иначе→+ed | `carry→carried`, `tidy→tidied`, `walk→walked` |
| Сравнительная | CVC→удвоение+er, -e→+r, согл.+y→ier, иначе→+er | `mad→madder`, `neat→neater`, `busy→busier` |
| 3-е лицо ед. | шипящие→es, согл.+y→ies, иначе→s | `guess→guesses`, `spy→spies`, `sing→sings` |

**Синтаксис.** Порядок S-V-O индуцирован из 2 примеров. do-support: вспомогательный
`does/did` несёт время и согласование, основной глагол базовый под отрицанием/вопросом.
Число подлежащего управляет согласованием (`cat drinks` / `cats drink`).

**Русская морфология (стресс-тест индуктора, `ru-rules-v1.json`, `test_ru_morphology.py`).**
Тот же движок; даны два примитива-класса: гласные (расширены на кириллицу) и
**велярные/шипящие** `к г х ж ш ч щ` (закрытое орфографическое множество, как и гласные).
Индуктор сам открыл правило ы/и:
- **Мужской род мн.ч.** → `-ы`, но `-и` после велярной (выучено как ОДИН класс `K`, не семь
  литералов): `сапог→сапоги`, `шкаф→шкафы`, `утюг→утюги`.
- **Средний род** → `-о→-а`, `-е→-я`: `вино→вина`, `море→моря`.
- **Женский род** → `-а→-ы`, но `-и` если перед `-а` стоит велярная/шипящая (паттерн `Kа`):
  `книга→книги` vs `рыба→рыбы`. Обобщается на невиданное, включая шипящие:
  `задача→задачи`, `свеча→свечи`, `эпоха→эпохи`; `ягода→ягоды`, `берёза→берёзы`.

Все три гейта проходят (held-out + neg-control + ablation). Это **закрыло** прежнюю границу
(женский род раньше не выводился) одним принципиальным примитивом — классом велярных.
Вне области: иррегуляры/беглые гласные/несклоняемые (`стул→стулья`, `носок→носки`, `метро`)
и мягкие основы на `-я` (другое склонение).

---

## 4. Запуск (end-to-end)

```python
import json, pathlib
from casa.prisms.memory.f0_math_ingest import ingest_math_bundle
from casa.prisms.memory.memory_prisms import ensure_prisms
from casa.curriculum import (
    teach_glossary, teach_conditioned_rule, teach_clause_constructions,
    teach_np_order, compose_full_clause,
)

bundle = json.loads(pathlib.Path("lab/exp_l/kb-math-concrete-schemas-l0.bundle.v1.json").read_text(encoding="utf-8"))
state = ensure_prisms({}); ingest_math_bundle(state, bundle)
L = "schema-math"

teach_glossary(state, [("кот","cat"),("вода","water"),("большой","big"),("два","two"),("пить","drink")], bundle=bundle)
rules = json.loads(pathlib.Path("lab/curriculum/en-rules-v1.json").read_text(encoding="utf-8"))["rules"]
for rid in ("lang.rule.plural.en","lang.rule.present3sg.en","lang.rule.past.en"):
    teach_conditioned_rule(state, L, rid, [tuple(p) for p in rules[rid]])
teach_clause_constructions(state, L); teach_np_order(state, L)

print(compose_full_clause(state, L, subject={"noun":"кот"}, obj={"noun":"вода"}, verb="пить"))
# -> The cat drinks the water.
print(compose_full_clause(state, L, subject={"noun":"кот","number":"два","adj":"большой","determiner":None},
                          obj={"noun":"вода"}, verb="пить"))
# -> Two big cats drink the water.
print(compose_full_clause(state, L, subject={"noun":"кот","plural":True}, obj={"noun":"вода"},
                          verb="пить", mood="interrogative"))
# -> Do the cats drink the water?
```

Тесты: `python -m pytest tests/test_glossary.py tests/test_compose.py tests/test_sentence.py tests/test_clause.py tests/test_np_clause.py -q`

---

## 5. Потолок (что честно НЕ умеет)

- **Не парсит свободный русский текст в роли.** Вход — уже размеченные роли
  (subject/verb/object). Назначение ролей — это понимание, которого подложка не делает.
- **Артикли упрощены** до фиксированного `the` (выбор a/the/∅, a/an — отдельная сложная тема).
- **Удвоение в прошедшем не заявляется**: оно зависит от ударения (`stop→stopped`, но
  `open→opened`, оба CVC) и не выводимо из орфографии. Лучше честно не заявлять правило.
- **Иррегуляры даны как лексикон** (`drink→drank`, `see→saw`, `does`, `did`) — суплетивные
  формы, из правил не выводятся.
- Это **порождение/перевод слов и форм**, не понимание смысла. Тот же потолок, что у глоссария.

В этих границах — детерминированно, продуктивно по лексикону, аудируемо, без галлюцинаций.
Сильная сторона архитектуры: контролируемый язык и доменная терминология.

---

## 6. Где что лежит

- Модули: `casa/curriculum/{translate,glossary,compose,sentence,clause}.py`
- Данные: `lab/curriculum/en-*.json` (+ `README-glossary.md` — атрибуция словаря)
- Сборка большого словаря: `scripts/build_open_glossary.py`
- Гейт: `casa/eval/held_out_gate.py`; обучение/верификация: `casa/curriculum/teach.py`
- Тесты: `tests/test_{translate,glossary,compose,sentence,clause,np_clause}.py`
