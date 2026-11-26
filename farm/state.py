"""Состояние фермы: сборки, пакеты, публикации, git pull. SQLite."""

from __future__ import annotations

import json
import sqlite3
from pathlib import Path

SCHEMA = """
create table if not exists builds (
  id integer primary key autoincrement,
  flavor text not null,
  platform text not null,
  started text not null,
  finished text,
  status text not null,
  release text,
  log text,
  manifest text,
  published integer not null default 0,
  pid integer
);
create table if not exists packages (
  build_id integer not null,
  name text not null,
  version text not null,
  arch text not null,
  file text not null,
  sha256 text not null,
  source_branch text,
  source_commit text
);
create index if not exists packages_build on packages(build_id);
create table if not exists publishes (
  id integer primary key autoincrement,
  feed text not null,
  build_id integer,
  ts text not null,
  packages integer,
  detail text
);
create table if not exists pulls (
  id integer primary key autoincrement,
  ts text not null,
  head text,
  behind integer,
  ahead integer,
  ok integer,
  detail text
);
"""


def connect(state_dir: Path) -> sqlite3.Connection:
    state_dir.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(state_dir / "state.db")
    conn.row_factory = sqlite3.Row
    conn.executescript(SCHEMA)
    try:
        conn.execute("alter table builds add column pid integer")
        conn.commit()
    except sqlite3.OperationalError:
        pass
    return conn


def start_build(conn, flavor: str, platform: str, started: str, release: str, log: Path,
                pid: int | None = None) -> int:
    cur = conn.execute(
        "insert into builds(flavor, platform, started, status, release, log, pid) values(?,?,?,?,?,?,?)",
        (flavor, platform, started, "running", release, str(log), pid),
    )
    conn.commit()
    return int(cur.lastrowid)


def finish_build(conn, build_id: int, status: str, finished: str, manifest: dict | None) -> None:
    conn.execute(
        "update builds set status=?, finished=?, manifest=? where id=?",
        (status, finished, json.dumps(manifest, ensure_ascii=False) if manifest else None, build_id),
    )
    conn.commit()


def add_package(conn, build_id: int, meta, file: str, sha256: str, branch: str, commit: str) -> None:
    conn.execute(
        "insert into packages(build_id, name, version, arch, file, sha256, source_branch, source_commit)"
        " values(?,?,?,?,?,?,?,?)",
        (build_id, meta.name, meta.version, meta.arch, file, sha256, branch, commit),
    )


def record_publish(conn, feed: str, build_id: int | None, ts: str, count: int, detail: dict) -> None:
    conn.execute(
        "insert into publishes(feed, build_id, ts, packages, detail) values(?,?,?,?,?)",
        (feed, build_id, ts, count, json.dumps(detail, ensure_ascii=False)),
    )
    conn.execute("update builds set published=1 where id=?", (build_id,))
    conn.commit()


def record_pull(conn, ts: str, head: str, behind: int, ahead: int, ok: bool, detail: str) -> None:
    conn.execute(
        "insert into pulls(ts, head, behind, ahead, ok, detail) values(?,?,?,?,?,?)",
        (ts, head, behind, ahead, 1 if ok else 0, detail),
    )
    conn.commit()


def mark_stopped(conn, build_id: int, finished: str) -> None:
    conn.execute(
        "update builds set status='stopped', finished=? where id=? and status='running'",
        (finished, build_id),
    )
    conn.commit()


def last_publish(conn, feed: str):
    return conn.execute(
        "select * from publishes where feed=? order by id desc limit 1", (feed,)
    ).fetchone()


def last_build(conn, flavor: str):
    return conn.execute(
        "select * from builds where flavor=? order by id desc limit 1", (flavor,)
    ).fetchone()


def recent_builds(conn, limit: int = 10):
    return conn.execute("select * from builds order by id desc limit ?", (limit,)).fetchall()


def last_pull(conn):
    return conn.execute("select * from pulls order by id desc limit 1").fetchone()
