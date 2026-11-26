"""Публикация сборки в opkg-фид: merge с текущим, индекс, подпись, атомарная замена."""

from __future__ import annotations

import fcntl
import gzip
import os
import shutil
import subprocess
from datetime import datetime
from pathlib import Path

from . import ipk, state
from .build import BuildError, acquire_lock
from .config import Farm


def publish_build(farm: Farm, manifest: dict, dry_run: bool = False) -> dict:
    feed = manifest["feed"]
    build_id = manifest["id"]
    dest = farm.publish_root / feed
    src = farm.builds_dir / str(build_id) / "ipk"
    sdk = Path(manifest["sdk"]["path"])
    key = farm.sign_key
    pub = key.with_suffix(".pub")

    if not manifest.get("packages"):
        raise BuildError("в манифесте нет пакетов — публиковать нечего")
    if not src.exists():
        raise BuildError(f"нет артефактов сборки: {src}")

    lock = acquire_lock(farm.locks_dir / f"publish-{feed}.lock")
    try:
        return _publish(farm, manifest, dest, src, sdk, key, pub, dry_run)
    finally:
        fcntl.flock(lock, fcntl.LOCK_UN)
        lock.close()


def _publish(farm, manifest, dest: Path, src: Path, sdk: Path, key: Path, pub: Path, dry_run: bool) -> dict:
    old = _index_versions(dest / "Packages")
    packages = manifest["packages"]

    violations = [
        f"{p['name']}: {p['version']} < опубликованной {old[p['name']]}"
        for p in packages
        if p["name"] in old and not ipk.newer(p["version"], old[p["name"]])
    ]
    if violations:
        raise BuildError("версии не растут: " + "; ".join(violations))

    if dry_run:
        return {"feed": dest.name, "packages": len(packages), "dry_run": True}

    dest.mkdir(parents=True, exist_ok=True)
    _drop_old_versions(dest, {p["name"]: p["version"] for p in packages})
    for p in packages:
        shutil.copy2(src / p["file"], dest / p["file"])

    env = os.environ.copy()
    bin_dir = sdk / "staging_dir" / "host" / "bin"
    env["PATH"] = f"{bin_dir}:{env.get('PATH', '')}"
    env["MKHASH"] = str(bin_dir / "mkhash")
    env["LC_ALL"] = "C"

    tmp = dest / "Packages.tmp"
    with open(tmp, "wb") as fh:
        proc = subprocess.run(
            [str(sdk / "scripts" / "ipkg-make-index.sh"), "."],
            cwd=dest, env=env, stdout=fh, stderr=subprocess.PIPE,
        )
    if proc.returncode:
        tmp.unlink(missing_ok=True)
        raise BuildError(f"ipkg-make-index.sh: {proc.stderr.decode(errors='replace')[-800:]}")

    gz = dest / "Packages.gz.tmp"
    with open(tmp, "rb") as rf, open(gz, "wb") as raw, gzip.GzipFile(
        filename="", mode="wb", fileobj=raw, mtime=0
    ) as wf:
        shutil.copyfileobj(rf, wf)

    sig = dest / "Packages.sig.tmp"
    proc = subprocess.run(
        ["usign", "-S", "-m", str(tmp), "-s", str(key)],
        env=env, capture_output=True,
    )
    if proc.returncode:
        raise BuildError(f"usign -S: {proc.stderr.decode(errors='replace')}")
    produced = Path(str(tmp) + ".sig")
    if not produced.exists():
        raise BuildError("usign не создал подпись")
    produced.replace(sig)

    if pub.exists():
        check = subprocess.run(["usign", "-V", "-m", str(tmp), "-p", str(pub)], env=env, capture_output=True)
        if check.returncode:
            raise BuildError(f"подпись не проверяется: {check.stderr.decode(errors='replace')}")

    tmp.replace(dest / "Packages")
    gz.replace(dest / "Packages.gz")
    sig.replace(dest / "Packages.sig")

    entry = _check_index(dest)
    conn = state.connect(farm.state_dir)
    state.record_publish(
        conn, dest.name, manifest["id"], datetime.now().astimezone().isoformat(timespec="seconds"),
        len(packages), {"files": [p["file"] for p in packages], "index": entry},
    )
    conn.close()
    return {"feed": dest.name, "packages": len(packages), "ts": datetime.now().isoformat(timespec="seconds")}


def _index_versions(path: Path) -> dict[str, str]:
    out: dict[str, str] = {}
    if not path.exists():
        return out
    name = ver = ""
    for line in path.read_text(errors="replace").splitlines():
        if line.startswith("Package:"):
            name = line.split(":", 1)[1].strip()
        elif line.startswith("Version:"):
            ver = line.split(":", 1)[1].strip()
        elif not line.strip() and name:
            out[name] = ver
            name = ver = ""
    if name:
        out[name] = ver
    return out


def _drop_old_versions(dest: Path, new: dict[str, str]) -> None:
    for f in dest.glob("*.ipk"):
        try:
            meta = ipk.read_meta(f)
        except ipk.IpkError:
            continue
        if meta.name in new and meta.version != new[meta.name]:
            f.unlink()


def _check_index(dest: Path) -> dict:
    listed = _index_versions(dest / "Packages")
    on_disk: dict[str, str] = {}
    for f in dest.glob("*.ipk"):
        try:
            meta = ipk.read_meta(f)
        except ipk.IpkError:
            continue
        on_disk[meta.name] = meta.version
    missing = [n for n in listed if n not in on_disk]
    stray = [n for n in on_disk if n not in listed]
    if missing or stray:
        raise BuildError(
            "индекс и файлы разошлись: "
            + ("нет файлов: " + ", ".join(missing) + "; " if missing else "")
            + ("нет в индексе: " + ", ".join(stray) if stray else "")
        )
    return {"packages": len(listed), "files": len(on_disk)}
