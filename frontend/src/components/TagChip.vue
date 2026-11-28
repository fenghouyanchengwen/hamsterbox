<script setup lang="ts">
/**
 * 标签胶囊。
 *
 * 注意 Tag 本身没有颜色（契约 §3.3：Tag 不含 color），颜色在所属分类上，
 * 所以这里直接收 name + color，由调用方把标签和分类拼好再传进来。
 */
withDefaults(
  defineProps<{
    name: string
    /** 来自所属分类的本地颜色，可为空 */
    color?: string | null
    active?: boolean
    removable?: boolean
    /** 数字角标，例如该标签下的条目数 */
    count?: number | null
  }>(),
  { color: null, active: false, removable: false, count: null },
)

const emit = defineEmits<{
  (e: 'click'): void
  (e: 'remove'): void
}>()
</script>

<template>
  <span class="chip" :class="{ active }" @click="emit('click')">
    <span class="dot" :style="{ backgroundColor: color ?? 'var(--border-strong)' }" />
    <span class="name">{{ name }}</span>
    <span v-if="count != null" class="count">{{ count }}</span>
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
