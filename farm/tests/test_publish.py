"""Публикация: индекс, версии, сверка файлов."""

from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from farm.build import BuildError
from farm.publish import _check_index, _drop_old_versions, _index_versions
from farm.tests.test_farm import make_ipk


class IndexTest(unittest.TestCase):
    def test_parse_multi(self):
        with tempfile.TemporaryDirectory() as d:
            p = Path(d) / "Packages"
            p.write_text(
                "Package: a\nVersion: 1\nArchitecture: all\nDepends: x, y\n\n"
                "Package: b\nVersion: 2-r3\nArchitecture: arm\n"
            )
            self.assertEqual(_index_versions(p), {"a": "1", "b": "2-r3"})

    def test_missing_file(self):
        self.assertEqual(_index_versions(Path("/nonexistent/Packages")), {})


class DropOldTest(unittest.TestCase):
    def test_removes_other_versions_only(self):
        with tempfile.TemporaryDirectory() as d:
            dest = Path(d)
            make_ipk(dest / "halo_0.1-r1_all.ipk", "halo", "0.1-r1")
            make_ipk(dest / "halo_0.1-r2_all.ipk", "halo", "0.1-r2")
            make_ipk(dest / "other_1_all.ipk", "other", "1")
            _drop_old_versions(dest, {"halo": "0.1-r2"})
            names = sorted(p.name for p in dest.glob("*.ipk"))
            self.assertEqual(names, ["halo_0.1-r2_all.ipk", "other_1_all.ipk"])


class CheckIndexTest(unittest.TestCase):
    def _index(self, dest: Path) -> None:
        lines = []
        for f in sorted(dest.glob("*.ipk")):
            name, version = f.name.rsplit("_", 2)[0], f.name.rsplit("_", 2)[1]
            lines.append(f"Package: {name}\nVersion: {version}\nArchitecture: all\n")
        (dest / "Packages").write_text("\n".join(lines))

    def test_consistent(self):
        with tempfile.TemporaryDirectory() as d:
            dest = Path(d)
            make_ipk(dest / "halo_0.1-r1_all.ipk", "halo", "0.1-r1")
            self._index(dest)
            self.assertEqual(_check_index(dest)["packages"], 1)

    def test_stray_file(self):
        with tempfile.TemporaryDirectory() as d:
            dest = Path(d)
            make_ipk(dest / "halo_0.1-r1_all.ipk", "halo", "0.1-r1")
            self._index(dest)
            make_ipk(dest / "extra_1_all.ipk", "extra", "1")
            with self.assertRaises(BuildError):
                _check_index(dest)

    def test_missing_file(self):
        with tempfile.TemporaryDirectory() as d:
            dest = Path(d)
            (dest / "Packages").write_text("Package: ghost\nVersion: 1\nArchitecture: all\n")
            with self.assertRaises(BuildError):
                _check_index(dest)


if __name__ == "__main__":
    unittest.main()
