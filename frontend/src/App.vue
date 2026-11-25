<script setup lang="ts">
import { computed, onMounted, ref } from 'vue'

import { getHealth, listTagCategories, listTags } from './api/client'
import EmptyState from './components/EmptyState.vue'
import TagChip from './components/TagChip.vue'
import { USE_MOCK } from './config'
import type { Entry, Tag, TagCategory, TagRef } from './types/api'
import EntryDetailView from './views/EntryDetailView.vue'
import LibraryView from './views/LibraryView.vue'
import SettingsView from './views/SettingsView.vue'

/**
 * 应用外壳：侧栏 + 列表 + 详情 三栏。
 *
 * 状态集中在这里的理由：条目"选中"这件事跨了两栏（列表里选、详情里看），
 * 标签筛选也跨了两栏（侧栏里点、列表里生效），所以由 App 持有，
 * 其余组件通过 props 拿、通过事件报。
 */

type Pane = 'library' | 'settings'

const pane = ref<Pane>('library')
const selectedEntry = ref<Entry | null>(null)
const selectedTagIds = ref<number[]>([])
const categories = ref<TagCategory[]>([])
const tags = ref<Tag[]>([])
const backendStatus = ref<'checking' | 'ok' | 'down'>('checking')
/** 加一就触发列表刷新，用于移出库之后 */
const refreshToken = ref(0)

onMounted(async () => {
  try {
    const health = await getHealth()
    backendStatus.value = health.status === 'ok' ? 'ok' : 'down'
  } catch {
    backendStatus.value = 'down'
  }

  try {
    const [categoryList, tagList] = await Promise.all([listTagCategories(), listTags()])
    categories.value = categoryList
    tags.value = tagList
  } catch {
    categories.value = []
    tags.value = []
  }
})

/** Tag 没有颜色，颜色在分类上，这里把两者拼成界面用的视图对象 */
const tagRefs = computed<TagRef[]>(() => {
  const colors = new Map<number, string | null>()
  for (const category of categories.value) {
    colors.set(category.id, category.color)
  }
  return tags.value.map((tag) => ({
    id: tag.id,
    category_id: tag.category_id,
    name: tag.name,
    color: colors.get(tag.category_id) ?? null,
  }))
})

/** 侧栏按分类分组显示标签 */
const groupedTags = computed(() =>
  categories.value.map((category) => ({
    category,
    tags: tagRefs.value.filter((tag) => tag.category_id === category.id),
  })),
)

const backendLabel = computed(() => {
  if (backendStatus.value === 'checking') {
    return '检测中'
  }
  return backendStatus.value === 'ok' ? '后端已连接' : '后端未启动'
})

/** 点在已选中的标签上就是取消筛选，所以用"切换"而不是"添加" */
function toggleTag(tagId: number) {
  selectedTagIds.value = selectedTagIds.value.includes(tagId)
    ? selectedTagIds.value.filter((id) => id !== tagId)
    : [...selectedTagIds.value, tagId]
}

function selectEntry(entry: Entry) {
  selectedEntry.value = entry
  pane.value = 'library'
}

/** 条目被移出库后：关掉详情，并让列表重新拉一次 */
function handleRemoved() {
  selectedEntry.value = null
  refreshToken.value += 1
}
</script>

