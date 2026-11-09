# 成员四 M4-01 至 M4-03 交接记录

| 项目 | 内容 |
|---|---|
| 用途 | 记录条目检索的查询契约、仓储实现、HTTP 接口与测试交付 |
| 负责人 | 成员四：检索与展示 |
| 状态 | 关键词、单标签、多标签、评分区间、排序与分页已完成 |
| 最后更新 | 2026-11-09 |
| 关联 Issue | #11 |

## 1. 已完成

- 新增 `app/domain/search.py`：查询条件、排序枚举、标签匹配方式、分页结果模型。
- 新增 `app/db/entry_query_repository.py`：条件组装、排序白名单、计数与标签批量填充。
- 新增 `app/application/search_service.py`：查询编排与评分区间校验。
- 新增 `GET /api/entries`，落地 `backend/app/api/README.md` 中已登记的查询参数。
- 新增 `app/db/records.py::EntryQueryRow` 与 `ports.py::EntryQueryRepository` 协议。
- 新增错误码 `RATING_RANGE_INVALID`。
- 查询契约写入 `docs/api/entry-search.md`。

## 2. 测试结果

```powershell
.venv\Scripts\python.exe -m pytest -q
```

结果：`161 passed, 1 xfailed`。新增 15 个用例，覆盖：

- 关键词命中标题与简介、中文关键词、未命中返回空；
- `%` 与 `_` 按字面字符处理；
- 单标签、多标签 AND/OR 差异；
- 评分区间按任一已评分标签命中；
- 类型筛选与临时条目不进入列表；
- 三种排序的主次顺序；
- 分页不重复不遗漏、超出末页返回空；
- 列表项携带 `tag_ids`；
- 空库返回固定分页结构；
- `rating_min` 大于 `rating_max`、页大小越界、非法排序与非法匹配方式返回 422。

## 3. 关键接口约定

```http
GET /api/entries?q=塞尔&tag_id=3&tag_id=5&tag_mode=and&sort=rating_desc&page=1&page_size=50
```

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

排序只接受 `updated_desc`、`title_asc`、`rating_desc`，全部带 `id` 作为最终比较键。

## 4. 性能基线

一万条目、一万九千条标签关系下，最重的组合查询（双标签 OR + 评分区间 + 评分排序）为 8.7 ms，首屏 5.5 ms。详见 `docs/api/entry-search.md` 第 6 节。

## 5. 后续依赖

- 成员二：确认 `GET /api/entries` 字段归属；确认 `cover_path` 是否对外暴露。
- 成员三：评分区间按 1 至 10 实现，与标签评分契约一致。
- 成员六：移除前端 Mock 后按本契约联调；`cover`/`summary` 与 `cover_path`/`description` 的映射需统一。
- 成员八：把检索用例纳入回归，冒烟数据建议使用五个条目、两个带三个标签、其中两个开启评分。

## 6. 第二篇博客可引用内容

检索是主链路里唯一需要同时处理四个维度的地方：关键词、标签组合、评分区间和排序。实现时把维度拆成三处：

1. 条件组装集中在仓储层，关键词用参数绑定并对 `%`、`_` 转义，标签用 `EXISTS` 子查询，评分区间要求存在已评分标签；
2. 排序走白名单映射，每种排序都追加 `id` 作为最终比较键，翻页因此不会跳行或重复；
3. 空结果是正常业务状态，返回固定结构与真实总数，不返回错误。

文本检索没有采用 FTS5：SQLite 的中文分词要么不切分，要么要求查询不少于三个字符。一万条目下的实测最慢为 8.7 ms，普通索引加 `LIKE` 已经够用，倒排索引留到十万条目再评估。
