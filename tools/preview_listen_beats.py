#!/usr/bin/env python3
"""Human review: HTML gallery + audio snippet per beat (before ingest)."""

from __future__ import annotations

import argparse
import html
import json
import shutil
import subprocess
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
if str(REPO) not in sys.path:
    sys.path.insert(0, str(REPO))

from casa.domain.listen_beat_model import BEAT_KIND_MOTION, beat_kind, normalize_keyframes
from casa.domain.listen_beat_verify import format_beat_report, validate_scene_beats


def _ffmpeg() -> str:
    path = shutil.which("ffmpeg")
    if not path:
        raise RuntimeError("ffmpeg not found on PATH")
    return path


def _extract_audio_snippet(
    wav_path: Path,
    *,
    t0_abs: float,
    t1_abs: float,
    out_wav: Path,
) -> bool:
    out_wav.parent.mkdir(parents=True, exist_ok=True)
    cmd = [
        _ffmpeg(),
        "-y",
        "-hide_banner",
        "-loglevel",
        "error",
        "-ss",
        f"{t0_abs:.3f}",
        "-to",
        f"{t1_abs:.3f}",
        "-i",
        str(wav_path),
        "-ac",
        "1",
        "-ar",
        "16000",
        str(out_wav),
    ]
    proc = subprocess.run(cmd, capture_output=True, text=True, encoding="utf-8", errors="replace")
    return proc.returncode == 0 and out_wav.is_file()


def _build_html(
    *,
    title: str,
    scene_id: str,
    cards: list[dict],
    check_ok: bool,
) -> str:
    status = "PASS" if check_ok else "FAIL"
    rows = []
    for c in cards:
        cid = html.escape(c["id"])
        crange = html.escape(c["range"])
        cdur = html.escape(c["dur"])
        caudio = html.escape(c["audio"])
        is_motion = bool(c.get("motion_steps"))
        if is_motion:
            steps_json = html.escape(json.dumps(c["motion_steps"], ensure_ascii=False))
            img_html = (
                f'<div class="motion-view" data-steps="{steps_json}">'
                f'<img class="motion-frame" src="{html.escape(c["img"])}" alt="{cid}"/>'
                f'<span class="kf-label"></span></div>'
            )
        else:
            img_html = f'<img src="{html.escape(c["img"])}" alt="{cid}"/>'
        rows.append(
            f"""
            <article class="beat" data-beat="{cid}">
              <header>
                <strong>{cid}</strong>
                <span>{crange}</span>
                <span class="dur">{cdur}</span>
              </header>
              <div class="imgs">{img_html}</div>
              <audio controls preload="none" src="{caudio}"></audio>
            </article>
            """
        )
    return f"""<!DOCTYPE html>
<html lang="ru">
<head>
  <meta charset="utf-8"/>
  <title>{html.escape(title)} — beat preview</title>
  <style>
    body {{ font-family: system-ui, sans-serif; margin: 1.5rem; background: #111; color: #eee; }}
    h1 {{ font-size: 1.1rem; font-weight: 600; }}
    .meta {{ color: #aaa; margin-bottom: 1rem; }}
    .grid {{ display: grid; grid-template-columns: repeat(auto-fill, minmax(280px, 1fr)); gap: 1rem; }}
    .beat {{ background: #1c1c1c; border-radius: 8px; padding: 0.75rem; }}
    .beat header {{ display: flex; flex-wrap: wrap; gap: 0.5rem; margin-bottom: 0.5rem; font-size: 0.85rem; }}
    .dur {{ color: #8cf; }}
    .imgs img, .motion-frame {{ width: 100%; border-radius: 4px; background: #000; }}
    .motion-view {{ position: relative; }}
    .kf-label {{ display: block; font-size: 11px; color: #8cf; margin-top: 4px; min-height: 1.2em; }}
    audio {{ width: 100%; margin-top: 0.5rem; }}
    .fail {{ color: #f88; }}
    .pass {{ color: #8f8; }}
  </style>
</head>
<body>
  <h1>{html.escape(title)}</h1>
  <p class="meta">scene: {html.escape(scene_id)} · beats: {len(cards)} · gate: <span class="{"pass" if check_ok else "fail"}">{status}</span></p>
  <p class="meta">Paired = статичный кадр. Motion = при play звук кадры переключаются по keyframes (stepped, как в анимации).</p>
  <div class="grid">
    {''.join(rows)}
  </div>
  <script>
    function activeStep(steps, t) {{
      let idx = 0;
      for (let i = 0; i < steps.length; i++) {{
        if (t + 1e-4 >= steps[i].t) idx = i;
      }}
      return steps[idx];
    }}
    document.querySelectorAll(".beat").forEach((beat) => {{
      const audio = beat.querySelector("audio");
      const view = beat.querySelector(".motion-view");
      if (!audio || !view) return;
      const steps = JSON.parse(view.dataset.steps || "[]");
      if (!steps.length) return;
      const img = view.querySelector(".motion-frame");
      const label = view.querySelector(".kf-label");
      const sync = () => {{
        const s = activeStep(steps, audio.currentTime || 0);
        if (s && img.src.indexOf(s.src) < 0) img.src = s.src;
        if (label) label.textContent = s ? `kf @${{s.t.toFixed(2)}}s` + (s.note ? ` · ${{s.note}}` : "") : "";
      }};
      audio.addEventListener("timeupdate", sync);
      audio.addEventListener("seeked", sync);
      audio.addEventListener("play", sync);
    }});
  </script>
</body>
</html>
"""


