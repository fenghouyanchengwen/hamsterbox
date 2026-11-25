/**
 * 界面文案映射。
 *
 * 领域模型里存的是英文稳定值，界面必须显示中文（协作约定 9.6）。
 * 所有映射集中在这里，组件里不要各写一份 switch。
 */

import type { EntryType, ResourceAvailability, SortKey } from '../types/api'

/** 条目类型的中文名。key 必须覆盖 EntryType 的每一个值 */
export const ENTRY_TYPE_LABELS: Record<EntryType, string> = {
  game: '游戏',
  book: '书籍',
  video: '影视',
  audio: '音频',
  image: '图片',
  model: '模型',
  other: '其他',
}

/** 供下拉框使用的有序选项 */
export const ENTRY_TYPE_OPTIONS: { value: EntryType; label: string }[] = (
  Object.keys(ENTRY_TYPE_LABELS) as EntryType[]
).map((value) => ({ value, label: ENTRY_TYPE_LABELS[value] }))

export function entryTypeLabel(type: EntryType): string {
  return ENTRY_TYPE_LABELS[type] ?? type
}

/** 资源可用性的中文说明 */
export const AVAILABILITY_LABELS: Record<ResourceAvailability, string> = {
  present: '正常',
  missing: '文件已失效',
}

/** 排序方式的中文名 */
export const SORT_LABELS: Record<SortKey, string> = {
  updated_desc: '最近更新',
  title_asc: '标题',
  rating_desc: '评分',
}

export const SORT_OPTIONS: { value: SortKey; label: string }[] = (
  Object.keys(SORT_LABELS) as SortKey[]
).map((value) => ({ value, label: SORT_LABELS[value] }))
