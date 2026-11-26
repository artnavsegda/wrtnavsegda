"""Сборка фида: SDK → feeds → make → манифест → (опционально) публикация."""

from __future__ import annotations

import fcntl
import hashlib
import json
import os
import re
import shutil
import subprocess
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path

from . import buildbot, ipk, state
from .config import Farm, Flavor, Platform

SDK_FEED = "halo"  # имя src-link в feeds.conf SDK, одинаковое для обоих flavor


class BuildError(Exception):
    pass


@dataclass
class Options:
    only: tuple[str, ...] = ()
    release: str | None = None
    dry_run: bool = False
    publish: bool = False
    feeds: bool = True
    jobs: int | None = None
    allow_dirty: bool = False
    refresh_buildbot: bool = False


@dataclass
class Result:
    build_id: int
    manifest: dict
    published: dict | None = None


def utc_release() -> str:
    return datetime.now(timezone.utc).strftime("%y%m%d%H%M")


def now() -> str:
    return datetime.now().astimezone().isoformat(timespec="seconds")


def acquire_lock(path: Path):
    path.parent.mkdir(parents=True, exist_ok=True)
    fh = open(path, "w")
    try:
        fcntl.flock(fh, fcntl.LOCK_EX | fcntl.LOCK_NB)
    except OSError:
        fh.close()
        raise BuildError(f"сборка уже идёт ({path.name}); второй экземпляр не запускаю") from None
    return fh


