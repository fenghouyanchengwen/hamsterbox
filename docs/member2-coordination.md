# 成员2：条目与资源协作清单

本文记录成员2在 `feature/entry-resource` 分支上的完成情况、跨成员协调事项和后续实现顺序。它与条目资源接口契约配套使用，不能替代接口契约。

## 当前职责边界

成员2负责：

- 条目创建、详情、编辑和移出库。
- 本地文件资源的关联、列表、解除关联和状态重新检测。
- 资源文件元数据和 SHA-256 计算。
- 根据 `resource_id` 解析路径，并调用受控的系统默认程序打开资源。
- 条目与资源相关的应用服务、HTTP 路由、仓储协作和测试。

成员2不负责：

- `GET /api/entries` 的搜索、筛选、排序和分页。
- 标签、评分和分享包业务。
- PyWebView 窗口生命周期和完整桌面桥实现。
- Alpha 阶段的跨条目资源共享提示和安全删除。

## 已完成

以下能力已经在本分支完成并提交到此前的提交中：

- 条目领域模型、条目 CRUD 应用服务和 SQLite 仓储。
- `POST /api/entries`、`GET /api/entries/{entry_id}`、`PATCH` 和 `DELETE`。
- 资源关联、资源列表、解除关联和重新检测接口。
- 资源路径必须为绝对路径，资源响应不泄露本地绝对路径。
- 资源关联时读取文件名、扩展名、大小、修改时间和 SHA-256。
- 文件缺失、目录路径、重复关联和访问失败的错误映射。
- `share_id` 持久化在条目和资源记录中；SQLite `id` 不进入分享包。


## 必须协调的事项

### 成员1：数据与存储

- 确认 `resources.entry_id` 的外键行为和条目删除时的级联策略。
- 条目移出库必须删除数据库中的条目和关联记录，但不能删除、移动或重命名原始文件。
- 将当前 ORM 临时建表实现迁移到 Alembic 后，保持字段名称和空值语义兼容：`path`、`file_name`、`extension`、`size_bytes`、`mtime_ns`、`sha256`、`availability`。
- 确认 `share_id` 的唯一约束、生成时机和导入时保留外部值的规则。
- 成员1完成迁移后，成员2需要补一次 SQLite 仓储和级联删除回归测试。

### 成员4：检索与展示

- 成员4实现 `GET /api/entries` 的列表、搜索、筛选、排序和分页；成员2不在本分支重复实现。
- 确认列表响应与 `EntryDetail` 的边界：详情包含资源，列表不默认展开资源路径。
- 确认成员4不会改变条目类型的英文稳定值：`game`、`book`、`video`、`audio`、`image`、`model`、`other`。
- 合并前一起运行条目详情、资源列表和检索接口测试，检查路由参数没有冲突。

### 成员5：分享包

- 分享包只携带 `share_id` 和资源元数据，不携带本机 SQLite `entry_id`。
- 导入模型需要保留外部 `share_id`，由本地数据库重新生成 `entry_id`。
- 分享包中资源路径应按分享包规范处理，不能把另一台设备的绝对路径直接当作本机可用路径。
- 成员5确定 schema 后，成员2检查条目、资源字段和英文枚举是否一致。

### 成员6：界面与交互

- 前端关联资源时调用 `POST /api/entries/{entry_id}/resources`，展示 `file_name`、大小、扩展名和 `availability`。
- 前端打开资源时只调用 `window.pywebview.api.open_resource(resource_id)`，不能把路径传给桥或浏览器端代码。
- 资源缺失时显示“重新检测”和可读错误；解除关联后不要提示删除原文件。
- 前端不要依赖错误消息文本分支，应使用稳定错误码。

### 成员7：扩展与适配

- 评审 `SystemDefaultOpener` 与适配器目录的职责是否一致。
- 后续文件类型识别适配器应作为资源关联流程的独立能力，不把媒体解析逻辑写入资源仓储。
- 系统打开能力必须继续遵守：不使用 `shell=True`，不接收任意路径，不绕过资源 ID 校验。

### 成员8：质量与发布

- 在桌面桥中调用 `ResourceService.open_resource(resource_id)`，不要复制路径查询和文件校验逻辑。
- 桥接方法只接受整数 `resource_id`，并把 `ResourceNotFoundError`、`ResourceFileMissingError`、`ResourceOpenFailedError` 转换为结构化错误。
- 增加假桥测试，验证前端不能传入任意本地路径。
- 在 Windows 发布验证中确认 `.txt`、音频、视频和 `.exe` 都交给系统默认程序处理；打开 `.exe` 必须来自用户显式操作。
- pytest 临时目录和 SQLAlchemy 导入环境修复后，运行成员2全量测试并记录结果。

## 后续实现顺序


### 1. 完成桌面桥联调

等待成员8提供桥接入口后，验证以下链路：

```text
前端 resource_id
  -> PyWebView open_resource(resource_id)
  -> ResourceService.open_resource(resource_id)
  -> ResourceService.resolve_path(resource_id)
  -> SystemDefaultOpener
```

### 2. 对齐数据库迁移

成员1完成 Alembic 迁移后，补充外键、级联删除、唯一约束和已有资源数据兼容测试。

### 3. 完成跨模块回归

成员4、5、6、8的接口和桥接合并后，回归条目详情、资源状态、分享导入后的资源记录和桌面打开流程。

### 4. Alpha 之后再做的内容

- 同一磁盘文件被多个条目引用时的提示和共享模型。
- 资源移入回收站或安全删除。
- 更丰富的媒体元数据和缩略图。
- 批量资源检测和后台任务调度。

## 验收标准

- 资源接口不会向前端返回本地绝对路径。
- 资源打开只接受 `resource_id`，路径始终由后端查询。
- 文件被删除后，打开操作返回 `RESOURCE_FILE_MISSING`。
- 目录不能作为可打开资源。
- 系统默认程序启动失败时返回 `RESOURCE_OPEN_FAILED`。
- 解除关联和移出库不会修改磁盘上的原始文件。
- 成员1迁移、成员8桥接和成员6界面合并后，端到端链路仍满足以上规则。

