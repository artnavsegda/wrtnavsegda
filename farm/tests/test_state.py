"""Состояние фермы: сборки, пакеты, публикации, pull."""

from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from farm import ipk, state


def meta(name="halo", version="0.1-r1", arch="all"):
    return ipk.IpkMeta(name=name, version=version, arch=arch)


class StateTest(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.dir = Path(self.tmp.name)
        self.conn = state.connect(self.dir)

    def tearDown(self):
        self.conn.close()
        self.tmp.cleanup()

    def test_build_lifecycle(self):
        bid = state.start_build(self.conn, "irz", "r50", "2026-11-26T17:00:00+03:00", "2611261700", self.dir / "log")
        self.assertGreater(bid, 0)
        self.assertEqual(state.last_build(self.conn, "irz")["status"], "running")

        state.finish_build(self.conn, bid, "ok", "2026-11-26T17:05:00+03:00", {"id": bid})
        row = state.last_build(self.conn, "irz")
        self.assertEqual(row["status"], "ok")
        self.assertEqual(row["manifest"], '{"id": %d}' % bid)

    def test_mark_stopped_only_running(self):
        bid = state.start_build(self.conn, "irz", "r50", "t", "r", self.dir / "l")
        state.mark_stopped(self.conn, bid, "t2")
        self.assertEqual(state.last_build(self.conn, "irz")["status"], "stopped")
        state.mark_stopped(self.conn, bid, "t3")
        self.assertEqual(state.last_build(self.conn, "irz")["status"], "stopped")

    def test_packages_and_publish(self):
        bid = state.start_build(self.conn, "irz", "r50", "t", "r", self.dir / "l")
        state.add_package(self.conn, bid, meta(), "halo_0.1-r1_all.ipk", "abc", "split", "12f3f2f")
        state.record_publish(self.conn, "halo", bid, "t2", 1, {"files": ["halo_0.1-r1_all.ipk"]})
        self.assertTrue(state.last_build(self.conn, "irz")["published"])
        pub = state.last_publish(self.conn, "halo")
        self.assertEqual(pub["packages"], 1)
        self.assertIsNone(state.last_publish(self.conn, "donyx"))

    def test_pull(self):
        state.record_pull(self.conn, "t", "abc", 2, 0, True, "ff")
        row = state.last_pull(self.conn)
        self.assertEqual((row["behind"], row["ahead"], row["ok"]), (2, 0, 1))

    def test_reopen_keeps_data(self):
        state.start_build(self.conn, "irz", "r50", "t", "r", self.dir / "l")
        self.conn.close()
        self.conn = state.connect(self.dir)
        self.assertEqual(len(state.recent_builds(self.conn)), 1)


if __name__ == "__main__":
    unittest.main()
