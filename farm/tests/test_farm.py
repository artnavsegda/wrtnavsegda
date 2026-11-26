"""Тесты фермы: конфиг, buildbot, opkg-конфиг, ipk, версии."""

from __future__ import annotations

import gzip
import io
import tarfile
import tempfile
import unittest
from pathlib import Path

from farm import buildbot, config, ipk, opkgcfg
from farm.publish import _index_versions


def make_ipk(path: Path, name: str, version: str, arch: str = "all", depends: str = "") -> None:
    """OpenWrt ipk: gzip tar с debian-binary, control.tar.gz и data.tar.gz."""
    control = (
        f"Package: {name}\nVersion: {version}\nArchitecture: {arch}\n"
        f"Depends: {depends}\nDescription: test\n"
    ).encode()

    def gz_tar(files: dict[str, bytes]) -> bytes:
        buf = io.BytesIO()
        with tarfile.open(fileobj=buf, mode="w:gz") as tf:
            for fname, data in files.items():
                info = tarfile.TarInfo(fname)
                info.size = len(data)
                tf.addfile(info, io.BytesIO(data))
        return buf.getvalue()

    control_tar = gz_tar({"./control": control})
    data_tar = gz_tar({"./usr/share/test": b"x"})
    path.write_bytes(
        gz_tar(
            {
                "./debian-binary": b"2.0\n",
                "./control.tar.gz": control_tar,
                "./data.tar.gz": data_tar,
            }
        )
    )


class ConfigTest(unittest.TestCase):
    def test_load(self):
        farm = config.load()
        self.assertIn("irz", farm.flavors)
        self.assertIn("r50", farm.platforms)
        self.assertEqual(farm.platforms["r50"].arch, "arm_cortex-a7_neon-vfpv4")
        self.assertTrue(farm.packages(farm.flavors["irz"]))
        self.assertTrue(all(p for p in farm.packages(farm.flavors["donyx"])))

    def test_paths_expanded(self):
        farm = config.load()
        self.assertTrue(str(farm.platforms["r50"].sdk).startswith("/"))


class BuildbotTest(unittest.TestCase):
    MANIFEST = {
        "name": "artifacts",
        "children": [
            {
                "name": "DEVELOP",
                "type": "dir",
                "children": [
                    {
                        "name": "irzOS",
                        "type": "dir",
                        "children": [
                            {
                                "name": "ipq50",
                                "type": "dir",
                                "children": [
                                    {"name": "249", "type": "dir", "children": []},
                                    {
                                        "name": "250",
                                        "type": "dir",
                                        "children": [
                                            {"name": "ipq50-irzOS-0.1.1051-devel.bin", "type": "file"},
                                            {
                                                "name": "ipk",
                                                "type": "dir",
                                                "children": [
                                                    {"name": "base", "type": "dir"},
                                                    {"name": "pkg", "type": "dir"},
                                                ],
                                            },
                                        ],
                                    },
                                ],
                            }
                        ],
                    }
                ],
            }
        ],
    }

    def test_latest(self):
        info = buildbot.find_latest(self.MANIFEST, "DEVELOP", "irzOS", "ipq50")
        self.assertEqual(info.number, 250)
        self.assertEqual(info.version, "0.1.1051-devel")
        self.assertEqual(info.feeds, ("base", "pkg"))
        self.assertEqual(
            info.feed_urls("http://bb")["base"],
            "http://bb/DEVELOP/irzOS/ipq50/250/ipk/base",
        )

    def test_missing(self):
        with self.assertRaises(buildbot.BuildbotError):
            buildbot.find_latest(self.MANIFEST, "RELEASE", "irzOS", "ipq50")


