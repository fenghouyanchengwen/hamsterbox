<script setup lang="ts">
import type { Tag } from '../types/api'

withDefaults(
  defineProps<{
    tag: Tag
    /** 是否处于选中状态（用于筛选） */
    active?: boolean
    /** 是否显示删除按钮 */
    removable?: boolean
  }>(),
  { active: false, removable: false },
)

const emit = defineEmits<{
  (e: 'click'): void
  (e: 'remove'): void
}>()
</script>

<template>
  <span class="chip" :class="{ active }" @click="emit('click')">
    <span class="dot" :style="{ backgroundColor: tag.color }" />
    <span class="name">{{ tag.name }}</span>
    <span v-if="tag.entry_count != null" class="count">{{ tag.entry_count }}</span>
    <button
      v-if="removable"
      class="remove"
      type="button"
      title="移除筛选"
      @click.stop="emit('remove')"
    >
      ×
    </button>
  </span>
</template>

<style scoped>
.chip {
  display: inline-flex;
  align-items: center;
  gap: 5px;
  padding: 2px 8px;
  border: 1px solid var(--border);
  border-radius: 999px;
  background: var(--panel);
  font-size: 12px;
  line-height: 1.8;
  cursor: pointer;
  user-select: none;
  transition: border-color 0.15s, background 0.15s;
}

.chip:hover {
  border-color: var(--border-strong);
}

.chip.active {
  border-color: var(--accent);
  background: var(--accent-soft);
}

.dot {
  width: 7px;
  height: 7px;
  border-radius: 50%;
  flex: none;
}

.name {
  color: var(--text);
}

.count {
  color: var(--text-faint);
}

.remove {
  margin-left: 2px;
  padding: 0;
  border: none;
  background: transparent;
  color: var(--text-faint);
  line-height: 1;
  font-size: 14px;
}

.remove:hover {
  color: var(--danger);
}
</style>
