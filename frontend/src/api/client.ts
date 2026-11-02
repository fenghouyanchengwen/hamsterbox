/**
 * 所有 HTTP 请求的唯一出口。
 *
 * 约定（frontend/README.md）：
 * - 组件里不许直接写 fetch，一律调用本文件的函数
 * - 只写相对路径 /api/...，由 vite.config.ts 的 proxy 转发到 127.0.0.1:8000
 * - 错误统一抛 ApiRequestError，组件据此决定显示什么
 *
 * USE_MOCK 为 true 时，业务接口返回 api/mock.ts 的演示数据（getHealth 例外，它永远
 * 走真实请求，用来确认后端到底通没通）。后端就绪后把 config.ts 里的开关改成 false。
 */

import { MOCK_LATENCY_MS, USE_MOCK } from '../config'
import type {
  ApiErrorBody,
  Entry,
  EntryCreatePayload,
  EntryListParams,
  EntryUpdatePayload,
  HealthResponse,
  Paginated,
  Rating,
  RatingPayload,
  Resource,
  ResourceCreatePayload,
  Tag,
  TagCreatePayload,
  VersionResponse,
} from '../types/api'
import {
  mockEntries,
  mockRatings,
  mockResources,
  mockTags,
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
  const list = mockRatings[entryId] ?? []
  const values = list
    .map((item) => item.rating)
    .filter((value): value is number => value !== null)
  if (values.length === 0) {
    return null
  }
  return values.reduce((sum, value) => sum + value, 0) / values.length
}

