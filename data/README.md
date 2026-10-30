# 运行时数据说明

本目录保存应用运行产生的本地数据，目录内容不提交到仓库。

## 目录结构

```
data/
  library.db           SQLite 主库
  library.db-wal       WAL 日志
  library.db-shm       共享内存文件
  cache/
    thumbnails/        缩略图缓存
    previews/          导入预览临时数据
  logs/
    app.log            应用日志
  backups/
    library-YYYYMMDD-HHMMSS.db
  temp/
    imports/           分享包解压与导入临时目录
```

## 规则

- `library.db` 是唯一业务数据库，不手工编辑。
- 缓存可随时删除，删除后能重新生成。
- 日志按大小轮转，单个文件不超过 10 MiB。
- 备份使用 SQLite 在线备份接口，复制前执行 WAL checkpoint。
- 导入临时目录在成功或失败后都要清理。
- 本目录默认被 `.gitignore` 排除，只保留本说明文件。

## 迁移与备份

- 升级前自动备份一次。
- 备份文件名包含时间戳，保留最近 10 份。
- 恢复后执行外键一致性检查，再允许应用启动。
- 用户数据目录不放在安装目录内，卸载时不删除用户库。
