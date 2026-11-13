<script setup lang="ts">
/**
 * 错误提示条。
 *
 * 约定：错误必须给出可执行动作（重试），不能只显示一行红字。
 * 后端返回的是 { code, message, details }，一般把 code 和 message 一起显示，
 * 方便排查时直接对人说"我这儿报 RATING_OUT_OF_RANGE"。
 */
withDefaults(
  defineProps<{
    message: string
    retryText?: string
  }>(),
  { retryText: '重试' },
)

const emit = defineEmits<{
  (e: 'retry'): void
}>()
</script>

<template>
  <div class="banner" role="alert">
    <span class="mark">!</span>
    <span class="message">{{ message }}</span>
    <button class="btn btn-ghost retry" type="button" @click="emit('retry')">
      {{ retryText }}
    </button>
  </div>
</template>

<style scoped>
.banner {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 8px 12px;
  border: 1px solid #f3c2c4;
  border-radius: var(--radius-sm);
  background: var(--danger-soft);
  color: #a5282c;
  font-size: 13px;
}

.mark {
  flex: none;
  width: 18px;
  height: 18px;
  display: inline-flex;
  align-items: center;
  justify-content: center;
  border-radius: 50%;
  background: var(--danger);
  color: #fff;
  font-size: 12px;
  font-weight: 600;
}

.message {
  flex: 1;
}

.retry {
  color: #a5282c;
}
</style>
