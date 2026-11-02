<script setup lang="ts">
import { computed, ref, watch } from 'vue'

import {
  clearRating,
  createResource,
  deleteEntry,
  getEntryRatings,
  getEntryResources,
  setRating,
} from '../api/client'
import { openResource, pickFiles } from '../bridge'
import EmptyState from '../components/EmptyState.vue'
import ErrorBanner from '../components/ErrorBanner.vue'
import RatingStars from '../components/RatingStars.vue'
import TagChip from '../components/TagChip.vue'
import type { Entry, Rating, Resource, Tag } from '../types/api'
import { toMessage } from '../utils/error'
import { formatBytes, formatDateTime } from '../utils/format'

/**
 * 详情视图（三栏里的右栏）。
 *
 * 自己负责资源列表和评分的读取，不把这些塞进列表数据里，
 * 避免列表接口为了显示详情而变重。
 */
const props = defineProps<{
  entry: Entry
  tags: Tag[]
}>()

const emit = defineEmits<{
  (e: 'close'): void
  (e: 'removed'): void
}>()

const resources = ref<Resource[]>([])
const ratings = ref<Rating[]>([])
const loading = ref(false)
const errorMessage = ref('')
const confirmRemove = ref(false)
const busy = ref(false)

const entryTags = computed(() => {
  const ids = props.entry.tag_ids ?? []
  return props.tags.filter((tag) => ids.includes(tag.id))
})

/* ---- 读取 ---- */

async function loadResources() {
  try {
    resources.value = await getEntryResources(props.entry.id)
  } catch (error) {
    errorMessage.value = toMessage(error, '无法读取资源列表')
  }
}

async function loadRatings() {
  try {
    ratings.value = await getEntryRatings(props.entry.id)
  } catch (error) {
    errorMessage.value = toMessage(error, '无法读取评分')
  }
}

async function loadAll() {
  loading.value = true
  errorMessage.value = ''
  await Promise.all([loadResources(), loadRatings()])
  loading.value = false
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
  return ratings.value.find((item) => item.tag_id === tagId)?.rating ?? null
}

function reviewOf(tagId: number): string {
  return ratings.value.find((item) => item.tag_id === tagId)?.review ?? ''
}

async function changeRating(tag: Tag, value: number | null) {
  errorMessage.value = ''
  try {
    if (value === null) {
      await clearRating(props.entry.id, tag.id)
    } else {
      // 只改分数时保留已有的评价文字，别把用户写的评论冲掉
      await setRating(props.entry.id, tag.id, { rating: value, review: reviewOf(tag.id) })
    }
    await loadRatings()
  } catch (error) {
    errorMessage.value = toMessage(error, '评分保存失败')
  }
}

/* ---- 资源 ---- */

async function addFiles() {
  errorMessage.value = ''
  try {
    const paths = await pickFiles()
    for (const path of paths) {
      // 路径只来自原生选择器；这里仅取文件名用于显示，不拼接路径
      const fileName = path.split(/[\\/]/).pop() ?? path
      await createResource(props.entry.id, { path, file_name: fileName })
    }
    await loadResources()
  } catch (error) {
    errorMessage.value = toMessage(error, '添加文件失败')
  }
}

async function open(resource: Resource) {
  errorMessage.value = ''
  try {
    await openResource(resource.id)
  } catch (error) {
    errorMessage.value = toMessage(error, '打开文件失败')
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
    errorMessage.value = toMessage(error, '移出库失败')
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
          {{ entry.type }} · 更新于 {{ formatDateTime(entry.updated_at) }}
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
        <h3 class="section-title">标签与评分</h3>

        <p v-if="entryTags.length === 0" class="faint">
          这个条目还没有标签。标签管理由成员三负责，界面接入后在这里添加。
        </p>

        <ul v-else class="rating-list">
          <li v-for="tag in entryTags" :key="tag.id" class="rating-row">
            <TagChip :tag="tag" />
            <RatingStars
              :rating="ratingOf(tag.id)"
              :disabled="!tag.rating_enabled"
              @change="changeRating(tag, $event)"
            />
            <span v-if="reviewOf(tag.id)" class="review">{{ reviewOf(tag.id) }}</span>
          </li>
        </ul>
      </section>

      <!-- 简介 -->
      <section class="section">
        <h3 class="section-title">简介</h3>
        <p v-if="entry.summary" class="summary">{{ entry.summary }}</p>
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
              <span class="faint">{{ formatBytes(resource.size_bytes) }}</span>
            </div>
            <span v-if="!resource.exists" class="missing">文件已失效</span>
            <button
              class="btn"
              type="button"
              :disabled="!resource.exists"
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

.rating-list,
.resource-list {
  margin: 0;
  padding: 0;
  list-style: none;
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.rating-row {
  display: flex;
  align-items: center;
  gap: 10px;
  flex-wrap: wrap;
}

.review {
  color: var(--text-dim);
  font-size: 12px;
}

.summary {
  color: var(--text);
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

.missing {
  padding: 0 6px;
  border-radius: var(--radius-sm);
  background: var(--danger-soft);
  color: var(--danger);
  font-size: 12px;
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
