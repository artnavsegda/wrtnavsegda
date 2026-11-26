"""farm — сборка и публикация ipk-фида."""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
from datetime import datetime
from pathlib import Path

from . import build, buildbot, config, opkgcfg, state


def _dt(value: str | None) -> str:
    if not value:
        return "—"
    try:
        return datetime.fromisoformat(value).strftime("%d.%m %H:%M")
    except ValueError:
        return value


def cmd_status(args) -> int:
    farm = config.load()
    farm.ensure_dirs()
    conn = state.connect(farm.state_dir)

    print("Платформы")
    for p in farm.platforms.values():
        ok = "sdk ok" if (p.sdk and p.sdk.exists()) else ("planned" if p.status != "active" else "НЕТ SDK")
        print(f"  {p.name:<5} {p.board:<6} {p.arch:<26} {ok}")

    print("\nФлейворы")
    for f in farm.flavors.values():
        b = state.last_build(conn, f.name)
        pub = state.last_publish(conn, f.feed)
        line = f"  {f.name:<6} {f.feed:<6}"
        if b:
            line += f" build #{b['id']} {_dt(b['started'])} {b['status']:<8}"
        else:
            line += " сборок нет".ljust(28)
        if pub:
            line += f" · опубликован {_dt(pub['ts'])}, {pub['packages']} пакетов"
        print(line)

    pull = state.last_pull(conn)
    if pull:
        print(
            f"\nАпстрим: проверен {_dt(pull['ts'])} · {pull['head'][:9]} · "
            f"позади {pull['behind']}, впереди {pull['ahead']}"
        )
    if args.json:
        print(json.dumps({"platforms": [p.name for p in farm.platforms.values()]}, ensure_ascii=False))
    return 0


def cmd_pull(args) -> int:
    farm = config.load()
    farm.ensure_dirs()
    repo = farm.repo
    log = []

    def git(*a, check=True):
        return subprocess.run(["git", "-C", str(repo), *a], capture_output=True, text=True, check=check)

    before = git("rev-parse", "HEAD").stdout.strip()
    git("fetch", "--prune", check=False)
    behind = int(git("rev-list", "--count", "HEAD..@{u}").stdout.strip() or 0)
    ahead = int(git("rev-list", "--count", "@{u}..HEAD").stdout.strip() or 0)
    dirty = git("status", "--porcelain").stdout.strip()

    merged = False
    if behind and not ahead and not dirty:
        r = git("merge", "--ff-only", "@{u}", check=False)
        merged = r.returncode == 0
        log.append(r.stdout.strip() or r.stderr.strip())
    head = git("rev-parse", "HEAD").stdout.strip()
    print(f"wrtnavsegda: {before[:9]} → {head[:9]} · позади {behind}, впереди {ahead}"
          + (" · fast-forward" if merged else ""))
    if dirty:
        print("рабочая копия грязная — не мержу")

    conn = state.connect(farm.state_dir)
    state.record_pull(
        conn, datetime.now().astimezone().isoformat(timespec="seconds"),
        head, behind, ahead, not dirty, " ".join(log),
    )
    return 0


def cmd_config(args) -> int:
    farm = config.load()
    flavor = farm.flavor(args.flavor)
    platform = farm.platform(args.platform or flavor.sdk_platform)
    if not platform.active or not platform.sdk:
        print(f"платформа {platform.name} не active — конфиг не генерирую", file=sys.stderr)
        return 2
    info = _buildbot(farm, flavor, platform, refresh=args.refresh)
    text = (
        opkgcfg.distfeeds(farm, flavor, platform, info, str(platform.sdk))
        if args.variant == "dist"
        else opkgcfg.customfeeds(farm, flavor, platform, info, str(platform.sdk))
    )
    if args.out and args.out != "-":
        Path(args.out).write_text(text)
        print(f"записан {args.out}")
    else:
        sys.stdout.write(text)
    return 0


