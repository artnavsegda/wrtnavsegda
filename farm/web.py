"""Веб-интерфейс фермы: состояние, пакеты, апстрим, конфиги, сборка и публикация.

Без зависимостей: ThreadingHTTPServer + статика + JSON API.
Слушает 127.0.0.1 по умолчанию — наружу выставляется через nginx.
"""

from __future__ import annotations

import json
import re
import subprocess
import sys
from datetime import datetime
import time
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import parse_qs, urlparse

from . import buildbot, config, opkgcfg, state

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
        commits = []
        if base and base != head:
            out = _git(repo, "log", f"{base}..{head}", "--date=short", "--format=%h\t%ad\t%s")
            for line in out.splitlines():
                parts = line.split("\t", 2)
                if len(parts) == 3:
                    commits.append({"hash": parts[0], "date": parts[1], "subject": parts[2]})
        return {"head": head, "base": base, "commits": commits}

    def _configs(self, farm, flavor_name: str) -> dict:
        flavor = farm.flavors[flavor_name]
        platform = farm.platforms[flavor.sdk_platform]
        try:
            manifest = buildbot.fetch_manifest(
                farm.buildbot, farm.state_dir / "buildbot.json", max_age=900
            )
            info = buildbot.find_latest(manifest, farm.channel, flavor.brand, platform.board)
        except buildbot.BuildbotError:
            return {"error": "buildbot недоступен"}
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

        rows = []
        for p in sorted(feed, key=lambda x: x["name"]):
            b = build_pkgs.pop(p["name"], None)
            status = "ок"
            if b and b["version"] != p["version"]:
                status = "обновится"
            rows.append({**p, "status": status, "build_version": b["version"] if b else ""})
        for name, b in sorted(build_pkgs.items()):
            rows.append(
                {
                    "name": name,
                    "version": b["version"],
                    "arch": b["arch"],
                    "depends": b.get("depends", ""),
                    "size": b.get("size", 0),
                    "status": "новый",
                    "build_version": b["version"],
                }
            )
        return {"feed": flavor.feed, "packages": rows, "build": build}

    def payload_log(self, build_id: int) -> dict:
        farm = config.load()
        path = farm.builds_dir / str(build_id) / "build.log"
        if not path.exists():
            return {"lines": [], "exists": False}
        text = path.read_text(errors="replace").splitlines()
        return {"lines": text[-MAX_LOG:], "exists": True, "size": path.stat().st_size}

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
        for item in body.get("only", []):
            args += ["--only", str(item)]
        if body.get("publish"):
            args += ["--publish"]
        log = farm.state_dir / "web-build.log"
        log.parent.mkdir(parents=True, exist_ok=True)
        with open(log, "ab") as fh:
            fh.write(f"\n$ {' '.join(args)}\n".encode())
            fh.flush()
            subprocess.Popen(args, cwd=str(farm.repo), stdout=fh, stderr=subprocess.STDOUT, start_new_session=True)
        return {"started": True, "flavor": flavor, "log": str(log)}

    def action_publish(self, body: dict) -> dict:
        build_id = int(body["build"])
        proc = subprocess.run(
            [sys.executable, str(PROJECT / "main.py"), "publish", "--build", str(build_id)],
            capture_output=True, text=True, timeout=600,
        )
        return {"ok": proc.returncode == 0, "output": (proc.stdout + proc.stderr).strip()}

    def action_config(self, query: dict) -> dict:
        flavor_name = query.get("flavor", ["irz"])[0]
        variant = query.get("variant", ["dist"])[0]
        configs = self._configs(config.load(), flavor_name)
        if "error" in configs:
            return configs
        return {"text": configs.get(variant, ""), "buildbot": configs["buildbot"]}


def data_flavor(body: dict) -> str:
    return str(body.get("flavor") or "irz")


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
    out["idle"] = max(0, int(time.time() - path.stat().st_mtime))
    try:
        lines = path.read_text(errors="replace").splitlines()[-200:]
    except OSError:
        return out
    for line in reversed(lines):
        m = re.search(r"\[(\d+)/(\d+)\] (\S+)", line)
        if m:
            out.update(current=int(m.group(1)), total=int(m.group(2)), package=m.group(3))
            break
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
