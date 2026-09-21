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
import { LocalServiceStatus } from '../packages/controller-session';
const dialogs = useAxisPresentation();
const manual = useManualPresentation();
const preview = useToolpathPresentation();
const programHeight = ref(150);
const dragging = ref(false);

function resize(event: PointerEvent) {
  if (dragging.value)
    programHeight.value = Math.max(90, Math.min(340, window.innerHeight - event.clientY - 28));
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
onMounted(() => window.addEventListener('keydown', shortcuts));
onUnmounted(() => window.removeEventListener('keydown', shortcuts));
</script>

<template>
  <main class="axis-window" :style="{ '--program-height': `${programHeight}px` }">
    <header class="window-titlebar">
      <img src="/axis/axis-16x16.png" alt="" /><span class="window-title"
        >{{ fixture.fileName }} — AXIS {{ fixture.version }} · 模拟机床</span
      ><span class="static-label" title="界面演示，尚未连接控制器">界面演示</span>
      <LocalServiceStatus />
      <div class="window-controls" aria-hidden="true">
        <span>−</span><span>□</span><span>×</span>
      </div>
    </header>
    <AxisMenubar />
    <AxisToolbar />
    <div class="workspace-panes"><ManualControl /><ToolpathView /></div>
    <div
      class="pane-sash"
      role="separator"
      aria-label="调整程序区高度"
      aria-orientation="horizontal"
      :aria-valuenow="programHeight"
      :aria-valuemin="90"
      :aria-valuemax="340"
      tabindex="0"
      @pointerdown="startResize"
      @pointermove="resize"
      @pointerup="dragging = false"
      @pointercancel="dragging = false"
      @keydown.up.prevent="programHeight = Math.min(340, programHeight + 10)"
      @keydown.down.prevent="programHeight = Math.max(90, programHeight - 10)"
    >
      <span />
    </div>
    <ProgramView />
    <footer class="statusbar" aria-label="机床状态示例">
      <span>{{ fixture.taskState }}</span
      ><span>{{ fixture.tool }}</span
      ><span class="position-status"
        >位置： {{ preview.choices.coordinates === 'relative' ? '工件坐标' : '机床坐标' }}
        {{ preview.choices.position === 'actual' ? '实际位置' : '指令位置' }}</span
      >
    </footer>
    <AxisDialogs />
  </main>
</template>

<style scoped>
.axis-window {
  display: grid;
  grid-template-rows: 29px 26px 39px minmax(260px, 1fr) 7px var(--program-height) 25px;
  width: 100%;
  height: 100dvh;
  min-height: 640px;
  min-width: 760px;
  overflow: hidden;
  background: #d9d9d9;
  border: 1px solid #8e969e;
}
.window-titlebar {
  display: flex;
  align-items: center;
  gap: 7px;
  background: linear-gradient(#668fb7, #426991);
  color: #fff;
  padding: 0 6px;
  white-space: nowrap;
  overflow: hidden;
  text-shadow: 0 1px #375472;
}
.window-titlebar img {
  width: 16px;
  height: 16px;
}
.window-title {
  overflow: hidden;
  text-overflow: ellipsis;
}
.static-label {
  font-size: 11px;
  letter-spacing: 0.6px;
  color: #e9eff6;
  margin-left: auto;
  padding: 2px 5px;
  border: 1px solid #ffffff45;
  line-height: 13px;
}
.window-controls {
  display: flex;
  gap: 6px;
  margin-left: 9px;
  align-items: center;
  font-size: 20px;
  line-height: 18px;
}
.window-controls > span {
  text-align: center;
  width: 15px;
}
.workspace-panes {
  display: grid;
  grid-template-columns: 318px minmax(0, 1fr);
  gap: 4px;
  padding: 3px 4px 0;
  min-height: 0;
}
.pane-sash {
  position: relative;
  background: #d9d9d9;
  cursor: row-resize;
  touch-action: none;
  border-top: 1px solid #fff;
  border-bottom: 1px solid #a5a5a5;
}
.pane-sash span {
  display: block;
  width: 10px;
  height: 6px;
  border: 1px solid;
  border-color: #fff #888 #888 #fff;
  position: absolute;
  right: 28px;
  top: 0;
}
.statusbar {
  display: flex;
  gap: 3px;
  padding: 3px 2px 1px;
  line-height: 18px;
  font-size: 12px;
}
.statusbar > span {
  border: 1px solid;
  border-color: #999 #fff #fff #999;
  padding: 0 5px;
}
.statusbar > span:first-child {
  min-width: 114px;
}
.statusbar > span:nth-child(2) {
  flex: 1;
}
.position-status {
  min-width: 220px;
}
@media (max-width: 900px) {
  .workspace-panes {
    grid-template-columns: 307px minmax(0, 1fr);
  }
  .static-label {
    font-size: 11px;
  }
  .window-title {
    font-size: 12px;
  }
}
</style>
