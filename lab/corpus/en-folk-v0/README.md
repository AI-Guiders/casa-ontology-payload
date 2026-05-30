# English folk corpus (lab v0)

Public-domain texts for EN lexicon ingest. **Corpus is source only** — structure on field is L2 headwords via `extract_en_headwords_v0.py` → `ingest_en_lex_dev_v0.py`.

## Sources

| File | Origin | License |
|------|--------|---------|
| `grimm-fairy-tales.gutenberg.txt` | [Grimm's Fairy Tales](https://www.gutenberg.org/ebooks/17038) (Project Gutenberg #17038) | Public domain |
| `jacobs-english-fairy-tales.gutenberg.txt` | [English Fairy Tales](https://www.gutenberg.org/ebooks/2591) (Joseph Jacobs, PG #2591) | Public domain |

Re-download:

```bash
curl -sL "https://www.gutenberg.org/cache/epub/17038/pg17038.txt" -o grimm-fairy-tales.gutenberg.txt
curl -sL "https://www.gutenberg.org/cache/epub/2591/pg2591.txt" -o jacobs-english-fairy-tales.gutenberg.txt
```

## Extract headwords

```bash
cd casa-ontology-payload
python tools/extract_en_headwords_v0.py \
  --corpus-dir lab/corpus/en-folk-v0 \
  --out lab/exp_bilingual_v0/en_folk_headwords.v1.txt \
  --report lab/corpus/en-folk-v0/extract_report.v1.json \
  --min-freq 2
```

Measured (2026-05-30): **~191k tokens**, **~6704** unique headwords (min_freq≥2) from both books.

Content-word list (no stopwords): `en_folk_content_headwords.v1.txt` via `--stopwords`.

## Ingest to L2

```bash
python tools/ingest_en_lex_dev_v0.py \
  --store-dir lab/agent-stores/sss-ru-lexicon-v0 \
  --headwords lab/exp_bilingual_v0/en_folk_headwords.v1.txt \
  --write
```

Then T9 sweep or smoke bench with `--prefer-field-state`.
