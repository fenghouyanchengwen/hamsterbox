/**
 * 与后端契约一一对应的类型定义。
 *
 * 唯一来源：
 * - backend/app/api/README.md          （接口索引）
 * - docs/api/entries-resources.md      （条目与资源契约）
 * - docs/tag-rating-contract.md        （标签与评分契约 v1）
 * - backend/app/domain/*.py            （Pydantic 模型，字段名的最终依据）
 *
 * 契约变了先改那三份文档，再改这里，最后改组件。
 */

/* ------------------------------------------------------------------ */
/* 基础枚举与常量                                                      */
/* ------------------------------------------------------------------ */

/**
 * 条目类型。领域模型使用英文稳定值，界面显示中文由 constants/labels.ts 负责。
 * 来源：backend/app/domain/entry.py 的 EntryType。
 */
export type EntryType =
  | 'game'
  | 'book'
  | 'video'
  | 'audio'
  | 'image'
  | 'model'
  | 'other'

/**
 * 条目生命周期。
 * library 正常条目；temporary 是分享时派生的隐藏条目，不出现在列表和检索里。
 */
export type LifecycleState = 'library' | 'temporary'

/** 资源可用性。missing 表示数据库有记录但磁盘文件不在了。 */
export type ResourceAvailability = 'present' | 'missing'

/** 排序方式，对应 GET /api/entries 的 sort 参数。 */
export type SortKey = 'updated_desc' | 'title_asc' | 'rating_desc'

/** 多标签匹配方式，对应 tag_mode 参数。 */
export type TagMode = 'and' | 'or'

/**
 * 评分区间：null 或 1 至 10 的整数。
 * 契约已从早期的 1 至 5 改为 1 至 10，见 docs/tag-rating-contract.md §2.5。
 */
export const RATING_MIN = 1
export const RATING_MAX = 10

/** 系统"未分类标签"分类的固定标识 */
export const SYSTEM_KEY_UNCATEGORIZED = 'uncategorized'

/* ------------------------------------------------------------------ */
/* 实体                                                                */
/* ------------------------------------------------------------------ */

export interface Entry {
  id: number
  /** 跨设备分享标识，UUID。前端不用它做业务判断 */
  share_id: string
  title: string
  type: EntryType
  description: string | null
  /**
   * 封面路径。契约 §3.1 写明"仅后端使用，不在响应中泄露绝对路径"，
   * 但 EntryRead 目前仍会返回它 —— 两处不一致，待成员二确认。
   * 定论前前端**不要**把它当 <img src> 用：本地路径在 http 页面里加载不了。
   */
  cover_path: string | null
  /**
   * 条目整体评价文字。
   *
   * ⚠ 契约 §3.1 与接口文档都要求有这个字段，但 domain/entry.py 的
   * EntryRead/EntryCreate/EntryUpdate 目前都没有暴露它，实际响应里取不到。
   * 见任务 T6-06，等成员二补齐模型后再接界面。
   */
  review?: string | null
  /** 同上，后端模型尚未暴露 */
  lifecycle_state?: LifecycleState
  created_at: string
  updated_at: string
}

/** 条目详情，多一个 resources 数组 */
export interface EntryDetail extends Entry {
  resources: Resource[]
}

export interface Resource {
  id: number
  share_id: string
  entry_id: number
  file_name: string
  /** 带点的扩展名，例如 ".mp4" */
  extension: string
  size_bytes: number | null
  mtime_ns: number | null
  sha256: string | null
  availability: ResourceAvailability
  /**
   * 注意：资源响应**不包含**本地绝对路径（契约 §4.2）。
   * 打开文件一律通过桥 open_resource(resource_id)，由后端解析路径。
   */
}

export interface ResourceList {
  items: Resource[]
  total: number
}

/** 重新检测的结果，比 Resource 多一个 changed 标记 */
export interface ResourceRecheck extends Resource {
  changed: boolean
}

/** 标签分类：只保存在本机，颜色不进入分享包 */
export interface TagCategory {
  id: number
  name: string
  color: string | null
  sort_order: number
  /** 用户分类为 null；系统"未分类标签"固定为 'uncategorized' */
  system_key: string | null
  created_at: string
  updated_at: string
}

/** 标签：没有颜色，也没有 rating_enabled */
export interface Tag {
  id: number
  category_id: number
  name: string
  created_at: string
  updated_at: string
}

