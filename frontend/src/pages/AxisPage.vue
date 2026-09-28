<script setup lang="ts">
import { onMounted, onUnmounted, ref } from 'vue';
import { AxisMenubar, AxisToolbar, AxisDialogs } from '../packages/axis-chrome';
import { ManualControl } from '../packages/manual-control';
import { ToolpathView } from '../packages/toolpath-view';
import { ProgramView } from '../packages/program-view';
import { fixture } from '../packages/axis-catalog';
import { useManualPresentation } from '../packages/manual-control/presentation';
import { useToolpathPresentation } from '../packages/toolpath-view/presentation';
import { useAxisPresentation } from '../packages/axis-presentation';
import { UiIcon } from '../packages/ui-system';
const dialogs = useAxisPresentation();
const manual = useManualPresentation();
const preview = useToolpathPresentation();
const programHeight = ref(184);
const dragging = ref(false);
const workspace = ref<HTMLElement>();
const maxProgramHeight = ref(340);
let resizeObserver: ResizeObserver | undefined;
function setProgramHeight(height: number) {
  programHeight.value = Math.max(90, Math.min(maxProgramHeight.value, height));
}

function resize(event: PointerEvent) {
  if (dragging.value && workspace.value)
    setProgramHeight(workspace.value.getBoundingClientRect().bottom - event.clientY);
}
function startResize(event: PointerEvent) {
  dragging.value = true;
  (event.currentTarget as HTMLElement).setPointerCapture(event.pointerId);
}
function shortcuts(event: KeyboardEvent) {
  if (dialogs.dialog) return;
  if (event.key === 'F3' || event.key === 'F5') {
    event.preventDefault();
    manual.controlTab = event.key === 'F3' ? 'manual' : 'mdi';
    return;
  }
  if (
    event.target instanceof HTMLInputElement ||
    event.target instanceof HTMLSelectElement ||
    event.target instanceof HTMLTextAreaElement ||
    (event.target as HTMLElement)?.closest('[role="menu"], [role="menubar"]')
  )
    return;
  if (!event.ctrlKey && !event.metaKey && !event.altKey) {
    if (['x', 'y', 'z'].includes(event.key.toLowerCase()))
      manual.selectedAxis = event.key.toUpperCase();
    if (event.key.toLowerCase() === 'v') {
      const views = ['p', 'z', 'z2', 'x', 'y'];
      preview.choices.view = views[(views.indexOf(preview.choices.view!) + 1) % views.length]!;
    }
    if (event.key.toLowerCase() === 'd') preview.rotate = !preview.rotate;
    if (event.key === '!') preview.choices.units = preview.choices.units === 'mm' ? 'inch' : 'mm';
    if (event.key === '@')
      preview.choices.position = preview.choices.position === 'actual' ? 'commanded' : 'actual';
    if (event.key === '#')
      preview.choices.coordinates =
        preview.choices.coordinates === 'relative' ? 'machine' : 'relative';
  }
}
onMounted(() => {
  window.addEventListener('keydown', shortcuts);
  resizeObserver = new ResizeObserver(([entry]) => {
    if (!entry) return;
    // Keep coordinates and a useful canvas visible while the program pane grows.
    maxProgramHeight.value = Math.max(90, Math.min(340, entry.contentRect.height - 247));
    setProgramHeight(programHeight.value);
  });
  if (workspace.value) resizeObserver.observe(workspace.value);
});
onUnmounted(() => {
  window.removeEventListener('keydown', shortcuts);
  resizeObserver?.disconnect();
});
</script>

