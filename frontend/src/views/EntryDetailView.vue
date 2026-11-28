<script setup lang="ts">
import { computed, ref, watch } from 'vue'

import {
  createResource,
  deleteEntry,
  getEntry,
  listEntryTags,
  upsertEntryTag,
} from '../api/client'
import { openResource, pickFiles } from '../bridge'
import { AVAILABILITY_LABELS, entryTypeLabel } from '../constants/labels'
import EmptyState from '../components/EmptyState.vue'
import ErrorBanner from '../components/ErrorBanner.vue'
import RatingScale from '../components/RatingScale.vue'
import TagChip from '../components/TagChip.vue'
import type { Entry, EntryTag, Resource, TagCategory } from '../types/api'
import { describeApiError } from '../utils/error'
import { formatBytes, formatDateTime } from '../utils/format'

/**
 * 详情视图（三栏里的右栏）。
 *
 * 数据来源：
 * - GET /api/entries/{id}           → 条目详情，响应里已带 resources
 * - GET /api/entries/{id}/tags      → 标签与评分
 * 两个请求并行发出，避免串行等待。
 */
const props = defineProps<{
  entry: Entry
  /** 标签分类，用于给标签胶囊取颜色（Tag 自身没有颜色） */
  categories: TagCategory[]
}>()

const emit = defineEmits<{
  (e: 'close'): void
  (e: 'removed'): void
}>()

const resources = ref<Resource[]>([])
const entryTags = ref<EntryTag[]>([])
const loading = ref(false)
const errorMessage = ref('')
const confirmRemove = ref(false)
const busy = ref(false)

const typeLabel = computed(() => entryTypeLabel(props.entry.type))

/** 分类 id → 颜色，标签胶囊渲染用 */
const categoryColors = computed(() => {
  const map = new Map<number, string | null>()
  for (const category of props.categories) {
    map.set(category.id, category.color)
  }
  return map
})

function colorOf(categoryId: number): string | null {
  return categoryColors.value.get(categoryId) ?? null
}

/* ---- 读取 ---- */

async function loadAll() {
  loading.value = true
  errorMessage.value = ''
  try {
    const [detail, tags] = await Promise.all([
      getEntry(props.entry.id),
      listEntryTags(props.entry.id),
    ])
    resources.value = detail.resources
    entryTags.value = tags
  } catch (error) {
    errorMessage.value = describeApiError(error, '无法加载条目详情')
    resources.value = []
    entryTags.value = []
  } finally {
    loading.value = false
  }
}

watch(
  () => props.entry.id,
  () => {
    confirmRemove.value = false
    void loadAll()
  },
  { immediate: true },
)

/* ---- 评分 ---- */

function ratingOf(tagId: number): number | null {
  return entryTags.value.find((item) => item.tag_id === tagId)?.rating ?? null
}

/** PUT 是幂等的：不存在则建关系，存在则只更新评分 */
async function changeRating(entryTag: EntryTag, value: number | null) {
  errorMessage.value = ''
  try {
    const updated = await upsertEntryTag(props.entry.id, entryTag.tag_id, { rating: value })
    const index = entryTags.value.findIndex((item) => item.tag_id === entryTag.tag_id)
    if (index >= 0) {
      entryTags.value.splice(index, 1, updated)
    } else {
      entryTags.value.push(updated)
    }
  } catch (error) {
    errorMessage.value = describeApiError(error, '评分保存失败')
  }
}

/* ---- 资源 ---- */

async function addFiles() {
  errorMessage.value = ''
  try {
    const paths = await pickFiles()
    if (paths.length === 0) {
      return
    }
    for (const path of paths) {
      // 路径只来自原生选择器；这里仅取文件名用于显示，不拼接路径
      const fileName = path.split(/[\\/]/).pop() ?? path
      await createResource(props.entry.id, { path, file_name: fileName })
    }
    await loadAll()
  } catch (error) {
    errorMessage.value = describeApiError(error, '添加文件失败')
  }
}

async function open(resource: Resource) {
  errorMessage.value = ''
  try {
    const result = await openResource(resource.id)
    if (!result.ok) {
      errorMessage.value = `${result.message ?? '无法打开文件'}${result.error ? `（${result.error}）` : ''}`
    }
  } catch (error) {
    errorMessage.value = describeApiError(error, '打开文件失败')
  }
}

/* ---- 移出库 ---- */

async function removeEntry() {
  busy.value = true
  errorMessage.value = ''
  try {
    await deleteEntry(props.entry.id)
    emit('removed')
  } catch (error) {
    errorMessage.value = describeApiError(error, '移出库失败')
  } finally {
    busy.value = false
    confirmRemove.value = false
  }
}
</script>

