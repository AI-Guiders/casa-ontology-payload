# lang-ru-math-bridge

Узкий русский текстовый мост к **math-palochki**: роли операндов, слова операций, сцены «палочки/кучки». Ingest **после** math-palochki на том же agent store.

```bash
python tools/ingest_lang_lesson_class.py --store-dir agents/von-neumann
python tools/check_lang_math_bridge.py --store-dir agents/von-neumann
```
