<script setup lang="ts">
import './program.css';
import { ref } from 'vue';
import {
  ContextMenuRoot,
  ContextMenuTrigger,
  ContextMenuPortal,
  ContextMenuContent,
  ContextMenuItem,
  ContextMenuSeparator,
} from 'reka-ui';
import { sampleProgram } from '../../axis-catalog';
import { useAxisPresentation } from '../../axis-presentation';
const dialogs = useAxisPresentation();
const selectedLine = ref(0);
</script>

<template>
  <ContextMenuRoot>
    <ContextMenuTrigger as-child>
      <section
        class="program-pane tk-inset"
        aria-label="G-code program"
        tabindex="0"
        @keydown.down.prevent="selectedLine = Math.min(sampleProgram.length - 1, selectedLine + 1)"
        @keydown.up.prevent="selectedLine = Math.max(0, selectedLine - 1)"
      >
        <div class="program-lines">
          <div
            v-for="(line, index) in sampleProgram"
            :key="index"
            class="program-line"
            :class="{ selected: index === selectedLine, comment: line.trimStart().startsWith('(') }"
            @click="selectedLine = index"
            @contextmenu="selectedLine = index"
          >
            <span class="line-number">{{ index + 1 }}</span
            ><span class="line-code">{{ line || ' ' }}</span>
          </div>
        </div>
      </section>
    </ContextMenuTrigger>
    <ContextMenuPortal
      ><ContextMenuContent class="tk-menu"
        ><ContextMenuItem class="menu-item" disabled>AXIS</ContextMenuItem
        ><ContextMenuSeparator class="menu-separator" /><ContextMenuItem
          class="menu-item"
          @select="dialogs.openDialog('program.run-line')"
          >Run from here</ContextMenuItem
        ></ContextMenuContent
      ></ContextMenuPortal
    >
  </ContextMenuRoot>
</template>
