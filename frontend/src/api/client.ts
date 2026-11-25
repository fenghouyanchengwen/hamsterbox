/**
 * 所有 HTTP 请求的唯一出口。
 *
 * 约定（frontend/README.md）：
 * - 组件里不许直接写 fetch，一律调用本文件的函数
 * - 只写相对路径 /api/...，由 vite.config.ts 的 proxy 转发到 127.0.0.1:8000
 * - 错误统一抛 ApiRequestError，组件用 code 判断分支、用 describeApiError 取文案
 *
 * USE_MOCK 为 true 时业务接口返回 api/mock.ts 的演示数据（getHealth / getVersion 例外，
 * 它们永远走真实请求，用来确认后端到底通没通）。接口就绪后把 config.ts 的开关改成 false。
 *
 * 接口来源：backend/app/api/README.md。契约文档：
 * docs/api/entries-resources.md、docs/tag-rating-contract.md
 */

import { MOCK_LATENCY_MS, USE_MOCK } from '../config'
import {
  RATING_MAX,
  RATING_MIN,
  SYSTEM_KEY_UNCATEGORIZED,
  type ApiErrorBody,
  type ApiErrorCode,
  type Entry,
  type EntryCreatePayload,
  type EntryDetail,
  type EntryListParams,
  type EntryTag,
  type EntryTagUpsertPayload,
  type EntryUpdatePayload,
  type HealthResponse,
  type Paginated,
  type Resource,
  type ResourceCreatePayload,
  type ResourceList,
  type ResourceRecheck,
  type Tag,
  type TagCategory,
  type TagCategoryCreatePayload,
  type TagCategoryUpdatePayload,
  type TagCreatePayload,
  type TagUpdatePayload,
  type VersionResponse,
} from '../types/api'
import {
  buildEntryTags,
  mockCategories,
  mockEntries,
  mockEntryTagLinks,
  mockEntryTagRatings,
  mockResources,
  mockTags,
  newShareId,
} from './mock'

const BASE = '/api'

/* ------------------------------------------------------------------ */
/* 错误类型                                                            */
/* ------------------------------------------------------------------ */

export class ApiRequestError extends Error {
  status: number
  code: string
  details?: Record<string, unknown>

  constructor(status: number, body: ApiErrorBody) {
    super(body.message)
    this.name = 'ApiRequestError'
    this.status = status
    this.code = body.code
    this.details = body.details
  }
}

/** 演示数据里模拟后端抛错 */
function fail(status: number, code: ApiErrorCode, message: string): never {
  throw new ApiRequestError(status, { code, message })
}

/* ------------------------------------------------------------------ */
/* 底层请求                                                            */
/* ------------------------------------------------------------------ */

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  const response = await fetch(`${BASE}${path}`, {
    headers: { 'Content-Type': 'application/json' },
    ...init,
  })

  if (!response.ok) {
    let body: ApiErrorBody = {
      code: 'UNKNOWN',
      message: `HTTP ${response.status}`,
    }
    try {
      body = (await response.json()) as ApiErrorBody
    } catch {
      // 后端返回的不是 JSON（例如网关错误页），保留兜底信息
    }
    throw new ApiRequestError(response.status, body)
  }

  if (response.status === 204) {
    return undefined as T
  }
  return (await response.json()) as T
}

/* ------------------------------------------------------------------ */
/* 演示数据辅助                                                        */
/* ------------------------------------------------------------------ */

function delay<T>(value: T): Promise<T> {
  return new Promise((resolve) => {
    window.setTimeout(() => resolve(structuredClone(value)), MOCK_LATENCY_MS)
  })
}

function averageRating(entryId: number): number | null {
  const ratings = mockEntryTagRatings[entryId] ?? {}
  const values = Object.values(ratings).filter(
    (value): value is number => typeof value === 'number',
  )
  if (values.length === 0) {
    return null
  }
  return values.reduce((sum, value) => sum + value, 0) / values.length
}

