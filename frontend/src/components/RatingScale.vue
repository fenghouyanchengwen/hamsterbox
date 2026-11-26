<script setup lang="ts">
import { RATING_MAX, RATING_MIN } from '../types/api'

/**
 * 1 至 10 分评分控件。
 *
 * 契约（docs/tag-rating-contract.md §2.5）：评分是 null 或 1 至 10 的整数，
 * 不是早期的 1 至 5。所以这里渲染 10 个刻度，而不是五颗星。
 *
 * 规则：
 * - 未评分时 rating 为 null，显示"未评分"
 * - 点当前分数表示取消评分，提交 null
 * - 只接受整数，不做半档
 * - 组件不自己发请求，只通过 change 事件向上报值
 */
const props = withDefaults(
  defineProps<{
    rating: number | null
    disabled?: boolean
  }>(),
  { disabled: false },
)

const emit = defineEmits<{
  (e: 'change', value: number | null): void
}>()

const stops: number[] = []
for (let value = RATING_MIN; value <= RATING_MAX; value += 1) {
  stops.push(value)
}

function pick(value: number) {
  if (props.disabled) {
    return
  }
  emit('change', props.rating === value ? null : value)
}
</script>

<template>
  <span class="scale" :class="{ disabled }">
    <button
      v-for="stop in stops"
      :key="stop"
      class="stop"
      :class="{ filled: rating !== null && stop <= rating }"
      type="button"
      :disabled="disabled"
      :aria-label="`${stop} 分`"
      @click="pick(stop)"
    >
      {{ stop }}
    </button>
    <span v-if="rating === null" class="hint">未评分</span>
  </span>
</template>

<style scoped>
.scale {
  display: inline-flex;
  align-items: center;
  gap: 2px;
}

.stop {
  width: 20px;
  height: 20px;
  padding: 0;
  border: 1px solid var(--border);
  border-radius: 4px;
  background: var(--panel);
  color: var(--text-faint);
  font-size: 11px;
  line-height: 1;
  transition: background 0.12s, color 0.12s, border-color 0.12s;
}

.stop:hover:not(:disabled) {
  border-color: var(--accent);
  color: var(--accent);
}

.stop.filled {
  border-color: var(--warn);
  background: var(--warn);
  color: #4a3400;
  font-weight: 600;
}

.scale.disabled .stop {
  cursor: not-allowed;
  opacity: 0.55;
}

.scale.disabled .stop.filled {
  background: var(--border-strong);
  border-color: var(--border-strong);
  color: var(--panel);
}

.hint {
  margin-left: 6px;
  color: var(--text-faint);
  font-size: 12px;
}
</style>
