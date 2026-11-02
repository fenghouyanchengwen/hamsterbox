<script setup lang="ts">
import EmptyState from '../components/EmptyState.vue'

/**
 * 设置页占位。
 *
 * 真实内容在 Alpha 第二阶段（F08 基础设置：库文件位置、重建索引），
 * 这里先占住入口，让侧栏导航可用。
 */
</script>

<template>
  <div class="settings">
    <header class="header">
      <h2 class="title">设置</h2>
    </header>

    <EmptyState
      title="设置页在 Alpha 第二阶段实现"
      description="计划中的内容：库文件位置、重建索引。任务已列在开发计划的 Alpha 第二阶段，负责人是成员六。"
    />

    <ul class="todo">
      <li>库文件位置：显示当前 library.db 路径，支持更换与备份</li>
      <li>重建索引：标题与标签索引损坏时的修复入口</li>
      <li>关于：版本号、开源许可</li>
    </ul>
  </div>
</template>

<style scoped>
.settings {
  height: 100%;
  display: flex;
  flex-direction: column;
  padding: 16px;
  gap: 12px;
}

.title {
  font-size: 16px;
}

.todo {
  margin: 0;
  padding-left: 18px;
  color: var(--text-dim);
  font-size: 13px;
}
</style>
