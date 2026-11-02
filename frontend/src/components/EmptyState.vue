<script setup lang="ts">
/**
 * 空数据状态。
 *
 * 四态里"空"这一态最容易被漏掉，但它是新用户看到的第一屏。
 * 所以除了说明没有数据，还要给出下一步该做什么。
 */
defineProps<{
  title: string
  description?: string
  /** 可选的操作按钮文案，配合 @action 使用 */
  actionText?: string
}>()

const emit = defineEmits<{
  (e: 'action'): void
}>()
</script>

<template>
  <div class="empty">
    <div class="icon">▤</div>
    <h3 class="title">{{ title }}</h3>
    <p v-if="description" class="description">{{ description }}</p>
    <slot />
    <button
      v-if="actionText"
      class="btn btn-primary action"
      type="button"
      @click="emit('action')"
    >
      {{ actionText }}
    </button>
  </div>
</template>

<style scoped>
.empty {
  height: 100%;
  min-height: 220px;
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  gap: 8px;
  padding: 32px;
  text-align: center;
}

.icon {
  font-size: 32px;
  color: var(--border-strong);
  line-height: 1;
}

.title {
  font-size: 15px;
}

.description {
  max-width: 320px;
  color: var(--text-dim);
  font-size: 13px;
}

.action {
  margin-top: 8px;
}
</style>
