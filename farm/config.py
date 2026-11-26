"""Конфиг фермы: farm.toml → flavor/platform с раскрытыми путями."""

from __future__ import annotations

import os
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


def load(path: Path | None = None) -> Farm:
    project = PROJECT
    toml_path = path or (project / "farm.toml")
    if not toml_path.exists():
        raise ConfigError(f"нет конфига {toml_path}")
    raw = tomllib.loads(toml_path.read_text())

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
