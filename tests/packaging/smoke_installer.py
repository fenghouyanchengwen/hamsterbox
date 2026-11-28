"""Install, start and uninstall the Windows build using disposable libraries."""

from contextlib import closing
import json
import os
from pathlib import Path
import sqlite3
import subprocess
import sys
from tempfile import TemporaryDirectory
import time
from urllib.error import URLError
from urllib.request import urlopen

from alembic import command
from alembic.config import Config
from alembic.script import ScriptDirectory

BACKEND = Path(__file__).resolve().parents[2] / "backend"
sys.path.insert(0, str(BACKEND))

from app.db import models  # noqa: E402,F401  Register the Alpha fallback schema.
from app.db.base import Base  # noqa: E402
from app.db.session import build_engine  # noqa: E402

BASE_URL = "http://127.0.0.1:8000"
TITLE = "Existing Alpha entry"


def read_api(path: str) -> dict:
    with urlopen(BASE_URL + path, timeout=2) as response:
        return json.load(response)


def seed_alpha(db: Path, *, fallback: bool) -> None:
    db.parent.mkdir(parents=True, exist_ok=True)
    engine = build_engine(f"sqlite:///{db.as_posix()}")
    try:
        if fallback:
            Base.metadata.create_all(engine)
        else:
            config = Config(str(BACKEND / "alembic.ini"))
            config.attributes["database_url"] = engine.url
            command.upgrade(config, "0001_alpha1_initial_schema")
    finally:
        engine.dispose()
    with closing(sqlite3.connect(db)) as connection, connection:
        connection.execute(
            "INSERT INTO entries (id, share_id, title, type, created_at, updated_at) "
            "VALUES (1, '009207af-8479-40d9-bc55-0a996ef06949', ?, 'image', "
            "'2026-11-01 12:00:00', '2026-11-01 12:00:00')",
            (TITLE,),
        )
        if fallback:
            connection.execute(
                "INSERT INTO tag_categories (id, name, created_at, updated_at) "
                "VALUES (8, '未分类标签', '2026-11-01 12:00:00', '2026-11-01 12:00:00')"
            )


def verify_start(exe: Path, db: Path, *, existing: bool, default_path: bool = False) -> None:
    env = os.environ.copy()
    env.pop("HAMSTERBOX_DB_URL", None)
    env.pop("HAMSTERBOX_DB_PATH", None)
    if not default_path:
        env["HAMSTERBOX_DB_PATH"] = str(db)
    with subprocess.Popen([str(exe)], cwd=exe.parent, env=env) as app:
        try:
            deadline = time.monotonic() + 45
            while time.monotonic() < deadline:
                assert app.poll() is None, f"Desktop app exited with code {app.returncode}"
                try:
                    assert read_api("/api/health") == {"status": "ok"}
                    break
                except (TimeoutError, URLError):
                    time.sleep(0.25)
            else:
                raise AssertionError("Installed application did not start its API")
            assert read_api("/api/version") == {"version": "0.3.0"}
            if existing:
                assert read_api("/api/entries/1")["title"] == TITLE
            head = ScriptDirectory.from_config(Config(str(BACKEND / "alembic.ini"))).get_current_head()
            with closing(sqlite3.connect(db)) as connection:
                assert connection.execute("SELECT version_num FROM alembic_version").fetchall() == [(head,)]
                assert connection.execute("PRAGMA foreign_key_check").fetchall() == []
                assert connection.execute(
                    "SELECT count(*) FROM tag_categories WHERE system_key='uncategorized'"
                ).fetchone() == (1,)
                if default_path:
                    assert connection.execute(
                        "SELECT name, system_key FROM tag_categories WHERE id=8"
                    ).fetchone() == ("未分类标签", None)
            print(f"Verified installed startup and database: {db.name}", flush=True)
        finally:
            if app.poll() is None:
                app.terminate()
                app.wait(timeout=15)


def main(installer: Path) -> None:
    silent = ["/VERYSILENT", "/SUPPRESSMSGBOXES", "/NORESTART"]
    with TemporaryDirectory(prefix="hamsterbox-setup-") as tmp:
        root = Path(tmp)
        install = root / "app"
        setup_env = dict(os.environ, HAMSTERBOX_DB_PATH=str(root / "setup.db"))
        subprocess.run(
            [str(installer), *silent, f"/DIR={install}", "/NOICONS", "/TASKS="],
            check=True, timeout=180, env=setup_env,
        )
        app, uninstaller = install / "HamsterBox.exe", install / "unins000.exe"
        try:
            assert app.is_file() and uninstaller.is_file()
            assert (install / "_internal" / "migrations" / "env.py").is_file()
            verify_start(app, root / "fresh.db", existing=False)
            versioned = root / "alpha-0001.db"
            seed_alpha(versioned, fallback=False)
            verify_start(app, versioned, existing=True)
            legacy = install / "data" / "library.db"
            seed_alpha(legacy, fallback=True)
            verify_start(app, legacy, existing=True, default_path=True)
        finally:
            if uninstaller.is_file():
                subprocess.run([str(uninstaller), *silent], check=True, timeout=180)
        assert not app.exists()
        assert legacy.is_file(), "Uninstall removed the existing library"
        print("Verified install and uninstall. Existing library preserved.", flush=True)


if __name__ == "__main__":
    main(Path(sys.argv[1]).resolve(strict=True))
