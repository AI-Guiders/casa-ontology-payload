# English folk corpus (lab v0)

Public-domain texts for EN lexicon ingest. **Texts are not in git** — download first.

## Download sources

```bash
python scripts/download_corpora.py
# or: python scripts/fetch_en_folk_gutenberg_v0.py
```

Files land in `source/` (gitignored):

| File | Origin | License |
|------|--------|---------|
| `source/grimm-fairy-tales.gutenberg.txt` | [Grimm's Fairy Tales](https://www.gutenberg.org/ebooks/17038) (PG #17038) | Public domain |
| `source/jacobs-english-fairy-tales.gutenberg.txt` | [English Fairy Tales](https://www.gutenberg.org/ebooks/2591) (Jacobs, PG #2591) | Public domain |

## Extract headwords (lab)

Headword extraction scripts live under `tools/` (see store ingest docs). Typical flow:
corpus dir → `en_folk_headwords.v1.txt` → `ingest_en_lex_dev_v0.py`.

## Ingest to L2

See `lab/agent-stores/INDEX.md` and `tools/init_en_folk_store_v0.py`.
