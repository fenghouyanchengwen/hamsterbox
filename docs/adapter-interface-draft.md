# Adapter 接口草案 v1

- **用途**：定义文件类型识别、元数据读取和系统能力声明的统一契约，供应用服务层与前端调用。
- **负责人**：成员七
- **最后更新**：2026-11-01
- **状态**：Alpha 第一阶段冻结，变更须走 Issue 并通知全员。

## 1. 职责边界
- **适配器负责**：按扩展名识别文件类型、读取轻量基础元数据、声明自身能力。
- **适配器不负责**：移动/删除原始文件、直接执行系统命令、前端图标布局。
- **安全红线**：系统打开、文件选择、目录定位由受控原生能力层（JS桥）执行，只接收 `resource_id`，绝不接收任意路径。

## 2. 核心类型定义
#对应代码：`backend/app/adapters/enums.py`

| type_id | 含义 | 前端图标 key | Alpha 阶段支持 |
| :--- | :--- | :--- | :--- |
| `book` | 电子书 | `icon_book` | 是 (基础) |
| `image` | 图片 | `icon_image` | 是 (基础) |
| `video` | 视频 | `icon_video` | 是 (基础) |
| `audio` | 音频 | `icon_audio` | 是 (基础) |
| `text` | 文本 | `icon_text` | 是 (基础) |
| `game` | 游戏/可执行 | `icon_game` | 否 (占位) |
| `model` | 3D 模型 | `icon_model` | 否 (占位) |
| `other` | 未知/兜底 | `icon_other` | 是 (兜底) |

### 2.2 扩展名映射表
| 扩展名 | type_id | 归属适配器 |
| :--- | :--- | :--- |
| `.epub`, `.pdf`, `.mobi` | `book` | `EbookAdapter` |
| `.png`, `.jpg`, `.jpeg`, `.webp` | `image` | `ImageAdapter` |
| `.mp4`, `.mkv`, `.avi` | `video` | `VideoAdapter` |
| `.mp3`, `.flac`, `.wav` | `audio` | `AudioAdapter` |
| `.txt`, `.md`, `.log` | `text` | `TextAdapter` |
| `.exe`, `.lnk` | `game` | `FallbackAdapter` (Alpha 占位) |
| `.glb`, `.gltf`, `.obj` | `model` | `FallbackAdapter` (Alpha 占位) |
| *(未知或无后缀)* | `other` | `FallbackAdapter` |

### 2.3 FileAdapter（适配器接口）
```python
class FileAdapter(Protocol):
    extensions: tuple[str, ...]

    def detect_type(self, path: Path) -> EntryType: ...
    def read_metadata(self, path: Path) -> dict[str, object]: ...
    def supports_preview(self) -> bool: ...
```
---

## 3. 接口规范

### 3.1 适配器接口协议 (FileAdapter)
对应代码：`backend/app/adapters/interface.py`

采用 Python 的 `typing.Protocol` 实现结构化子类型。任何实现了以下成员的对象即视为合法的适配器，无需显式继承。

```python
from pathlib import Path
from typing import Protocol
from .enums import EntryType

class FileAdapter(Protocol):
    extensions: tuple[str, ...]
    """该适配器支持的扩展名元组，统一小写且带点，如 ('.jpg', '.png')"""

    def detect_type(self, path: Path) -> EntryType:
        """
        识别文件类型。
        :param path: 文件的完整路径。
        :return: 稳定的 EntryType 枚举，未知类型必须返回 EntryType.OTHER。
        """
        ...

    def read_metadata(self, path: Path) -> dict[str, object]:
        """
        读取基础元数据（轻量级，不深入解析文件流）。
        :param path: 文件的完整路径。
        :return: 包含元数据的字典，若读取失败应返回空字典或仅含 file_size，不抛异常。
        """
        ...

    def supports_preview(self) -> bool:
        """声明该类型的文件是否支持内嵌预览。Alpha 阶段均暂不生成实际预览。"""
        ...
```
### 3.2 类型注册表 (TypeRegistry)
对应代码：backend/app/adapters/registry.py

负责“扩展名”到“适配器”的路由分发，在应用启动时初始化。

