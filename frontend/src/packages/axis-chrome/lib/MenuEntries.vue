<script setup lang="ts">
import {
  MenubarItem,
  MenubarSeparator,
  MenubarSub,
  MenubarSubTrigger,
  MenubarSubContent,
  MenubarPortal,
  MenubarCheckboxItem,
  MenubarRadioGroup,
  MenubarRadioItem,
} from 'reka-ui';
import type { MenuItem } from '../../axis-catalog/model';
import { useChromeActions } from './actions';
defineProps<{ items: MenuItem[] }>();
const ui = useChromeActions();
</script>

<template>
  <template v-for="item in items" :key="item.id">
    <MenubarSeparator v-if="item.kind === 'separator'" class="menu-separator" />
    <MenubarSub v-else-if="item.children">
      <MenubarSubTrigger class="menu-item"
        ><span class="menu-mark" aria-hidden="true" /><span>{{ item.label }}</span
        ><span class="menu-shortcut" aria-hidden="true">▸</span></MenubarSubTrigger
      >
      <MenubarPortal>
        <MenubarSubContent
          class="tk-menu"
          :side-offset="-3"
          :align-offset="-3"
          :collision-padding="4"
        >
          <MenuEntries :items="item.children" />
        </MenubarSubContent>
      </MenubarPortal>
    </MenubarSub>
    <MenubarCheckboxItem
      v-else-if="item.kind === 'check'"
      :model-value="ui.isSelected(item)"
      class="menu-item"
      @select="ui.activate(item.id)"
    >
      <span class="menu-mark menu-check" aria-hidden="true">{{
        ui.isSelected(item) ? '✓' : ''
      }}</span
      ><span>{{ item.label }}</span
      ><span class="menu-shortcut" aria-hidden="true">{{ item.shortcut }}</span>
    </MenubarCheckboxItem>
    <MenubarRadioGroup
      v-else-if="item.kind === 'radio'"
      :model-value="ui.selectedValue(item.group!)"
    >
      <MenubarRadioItem :value="item.value!" class="menu-item" @select="ui.activate(item.id)">
        <span class="menu-mark" aria-hidden="true">{{ ui.isSelected(item) ? '●' : '○' }}</span
        ><span>{{ item.label }}</span
        ><span class="menu-shortcut" aria-hidden="true">{{ item.shortcut }}</span>
      </MenubarRadioItem>
    </MenubarRadioGroup>
    <MenubarItem v-else class="menu-item" @select="ui.activate(item.id)">
      <span class="menu-mark" aria-hidden="true" /><span>{{ item.label }}</span
      ><span class="menu-shortcut" aria-hidden="true">{{ item.shortcut }}</span>
    </MenubarItem>
  </template>
</template>