function isRating(value: number | null): boolean {
  return value === null || (Number.isInteger(value) && value >= RATING_MIN && value <= RATING_MAX)
}

function mockListEntries(params: EntryListParams): Paginated<Entry> {
  const keyword = params.q?.trim().toLowerCase() ?? ''
  const tagIds = params.tag_id ?? []

  const filtered = mockEntries.filter((entry) => {
    if (entry.lifecycle_state === 'temporary') {
      return false
    }

    if (keyword !== '') {
      const hit =
        entry.title.toLowerCase().includes(keyword) ||
        (entry.description ?? '').toLowerCase().includes(keyword)
      if (!hit) {
        return false
      }
    }

    if (params.type && params.type.length > 0 && !params.type.includes(entry.type)) {
      return false
    }

    if (tagIds.length > 0) {
      const owned = mockEntryTagLinks[entry.id] ?? []
      const matched =
        params.tag_mode === 'or'
          ? tagIds.some((id) => owned.includes(id))
          : tagIds.every((id) => owned.includes(id))
      if (!matched) {
        return false
      }
    }

    if (params.rating_min != null || params.rating_max != null) {
      const value = averageRating(entry.id)
      if (value === null) {
        return false
      }
      if (params.rating_min != null && value < params.rating_min) {
        return false
      }
      if (params.rating_max != null && value > params.rating_max) {
        return false
      }
    }

    return true
  })

  const sorted = [...filtered]
  if (params.sort === 'title_asc') {
    sorted.sort((a, b) => a.title.localeCompare(b.title, 'zh-Hans-CN'))
  } else if (params.sort === 'rating_desc') {
    sorted.sort((a, b) => (averageRating(b.id) ?? -1) - (averageRating(a.id) ?? -1))
  } else {
    sorted.sort((a, b) => b.updated_at.localeCompare(a.updated_at))
  }

  const page = params.page ?? 1
  const pageSize = params.page_size ?? 50
  const start = (page - 1) * pageSize

  return {
    items: sorted.slice(start, start + pageSize),
    total: sorted.length,
    page,
    page_size: pageSize,
  }
}

/* ------------------------------------------------------------------ */
/* 系统                                                                */
/* ------------------------------------------------------------------ */

/** 健康检查。永远走真实请求，不受 USE_MOCK 影响 */
export async function getHealth(): Promise<HealthResponse> {
  return request<HealthResponse>('/health')
}

export async function getVersion(): Promise<VersionResponse> {
  return request<VersionResponse>('/version')
}

/* ------------------------------------------------------------------ */
/* 条目                                                                */
/* ------------------------------------------------------------------ */

/**
 * 条目列表、检索、筛选、排序与分页。
 *
 * ⚠ 后端尚未实现该接口（由成员四负责，见 T6-07）。目前只有 USE_MOCK 分支可用；
 * 接口上线后本函数的真实分支即可生效，参数已按契约写好。
 */
export async function listEntries(params: EntryListParams = {}): Promise<Paginated<Entry>> {
  if (USE_MOCK) {
    return delay(mockListEntries(params))
  }

  const query = new URLSearchParams()
  if (params.q) {
    query.set('q', params.q)
  }
  params.type?.forEach((value) => query.append('type', value))
  params.tag_id?.forEach((value) => query.append('tag_id', String(value)))
  if (params.tag_mode) {
    query.set('tag_mode', params.tag_mode)
  }
  if (params.rating_min != null) {
    query.set('rating_min', String(params.rating_min))
  }
  if (params.rating_max != null) {
    query.set('rating_max', String(params.rating_max))
  }
  if (params.sort) {
    query.set('sort', params.sort)
  }
  query.set('page', String(params.page ?? 1))
  query.set('page_size', String(params.page_size ?? 50))

  return request<Paginated<Entry>>(`/entries?${query.toString()}`)
}

