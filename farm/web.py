"""Веб-интерфейс фермы: состояние, пакеты, апстрим, конфиги, сборка и публикация.

Без зависимостей: ThreadingHTTPServer + статика + JSON API.
Слушает 127.0.0.1 по умолчанию — наружу выставляется через nginx.
"""

from __future__ import annotations

import json
import os
import re
import signal
import subprocess
import threading
import sys
from datetime import datetime
import time
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import parse_qs, urlparse

from . import buildbot, config, opkgcfg, repos, state
from .sources import makefile_packages, repo_dirs, source_map

STATIC = Path(__file__).resolve().parent / "static"
PROJECT = Path(__file__).resolve().parent
MAX_LOG = 400


def _json_default(o):
    return str(o)


def _git(repo: Path, *args: str) -> str:
    try:
        return subprocess.run(
            ["git", "-C", str(repo), *args], capture_output=True, text=True, timeout=15
        ).stdout.strip()
    except (OSError, subprocess.SubprocessError):
        return ""


def _feed_index(path: Path) -> list[dict]:
    """Пакеты опубликованного фида из Packages."""
    if not path.exists():
        return []
    out, cur = [], {}
    for line in path.read_text(errors="replace").splitlines():
        if not line.strip():
            if cur:
                out.append(cur)
                cur = {}
            continue
        key, _, value = line.partition(":")
        key = key.strip().lower()
        if key in ("package", "version", "architecture", "depends", "installed-size", "filename"):
            cur[key] = value.strip()
    if cur:
        out.append(cur)
    return [
        {
            "name": p.get("package", ""),
            "version": p.get("version", ""),
            "arch": p.get("architecture", ""),
            "depends": p.get("depends", ""),
            "size": int(p.get("installed-size", "0") or 0),
        }
        for p in out
    ]


