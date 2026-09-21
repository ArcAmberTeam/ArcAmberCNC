<script setup lang="ts">
const value = defineModel<number>({ required: true });
defineProps<{ label: string; max: number; unit?: string }>();
</script>

<template>
  <label class="tk-range">
    <span
      >{{ label }}: <span class="range-value">{{ value }}</span
      >{{ unit ?? '%' }}</span
    >
    <input v-model.number="value" type="range" min="0" :max="max" :aria-label="label" />
  </label>
</template>
