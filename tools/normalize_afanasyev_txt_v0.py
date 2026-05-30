#!/usr/bin/env python3
"""
Normalize Afanasyev fairy tales → one UTF-8 .txt per tale for SSS corpus ingest.

Sources:
  - lib.ru FB2 zip (default, 3 volumes 1855 edition on az.lib.ru)
  - local .fb2 / .fb2.zip / .txt

Output: lab/text/corpus/afanasyev/afan-v{vol}-n{no:03d}.txt
"""

from __future__ import annotations

import argparse
import io
import json
import re
import urllib.request
import xml.etree.ElementTree as ET
import zipfile
from html import unescape
from pathlib import Path
from typing import Any

from sss_text_tokenize_v0 import norm_text  # type: ignore

FB2_NS = "http://www.gribuser.ru/xml/fictionbook/2.1"

LIBRU_FB2_ZIPS: list[tuple[str, int]] = [
    ("http://az.lib.ru/a/afanasxew_a_n/afanasxew_a_n-text_1855_skazki1.fb2.zip", 1),
    ("http://az.lib.ru/a/afanasxew_a_n/afanasxew_a_n-text_1855_skazki2.fb2.zip", 2),
    ("http://az.lib.ru/a/afanasxew_a_n/afanasxew_a_n-text_1855_skazki3.fb2.zip", 3),
]

_TALE_TITLE_RE = re.compile(r"^No\s+(\d+)", re.IGNORECASE)
_GROUP_TITLE_RE = re.compile(r"\(No\s+(\d+)\s*[-–—]\s*(\d+)\)", re.IGNORECASE)
_FOOTNOTE_INLINE_RE = re.compile(r"\[\d+\]")
_SCHOLARLY_TAIL_RE = re.compile(
    r"^(Место записи|AT\s+\d|Ср\.|Ср\s|Сказки,|Текст\s|Зап\.|Запись|Список сокращений)",
    re.IGNORECASE,
)
_TALE_MARKER_TXT_RE = re.compile(
    r"^(?:####\s*)?(?:No|№)\s*(\d+)(?:\[\d+\])?\s*$",
    re.IGNORECASE | re.MULTILINE,
)


def _local_tag(tag: str) -> str:
    return tag.rsplit("}", 1)[-1]


def _text_nodes(elem: ET.Element) -> str:
    parts: list[str] = []
    if elem.text:
        parts.append(elem.text)
    for child in elem:
        if _local_tag(child.tag) in ("style", "a"):
            if child.text:
                parts.append(child.text)
            if child.tail:
                parts.append(child.tail)
            continue
        parts.append(_text_nodes(child))
        if child.tail:
            parts.append(child.tail)
    return "".join(parts)


def _clean_line(line: str) -> str:
    line = unescape(line)
    line = _FOOTNOTE_INLINE_RE.sub("", line)
    line = re.sub(r"\(\s*sic\s*\)", "", line, flags=re.I)
    line = line.replace("\ufffd", "").replace("�", "")
    line = line.replace("\u00ad", "")  # soft hyphen
    line = re.sub(r"\s+", " ", line).strip()
    return line


def _clean_body(paragraphs: list[str], *, strip_scholarly: bool) -> str:
    lines = [_clean_line(p) for p in paragraphs if _clean_line(p)]
    if strip_scholarly:
        trimmed: list[str] = []
        for ln in lines:
            if _SCHOLARLY_TAIL_RE.match(ln) and len(trimmed) >= 3:
                break
            trimmed.append(ln)
        lines = trimmed
    if not lines:
        return ""
    return norm_text("\n\n".join(lines))


def _section_title(section: ET.Element) -> str:
    for child in section:
        if _local_tag(child.tag) == "title":
            return _clean_line(_text_nodes(child))
    return ""


def _section_paragraphs(section: ET.Element) -> list[str]:
    out: list[str] = []
    for child in section:
        tag = _local_tag(child.tag)
        if tag == "title":
            continue
        if tag == "p":
            t = _clean_line(_text_nodes(child))
            if t:
                out.append(t)
        elif tag == "empty-line":
            continue
        elif tag == "section":
            out.extend(_section_paragraphs(child))
    return out


