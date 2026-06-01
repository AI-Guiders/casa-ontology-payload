# Lattice naming v1 — lab mirror (CASA)

**Date:** 2026-05-31  
**Status:** accepted (target names); **migration:** in progress  
**KB canon:** `work/projects/door-to-singularity/ca-substrate-agent/kb-casa-lattice-naming-v1.md` (agent-notes)  
**Machine map:** [`lattice-id-map.v1.json`](lattice-id-map.v1.json)  
**Code:** `tools/lattice_names_v1.py`  
**Related:** [`alphabet-core-immutable.md`](alphabet-core-immutable.md)

---

## KB — канон; этот файл — lab mirror

**Канон в agent-notes** (`kb-casa-lattice-naming-v1.md`). Этот док — **проекция для lab**: machine map, migrate, store paths. Агент **сначала** читает KB через `route_context` / `read_knowledge_file`, **потом** этот файл и код.

| Источник | Что брать |
|----------|-----------|
| **KB (канон)** | `work/projects/door-to-singularity/ca-substrate-agent/kb-casa-lattice-naming-v1.md` (agent-notes MCP) |
| **Design (этот репо)** | [`language-acquisition-loop.md`](language-acquisition-loop.md), [`infancy-corpus-phases.md`](infancy-corpus-phases.md), [`agent-store-catalog.md`](agent-store-catalog.md) |
| **Lab v0** | ru/en stores — **первые корпуса**, не модель «только два языка» |

**Правило для агента:** вопросы про имена решёток → **KB canon**, затем этот mirror + `lattice_names_v1.py`.

---

## Три уровня (не смешивать)

```text
  SCRIPT (метаданные)     АЛФАВИТ ЯЗЫКА (L0)           ЛЕКСИКОН (L2)
  cyrl | latn | …         alphabet-ru  alphabet-uk       words-ru-*
                          │            │  (і, ї, є, ґ)    words-uk-*
                          └─ script=cyrl, но буквы РАЗНЫЕ
```

| Уровень | Вопрос | Id | Пример |
|---------|--------|-----|--------|
| **script** | Unicode-семейство, раскладка | поле `script` на решётке | cyrl, latn, latin-extended |
| **alphabet** | *какие буквы в этом языке?* | **`alphabet-{locale}`** | `alphabet-ru` (нет **і**), `alphabet-uk` (есть **і**, **ї**, **є**, **ґ**) |
| **lexicon** | *какие слова?* | **`words-{locale}-{shard}`** | `words-ru-47`, `words-uk-03` |

**Кириллица ≠ один алфавит.** RU и UK оба `script=cyrl`, но **разные решётки** `alphabet-ru` и `alphabet-uk`: в украинском есть **і**, в русском её нет; наборы букв не совпадают 1:1.

То же для latn: `alphabet-en` (26) ≠ `alphabet-de` (ä, ö, ü, ß) — позже отдельные immutable packs.

---

## Много языков

| locale | alphabet (L0) | syllables (L1) | words (L2) | script (meta) |
|--------|---------------|----------------|------------|---------------|
| **ru** | `alphabet-ru` | `syllables-ru` | `words-ru-*` | cyrl |
| **uk** | `alphabet-uk` | `syllables-uk` | `words-uk-*` | cyrl |
| **be** | `alphabet-be` | `syllables-be` | `words-be-*` | cyrl |
| **en** | `alphabet-en` | `syllables-en` | `words-en-*` | latn |
| **de** | `alphabet-de` | `syllables-de` | `words-de-*` | latn / latin-extended |

```text
alphabet-ru ── syllables-ru ── words-ru-*
alphabet-uk ── syllables-uk ── words-uk-*    ← не общий «alphabet-cyrl»
alphabet-en ── syllables-en ── words-en-*
phrases (hub, multilingual)
```

**Lab v0:** только `alphabet-ru` + `alphabet-en` (legacy `L0_grapheme_cyrl` / `_latn`). `alphabet-uk` — при добавлении UK corpus.

