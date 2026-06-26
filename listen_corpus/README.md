# Listen corpus (cold path media)

**Медиа не в git.** В репозитории только этот README и скрипты в `tools/`.

## Где лежат байты

По умолчанию — **соседняя папка** рядом с репо:

```text
Experiments/
  casa-ontology-payload/     ← git (код)
  casa-listen-corpus/        ← wav, mp4, frames, manifest (локально)
```

Переопределение:

```powershell
$env:CASA_LISTEN_CORPUS = "D:\media\casa-listen"
```

## Layout одного ролика

```text
casa-listen-corpus/
  sources.json
  lalabook/
    speech-dev/
      IixOLmEcKtk/
        video.info.json
        audio.wav
        video.mp4          # опционально, для кадров
        frames/
          00-chapter-slug/
            f0000.jpg … f0016.jpg   # burst внутри главы, не один poster
        manifest.ndjson    # bind: t0/t1, frames[], speaker, без words[]
```

## Lalabook — multimodal bind (default)

**Три модальности без yt-subs:**
- **звук** — `audio.wav` + `t0/t1`
- **картинка** — `frames/<chapter>/f*.jpg` burst (~12 с между кадрами), текст **в кадре**
- **текст** — не отдельный subs-трек; строки в мультике = часть visual imprint (LRGB); L3 `caption` = название главы

```powershell
python tools/lalabook_batch_cold.py
```

Только аудио (быстрее, без visual): `--audio-only`.


Состояние: `casa-listen-corpus/lalabook.batch.state.json` (resume, skip готовых bundle).

Один плейлист:

```powershell
python tools/lalabook_batch_cold.py --collection speech-dev
python tools/lalabook_batch_cold.py --collection emotions
```


```powershell
cd casa-ontology-payload
python tools/yt_chapters_listen_cold.py `
  "https://www.youtube.com/watch?v=IixOLmEcKtk" `
  --publisher lalabook `
  --collection speech-dev
```

Требуется: `yt-dlp`, `ffmpeg` (для кадров). Только аудио: `--audio-only`.

Повторный прогон без скачивания:

```powershell
python tools/yt_chapters_listen_cold.py "<url>" --publisher lalabook --collection speech-dev --no-fetch
```

## Ingest в агента

**Сначала** проверка paired beats (scene-cut + A/V окна):

```powershell
python tools/verify_listen_beats.py `
  --manifest "..\casa-listen-corpus\lalabook\emotions\ukt4kquicra\manifest.ndjson" `
  --chapters 0
```

**Глазами и ушами** — HTML-галерея (кадр + кусок звука на каждый beat):

```powershell
python tools/preview_listen_beats.py `
  --manifest "..\casa-listen-corpus\lalabook\emotions\ukt4kquicra\manifest.ndjson" `
  --chapters 0
# → открой в браузере: ...\ukt4kquicra\preview\ch00\index.html
```

Только после `PASS` в verify и если preview выглядит правдоподобно — ingest:

Manifest ссылается на файлы **относительно bundle_dir**. Ingest указывает store агента; wav/frame резолвятся от `--manifest` parent + store:

```powershell
python tools/listen_mass_ingest.py `
  --manifest "..\casa-listen-corpus\lalabook\speech-dev\IixOLmEcKtk\manifest.ndjson" `
  --store-dir agents/von-neumann
```

`listen_mass_ingest` резолвит `wav`/`frame` от каталога manifest и от `store_dir`; для внешнего корпуса пути в manifest — относительные (`audio.wav`, `frames/…`), а bundle лежит рядом с manifest.

## Git LFS?

**Не рекомендуем** для сотен мегабайт видео в основном репо. Варианты:

| Вариант | Когда |
|---------|--------|
| Локальный `casa-listen-corpus/` | dev machine (default) |
| Отдельный private repo + LFS | шарить корпус между машинами |
| Только manifest в git | CI smoke без медиа |

## Профили manifest

| profile | Смысл |
|---------|--------|
| `bind` | короткие главы, speaker on-screen, без `words[]` |
| `womb` | mass фон (тот же формат, другой отбор источников) |

Слова (`words[]`) — только явный bukvar/reading path (`--with-words` в других tools).
