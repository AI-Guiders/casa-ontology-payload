# Config formats (TOML + JSON)

**Date:** 2026-05-30  
**Status:** pilot

## Зачем TOML

| Формат | Где |
|--------|-----|
| **TOML** | Ручные design/manifest: stack, control, catalog, keyboard tables, registry |
| **JSON** | Runtime и обмен: `field_state.json`, KB `*.payload.json`, bench `report.json`, `import_log.ndjson` |
| **LTM binary** | Решётки на диске (`*.ltm`), не текст |

TOML: комментарии, меньше шума `{}`, таблицы `[[lattices]]` читаются как документ.  
JSON: экосистема .NET, компактный dump, уже везде в tooling.

## Загрузка

`tools/config_io_v0.py`:

- `load_config(path)` — читает `.toml` или `.json`
- `resolve_config_path` — если передан `*.v0.json`, а на диске есть sibling `.toml`, берёт **TOML**

Старые пути в `field_state` (`"stack": "design/sss-lattice-stack.v0.json"`) продолжают работать.

## Миграция (поэтапно)

1. ✅ `sss-lattice-stack.v0.toml` (канон); JSON — legacy, не править вручную
2. ⏳ `control-lattice-stack.v0.toml`
3. ⏳ `lab/agent-stores/catalog.v0.toml`, `manifests/kb-*.toml`
4. ⏳ keyboard `lab/keyboard-layouts/*.toml`
5. ❌ не трогать: `field_state`, `pack.manifest` (генерируется), KB bundles

## Правила

- Новый hand-edited config → **`.toml`**
- Генераторы могут писать JSON (отчёты, CI)
- В design-doc ссылаться на `.toml`, JSON упоминать как legacy
