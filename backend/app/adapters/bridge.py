from pathlib import Path
import webview
import sys
import subprocess


class NativeBridge:
    def __init__(self, window=None):
        self._window = window

    def pick_files(self) -> list[str]:
        if self._window is None:
            return []
        result = self._window.create_file_dialog(
            webview.OPEN_DIALOG, allow_multiple=True#打开文件选择对话框，允许用户按住Ctrl多选文件
        )
        return list(result) if result else []#返回规则：用户选中文件返回字符串列表，用户点取消返回空列表

    def pick_folder(self) -> str | None:
        if self._window is None:
            return None
        result = self._window.create_file_dialog(webview.FOLDER_DIALOG)#打开文件夹选择对话框
        return result[0] if result else None

    def pick_package(self) -> list[str]:
        if self._window is None:
            return []
        result = self._window.create_file_dialog(
            webview.OPEN_DIALOG,
            allow_multiple=False,
            file_types=('仓鼠盒分享包 (*.zip)',"*.zip")
            #与选择文件相同，但只允许zip压缩包文件，其不可多选
        )
        return list(result) if result else None

    def choose_save_path(self) -> str | None:
        if self._window is None:
            return None
        result = self._window.create_file_dialog(webview.SAVE_DIALOG)#打开另存为选择对话框
        return result[0] if result else None

    def open_resource(self, resource_id: int) -> dict:
        # 由后端根据 resource_id 查询真实路径
        path = self._resolve_path(resource_id)  # 成员二/数据层提供
        if path is None or not path.exists():
            return {"ok": False, "error": "资源不存在或文件已失效"}
        if path.suffix.lower() in (".exe", ".bat", ".cmd", ".lnk"):
            return {
                "ok": False,
                "error": "EXECUTABLE_CONFIRM_REQUIRED",
                "message": "出于安全考虑，运行可执行文件需要二次确认。"
            }
        return self._safe_open_path(path)

    #专门针对可执行文件，用于二次确认
    #后端不调用，前端存在二次确认时可调用
    def confirm_open_executable(self, resource_id: int) -> dict:
        path = self._resolve_path(resource_id)
        if path is None or not path.exists():
            return {"ok": False, "error": "资源不存在或文件已失效"}
        return self._safe_open_path(path)

    def _safe_open_path(self, path: Path) -> dict:
        #内部方法：安全调用系统默认程序打开文件
        try:
            if sys.platform == "win32":
                import os
                os.startfile(str(path))
            elif sys.platform == "darwin":
                subprocess.run(["open", str(path)], check=False)
            else:
                subprocess.run(["xdg-open", str(path)], check=False)
            return {"ok": True}
        except OSError as exc:
            return {"ok": False, "error": f"无法打开文件: {exc}"}

    def reveal_resource(self, resource_id: int) -> dict:
        path = self._resolve_path(resource_id)
        if path is None or not path.exists():
            return {"ok": False, "error": "资源不存在或文件已失效"}
        try:
            if sys.platform == "win32":
                # Windows: explorer 定位文件，/select, 后面紧跟路径
                subprocess.run(["explorer", "/select,", str(path)], check=False)
            elif sys.platform == "darwin":
                # macOS: open -R
                subprocess.run(["open", "-R", str(path)], check=False)
            else:
                # Linux: 尝试打开父目录
                subprocess.run(["xdg-open", str(path.parent)], check=False)
            return {"ok": True}
        except Exception as exc:
            return {"ok": False, "error": f"无法定位文件: {exc}"}

    def _resolve_path(self, resource_id: int) -> Path | None:
        # 占位：实际调用成员二的仓储层
        ...