/** 条目详情，响应里已带 resources（EntryDetail），无需再调资源列表 */
export async function getEntry(entryId: number): Promise<EntryDetail> {
  if (USE_MOCK) {
    const found = mockEntries.find((entry) => entry.id === entryId)
    if (!found) {
      fail(404, 'ENTRY_NOT_FOUND', `条目 ${entryId} 不存在`)
    }
    return delay<EntryDetail>({
      ...found,
      resources: mockResources[entryId] ?? [],
    })
  }
  return request<EntryDetail>(`/entries/${entryId}`)
}

export async function createEntry(payload: EntryCreatePayload): Promise<Entry> {
  if (USE_MOCK) {
    const title = payload.title.trim()
    if (title.length === 0 || title.length > 200) {
      fail(422, 'VALIDATION_ERROR', '标题长度必须在 1 到 200 之间')
    }
    const now = new Date().toISOString()
    const nextId = mockEntries.reduce((max, entry) => Math.max(max, entry.id), 0) + 1
    const created: Entry = {
      id: nextId,
      share_id: newShareId(),
      title,
      type: payload.type,
      description: payload.description ?? null,
      cover_path: payload.cover_path ?? null,
      review: null,
      lifecycle_state: 'library',
      created_at: now,
      updated_at: now,
    }
    mockEntries.unshift(created)
    mockEntryTagLinks[nextId] = []
    mockEntryTagRatings[nextId] = {}
    mockResources[nextId] = []
    return delay(created)
  }
  return request<Entry>('/entries', {
    method: 'POST',
    body: JSON.stringify(payload),
  })
}

export async function updateEntry(
  entryId: number,
  payload: EntryUpdatePayload,
): Promise<Entry> {
  if (USE_MOCK) {
    const target = mockEntries.find((entry) => entry.id === entryId)
    if (!target) {
      fail(404, 'ENTRY_NOT_FOUND', `条目 ${entryId} 不存在`)
    }
    Object.assign(target, payload, { updated_at: new Date().toISOString() })
    return delay(target)
  }
  return request<Entry>(`/entries/${entryId}`, {
    method: 'PATCH',
    body: JSON.stringify(payload),
  })
}

/** 移出库。只解除软件里的记录，不删除磁盘文件 */
export async function deleteEntry(entryId: number): Promise<void> {
  if (USE_MOCK) {
    const index = mockEntries.findIndex((entry) => entry.id === entryId)
    if (index < 0) {
      fail(404, 'ENTRY_NOT_FOUND', `条目 ${entryId} 不存在`)
    }
    mockEntries.splice(index, 1)
    delete mockEntryTagLinks[entryId]
    delete mockEntryTagRatings[entryId]
    delete mockResources[entryId]
    return delay(undefined)
  }
  return request<void>(`/entries/${entryId}`, { method: 'DELETE' })
}

/* ------------------------------------------------------------------ */
/* 资源                                                                */
/* ------------------------------------------------------------------ */

export async function listResources(entryId: number): Promise<ResourceList> {
  if (USE_MOCK) {
    const items = mockResources[entryId] ?? []
    return delay<ResourceList>({ items, total: items.length })
  }
  return request<ResourceList>(`/entries/${entryId}/resources`)
}

/** path 只能来自桥 pick_files 的返回值，禁止前端自己拼 */
export async function createResource(
  entryId: number,
  payload: ResourceCreatePayload,
): Promise<Resource> {
  if (USE_MOCK) {
    const entry = mockEntries.find((item) => item.id === entryId)
    if (!entry) {
      fail(404, 'ENTRY_NOT_FOUND', `条目 ${entryId} 不存在`)
    }
    const list = mockResources[entryId] ?? (mockResources[entryId] = [])
    const fileName = payload.file_name ?? payload.path.split(/[\\/]/).pop() ?? payload.path
    const dotIndex = fileName.lastIndexOf('.')
    const nextId = list.reduce((max, item) => Math.max(max, item.id), 0) + 1
    const created: Resource = {
      id: nextId,
      share_id: newShareId(),
      entry_id: entryId,
      file_name: fileName,
      extension: dotIndex >= 0 ? fileName.slice(dotIndex) : '',
      size_bytes: null,
      mtime_ns: null,
      sha256: null,
      availability: 'present',
    }
    list.push(created)
    return delay(created)
  }
  return request<Resource>(`/entries/${entryId}/resources`, {
    method: 'POST',
    body: JSON.stringify(payload),
  })
}

