<script setup lang="ts">
import { onMounted, onUnmounted, ref } from 'vue';
import { checkLocalService, isDesktop } from './client';

const desktop = isDesktop();
const label = ref('正在检查本地服务');
const detail = ref('仅检查本地通信，机床控制尚未接入');
const checking = ref(false);
let timer: ReturnType<typeof setInterval> | undefined;
let disposed = false;

async function refresh() {
  if (checking.value || disposed) return;
  checking.value = true;
  try {
    await checkLocalService();
    if (!disposed) {
      label.value = '本地服务已连接';
      detail.value = '本地通信正常；机床控制尚未接入';
    }
  } catch {
    if (!disposed) {
      label.value = '本地服务未连接';
      detail.value = '请启动 Python 本地服务；点击重新检查。机床控制尚未接入';
    }
  } finally {
    if (!disposed) checking.value = false;
  }
}

onMounted(() => {
  if (desktop) {
    void refresh();
    timer = setInterval(() => void refresh(), 5000);
  }
});
onUnmounted(() => {
  disposed = true;
  clearInterval(timer);
});
</script>

<template>
  <button
    v-if="desktop"
    class="service-status"
    :title="detail"
    :disabled="checking"
    aria-label="检查本地服务连接"
    @click="refresh"
  >
    {{ label }}
  </button>
</template>

<style scoped>
.service-status {
  font-size: 11px;
  color: inherit;
  padding: 1px 4px;
  border: 1px solid #ffffff45;
  white-space: nowrap;
}
.service-status:focus-visible {
  outline: 1px solid white;
}
</style>
