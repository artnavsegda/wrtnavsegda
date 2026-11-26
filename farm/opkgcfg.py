"""Генерация конфигов opkg для роутера по платформе и сборке buildbot.

Два варианта:
  distfeeds.conf   — полный, вместо сломанного прошивочного;
  customfeeds.conf — только наш фид, остальное из прошивки.

Пути buildbot меняются каждую ночь (номер сборки), поэтому конфиг всегда
привязан к конкретному номеру и его надо перегенерировать после обновления.
"""

from __future__ import annotations

from .buildbot import BuildInfo
from .config import Farm, Flavor, Platform

OPENWRT_MIRROR = "https://downloads.openwrt.org/releases"
PROVISION_FEEDS = ("kernel", "base", "pkg", "oss", "wrt")


def _header(farm: Farm, flavor: Flavor, platform: Platform, build: BuildInfo, sdk: str) -> list[str]:
    return [
        f"# {flavor.brand} {build.version or '?'} · {platform.target} · {platform.arch} · OpenWrt {platform.release}",
        f"# SDK: {sdk}",
        f"# buildbot: {farm.buildbot.rstrip('/')}/{build.path}",
    ]


def _render(items: list[tuple[str, str]], width: int) -> list[str]:
    return [f"src/gz {name:<{width}} {url}" for name, url in items]


def _width(items: list[tuple[str, str]]) -> int:
    return max([len(n) for n, _ in items] + [12]) + 1


def distfeeds(farm: Farm, flavor: Flavor, platform: Platform, build: BuildInfo, sdk: str) -> str:
    """Полный конфиг: фиды прошивки с buildbot + наш фид + стандартный OpenWrt."""
    lines = _header(farm, flavor, platform, build, sdk)
    urls = build.feed_urls(farm.buildbot)

    active = [(n, urls[n]) for n in PROVISION_FEEDS if n in urls]
    active.append((flavor.feed, f"{farm.farm_base.rstrip('/')}/{flavor.feed}"))
    lines += _render(active, _width(active))

    mirror = f"{OPENWRT_MIRROR}/{platform.release}"
    optional = [("openwrt_core", f"{mirror}/targets/{platform.target}/packages")]
    optional += [
        (f"openwrt_{feed}", f"{mirror}/packages/{platform.arch}/{feed}")
        for feed in ("base", "luci", "packages", "routing", "telephony")
    ]
    for f in farm.flavors.values():
        if f.feed != flavor.feed:
            optional.append((f.feed, f"{farm.farm_base.rstrip('/')}/{f.feed}"))

    lines.append("")
    lines.append(f"# стандартный OpenWrt {platform.release} — если нужны пакеты не из прошивки")
    width = _width(optional)
    for name, url in optional:
        comment = "  # другой бренд, не ставить вместе" if not name.startswith("openwrt_") else ""
        lines.append("# " + f"src/gz {name:<{width}} {url}{comment}")
    return "\n".join(lines) + "\n"


def customfeeds(farm: Farm, flavor: Flavor, platform: Platform, build: BuildInfo, sdk: str) -> str:
    """Только наш фид: остальное не трогаем."""
    lines = _header(farm, flavor, platform, build, sdk)
    items = [(flavor.feed, f"{farm.farm_base.rstrip('/')}/{flavor.feed}")]
    lines += _render(items, _width(items))
    return "\n".join(lines) + "\n"
