<script setup lang="ts">
import { computed, onMounted, ref, watch } from 'vue'

import { createEntry, listEntries } from '../api/client'
import { USE_MOCK } from '../config'
import EmptyState from '../components/EmptyState.vue'
import EntryCard from '../components/EntryCard.vue'
import ErrorBanner from '../components/ErrorBanner.vue'
import FilterBar from '../components/FilterBar.vue'
import LoadingSkeleton from '../components/LoadingSkeleton.vue'
import type { Entry, SortKey, Tag } from '../types/api'
import { toMessage } from '../utils/error'

/**
 * 列表视图（三栏里的中间那栏）。
 *
 * 职责：拉数据、管筛选条件、按四种状态渲染。
 * 它不负责"选中哪个条目"的展示，选中结果通过 select 事件交给 App。
 */
const props = defineProps<{
  tags: Tag[]
  selectedTagIds: number[]
  selectedId: number | null
  /** 父组件把它加一，本组件就重新拉一次列表（移出库后刷新用） */
  refreshToken: number
}>()

const emit = defineEmits<{
  (e: 'select', entry: Entry): void
  (e: 'remove-tag', tagId: number): void
}>()

const keyword = ref('')
const appliedKeyword = ref('')
const sort = ref<SortKey>('updated_desc')
const entries = ref<Entry[]>([])
const total = ref(0)
const loading = ref(false)
const errorMessage = ref('')

const activeTags = computed(() =>
  props.tags.filter((tag) => props.selectedTagIds.includes(tag.id)),
)

const isFiltered = computed(
  () => appliedKeyword.value !== '' || props.selectedTagIds.length > 0,
)

/* ---- 拉列表 ---- */

async function load() {
  loading.value = true
  errorMessage.value = ''
  try {
    const page = await listEntries({
      q: appliedKeyword.value || undefined,
      tag_id: props.selectedTagIds.length > 0 ? props.selectedTagIds : undefined,
      sort: sort.value,
      page: 1,
      page_size: 50,
    })
    entries.value = page.items
    total.value = page.total
  } catch (error) {
    entries.value = []
    total.value = 0
    errorMessage.value = toMessage(error, '无法加载条目列表')
  } finally {
    loading.value = false
  }
}

/* ---- 搜索防抖：输入停顿 250ms 才真正发请求，避免每敲一个字打一次接口 ---- */

let debounceTimer: number | undefined

watch(keyword, (value) => {
  window.clearTimeout(debounceTimer)
  debounceTimer = window.setTimeout(() => {
    appliedKeyword.value = value.trim()
  }, 250)
})

watch(
  [appliedKeyword, sort, () => props.selectedTagIds.join(','), () => props.refreshToken],
  () => {
    void load()
  },
)

onMounted(() => {
  void load()
})

/* ---- 新建条目 ---- */

const typeOptions = ['电子书', '影视', '游戏', '音频', '图片', '模型', '其他']

const showForm = ref(false)
const formTitle = ref('')
const formType = ref('电子书')
const formSummary = ref('')
const formError = ref('')
const submitting = ref(false)

function openForm() {
  showForm.value = true
  formError.value = ''
}

function closeForm() {
  showForm.value = false
  formTitle.value = ''
  formSummary.value = ''
  formError.value = ''
}

async function submitForm() {
  if (formTitle.value.trim() === '') {
    formError.value = '标题不能为空'
    return
  }
  submitting.value = true
  formError.value = ''
  try {
    const created = await createEntry({
      title: formTitle.value.trim(),
      type: formType.value,
      summary: formSummary.value.trim(),
    })
    closeForm()
    await load()
    emit('select', created)
  } catch (error) {
    formError.value = toMessage(error, '创建失败')
  } finally {
    submitting.value = false
  }
}
</script>

<template>
  <div class="library">
    <header class="header">
      <div class="heading">
        <h2 class="heading-title">{{ appliedKeyword ? `搜索“${appliedKeyword}”` : '全部条目' }}</h2>
        <p class="faint">
          <span v-if="loading">加载中…</span>
          <span v-else>共 {{ total }} 个条目</span>
          <span v-if="USE_MOCK" class="mock-badge">演示数据</span>
        </p>
      </div>
      <button class="btn btn-primary" type="button" @click="openForm">新建条目</button>
    </header>

    <FilterBar
      :keyword="keyword"
      :sort="sort"
      :active-tags="activeTags"
      @update:keyword="keyword = $event"
      @update:sort="sort = $event"
      @remove-tag="emit('remove-tag', $event)"
    />

    <form v-if="showForm" class="create-form" @submit.prevent="submitForm">
      <input v-model="formTitle" class="field" placeholder="标题，例如 三体（全集）" />
      <select v-model="formType" class="field">
        <option v-for="type in typeOptions" :key="type" :value="type">{{ type }}</option>
      </select>
      <textarea v-model="formSummary" class="field" rows="2" placeholder="简介（可选）" />
      <p v-if="formError" class="form-error">{{ formError }}</p>
      <div class="form-actions">
        <button class="btn" type="button" :disabled="submitting" @click="closeForm">取消</button>
        <button class="btn btn-primary" type="submit" :disabled="submitting">
          {{ submitting ? '创建中…' : '创建' }}
        </button>
      </div>
    </form>

    <div class="body">
      <!-- 状态一：加载中 -->
      <LoadingSkeleton v-if="loading && entries.length === 0" :rows="4" />

      <!-- 状态二：出错 -->
      <ErrorBanner v-else-if="errorMessage" :message="errorMessage" @retry="load" />

      <!-- 状态三：空 -->
      <EmptyState
        v-else-if="entries.length === 0"
        :title="isFiltered ? '没有匹配的条目' : '还没有条目'"
        :description="
          isFiltered
            ? '当前筛选条件下没有找到条目，换个关键词或清掉标签筛选试试。'
            : '点击「新建条目」，把硬盘上的一个作品记录下来。'
        "
        :action-text="isFiltered ? undefined : '新建条目'"
        @action="openForm"
      />

      <!-- 状态四：有数据 -->
      <div v-else class="list">
        <EntryCard
          v-for="entry in entries"
          :key="entry.id"
          :entry="entry"
          :tags="tags"
          :selected="entry.id === props.selectedId"
          @select="emit('select', $event)"
        />
      </div>
    </div>
  </div>
</template>

<style scoped>
.library {
  height: 100%;
  display: flex;
  flex-direction: column;
  gap: 12px;
  padding: 16px;
  min-height: 0;
}

.header {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  gap: 12px;
}

.heading-title {
  font-size: 16px;
}

.mock-badge {
  margin-left: 8px;
  padding: 0 6px;
  border-radius: 999px;
  background: #fff4d6;
  color: #8a6100;
  font-size: 11px;
}

.create-form {
  display: flex;
  flex-direction: column;
  gap: 8px;
  padding: 12px;
  border: 1px solid var(--border);
  border-radius: var(--radius);
  background: var(--panel-alt);
}

.form-error {
  color: var(--danger);
  font-size: 12px;
}

.form-actions {
  display: flex;
  justify-content: flex-end;
  gap: 8px;
}

.body {
  flex: 1;
  min-height: 0;
  overflow-y: auto;
}

.list {
  display: flex;
  flex-direction: column;
  gap: 10px;
  padding-bottom: 16px;
}
</style>
