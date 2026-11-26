"""Источник пакета: ветка/репозиторий и коммит из Makefile."""

from __future__ import annotations

import re
from pathlib import Path

from .config import Farm, Flavor


def makefile_packages(path: Path) -> list[str]:
    if not path.exists():
        return []
    text = path.read_text(errors="replace")
    m = re.search(r"^PKG_NAME\s*:?=\s*(\S+)", text, re.M)
    pkg = m.group(1) if m else ""
    names = []
    for m in re.finditer(r"BuildPackage,\s*(\$\(PKG_NAME\)[^,)\s]*|[\w.-]+)", text):
        name = m.group(1).replace("$(PKG_NAME)", pkg)
        if name:
            names.append(name)
    return names


def _pin(text: str, prefix: str) -> tuple[str, str]:
    b = re.search(rf"^{prefix}_BRANCH\??\s*:?=\s*(\S+)", text, re.M)
    h = re.search(rf"^{prefix}_PINNED\s*:?=\s*([0-9a-f]{{7,40}})", text, re.M)
    return (b.group(1) if b else ""), (h.group(1) if h else "")


def _url(text: str) -> str:
    m = re.search(r"^PKG_SOURCE_URL\s*:?=\s*(\S+)", text, re.M)
    return m.group(1) if m else ""


def source_map(farm: Farm, flavor: Flavor) -> dict[str, dict]:
    out: dict[str, dict] = {}
    halo = farm.repo / "halo.mk"
    halo_text = halo.read_text(errors="replace") if halo.exists() else ""
    for d in farm.packages(flavor):
        mk = farm.repo / d / "Makefile"
        text = mk.read_text(errors="replace") if mk.exists() else ""
        names = makefile_packages(mk) or [d]
        if "../halo.mk" in text:
            repo, commit = _pin(halo_text, "HALO")
            url = _url(halo_text)
        elif "AURORA_PINNED" in text:
            repo, commit = _pin(text, "AURORA")
            url = _url(text)
        else:
            h = re.search(r"^PKG_SOURCE_VERSION\s*:?=\s*([0-9a-f]{7,40})", text, re.M)
            url = _url(text)
            repo = url.rstrip("/").split("/")[-1].removesuffix(".git") if url else ""
            commit = h.group(1) if h else ""
        info = {"repo": repo or "в репо", "commit": commit[:7], "commit_full": commit, "url": url}
        for n in names:
            out[n] = info
    return out
