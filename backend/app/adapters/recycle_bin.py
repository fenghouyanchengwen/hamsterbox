"""调用操作系统回收站安全移除本地文件，不提供永久删除。"""

from __future__ import annotations

import ctypes
import subprocess
import sys
from pathlib import Path


FO_DELETE = 0x0003
FOF_SILENT = 0x0004
FOF_NOCONFIRMATION = 0x0010
FOF_ALLOWUNDO = 0x0040
FOF_NOERRORUI = 0x0400


class RecycleBinError(RuntimeError):
    """操作系统无法将文件移入系统回收站。"""


def _move_to_windows_recycle_bin(path: Path) -> None:
    from ctypes import wintypes

    class _SHFILEOPSTRUCTW(ctypes.Structure):
        if ctypes.sizeof(ctypes.c_void_p) == 4:
            _pack_ = 1
        _fields_ = [
            ("hwnd", wintypes.HWND),
            ("wFunc", wintypes.UINT),
            ("pFrom", ctypes.c_void_p),
            ("pTo", ctypes.c_void_p),
            ("fFlags", wintypes.WORD),
            ("fAnyOperationsAborted", wintypes.BOOL),
            ("hNameMappings", ctypes.c_void_p),
            ("lpszProgressTitle", wintypes.LPCWSTR),
        ]

    # SHFileOperationW 要求完整绝对路径且以双空字符结尾，否则 FOF_ALLOWUNDO 不生效。
    double_null_buffer = ctypes.create_unicode_buffer(str(path) + "\0")
    operation = _SHFILEOPSTRUCTW(
        hwnd=None,
        wFunc=FO_DELETE,
        pFrom=ctypes.cast(double_null_buffer, ctypes.c_void_p).value,
        pTo=None,
        fFlags=FOF_ALLOWUNDO | FOF_NOCONFIRMATION | FOF_NOERRORUI | FOF_SILENT,
        fAnyOperationsAborted=False,
        hNameMappings=None,
        lpszProgressTitle=None,
    )
    code = ctypes.windll.shell32.SHFileOperationW(ctypes.byref(operation))  # type: ignore[attr-defined]
    if code != 0 or operation.fAnyOperationsAborted:
        raise RecycleBinError(f"系统回收站拒绝移动文件 (code={code}): {path.name}")


class SystemRecycleBin:
    """跨平台的系统回收站移动器。

    只接收后端已经解析和校验过的绝对路径 ``Path``，绝不回退为永久删除。
    """

    def move(self, path: Path) -> None:
        if not path.is_absolute():
            raise RecycleBinError("移入回收站的路径必须是绝对路径")

        resolved = path.resolve(strict=False)
        if not resolved.exists() or not resolved.is_file():
            raise RecycleBinError(f"待移入回收站的普通文件不存在: {resolved.name}")

        try:
            if sys.platform.startswith("win"):
                _move_to_windows_recycle_bin(resolved)
            elif sys.platform == "darwin":
                script = (
                    'on run argv\n'
                    'tell application "Finder" to delete POSIX file (item 1 of argv)\n'
                    'end run'
                )
                subprocess.run(["osascript", "-e", script, str(resolved)], check=True)
            else:
                subprocess.run(["gio", "trash", str(resolved)], check=True)
        except RecycleBinError:
            raise
        except (OSError, subprocess.SubprocessError) as exc:
            raise RecycleBinError(f"无法将文件移入系统回收站: {resolved.name}") from exc
