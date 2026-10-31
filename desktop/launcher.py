"""桌面启动器：启动本地 API，再打开 PyWebView 窗口。"""

import sys
import threading
import time
from pathlib import Path
from urllib.request import urlopen

if getattr(sys, "frozen", False):
    ROOT = Path(getattr(sys, "_MEIPASS", Path(sys.executable).parent))
else:
    ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "backend"))

import uvicorn  # noqa: E402
import webview  # noqa: E402

HOST = "127.0.0.1"
PORT = 8000


def _serve() -> None:
    uvicorn.run("app.main:app", host=HOST, port=PORT, log_level="info")


def _wait_for_backend(timeout: float = 20.0) -> None:
    """Wait until the local API is ready before creating the desktop window."""
    deadline = time.monotonic() + timeout
    last_error: OSError | None = None
    while time.monotonic() < deadline:
        try:
            with urlopen(f"http://{HOST}:{PORT}/api/health", timeout=1) as response:
                if response.status == 200:
                    return
        except OSError as error:
            last_error = error
        time.sleep(0.25)
    raise RuntimeError("仓鼠盒后端启动失败，请检查本地运行环境。") from last_error


def main() -> None:
    threading.Thread(target=_serve, daemon=True).start()
    _wait_for_backend()
    webview.create_window(
        "仓鼠盒",
        f"http://{HOST}:{PORT}/",
        width=1280,
        height=820,
    )
    webview.start()


if __name__ == "__main__":
    main()
