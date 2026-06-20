#!/usr/bin/env python3
"""Local HTTP server for listen beat annotator (lightweight A/V timing UI)."""

from __future__ import annotations

import argparse
import json
import mimetypes
import sys
import webbrowser
from http import HTTPStatus
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import Any
from urllib.parse import urlparse

TOOLS = Path(__file__).resolve().parent
HTML = TOOLS / "listen_beat_annotator.html"


def _load_beats(path: Path | None) -> list[dict[str, Any]]:
    if path is None or not path.is_file():
        return []
    raw = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(raw, list):
        raise ValueError(f"{path}: expected JSON array")
    return [dict(row) for row in raw if isinstance(row, dict)]


def _manifest_chapter_beats(manifest: Path, chapter: int) -> list[dict[str, Any]]:
    for line in manifest.read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        scene = json.loads(line)
        if int(scene.get("chapter_index", -1)) == chapter:
            beats = scene.get("beats")
            if isinstance(beats, list):
                return [dict(b) for b in beats if isinstance(b, dict)]
    return []


class AnnotatorHandler(BaseHTTPRequestHandler):
    video_path: Path
    beats: list[dict[str, Any]]
    save_path: Path | None

    def log_message(self, fmt: str, *args: Any) -> None:
        sys.stderr.write(f"[annotator] {self.address_string()} - {fmt % args}\n")

    def _send_json(self, payload: Any, status: int = HTTPStatus.OK) -> None:
        body = json.dumps(payload, ensure_ascii=False).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def _send_bytes(self, data: bytes, content_type: str) -> None:
        self.send_response(HTTPStatus.OK)
        self.send_header("Content-Type", content_type)
        self.send_header("Content-Length", str(len(data)))
        self.end_headers()
        self.wfile.write(data)

    def do_GET(self) -> None:
        path = urlparse(self.path).path
        if path in ("/", "/index.html"):
            self._send_bytes(HTML.read_bytes(), "text/html; charset=utf-8")
            return
        if path == "/api/config":
            self._send_json(
                {
                    "video_url": "/video",
                    "video_label": str(self.video_path),
                    "beats": self.beats,
                    "save_path": str(self.save_path) if self.save_path else "",
                }
            )
            return
        if path == "/video":
            data = self.video_path.read_bytes()
            ctype = mimetypes.guess_type(str(self.video_path))[0] or "application/octet-stream"
            self._send_bytes(data, ctype)
            return
        self.send_error(HTTPStatus.NOT_FOUND, f"not found: {path}")

    def do_POST(self) -> None:
        path = urlparse(self.path).path
        if path != "/api/save":
            self.send_error(HTTPStatus.NOT_FOUND)
            return
        length = int(self.headers.get("Content-Length") or 0)
        raw = self.rfile.read(length)
        try:
            payload = json.loads(raw.decode("utf-8"))
            beats = payload.get("beats")
            if not isinstance(beats, list):
                raise ValueError("beats must be array")
            target = Path(str(payload.get("path") or self.save_path or "")).resolve()
            if self.save_path is not None and target != self.save_path.resolve():
                raise ValueError("save path not allowed")
            if not target.parent.is_dir():
                raise ValueError(f"parent missing: {target.parent}")
            target.write_text(json.dumps(beats, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
            self.beats = [dict(b) for b in beats if isinstance(b, dict)]
            self._send_json({"ok": True, "path": str(target), "beats": len(self.beats)})
        except (json.JSONDecodeError, ValueError, OSError) as exc:
            self._send_json({"error": str(exc)}, status=HTTPStatus.BAD_REQUEST)


def main() -> int:
    parser = argparse.ArgumentParser(description="Serve listen beat annotator UI")
    parser.add_argument("--video", type=Path, required=True, help="video file (mp4/webm)")
    parser.add_argument("--beats", type=Path, default=None, help="initial beats JSON")
    parser.add_argument("--manifest", type=Path, default=None, help="load beats from manifest chapter")
    parser.add_argument("--chapter", type=int, default=0)
    parser.add_argument("--save", type=Path, default=None, help="path for Save to server button")
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=8765)
    parser.add_argument("--open", action="store_true", help="open browser")
    args = parser.parse_args()

    video = args.video.resolve()
    if not video.is_file():
        print(f"video not found: {video}", file=sys.stderr)
        return 2

    beats: list[dict[str, Any]]
    if args.beats is not None:
        beats = _load_beats(args.beats.resolve())
    elif args.manifest is not None:
        beats = _manifest_chapter_beats(args.manifest.resolve(), args.chapter)
    else:
        beats = []

    save_path = args.save.resolve() if args.save else args.beats.resolve() if args.beats else None

    handler = AnnotatorHandler
    handler.video_path = video
    handler.beats = beats
    handler.save_path = save_path

    url = f"http://{args.host}:{args.port}/"
    server = ThreadingHTTPServer((args.host, args.port), handler)
    print(json.dumps({"url": url, "video": str(video), "beats": len(beats), "save": str(save_path or "")}, ensure_ascii=False))
    if args.open:
        webbrowser.open(url)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\nstopped")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
