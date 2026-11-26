"""Собрать манифест из уже собранных ipk в SDK (восстановление после сбоя на сборке)."""

from __future__ import annotations

import json
import re
import shutil
import subprocess
from datetime import datetime
from pathlib import Path

from . import buildbot, ipk, state
from .build import BuildError, SDK_FEED, _sha256, json_dumps, now
from .config import Farm
from .sources import source_map


def _git(repo: Path, *args: str) -> str:
    try:
        return subprocess.run(
            ["git", "-C", str(repo), *args], capture_output=True, text=True, check=True
        ).stdout.strip()
    except subprocess.SubprocessError:
        return ""


def collect(
    farm: Farm,
    flavor_name: str,
    release: str,
    build_id: int | None = None,
    ref: str = "",
    publish: bool = False,
    dry_run: bool = False,
) -> dict:
    flavor = farm.flavor(flavor_name)
    platform = farm.platform(flavor.sdk_platform)
    sdk = platform.sdk
    if not sdk:
        raise BuildError(f"у платформы {platform.name} нет SDK")
    pkgdir = sdk / "bin" / "packages" / platform.arch / SDK_FEED
    if not pkgdir.exists():
        raise BuildError(f"нет каталога сборки {pkgdir}")

    since = 0.0
    if build_id is not None:
        conn0 = state.connect(farm.state_dir)
        row0 = conn0.execute("select started from builds where id=?", (build_id,)).fetchone()
        if row0:
            since = datetime.fromisoformat(row0["started"]).timestamp()
        conn0.close()

    files: list[tuple[Path, ipk.IpkMeta]] = []
    seen: set[str] = set()
    for f in sorted(pkgdir.glob("*.ipk")):
        try:
            meta = ipk.read_meta(f)
        except ipk.IpkError:
            continue
        fresh = f.stat().st_mtime >= since - 5 if since else meta.version.endswith(release)
        if not fresh:
            continue
        if meta.name in seen:
            continue
        seen.add(meta.name)
        files.append((f, meta))
    for pattern in platform.extras:
        for f in sorted((sdk / "bin" / "packages" / platform.arch).glob(pattern)):
            meta = ipk.read_meta(f)
            if meta.name not in seen:
                seen.add(meta.name)
                files.append((f, meta))
    if not files:
        raise BuildError(f"в {pkgdir} нет ipk с release {release}")

    bad = [f"{m.name}: {m.arch}" for _, m in files if m.arch not in ("all", platform.arch)]
    if bad:
        raise BuildError("arch не совпадает: " + ", ".join(bad))

    head = ref or _git(farm.repo, "rev-parse", "HEAD")
    branch = _git(farm.repo, "rev-parse", "--abbrev-ref", "HEAD")
    halo = _git(farm.repo, "show", f"{head}:halo.mk")
    pinned = re.search(r"^HALO_PINNED:=([0-9a-f]{40})", halo, re.M)
    hbranch = re.search(r"^HALO_BRANCH\?=(\S+)", halo, re.M)

    bb: dict = {}
    try:
        manifest_bb = buildbot.fetch_manifest(farm.buildbot, farm.state_dir / "buildbot.json")
        info = buildbot.find_latest(manifest_bb, farm.channel, flavor.brand, platform.board)
        bb = {"path": info.path, "number": info.number, "version": info.version}
    except buildbot.BuildbotError:
        pass

    conn = state.connect(farm.state_dir)
    if build_id is None:
        build_id = state.start_build(conn, flavor.name, platform.name, now(), release, Path(""))
        started = now()
    else:
        row = conn.execute("select * from builds where id=?", (build_id,)).fetchone()
        if not row:
            raise BuildError(f"нет сборки #{build_id}")
        started = row["started"]
        conn.execute("delete from packages where build_id=?", (build_id,))
        conn.commit()

    sources = source_map(farm, flavor)
    out_dir = farm.builds_dir / str(build_id)
    ipk_dir = out_dir / "ipk"
    ipk_dir.mkdir(parents=True, exist_ok=True)

    packages = []
    for f, meta in files:
        target = ipk_dir / f.name
        if not dry_run:
            shutil.copy2(f, target)
        digest = _sha256(target) if target.exists() else ""
        src = sources.get(meta.name, {})
        packages.append(
            {
                "name": meta.name,
                "version": meta.version,
                "arch": meta.arch,
                "file": f.name,
                "sha256": digest,
                "size": target.stat().st_size if target.exists() else 0,
                "depends": meta.depends,
                "source_branch": src.get("repo", ""),
                "source_commit": src.get("commit", ""),
            }
        )
        if not dry_run:
            state.add_package(
                conn, build_id, meta, f.name, digest,
                src.get("repo", ""), src.get("commit", ""),
            )
    if not dry_run:
        conn.commit()

    manifest = {
        "id": build_id,
        "flavor": flavor.name,
        "feed": flavor.feed,
        "brand": flavor.brand,
        "platform": platform.name,
        "build_platform": platform.name,
        "channel": farm.channel,
        "release": release,
        "started": started,
        "finished": now(),
        "status": "ok",
        "refs": {
            "repo_head": head,
            "repo_branch": branch,
            "halo_pinned": pinned.group(1) if pinned else "",
            "halo_branch": hbranch.group(1) if hbranch else "",
        },
        "buildbot": bb,
        "sdk": {
            "path": str(sdk),
            "target": platform.target,
            "arch": platform.arch,
            "release": platform.release,
        },
        "checks": [{"name": "arch", "ok": True, "detail": "all / " + platform.arch}],
        "packages": packages,
    }

    if not dry_run:
        (out_dir / "manifest.json").write_text(json_dumps(manifest), encoding="utf-8")
        state.finish_build(conn, build_id, "ok", manifest["finished"], manifest)
        if publish:
            from .publish import publish_build

            publish_build(farm, manifest)
    return manifest
