<script setup lang="ts">
const value = defineModel<number>({ required: true });
defineProps<{ label: string; max: number; unit?: string }>();
</script>
<template>
  <label class="tk-range" :style="{ '--range-fill': `${(value / max) * 100}%` }">
    <span class="range-caption"
      ><span>{{ label }}</span
      ><span class="range-reading"
        >{{ value }}<span class="range-unit">{{ unit?.trim() ?? '%' }}</span></span
      ></span
    >
    <input v-model.number="value" type="range" min="0" :max="max" :aria-label="label" />
  </label>
</template>
