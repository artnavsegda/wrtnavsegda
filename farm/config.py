"""Конфиг фермы: farm.toml → flavor/platform с раскрытыми путями."""

from __future__ import annotations

import json
import os
import re
import tomllib
from dataclasses import dataclass
from pathlib import Path

PROJECT = Path(__file__).resolve().parent


class ConfigError(Exception):
    pass


def _path(value: str | None, base: Path) -> Path | None:
    if not value:
        return None
    p = Path(os.path.expandvars(value)).expanduser()
    return p if p.is_absolute() else (base / p).resolve()


@dataclass(frozen=True)
class Platform:
    name: str
    board: str
    target: str
    arch: str
    release: str
    sdk: Path | None
    feeds: Path | None
    extras: tuple[str, ...]
    status: str
    brands: tuple[str, ...] = ()
    image_tree: Path | None = None

    @property
    def active(self) -> bool:
        return self.status == "active"


@dataclass(frozen=True)
class Flavor:
    name: str
    brand: str
    feed: str
    packages: Path
    sdk_platform: str
    donyx: bool

    @property
    def env(self) -> dict[str, str]:
        return {"DONYX": "1"} if self.donyx else {}


@dataclass(frozen=True)
class Farm:
    project: Path
    repo: Path
    irz_local: Path
    buildbot: str
    channel: str
    publish_root: Path
    farm_base: str
    state_dir: Path
    sign_key: Path
    jobs: int
    flavors: dict[str, Flavor]
    platforms: dict[str, Platform]

    def flavor(self, name: str) -> Flavor:
        try:
            return self.flavors[name]
        except KeyError:
            raise ConfigError(f"нет flavor «{name}»; есть: {', '.join(sorted(self.flavors))}") from None

    def platform(self, name: str) -> Platform:
        try:
            return self.platforms[name]
        except KeyError:
            raise ConfigError(f"нет платформы «{name}»; есть: {', '.join(sorted(self.platforms))}") from None

    def packages(self, flavor: Flavor) -> list[str]:
        if not flavor.packages.exists():
            raise ConfigError(f"нет файла пакетов {flavor.packages}")
        out: list[str] = []
        for line in flavor.packages.read_text().splitlines():
            line = line.split("#", 1)[0].strip()
            if line:
                out.append(line)
        return out

    @property
    def builds_dir(self) -> Path:
        return self.state_dir / "builds"

    @property
    def locks_dir(self) -> Path:
        return self.state_dir / "locks"

    def ensure_dirs(self) -> None:
        for d in (self.state_dir, self.builds_dir, self.locks_dir):
            d.mkdir(parents=True, exist_ok=True)


def _deep_merge(base: dict, extra: dict) -> dict:
    out = dict(base)
    for k, v in extra.items():
        if isinstance(v, dict) and isinstance(out.get(k), dict):
            out[k] = _deep_merge(out[k], v)
        else:
            out[k] = v
    return out


def load(path: Path | None = None) -> Farm:
    project = PROJECT
    toml_path = path or (project / "farm.toml")
    if not toml_path.exists():
        raise ConfigError(f"нет конфига {toml_path}")
    raw = tomllib.loads(toml_path.read_text())
    local = project / "platforms.local.toml"
    if local.exists():
        raw = _deep_merge(raw, tomllib.loads(local.read_text()))

    f = raw.get("farm", {})
    env = os.environ
    repo = _path(env.get("FARM_REPO") or f.get("repo", ".."), project)
    state_dir = _path(env.get("FARM_STATE_DIR") or f.get("state_dir"), project)
    publish_root = _path(env.get("FARM_PUBLISH_ROOT") or f.get("publish_root"), project)
    irz_local = _path(env.get("FARM_IRZ_LOCAL") or f.get("irz_local"), project)
    sign_key = _path(env.get("FARM_SIGN_KEY") or f.get("sign_key", "~/.config/opkg-feed/key-build"), project)

    flavors: dict[str, Flavor] = {}
    for name, v in raw.get("flavors", {}).items():
        flavors[name] = Flavor(
            name=name,
            brand=v["brand"],
            feed=v["feed"],
            packages=_path(v["packages"], repo),
            sdk_platform=v["sdk_platform"],
            donyx=bool(v.get("donyx", False)),
        )

    platforms: dict[str, Platform] = {}
    for name, v in raw.get("platforms", {}).items():
        platforms[name] = Platform(
            name=name,
            board=v.get("board", ""),
            target=v.get("target", ""),
            arch=v.get("arch", ""),
            release=v.get("release", ""),
            sdk=_path(v.get("sdk"), project),
            feeds=_path(v.get("feeds"), project),
            extras=tuple(v.get("extras", ())),
            status=v.get("status", "active"),
            brands=tuple(v.get("brands", ())),
            image_tree=_path(v.get("image_tree"), project),
        )

    farm = Farm(
        project=project,
        repo=repo,
        irz_local=irz_local,
        buildbot=env.get("FARM_BUILDBOT") or f.get("buildbot", ""),
        channel=env.get("FARM_CHANNEL") or f.get("channel", "DEVELOP"),
        publish_root=publish_root,
        farm_base=env.get("FARM_FARM_BASE") or f.get("farm_base", ""),
        state_dir=state_dir,
        sign_key=sign_key,
        jobs=int(env.get("FARM_JOBS") or f.get("jobs", os.cpu_count() or 8)),
        flavors=flavors,
        platforms=platforms,
    )
    _validate(farm)
    return farm


