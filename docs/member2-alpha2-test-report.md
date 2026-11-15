# 成员二 Alpha 第二阶段测试报告

| 项目 | 内容 |
|---|---|
| 用途 | 记录条目、资源、数据库迁移和桌面桥接模块的 Alpha 测试证据 |
| 负责人 | 成员二 |
| 测试日期 | 2026-11-15 |
| 被测提交 | `83723884dd434cf71af5a1e7ce5a0bd589f64b8a` |
| 被测范围 | 条目、资源、SQLite 迁移与级联、条目与资源 API、桌面桥资源打开、Alpha 二阶段资源工作流 |
| 结论 | 成员二负责的自动化测试全部通过；全量测试有一项已登记的适配器失败 |

## 1. 环境与方法

测试在 Windows 本机项目虚拟环境中执行，使用独立的 detached worktree 获取最新提交，未修改原分支。测试数据库和文件均使用临时数据，不接触用户媒体文件。

为兼容 Python 3.14 下 SQLAlchemy 导入时的本机 WMI 查询，执行时将 `platform.machine()` 固定为 `AMD64`。这是测试环境兼容设置，没有修改项目代码。

## 2. 成员二重点用例

执行领域、应用、API、数据库、迁移、集成、桥接和 Alpha 二阶段资源用例，结果为：

```text
51 passed, 57 warnings in 4.12s
```

覆盖范围包括：

- 条目模型、创建、查询、更新和移出库；
- 资源关联的路径校验、文件元数据和 SHA-256 计算；
- 同一资源、同一条目的重复关联拒绝；
- 资源文件缺失、恢复、重新检测、解除关联和原始文件保留；
- 资源 HTTP 响应不泄露本地绝对路径；
- Alembic 迁移、外键约束和资源记录级联删除；
- 桌面桥 `open_resource(resource_id)` 的调用和错误边界；
- 资源哈希变化、文件缺失、恢复和解除关联工作流。

重点测试文件包括：

- `tests/domain/test_entry_models.py`
- `tests/application/test_entry_service.py`
- `tests/application/test_resource_service.py`
- `tests/api/test_entries.py`
- `tests/api/test_resources.py`
- `tests/db/test_entry_repository.py`
- `tests/db/test_entry_resource_integration.py`
- `tests/db/test_migrations.py`
- `tests/db/test_constraints.py`
- `tests/e2e/test_alpha2_resource_workflow.py`
- `tests/adapters/test_bridge.py`

## 3. 全量回归

补齐项目声明的媒体测试依赖后，执行全部测试，结果为：

```text
161 passed, 1 xfailed, 111 warnings in 9.43s
```

唯一 `xfail` 是 `build_registry()` 重复注册多个 `FallbackAdapter` 导致 `ValueError`。使用 `--runxfail` 后按预期失败，说明适配器注册缺陷仍存在，不属于成员二负责模块。

## 4. 环境风险

- Starlette 提示当前 `httpx` 与 `starlette.testclient` 的组合已弃用。
- SQLite/Python 3.12+ 日期适配器产生 110 条弃用提醒。
- 新环境必须安装 `backend/requirements.txt` 中包含的媒体依赖，否则适配器测试无法收集。

这些问题不影响本轮断言结果，但应在后续迭代评估迁移和清理。

## 5. 未覆盖的人工验收

自动化测试没有替代以下桌面场景：

- Windows 下不同文件类型由系统默认程序打开的实际行为；
- `.exe`、`.bat`、`.cmd`、`.lnk` 的二次确认和取消流程；
- PyWebView 前端按钮到系统程序的完整人工点击流程；
- 用户真实媒体库、网络盘、长路径和权限拒绝场景。

## 6. 结论

条目与资源模块达到 Alpha 模块级自动化验收条件。团队 Alpha 出口仍受适配器注册缺陷、前端真实接口联调、Entry 整体评价字段和安装包场景验收影响。
