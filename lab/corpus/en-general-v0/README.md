# EN general corpus (folk / prose)

Headwords: `headwords.v1.txt` (from Gutenberg Grimm + Jacobs).

```bash
python tools/extract_en_headwords_v0.py \
  --corpus-dir lab/corpus/en-folk-v0 \
  --out lab/corpus/en-general-v0/headwords.v1.txt \
  --stopwords
```

Store: `lab/agent-stores/sss-en-general-v0`
