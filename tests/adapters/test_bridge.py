from contextlib import nullcontext
from pathlib import Path
from unittest.mock import Mock

import pytest

from app.adapters.bridge import NativeBridge
from app.application.errors import (
    ResourceFileMissingError,
    ResourceNotFoundError,
    ResourceOpenFailedError,
)
from app.application.resource_service import ResourceService


@pytest.fixture
def wired_bridge(tmp_path):
    opener = Mock()
    service = ResourceService(Mock(), Mock(), opener=opener)
    service.resolve_path = Mock(return_value=tmp_path / "document.txt")
    window = Mock()
    bridge = NativeBridge(lambda: nullcontext(service))
    bridge._bind_window(window)
    return bridge, service, window, opener


def test_open_normal_resource(wired_bridge):
    bridge, service, window, opener = wired_bridge
    assert bridge.open_resource(1) == {"ok": True}
    service.resolve_path.assert_called_once_with(1)
    opener.open.assert_called_once_with(service.resolve_path.return_value)
    window.create_confirmation_dialog.assert_not_called()


@pytest.mark.parametrize("resource_id", [True, 0, -1, 2**63, "1", "C:/file.txt", 1.0])
def test_invalid_id_never_reaches_service(wired_bridge, resource_id):
    bridge, service, _, opener = wired_bridge
    assert bridge.open_resource(resource_id)["error"] == "RESOURCE_ID_INVALID"
    service.resolve_path.assert_not_called()
    opener.open.assert_not_called()


@pytest.mark.parametrize("extension", [".EXE", ".bat", ".cmd", ".lnk"])
@pytest.mark.parametrize("confirmed", [True, False])
def test_executables_only_open_after_native_confirmation(wired_bridge, extension, confirmed):
    bridge, service, window, opener = wired_bridge
    path = Path("C:/fixture") / f"sample{extension}"
    service.resolve_path.return_value = path
    window.create_confirmation_dialog.return_value = confirmed

    if confirmed:
        opener.open.side_effect = lambda _: window.create_confirmation_dialog.assert_called_once()

    assert bridge.open_resource(1) == {"ok": True}
    window.create_confirmation_dialog.assert_called_once()
    service.resolve_path.assert_called_once_with(1)
    if confirmed:
        opener.open.assert_called_once_with(path)
    else:
        opener.open.assert_not_called()


@pytest.mark.parametrize(
    ("exception", "code"),
    [
        (ResourceNotFoundError, "RESOURCE_NOT_FOUND"),
        (ResourceFileMissingError, "RESOURCE_FILE_MISSING"),
        (ResourceOpenFailedError, "RESOURCE_OPEN_FAILED"),
    ],
)
def test_native_errors_return_stable_codes_and_hide_paths(wired_bridge, exception, code):
    bridge, service, _, opener = wired_bridge
    service.resolve_path.side_effect = exception("C:/private/file")
    result = bridge.open_resource(1)
    assert result["ok"] is False
    assert result["error"] == code
    assert "C:/private" not in result["message"]
    opener.open.assert_not_called()
