"""Bare-клоны репозиториев пакетов: история коммитов для выбранного пакета."""

from __future__ import annotations

import os
import re
import subprocess
import time
from pathlib import Path

from .config import Farm


class RepoError(Exception):
    pass


def _name(url: str) -> str:
    base = url.rstrip("/").split("/")[-1].removesuffix(".git")
    return re.sub(r"[^A-Za-z0-9._-]+", "-", base) or "repo"


def cache_dir(farm: Farm, url: str) -> Path:
    return farm.state_dir / "git" / _name(url)


ENV = {
    **os.environ,
    "GIT_TERMINAL_PROMPT": "0",
    "GIT_SSH_COMMAND": "ssh -o BatchMode=yes -o ConnectTimeout=10",
}


def _run(cmd: list[str], timeout: int = 30) -> subprocess.CompletedProcess:
    try:
        return subprocess.run(cmd, capture_output=True, text=True, timeout=timeout, env=ENV)
    except subprocess.TimeoutExpired:
        raise RepoError(f"репозиторий не отвечает: {' '.join(cmd[:4])}…") from None


def ensure(farm: Farm, url: str, ttl: int = 600) -> Path:
    if url.startswith("git://"):
        raise RepoError("git:// больше не поддерживается — история этого пакета недоступна")
    path = cache_dir(farm, url)
    if not (path / "HEAD").exists():
        path.parent.mkdir(parents=True, exist_ok=True)
        proc = _run(["git", "clone", "--bare", "--filter=blob:none", url, str(path)], timeout=45)
        if proc.returncode:
            raise RepoError(f"git clone {url}: {proc.stderr.strip()[:300]}")
    elif time.time() - (path / "HEAD").stat().st_mtime > ttl:
        _run(["git", "-C", str(path), "fetch", "--prune", "--tags", "origin"], timeout=45)
    return path


def info(farm: Farm, url: str, rev: str, limit: int = 40) -> dict:
    path = ensure(farm, url)

    def log(rev: str) -> str:
        proc = _run(
            ["git", "-C", str(path), "log", "-n", str(limit), "--date=short",
             "--format=%h\t%ad\t%s", rev],
            timeout=60,
        )
        return proc.stdout if proc.returncode == 0 else ""

    out = log(rev)
    if not out.strip():
        _run(["git", "-C", str(path), "fetch", "origin", rev], timeout=45)
        out = log(rev)
    commits = []
    for line in out.splitlines():
        parts = line.split("\t", 2)
        if len(parts) == 3:
            commits.append({"hash": parts[0], "date": parts[1], "subject": parts[2]})
    head = commits[0] if commits else None
    return {
        "repo": _name(url),
        "url": url,
        "rev": rev,
        "found": bool(head),
        "commit": head["hash"] if head else rev[:7],
        "date": head["date"] if head else "",
        "subject": head["subject"] if head else "",
        "commits": commits,
    }
