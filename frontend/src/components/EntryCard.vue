<script setup lang="ts">
import { computed } from 'vue'

import { entryTypeLabel } from '../constants/labels'
import type { Entry } from '../types/api'
import { formatDate } from '../utils/format'

/**
 * 条目卡片。
 *
 * 两点刻意的取舍：
 * 1. 不显示标签。列表接口还没定义是否返回标签摘要，逐条请求 /entries/{id}/tags
 *    会造成 N+1 请求（20 条卡片 20 个请求）。等成员四确认后再决定（任务 T6-07）。
 * 2. 不把 cover_path 当 <img src>。它是本地绝对路径，在 http 页面里加载不了，
 *    而且契约说这个路径不该外泄。暂时用首字渐变占位。
 */
const props = withDefaults(
  defineProps<{
    entry: Entry
    selected?: boolean
  }>(),
  { selected: false },
)

const emit = defineEmits<{
  (e: 'select', entry: Entry): void
}>()

/** 没有封面时用条目 id 生成稳定的渐变色，避免所有卡片长得一样 */
const coverStyle = computed(() => {
  const hue = (props.entry.id * 47) % 360
  return {
    backgroundImage: `linear-gradient(135deg, hsl(${hue}, 70%, 90%), hsl(${(hue + 40) % 360}, 65%, 80%))`,
  }
})

const coverInitial = computed(() => props.entry.title.slice(0, 1))

const typeLabel = computed(() => entryTypeLabel(props.entry.type))
</script>

<template>
  <article class="card" :class="{ selected }" @click="emit('select', entry)">
    <div class="cover" :style="coverStyle">
      <span class="cover-initial">{{ coverInitial }}</span>
    </div>

    <div class="body">
      <div class="title-row">
        <h3 class="title" :title="entry.title">{{ entry.title }}</h3>
        <span class="type">{{ typeLabel }}</span>
      </div>

      <p class="description">{{ entry.description || '暂无简介' }}</p>

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
  width: 56px;
  height: 74px;
  border-radius: var(--radius-sm);
  overflow: hidden;
  display: flex;
  align-items: center;
  justify-content: center;
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

.description {
  color: var(--text-dim);
  font-size: 12px;
  display: -webkit-box;
  -webkit-line-clamp: 2;
  -webkit-box-orient: vertical;
  overflow: hidden;
}
</style>
