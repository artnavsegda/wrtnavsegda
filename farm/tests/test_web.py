"""Веб-слой: разбор фида и план сборки (без HTTP)."""

from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from types import SimpleNamespace

from farm import config, web


class FeedIndexTest(unittest.TestCase):
    def test_parse(self):
        with tempfile.TemporaryDirectory() as d:
            p = Path(d) / "Packages"
            p.write_text(
                "Package: halo\nVersion: 0.1-r1\nArchitecture: all\n"
                "Depends: lighttpd, ttyd\nInstalled-Size: 1234\n\n"
                "Package: arm-only\nVersion: 1.4.85-r1\nArchitecture: arm_cortex-a7\n"
            )
            rows = web._feed_index(p)
            self.assertEqual(len(rows), 2)
            self.assertEqual(rows[0]["name"], "halo")
            self.assertEqual(rows[0]["depends"], "lighttpd, ttyd")
            self.assertEqual(rows[0]["size"], 1234)
            self.assertEqual(rows[1]["arch"], "arm_cortex-a7")

    def test_missing(self):
        self.assertEqual(web._feed_index(Path("/nonexistent/Packages")), [])


class ProgressTest(unittest.TestCase):
    def _farm(self, tmp: str, text: str) -> SimpleNamespace:
        base = Path(tmp) / "builds" / "5"
        base.mkdir(parents=True)
        (base / "build.log").write_text(text)
        return SimpleNamespace(builds_dir=Path(tmp) / "builds", state_dir=Path(tmp))

    def test_full_build(self):
        with tempfile.TemporaryDirectory() as d:
            farm = self._farm(d, "[18:00:00] пакетов к сборке: 15\n[18:00:01] [1/15] aurora\n[18:01:00] [2/15] halo\n")
            p = web._progress(farm, {"id": 5}, 15)
            self.assertEqual(p["done"], {"aurora"})
            self.assertEqual(p["current"], "halo")
            self.assertTrue(p["full"])

    def test_point_build(self):
        with tempfile.TemporaryDirectory() as d:
            farm = self._farm(d, "[18:00:00] пакетов к сборке: 1\n[18:00:01] [1/1] halo-mod-dash-gauge\n")
            p = web._progress(farm, {"id": 5}, 15)
            self.assertEqual(p["done"], set())
            self.assertEqual(p["current"], "halo-mod-dash-gauge")
            self.assertFalse(p["full"])

    def test_no_log(self):
        with tempfile.TemporaryDirectory() as d:
            farm = SimpleNamespace(builds_dir=Path(d) / "builds")
            self.assertIsNone(web._progress(farm, {"id": 99}, 15))


class PlanTest(unittest.TestCase):
    def setUp(self):
        self.farm = config.load()

    def test_irz_plan(self):
        plan = web._plan(self.farm, self.farm.flavors["irz"])
        self.assertIn("halo", plan)
        self.assertIn("halo-preview", plan)
        self.assertEqual(plan["halo"][1], "halo")
        self.assertEqual(plan["halo-preview"][1], "halo")  # оба из каталога halo
        self.assertEqual(plan["zenith-uc"][1], "horizon-uc")
        self.assertIn("opkg-repository", plan)
        self.assertNotIn("hello", plan)

    def test_donyx_plan(self):
        plan = web._plan(self.farm, self.farm.flavors["donyx"])
        self.assertIn("halo-mod-dash-webgl", plan)
        self.assertNotIn("aurora", plan)

    def test_indices_follow_feed_packages(self):
        flavor = self.farm.flavors["irz"]
        dirs = self.farm.packages(flavor)
        plan = web._plan(self.farm, flavor)
        for name, (idx, d) in plan.items():
            self.assertEqual(dirs[idx], d)


if __name__ == "__main__":
    unittest.main()