def _validate(farm: Farm) -> None:
    if not farm.flavors:
        raise ConfigError("в farm.toml нет ни одного flavor")
    feeds = [fl.feed for fl in farm.flavors.values()]
    if len(feeds) != len(set(feeds)):
        raise ConfigError(f"flavor'ы публикуются в один фид: {feeds}")
    for fl in farm.flavors.values():
        if fl.sdk_platform not in farm.platforms:
            raise ConfigError(f"flavor {fl.name}: sdk_platform «{fl.sdk_platform}» не описан")
        plt = farm.platforms[fl.sdk_platform]
        if plt.status != "active":
            raise ConfigError(f"flavor {fl.name}: sdk_platform «{plt.name}» не active")
    for plt in farm.platforms.values():
        if plt.status == "active" and (not plt.sdk or not plt.feeds):
            raise ConfigError(f"платформа {plt.name}: active, но не заданы sdk/feeds")


def _toml_value(v) -> str:
    if isinstance(v, bool):
        return "true" if v else "false"
    if isinstance(v, (int, float)):
        return str(v)
    if isinstance(v, (list, tuple)):
        return "[" + ", ".join(_toml_value(x) for x in v) + "]"
    return json.dumps(str(v), ensure_ascii=False)


def save_platform(project: Path, name: str, values: dict) -> Path:
    """Правки платформы — в platforms.local.toml (поверх farm.toml)."""
    path = project / "platforms.local.toml"
    data = tomllib.loads(path.read_text()) if path.exists() else {}
    platforms = data.setdefault("platforms", {})
    cur = dict(platforms.get(name, {}))
    for k, v in values.items():
        if v in ("", [], None):
            cur.pop(k, None)
        else:
            cur[k] = v
    platforms[name] = cur
    lines = ["# Правки платформ из интерфейса. Поверх farm.toml; можно удалять вручную.", ""]
    for pname, pdata in platforms.items():
        lines.append(f"[platforms.{pname}]")
        for k, v in pdata.items():
            lines.append(f"{k} = {_toml_value(v)}")
        lines.append("")
    path.write_text("\n".join(lines))
    return path


def remove_platform(project: Path, name: str) -> None:
    """Удалить платформу из farm.toml и её правки из platforms.local.toml."""
    farm_file = project / "farm.toml"
    if not farm_file.exists():
        raise ConfigError(f"нет конфига {farm_file}")
    text = farm_file.read_text()
    raw = tomllib.loads(text)
    platforms = raw.get("platforms", {})
    if name not in platforms:
        raise ConfigError(f"нет платформы «{name}»")
    for fl, spec in raw.get("flavors", {}).items():
        if spec.get("sdk_platform") == name:
            raise ConfigError(f"платформа {name} — основная для flavor {fl}; сначала переключите flavor")
    if len(platforms) <= 1:
        raise ConfigError("нельзя удалить последнюю платформу")

    pattern = re.compile(rf"(?ms)^\[platforms\.{re.escape(name)}\]\n.*?(?=^\[|\Z)")
    new_text, n = pattern.subn("", text)
    if not n:
        raise ConfigError(f"не нашёл секцию [platforms.{name}]")
    farm_file.write_text(new_text.rstrip() + "\n")

    local = project / "platforms.local.toml"
    if local.exists():
        data = tomllib.loads(local.read_text())
        if name in data.get("platforms", {}):
            data["platforms"].pop(name)
            lines = ["# Правки платформ из интерфейса. Поверх farm.toml; можно удалять вручную.", ""]
            for pname, pdata in data.get("platforms", {}).items():
                lines.append(f"[platforms.{pname}]")
                for k, v in pdata.items():
                    lines.append(f"{k} = {_toml_value(v)}")
                lines.append("")
            local.write_text("\n".join(lines))


NAME_RE = re.compile(r"^[a-z0-9][a-z0-9_-]*$")


def add_platform(project: Path, name: str, values: dict) -> None:
    """Добавить платформу в farm.toml (с проверкой SDK и шаблона feeds)."""
    if not NAME_RE.match(name or ""):
        raise ConfigError("имя платформы: строчные латинские буквы, цифры, - и _")
    farm_file = project / "farm.toml"
    text = farm_file.read_text() if farm_file.exists() else ""
    raw = tomllib.loads(text) if text.strip() else {}
    if name in raw.get("platforms", {}):
        raise ConfigError(f"платформа «{name}» уже есть")

    sdk = _path(values.get("sdk"), project)
    if not sdk or not sdk.exists():
        raise ConfigError(f"нет каталога SDK: {values.get('sdk')}")
    if not (sdk / "scripts" / "feeds").exists():
        raise ConfigError(f"это не OpenWrt SDK (нет scripts/feeds): {sdk}")
    feeds = _path(values.get("feeds"), project)
    if not feeds or not feeds.exists():
        raise ConfigError(f"нет шаблона feeds.conf: {values.get('feeds')}")
    for key in ("board", "target", "arch", "release"):
        if not str(values.get(key) or "").strip():
            raise ConfigError(f"не заполнено поле {key}")

    brands = values.get("brands") or ["irzOS", "dnxOS"]
    extras = values.get("extras") or []
    if isinstance(extras, str):
        extras = [x.strip() for x in extras.split(",") if x.strip()]

    block = [
        "",
        f"[platforms.{name}]",
        'status = "active"',
        f"brands = {_toml_value(list(brands))}",
        f"board = {_toml_value(values['board'])}",
        f"target = {_toml_value(values['target'])}",
        f"arch = {_toml_value(values['arch'])}",
        f"release = {_toml_value(values['release'])}",
        f"sdk = {_toml_value(values['sdk'])}",
        f"feeds = {_toml_value(_rel(project, values['feeds']))}",
        f"extras = {_toml_value(extras)}",
        "",
    ]
    farm_file.write_text(text.rstrip() + "\n" + "\n".join(block))


def _rel(project: Path, value: str) -> str:
    p = _path(value, project)
    try:
        return str(p.relative_to(project))
    except ValueError:
        return str(p)
