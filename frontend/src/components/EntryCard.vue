<script setup lang="ts">
import { computed } from 'vue'

import type { Entry, Tag } from '../types/api'
import { formatDate } from '../utils/format'
import TagChip from './TagChip.vue'

const props = withDefaults(
  defineProps<{
    entry: Entry
    /** 全量标签，用来把 entry.tag_ids 还原成标签对象 */
    tags: Tag[]
    selected?: boolean
  }>(),
  { selected: false },
)

const emit = defineEmits<{
  (e: 'select', entry: Entry): void
}>()

const entryTags = computed(() => {
  const ids = props.entry.tag_ids ?? []
  return props.tags.filter((tag) => ids.includes(tag.id))
})

/** 没有封面时用条目 id 生成稳定的渐变色，避免所有卡片长得一样 */
const coverStyle = computed(() => {
  const hue = (props.entry.id * 47) % 360
  return {
    backgroundImage: `linear-gradient(135deg, hsl(${hue}, 70%, 90%), hsl(${(hue + 40) % 360}, 65%, 80%))`,
  }
})

const coverInitial = computed(() => props.entry.title.slice(0, 1))
</script>

<template>
  <article class="card" :class="{ selected }" @click="emit('select', entry)">
    <div class="cover" :style="coverStyle">
      <img v-if="entry.cover" :src="entry.cover" :alt="entry.title" />
      <span v-else class="cover-initial">{{ coverInitial }}</span>
    </div>

    <div class="body">
      <div class="title-row">
        <h3 class="title" :title="entry.title">{{ entry.title }}</h3>
        <span class="type">{{ entry.type }}</span>
      </div>

      <p class="summary">{{ entry.summary || '暂无简介' }}</p>

      <div v-if="entryTags.length > 0" class="tags">
        <TagChip v-for="tag in entryTags" :key="tag.id" :tag="tag" />
      </div>

      <p class="faint">更新于 {{ formatDate(entry.updated_at) }}</p>
    </div>
  </article>
</template>

<style scoped>
.card {
  display: flex;
  gap: 12px;
  padding: 12px;
  border: 1px solid var(--border);
  border-radius: var(--radius);
  background: var(--panel);
  cursor: pointer;
  transition: border-color 0.15s, box-shadow 0.15s;
}

.card:hover {
  border-color: var(--border-strong);
  box-shadow: 0 2px 8px rgb(31 31 31 / 6%);
}

.card.selected {
  border-color: var(--accent);
  box-shadow: 0 0 0 2px var(--accent-soft);
}

.cover {
  flex: none;
  width: 72px;
  height: 74px;
  border-radius: var(--radius-sm);
  overflow: hidden;
  display: flex;
  align-items: center;
  justify-content: center;
  background: var(--panel-alt);
}

.cover img {
  width: 100%;
  height: 100%;
  object-fit: cover;
}

.cover-initial {
  color: #fff;
  font-size: 24px;
  font-weight: 600;
  text-shadow: 0 1px 2px rgb(0 0 0 / 12%);
}

.body {
  flex: 1;
  min-width: 0;
  display: flex;
  flex-direction: column;
  gap: 4px;
}

.title-row {
  display: flex;
  align-items: baseline;
  gap: 8px;
}

.title {
  flex: 1;
  min-width: 0;
  font-size: 14px;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.type {
  flex: none;
  padding: 0 6px;
  border-radius: var(--radius-sm);
  background: var(--panel-alt);
  color: var(--text-dim);
  font-size: 12px;
}

.summary {
  color: var(--text-dim);
  font-size: 12px;
  display: -webkit-box;
  -webkit-line-clamp: 2;
  -webkit-box-orient: vertical;
  overflow: hidden;
}

.tags {
  display: flex;
  flex-wrap: wrap;
  gap: 4px;
}
</style>
