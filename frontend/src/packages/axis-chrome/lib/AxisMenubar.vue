<script setup lang="ts">
import './chrome.css';
import { MenubarRoot, MenubarMenu, MenubarTrigger, MenubarPortal, MenubarContent } from 'reka-ui';
import { menus } from '../../axis-catalog';
import MenuEntries from './MenuEntries.vue';
</script>

<template>
  <MenubarRoot class="axis-menubar" aria-label="Application menu">
    <MenubarMenu v-for="menu in menus" :key="menu.id" :value="menu.id">
      <MenubarTrigger class="menu-trigger"
        ><u>{{ menu.label[0] }}</u
        >{{ menu.label.slice(1) }}</MenubarTrigger
      >
      <MenubarPortal>
        <MenubarContent class="tk-menu" align="start" :side-offset="0" :collision-padding="4">
          <MenuEntries :items="menu.children!" />
        </MenubarContent>
      </MenubarPortal>
    </MenubarMenu>
  </MenubarRoot>
</template>
