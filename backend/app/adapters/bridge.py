from pathlib import Path
import webview
import sys
import subprocess
import os

# alpha2
# 引入成员二的接口和异常类
#from app.application.resource_service import ResourceService
#由于上面这一行报错，且调试后暂时无法解决，暂时改为相对导入，使用如下这行代码
from ..application.resource_service import ResourceService
from ..application.errors import ResourceNotFoundError, ResourceFileMissingError, ResourceOpenFailedError

class NativeBridge:
    def __init__(self, window=None, resource_service: ResourceService | None = None):
        self._window = window
        #alpha2
        self._resource_service = resource_service
        # ResourceService内部已经包含了opener，不需要再实例化SystemDefaultOpener
        #self._opener = SystemDefaultOpener()

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

    def open_resource(self, resource_id: int,user_confirmed: bool = False) -> dict:
        """打开资源"""
        if not self._resource_service:
            return {"ok": False, "error": "SERVICE_UNAVAILABLE", "message": "资源服务未初始化"}

        try:
            # 1. 先通过成员二的 resolve_path 拿到真实路径（用于拦截检查）
            path = self._resource_service.resolve_path(resource_id)
        except Exception as exc:
            # 捕获如 ResourceNotFoundError, ResourceFileMissingError 等
            return {"ok": False, "error": "FILE_NOT_FOUND", "message": str(exc)}
        """
        以下为未修改前代码
        # 由后端根据 resource_id 查询真实路径
        path = self._resolve_path(resource_id)  # 成员二/数据层提供
        if path is None or not path.exists():
            return {"ok": False, "error": "资源不存在或文件已失效"}
        """
        #alpha2：添加and not user_confirmed，避免一次直接打开.exe等文件
        if path.suffix.lower() in (".exe", ".bat", ".cmd", ".lnk")and not user_confirmed:
            return {
                "ok": False,
                "error": "EXECUTABLE_CONFIRM_REQUIRED",
                "message": "出于安全考虑，运行可执行文件需要二次确认。"
            }
        try:
            #调用成员二的open_resource方法执行打开
            self._resource_service.open_resource(resource_id)
            return {"ok": True}
        except Exception as exc:
            # 捕获 ResourceOpenFailedError
            return {"ok": False, "error": "OPEN_FAILED", "message": str(exc)}
        """
        except SystemOpenError as exc:
            # 捕获对方定义的异常，返回统一错误结构
            return {"ok": False, "error": "OPEN_FAILED", "message": str(exc)}
        except Exception as exc:
            return {"ok": False, "error": "UNKNOWN_ERROR", "message": f"未知错误: {exc}"}
        #return self._safe_open_path(path)
        """

    """基于system_open.py，在alpha二阶段取消此函数，直接使用其中的方法
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
    """

    def reveal_resource(self, resource_id: int) -> dict:
        if not self._resource_service:
            return {"ok": False, "error": "SERVICE_UNAVAILABLE", "message": "资源服务未初始化"}

        try:
            # 【修改点】不再使用废弃的 _resolve_path，改为调用成员二的服务
            path = self._resource_service.resolve_path(resource_id)
        except Exception as exc:
            return {"ok": False, "error": "FILE_NOT_FOUND", "message": str(exc)}

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
