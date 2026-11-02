"""备份与一致性校验测试。"""

from __future__ import annotations

import sqlite3
from datetime import datetime, timedelta
from pathlib import Path

import pytest

from app.db.backup import (
    create_backup,
    foreign_key_violations,
    integrity_ok,
    verify_backup,
)


def _make_database(path: Path) -> Path:
    with sqlite3.connect(path) as connection:
        connection.execute("CREATE TABLE notes (id INTEGER PRIMARY KEY, body TEXT)")
        connection.execute("INSERT INTO notes (body) VALUES ('hello')")
    return path


def test_create_backup_copies_database(tmp_path: Path) -> None:
    source = _make_database(tmp_path / "library.db")
    target = create_backup(source, tmp_path / "backups")

    assert target.is_file()
    assert target.name.startswith("library-")
    assert verify_backup(target) is True

    with sqlite3.connect(target) as connection:
        assert connection.execute("SELECT body FROM notes").fetchone() == ("hello",)


def test_backup_keeps_only_latest_files(tmp_path: Path) -> None:
    source = _make_database(tmp_path / "library.db")
    backup_dir = tmp_path / "backups"
    base = datetime(2026, 1, 1, 12, 0, 0)

    created = [
        create_backup(
            source,
            backup_dir,
            keep=3,
            now=base + timedelta(minutes=index),
        )
        for index in range(5)
    ]

    remaining = sorted(path.name for path in backup_dir.glob("library-*.db"))
    assert remaining == sorted(path.name for path in created[-3:])


def test_backup_name_does_not_collide(tmp_path: Path) -> None:
    source = _make_database(tmp_path / "library.db")
    backup_dir = tmp_path / "backups"
    moment = datetime(2026, 1, 1, 12, 0, 0)

    first = create_backup(source, backup_dir, now=moment)
    second = create_backup(source, backup_dir, now=moment)

    assert first != second
    assert first.is_file() and second.is_file()


def test_backup_requires_existing_database(tmp_path: Path) -> None:
    with pytest.raises(FileNotFoundError):
        create_backup(tmp_path / "missing.db", tmp_path / "backups")


def test_integrity_check_passes_for_healthy_database(tmp_path: Path) -> None:
    source = _make_database(tmp_path / "library.db")

    assert integrity_ok(source) is True
    assert foreign_key_violations(source) == []


def test_foreign_key_check_detects_violation(tmp_path: Path) -> None:
    path = tmp_path / "broken.db"

    with sqlite3.connect(path) as connection:
        connection.execute("PRAGMA foreign_keys=OFF")
        connection.execute("CREATE TABLE parent (id INTEGER PRIMARY KEY)")
        connection.execute(
            "CREATE TABLE child ("
            "id INTEGER PRIMARY KEY, "
            "parent_id INTEGER REFERENCES parent(id))"
        )
        connection.execute("INSERT INTO child (parent_id) VALUES (99)")

    assert foreign_key_violations(path) != []
    assert verify_backup(path) is False