/** 解除关联，不删除磁盘文件 */
export async function deleteResource(entryId: number, resourceId: number): Promise<void> {
  if (USE_MOCK) {
    const list = mockResources[entryId] ?? []
    const index = list.findIndex((item) => item.id === resourceId)
    if (index < 0) {
      fail(404, 'RESOURCE_LINK_NOT_FOUND', '该条目没有关联此资源')
    }
    list.splice(index, 1)
    return delay(undefined)
  }
  return request<void>(`/entries/${entryId}/resources/${resourceId}`, {
    method: 'DELETE',
  })
}

/** 重新检测文件是否存在并刷新哈希。文件不存在不算请求失败，返回 availability='missing' */
export async function recheckResource(resourceId: number): Promise<ResourceRecheck> {
  if (USE_MOCK) {
    for (const list of Object.values(mockResources)) {
      const found = list.find((item) => item.id === resourceId)
      if (found) {
        const changed = found.availability !== 'present'
        found.availability = 'present'
        return delay<ResourceRecheck>({ ...found, changed })
      }
    }
    fail(404, 'RESOURCE_NOT_FOUND', '资源不存在')
  }
  return request<ResourceRecheck>(`/resources/${resourceId}/recheck`, {
    method: 'POST',
  })
}

/* ------------------------------------------------------------------ */
/* 标签分类                                                            */
/* ------------------------------------------------------------------ */

export async function listTagCategories(): Promise<TagCategory[]> {
  if (USE_MOCK) {
    const sorted = [...mockCategories].sort((a, b) => a.sort_order - b.sort_order)
    return delay(sorted)
  }
  return request<TagCategory[]>('/tag-categories')
}

export async function createTagCategory(
  payload: TagCategoryCreatePayload,
): Promise<TagCategory> {
  if (USE_MOCK) {
    const name = payload.name.trim()
    if (name.length === 0 || name.length > 32) {
      fail(422, 'TAG_NAME_INVALID', '分类名称长度必须在 1 到 32 之间')
    }
    if (mockCategories.some((item) => item.name.toLowerCase() === name.toLowerCase())) {
      fail(409, 'TAG_CATEGORY_NAME_DUPLICATED', '分类名称已存在')
    }
    if (payload.color && !/^#[0-9A-Fa-f]{6}$/.test(payload.color)) {
      fail(422, 'TAG_CATEGORY_COLOR_INVALID', '颜色格式必须是 #RRGGBB')
    }
    const now = new Date().toISOString()
    const nextId = mockCategories.reduce((max, item) => Math.max(max, item.id), 0) + 1
    const created: TagCategory = {
      id: nextId,
      name,
      color: payload.color ?? null,
      sort_order: payload.sort_order ?? 0,
      system_key: null,
      created_at: now,
      updated_at: now,
    }
    mockCategories.push(created)
    return delay(created)
  }
  return request<TagCategory>('/tag-categories', {
    method: 'POST',
    body: JSON.stringify(payload),
  })
}