class App:
    def __init__(self, host: str, port: int):
        self.host = host
        self.port = port

    # ---------- данные ----------

    def payload_state(self) -> dict:
        farm = config.load()
        farm.ensure_dirs()
        conn = state.connect(farm.state_dir)
        repo = farm.repo
        head = _git(repo, "rev-parse", "HEAD")
        branch = _git(repo, "rev-parse", "--abbrev-ref", "HEAD")
        dirty = bool(_git(repo, "status", "--porcelain"))

        builds = []
        for row in state.recent_builds(conn, 12):
            item = {
                "id": row["id"],
                "flavor": row["flavor"],
                "platform": row["platform"],
                "started": row["started"],
                "finished": row["finished"],
                "status": row["status"],
                "release": row["release"],
                "published": bool(row["published"]),
                "pid": row["pid"] if "pid" in row.keys() else None,
            }
            if item["status"] == "running":
                item["live"] = _live_progress(farm, item)
            builds.append(item)

        platforms = [
            {
                "name": p.name,
                "board": p.board,
                "target": p.target,
                "arch": p.arch,
                "release": p.release,
                "status": p.status,
                "sdk": str(p.sdk or ""),
                "sdk_ok": bool(p.sdk and p.sdk.exists()),
                "feeds": str(p.feeds or ""),
                "extras": list(p.extras),
                "brands": list(p.brands),
            }
            for p in farm.platforms.values()
        ]

        flavors = []
        for f in farm.flavors.values():
            fb = state.last_build(conn, f.name)
            pub = state.last_publish(conn, f.feed)
            flavors.append(
                {
                    "name": f.name,
                    "brand": f.brand,
                    "feed": f.feed,
                    "packages": str(f.packages),
                    "sdk_platform": f.sdk_platform,
                    "last_build": _build_row(fb) if fb else None,
                    "last_publish": dict(pub) if pub else None,
                    "feed_packages": _feed_index(farm.publish_root / f.feed / "Packages"),
                }
            )

        pull = state.last_pull(conn)
        return {
            "farm": {
                "repo": str(repo),
                "head": head,
                "branch": branch,
                "dirty": dirty,
                "channel": farm.channel,
                "buildbot": farm.buildbot,
                "farm_base": farm.farm_base,
                "publish_root": str(farm.publish_root),
            },
            "platforms": platforms,
            "flavors": flavors,
            "builds": builds,
            "pull": dict(pull) if pull else None,
            "upstream": self.payload_upstream(farm, conn, builds),
        }

    def payload_upstream(self, farm, conn, builds) -> dict:
        repo = farm.repo
        head = _git(repo, "rev-parse", "HEAD")
        base = ""
        for b in builds:
            if b.get("published"):
                row = conn.execute("select manifest from builds where id=?", (b["id"],)).fetchone()
                if row and row["manifest"]:
                    base = json.loads(row["manifest"]).get("refs", {}).get("repo_head", "")
                    break
        out = _git(repo, "log", "-200", "--date=short", "--format=%h\t%ad\t%s")
        commits = []
        for line in out.splitlines():
            parts = line.split("\t", 2)
            if len(parts) == 3:
                commits.append(
                    {
                        "hash": parts[0],
                        "date": parts[1],
                        "subject": parts[2],
                        "published": bool(base) and base.startswith(parts[0]),
                        "head": parts[0] == head[:7],
                    }
                )
        return {"head": head, "base": base, "commits": commits}

    def _configs(self, farm, flavor_name: str, platform_name: str = "") -> dict:
        flavor = farm.flavors[flavor_name]
        platform = farm.platforms[platform_name or flavor.sdk_platform]
        try:
            manifest = buildbot.fetch_manifest(
                farm.buildbot, farm.state_dir / "buildbot.json", max_age=900
            )
            info = buildbot.find_latest(manifest, farm.channel, flavor.brand, platform.board)
        except buildbot.BuildbotError as e:
            return {"error": f"buildbot: {e}"}
        sdk = str(platform.sdk or "")
        return {
            "buildbot": {"path": info.path, "version": info.version, "number": info.number},
            "dist": opkgcfg.distfeeds(farm, flavor, platform, info, sdk),
            "custom": opkgcfg.customfeeds(farm, flavor, platform, info, sdk),
        }

    def payload_packages(self, flavor_name: str) -> dict:
        farm = config.load()
        conn = state.connect(farm.state_dir)
        flavor = farm.flavor(flavor_name)
        feed = _feed_index(farm.publish_root / flavor.feed / "Packages")

        last = state.last_build(conn, flavor.name)
        build_pkgs: dict[str, dict] = {}
        build = None
        if last:
            build = _build_row(last)
            row = conn.execute("select manifest from builds where id=?", (last["id"],)).fetchone()
            if row and row["manifest"]:
                manifest = json.loads(row["manifest"])
                build = {**build, "refs": manifest.get("refs", {}), "buildbot": manifest.get("buildbot", {})}
                build_pkgs = {p["name"]: p for p in manifest.get("packages", [])}

        plan = _plan(farm, flavor)
        sources = source_map(farm, flavor)
        running = _last_dir_index(farm, [dict(x) for x in state.recent_builds(conn, 5)])
        done_all = last is not None and last["status"] == "ok"

        def state_of(name: str) -> str:
            if name not in plan or last is None:
                return ""
            if done_all:
                return "built"
            if running is None:
                return "pending"
            idx, _ = plan[name]
            cur = running[0] - 1
            if idx < cur:
                return "built"
            if idx == cur:
                return "building"
            return "pending"

        rows, seen = [], set()
        for p in sorted(feed, key=lambda x: (plan.get(x["name"], (999, ""))[0], x["name"])):
            b = build_pkgs.pop(p["name"], None)
            seen.add(p["name"])
            status = "ок" if not b or b["version"] == p["version"] else "обновится"
            rows.append({**p, "status": status, "build_version": b["version"] if b else "",
                         "build_state": state_of(p["name"]), "dir": plan.get(p["name"], (0, ""))[1],
                         "source": sources.get(p["name"], {})})
        for name, b in sorted(build_pkgs.items(), key=lambda kv: (plan.get(kv[0], (999, ""))[0], kv[0])):
            seen.add(name)
            rows.append({"name": name, "version": "", "arch": b["arch"], "depends": b.get("depends", ""),
                         "size": b.get("size", 0), "status": "новый", "build_version": b["version"],
                         "build_state": state_of(name), "dir": plan.get(name, (0, ""))[1],
                         "source": sources.get(name, {})})
        for name in sorted(plan, key=lambda n: (plan[n][0], n)):
            if name in seen:
                continue
            rows.append({"name": name, "version": "", "arch": "", "depends": "", "size": 0,
                         "status": "не в фиде", "build_version": "", "build_state": state_of(name),
                         "dir": plan[name][1], "source": sources.get(name, {})})
        for d in repo_dirs(farm):
            for name in makefile_packages(farm.repo / d / "Makefile") or [d]:
                if name in seen:
                    continue
                seen.add(name)
                rows.append({"name": name, "version": "", "arch": "", "depends": "", "size": 0,
                             "status": "не в сборке", "build_version": "", "build_state": "",
                             "dir": d, "source": sources.get(name, {})})
        rows.sort(key=lambda r: (plan.get(r["name"], (999, r.get("dir", "")))[0], r["name"]))
        current = None
        if running:
            last_lines = self.payload_pkg_log(last["id"] if last else 0, running[2], 1)["lines"]
            current = {"dir": running[2], "last": last_lines[-1].strip() if last_lines else ""}
        return {"feed": flavor.feed, "packages": rows, "build": build, "current": current,
                "last_status": last["status"] if last else None,
                "plan": {"total": len(farm.packages(flavor)), "running": running is not None,
                         "current": running[0] if running else 0, "dir": running[2] if running else ""}}

    def payload_pkg_log(self, build_id: int, pkg: str, lines: int = 80) -> dict:
        farm = config.load()
        path = farm.builds_dir / str(build_id) / "logs" / f"{pkg}.log"
        if not path.exists():
            return {"lines": [], "exists": False, "pkg": pkg}
        text = path.read_text(errors="replace").splitlines()[-lines:]
        return {"lines": text, "exists": True, "pkg": pkg}

    def payload_log(self, build_id: int) -> dict:
        farm = config.load()
        base = farm.builds_dir / str(build_id)
        path = base / "build.log"
        if not path.exists():
            return {"lines": [], "exists": False}
        lines = path.read_text(errors="replace").splitlines()[-MAX_LOG:]
        pkgdir = base / "logs"
        if pkgdir.exists():
            logs = sorted(pkgdir.glob("*.log"), key=lambda p: p.stat().st_mtime)
            if logs:
                cur = logs[-1]
                tail = cur.read_text(errors="replace").splitlines()[-120:]
                lines += ["", f"--- {cur.name} ---"] + tail
        return {"lines": lines, "exists": True, "size": path.stat().st_size}

    # ---------- действия ----------

    def action_pull(self) -> dict:
        proc = subprocess.run(
            [sys.executable, str(PROJECT / "main.py"), "pull"],
            capture_output=True, text=True, timeout=180,
        )
        return {"ok": proc.returncode == 0, "output": (proc.stdout + proc.stderr).strip()}

    def action_build(self, body: dict) -> dict:
        farm = config.load()
        flavor = data_flavor(body)
        args = [sys.executable, str(PROJECT / "main.py"), "build", "--flavor", flavor]
        if body.get("platform"):
            args += ["--platform", str(body["platform"])]
        want = body.get("only") or body.get("packages") or []
        if want:
            plan = _plan(farm, farm.flavor(flavor))
            all_dirs = repo_dirs(farm)
            dirs = []
            for item in want:
                item = str(item)
                d = plan.get(item, (0, ""))[1]
                if not d:
                    for dd in all_dirs:
                        if item in (makefile_packages(farm.repo / dd / "Makefile") or [dd]):
                            d = dd
                            break
                if d and d not in dirs:
                    dirs.append(d)
            if dirs:
                args += ["--only", *dirs]
        if body.get("publish"):
            args += ["--publish"]
        log = farm.state_dir / "web-build.log"
        log.parent.mkdir(parents=True, exist_ok=True)
        with open(log, "ab") as fh:
            fh.write(f"\n$ {' '.join(args)}\n".encode())
            fh.flush()
            subprocess.Popen(args, cwd=str(farm.repo), stdout=fh, stderr=subprocess.STDOUT, start_new_session=True)
        return {"started": True, "flavor": flavor, "log": str(log)}

    # ---------- платформа ----------

    OPS = {
        "feeds_update": ("обновить фиды", "./scripts/feeds update -a",
                         ["./scripts/feeds", "update", "-a"], False),
        "feeds_install": ("установить все пакеты фидов", "./scripts/feeds install -a",
                          ["./scripts/feeds", "install", "-a"], False),
        "feeds_list": ("список пакетов фидов", "./scripts/feeds list",
                       ["./scripts/feeds", "list"], True),
        "sdk_pull": ("обновить SDK", "git pull --ff-only",
                     ["git", "pull", "--ff-only"], False),
    }

    def payload_source(self, flavor_name: str, package: str) -> dict:
        farm = config.load()
        try:
            flavor = farm.flavor(flavor_name)
        except config.ConfigError as e:
            return {"error": str(e)}
        src = source_map(farm, flavor).get(package)
        if not src:
            return {"error": "пакет не из фида"}
        if not src.get("url"):
            return {"error": "собирается из самого репозитория"}
        try:
            return {**src, **repos.info(farm, src["url"], src.get("commit_full") or src.get("commit", ""))}
        except repos.RepoError as e:
            return {"error": str(e)}

    def payload_platform(self, name: str) -> dict:
        farm = config.load()
        p = farm.platform(name)
        sdk = p.sdk
        cfg = sdk / ".config" if sdk else None
        text = cfg.read_text(errors="replace") if cfg and cfg.exists() else ""
        local = farm.project / "platforms.local.toml"
        ops = []
        for op, (title, cmd, argv, sync) in self.OPS.items():
            ok = bool(sdk and sdk.exists())
            if op == "sdk_pull":
                ok = ok and (sdk / ".git").exists()
            ops.append({"id": op, "title": title, "cmd": cmd, "sync": sync, "ok": ok})
        ops.append({"id": "image", "title": "собрать образ прошивки",
                    "cmd": f"make -j{farm.jobs} в image_tree", "sync": False,
                    "ok": bool(p.image_tree and p.image_tree.exists())})
        return {
            "name": p.name,
            "board": p.board,
            "target": p.target,
            "arch": p.arch,
            "release": p.release,
            "status": p.status,
            "sdk": str(sdk or ""),
            "sdk_ok": bool(sdk and sdk.exists()),
            "sdk_git": bool(sdk and (sdk / ".git").exists()),
            "feeds": str(p.feeds or ""),
            "extras": list(p.extras),
            "image_tree": str(p.image_tree or ""),
            "image_ok": bool(p.image_tree and p.image_tree.exists()),
            "config": text,
            "config_path": str(cfg or ""),
            "overrides": local.exists(),
            "ops": ops,
        }

    def _sdk_run(self, sdk: Path, cmd: list[str], timeout: int = 120):
        env = os.environ.copy()
        env["PATH"] = f"{sdk / 'staging_dir' / 'host' / 'bin'}:{env.get('PATH', '')}"
        env["LC_ALL"] = "C"
        return subprocess.run(cmd, cwd=sdk, env=env, capture_output=True, text=True, timeout=timeout)

    def payload_platform_feeds(self, name: str) -> dict:
        farm = config.load()
        sdk = farm.platform(name).sdk
        if not sdk or not (sdk / "scripts" / "feeds").exists():
            return {"error": "нет SDK"}
        proc = self._sdk_run(sdk, ["./scripts/feeds", "list", "-s"])
        feeds = []
        for line in proc.stdout.splitlines():
            parts = line.split(None, 3)
            if len(parts) < 4:
                continue
            fname, proto, rev, url = parts
            installed = 0
            fdir = sdk / "package" / "feeds" / fname
            if fdir.exists():
                installed = sum(1 for _ in fdir.iterdir())
            count = 0
            try:
                out = self._sdk_run(sdk, ["./scripts/feeds", "list", "-r", fname], timeout=60)
                count = sum(1 for l in out.stdout.splitlines() if l.strip())
            except subprocess.SubprocessError:
                pass
            feeds.append({"name": fname, "proto": proto, "revision": rev[:9], "url": url,
                          "packages": count, "installed": installed})
        return {"feeds": feeds}

    def payload_platform_packages(self, name: str, q: str = "") -> dict:
        farm = config.load()
        sdk = farm.platform(name).sdk
        if not sdk:
            return {"error": "нет SDK"}
        base = sdk / "package" / "feeds"
        rows = []
        if q:
            try:
                proc = self._sdk_run(sdk, ["./scripts/feeds", "search", q], timeout=90)
            except subprocess.SubprocessError as e:
                return {"error": str(e)}
            feed = ""
            for line in proc.stdout.splitlines():
                m = re.match(r"Search results in feed '([^']+)'", line)
                if m:
                    feed = m.group(1)
                    continue
                if not line.strip() or line.startswith("Search results"):
                    continue
                parts = re.split(r"\t+|\s{2,}", line.strip(), maxsplit=1)
                pname = parts[0]
                desc = parts[1] if len(parts) > 1 else ""
                rows.append({"feed": feed, "name": pname, "description": desc,
                             "installed": bool(base / feed / pname and (base / feed / pname).exists())})
                if len(rows) >= 300:
                    break
        else:
            if base.exists():
                for feed_dir in sorted(base.iterdir()):
                    if not feed_dir.is_dir():
                        continue
                    for pkg in sorted(feed_dir.iterdir()):
                        if pkg.name.startswith("."):
                            continue
                        rows.append({"feed": feed_dir.name, "name": pkg.name,
                                     "description": "", "installed": True})
                        if len(rows) >= 300:
                            break
                    if len(rows) >= 300:
                        break
        return {"packages": rows, "query": q}

    def action_platform_pkg(self, name: str, body: dict) -> dict:
        farm = config.load()
        sdk = farm.platform(name).sdk
        if not sdk:
            return {"ok": False, "error": "нет SDK"}
        conn = state.connect(farm.state_dir)
        busy = conn.execute("select id, flavor from builds where status='running'").fetchone()
        if busy and farm.flavors.get(busy["flavor"]) and farm.flavors[busy["flavor"]].sdk_platform == name:
            return {"ok": False, "error": f"идёт сборка #{busy['id']} — SDK занят"}
        action = str(body.get("action", ""))
        pkg = str(body.get("package", ""))
        feed = str(body.get("feed", ""))
        if not pkg:
            return {"ok": False, "error": "не указан пакет"}
        try:
            if action == "install":
                cmd = ["./scripts/feeds", "install"] + (["-p", feed] if feed else []) + [pkg]
            elif action == "uninstall":
                cmd = ["./scripts/feeds", "uninstall", pkg]
            else:
                return {"ok": False, "error": f"неизвестное действие {action}"}
            proc = self._sdk_run(sdk, cmd, timeout=120)
        except subprocess.SubprocessError as e:
            return {"ok": False, "error": str(e)}
        return {"ok": proc.returncode == 0, "output": (proc.stdout + proc.stderr)[-8000:]}

    def action_platform_paths(self, name: str, body: dict) -> dict:
        extras = body.get("extras", "")
        if isinstance(extras, str):
            extras = [x.strip() for x in extras.split(",") if x.strip()]
        values = {
            "sdk": body.get("sdk", ""),
            "feeds": body.get("feeds", ""),
            "extras": extras,
            "image_tree": body.get("image_tree", ""),
        }
        path = config.save_platform(config.PROJECT, name, values)
        return {"ok": True, "saved": str(path)}

    def action_platform_config(self, name: str, body: dict) -> dict:
        farm = config.load()
        sdk = farm.platform(name).sdk
        if not sdk or not sdk.exists():
            return {"ok": False, "error": "нет SDK"}
        cfg = sdk / ".config"
        if cfg.exists():
            backup = sdk / f".config.bak.{datetime.now().strftime('%Y%m%d-%H%M%S')}"
            backup.write_bytes(cfg.read_bytes())
        cfg.write_text(str(body.get("text", "")))
        return {"ok": True, "path": str(cfg)}

    def action_platform_op(self, name: str, body: dict) -> dict:
        farm = config.load()
        p = farm.platform(name)
        op = str(body.get("op", ""))
        if op == "image":
            if not p.image_tree or not p.image_tree.exists():
                return {"ok": False, "error": "не задан image_tree"}
            cmd = ["make", f"-j{farm.jobs}"]
            cwd = p.image_tree
        else:
            spec = self.OPS.get(op)
            if not spec:
                return {"ok": False, "error": f"неизвестная операция {op}"}
            if not p.sdk or not p.sdk.exists():
                return {"ok": False, "error": "нет SDK"}
            if op == "sdk_pull" and not (p.sdk / ".git").exists():
                return {"ok": False, "error": "SDK не git-репозиторий"}
            cmd = spec[2]
            cwd = p.sdk

        if op != "feeds_list":
            conn = state.connect(farm.state_dir)
            busy = conn.execute("select id, flavor from builds where status='running'").fetchone()
            if busy and farm.flavors.get(busy["flavor"]) and farm.flavors[busy["flavor"]].sdk_platform == name:
                return {"ok": False, "error": f"идёт сборка #{busy['id']} ({busy['flavor']}) — SDK занят"}

        env = os.environ.copy()
        if p.sdk:
            env["PATH"] = f"{p.sdk / 'staging_dir' / 'host' / 'bin'}:{env.get('PATH', '')}"
        env["LC_ALL"] = "C"

        specs = self.OPS.get(op)
        if specs and specs[3]:
            proc = subprocess.run(cmd, cwd=cwd, env=env, capture_output=True, text=True, timeout=120)
            return {"ok": proc.returncode == 0, "output": (proc.stdout + proc.stderr)[-20000:]}

        log = farm.state_dir / "ops" / f"{name}-{op}.log"
        log.parent.mkdir(parents=True, exist_ok=True)
        log.write_text(f"$ {' '.join(cmd)}  (cwd {cwd})\n")
        with open(log, "a") as fh:
            proc = subprocess.Popen(cmd, cwd=cwd, env=env, stdout=fh, stderr=subprocess.STDOUT,
                                    start_new_session=True)

        def wait_and_mark():
            code = proc.wait()
            with open(log, "a") as fh:
                fh.write(f"\nEXIT:{code}\n")

        threading.Thread(target=wait_and_mark, daemon=True).start()
        return {"ok": True, "started": True, "log": str(log), "pid": proc.pid}

    def payload_oplog(self, name: str, op: str) -> dict:
        farm = config.load()
        path = farm.state_dir / "ops" / f"{name}-{op}.log"
        if not path.exists():
            return {"exists": False, "lines": []}
        return {"exists": True, "lines": path.read_text(errors="replace").splitlines()[-300:]}

    def action_stop(self, body: dict) -> dict:
        farm = config.load()
        conn = state.connect(farm.state_dir)
        flavor = data_flavor(body)
        row = conn.execute(
            "select * from builds where flavor=? and status='running' order by id desc limit 1",
            (flavor,),
        ).fetchone()
        if not row:
            return {"ok": False, "error": "нет идущей сборки"}
        pid = row["pid"] if "pid" in row.keys() else None
        if not pid:
            out = subprocess.run(["pgrep", "-f", f"farm/main.py build --flavor {flavor}"],
                                 capture_output=True, text=True)
            pid = int(out.stdout.split()[0]) if out.stdout.strip() else None
        if not pid:
            return {"ok": False, "error": "не найден процесс сборки"}
        try:
            pgid = os.getpgid(pid)
            os.killpg(pgid, signal.SIGTERM)
        except ProcessLookupError:
            pass
        except PermissionError:
            os.kill(pid, signal.SIGTERM)
        state.mark_stopped(conn, row["id"], datetime.now().astimezone().isoformat(timespec="seconds"))
        return {"ok": True, "build": row["id"], "pid": pid}

    def action_publish(self, body: dict) -> dict:
        build_id = int(body["build"])
        proc = subprocess.run(
            [sys.executable, str(PROJECT / "main.py"), "publish", "--build", str(build_id)],
            capture_output=True, text=True, timeout=600,
        )
        return {"ok": proc.returncode == 0, "output": (proc.stdout + proc.stderr).strip()}

    def action_config(self, query: dict) -> dict:
        flavor_name = query.get("flavor", ["irz"])[0]
        platform_name = query.get("platform", [""])[0]
        variant = query.get("variant", ["dist"])[0]
        configs = self._configs(config.load(), flavor_name, platform_name)
        if "error" in configs:
            return configs
        return {"text": configs.get(variant, ""), "buildbot": configs["buildbot"]}


