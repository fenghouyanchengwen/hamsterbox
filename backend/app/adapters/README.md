# 适配器说明

## 职责

把不同文件类型的识别、元数据读取和系统能力封装成统一接口，供应用服务调用。

负责人：成员七。

## 文件适配器接口

```python
class FileAdapter(Protocol):
    extensions: tuple[str, ...]

    def detect_type(self, path: Path) -> EntryType: ...
    def read_metadata(self, path: Path) -> dict[str, object]: ...
    def supports_preview(self) -> bool: ...
```

## 类型注册表

```python
class TypeRegistry:
    def register(self, adapter: FileAdapter) -> None: ...
    def for_extension(self, extension: str) -> FileAdapter | None: ...
    def detect(self, path: Path) -> EntryType: ...
```

| 扩展名 | 类型 |
|---|---|
| `.epub`、`.pdf`、`.mobi` | book |
| `.png`、`.jpg`、`.jpeg`、`.webp` | image |
| `.mp4`、`.mkv`、`.avi` | video |
| `.mp3`、`.flac`、`.wav` | audio |
| `.exe`、`.lnk` | 由游戏适配器处理 |
| `.glb`、`.gltf`、`.obj` | model |
| 其他 | other |

## 内置适配器

Alpha 阶段提供三个：

- 图片适配器：读取宽高与文件大小。
- 视频适配器：读取容器信息，暂不生成缩略图。
- 电子书适配器：读取书名、作者等基础元数据。

## 系统能力

系统能力由 PyWebView 的 JS 桥提供，后端不直接调用系统命令。

| 能力 | 入口 | 使用方 |
|---|---|---|
| 选择文件 | `pick_files()` | 前端 |
| 选择文件夹 | `pick_folder()` | 前端 |
| 选择分享包 | `pick_package()` | 前端 |
| 选择保存位置 | `choose_save_path()` | 前端 |
| 打开资源 | `open_resource(resource_id)` | 前端调用，后端解析路径 |
| 定位资源 | `reveal_resource(resource_id)` | 前端调用，后端解析路径 |

## 安全规则

- 桥接方法不接收任意路径，只接收 `resource_id`。
- 不使用 `shell=True` 拼接命令。
- 打开可执行文件前必须由用户显式操作。
- 删除到回收站属于 Beta 能力，Alpha 只移出库。
