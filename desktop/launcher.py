"""桌面启动器：启动本地 API，再打开 PyWebView 窗口。"""

import sys
import threading
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "backend"))

import uvicorn  # noqa: E402
import webview  # noqa: E402

HOST = "127.0.0.1"
PORT = 8000


def _serve() -> None:
    uvicorn.run("app.main:app", host=HOST, port=PORT, log_level="info")


def main() -> None:
    threading.Thread(target=_serve, daemon=True).start()
    time.sleep(1.5)
    webview.create_window(
        "仓鼠盒",
        f"http://{HOST}:{PORT}/",
        width=1280,
        height=820,
    )
    webview.start()


if __name__ == "__main__":
    main()