def data_flavor(body: dict) -> str:
    return str(body.get("flavor") or "irz")


def _plan(farm, flavor) -> dict[str, tuple[int, str]]:
    """Пакет → (индекс каталога в порядке сборки, каталог)."""
    plan: dict[str, tuple[int, str]] = {}
    for i, d in enumerate(farm.packages(flavor)):
        names = makefile_packages(farm.repo / d / "Makefile") or [d]
        for n in names:
            plan[n] = (i, d)
    return plan


def _last_dir_index(farm, builds) -> tuple[int, int, str] | None:
    """Последний [i/n] dir из лога последней сборки (running или упавшей)."""
    for b in builds:
        if b["status"] == "ok":
            return None
        if b["status"] not in ("running", "failed"):
            continue
        path = farm.builds_dir / str(b["id"]) / "build.log"
        if not path.exists():
            continue
        try:
            lines = path.read_text(errors="replace").splitlines()[-300:]
        except OSError:
            continue
        for line in reversed(lines):
            m = re.search(r"\[(\d+)/(\d+)\] (\S+)", line)
            if m:
                return int(m.group(1)), int(m.group(2)), m.group(3)
    return None


def _live_progress(farm, build: dict) -> dict:
    path = farm.builds_dir / str(build["id"]) / "build.log"
    out: dict = {"elapsed": 0, "idle": 0, "current": 0, "total": 0, "package": ""}
    try:
        started = datetime.fromisoformat(build["started"]).timestamp()
        out["elapsed"] = max(0, int(time.time() - started))
    except ValueError:
        pass
    if not path.exists():
        return out
    try:
        lines = path.read_text(errors="replace").splitlines()[-200:]
    except OSError:
        return out
    for line in reversed(lines):
        m = re.search(r"\[(\d+)/(\d+)\] (\S+)", line)
        if m:
            out.update(current=int(m.group(1)), total=int(m.group(2)), package=m.group(3))
            break
    # вывод пакета идёт в logs/<каталог>.log, build.log молчит всё время сборки
    stamp = path
    if out["package"]:
        pkg_log = path.parent / "logs" / f"{out['package']}.log"
        if pkg_log.exists():
            stamp = pkg_log
    out["idle"] = max(0, int(time.time() - stamp.stat().st_mtime))
    return out


