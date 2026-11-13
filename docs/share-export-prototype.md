# 分享包导出原型

| 项目 | 内容 |
|---|---|
| 负责人 | 成员五：分享包 |
| 状态 | 待评审的原型，依赖分享包格式草案 |
| 更新日期 | 2026-11-12 |

## 已实现

- 通过 `ShareExportRepository` 只读正式条目、资源、标签与评分。
- `export_share_package` 接收选中条目 ID、稳定来源资料库 UUID 和应用版本，返回 `.hbox` 的 ZIP 字节；调用方负责保存。
- 只写入 UTF-8 `manifest.json`。现有文件重新计算 SHA-256；缺失文件保留元数据并标为 `missing`。不会读取设置或导出原始媒体、资源和封面的本地路径字段、标签分类及颜色。
- 按草案 Schema 校验结果，并检查条目选择、资源文件名、普通文件、生成过程中文件变化和元数据大小。
- 保留条目 `share_id`，每次生成新 `package_id` 和包内标签 `tag_ref`；同一包中同一本地标签复用同一个 `tag_ref`。

## 调用方式

```python
from app.application.share_export import export_share_package
from app.db.share_export_repository import ShareExportRepository

# session 由调用方创建并在结束时关闭；library_id 为调用方提供的稳定 UUID。
package_bytes = export_share_package(ShareExportRepository(session), [1, 2], library_id)
```

原型不创建文件或接收前端传来的保存路径；错误抛出 `ShareExportError`，由后续调用方转换为用户提示。

## 尚未完成

- `source_library_id` 的持久化方案尚未确认，调用方必须提供已有的稳定 UUID；不应每次生成随机库标识。
- 暂未接入 FastAPI、桌面保存对话框及前端；安装包中 Schema 文件的携带方式也需由成员八确认。
- 条目标题、描述、评价和标签名来自用户输入，可能由用户自行写入路径、密钥等敏感内容；导出预览及必要的提示或过滤规则仍需设计，不能声称已自动识别所有敏感文本。
- 目前仅支持完整正式条目、全部关联标签、`original` 评价模式；部分资源、标签重选、`new` / `both` 评价模式、临时条目和保存/清理流程需联调。
- 暂不打包封面，所有导出条目的 `cover` 为 `null`；正式行为需评审。
- 导入、预览、跨设备匹配、冲突处理与事务回滚尚未实现。数据库并发修改下的一致性快照仍需联调验证。

## 校验

在仓库根目录安装 `backend/requirements.txt` 后运行：

```text
python -m pytest tests/application/test_share_export.py -q
```

测试使用临时数据库和文件，不修改用户资料库或原始媒体。
