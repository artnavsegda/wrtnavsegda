"""buildbot.radiofid.ru: манифест артефактов и последняя сборка платформы.

Манифест один на весь buildbot (~12 МБ) и содержит дерево каталогов.
Кэшируем его на диск, чтобы не тянуть на каждый запрос.
"""

from __future__ import annotations

import json
import re
import shutil
import subprocess
import time
import urllib.request
from dataclasses import dataclass
from pathlib import Path

VERSION_RE = re.compile(r"(\d+\.\d+\.\d+(?:-[A-Za-z0-9.]+)?)")
_EXT = (".bin", ".itb", ".initramfs", ".json")


class BuildbotError(Exception):
    pass


@dataclass(frozen=True)
class BuildInfo:
    channel: str
    brand: str
    board: str
    number: int
    version: str
    feeds: tuple[str, ...]

    @property
    def path(self) -> str:
        return f"{self.channel}/{self.brand}/{self.board}/{self.number}"

    def feed_urls(self, base: str) -> dict[str, str]:
        base = base.rstrip("/")
        return {name: f"{base}/{self.path}/ipk/{name}" for name in self.feeds}


def _children(node: dict) -> dict[str, dict]:
    return {c["name"]: c for c in node.get("children", [])}


def fetch_manifest(url: str, cache: Path, max_age: int = 900, refresh: bool = False, timeout: int = 120) -> dict:
    """Скачать манифест, если кэш старше max_age (или refresh)."""
    url = url.rstrip("/") + "/manifest.json"
    fresh = cache.exists() and (time.time() - cache.stat().st_mtime) < max_age
    if not (fresh and not refresh):
        cache.parent.mkdir(parents=True, exist_ok=True)
        tmp = cache.with_suffix(".tmp")
        try:
            _download(url, tmp, timeout)
        except OSError as e:
            if cache.exists() and not refresh:
                pass  # работаем на старом кэше
            else:
                raise BuildbotError(f"buildbot недоступен: {url}: {e}") from e
        else:
            tmp.replace(cache)
    try:
        return json.loads(cache.read_text())
    except (OSError, json.JSONDecodeError) as e:
        raise BuildbotError(f"битый манифест {cache}: {e}") from e


def _download(url: str, tmp: Path, timeout: int) -> None:
    try:
        with urllib.request.urlopen(url, timeout=timeout) as r, open(tmp, "wb") as fh:
            while chunk := r.read(1 << 20):
                fh.write(chunk)
        return
    except OSError:
        # На macOS python-процессу бывает закрыт локальный сегмент сети,
        # а curl ходит; на Debian этот путь просто не понадобится.
        if not shutil.which("curl"):
            raise
    proc = subprocess.run(
        ["curl", "-fsSL", "--max-time", str(timeout), url, "-o", str(tmp)],
        capture_output=True,
    )
    if proc.returncode:
        raise OSError(proc.stderr.decode(errors="replace").strip() or "curl failed")


def find_latest(manifest: dict, channel: str, brand: str, board: str) -> BuildInfo:
    node = manifest
    for key in (channel, brand, board):
        children = _children(node)
        if key not in children:
            raise BuildbotError(f"в манифесте нет {channel}/{brand}/{board}")
        node = children[key]

    numbers = sorted(int(name) for name in _children(node) if name.isdigit())
    if not numbers:
        raise BuildbotError(f"у {channel}/{brand}/{board} нет сборок")

    number = numbers[-1]
    node = _children(node)[str(number)]

    ipk = _children(node).get("ipk")
    feeds = tuple(sorted(_children(ipk))) if ipk else ()
    return BuildInfo(
        channel=channel,
        brand=brand,
        board=board,
        number=number,
        version=_version(node, brand),
        feeds=feeds,
    )


def _version(node: dict, brand: str) -> str:
    best = ""
    for name in _children(node):
        if name.endswith((".json", ".manifest", ".buildinfo", ".initramfs", ".bom.cdx.json")):
            continue
        m = VERSION_RE.search(name)
        if m:
            v = m.group(1)
            for ext in _EXT:
                if v.endswith(ext):
                    v = v[: -len(ext)]
            if v and (not best or len(v) > len(best)):
                best = v
    return best
