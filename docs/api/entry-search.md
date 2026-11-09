# 条目检索查询契约 v1

| 项目 | 内容 |
|---|---|
| 用途 | 定义 `GET /api/entries` 的查询参数、筛选语义、排序白名单与分页响应 |
| 负责人 | 成员四：检索与展示 |
| 状态 | 已实现，待成员二确认字段归属 |
| 最后更新 | 2026-11-09 |
| 关联 Issue | #11 |

## 1. 范围

覆盖条目列表的关键词检索、类型筛选、标签筛选、评分区间、排序与分页。

不覆盖：条目写入（成员二）、标签与评分写入（成员三）、分享包内容（成员五）、前端渲染（成员六）。

## 2. 请求

```http
GET /api/entries?q=塞尔&tag_id=3&tag_id=5&tag_mode=and&sort=rating_desc&page=1&page_size=50
```

| 参数 | 类型 | 默认 | 取值 | 说明 |
|---|---|---|---|---|
| `q` | string | 空 | 最长 200 字符 | 标题或简介包含该片段 |
| `type` | string，可重复 | 空 | `game`、`book`、`video`、`audio`、`image`、`model`、`other` | 任一命中即可 |
| `tag_id` | int，可重复 | 空 | 标签 ID | 与 `tag_mode` 组合生效 |
| `tag_mode` | string | `and` | `and`、`or` | `and` 要求同时具备全部标签 |
| `rating_min` | int | 空 | 1 至 10 | 评分区间下界 |
| `rating_max` | int | 空 | 1 至 10 | 评分区间上界 |
| `sort` | string | `updated_desc` | 见第 3 节 | 排序方式 |
| `page` | int | 1 | ≥ 1 | 页码，从 1 开始 |
| `page_size` | int | 50 | 1 至 200 | 每页条数 |

## 3. 筛选与排序语义

**关键词**：`title LIKE %q%` 或 `description LIKE %q%`。用户输入中的 `%` 与 `_` 按字面字符处理，不作为通配符。ASCII 大小写不敏感。

**标签**：`and` 时对每个 `tag_id` 要求存在关联记录；`or` 时命中任一 `tag_id` 即可。

**评分区间**：存在某个已开启评分且分数落在区间内的标签。未评分（`rating` 为空）不参与匹配。`rating_min` 大于 `rating_max` 返回 `RATING_RANGE_INVALID`。

**库内状态**：只返回 `lifecycle_state = library` 的条目，分享导出的临时条目不出现在列表中。

**排序白名单**：

| `sort` | 主排序 | 次级排序 |
|---|---|---|
| `updated_desc` | `updated_at` 降序 | `id` 降序 |
| `title_asc` | `lower(title)` 升序 | `id` 升序 |
| `rating_desc` | 所有已评分标签的平均分降序，无评分排最后 | `updated_at` 降序、`id` 降序 |

所有排序都带 `id` 作为最终比较键，保证翻页不重复、不跳行。白名单之外的排序值返回 422。

## 4. 响应

```json
{
  "items": [
    {
      "id": 1,
      "share_id": "0f0a6d1e-...",
      "title": "塞尔达传说",
      "type": "game",
      "description": "开放世界冒险",
      "cover_path": null,
      "created_at": "2026-11-01T08:00:00",
      "updated_at": "2026-11-09T08:00:00",
      "tag_ids": [3, 5]
    }
  ],
  "total": 1,
  "page": 1,
  "page_size": 50
}
```

- `items` 字段沿用 `EntryRead`，`cover_path` 为后端字段名，是否对外暴露由成员二决定。
- `tag_ids` 由检索接口一次批量查询填充，供列表卡片显示标签，不产生 N+1 查询。
- `total` 是筛选后的总数，与当前页无关。

**空结果**：返回 200 与 `items: []`，`total` 为 0。
**超出末页**：返回 200 与 `items: []`，`total` 仍为真实总数。

## 5. 错误码

| 状态 | 错误码 | 触发条件 |
|---|---|---|
| 422 | `RATING_RANGE_INVALID` | `rating_min` 大于 `rating_max` |
| 422 | `VALIDATION_ERROR` | 页大小越界、排序值不在白名单、标签匹配方式非法 |

## 6. 性能基线

环境：Windows、Python 3.13、SQLite 单库、一万条目与一万九千条标签关系。

| 查询 | 耗时 | 计数耗时 |
|---|---|---|
| 首屏无筛选 | 5.5 ms | 1.5 ms |
| 关键词 | 2.9 ms | 1.5 ms |
| 单标签 | 4.1 ms | 2.6 ms |
| 双标签 OR + 评分区间 + 评分排序 | 8.7 ms | 5.5 ms |

结论：一阶段与二阶段的规模目标（一千条、一万条）不需要 FTS5。SQLite FTS5 的 `unicode61` 分词器不切分中文，`trigram` 要求查询不少于三个字符，两者都不适合当前的中文短片段检索。十万条目阶段再评估倒排索引或 trigram。

## 7. 待确认事项

1. 评分区间按 1 至 10 校验，与 `docs/tag-rating-contract.md` 一致；课程文档与分工文档中的 1 至 5 分需统一修正。
2. `GET /api/entries` 在 `backend/app/api/README.md` 中标注为成员二与成员四共同负责，本实现按「成员二负责单条字段与写入，成员四负责查询参数、筛选、排序、分页与 `tag_ids` 聚合」切分。
3. 前端 `types/api.ts` 使用 `cover`、`summary` 两个字段名，与本响应中的 `cover_path`、`description` 不一致，联调前需统一。