<template>
  <div class="detail">
    <header class="header">
      <div class="heading">
        <h2 class="title">{{ entry.title }}</h2>
        <p class="faint">
          {{ typeLabel }} · 更新于 {{ formatDateTime(entry.updated_at) }}
        </p>
      </div>
      <button class="btn btn-ghost" type="button" title="关闭详情" @click="emit('close')">
        ×
      </button>
    </header>

    <div class="scroll">
      <ErrorBanner v-if="errorMessage" :message="errorMessage" @retry="loadAll" />

      <!-- 标签与评分 -->
      <section class="section">
        <h3 class="section-title">标签与评分（1–10 分）</h3>

        <p v-if="loading" class="faint">加载中…</p>

        <p v-else-if="entryTags.length === 0" class="faint">
          这个条目还没有标签。添加标签的入口在任务 T6-03 里实现。
        </p>

        <ul v-else class="tag-list">
          <li v-for="item in entryTags" :key="item.tag_id" class="tag-row">
            <TagChip :name="item.tag_name"
                     :color="colorOf(item.category_id)" />
            <RatingScale :rating="ratingOf(item.tag_id)" @change="changeRating(item, $event)" />
            <button class="remove-tag" type="button" title="移出标签"></button>
          </li>
        </ul>
        <button 
          class="add-tag"
          type="button"
          title="添加标签"
        >
        </button>
      </section>

      <!-- 简介 -->
      <section class="section">
        <h3 class="section-title">简介</h3>
        <p v-if="entry.description" class="description">{{ entry.description }}</p>
        <p v-else class="faint">暂无简介</p>
      </section>

      <!-- 关联文件 -->
      <section class="section">
        <div class="section-head">
          <h3 class="section-title">关联文件</h3>
          <button class="btn" type="button" @click="addFiles">添加文件</button>
        </div>

        <p v-if="loading" class="faint">加载中…</p>

        <EmptyState
          v-else-if="resources.length === 0"
          title="还没有关联文件"
          description="点击「添加文件」把硬盘上的文件挂到这个条目上。文件留在原位置，软件只记录路径。"
        />

        <ul v-else class="resource-list">
          <li v-for="resource in resources" :key="resource.id" class="resource-row">
            <div class="resource-main">
              <span class="resource-name" :title="resource.file_name">
                {{ resource.file_name }}
              </span>
              <span class="faint">
                {{ resource.extension || '—' }} · {{ formatBytes(resource.size_bytes) }}
              </span>
            </div>
            <span
              class="availability"
              :class="resource.availability"
            >
              {{ AVAILABILITY_LABELS[resource.availability] }}
            </span>
            <button
              class="btn"
              type="button"
              :disabled="resource.availability !== 'present'"
              @click="open(resource)"
            >
              打开
            </button>
          </li>
        </ul>
      </section>
    </div>

    <footer class="footer">
      <template v-if="!confirmRemove">
        <button class="btn btn-danger" type="button" @click="confirmRemove = true">
          移出库
        </button>
        <span class="faint">只从软件里移除记录，不会删除磁盘文件。</span>
      </template>

      <template v-else>
        <div class="confirm">
          <p class="confirm-text">
            确认把「{{ entry.title }}」移出库？磁盘上的文件不会被删除。
          </p>
          <div class="confirm-actions">
            <button class="btn" type="button" :disabled="busy" @click="confirmRemove = false">
              取消
            </button>
            <button class="btn btn-danger" type="button" :disabled="busy" @click="removeEntry">
              {{ busy ? '处理中…' : '确认移出' }}
            </button>
          </div>
        </div>
      </template>
    </footer>
  </div>
</template>

<style scoped>
.detail {
  height: 100%;
  display: flex;
  flex-direction: column;
  min-height: 0;
}

.header {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  gap: 12px;
  padding: 16px;
  border-bottom: 1px solid var(--border);
}

.title {
  font-size: 17px;
}

.scroll {
  flex: 1;
  min-height: 0;
  overflow-y: auto;
  padding: 16px;
  display: flex;
  flex-direction: column;
  gap: 20px;
}

.section {
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.section-head {
  display: flex;
  align-items: center;
  justify-content: space-between;
}

.section-title {
  font-size: 13px;
  color: var(--text-dim);
  font-weight: 600;
}

.tag-list,
.resource-list {
  margin: 0;
  padding: 0;
  list-style: none;
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.tag-row {
  display: flex;
  align-items: center;
  gap: 10px;
  flex-wrap: wrap;
}

.remove-tag {
  

}

.description {
  color: var(--text);
  white-space: pre-wrap;
}

.resource-row {
  display: flex;
  align-items: center;
  gap: 10px;
  padding: 8px 10px;
  border: 1px solid var(--border);
  border-radius: var(--radius-sm);
  background: var(--panel);
}

.resource-main {
  flex: 1;
  min-width: 0;
  display: flex;
  flex-direction: column;
}

.resource-name {
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.availability {
  padding: 0 6px;
  border-radius: var(--radius-sm);
  font-size: 12px;
  background: var(--panel-alt);
  color: var(--text-dim);
}

.availability.missing {
  background: var(--danger-soft);
  color: var(--danger);
}

.footer {
  display: flex;
  align-items: center;
  gap: 12px;
  padding: 12px 16px;
  border-top: 1px solid var(--border);
  background: var(--panel-alt);
}

.confirm {
  display: flex;
  flex-direction: column;
  gap: 8px;
  width: 100%;
}

.confirm-text {
  color: #a5282c;
  font-size: 13px;
}

.confirm-actions {
  display: flex;
  gap: 8px;
}
</style>
