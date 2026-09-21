<script setup lang="ts">
import { toolbar } from '../../axis-catalog';
import { useToolpathPresentation } from '../../toolpath-view/presentation';
import { useChromeActions } from './actions';
import { TkButton } from '../../ui-system';
const ui = useChromeActions();
const preview = useToolpathPresentation();
</script>

<template>
  <div class="axis-toolbar" role="toolbar" aria-label="AXIS controls">
    <template v-for="item in toolbar" :key="item.id">
      <span v-if="item.separator" class="toolbar-separator" role="separator" />
      <TkButton
        class="toolbar-button"
        :aria-label="item.label"
        :title="item.label"
        :pressed="
          item.id === 'machine.estop' ||
          item.id === `view.${preview.choices.view}` ||
          (item.id === 'view.rotate' && preview.rotate)
        "
        @click="ui.activate(item.id, item.label)"
      >
        <img :src="`/axis/${item.icon}.gif`" alt="" draggable="false" />
      </TkButton>
    </template>
  </div>
</template>
