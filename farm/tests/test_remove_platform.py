"""Удаление платформы: секция из farm.toml и правки из platforms.local.toml."""

from __future__ import annotations

import tempfile
import tomllib
import unittest
from pathlib import Path

from farm import config

TOML = """[farm]
repo = "."

[flavors.irz]
brand = "irzOS"
feed = "halo"
packages = "packages"
sdk_platform = "r50"

[platforms.r50]
status = "active"
sdk = "/sdk/r50"
feeds = "/feeds/r50.conf"

[platforms.r2]
status = "active"
sdk = "/sdk/r2"
feeds = "/feeds/r2.conf"

[platforms.irm]
status = "active"
sdk = "/sdk/irm"
feeds = "/feeds/irm.conf"
"""


class RemovePlatformTest(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.project = Path(self.tmp.name)
        (self.project / "farm.toml").write_text(TOML)
        (self.project / "platforms.local.toml").write_text(
            '[platforms.irm]\nsdk = "/custom/irm"\n\n[platforms.r2]\nsdk = "/custom/r2"\n'
        )

    def tearDown(self):
        self.tmp.cleanup()

    def test_remove_unused(self):
        config.remove_platform(self.project, "irm")
        raw = tomllib.loads((self.project / "farm.toml").read_text())
        self.assertNotIn("irm", raw["platforms"])
        self.assertIn("r2", raw["platforms"])
        local = tomllib.loads((self.project / "platforms.local.toml").read_text())
        self.assertNotIn("irm", local["platforms"])
        self.assertIn("r2", local["platforms"])

    def test_cannot_remove_flavor_platform(self):
        with self.assertRaises(config.ConfigError):
            config.remove_platform(self.project, "r50")
        raw = tomllib.loads((self.project / "farm.toml").read_text())
        self.assertIn("r50", raw["platforms"])

    def test_unknown(self):
        with self.assertRaises(config.ConfigError):
            config.remove_platform(self.project, "nope")


if __name__ == "__main__":
    unittest.main()