function mockListEntries(params: EntryListParams): Paginated<Entry> {
  const keyword = params.q?.trim().toLowerCase() ?? ''
  const tagIds = params.tag_id ?? []

  const filtered = mockEntries.filter((entry) => {
    if (keyword !== '') {
      const hit =
        entry.title.toLowerCase().includes(keyword) ||
        entry.summary.toLowerCase().includes(keyword)
      if (!hit) {
        return false
      }
    }

    if (tagIds.length > 0) {
      const ownTagIds = entry.tag_ids ?? []
      const matched =
        params.tag_mode === 'or'
          ? tagIds.some((id) => ownTagIds.includes(id))
          : tagIds.every((id) => ownTagIds.includes(id))
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

/** 健康检查。这个永远走真实请求，不受 USE_MOCK 影响。 */
export function getHealth() {
  return request<HealthResponse>('/health')
}

export function getVersion() {
  return request<VersionResponse>('/version')
}

/* ------------------------------------------------------------------ */
/* 条目                                                                */
/* ------------------------------------------------------------------ */

export function listEntries(params: EntryListParams = {}) {
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

export function getEntry(entryId: number) {
  if (USE_MOCK) {
    const found = mockEntries.find((entry) => entry.id === entryId)
    if (!found) {
      throw new ApiRequestError(404, { code: 'ENTRY_NOT_FOUND', message: '条目不存在' })
    }
    return delay(found)
  }
  return request<Entry>(`/entries/${entryId}`)
}

export function createEntry(payload: EntryCreatePayload) {
  if (USE_MOCK) {
    const now = new Date().toISOString()
    const nextId = mockEntries.reduce((max, entry) => Math.max(max, entry.id), 0) + 1
    const created: Entry = {
      id: nextId,
      title: payload.title,
      type: payload.type,
      cover: payload.cover ?? null,
      summary: payload.summary ?? '',
      created_at: now,
      updated_at: now,
      tag_ids: [],
    }
    mockEntries.unshift(created)
    mockResources[nextId] = []
    return delay(created)
  }
  return request<Entry>('/entries', { method: 'POST', body: JSON.stringify(payload) })
}

export function updateEntry(entryId: number, payload: EntryUpdatePayload) {
  if (USE_MOCK) {
    const target = mockEntries.find((entry) => entry.id === entryId)
    if (!target) {
      throw new ApiRequestError(404, { code: 'ENTRY_NOT_FOUND', message: '条目不存在' })
    }
    Object.assign(target, payload, { updated_at: new Date().toISOString() })
    return delay(target)
  }
  return request<Entry>(`/entries/${entryId}`, {
    method: 'PATCH',
    body: JSON.stringify(payload),
  })
}

/** 移出库。只解除软件里的记录，不动磁盘文件。 */
export function deleteEntry(entryId: number) {
  if (USE_MOCK) {
    const index = mockEntries.findIndex((entry) => entry.id === entryId)
    if (index >= 0) {
      mockEntries.splice(index, 1)
    }
    return delay(undefined as void)
  }
  return request<void>(`/entries/${entryId}`, { method: 'DELETE' })
}

/* ------------------------------------------------------------------ */
/* 资源                                                                */
/* ------------------------------------------------------------------ */

/**
 * 读取条目的资源列表。
 *
 * 注意：backend/app/api/README.md 目前只定义了资源的新增和解除关联，没写 GET 列表。
 * 这里先按 `/api/entries/{id}/resources` 约定，**需要和成员二确认后同步进接口文档**。
 */
export function getEntryResources(entryId: number) {
  if (USE_MOCK) {
    return delay(mockResources[entryId] ?? [])
  }
  return request<Resource[]>(`/entries/${entryId}/resources`)
}

/** path 只能来自桥返回的原生文件选择结果，禁止前端自己拼。 */
export function createResource(entryId: number, payload: ResourceCreatePayload) {
  if (USE_MOCK) {
    const list = mockResources[entryId] ?? (mockResources[entryId] = [])
    const nextId = list.reduce((max, item) => Math.max(max, item.id), 0) + 1
    const created: Resource = {
      id: nextId,
      entry_id: entryId,
      path: payload.path,
      file_name: payload.file_name,
      sha256: null,
      size_bytes: null,
      exists: true,
    }
    list.push(created)
    return delay(created)
  }
  return request<Resource>(`/entries/${entryId}/resources`, {
    method: 'POST',
    body: JSON.stringify(payload),
  })
}

export function deleteResource(entryId: number, resourceId: number) {
  if (USE_MOCK) {
    mockResources[entryId] = (mockResources[entryId] ?? []).filter(
      (item) => item.id !== resourceId,
    )
    return delay(undefined as void)
  }
  return request<void>(`/entries/${entryId}/resources/${resourceId}`, {
    method: 'DELETE',
  })
}

/** 重新检测文件是否存在并刷新哈希。 */
export function recheckResource(resourceId: number) {
  if (USE_MOCK) {
    for (const list of Object.values(mockResources)) {
      const found = list.find((item) => item.id === resourceId)
      if (found) {
        found.exists = true
        return delay(found)
      }
    }
    throw new ApiRequestError(404, { code: 'RESOURCE_NOT_FOUND', message: '资源不存在' })
  }
  return request<Resource>(`/resources/${resourceId}/recheck`, { method: 'POST' })
}

/* ------------------------------------------------------------------ */
/* 标签                                                                */
/* ------------------------------------------------------------------ */

export function listTags() {
  if (USE_MOCK) {
    return delay(mockTags)
  }
  return request<Tag[]>('/tags')
}

export function createTag(payload: TagCreatePayload) {
  if (USE_MOCK) {
    const nextId = mockTags.reduce((max, tag) => Math.max(max, tag.id), 0) + 1
    const created: Tag = { id: nextId, ...payload, entry_count: 0 }
    mockTags.push(created)
    return delay(created)
  }
  return request<Tag>('/tags', { method: 'POST', body: JSON.stringify(payload) })
}

export function updateTag(tagId: number, payload: Partial<TagCreatePayload>) {
  if (USE_MOCK) {
    const target = mockTags.find((tag) => tag.id === tagId)
    if (!target) {
      throw new ApiRequestError(404, { code: 'TAG_NOT_FOUND', message: '标签不存在' })
    }
    Object.assign(target, payload)
    return delay(target)
  }
  return request<Tag>(`/tags/${tagId}`, {
    method: 'PATCH',
    body: JSON.stringify(payload),
  })
}

export function deleteTag(tagId: number) {
  if (USE_MOCK) {
    const index = mockTags.findIndex((tag) => tag.id === tagId)
    if (index >= 0) {
      mockTags.splice(index, 1)
    }
    return delay(undefined as void)
  }
  return request<void>(`/tags/${tagId}`, { method: 'DELETE' })
}

/* ------------------------------------------------------------------ */
/* 评分                                                                */
/* ------------------------------------------------------------------ */

export function getEntryRatings(entryId: number) {
  if (USE_MOCK) {
    return delay(mockRatings[entryId] ?? [])
  }
  return request<Rating[]>(`/entries/${entryId}/ratings`)
}

export function setRating(entryId: number, tagId: number, payload: RatingPayload) {
  if (USE_MOCK) {
    const list = mockRatings[entryId] ?? (mockRatings[entryId] = [])
    const found = list.find((item) => item.tag_id === tagId)
    if (found) {
      found.rating = payload.rating
      found.review = payload.review ?? found.review
      return delay(found)
    }
    const created: Rating = {
      tag_id: tagId,
      rating: payload.rating,
      review: payload.review ?? '',
    }
    list.push(created)
    return delay(created)
  }
  return request<Rating>(`/entries/${entryId}/ratings/${tagId}`, {
    method: 'PUT',
    body: JSON.stringify(payload),
  })
}

export function clearRating(entryId: number, tagId: number) {
  if (USE_MOCK) {
    const list = mockRatings[entryId] ?? []
    const found = list.find((item) => item.tag_id === tagId)
    if (found) {
      found.rating = null
      found.review = ''
    }
    return delay(undefined as void)
  }
  return request<void>(`/entries/${entryId}/ratings/${tagId}`, { method: 'DELETE' })
}

/* ------------------------------------------------------------------ */
/* 分享包（Alpha 第二阶段接入）                                        */
/* ------------------------------------------------------------------ */

export interface ShareExportPayload {
  entry_ids: number[]
  include_covers: boolean
}

export function exportSharePackage(payload: ShareExportPayload) {
  if (USE_MOCK) {
    return delay({ file_name: 'hamsterbox-demo.hbox', entry_count: payload.entry_ids.length })
  }
  return request<{ file_name: string; entry_count: number }>('/share/export', {
    method: 'POST',
    body: JSON.stringify(payload),
  })
}