export async function updateTagCategory(
  categoryId: number,
  payload: TagCategoryUpdatePayload,
): Promise<TagCategory> {
  if (USE_MOCK) {
    const target = mockCategories.find((item) => item.id === categoryId)
    if (!target) {
      fail(404, 'TAG_CATEGORY_NOT_FOUND', '标签分类不存在')
    }
    if (target.system_key === SYSTEM_KEY_UNCATEGORIZED && payload.name != null) {
      fail(409, 'SYSTEM_CATEGORY_PROTECTED', '系统分类不能修改')
    }
    if (
      payload.name != null &&
      mockCategories.some(
        (item) =>
          item.id !== categoryId && item.name.toLowerCase() === payload.name!.trim().toLowerCase(),
      )
    ) {
      fail(409, 'TAG_CATEGORY_NAME_DUPLICATED', '分类名称已存在')
    }
    Object.assign(target, payload, { updated_at: new Date().toISOString() })
    return delay(target)
  }
  return request<TagCategory>(`/tag-categories/${categoryId}`, {
    method: 'PATCH',
    body: JSON.stringify(payload),
  })
}

export async function deleteTagCategory(categoryId: number): Promise<void> {
  if (USE_MOCK) {
    const target = mockCategories.find((item) => item.id === categoryId)
    if (!target) {
      fail(404, 'TAG_CATEGORY_NOT_FOUND', '标签分类不存在')
    }
    if (target.system_key === SYSTEM_KEY_UNCATEGORIZED) {
      fail(409, 'SYSTEM_CATEGORY_PROTECTED', '系统分类不能删除')
    }
    if (mockTags.some((item) => item.category_id === categoryId)) {
      fail(409, 'TAG_CATEGORY_NOT_EMPTY', '该分类下还有标签')
    }
    const index = mockCategories.findIndex((item) => item.id === categoryId)
    mockCategories.splice(index, 1)
    return delay(undefined)
  }
  return request<void>(`/tag-categories/${categoryId}`, { method: 'DELETE' })
}

/* ------------------------------------------------------------------ */
/* 标签                                                                */
/* ------------------------------------------------------------------ */

export async function listTags(categoryId?: number): Promise<Tag[]> {
  if (USE_MOCK) {
    const items =
      categoryId == null
        ? mockTags
        : mockTags.filter((item) => item.category_id === categoryId)
    return delay(items)
  }
  const query = categoryId == null ? '' : `?category_id=${categoryId}`
  return request<Tag[]>(`/tags${query}`)
}

export async function createTag(payload: TagCreatePayload): Promise<Tag> {
  if (USE_MOCK) {
    const name = payload.name.trim()
    if (name.length === 0 || name.length > 32) {
      fail(422, 'TAG_NAME_INVALID', '标签名称长度必须在 1 到 32 之间')
    }
    const category = mockCategories.find((item) => item.id === payload.category_id)
    if (!category) {
      fail(404, 'TAG_CATEGORY_NOT_FOUND', '标签分类不存在')
    }
    const duplicated = mockTags.some(
      (item) =>
        item.category_id === payload.category_id &&
        item.name.toLowerCase() === name.toLowerCase(),
    )
    if (duplicated) {
      fail(409, 'TAG_NAME_DUPLICATED', '该分类下已有同名标签')
    }
    const now = new Date().toISOString()
    const nextId = mockTags.reduce((max, item) => Math.max(max, item.id), 0) + 1
    const created: Tag = {
      id: nextId,
      category_id: payload.category_id,
      name,
      created_at: now,
      updated_at: now,
    }
    mockTags.push(created)
    return delay(created)
  }
  return request<Tag>('/tags', {
    method: 'POST',
    body: JSON.stringify(payload),
  })
}

export async function updateTag(tagId: number, payload: TagUpdatePayload): Promise<Tag> {
  if (USE_MOCK) {
    const target = mockTags.find((item) => item.id === tagId)
    if (!target) {
      fail(404, 'TAG_NOT_FOUND', '标签不存在')
    }
    const categoryId = payload.category_id ?? target.category_id
    const name = payload.name?.trim() ?? target.name
    const duplicated = mockTags.some(
      (item) =>
        item.id !== tagId &&
        item.category_id === categoryId &&
        item.name.toLowerCase() === name.toLowerCase(),
    )
    if (duplicated) {
      fail(409, 'TAG_NAME_DUPLICATED', '该分类下已有同名标签')
    }
    target.category_id = categoryId
    target.name = name
    target.updated_at = new Date().toISOString()
    return delay(target)
  }
  return request<Tag>(`/tags/${tagId}`, {
    method: 'PATCH',
    body: JSON.stringify(payload),
  })
}

