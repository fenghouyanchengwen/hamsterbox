/**
 * 展示层格式化工具。
 *
 * 时间约定（docs/architecture.md）：后端以 UTC 存储，界面按本地时区显示。
 * 所以这里一律用 Date 解析 ISO 字符串，再交给 Intl 按本地时区格式化，
 * 不要自己拼 "年-月-日" 字符串。
 */

/** 把 ISO 8601 字符串格式化为本地时区的日期时间 */
export function formatDateTime(iso: string): string {
  const date = new Date(iso)
  if (Number.isNaN(date.getTime())) {
    return '—'
  }
  return new Intl.DateTimeFormat('zh-CN', {
    year: 'numeric',
    month: '2-digit',
    day: '2-digit',
    hour: '2-digit',
    minute: '2-digit',
  }).format(date)
}

/** 只显示日期部分 */
export function formatDate(iso: string): string {
  const date = new Date(iso)
  if (Number.isNaN(date.getTime())) {
    return '—'
  }
  return new Intl.DateTimeFormat('zh-CN', {
    year: 'numeric',
    month: '2-digit',
    day: '2-digit',
  }).format(date)
}

/** 字节数转可读大小 */
export function formatBytes(bytes: number | null): string {
  if (bytes === null || bytes <= 0) {
    return '—'
  }
  const units = ['B', 'KB', 'MB', 'GB', 'TB']
  let value = bytes
  let index = 0
  while (value >= 1024 && index < units.length - 1) {
    value /= 1024
    index += 1
  }
  return `${value.toFixed(index === 0 ? 0 : 1)} ${units[index]}`
}