class Builder:
    def __init__(self, farm: Farm, flavor: Flavor, platform: Platform, opts: Options):
        self.farm = farm
        self.flavor = flavor
        self.platform = platform
        self.build_platform = platform
        self.opts = opts
        self.sdk = self.build_platform.sdk
        self.release = opts.release or utc_release()
        self.build_id = 0
        self.dir: Path = Path()
        self.log_path: Path = Path()
        self.log_fh = None
        self.started_ts = 0.0
        self.conn = None

    # ---------- журнал ----------

    def log(self, text: str) -> None:
        line = f"[{datetime.now().strftime('%H:%M:%S')}] {text}"
        print(line, flush=True)
        if self.log_fh:
            self.log_fh.write(line + "\n")
            self.log_fh.flush()

    # ---------- команды ----------

    def run(self, cmd: list[str], cwd: Path, logfile: Path, env: dict | None = None, check: bool = True) -> int:
        shown = " ".join(cmd)
        if self.opts.dry_run:
            self.log(f"dry-run: {shown}")
            return 0
        logfile.parent.mkdir(parents=True, exist_ok=True)
        with open(logfile, "ab") as fh:
            fh.write(f"$ {shown}\n".encode())
            fh.flush()
            proc = subprocess.run(cmd, cwd=cwd, env=env, stdout=fh, stderr=subprocess.STDOUT)
        if check and proc.returncode:
            tail = _tail(logfile, 25)
            raise BuildError(f"команда упала (код {proc.returncode}): {shown}\n{tail}")
        return proc.returncode

    def env(self) -> dict[str, str]:
        env = os.environ.copy()
        env.update(self.flavor.env)
        env["HALO_RELEASE"] = self.release
        bin_dir = self.sdk / "staging_dir" / "host" / "bin"
        env["PATH"] = f"{bin_dir}:{env.get('PATH', '')}"
        env["MKHASH"] = str(bin_dir / "mkhash")
        return env

    # ---------- этапы ----------

    def preflight(self) -> None:
        if not self.sdk or not (self.sdk / "scripts" / "feeds").exists():
            raise BuildError(f"SDK не найден: {self.sdk}")
        if not self.build_platform.feeds or not self.build_platform.feeds.exists():
            raise BuildError(f"нет feeds.conf шаблона: {self.build_platform.feeds}")
        if not self.farm.repo.exists():
            raise BuildError(f"нет рабочей копии репозитория: {self.farm.repo}")
        if not self.opts.allow_dirty and not self.opts.dry_run:
            dirty = subprocess.run(
                ["git", "-C", str(self.farm.repo), "status", "--porcelain"],
                capture_output=True, text=True,
            ).stdout.strip()
            if dirty:
                raise BuildError("в репозитории есть незакоммиченные изменения; --allow-dirty, если так и надо")

    def write_feeds(self) -> None:
        template = self.build_platform.feeds.read_text()
        text = (
            template.replace("@REPO@", str(self.farm.repo))
            .replace("@IRZ_LOCAL@", str(self.farm.irz_local))
            .rstrip()
            + f"\nsrc-link halo {self.farm.repo}\n"
        )
        target = self.sdk / "feeds.conf"
        old = target.read_text() if target.exists() else None
        if old == text:
            self.log("feeds.conf не изменился")
            return
        self.log(f"feeds.conf: записываю {len(text.splitlines())} строк")
        if self.opts.dry_run:
            return
        shutil.copyfile(target, target.with_suffix(".conf.bak")) if target.exists() else None
        target.write_text(text)

    def refs(self) -> dict:
        repo = self.farm.repo
        head = _git(repo, "rev-parse", "HEAD")
        branch = _git(repo, "rev-parse", "--abbrev-ref", "HEAD")
        halo = (repo / "halo.mk").read_text() if (repo / "halo.mk").exists() else ""
        pinned = re.search(r"^HALO_PINNED:=([0-9a-f]{40})", halo, re.M)
        hbranch = re.search(r"^HALO_BRANCH\?=(\S+)", halo, re.M)
        return {
            "repo_head": head,
            "repo_branch": branch,
            "halo_pinned": pinned.group(1) if pinned else "",
            "halo_branch": hbranch.group(1) if hbranch else "",
        }

    def buildbot_info(self) -> dict:
        try:
            manifest = buildbot.fetch_manifest(
                self.farm.buildbot,
                self.farm.state_dir / "buildbot.json",
                refresh=self.opts.refresh_buildbot,
            )
            info = buildbot.find_latest(
                manifest, self.farm.channel, self.flavor.brand, self.platform.board
            )
            self.log(f"buildbot: {info.path} · {info.version or '?'}")
            return {"path": info.path, "number": info.number, "version": info.version}
        except buildbot.BuildbotError as e:
            self.log(f"buildbot: {e} (продолжаю без него)")
            return {}

    def feeds_update(self) -> None:
        if not self.opts.feeds:
            return
        self.log("feeds update/install")
        self.run(["./scripts/feeds", "update", "-a"], self.sdk, self.log_path, self.env())
        self.run(["./scripts/feeds", "install", "-a"], self.sdk, self.log_path, self.env())

    def compile(self) -> None:
        dirs = self.farm.packages(self.flavor)
        if self.opts.only:
            missing = [d for d in self.opts.only if not (self.farm.repo / d / "Makefile").exists()]
            if missing:
                raise BuildError(f"нет каталога в репозитории: {', '.join(missing)}")
            dirs = list(self.opts.only)
        self.log(f"пакетов к сборке: {len(dirs)} · release {self.release}")
        env = self.env()
        for i, d in enumerate(dirs, 1):
            self.log(f"[{i}/{len(dirs)}] {d}")
            log = self.dir / "logs" / f"{d}.log"
            base = f"package/feeds/{SDK_FEED}/{d}"
            self.run(["make", f"{base}/clean"], self.sdk, log, env, check=False)
            self.run(["make", f"{base}/compile", "V=s"], self.sdk, log, env)

    def collect(self) -> list[tuple[Path, ipk.IpkMeta]]:
        arch = self.build_platform.arch
        pkgdir = self.sdk / "bin" / "packages" / arch / SDK_FEED
        if not pkgdir.exists():
            raise BuildError(f"нет каталога сборки {pkgdir}")
        files = [p for p in pkgdir.glob("*.ipk") if p.stat().st_mtime >= self.started_ts - 5]
        for pattern in self.platform.extras:
            files += list((self.sdk / "bin" / "packages" / arch).glob(pattern))

        out, seen = [], set()
        for f in sorted(files):
            meta = ipk.read_meta(f)
            key = (meta.name, meta.version, meta.arch)
            if key in seen:
                continue
            seen.add(key)
            out.append((f, meta))
        if not out:
            raise BuildError("не собралось ни одного пакета")
        return out

    def gates(self, packages: list[tuple[Path, ipk.IpkMeta]]) -> list[dict]:
        allowed = {self.platform.arch, "all"}
        checks = []
        bad = [f"{m.name}: {m.arch}" for _, m in packages if m.arch not in allowed]
        checks.append({"name": "arch", "ok": not bad, "detail": ", ".join(bad) or "all / " + self.platform.arch})
        names = [m.name for _, m in packages]
        dupes = sorted({n for n in names if names.count(n) > 1})
        checks.append({"name": "дубликаты", "ok": not dupes, "detail": ", ".join(dupes) or "нет"})
        failed = [c for c in checks if not c["ok"]]
        if failed:
            raise BuildError("гейты не пройдены: " + "; ".join(f"{c['name']} ({c['detail']})" for c in failed))
        return checks

    # ---------- основной сценарий ----------

    def go(self) -> Result:
        self.farm.ensure_dirs()
        lock = acquire_lock(self.farm.locks_dir / f"{self.flavor.name}.lock")
        try:
            return self._go()
        finally:
            if self.log_fh:
                self.log_fh.close()
            fcntl.flock(lock, fcntl.LOCK_UN)
            lock.close()

    def _go(self) -> Result:
        self.preflight()
        self.started_ts = datetime.now().timestamp()
        if self.opts.dry_run:
            self.conn = None
            self.build_id = 0
            self.dir = self.farm.builds_dir / "dry-run"
        else:
            self.conn = state.connect(self.farm.state_dir)
            self.build_id = state.start_build(
                self.conn, self.flavor.name, self.platform.name, now(), self.release, Path(""),
                pid=os.getpid(),
            )
            self.dir = self.farm.builds_dir / str(self.build_id)
        (self.dir / "logs").mkdir(parents=True, exist_ok=True)
        self.log_path = self.dir / "build.log"
        self.log_fh = open(self.log_path, "a")
        if self.conn:
            self.conn.execute(
                "update builds set log=? where id=?", (str(self.log_path), self.build_id)
            )
            self.conn.commit()

        manifest: dict = {}
        try:
            self.log(
                f"build #{self.build_id} · {self.flavor.name}/{self.flavor.brand} · "
                f"{self.platform.name} ({self.platform.arch}) · sdk {self.build_platform.name}"
            )
            self.write_feeds()
            refs = self.refs()
            bb = self.buildbot_info()
            self.feeds_update()
            self.compile()
            if self.opts.dry_run:
                self.log("dry-run: команды показаны, сборка не выполнялась")
                return Result(self.build_id, {"id": self.build_id, "status": "dry-run", "packages": []})
            packages = self.collect()
            checks = self.gates(packages)

            manifest = {
                "id": self.build_id,
                "flavor": self.flavor.name,
                "feed": self.flavor.feed,
                "brand": self.flavor.brand,
                "platform": self.platform.name,
                "build_platform": self.build_platform.name,
                "channel": self.farm.channel,
                "release": self.release,
                "started": now(),
                "finished": now(),
                "status": "ok",
                "refs": refs,
                "buildbot": bb,
                "sdk": {
                    "path": str(self.sdk),
                    "target": self.build_platform.target,
                    "arch": self.build_platform.arch,
                    "release": self.build_platform.release,
                },
                "checks": checks,
                "packages": [],
            }

            ipk_dir = self.dir / "ipk"
            ipk_dir.mkdir(exist_ok=True)
            for f, meta in packages:
                target = ipk_dir / f.name
                if not self.opts.dry_run:
                    shutil.copy2(f, target)
                digest = _sha256(target) if target.exists() else ""
                b, c = self._source_of(meta.name)
                manifest["packages"].append(
                    {
                        "name": meta.name,
                        "version": meta.version,
                        "arch": meta.arch,
                        "file": f.name,
                        "sha256": digest,
                        "size": target.stat().st_size if target.exists() else 0,
                        "depends": meta.depends,
                        "source_branch": b,
                        "source_commit": c,
                    }
                )
                if self.conn:
                    state.add_package(self.conn, self.build_id, meta, f.name, digest, b, c)
            if self.conn:
                self.conn.commit()

            if not self.opts.dry_run:
                (self.dir / "manifest.json").write_text(
                    json_dumps(manifest), encoding="utf-8"
                )
            if self.conn:
                state.finish_build(self.conn, self.build_id, "ok", now(), manifest)
            self.log(f"собрано {len(manifest['packages'])} пакетов; манифест {self.dir}/manifest.json")

            published = None
            if self.opts.publish:
                from .publish import publish_build

                published = publish_build(self.farm, manifest, dry_run=self.opts.dry_run)
                self.log(f"опубликовано в {self.farm.publish_root / self.flavor.feed}")
            return Result(self.build_id, manifest, published)
        except Exception:
            if self.conn:
                state.finish_build(self.conn, self.build_id, "failed", now(), manifest or None)
            raise

    def _source_of(self, name: str) -> tuple[str, str]:
        if name.startswith("halo"):
            halo = (self.farm.repo / "halo.mk").read_text()
            pinned = re.search(r"^HALO_PINNED:=([0-9a-f]{40})", halo, re.M)
            branch = re.search(r"^HALO_BRANCH\?=(\S+)", halo, re.M)
            return (branch.group(1) if branch else ""), (pinned.group(1) if pinned else "")
        return "", ""


def _git(repo: Path, *args: str) -> str:
    return subprocess.run(
        ["git", "-C", str(repo), *args], capture_output=True, text=True, check=True
    ).stdout.strip()


def _sha256(path: Path) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as fh:
        for chunk in iter(lambda: fh.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def _tail(path: Path, lines: int) -> str:
    try:
        data = path.read_text(errors="replace").splitlines()
    except OSError:
        return ""
    return "\n".join(data[-lines:])


def json_dumps(obj) -> str:
    return json.dumps(obj, ensure_ascii=False, indent=2)
