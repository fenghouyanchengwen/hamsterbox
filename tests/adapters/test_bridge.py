import pytest
from pathlib import Path
from unittest.mock import MagicMock

from app.adapters.bridge import NativeBridge


# ==========================================
# Mock 成员二的 ResourceService
# ==========================================
@pytest.fixture
def mock_resource_service():
    """创建一个假的 ResourceService 用于测试"""
    service = MagicMock()
    # 默认让 resolve_path 返回一个普通文本文件路径
    service.resolve_path.return_value = Path("C:/dummy/document.txt")
    return service


@pytest.fixture
def bridge(mock_resource_service):
    """注入假服务的 Bridge 实例"""
    return NativeBridge(window=None, resource_service=mock_resource_service)


# ==========================================
# 测试 open_resource 安全拦截
# ==========================================
def test_open_normal_file_success(bridge, mock_resource_service):
    """测试打开普通文件：放行并调用 service.open_resource"""
    res = bridge.open_resource(1)

    assert res["ok"] is True
    # 验证确实调用了成员二的 resolve_path 和 open_resource
    mock_resource_service.resolve_path.assert_called_once_with(1)
    mock_resource_service.open_resource.assert_called_once_with(1)


def test_open_executable_requires_confirmation(bridge, mock_resource_service):
    """测试拦截可执行文件：传入 .exe，应拒绝打开并返回确认错误码"""
    # 篡改 Mock 的返回值，让其返回 .exe 路径
    mock_resource_service.resolve_path.return_value = Path("C:/dummy/hack.exe")

    res = bridge.open_resource(1)  # 默认 user_confirmed=False

    assert res["ok"] is False
    assert res["error"] == "EXECUTABLE_CONFIRM_REQUIRED"
    # 确保没有调用 service 的打开方法
    mock_resource_service.open_resource.assert_not_called()


def test_open_executable_confirmed(bridge, mock_resource_service):
    """测试二次确认后打开可执行文件：传入 True，应放行"""
    mock_resource_service.resolve_path.return_value = Path("C:/dummy/game.exe")

    res = bridge.open_resource(1, user_confirmed=True)  # 用户确认

    assert res["ok"] is True
    mock_resource_service.open_resource.assert_called_once_with(1)


def test_open_resource_service_error(bridge, mock_resource_service):
    """测试成员二服务抛出异常的情况（如资源不存在）"""
    # 模拟 resolve_path 抛出异常
    mock_resource_service.resolve_path.side_effect = Exception("资源不存在")

    res = bridge.open_resource(1)

    assert res["ok"] is False
    assert res["error"] == "FILE_NOT_FOUND"
    assert "资源不存在" in res["message"]