<template>
  <div class="shell">
    <!-- 第一栏：侧栏 -->
    <aside class="sidebar">
      <div class="brand">
        <span class="logo">🐹</span>
        <span class="brand-name">仓鼠盒</span>
      </div>

      <nav class="nav">
        <button
          class="nav-item"
          :class="{ active: pane === 'library' }"
          type="button"
          @click="pane = 'library'"
        >
          全部条目
        </button>
        <button
          class="nav-item"
          :class="{ active: pane === 'settings' }"
          type="button"
          @click="pane = 'settings'"
        >
          设置
        </button>
      </nav>

      <div class="tags-section">
        <p v-if="categories.length === 0" class="faint">还没有标签</p>

        <div v-for="group in groupedTags" :key="group.category.id" class="tag-group">
          <p class="group-title">
            <span
              class="group-dot"
              :style="{ backgroundColor: group.category.color ?? 'var(--border-strong)' }"
            />
            {{ group.category.name }}
          </p>
          <div v-if="group.tags.length > 0" class="tag-list">
            <TagChip
              v-for="tag in group.tags"
              :key="tag.id"
              :name="tag.name"
              :color="tag.color"
              :active="selectedTagIds.includes(tag.id)"
              @click="toggleTag(tag.id)"
            />
          </div>
          <p v-else class="faint empty-hint">暂无标签</p>
        </div>
      </div>

      <footer class="sidebar-footer">
        <span class="status-dot" :class="backendStatus" />
        <span class="faint">{{ backendLabel }}</span>
        <span v-if="USE_MOCK" class="mock">演示数据</span>
      </footer>
    </aside>

    <!-- 第二栏：列表 -->
    <section class="list-pane">
      <LibraryView
        v-if="pane === 'library'"
        :tag-refs="tagRefs"
        :selected-tag-ids="selectedTagIds"
        :selected-id="selectedEntry ? selectedEntry.id : null"
        :refresh-token="refreshToken"
        @select="selectEntry"
        @remove-tag="toggleTag"
      />
      <SettingsView v-else />
    </section>

    <!-- 第三栏：详情 -->
    <section class="detail-pane">
      <EntryDetailView
        v-if="selectedEntry"
        :entry="selectedEntry"
        :categories="categories"
        @close="selectedEntry = null"
        @removed="handleRemoved"
      />
      <EmptyState
        v-else
        title="还没有选中条目"
        description="从中间列表点一张卡片，这里会显示它的标签评分、简介和关联文件。"
      />
    </section>
  </div>
</template>

<style scoped>
.shell {
  display: flex;
  height: 100%;
  overflow: hidden;
}

.sidebar {
  flex: none;
  width: var(--sidebar-width);
  display: flex;
  flex-direction: column;
  gap: 16px;
  padding: 16px 12px;
  border-right: 1px solid var(--border);
  background: var(--panel);
}

.brand {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 0 4px;
}

.logo {
  font-size: 20px;
  line-height: 1;
}

.brand-name {
  font-size: 15px;
  font-weight: 600;
}

.nav {
  display: flex;
  flex-direction: column;
  gap: 2px;
}

.nav-item {
  padding: 7px 10px;
  border: none;
  border-radius: var(--radius-sm);
  background: transparent;
  color: var(--text-dim);
  text-align: left;
}

.nav-item:hover {
  background: var(--panel-alt);
}

.nav-item.active {
  background: var(--accent-soft);
  color: var(--accent);
  font-weight: 600;
}

.tags-section {
  flex: 1;
  min-height: 0;
  overflow-y: auto;
  display: flex;
  flex-direction: column;
  gap: 12px;
}

.tag-group {
  display: flex;
  flex-direction: column;
  gap: 6px;
}

.group-title {
  display: flex;
  align-items: center;
  gap: 5px;
  padding: 0 4px;
  color: var(--text-faint);
  font-size: 12px;
}

.group-dot {
  width: 7px;
  height: 7px;
  border-radius: 50%;
  flex: none;
}

.tag-list {
  display: flex;
  flex-wrap: wrap;
  gap: 6px;
  padding: 0 2px;
}

.empty-hint {
  padding: 0 4px;
}

.sidebar-footer {
  display: flex;
  align-items: center;
  gap: 6px;
  padding: 8px 4px 0;
  border-top: 1px solid var(--border);
}

.status-dot {
  width: 7px;
  height: 7px;
  border-radius: 50%;
  background: var(--text-faint);
  flex: none;
}

.status-dot.ok {
  background: var(--success);
}

.status-dot.down {
  background: var(--danger);
}

.mock {
  margin-left: auto;
  padding: 0 6px;
  border-radius: 999px;
  background: #fff4d6;
  color: #8a6100;
  font-size: 11px;
}

.list-pane {
  flex: none;
  width: var(--list-width);
  min-height: 0;
  border-right: 1px solid var(--border);
  background: var(--bg);
}

.detail-pane {
  flex: 1;
  min-width: 0;
  min-height: 0;
  background: var(--panel);
}
</style>
