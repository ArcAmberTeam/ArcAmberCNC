<script setup lang="ts">
defineProps<{ pressed?: boolean }>();
</script>

<template>
  <button type="button" class="tk-button" :class="{ 'is-pressed': pressed }"><slot /></button>
</template>