export async function deleteTag(tagId: number): Promise<void> {
  if (USE_MOCK) {
    const target = mockTags.find((item) => item.id === tagId)
    if (!target) {
      fail(404, 'TAG_NOT_FOUND', '标签不存在')
    }
    const inUse = Object.values(mockEntryTagLinks).some((ids) => ids.includes(tagId))
    if (inUse) {
      fail(409, 'TAG_IN_USE', '该标签仍被条目使用')
    }
    const index = mockTags.findIndex((item) => item.id === tagId)
    mockTags.splice(index, 1)
    return delay(undefined)
  }
  return request<void>(`/tags/${tagId}`, { method: 'DELETE' })
}

/* ------------------------------------------------------------------ */
/* 条目标签与评分                                                      */
/* ------------------------------------------------------------------ */

export async function listEntryTags(entryId: number): Promise<EntryTag[]> {
  if (USE_MOCK) {
    const entry = mockEntries.find((item) => item.id === entryId)
    if (!entry) {
      fail(404, 'ENTRY_NOT_FOUND', `条目 ${entryId} 不存在`)
    }
    return delay(buildEntryTags(entryId))
  }
  return request<EntryTag[]>(`/entries/${entryId}/tags`)
}

/** 幂等：不存在则创建关系，存在则只更新评分。rating 为 null 表示只关联不评分 */
export async function upsertEntryTag(
  entryId: number,
  tagId: number,
  payload: EntryTagUpsertPayload,
): Promise<EntryTag> {
  if (USE_MOCK) {
    const entry = mockEntries.find((item) => item.id === entryId)
    if (!entry) {
      fail(404, 'ENTRY_NOT_FOUND', `条目 ${entryId} 不存在`)
    }
    const tag = mockTags.find((item) => item.id === tagId)
    if (!tag) {
      fail(404, 'TAG_NOT_FOUND', '标签不存在')
    }
    if (!isRating(payload.rating)) {
      fail(422, 'RATING_OUT_OF_RANGE', `评分必须为空或 ${RATING_MIN} 到 ${RATING_MAX} 的整数`)
    }
    const links = mockEntryTagLinks[entryId] ?? (mockEntryTagLinks[entryId] = [])
    if (!links.includes(tagId)) {
      links.push(tagId)
    }
    const ratings = mockEntryTagRatings[entryId] ?? (mockEntryTagRatings[entryId] = {})
    ratings[tagId] = payload.rating
    const updated = buildEntryTags(entryId).find((item) => item.tag_id === tagId)
    if (!updated) {
      fail(404, 'ENTRY_TAG_NOT_FOUND', '条目标签关系不存在')
    }
    return delay(updated)
  }
  return request<EntryTag>(`/entries/${entryId}/tags/${tagId}`, {
    method: 'PUT',
    body: JSON.stringify(payload),
  })
}

/** 只移除关系，不删除标签定义 */
export async function removeEntryTag(entryId: number, tagId: number): Promise<void> {
  if (USE_MOCK) {
    const links = mockEntryTagLinks[entryId] ?? []
    const index = links.indexOf(tagId)
    if (index < 0) {
      fail(404, 'ENTRY_TAG_NOT_FOUND', '条目标签关系不存在')
    }
    links.splice(index, 1)
    const ratings = mockEntryTagRatings[entryId]
    if (ratings) {
      delete ratings[tagId]
    }
    return delay(undefined)
  }
  return request<void>(`/entries/${entryId}/tags/${tagId}`, { method: 'DELETE' })
}
