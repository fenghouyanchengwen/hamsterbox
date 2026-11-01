# 应用服务说明

应用服务层负责用例编排、业务校验和事务边界。路由只调用这一层，不直接操作数据库。

## 服务划分

| 服务 | 负责 | 负责人 |
|---|---|---|
| `entry_service` | 条目增删改查、资源关联与解除 | 成员二 |
| `resource_service` | 资源关联、文件元数据、失效检测与解除关联 | 成员二 |
| `tag_service` | 标签分类和标签增删改查、名称与本地颜色校验 | 成员三 |
| `rating_service` | 条目标签关联与可选 1 至 10 分评分 | 成员三 |
| `search_service` | 关键词、标签、评分区间与排序 | 成员四 |
| `share_service` | 导出、预览、哈希匹配与导入 | 成员五 |

## 方法签名

```python
class EntryService:
    def list_entries(self, query: EntryQuery) -> Page[EntryRead]: ...
    def create_entry(self, payload: EntryCreate) -> EntryRead: ...
    def get_entry(self, entry_id: int) -> EntryRead: ...
    def update_entry(self, entry_id: int, payload: EntryUpdate) -> EntryRead: ...
    def remove_entry(self, entry_id: int) -> None: ...
    def attach_resource(self, entry_id: int, path: str) -> ResourceRead: ...
    def detach_resource(self, entry_id: int, resource_id: int) -> None: ...

class ResourceService:
    def list_resources(self, entry_id: int) -> list[ResourceRead]: ...
    def attach_resource(self, entry_id: int, payload: ResourceCreate) -> ResourceRead: ...
    def detach_resource(self, entry_id: int, resource_id: int) -> None: ...
    def recheck_resource(self, resource_id: int) -> tuple[ResourceRead, bool]: ...

class TagService:
    def list_categories(self) -> list[TagCategoryRead]: ...
    def create_category(self, payload: TagCategoryCreate) -> TagCategoryRead: ...
    def update_category(self, category_id: int, payload: TagCategoryUpdate) -> TagCategoryRead: ...
    def delete_category(self, category_id: int) -> None: ...
    def list_tags(self, category_id: int | None = None) -> list[TagRead]: ...
    def create_tag(self, payload: TagCreate) -> TagRead: ...
    def update_tag(self, tag_id: int, payload: TagUpdate) -> TagRead: ...
    def delete_tag(self, tag_id: int) -> None: ...

class RatingService:
    def list_entry_tags(self, entry_id: int) -> list[EntryTagRead]: ...
    def upsert_entry_tag(self, entry_id: int, tag_id: int, payload: EntryTagUpsert) -> EntryTagRead: ...
    def remove_entry_tag(self, entry_id: int, tag_id: int) -> None: ...

class SearchService:
    def search(self, query: SearchQuery) -> Page[EntryRead]: ...

class ShareService:
    def export(self, payload: ShareExportRequest) -> ShareExportResult: ...
    def preview(self, package_path: str) -> SharePreview: ...
    def commit_import(self, preview_id: str, selection: list[str]) -> ImportResult: ...
```

## 事务规则

- 一个 HTTP 请求对应一个事务。
- 先完成全部校验，再执行写入。
- 分享包导入使用单事务，失败时整体回滚。
- 删除条目只删除条目、资源记录和标签关联，不操作磁盘文件。
- 删除标签时，如果还存在 `entry_tags` 引用，返回冲突错误。
- 删除非空分类、修改或删除系统“未分类标签”分类均返回冲突错误。
- 评分只能为空或 1 至 10 的整数；条目评价文字只在 Entry 上更新。

## 异常约定

应用服务抛出领域异常，由 API 层映射为 HTTP 状态：

| 异常 | HTTP 状态 |
|---|---|
| `NotFoundError` | 404 |
| `ConflictError` | 409 |
| `ValidationError` | 422 |
| `InvalidStateError` | 400 |

## 依赖注入

- 服务通过构造函数接收仓储接口。
- 测试时注入内存仓储，不依赖真实数据库。
- 服务层不得导入 FastAPI 的 `Request`、`HTTPException`。

## 打开资源

桌面桥只传入 `resource_id`，然后调用 `ResourceService.open_resource()`。服务先
通过资源仓储取出数据库中的路径，再确认路径存在且是普通文件，最后调用注入的
`ResourceOpener`。默认实现是 `SystemDefaultOpener`；测试和桌面集成可以注入假
实现，因此不会在测试中真的启动外部程序。

服务层不接受前端传入的任意路径，也不把本地绝对路径放入 HTTP 响应。