<template>
  <main class="axis-window" :style="{ '--program-height': `${programHeight}px` }">
    <header class="workspace-header">
      <div class="workspace-brand">
        <strong>BetterLinuxCNC</strong><span class="workspace-edition">工作空间</span>
      </div>
      <div class="workspace-location">
        <span>机床</span><UiIcon name="chevron" /><strong>操作台</strong>
      </div>
      <AxisMenubar />
    </header>
    <div class="workspace-context">
      <div class="context-title">
        三轴加工<span class="context-divider">/</span
        ><span class="context-file"><UiIcon name="file" />{{ fixture.fileName }}</span>
      </div>
    </div>
    <AxisToolbar />
    <div ref="workspace" class="workspace-panes">
      <ManualControl />
      <ToolpathView />
      <div
        class="pane-sash"
        role="separator"
        aria-label="调整程序区高度"
        aria-orientation="horizontal"
        :aria-valuenow="programHeight"
        :aria-valuemin="90"
        :aria-valuemax="maxProgramHeight"
        tabindex="0"
        @pointerdown="startResize"
        @pointermove="resize"
        @pointerup="dragging = false"
        @pointercancel="dragging = false"
        @keydown.up.prevent="setProgramHeight(programHeight + 10)"
        @keydown.down.prevent="setProgramHeight(programHeight - 10)"
      >
        <span />
      </div>
      <ProgramView />
    </div>
    <AxisDialogs />
  </main>
</template>

<style scoped>
.axis-window {
  display: grid;
  grid-template-rows: 52px 44px 50px minmax(400px, 1fr);
  width: 100%;
  height: 100dvh;
  min-height: 640px;
  min-width: 760px;
  overflow: hidden;
  background: var(--surface-base);
}
.workspace-header {
  display: flex;
  align-items: center;
  border-bottom: 1px solid var(--border-subtle);
  background: var(--surface-sidebar);
  padding-right: 14px;
  min-width: 0;
}
.workspace-brand {
  display: flex;
  align-items: center;
  gap: 10px;
  width: 296px;
  flex-shrink: 0;
  padding: 0 18px;
}
.workspace-brand strong {
  font-size: 13px;
  font-weight: 600;
  letter-spacing: -0.3px;
}
.workspace-edition {
  font-size: 10px;
  color: var(--text-muted);
  margin-left: auto;
}
.workspace-location {
  display: flex;
  align-items: center;
  gap: 9px;
  color: var(--text-muted);
  padding: 0 20px;
  flex: 1;
  font-size: 12px;
}
.workspace-location strong {
  color: var(--text-primary);
  font-weight: 500;
}
.workspace-location .ui-icon {
  width: 12px;
  height: 12px;
}
.workspace-context {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
  padding: 0 20px;
  border-bottom: 1px solid var(--border-subtle);
}
.context-title,
.context-file {
  display: flex;
  align-items: center;
  gap: 10px;
}
.context-title {
  font-size: 12px;
  font-weight: 500;
}
.context-file {
  color: var(--text-secondary);
  font-family: var(--mono);
  font-size: 11px;
}
.context-file .ui-icon {
  width: 14px;
}
.context-divider {
  color: #555761;
  margin: 0 5px;
}
.workspace-panes {
  display: grid;
  grid-template-columns: 296px minmax(0, 1fr);
  grid-template-rows: minmax(200px, 1fr) 7px var(--program-height);
  min-height: 0;
}
.pane-sash {
  grid-column: 2;
  position: relative;
  background: var(--surface-base);
  cursor: row-resize;
  touch-action: none;
  border-top: 1px solid var(--border-subtle);
}
.pane-sash span {
  display: block;
  width: 26px;
  height: 2px;
  border-radius: 2px;
  background: #41434c;
  position: absolute;
  left: calc(50% - 13px);
  top: 2px;
}
.pane-sash:hover span {
  background: var(--accent);
}
.pane-sash:focus-visible {
  outline-offset: -2px;
  z-index: 1;
}
@media (max-width: 900px) {
  .workspace-panes {
    grid-template-columns: 264px minmax(0, 1fr);
  }
  .workspace-brand {
    width: 264px;
  }
  .workspace-edition {
    display: none;
  }
  .workspace-location {
    padding: 0 14px;
  }
}
</style>
