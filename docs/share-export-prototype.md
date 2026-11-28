# 分享包导出接口

| 项目 | 内容 |
|---|---|
| 负责人 | 成员五 |
| 关联 Issue | #3 |
| 更新日期 | 2026-11-19 |

导出以分享包 v1 草案为基础。接口接受一个或多个正式条目的本地 ID，生成仅包含元数据的 `.hbox` 文件。

| 方法与路径 | 请求 | 成功响应 |
|---|---|---|
| `POST /api/share/export/preview` | `{"entry_ids":[1,2]}` | `200`，JSON 中的 `entries` 包含将要分享的元数据。 |
| `POST /api/share/export` | `{"entry_ids":[1,2]}` | `200`，ZIP 字节，`Content-Disposition` 提供默认文件名。 |

最多选择 200 个条目。无效请求结构返回 `422 VALIDATION_ERROR`。重复选择、非正式条目、资源无法读取和超出格式大小限制返回 `422 SHARE_EXPORT_INVALID`。导出前预览不写资料库。实际导出首次使用当前库的 `share.source_library_id`，并以 SQLite 原子插入保留稳定值。重复导出时此 UUID 保持不变，包 UUID 和标签引用重新生成。

元数据包含完整正式条目、原评价、全部关联标签和可选评分。使用新计算的 SHA-256 导出现有资源，缺失文件携带已有的摘要和大小（如有）。封面字段为空。生成的 ZIP 只有 `manifest.json`，其标准字段不含本机资源路径、分类、颜色、全局设置和原始媒体。PyInstaller 可通过 Python 模块直接加载 Schema，测试对照公开的 JSON 文件。

前端应在保存前展示标题、简介、评价、标签与文件名，并提示用户检查自行输入的敏感内容。客户端决定保存位置并处理取消或写入错误，后端端点不接受保存路径。成员六联调时以此处的二进制响应为准。封面、部分资源选择、临时条目和自定义评价仍需评审相关接口。

## 本地验证

以临时资料库启动后端，先创建一个正式条目。以下示例中条目 ID 为 1。

```sh
curl --fail-with-body http://127.0.0.1:8000/api/share/export/preview \
  -H 'Content-Type: application/json' -d '{"entry_ids":[1]}'
curl --fail http://127.0.0.1:8000/api/share/export \
  -H 'Content-Type: application/json' -d '{"entry_ids":[1]}' -o hamsterbox.hbox
python -m zipfile -l hamsterbox.hbox
python -m pytest -q tests/api/test_share_export_api.py tests/application/test_share_export.py tests/application/test_share_schema.py
```
