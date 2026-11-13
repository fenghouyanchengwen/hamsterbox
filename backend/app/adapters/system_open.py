"""调用操作系统默认程序打开本地文件。"""

import os
import subprocess
import sys
from pathlib import Path


class SystemOpenError(RuntimeError):
    """操作系统无法启动文件的默认程序。"""


class SystemDefaultOpener:
    """跨平台的系统默认程序打开器。

    适配器只接收后端已经解析和校验过的 ``Path``，不负责接收前端路径
    或拼接 shell 命令。
    """

    def open(self, path: Path) -> None:
        try:
            if sys.platform.startswith("win"):
                os.startfile(str(path))  # type: ignore[attr-defined]
            elif sys.platform == "darwin":
                subprocess.run(["open", str(path)], check=True)
            else:
                subprocess.run(["xdg-open", str(path)], check=True)
        except (FileNotFoundError, PermissionError, OSError, subprocess.SubprocessError) as exc:
            raise SystemOpenError(f"无法使用系统默认程序打开资源: {path.name}") from exc
