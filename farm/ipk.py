"""Разбор .ipk (ar + control.tar.*) и сравнение версий opkg."""

from __future__ import annotations

import io
import re
import tarfile
from dataclasses import dataclass
from pathlib import Path

AR_MAGIC = b"!<arch>\n"


class IpkError(Exception):
    pass


@dataclass(frozen=True)
class IpkMeta:
    name: str
    version: str
    arch: str
    depends: str = ""


def read_meta(path: Path) -> IpkMeta:
    data = path.read_bytes()
    if not data.startswith(AR_MAGIC):
        raise IpkError(f"{path.name}: не ar-архив")
    off = len(AR_MAGIC)
    while off + 60 <= len(data):
        header = data[off : off + 60]
        raw_name = header[0:16].decode("ascii", "replace").strip()
        try:
            size = int(header[48:58].decode("ascii", "replace").strip())
        except ValueError as e:
            raise IpkError(f"{path.name}: битый заголовок ar") from e
        body = data[off + 60 : off + 60 + size]
        name = raw_name.rstrip("/")
        if name.startswith("#1/"):
            n = int(name[3:])
            name, body = body[:n].decode().strip(), body[n:]
        if name.startswith("control.tar"):
            fields = _control_fields(body, path)
            return IpkMeta(
                name=fields.get("Package", ""),
                version=fields.get("Version", ""),
                arch=fields.get("Architecture", ""),
                depends=fields.get("Depends", ""),
            )
        off += 60 + size + (size % 2)
    raise IpkError(f"{path.name}: нет control.tar")


def _control_fields(blob: bytes, path: Path) -> dict[str, str]:
    try:
        with tarfile.open(fileobj=io.BytesIO(blob)) as tar:
            member = next((m for m in tar.getmembers() if m.name in ("./control", "control")), None)
            if member is None:
                raise IpkError(f"{path.name}: в control.tar нет control")
            text = tar.extractfile(member).read().decode("utf-8", "replace")
    except (tarfile.TarError, OSError) as e:
        raise IpkError(f"{path.name}: не читается control.tar: {e}") from e

    fields: dict[str, str] = {}
    key = ""
    for line in text.splitlines():
        if not line:
            continue
        if line[0] in " \t" and key:
            fields[key] += " " + line.strip()
            continue
        k, sep, v = line.partition(":")
        if not sep:
            continue
        key = k.strip()
        fields[key] = v.strip()
    return fields


def version_key(version: str):
    """Ключ сравнения в духе opkg: [epoch:]version[-release]."""
    epoch_s, sep, rest = version.partition(":")
    if not sep:
        epoch_s, rest = "0", version
    try:
        epoch = int(epoch_s)
    except ValueError:
        epoch = 0
    base, _, release = rest.rpartition("-")
    if not base:
        base, release = rest, ""
    return (epoch, _tokens(base), _tokens(release))


def _tokens(s: str) -> tuple:
    out = []
    for part in re.findall(r"\d+|[A-Za-z]+", s):
        out.append((0, int(part)) if part.isdigit() else (1, part.lower()))
    return tuple(out)


def newer(new: str, old: str) -> bool:
    return version_key(new) > version_key(old)
