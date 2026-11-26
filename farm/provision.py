"""Подготовка SDK: скачать готовый архив или собрать из ветки Git, затем
зарегистрировать платформу в farm.toml."""

from __future__ import annotations

import hashlib
import os
import shutil
import subprocess
import sys
import tarfile
import time
import urllib.request
from pathlib import Path

from . import config

ARCH = {
    "ramips/mt7620": "mipsel_24kc",
    "ramips/mt7621": "mipsel_24kc",
    "ipq40xx/generic": "arm_cortex-a7_neon-vfpv4",
    "mediatek/filogic": "aarch64_cortex-a53",
    "x86/64": "x86_64",
}
MIRROR = "https://downloads.openwrt.org/releases"


class ProvisionError(Exception):
    pass


def log(msg: str) -> None:
    print(f"[{time.strftime('%H:%M:%S')}] {msg}", flush=True)


def _download(url: str, dest: Path, timeout: int = 300) -> None:
    dest.parent.mkdir(parents=True, exist_ok=True)
    tmp = dest.with_suffix(dest.suffix + ".part")
    try:
        with urllib.request.urlopen(url, timeout=timeout) as r, open(tmp, "wb") as fh:
            shutil.copyfileobj(r, fh)
    except OSError:
        proc = subprocess.run(
            ["curl", "-fL", "--connect-timeout", "20", "--max-time", str(timeout * 4), url, "-o", str(tmp)],
            capture_output=True,
        )
        if proc.returncode:
            raise ProvisionError(f"не скачалось {url}: {proc.stderr.decode(errors='replace')[-300:]}") from None
    tmp.replace(dest)


def _sha256(path: Path) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as fh:
        for chunk in iter(lambda: fh.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def _feeds_template(project: Path, name: str, sdk: Path, irz_local: Path) -> Path:
    default = sdk / "feeds.conf.default"
    text = default.read_text() if default.exists() else ""
    if "src-link irz" not in text:
        text = text.rstrip() + f"\nsrc-link irz {irz_local}\n"
    out = project / "feeds" / f"{name}.conf"
    out.parent.mkdir(parents=True, exist_ok=True)
    # src-link halo ферма добавляет сама при сборке
    out.write_text(text)
    return out


def _register(project: Path, name: str, body: dict, sdk: Path, feeds: Path, irz_local: Path) -> None:
    config.add_platform(project, name, {
        "board": body.get("board") or name,
        "target": body["target"],
        "arch": ARCH[body["target"]],
        "release": body["release"],
        "sdk": str(sdk),
        "feeds": str(_feeds_template(project, name, sdk, irz_local)),
        "extras": body.get("extras") or [],
        "brands": body.get("brands") or ["irzOS", "dnxOS"],
    })


def run(project: Path, body: dict) -> None:
    name = body["name"]
    target = body["target"]
    release = body["release"]
    if target not in ARCH:
        raise ProvisionError(f"неподдерживаемый target: {target}")
    home = Path.home()
    sdk_dest = home / f"sdk-{name}"
    irz_local = Path(os.path.expanduser(body.get("irz_local") or "~/sdk24/irz-local"))

    log(f"платформа {name}: target {target}, arch {ARCH[target]}, release {release}")
    if sdk_dest.exists() and any(sdk_dest.iterdir()):
        raise ProvisionError(f"каталог {sdk_dest} уже не пуст")

    if body.get("source") == "archive":
        base = f"{MIRROR}/{release}/targets/{target}"
        log(f"читаю {base}/sha256sums")
        sums_path = project / ".." / "cache" / "sha256sums"
        sums_text = _fetch_text(f"{base}/sha256sums")
        line = next(
            (l for l in sums_text.splitlines() if "openwrt-sdk-" in l and l.strip().endswith(".tar.zst")),
            "",
        )
        if not line:
            raise ProvisionError("в sha256sums нет SDK-архива для этого target")
        parts = line.split()
        digest, filename = parts[0], parts[-1].lstrip("*")
        archive = home / ".cache" / "ipk-farm" / filename
        log(f"скачиваю {filename}")
        _download(f"{base}/{filename}", archive)
        if _sha256(archive) != digest:
            raise ProvisionError("sha256 не совпал")
        log("sha256 совпал, распаковываю")
        _extract(archive, sdk_dest)
    elif body.get("source") == "git":
        repo = body.get("repo") or ""
        branch = body.get("branch") or "master"
        if not repo:
            raise ProvisionError("не указан git-репозиторий")
        work = home / f"sdk-src-{name}"
        log(f"git clone {repo} ({branch}) → {work}")
        proc = subprocess.run(
            ["git", "clone", "--depth", "1", "--branch", branch, repo, str(work)],
            capture_output=True, text=True,
            env={**os.environ, "GIT_TERMINAL_PROMPT": "0",
                 "GIT_SSH_COMMAND": "ssh -o BatchMode=yes -o ConnectTimeout=15"},
        )
        if proc.returncode:
            raise ProvisionError(f"git clone: {proc.stderr.strip()[-500:]}")
        conf = work / ".config"
        tgt, sub = target.split("/", 1)
        conf.write_text(
            f"CONFIG_TARGET_{tgt}=y\nCONFIG_TARGET_{tgt}_{sub.replace('/', '_')}=y\nCONFIG_SDK=y\n"
        )
        jobs = str(body.get("jobs") or os.cpu_count() or 8)
        log(f"make defconfig && make -j{jobs} (≈4–8 часов)")
        for cmd in (["make", "defconfig"], ["make", f"-j{jobs}"]):
            proc = subprocess.run(cmd, cwd=work, stdout=sys.stdout, stderr=subprocess.STDOUT)
            if proc.returncode:
                raise ProvisionError(f"{' '.join(cmd)}: код {proc.returncode}")
        archives = list((work / "bin" / "targets").rglob("openwrt-sdk-*.tar.zst"))
        if not archives:
            raise ProvisionError("сборка прошла, но openwrt-sdk-*.tar.zst не найден")
        log(f"SDK собран: {archives[0].name}, распаковываю")
        _extract(archives[0], sdk_dest)
    else:
        raise ProvisionError(f"неизвестный источник: {body.get('source')}")

    sdk = _single_dir(sdk_dest)
    if not (sdk / "scripts" / "feeds").exists():
        raise ProvisionError(f"в распакованном SDK нет scripts/feeds: {sdk}")
    _register(project, name, body, sdk, project / "feeds" / f"{name}.conf", irz_local)
    log(f"платформа {name} добавлена: {sdk}")


def _fetch_text(url: str, timeout: int = 60) -> str:
    try:
        with urllib.request.urlopen(url, timeout=timeout) as r:
            return r.read().decode(errors="replace")
    except OSError:
        proc = subprocess.run(["curl", "-fsSL", "--max-time", str(timeout), url], capture_output=True)
        if proc.returncode:
            raise ProvisionError(f"не читается {url}") from None
        return proc.stdout.decode(errors="replace")


def _extract(archive: Path, dest: Path) -> None:
    dest.mkdir(parents=True, exist_ok=True)
    if archive.suffix == ".zst":
        proc = subprocess.run(["tar", "--zstd", "-xf", str(archive), "-C", str(dest)])
        if proc.returncode:
            raise ProvisionError(f"tar --zstd: код {proc.returncode}")
        return
    with tarfile.open(archive) as tar:
        tar.extractall(dest)


def _single_dir(path: Path) -> Path:
    dirs = [p for p in path.iterdir() if p.is_dir()]
    if len(dirs) != 1:
        raise ProvisionError(f"в {path} ожидался один каталог SDK, найдено {len(dirs)}")
    return dirs[0]
