"""桌面启动器：启动本地 API，再打开 PyWebView 窗口。"""

from contextlib import contextmanager
import socket
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
from app.adapters.bridge import NativeBridge  # noqa: E402
from app.api.dependencies import get_resource_service  # noqa: E402

HOST = "127.0.0.1"
PORT = 8000


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
    config = uvicorn.Config(
        "app.main:app", host=HOST, port=PORT, log_level="info", timeout_graceful_shutdown=3
    )
    server = uvicorn.Server(config)
    # Reserve the port before granting the window access to native methods.
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as listener:
        # Windows SO_REUSEADDR can share a port with a different listener.
        option = getattr(socket, "SO_EXCLUSIVEADDRUSE", socket.SO_REUSEADDR)
        listener.setsockopt(socket.SOL_SOCKET, option, 1)
        listener.bind((HOST, PORT))
        api_thread = threading.Thread(target=server.run, kwargs={"sockets": [listener]}, daemon=True)
        api_thread.start()
        try:
            _wait_for_backend()
            bridge = NativeBridge(contextmanager(get_resource_service))
            window = webview.create_window(
                "仓鼠盒",
                f"http://{HOST}:{PORT}/",
                js_api=bridge,
                width=1280,
                height=820,
            )
            bridge._bind_window(window)
            webview.start()
        finally:
            server.should_exit = True
            api_thread.join(timeout=5)


if __name__ == "__main__":
    main()