def parse_fb2(data: bytes, *, volume: int, strip_scholarly: bool) -> list[dict[str, Any]]:
    root = ET.fromstring(data)
    body = None
    for elem in root.iter():
        if _local_tag(elem.tag) == "body":
            body = elem
            break
    if body is None:
        return []

    tales: list[dict[str, Any]] = []
    current_group = ""
    in_tales = False

    for section in body:
        if _local_tag(section.tag) != "section":
            continue
        title = _section_title(section)
        if title and "Тексты сказок" in title:
            in_tales = True
            continue
        if not in_tales:
            continue

        if title and _GROUP_TITLE_RE.search(title):
            current_group = title
            continue

        m = _TALE_TITLE_RE.match(title or "")
        if not m:
            continue

        no = int(m.group(1))
        body_text = _clean_body(_section_paragraphs(section), strip_scholarly=strip_scholarly)
        if len(body_text) < 40:
            continue
        tales.append(
            {
                "volume": volume,
                "no": no,
                "group": current_group,
                "title": title,
                "text": body_text,
            }
        )
    return tales


def parse_plain_txt(text: str, *, volume: int, strip_scholarly: bool) -> list[dict[str, Any]]:
    raw = norm_text(text)
    markers = list(_TALE_MARKER_TXT_RE.finditer(raw))
    if not markers:
        return []

    tales: list[dict[str, Any]] = []
    current_group = ""
    for i, m in enumerate(markers):
        no = int(m.group(1))
        start = m.end()
        end = markers[i + 1].start() if i + 1 < len(markers) else len(raw)
        chunk = raw[start:end].strip()
        lines = chunk.splitlines()
        body_lines: list[str] = []
        for ln in lines:
            cl = _clean_line(ln)
            if not cl:
                if body_lines and body_lines[-1] != "":
                    body_lines.append("")
                continue
            if _GROUP_TITLE_RE.search(cl) and not body_lines:
                current_group = cl
                continue
            if cl.startswith("####") or _TALE_TITLE_RE.match(cl):
                continue
            body_lines.append(cl)
        body_text = _clean_body([x for x in body_lines if x != ""], strip_scholarly=strip_scholarly)
        if len(body_text) < 40:
            continue
        tales.append(
            {
                "volume": volume,
                "no": no,
                "group": current_group,
                "title": f"No {no}",
                "text": body_text,
            }
        )
    return tales


def load_fb2_source(path: Path) -> bytes:
    if path.suffix.lower() == ".zip" or path.name.lower().endswith(".fb2.zip"):
        with zipfile.ZipFile(path) as zf:
            name = next(n for n in zf.namelist() if n.lower().endswith(".fb2"))
            return zf.read(name)
    return path.read_bytes()


def download_url(url: str, *, timeout: int = 120) -> bytes:
    req = urllib.request.Request(url, headers={"User-Agent": "casa-ontology-payload/afanasyev-normalizer"})
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        return resp.read()


def read_source(path: Path, *, volume: int, strip_scholarly: bool) -> list[dict[str, Any]]:
    suffix = path.suffix.lower()
    if suffix == ".txt":
        text = path.read_text(encoding="utf-8", errors="replace")
        if "\ufffd" in text[:2000]:
            text = path.read_text(encoding="cp1251", errors="replace")
        return parse_plain_txt(text, volume=volume, strip_scholarly=strip_scholarly)
    data = load_fb2_source(path)
    return parse_fb2(data, volume=volume, strip_scholarly=strip_scholarly)


def tale_filename(tale: dict[str, Any]) -> str:
    vol = int(tale["volume"])
    no = int(tale["no"])
    return f"afan-v{vol}-n{no:03d}.txt"


