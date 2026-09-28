<script setup lang="ts">
import { toolbar } from '../../axis-catalog';
import { useToolpathPresentation } from '../../toolpath-view/presentation';
import { useChromeActions } from './actions';
import { TkButton, UiIcon } from '../../ui-system';
const ui = useChromeActions();
const preview = useToolpathPresentation();
const icons: Record<string, string> = {
  'machine.estop': 'octagon',
  'machine.power': 'power',
  'file.open': 'folder',
  'file.reload': 'refresh',
  'program.run': 'play',
  'program.step': 'step',
  'program.pause': 'pause',
  'program.stop': 'stop',
  'program.block-delete': 'skip',
  'program.optional': 'circle',
  'view.zoom-in': 'zoom-in',
  'view.zoom-out': 'zoom-out',
  'view.z': 'top',
  'view.z2': 'diamond',
  'view.x': 'side',
  'view.y': 'front',
  'view.p': 'cube',
  'view.rotate': 'orbit',
  'view.clear': 'eraser',
};
</script>

<template>
  <div class="axis-toolbar" role="toolbar" aria-label="常用操作工具栏">
    <template v-for="item in toolbar" :key="item.id">
      <span v-if="item.separator" class="toolbar-separator" role="separator" />
      <TkButton
        class="toolbar-button"
        :class="{
          'toolbar-estop': item.id === 'machine.estop',
          'toolbar-run': item.id === 'program.run',
        }"
        :aria-label="item.label"
        :title="item.label"
        :pressed="
          item.id === `view.${preview.choices.view}` ||
          (item.id === 'view.rotate' && preview.rotate)
        "
        @click="ui.activate(item.id, item.label)"
      >
        <UiIcon :name="icons[item.id] ?? 'cube'" />
        <span v-if="item.id === 'machine.estop'" class="toolbar-label">急停</span>
        <span v-if="item.id === 'program.run'" class="toolbar-label">运行</span>
      </TkButton>
    </template>
  </div>
</template>
