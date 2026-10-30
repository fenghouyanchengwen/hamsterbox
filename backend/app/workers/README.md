# 后台任务说明

## 职责

处理耗时操作，避免阻塞 FastAPI 请求线程和界面。

负责人：成员七，成员八负责测试。

## 任务类型

| 任务 | 输入 | 输出 | 阶段 |
|---|---|---|---|
| `hash_resource` | `resource_id` | SHA-256、大小、更新时间 | Alpha |
| `recheck_resources` | 条目 ID 或资源 ID 列表 | 存在性与哈希状态 | Alpha |
| `scan_folder` | 文件夹路径、扩展名过滤 | 待导入文件列表 | Beta |
| `import_package` | 预览 ID、导入选择 | 导入进度与结果 | Beta |

## 接口

```python
class JobService:
    def submit(self, job: JobRequest) -> str: ...
    def status(self, job_id: str) -> JobStatus: ...
    def cancel(self, job_id: str) -> None: ...
```

状态模型：

```json
{
  "job_id": "uuid",
  "state": "pending|running|succeeded|failed|cancelled",
  "progress": 0.0,
  "message": "",
  "error": null
}
```

## 实现约束

- I/O 密集任务使用线程或 `asyncio.to_thread`。
- 长任务按批次提交数据库事务，不长时间持有写锁。
- 任务状态保存在内存，应用重启后不恢复。
- 同一资源的哈希任务需要去重。
- 任务失败必须返回可读错误，不吞异常。

## Alpha 范围

Alpha 只实现：

- 关联文件时计算一次 SHA-256。
- 手动重新检测资源存在性。

文件夹扫描和批量导入放到 Beta。
