# 成员2：条目与资源协作与交付说明

| 项目 | 内容 |
| --- | --- |
| 负责人 | 成员2：条目与资源 |
| 最后更新 | 2026-11-27 |
| 关联 Issue | #27（跨成员协调）、#32（适配器接入）、Beta 第一阶段安全删除（B1-A01 ~ B1-A03） |
| 配套契约 | `docs/api/entries-resources.md`、`docs/tag-rating-contract.md` |

## 1. 本轮已完成修复与新增能力

### 1.1 条目评价、生命周期与隐私时间对齐（Issue #27 / ALPHA-03 / ALPHA-06 / B9）

- `EntryCreate`、`EntryUpdate`、`EntryRead` 与 `SqliteEntryRepository` 已完整接入 `review`（最多 10000 字符，超长返回 `422 ENTRY_REVIEW_TOO_LONG`）和 `lifecycle_state`（`library` / `temporary`）。
- 普通 HTTP `POST /api/entries` 固定创建 `lifecycle_state="library"`。
- 为成员5“部分资源分享”提供应用层内部方法：
  - `EntryService.create_temporary_entry(payload, source_resource_ids=...)`
  - `EntryService.promote_temporary_entry(entry_id, review=...)`
  - `EntryService.discard_temporary_entry(entry_id)`（严禁误删 `library` 条目）
- `EntryRead` / `EntryDetail` 移除原始本地路径 `cover_path`，改为返回布尔 `has_cover`，消除详情接口本地目录结构泄露；写入 `cover_path` 时统一执行绝对路径、存在性与普通文件校验。
- `EntryRead` 时间字段（`created_at`、`updated_at`）统一标准化为 UTC aware 时间，序列化输出带 `Z` 后缀，修复浏览器按本地时间解析偏移 8 小时的问题。
- 修复 `PATCH /api/entries/{entry_id}` 两个边界缺陷：拒绝空请求体 `{}`（返回 `422`），拒绝将 `title` 或 `type` 显式置为 `null`（返回 `422`，不再触发数据库 `500 IntegrityError`）。

### 1.2 文件类型自动识别接入（Issue #32）

- `ResourceService` 新增可选 `type_detector`（默认在 `dependencies.py` 注入 `TypeRegistry`）。
- 关联资源时安全调用 `detect(path)`（异常降级为 `other`，绝不阻断关联流程）。
- 遵循 `docs/tag-rating-contract.md` §4 第 2 条边界：**仅当条目当前类型为 `other` 且识别出具体媒体类型时自动更新 `entry.type`**，不会在用户为“游戏/影视”条目挂载附加说明文档或封面图片时篡改原有作品类型。

### 1.3 Beta 第一阶段安全删除与共享引用检测（B1-A01 ~ B1-A03）

- 新增 `SystemRecycleBin`（`backend/app/adapters/recycle_bin.py`）：Windows 下通过标准库 `ctypes` 调用 `SHFileOperationW`（`FOF_ALLOWUNDO`）将文件移入系统回收站，支持在系统回收站原路径无损还原（保持 SHA-256 一致），不提供任何永久删除回退。
- 新增 `POST /api/resources/delete/preview`：按勾选 `resource_ids` 返回跨条目共享引用状态（`shared`、`has_shared_files` 及受影响的 `entry_id` / `entry_title` / `resource_id` 列表），供前端在二次确认弹窗展示共享提示与跳转定位。
- 新增 `POST /api/resources/delete`：强制要求 `confirmed=true`（否则 `400 RESOURCE_DELETE_CONFIRM_REQUIRED`）；当存在跨条目共享引用且 `acknowledge_shared=false` 时返回 `409 RESOURCE_SHARED_CONFIRM_REQUIRED` 并携带受影响条目详情；确认后仅移入勾选资源对应的物理文件并清理对应数据库关联，未勾选资源及其原文件保持不变。

## 2. 下游成员联调提示

- **成员5（分享包）**：部分资源分享可直接调用 `EntryService` 的 `create_temporary_entry` / `promote_temporary_entry` / `discard_temporary_entry`，临时条目默认被检索仓储排除在普通列表之外。
- **成员6（界面与交互）**：
  - 详情页可直接通过 `PATCH /api/entries/{entry_id}` 读写 `review`（T6-06 已解除阻塞）；响应中的 `cover_path` 已替换为 `has_cover: boolean`。
  - 删除资源文件弹窗可先调 `POST /api/resources/delete/preview` 检查 `has_shared_files` 与 `affected_entries`，用户确认后调 `POST /api/resources/delete`（传 `confirmed: true` 及 `acknowledge_shared`）。
- **成员7（扩展与适配）**：`dependencies.py` 优先调用 `build_registry()`；待 PR #53 合入后将自动包含动态加载的外部插件识别能力。
- **成员8（质量与发布）**：`B1-A01`、`B1-A02`、`B1-A03` 后端接口与回收站能力已就绪，可在桌面端联调后执行手工回收站还原验证。
