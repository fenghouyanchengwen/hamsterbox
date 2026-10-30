# 文档索引

本目录保存跨模块共享的规范与过程记录。代码模块的职责说明放在各自目录的 `README.md`。

## 现有文档

| 文档 | 内容 | 负责人 |
|---|---|---|
| `architecture.md` | 技术栈、进程结构、接口边界与安全规则 | 成员八 |
| `branching.md` | 分支模型、提交格式、PR 与评审配对 | 成员八 |
| `share-package-spec.md` | 分享包 `.hbox` 格式与字段 | 成员五 |
| `share-package-v1.schema.json` | 分享包 JSON Schema | 成员五 |
| `meetings/README.md` | 每周 Scrum Meeting 记录模板 | 成员八 |

分享包规范目前位于成员五的分支，合并后进入本目录。

## 模块说明

| 模块 | 文档 |
|---|---|
| 后端总览 | `backend/README.md` |
| HTTP 接口 | `backend/app/api/README.md` |
| 应用服务 | `backend/app/application/README.md` |
| 数据层 | `backend/app/db/README.md` |
| 领域模型 | `backend/app/domain/README.md` |
| 文件适配器 | `backend/app/adapters/README.md` |
| 后台任务 | `backend/app/workers/README.md` |
| 前端 | `frontend/README.md` |
| 桌面容器 | `desktop/README.md` |
| 测试 | `tests/README.md` |
| 运行时数据 | `data/README.md` |

## 编写规则

- 接口变更先改文档，再改实现。
- 每个文档开头写明用途、负责人和最后更新日期。
- 文件名使用小写连字符。
- 中文正文，字段名与代码保持一致。
- 不在文档里写真实本机路径、账号或密钥。

## 更新节奏

- 每次 PR 如果改变了接口、字段或错误码，必须同步更新对应文档。
- 每周例会前检查一次文档是否落后于实现。
- 发布前由成员八统一校对文档链接是否有效。