class OpkgConfigTest(unittest.TestCase):
    def setUp(self):
        self.farm = config.load()
        self.flavor = self.farm.flavors["irz"]
        self.platform = self.farm.platforms["r50"]
        self.info = buildbot.BuildInfo(
            channel="DEVELOP", brand="irzOS", board="ipq50", number=250,
            version="0.1.1051-devel", feeds=("base", "kernel", "oss", "pkg", "wrt"),
        )

    def test_dist(self):
        text = opkgcfg.distfeeds(self.farm, self.flavor, self.platform, self.info, "/sdk")
        self.assertIn("src/gz base", text)
        self.assertIn("/DEVELOP/irzOS/ipq50/250/ipk/base", text)
        self.assertIn("/DEVELOP/irzOS/ipq50/250/ipk/pkg", text)
        self.assertIn(f"{self.farm.farm_base}/halo", text)
        self.assertIn("src/gz openwrt_telephony", text)
        self.assertNotIn("# src/gz openwrt_telephony", text)
        self.assertIn("# SDK: /sdk", text)
        self.assertIn("# src/gz donyx", text)

    def test_custom(self):
        text = opkgcfg.customfeeds(self.farm, self.flavor, self.platform, self.info, "/sdk")
        self.assertEqual(len([l for l in text.splitlines() if l.startswith("src/gz")]), 1)


class IpkTest(unittest.TestCase):
    def test_parse(self):
        with tempfile.TemporaryDirectory() as d:
            p = Path(d) / "halo_0.1-r1_all.ipk"
            make_ipk(p, "halo", "0.1-r1", "all", "lighttpd, ttyd")
            meta = ipk.read_meta(p)
            self.assertEqual(meta.name, "halo")
            self.assertEqual(meta.version, "0.1-r1")
            self.assertEqual(meta.arch, "all")
            self.assertEqual(meta.depends, "lighttpd, ttyd")


class ArIpkTest(unittest.TestCase):
    def test_parse_ar(self):
        with tempfile.TemporaryDirectory() as d:
            p = Path(d) / "old_0.1-r1_all.ipk"
            control = (
                "Package: old\nVersion: 0.1-r1\nArchitecture: all\n"
                "Depends: busybox\n"
            ).encode()
            tar = io.BytesIO()
            with tarfile.open(fileobj=tar, mode="w:gz") as tf:
                info = tarfile.TarInfo("./control")
                info.size = len(control)
                tf.addfile(info, io.BytesIO(control))
            body = tar.getvalue()

            def entry(aname: str, data: bytes) -> bytes:
                header = f"{aname:<16}{'0':<12}{'0':<6}{'0':<6}{'100644':<8}{len(data):<10}`\n".encode()
                return header + data + (b"\n" if len(data) % 2 else b"")

            p.write_bytes(b"!<arch>\n" + entry("debian-binary", b"2.0\n") + entry("control.tar.gz", body))
            meta = ipk.read_meta(p)
            self.assertEqual(meta.name, "old")
            self.assertEqual(meta.version, "0.1-r1")
            self.assertEqual(meta.depends, "busybox")


class CliTest(unittest.TestCase):
    def test_build_publishes_by_default(self):
        from farm.cli import parser

        args = parser().parse_args(["build", "--flavor", "irz"])
        self.assertFalse(args.no_publish)

    def test_no_publish_flag(self):
        from farm.cli import parser

        args = parser().parse_args(["build", "--flavor", "irz", "--no-publish"])
        self.assertTrue(args.no_publish)

    def test_publish_flag_removed(self):
        from farm.cli import parser

        with self.assertRaises(SystemExit):
            parser().parse_args(["build", "--flavor", "irz", "--publish"])


class VersionTest(unittest.TestCase):
    def test_order(self):
        self.assertTrue(ipk.newer("0.1-r2611261430", "0.1-r2611191108"))
        self.assertFalse(ipk.newer("0.1-r2611191108", "0.1-r2611261430"))
        self.assertTrue(ipk.newer("1.3-r2", "1.3-r1"))
        self.assertTrue(ipk.newer("1.10", "1.9"))

    def test_index_parse(self):
        with tempfile.TemporaryDirectory() as d:
            p = Path(d) / "Packages"
            p.write_text(
                "Package: halo\nVersion: 0.1-r1\nArchitecture: all\n\n"
                "Package: halo-metrics\nVersion: 0.1-r2\nArchitecture: all\n"
            )
            self.assertEqual(_index_versions(p), {"halo": "0.1-r1", "halo-metrics": "0.1-r2"})


if __name__ == "__main__":
    unittest.main()