```python
class TypeRegistry:
    def register(self, adapter: FileAdapter) -> None: ...
    def for_extension(self, extension: str) -> FileAdapter | None: ...
    def detect(self, path: Path) -> EntryType: ...
    def adapters(self) -> tuple[FileAdapter, ...]: ...
    def supported_extensions(self) -> tuple[str, ...]: ...
```
注册表核心规则：

归一化：注册与查询时，自动对扩展名执行 lower().lstrip(".") 处理。

原子注册：若一个适配器声明了多个扩展名，其中任意一个发生冲突，则整个适配器注册失败（回滚），避免半注册脏数据。

未知兜底：对于没有适配器接管的扩展名或无后缀文件，detect() 必须稳定返回 EntryType.OTHER，绝不可抛出异常导致导入失败。


## 4.JS 桥接安全规则
### 4.1 暴露给前端的入口

| 方法名                   | 参数                                          | 返回值                         | 说明                   |
|:----------------------|:--------------------------------------------|:----------------------------|:---------------------|
| `pick_files()`        | 无                                           | `list[str]`                 | 弹出文件选择框，返回选中的绝对路径列表。 |
| `pick_folder()`       | 无                                           | `str/ None`                 | 弹出文件夹选择框。               |
| `pick_package()`      | 无                                           | `str / None`                | 选择分享包，强制过滤 .zip 格式               |
| `choose_save_path()	` | 无                                           | `str / None`                | 弹出“另存为”对话框。               |
| `open_resource()`     | resource_id: int/user_confirmed: bool=False | `dict`                      | 打开文件。后端根据 ID 查路径。             |
| `reveal_resource()`   | resource_id: int                            | `dict`                      | 在系统资源管理器中定位并选中文件。               |

### 4.2 安全规则强制落实
禁止路径注入：桥接方法接收的参数只能是业务主键 resource_id。后端必须通过仓储层查出真实路径，严禁前端直接传路径执行。

可执行文件拦截：

  当 open_resource 检测到后缀为 .exe, .bat, .cmd, .lnk 等可执行文件时，且 user_confirmed=False，必须拦截。

  返回 {"ok": false, "error": "EXECUTABLE_CONFIRM_REQUIRED"}。

  前端弹出警告框，用户点击确认后，传入 user_confirmed=True 再次调用方可执行。

命令注入防护：

  在实现“定位资源 (reveal_resource)”或调用其他外部程序时，绝对禁止使用 os.system() 或 subprocess.run(..., shell=True)。

  必须采用列表传参形式：subprocess.run(["explorer", "/select,", str(path)], check=False)。

## 5. 错误模型与异常处理
所有桥接方法均返回统一的结构，便于前端做统一的 UI 提示：
```python
json
{
    "ok": true, 
    "data": {}
}
```
或
```python
json
{
    "ok": false, 
    "error_code": "ERROR_CODE_STRING", 
    "message": "人类可读的错误提示"
}
```


| 错误码 (error_code)           | 触发场景                                          | 前端处理建议                         |
|:---------------------------|:--------------------------------------------|:----------------------------|
| `FILE_NOT_FOUND`           | 文件已被移动或删除，path.exists() 为 False                                           | `Toast 提示“文件已失效，请重新关联”。`                 |
| `EXECUTABLE_CONFIRM_REQUIRED`              | 用户尝试打开可执行文件                                           | `弹出安全警告弹窗，用户确认后带 True 参数重试。`                 |
| `OPEN_FAILED`             | 系统找不到默认程序或权限不足	                                           | `Toast 提示具体错误信息。`                |
| `INVALID_ARGUMENT	`        | 缺少必要的参数或参数格式错误                                           | `Toast 提示“参数错误”。`                |

## 6. 交接与协作备忘
### 对成员二：

请在资源关联时调用 registry.detect(path) 获取类型；请提供 _resolve_path 所需的仓储层查询接口。

### 对成员六：
请根据 EntryType 对应的 icon_key 渲染列表和详情页；请处理 EXECUTABLE_CONFIRM_REQUIRED 的弹窗逻辑。