def write_tales(tales: list[dict[str, Any]], out_dir: Path) -> list[Path]:
    out_dir.mkdir(parents=True, exist_ok=True)
    written: list[Path] = []
    for tale in tales:
        fp = out_dir / tale_filename(tale)
        header = ""
        if tale.get("group"):
            header = f"{tale['group']}\n\n"
        fp.write_text(f"{header}{tale['text']}\n", encoding="utf-8")
        written.append(fp)
    return written


def fetch_libru_volumes(
    volumes: list[int],
    *,
    cache_dir: Path | None,
    strip_scholarly: bool,
) -> list[dict[str, Any]]:
    all_tales: list[dict[str, Any]] = []
    for url, vol in LIBRU_FB2_ZIPS:
        if vol not in volumes:
            continue
        cache_path = cache_dir / f"skazki{vol}.fb2.zip" if cache_dir else None
        if cache_path and cache_path.exists():
            data = cache_path.read_bytes()
        else:
            data = download_url(url)
            if cache_path:
                cache_dir.mkdir(parents=True, exist_ok=True)
                cache_path.write_bytes(data)
        with zipfile.ZipFile(io.BytesIO(data)) as zf:
            fb2_name = next(n for n in zf.namelist() if n.lower().endswith(".fb2"))
            fb2_bytes = zf.read(fb2_name)
        all_tales.extend(parse_fb2(fb2_bytes, volume=vol, strip_scholarly=strip_scholarly))
    return all_tales


def main() -> None:
    p = argparse.ArgumentParser(description="Normalize Afanasyev corpus → per-tale UTF-8 txt")
    p.add_argument("--out-dir", type=Path, default=Path("lab/text/corpus/afanasyev"))
    p.add_argument("--cache-dir", type=Path, default=Path("lab/text/_cache/afanasyev"))
    p.add_argument("--download-libru", action="store_true", help="Fetch 3 volumes from az.lib.ru (fb2.zip)")
    p.add_argument("--volumes", default="1,2,3", help="Which lib.ru volumes (default 1,2,3)")
    p.add_argument("--local", type=Path, nargs="+", default=None, help="Local fb2/fb2.zip/txt; use name skazkiN.* or pass --volume")
    p.add_argument("--volume", type=int, default=1, help="Volume number for single --local file")
    p.add_argument("--limit", type=int, default=0, help="Write only first N tales (0=all)")
    p.add_argument("--keep-scholarly", action="store_true", help="Keep AT / place-of-recording tails")
    p.add_argument("--manifest", type=Path, default=None)
    p.add_argument("--dry-run", action="store_true")
    args = p.parse_args()

    strip_scholarly = not args.keep_scholarly
    volumes = [int(x.strip()) for x in args.volumes.split(",") if x.strip()]

    tales: list[dict[str, Any]] = []
    if args.local:
        for i, path in enumerate(args.local):
            vol = args.volume if len(args.local) == 1 else (i + 1)
            m = re.search(r"skazki(\d+)", path.name, re.I)
            if m:
                vol = int(m.group(1))
            tales.extend(read_source(path.resolve(), volume=vol, strip_scholarly=strip_scholarly))
    elif args.download_libru:
        tales = fetch_libru_volumes(volumes, cache_dir=args.cache_dir, strip_scholarly=strip_scholarly)
    else:
        p.error("Use --download-libru or --local PATH")

    tales.sort(key=lambda t: (int(t["volume"]), int(t["no"])))
    if args.limit > 0:
        tales = tales[: args.limit]

    report = {
        "source": "libru-fb2" if args.download_libru else "local",
        "volumes": sorted({int(t["volume"]) for t in tales}),
        "tales_parsed": len(tales),
        "out_dir": str(args.out_dir),
        "files": [tale_filename(t) for t in tales],
    }

    if args.dry_run:
        report["sample"] = tales[:2]
        print(json.dumps(report, ensure_ascii=False, indent=2))
        return

    written = write_tales(tales, args.out_dir)
    report["written"] = len(written)
    if args.manifest:
        args.manifest.parent.mkdir(parents=True, exist_ok=True)
        args.manifest.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps(report, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
