<script setup lang="ts">
import { SORT_OPTIONS } from '../constants/labels'
import type { SortKey, TagRef } from '../types/api'
import TagChip from './TagChip.vue'

/**
 * 检索与筛选栏。
 *
 * 组件不自己保管 keyword / sort 的值，全部通过 props 从父组件拿、通过事件向上报告。
 * 这叫"受控组件"，好处是列表数据只在父组件里拉一次，状态不会两头各存一份。
 */
defineProps<{
  keyword: string
  sort: SortKey
  activeTags: TagRef[]
}>()

const emit = defineEmits<{
  (e: 'update:keyword', value: string): void
  (e: 'update:sort', value: SortKey): void
  (e: 'remove-tag', tagId: number): void
}>()

function handleKeyword(event: Event) {
  emit('update:keyword', (event.target as HTMLInputElement).value)
}

function handleSort(event: Event) {
  emit('update:sort', (event.target as HTMLSelectElement).value as SortKey)
}
</script>

<template>
  <div class="filter-bar">
    <input
      class="field search"
      type="search"
      placeholder="搜索标题或简介"
      :value="keyword"
      @input="handleKeyword"
    />

    <select class="field sort" :value="sort" @change="handleSort">
      <option v-for="option in SORT_OPTIONS" :key="option.value" :value="option.value">
        {{ option.label }}
      </option>
    </select>

    <div v-if="activeTags.length > 0" class="active-tags">
      <span class="faint">筛选：</span>
      <TagChip
        v-for="tag in activeTags"
        :key="tag.id"
        :name="tag.name"
        :color="tag.color"
        active
        removable
        @remove="emit('remove-tag', tag.id)"
      />
    </div>
  </div>
</template>

<style scoped>
.filter-bar {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
  align-items: center;
}

.search {
  flex: 1;
  min-width: 140px;
}

.sort {
  width: 96px;
  flex: none;
}

.active-tags {
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  gap: 6px;
  width: 100%;
}
</style>
