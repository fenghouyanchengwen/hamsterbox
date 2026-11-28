# 分享包导入和预览接口

| 项目 | 内容 |
|---|---|
| 负责人 | 成员五 |
| 关联 Issue | #38 |
| 更新日期 | 2026-11-19 |

## 请求与响应

两个接口均使用 `Content-Type: application/octet-stream` 发送原始 `.hbox` 字节。

| 方法与路径 | 请求参数 | 成功响应 |
|---|---|---|
| `POST /api/share/import/preview` | 可选且可重复的 `tag_category=<tag_ref>:<category_id>` | `200`，返回 `package_sha256`、`manifest`、封面 `warnings` 和各条目的 `entries` 状态。 |
| `POST /api/share/import` | 必填的 `preview_sha256`。可重复传 `entry_share_id` 选择部分条目，省略则导入全部。可传同样的 `tag_category`。 | `200`，返回成功创建的 `imported` 条目和资源结果、跳过的 `skipped_share_ids` 和封面 `warnings`。 |

前端应在用户确认后再调用提交接口，并传入预览返回的 SHA-256。预览可能以本机状态变化为准更新。提交时再次校验包、复核 SHA-256 候选和冲突，在一个事务中写入条目、标签评分和匹配资源。资源的返回项只有 `share_id`、`status` 和 `candidate_count`，预览状态还包含标签冲突的名称 `tag_conflicts`。预览阶段只读，所有阶段均不解压到磁盘。

## 匹配与冲突

- 导入为条目生成接收端的主键，保留条目 `share_id`。同一 `share_id` 已存在时，在预览中显示 `conflict`，提交时跳过并保留本地数据。
- 对已登记资源，先按 SHA-256 查找，再对实际本地文件重新计算摘要，仅在恰有一个候选时自动关联。多个候选提示 `needs_selection`，无匹配提示 `missing`，重复资源标识或同条目重复路径提示 `conflict`。未关联的资源仍可在预览中查看，导入后用户可通过条目资源功能添加。
- 标签按目标分类的规范化名称复用。未指定时使用系统“未分类标签”。不同包内标签映射到同一分类中的同名标签时，相同评分可复用，不同评分需改选分类，提交返回冲突并回滚。
- 预览同时提供原评价和分享评价。导入为本地条目保存非空分享评价，否则保存原评价。
- 封面会校验归档路径、类型、大小、文件头与 SHA-256。预览报告缺失和损坏。初版导入保存条目元数据，封面落盘、手动候选选择和桌面界面仍待对接。

## 错误

| 状态 | 错误码 | 场景 |
|---|---|---|
| 422 | `SHARE_PACKAGE_INVALID` | 大小超限、ZIP 路径或成员无效、格式版本不兼容、JSON 或字段不合法。 |
| 422 | `SHARE_IMPORT_SELECTION_INVALID` | 选择了包外的条目、重复条目、重复的标签分类映射或无效分类。 |
| 409 | `SHARE_IMPORT_CONFLICT` | 提交字节与预览摘要不同，或所选条目的标签评分冲突。 |

## 验证

分别使用两个临时资料库模拟发送端与接收端。上传导出的测试包进行预览，并从响应复制 `package_sha256`。

```sh
curl --fail-with-body http://127.0.0.1:8000/api/share/import/preview \
  -H 'Content-Type: application/octet-stream' --data-binary '@hamsterbox.hbox'
curl --fail-with-body 'http://127.0.0.1:8000/api/share/import?preview_sha256=<预览返回的摘要>' \
  -H 'Content-Type: application/octet-stream' --data-binary '@hamsterbox.hbox'
python -m pytest -q tests/api/test_share_import_api.py tests/application/test_share_preview.py
```
