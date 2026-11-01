<script setup lang="ts">
/**
 * 加载骨架屏。
 *
 * 为什么不用"加载中…"一行字：骨架屏保留布局轮廓，数据到位时不会跳一下，
 * 长列表里这个差别很明显。
 */
withDefaults(defineProps<{ rows?: number }>(), { rows: 4 })
</script>

<template>
  <div class="skeleton">
    <div v-for="row in rows" :key="row" class="row">
      <div class="block cover" />
      <div class="lines">
        <div class="block line w-60" />
        <div class="block line w-90" />
        <div class="block line w-40" />
      </div>
    </div>
  </div>
</template>

<style scoped>
.skeleton {
  display: flex;
  flex-direction: column;
  gap: 10px;
}

.row {
  display: flex;
  gap: 12px;
  padding: 12px;
  border: 1px solid var(--border);
  border-radius: var(--radius);
  background: var(--panel);
}

.block {
  border-radius: var(--radius-sm);
  background: linear-gradient(90deg, #eef1f5 25%, #f6f8fa 37%, #eef1f5 63%);
  background-size: 400% 100%;
  animation: shimmer 1.4s ease infinite;
}

.cover {
  flex: none;
  width: 56px;
  height: 74px;
}

.lines {
  flex: 1;
  display: flex;
  flex-direction: column;
  gap: 8px;
  padding-top: 4px;
}

.line {
  height: 12px;
}

.w-90 {
  width: 90%;
}

.w-60 {
  width: 60%;
}

.w-40 {
  width: 40%;
}

@keyframes shimmer {
  0% {
    background-position: 100% 50%;
  }
  100% {
    background-position: 0 50%;
  }
}
</style>