def _build_row(row) -> dict:
    try:
        d = dict(row)
    except (TypeError, ValueError):
        return {}
    return {k: d.get(k) for k in ("id", "flavor", "platform", "started", "finished", "status", "release", "published")}


class Handler(BaseHTTPRequestHandler):
    server_version = "ipk-farm/0.1"

    @property
    def app(self) -> App:
        return self.server.app  # type: ignore[attr-defined]

    def log_message(self, fmt, *args):
        sys.stderr.write("%s %s\n" % (self.address_string(), fmt % args))

    # ---------- ответы ----------

    def _send(self, code: int, body: bytes, ctype: str, extra: dict | None = None) -> None:
        self.send_response(code)
        self.send_header("Content-Type", ctype)
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Cache-Control", "no-store")
        for k, v in (extra or {}).items():
            self.send_header(k, v)
        self.end_headers()
        self.wfile.write(body)

    def json(self, data, code: int = 200) -> None:
        self._send(code, json.dumps(data, ensure_ascii=False, default=_json_default).encode(), "application/json; charset=utf-8")

    def error(self, message: str, code: int = 400) -> None:
        self.json({"error": message}, code)

    # ---------- маршруты ----------

    def do_GET(self) -> None:
        url = urlparse(self.path)
        path = url.path
        q = parse_qs(url.query)
        try:
            if path == "/" or path == "/index.html":
                return self.static("index.html")
            if path.startswith("/static/"):
                return self.static(path[len("/static/"):])
            if path == "/api/state":
                return self.json(self.app.payload_state())
            if path == "/api/packages":
                return self.json(self.app.payload_packages(q.get("flavor", ["irz"])[0]))
            if path == "/api/config":
                return self.json(self.app.action_config(q))
            if path.startswith("/platform/"):
                return self.static("platform.html")
            if path.startswith("/api/platform/"):
                parts = path[len("/api/platform/"):].split("/")
                name = parts[0]
                if len(parts) == 1:
                    return self.json(self.app.payload_platform(name))
                if parts[1] == "oplog":
                    return self.json(self.app.payload_oplog(name, q.get("op", [""])[0]))
                if parts[1] == "feeds":
                    return self.json(self.app.payload_platform_feeds(name))
                if parts[1] == "packages":
                    return self.json(self.app.payload_platform_packages(name, q.get("q", [""])[0]))
            if path == "/api/source":
                return self.json(self.app.payload_source(
                    q.get("flavor", ["irz"])[0], q.get("package", [""])[0]
                ))
            if path == "/api/log":
                return self.json(self.app.payload_pkg_log(
                    int(q.get("build", ["0"])[0]),
                    q.get("pkg", [""])[0],
                    int(q.get("lines", ["80"])[0]),
                ))
            if path.startswith("/api/builds/") and path.endswith("/log"):
                return self.json(self.app.payload_log(int(path.split("/")[3])))
            if path.startswith("/api/builds/"):
                return self.json(self.build_detail(int(path.rsplit("/", 1)[1])))
            if path == "/api/feed":
                return self.feed_file(q)
            return self.error("не найдено", 404)
        except Exception as e:  # noqa: BLE001
            return self.error(f"{type(e).__name__}: {e}", 500)

    def do_POST(self) -> None:
        url = urlparse(self.path)
        length = int(self.headers.get("Content-Length") or 0)
        body = json.loads(self.rfile.read(length) or b"{}") if length else {}
        try:
            if url.path == "/api/pull":
                return self.json(self.app.action_pull())
            if url.path == "/api/build":
                return self.json(self.app.action_build(body))
            if url.path == "/api/publish":
                return self.json(self.app.action_publish(body))
            if url.path == "/api/stop":
                return self.json(self.app.action_stop(body))
            if url.path.startswith("/api/platform/"):
                parts = url.path[len("/api/platform/"):].split("/")
                if len(parts) == 2:
                    name, action = parts
                    if action == "paths":
                        return self.json(self.app.action_platform_paths(name, body))
                    if action == "config":
                        return self.json(self.app.action_platform_config(name, body))
                    if action == "op":
                        return self.json(self.app.action_platform_op(name, body))
                    if action == "pkg":
                        return self.json(self.app.action_platform_pkg(name, body))
            return self.error("не найдено", 404)
        except Exception as e:  # noqa: BLE001
            return self.error(f"{type(e).__name__}: {e}", 500)

    def build_detail(self, build_id: int) -> dict:
        farm = config.load()
        path = farm.builds_dir / str(build_id) / "manifest.json"
        if not path.exists():
            return {"id": build_id, "exists": False}
        manifest = json.loads(path.read_text())
        manifest["exists"] = True
        return manifest

    def feed_file(self, q: dict) -> None:
        farm = config.load()
        flavor = q.get("flavor", ["irz"])[0]
        kind = q.get("kind", ["dist"])[0]
        configs = self.app._configs(farm, flavor)
        if "error" in configs:
            return self.error(configs["error"], 503)
        text = configs.get(kind, "")
        self._send(200, text.encode(), "text/plain; charset=utf-8", {
            "Content-Disposition": f'attachment; filename="{kind}feeds.conf"'
        })

    def static(self, name: str) -> None:
        path = (STATIC / name).resolve()
        if not str(path).startswith(str(STATIC)) or not path.exists():
            return self.error("не найдено", 404)
        ctype = {
            ".html": "text/html; charset=utf-8",
            ".css": "text/css; charset=utf-8",
            ".js": "application/javascript; charset=utf-8",
            ".svg": "image/svg+xml",
        }.get(path.suffix, "application/octet-stream")
        self._send(200, path.read_bytes(), ctype)


def serve(host: str = "127.0.0.1", port: int = 8099) -> None:
    httpd = ThreadingHTTPServer((host, port), Handler)
    httpd.app = App(host, port)  # type: ignore[attr-defined]
    print(f"ipk farm: http://{host}:{port}/")
    try:
        httpd.serve_forever()
    except KeyboardInterrupt:
        pass


if __name__ == "__main__":
    serve()
