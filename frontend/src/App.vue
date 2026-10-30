<script setup lang="ts">
import { onMounted, ref } from 'vue'
import { getHealth } from './api/client'

const status = ref('检测中')

onMounted(async () => {
  try {
    const data = await getHealth()
    status.value = data.status === 'ok' ? '后端已连接' : '后端异常'
  } catch {
    status.value = '后端未启动'
  }
})
</script>

<template>
  <main class="app">
    <h1>仓鼠盒</h1>
    <p>本地优先的多媒体收藏管理工具</p>
    <p class="status">后端状态：{{ status }}</p>
  </main>
</template>
