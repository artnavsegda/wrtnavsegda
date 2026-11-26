"""Источники пакетов: разбор Makefile, repo_dirs, source_map."""

from __future__ import annotations

import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace

from farm import sources


def write(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text)


class SourcesTest(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        repo = Path(self.tmp.name)
        write(repo / "halo.mk",
              "PKG_SOURCE_URL:=git@github.com:artnavsegda/donyx.git\n"
              "HALO_PINNED:=12f3f2f316bddbc0b8da26e8704b1338b1b777a0\n"
              "HALO_BRANCH?=split\n")
        write(repo / "mod" / "Makefile",
              "PKG_NAME:=mod\ninclude ../halo.mk\n"
              "$(eval $(call BuildPackage,$(PKG_NAME)))\n"
              "$(eval $(call BuildPackage,$(PKG_NAME)-extra))\n")
        write(repo / "own" / "Makefile",
              "PKG_NAME:=own\nPKG_SOURCE_PROTO:=git\n"
              "PKG_SOURCE_URL:=git@github.com:u/own.git\n"
              "PKG_SOURCE_VERSION:=30cc82fb43941e43becec0d6fd88428118920d8c\n"
              "$(eval $(call BuildPackage,own))\n")
        write(repo / "aur" / "Makefile",
              "PKG_NAME:=aur\nAURORA_PINNED:=0b714deaf14bd3d222e3ee64f858160ab732f1d3\n"
              "AURORA_BRANCH?=vue3\nPKG_SOURCE_URL:=git@gitlab.x:Routers/aurora.git\n"
              "$(eval $(call BuildPackage,aur))\n")
        write(repo / "intree" / "Makefile",
              "PKG_NAME:=intree\n$(eval $(call BuildPackage,intree))\n")
        write(repo / "empty" / "README", "no makefile")
        self.farm = SimpleNamespace(repo=repo)

    def tearDown(self):
        self.tmp.cleanup()

    def test_repo_dirs(self):
        self.assertEqual(sources.repo_dirs(self.farm), ["aur", "intree", "mod", "own"])

    def test_makefile_packages(self):
        self.assertEqual(
            sources.makefile_packages(self.farm.repo / "mod" / "Makefile"),
            ["mod", "mod-extra"],
        )
        self.assertEqual(sources.makefile_packages(self.farm.repo / "empty" / "x" / "Makefile"), [])

    def test_halo_source(self):
        src = sources.source_of(self.farm, "mod")
        self.assertEqual(src["repo"], "split")
        self.assertEqual(src["commit"], "12f3f2f")
        self.assertEqual(src["commit_full"], "12f3f2f316bddbc0b8da26e8704b1338b1b777a0")
        self.assertIn("donyx", src["url"])

    def test_pinned_source(self):
        src = sources.source_of(self.farm, "own")
        self.assertEqual(src["repo"], "own")
        self.assertEqual(src["commit"], "30cc82f")

    def test_aurora_source(self):
        src = sources.source_of(self.farm, "aur")
        self.assertEqual(src["repo"], "vue3")
        self.assertEqual(src["commit"], "0b714de")

    def test_in_tree(self):
        src = sources.source_of(self.farm, "intree")
        self.assertEqual(src["repo"], "в репо")
        self.assertEqual(src["commit"], "")

    def test_source_map(self):
        m = sources.source_map(self.farm)
        self.assertIn("mod-extra", m)
        self.assertEqual(m["mod"]["repo"], "split")
        self.assertEqual(m["own"]["commit"], "30cc82f")


if __name__ == "__main__":
    unittest.main()