/** 条目与标签的关系，带该维度上的可选评分 */
export interface EntryTag {
  entry_id: number
  tag_id: number
  tag_name: string
  category_id: number
  rating: number | null
  created_at: string
  updated_at: string
}

/**
 * 界面用的标签视图对象。
 *
 * Tag 本身没有颜色，颜色在所属分类上，所以渲染胶囊时要把两者拼起来。
 * 这不是后端契约的一部分，只是前端的展示辅助类型。
 */
export interface TagRef {
  id: number
  /** 所属分类，界面按分类分组时用 */
  category_id: number
  name: string
  color: string | null
}

/* ------------------------------------------------------------------ */
/* 通用响应与错误                                                      */
/* ------------------------------------------------------------------ */

export interface Paginated<T> {
  items: T[]
  total: number
  page: number
  page_size: number
}

/** 后端统一错误响应体 */
export interface ApiErrorBody {
  code: string
  message: string
  details?: Record<string, unknown>
}

/**
 * 契约中已登记的错误码。
 *
 * 前端判断分支**只能**用 code，不能用 message（契约 §3.2）：
 * message 是给人看的，允许改文案；code 是稳定标识。
 */
export const API_ERROR_CODES = [
  // 条目与资源（docs/api/entries-resources.md §3.2）
  'ENTRY_NOT_FOUND',
  'RESOURCE_NOT_FOUND',
  'RESOURCE_LINK_NOT_FOUND',
  'RESOURCE_FILE_MISSING',
  'RESOURCE_NOT_FILE',
  'RESOURCE_PATH_NOT_ABSOLUTE',
  'RESOURCE_ACCESS_DENIED',
  'RESOURCE_ALREADY_LINKED',
  'RESOURCE_OPEN_FAILED',
  // 标签与评分（docs/tag-rating-contract.md §6）
  'TAG_CATEGORY_NOT_FOUND',
  'TAG_NOT_FOUND',
  'ENTRY_TAG_NOT_FOUND',
  'TAG_CATEGORY_NAME_DUPLICATED',
  'TAG_NAME_DUPLICATED',
  'TAG_IN_USE',
  'TAG_CATEGORY_NOT_EMPTY',
  'SYSTEM_CATEGORY_PROTECTED',
  'TAG_NAME_INVALID',
  'TAG_CATEGORY_COLOR_INVALID',
  'RATING_OUT_OF_RANGE',
  'ENTRY_REVIEW_TOO_LONG',
  // 通用
  'VALIDATION_ERROR',
  'UNKNOWN',
] as const

export type ApiErrorCode = (typeof API_ERROR_CODES)[number]

export function isApiErrorCode(value: string): value is ApiErrorCode {
  return (API_ERROR_CODES as readonly string[]).includes(value)
}

/* ------------------------------------------------------------------ */
/* 请求载荷                                                            */
/* ------------------------------------------------------------------ */

export interface EntryListParams {
  q?: string
  type?: EntryType[]
  /** 可重复。注意：tag-rating-contract §8 写的是 tag_ids，两处不一致，待成员四确认 */
  tag_id?: number[]
  tag_mode?: TagMode
  /** 1 至 10 */
  rating_min?: number
  rating_max?: number
  sort?: SortKey
  page?: number
  page_size?: number
}

export interface EntryCreatePayload {
  title: string
  type: EntryType
  description?: string | null
  cover_path?: string | null
}

export interface EntryUpdatePayload {
  title?: string
  type?: EntryType
  description?: string | null
  cover_path?: string | null
  /** 契约允许，但后端模型还没暴露，见 T6-06 */
  review?: string | null
}

export interface ResourceCreatePayload {
  /** 只能来自桥 pick_files 的返回值 */
  path: string
  file_name?: string
}

export interface TagCategoryCreatePayload {
  name: string
  color?: string | null
  sort_order?: number
}

export interface TagCategoryUpdatePayload {
  name?: string
  color?: string | null
  sort_order?: number
}

export interface TagCreatePayload {
  category_id: number
  name: string
}

export interface TagUpdatePayload {
  category_id?: number
  name?: string
}

export interface EntryTagUpsertPayload {
  /** null 表示只关联不评分 */
  rating: number | null
}

export interface HealthResponse {
  status: string
}

export interface VersionResponse {
  version: string
}
