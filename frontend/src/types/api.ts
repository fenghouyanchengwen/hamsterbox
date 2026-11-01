/**
 * 与后端契约一一对应的类型定义。
 *
 * 唯一来源：backend/app/api/README.md
 * 字段变了先改那份文档，再改这里，最后改组件。
 */

/** 条目类型。后端目前是自由字符串，这里不放枚举，避免和成员二的口径打架。 */
export type EntryType = string

/** 排序方式，对应 GET /api/entries 的 sort 参数。 */
export type SortKey = 'updated_desc' | 'title_asc' | 'rating_desc'

/** 多标签匹配方式，对应 tag_mode 参数。 */
export type TagMode = 'and' | 'or'

export interface Entry {
  id: number
  title: string
  type: EntryType
  /** 封面地址，可能为 null，组件里必须处理 */
  cover: string | null
  summary: string
  /** ISO 8601 字符串，存的是 UTC，界面按本地时区显示 */
  created_at: string
  updated_at: string
  /**
   * 该条目关联的标签 id。
   *
   * ⚠ 待确认：backend/app/api/README.md 没有定义列表响应是否携带标签。
   * 前端渲染卡片上的标签需要它，**必须和成员二确认后写进接口文档**。
   * 如果后端决定不返回，卡片改成不显示标签，届时删掉此字段。
   */
  tag_ids?: number[]
}

export interface Resource {
  id: number
  entry_id: number
  /** 绝对路径，只由后端从数据库读出，前端不拼接 */
  path: string
  file_name: string
  sha256: string | null
  size_bytes: number | null
  /** 文件当前是否还在磁盘上，false 时界面要打"失效"标记 */
  exists: boolean
}

export interface Tag {
  id: number
  name: string
  /** #RRGGBB */
  color: string
  /** 为 false 时评分控件必须禁用 */
  rating_enabled: boolean
  entry_count?: number
}

export interface Rating {
  tag_id: number
  /** 1 至 5，未评分时为 null */
  rating: number | null
  review: string
}

export interface Paginated<T> {
  items: T[]
  total: number
  page: number
  page_size: number
}

/** 后端的统一错误响应体 */
export interface ApiErrorBody {
  code: string
  message: string
  details?: Record<string, unknown>
}

export interface EntryListParams {
  q?: string
  type?: string[]
  tag_id?: number[]
  tag_mode?: TagMode
  rating_min?: number
  rating_max?: number
  sort?: SortKey
  page?: number
  page_size?: number
}

export interface EntryCreatePayload {
  title: string
  type: EntryType
  summary?: string
  cover?: string | null
}

export interface EntryUpdatePayload {
  title?: string
  type?: EntryType
  summary?: string
  cover?: string | null
}

export interface ResourceCreatePayload {
  path: string
  file_name: string
}

export interface RatingPayload {
  rating: number
  review?: string
}

export interface TagCreatePayload {
  name: string
  color: string
  rating_enabled: boolean
}

export interface HealthResponse {
  status: string
}

export interface VersionResponse {
  version: string
}
