# 桌面容器说明

## 职责

用 PyWebView 创建原生窗口，启动本地 FastAPI 服务，并向前端暴露受限的系统能力。

负责人：成员八，成员二和成员六参与桥接联调。

## 启动顺序

1. 在主线程读取配置和日志目录。
2. 在后台线程启动 Uvicorn，绑定 `127.0.0.1`。
3. 轮询 `GET /api/health`，通过后创建窗口。
4. 窗口加载前端页面。
5. 关闭窗口时通知 Uvicorn 停止，等待线程结束。

任何一步失败都要给出可读错误，不能留下无窗口的后台进程。

## 开发与发布

| 模式 | 加载地址 |
|---|---|
| 开发 | `http://127.0.0.1:5173`，由 Vite 提供热更新 |
| 发布 | `http://127.0.0.1:8000`，由 FastAPI 托管 `frontend/dist` |

## JS 桥接口

| 方法 | 参数 | 返回 | 说明 |
|---|---|---|---|
| `pick_files` | 无 | `list[str]` | 打开系统文件选择器 |
| `pick_folder` | 无 | `str \| null` | 选择文件夹 |
| `pick_package` | 无 | `str \| null` | 选择一个 `.hbox` 文件 |
| `choose_save_path` | `default_name: str` | `str \| null` | 保存对话框 |
| `open_resource` | `resource_id: int` | `void` | 后端查路径后打开 |
| `reveal_resource` | `resource_id: int` | `void` | 在资源管理器中定位 |
| `get_app_info` | 无 | `{version, platform}` | 版本与平台 |
| `move_to_recycle_bin` | `resource_ids: list[int]` | `object` | Beta 阶段，Alpha 不开放 |

## 安全规则

- 桥接方法只接收业务 ID，不接收任意路径。
- `open_resource` 必须由后端查询数据库得到路径。
- 不允许把前端字符串拼进系统命令。
- 打开 `.exe` 等可执行文件时，必须由用户显式点击确认。
- 所有异常转换为结构化错误返回给前端。

## 打包

- 使用 PyInstaller 生成 Windows 可执行文件。
- 目标机器需要 WebView2 Runtime；安装包中说明检测与安装方式。
- 用户数据写入 `data/` 或系统应用数据目录，不写入安装目录。
- 发布前在至少三台干净 Windows 电脑验证安装、启动、导入、卸载。
