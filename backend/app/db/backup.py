"""SQLite 在线备份与一致性校验。

约定（见 `data/README.md`）：

- 备份前执行 WAL checkpoint，再使用 SQLite 在线备份接口；
- 备份文件名带时间戳，默认保留最近 10 份；
- 恢复后先做外键一致性检查，再允许应用启动。
"""

from __future__ import annotations

import sqlite3
from contextlib import closing
from datetime import datetime
from pathlib import Path

BACKUP_PREFIX = "library-"
DEFAULT_RETENTION = 10


def create_backup(
    database_path: str | Path,
    backup_dir: str | Path,
    *,
    keep: int = DEFAULT_RETENTION,
    now: datetime | None = None,
) -> Path:
    """创建一份在线备份并返回备份文件路径。"""
    source_path = Path(database_path)

    if not source_path.is_file():
        raise FileNotFoundError(f"数据库文件不存在：{source_path}")

    target_dir = Path(backup_dir)
    target_dir.mkdir(parents=True, exist_ok=True)

    stamp = (now or datetime.now()).strftime("%Y%m%d-%H%M%S")
    target_path = _unique_path(target_dir / f"{BACKUP_PREFIX}{stamp}.db")

    with closing(sqlite3.connect(source_path)) as source:
        source.execute("PRAGMA wal_checkpoint(TRUNCATE)")
        with closing(sqlite3.connect(target_path)) as destination:
            source.backup(destination)

    _prune(target_dir, keep)
    return target_path


def integrity_ok(database_path: str | Path) -> bool:
    """执行 `PRAGMA integrity_check`。"""
    with closing(sqlite3.connect(Path(database_path))) as connection:
        result = connection.execute("PRAGMA integrity_check").fetchone()
    return bool(result) and result[0] == "ok"


def foreign_key_violations(database_path: str | Path) -> list[tuple]:
    """返回外键一致性问题的列表，空列表表示通过。"""
    with closing(sqlite3.connect(Path(database_path))) as connection:
        return list(connection.execute("PRAGMA foreign_key_check").fetchall())


def verify_backup(database_path: str | Path) -> bool:
    """备份可用性检查：完整性通过且没有外键问题。"""
    return integrity_ok(database_path) and not foreign_key_violations(database_path)


def _unique_path(path: Path) -> Path:
    candidate = path
    suffix = 1

    while candidate.exists():
        candidate = path.with_name(f"{path.stem}-{suffix}{path.suffix}")
        suffix += 1

    return candidate


def _prune(directory: Path, keep: int) -> None:
    if keep <= 0:
        return

    backups = sorted(
        directory.glob(f"{BACKUP_PREFIX}*.db"),
        key=lambda item: item.name,
        reverse=True,
    )

    for stale in backups[keep:]:
        stale.unlink(missing_ok=True)