def cmd_build(args) -> int:
    farm = config.load()
    flavor = farm.flavor(args.flavor)
    platform = farm.platform(args.platform or flavor.sdk_platform)
    opts = build.Options(
        only=tuple(args.only),
        release=args.release,
        dry_run=args.dry_run,
        publish=args.publish,
        feeds=not args.no_feeds,
        allow_dirty=args.allow_dirty,
        refresh_buildbot=args.refresh,
    )
    result = build.Builder(farm, flavor, platform, opts).go()
    if result.manifest.get("status") == "dry-run":
        return 0
    print(f"\nсборка #{result.build_id}: {len(result.manifest.get('packages', []))} пакетов")
    for p in result.manifest.get("packages", []):
        print(f"  {p['name']:<28} {p['version']:<20} {p['arch']}")
    return 0


def cmd_publish(args) -> int:
    from .publish import publish_build

    farm = config.load()
    manifest_path = farm.builds_dir / str(args.build) / "manifest.json"
    if not manifest_path.exists():
        print(f"нет манифеста {manifest_path}", file=sys.stderr)
        return 2
    manifest = json.loads(manifest_path.read_text())
    out = publish_build(farm, manifest, dry_run=args.dry_run)
    print(json.dumps(out, ensure_ascii=False, indent=2))
    return 0


def cmd_logs(args) -> int:
    farm = config.load()
    base = farm.builds_dir / str(args.build)
    path = base / "build.log"
    if not path.exists():
        print(f"нет лога {path}", file=sys.stderr)
        return 2
    lines = path.read_text(errors="replace").splitlines()
    print("\n".join(lines[-args.lines:]))
    failed = [p for p in (base / "logs").glob("*.log")] if (base / "logs").exists() else []
    if failed:
        print("\nлоги пакетов:")
        for p in sorted(failed, key=lambda x: x.stat().st_mtime, reverse=True)[:5]:
            print(f"  {p}")
    return 0


def _buildbot(farm, flavor, platform, refresh=False) -> buildbot.BuildInfo:
    manifest = buildbot.fetch_manifest(
        farm.buildbot, farm.state_dir / "buildbot.json", refresh=refresh
    )
    return buildbot.find_latest(manifest, farm.channel, flavor.brand, platform.board)


def parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(prog="farm", description="ipk farm: сборка и публикация фида")
    sub = p.add_subparsers(dest="cmd", required=True)

    s = sub.add_parser("status", help="состояние платформ, сборок и публикаций")
    s.add_argument("--json", action="store_true")
    s.set_defaults(func=cmd_status)

    s = sub.add_parser("pull", help="git pull упаковки (wrtnavsegda)")
    s.set_defaults(func=cmd_pull)

    s = sub.add_parser("config", help="конфиг opkg для роутера")
    s.add_argument("--flavor", required=True)
    s.add_argument("--platform")
    s.add_argument("--variant", choices=["dist", "custom"], default="dist")
    s.add_argument("--out", default="-")
    s.add_argument("--refresh", action="store_true")
    s.set_defaults(func=cmd_config)

    s = sub.add_parser("build", help="собрать фид")
    s.add_argument("--flavor", required=True)
    s.add_argument("--platform")
    s.add_argument("--only", nargs="*", default=[], metavar="ПАКЕТ")
    s.add_argument("--release")
    s.add_argument("--dry-run", action="store_true")
    s.add_argument("--publish", action="store_true")
    s.add_argument("--no-feeds", action="store_true")
    s.add_argument("--allow-dirty", action="store_true")
    s.add_argument("--refresh", action="store_true")
    s.set_defaults(func=cmd_build)

    s = sub.add_parser("publish", help="опубликовать готовую сборку")
    s.add_argument("--build", type=int, required=True)
    s.add_argument("--dry-run", action="store_true")
    s.set_defaults(func=cmd_publish)

    s = sub.add_parser("logs", help="хвост лога сборки")
    s.add_argument("--build", type=int, required=True)
    s.add_argument("-n", "--lines", type=int, default=40)
    s.set_defaults(func=cmd_logs)
    return p


def main(argv: list[str] | None = None) -> int:
    args = parser().parse_args(argv)
    try:
        return args.func(args)
    except (config.ConfigError, build.BuildError, buildbot.BuildbotError) as e:
        print(f"farm: {e}", file=sys.stderr)
        return 1