def preview_chapter(
    scene: dict,
    bundle_dir: Path,
    out_dir: Path,
    *,
    extract_audio: bool = True,
) -> Path:
    bundle_dir = bundle_dir.resolve()
    out_dir = out_dir.resolve()
    out_dir.mkdir(parents=True, exist_ok=True)

    check = validate_scene_beats(scene, bundle_dir)
    report_path = out_dir / "verify.txt"
    title = str(scene.get("chapter_title") or scene.get("caption") or scene.get("id") or "")
    report_path.write_text(format_beat_report(check, scene_title=title) + "\n", encoding="utf-8")

    chapter_t0 = float(scene.get("t0") or 0.0)
    wav_name = str(scene.get("wav") or "audio.wav")
    wav_path = bundle_dir / wav_name
    if extract_audio and not wav_path.is_file():
        raise FileNotFoundError(wav_path)

    cards: list[dict[str, str]] = []
    beats = scene.get("beats") or []
    for beat in beats:
        if not isinstance(beat, dict):
            continue
        bid = str(beat.get("id") or "b000")
        bt0 = float(beat["t0"])
        bt1 = float(beat["t1"])
        note = str(beat.get("note") or "").strip()
        note_s = f" · {html.escape(note)}" if note else ""
        kind = beat_kind(beat)
        img_names: list[str] = []
        keyframes: list[dict] = []
        ft_s = ""
        if kind == BEAT_KIND_MOTION:
            keyframes = normalize_keyframes(beat)
            ft_bits = []
            for ki, kf in enumerate(keyframes):
                rel_img = str(kf.get("path") or "")
                src_img = bundle_dir / rel_img
                if not src_img.is_file():
                    continue
                img_name = f"{bid}-k{ki}.jpg"
                shutil.copy2(src_img, out_dir / img_name)
                img_names.append(img_name)
                if "frame_t" in kf:
                    ft_bits.append(f"@{float(kf['frame_t']):.1f}s")
            ft_s = f" · motion {len(img_names)}: {' '.join(ft_bits)}" if ft_bits else ""
        else:
            ft = beat.get("frame_t")
            ft_s = f" · кадр@{float(ft):.1f}s" if ft is not None else ""
            rel_img = str(beat.get("path") or "")
            src_img = bundle_dir / rel_img
            if src_img.is_file():
                img_name = f"{bid}.jpg"
                shutil.copy2(src_img, out_dir / img_name)
                img_names.append(img_name)
        if not img_names:
            continue
        audio_rel = ""
        if extract_audio:
            audio_name = f"{bid}.wav"
            ok = _extract_audio_snippet(
                wav_path,
                t0_abs=chapter_t0 + bt0,
                t1_abs=chapter_t0 + bt1,
                out_wav=out_dir / audio_name,
            )
            if ok:
                audio_rel = audio_name
        card: dict = {
                "id": bid,
                "range": f"{bt0:.2f}–{bt1:.2f} s{ft_s}{note_s}",
                "dur": f"{bt1 - bt0:.2f} s",
                "img": img_names[0],
                "imgs": img_names,
                "audio": audio_rel,
            }
        if kind == BEAT_KIND_MOTION and keyframes:
            steps = []
            for ki, kf in enumerate(keyframes):
                if ki >= len(img_names):
                    break
                steps.append(
                    {
                        "t": round(float(kf["frame_t"]) - bt0, 3),
                        "src": img_names[ki],
                        "note": str(kf.get("note") or ""),
                    }
                )
            if len(steps) >= 2:
                card["motion_steps"] = steps
        cards.append(card)

    html_path = out_dir / "index.html"
    html_path.write_text(
        _build_html(
            title=title,
            scene_id=str(scene.get("id") or ""),
            cards=cards,
            check_ok=check.ok,
        ),
        encoding="utf-8",
    )
    return html_path


def main() -> int:
    parser = argparse.ArgumentParser(description="Build human-review HTML for listen beats")
    parser.add_argument("--manifest", type=Path, required=True)
    parser.add_argument("--chapters", type=str, default="0", help="comma indices, default 0")
    parser.add_argument("--out-dir", type=Path, default=None, help="default: bundle/preview/chNN")
    parser.add_argument("--no-audio", action="store_true", help="images only")
    args = parser.parse_args()

    manifest = args.manifest.resolve()
    bundle_dir = manifest.parent
    want = {int(x.strip()) for x in args.chapters.split(",") if x.strip()}

    built: list[Path] = []
    for line in manifest.read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        scene = json.loads(line)
        idx = scene.get("chapter_index")
        if idx is None or int(idx) not in want:
            continue
        out = args.out_dir or (bundle_dir / "preview" / f"ch{int(idx):02d}")
        html_path = preview_chapter(
            scene,
            bundle_dir,
            out,
            extract_audio=not args.no_audio,
        )
        built.append(html_path)
        print(f"preview: {html_path}")
        print(f"verify:  {html_path.parent / 'verify.txt'}")

    if not built:
        print("no chapters matched", file=sys.stderr)
        return 2
    print("\nОткрой index.html в браузере: картинка + звук на каждый beat.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
