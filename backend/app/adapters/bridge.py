"""PyWebView bridge for native dialogs and registered resources."""

from collections.abc import Callable
from contextlib import AbstractContextManager
from pathlib import Path
import subprocess
import sys

import webview

from app.application.errors import (
    ResourceAccessDeniedError,
    ResourceFileMissingError,
    ResourceNotFileError,
    ResourceNotFoundError,
    ResourceOpenFailedError,
    ResourcePathNotAbsoluteError,
)
from app.application.resource_service import ResourceService


EXECUTABLE_EXTENSIONS = {".exe", ".bat", ".cmd", ".lnk"}
RESOURCE_ERRORS = {
    ResourceNotFoundError: ("RESOURCE_NOT_FOUND", "资源不存在"),
    ResourceFileMissingError: ("RESOURCE_FILE_MISSING", "资源文件不存在"),
    ResourceAccessDeniedError: ("RESOURCE_ACCESS_DENIED", "无法访问资源文件"),
    ResourceNotFileError: ("RESOURCE_NOT_FILE", "资源不是普通文件"),
    ResourcePathNotAbsoluteError: ("RESOURCE_PATH_NOT_ABSOLUTE", "资源路径无效"),
    ResourceOpenFailedError: ("RESOURCE_OPEN_FAILED", "无法使用系统默认程序打开资源"),
}
RESOURCE_FAILURES = tuple(RESOURCE_ERRORS)


def _failure(error: str, message: str) -> dict:
    return {"ok": False, "error": error, "message": message}


class NativeBridge:
    def __init__(self, resource_service: Callable[[], AbstractContextManager[ResourceService]]):
        self._window = None
        self._resource_service = resource_service

    def _bind_window(self, window: webview.Window) -> None:
        self._window = window

    def pick_files(self) -> list[str]:
        if self._window is None:
            return []
        result = self._window.create_file_dialog(webview.OPEN_DIALOG, allow_multiple=True)
        return list(result) if result else []

    def pick_folder(self) -> str | None:
        if self._window is None:
            return None
        result = self._window.create_file_dialog(webview.FOLDER_DIALOG)
        return result[0] if result else None

    def pick_package(self) -> str | None:
        if self._window is None:
            return None
        result = self._window.create_file_dialog(
            webview.OPEN_DIALOG, file_types=("仓鼠盒分享包 (*.hbox)",)
        )
        return result[0] if result else None

    def choose_save_path(self) -> str | None:
        if self._window is None:
            return None
        result = self._window.create_file_dialog(webview.SAVE_DIALOG)
        return result[0] if result else None

    def _confirm_open(self, path: Path) -> bool:
        if path.suffix.lower() not in EXECUTABLE_EXTENSIONS:
            return True
        if self._window is None:
            return False
        return self._window.create_confirmation_dialog(
            "确认运行文件", f"确定要打开「{path.name}」吗？它可能运行程序或脚本。"
        ) is True

    def open_resource(self, resource_id: int) -> dict:
        """Open a registered resource after native confirmation when required."""
        if type(resource_id) is not int or not 0 < resource_id < 2**63:
            return _failure("RESOURCE_ID_INVALID", "资源 ID 无效")
        try:
            with self._resource_service() as service:
                service.open_resource(resource_id, confirm_open=self._confirm_open)
        except RESOURCE_FAILURES as exc:
            return _failure(*RESOURCE_ERRORS[type(exc)])
        except (OSError, RuntimeError):
            return _failure(*RESOURCE_ERRORS[ResourceOpenFailedError])
        return {"ok": True}

    def reveal_resource(self, resource_id: int) -> dict:
        if type(resource_id) is not int or not 0 < resource_id < 2**63:
            return _failure("RESOURCE_ID_INVALID", "资源 ID 无效")
        try:
            with self._resource_service() as service:
                path = service.resolve_path(resource_id)
            if sys.platform == "win32":
                subprocess.run(["explorer", "/select,", str(path)], check=False)
            elif sys.platform == "darwin":
                subprocess.run(["open", "-R", str(path)], check=True)
            else:
                subprocess.run(["xdg-open", str(path.parent)], check=True)
        except RESOURCE_FAILURES as exc:
            return _failure(*RESOURCE_ERRORS[type(exc)])
        except (OSError, subprocess.SubprocessError):
            return _failure("RESOURCE_REVEAL_FAILED", "无法定位资源文件")
        return {"ok": True}
