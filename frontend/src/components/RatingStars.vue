<script setup lang="ts">
/**
 * 五颗星评分控件。
 *
 * 规则（frontend/README.md）：
 * - 标签 rating_enabled=false 时，控件必须禁用，而不是隐藏
 * - 未评分时 rating 为 null
 * - 点当前分数可取消评分
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

const stars = [1, 2, 3, 4, 5]

function pick(star: number) {
  if (props.disabled) {
    return
  }
  emit('change', props.rating === star ? null : star)
}
</script>

<template>
  <span class="stars" :class="{ disabled }" :title="disabled ? '该标签未开启评分' : ''">
    <button
      v-for="star in stars"
      :key="star"
      class="star"
      :class="{ filled: rating !== null && star <= rating }"
      type="button"
      :disabled="disabled"
      @click="pick(star)"
    >
      ★
    </button>
    <span v-if="rating === null" class="empty-hint">未评分</span>
  </span>
</template>

<style scoped>
.stars {
  display: inline-flex;
  align-items: center;
  gap: 1px;
}

.star {
  padding: 0 1px;
  border: none;
  background: transparent;
  color: #d7dbe2;
  font-size: 17px;
  line-height: 1;
  transition: color 0.12s, transform 0.12s;
}

.star:hover:not(:disabled) {
  transform: scale(1.15);
}

.star.filled {
  color: var(--warn);
}

.stars.disabled .star {
  cursor: not-allowed;
}

.stars.disabled .star.filled {
  color: #e3d8b4;
}

.empty-hint {
  margin-left: 6px;
  color: var(--text-faint);
  font-size: 12px;
}
</style>
