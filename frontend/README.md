# 前端模块说明

## 职责

使用 Vue 3 + TypeScript + Vite 实现侧栏、列表、详情、标签评分、导入预览和设置页面。前端不直接访问 SQLite，也不直接操作文件系统。

负责人：成员六，成员四负责检索与列表数据，成员二至五提供接口。

## 目录建议

```
src/
  main.ts
  App.vue
  api/client.ts           HTTP 封装
  bridge/index.ts         PyWebView JS 桥封装
  types/api.ts            与后端契约对应的类型
  views/
    LibraryView.vue
    EntryDetailView.vue
    ImportPreviewView.vue
    SettingsView.vue
  components/
    EntryCard.vue
    TagChip.vue
    RatingStars.vue
    FilterBar.vue
    EmptyState.vue
    ErrorBanner.vue
```

## 页面与接口对应

| 页面或操作 | 调用 |
|---|---|
| 应用启动检查 | `GET /api/health` |
| 库列表 | `GET /api/entries` |
| 新建条目 | `POST /api/entries` |
| 编辑条目 | `PATCH /api/entries/{entry_id}` |
| 移出库 | `DELETE /api/entries/{entry_id}` |
| 添加本地文件 | `bridge.pick_files()` → `POST /api/entries/{entry_id}/resources` |
| 打开文件 | `bridge.open_resource(resource_id)` |
| 标签列表 | `GET /api/tags` |
| 新建或编辑标签 | `POST /api/tags`、`PATCH /api/tags/{tag_id}` |
| 评分 | `PUT /api/entries/{entry_id}/ratings/{tag_id}` |
| 筛选与检索 | `GET /api/entries` 的查询参数 |
| 导出分享包 | `POST /api/share/export` |
| 预览导入 | `bridge.pick_package()` → `POST /api/share/preview` |

## 状态设计

每个列表和详情页面必须覆盖四种状态：

| 状态 | 展示 |
|---|---|
| 加载中 | 骨架屏或加载提示 |
| 空数据 | 说明下一步操作的引导 |
| 错误 | 错误码与可执行的重试操作 |
| 部分失效 | 标记缺失资源，允许重新定位 |

## 交互约定

- 删除条目只移出库，界面必须写清"不会删除磁盘文件"。
- 评分控件在 `rating_enabled=false` 时禁用。
- 标签重名时展示 409 提示，不静默失败。
- 分享包导入必须先预览，再确认写入。

## 与后端的边界

- 业务数据只走 HTTP/JSON。
- 文件选择、打开、定位和保存对话框只走 JS 桥。
- 前端不拼接本地绝对路径，不在 URL 中传递路径。
- 所有请求集中在 `api/client.ts`，组件不直接写 `fetch`。