**Store:** `lexicon-{locale}-{tier}` — один store на язык+tier ([`agent-store-catalog.md`](agent-store-catalog.md)).

**Hub `phrases`:** entity/POS/taxonomy — общий каркас; леммы на **words-{locale}**.

---

## Правило имени

```text
{kind}-{locale}              # alphabet, syllables (на язык)
{kind}-{locale}[-{shard}]    # words
{kind}                       # phrases, keys-physical
{kind}-{locale}-{layout}   # layout-ru-jcuken, layout-uk-…
```

| kind | по locale | shared |
|------|-----------|--------|
| `alphabet` | ✅ ru, uk, be, en, de, … | |
| `syllables` | ✅ | |
| `words` | ✅ + shard | |
| `punct` | ✅ `punct-ru`, `punct-uk`, … | |
| `layout` | ✅ | |
| `phrases` | | `phrases` |
| `keys` | | `keys-physical` |

**concept_id (v0 lab):** по-прежнему `grapheme.cyrl.*` / `grapheme.latn.*` — script в id токена; **решётка** при этом **`alphabet-ru`**, не `alphabet-cyrl`. Roadmap: `grapheme.ru.*` / `grapheme.uk.*` при split concept namespaces.

---

## Таблица v0 → v1

| Legacy (v0) | **v1 canonical** | Примечание |
|-------------|------------------|------------|
| `L0_grapheme_cyrl` | **`alphabet-ru`** | был RU 33 буквы, не «вся кириллица» |
| `L0_grapheme_latn` | **`alphabet-en`** | EN 26 |
| `L0_grapheme` | migrate → split | |
| `L1_syllable` | split → `syllables-{locale}` | roadmap |
| `L2_word_{nn}` | `words-ru-{nn}` | |
| `L2_en_word_{nn}` | `words-en-{nn}` | |
| `L3_phrase` | `phrases` | |
| `L0_punct_cyrl` | `punct-ru` (или shared `punct-cyrl` — TBD) | |
| `L0_punct_latn` | `punct-en` | |

*(новые)* | `alphabet-uk`, `syllables-uk`, `words-uk-*` | UK immutable pack |

### Math (1-я СС)

| Legacy | v1 |
|--------|-----|
| `F0_schema` | `schema-math` |
| `F1_compose` | `compose-math` |
| `F2_quantity` | `quantity-math` |

---

## Compose ladder (z_level)

| z | per locale | shared |
|---|------------|--------|
| 0 | alphabet-*, punct-*, layout | keys-physical |
| 1 | syllables-* | |
| 2 | words-{locale}-* | |
| 3 | | phrases |

Мосты: `bridge-alphabet-ru-syllables-ru`, `bridge-alphabet-uk-syllables-uk`, …

---

## Миграция

Map: `lattice-id-map.v1.json`. **`L0_grapheme_cyrl` → `alphabet-ru`**, не `alphabet-cyrl`.

```bash
# dry-run
python tools/migrate_lattice_ids_v1.py --store-dir lab/agent-stores/lexicon-ru-general --dry-run

# apply (ltm + manifest + nca paths; без NCA retrain)
python tools/migrate_lattice_ids_v1.py --store-dir lab/agent-stores/lexicon-ru-general --compact

# только ltm/manifest, без field_state (400 MiB JSON)
python tools/migrate_lattice_ids_v1.py --store-dir … --skip-field-state
```

---

## Changelog

| Date | Change |
|------|--------|
| 2026-05-31 | v1.0–v1.2 | … |
| 2026-05-31 | v1.3: **alphabet per locale** (ru≠uk: і); script = metadata only |
| 2026-05-31 | v1.4: KB canon in agent-notes; this file = lab mirror only |
| 2026-05-31 | v1.5: `tools/migrate_lattice_ids_v1.py` — rename без NCA retrain |
