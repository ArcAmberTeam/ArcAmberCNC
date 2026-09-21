<script setup lang="ts">
import {
  DialogRoot,
  DialogPortal,
  DialogOverlay,
  DialogContent,
  DialogTitle,
  DialogDescription,
  DialogClose,
} from 'reka-ui';
defineProps<{ title: string; description: string }>();
const emit = defineEmits<{ close: [] }>();
</script>

<template>
  <DialogRoot :open="true" @update:open="!$event && emit('close')">
    <DialogPortal>
      <DialogOverlay class="tk-dialog-overlay" />
      <DialogContent class="tk-dialog">
        <div class="tk-dialog-titlebar">
          <DialogTitle>{{ title }}</DialogTitle>
          <DialogClose class="dialog-x" aria-label="关闭对话框">×</DialogClose>
        </div>
        <div class="tk-dialog-body">
          <DialogDescription class="dialog-description">{{ description }}</DialogDescription>
          <slot />
        </div>
      </DialogContent>
    </DialogPortal>
  </DialogRoot>
</template>
