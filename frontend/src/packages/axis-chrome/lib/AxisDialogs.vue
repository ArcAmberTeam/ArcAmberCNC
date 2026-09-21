<script setup lang="ts">
import { computed, ref, watch } from 'vue';
import { coordinateSystems, fixture, quickReference, sampleProgram } from '../../axis-catalog';
import { useAxisPresentation } from '../../axis-presentation';
import { TkButton, TkDialog } from '../../ui-system';
const ui = useAxisPresentation();
const value = ref('0.0');
const system = ref('G54');
const description = computed(() => {
  if (ui.dialog?.id === 'help.about') return 'AXIS — LinuxCNC graphical user interface';
  if (ui.dialog?.id === 'help.reference')
    return 'AXIS keyboard reference. This preview enables F3, F5 and display shortcuts only.';
  if (ui.dialog?.id === 'file.properties') return 'Properties of the bundled display sample.';
  return 'Static UI preview — no controller connected. This action is not implemented.';
});
watch(
  () => ui.dialog?.id,
  () => {
    value.value = '0.0';
  },
);
</script>

<template>
  <TkDialog
    v-if="ui.dialog"
    :title="ui.dialog.title"
    :description="description"
    @close="ui.dialog = null"
  >
    <div v-if="ui.dialog.id === 'help.about'" class="about-dialog">
      <img src="/axis/axis-48x48.png" alt="AXIS" />
      <div>
        <strong>AXIS {{ fixture.version }}</strong>
        <p>LinuxCNC-HAL-SIM-AXIS</p>
        <p>Web interface study · UI only</p>
        <p>Based on this repository’s Tcl / Python interface.</p>
      </div>
    </div>
    <dl v-else-if="ui.dialog.id === 'help.reference'" class="shortcut-list">
      <template v-for="[key, action] in quickReference" :key="key"
        ><dt>{{ key }}</dt>
        <dd>{{ action }}</dd></template
      >
    </dl>
    <dl v-else-if="ui.dialog.id === 'file.properties'" class="property-list">
      <dt>File</dt>
      <dd>{{ fixture.fileName }}</dd>
      <dt>Lines</dt>
      <dd>{{ sampleProgram.length }}</dd>
      <dt>Source</dt>
      <dd>Bundled AXIS splash G-code</dd>
      <dt>Preview</dt>
      <dd>Static illustration; no G-code interpreter</dd>
    </dl>
    <div
      v-else-if="
        ui.dialog.id === 'file.open' ||
        ui.dialog.id === 'file.open-sample' ||
        ui.dialog.id === 'file.save'
      "
      class="file-dialog"
    >
      <label>Directory: <input value="/linuxcnc/nc_files" readonly /></label>
      <div class="tk-inset file-list">
        <span>📁&nbsp; ../</span><span class="selected-file">▤&nbsp; axis.ngc</span>
      </div>
      <label>File name: <input :value="fixture.fileName" readonly /></label>
      <label
        >Files of type:
        <select aria-label="File type">
          <option>G-code files (*.ngc)</option>
          <option>All files (*)</option>
        </select></label
      >
    </div>
    <div
      v-else-if="ui.dialog.id === 'machine.touch-off' || ui.dialog.id === 'tool.touch-off'"
      class="touch-dialog"
    >
      <p>
        Set {{ ui.dialog.axis }}
        {{ ui.dialog.id.startsWith('tool') ? 'tool offset' : 'coordinate' }} to:
      </p>
      <label>Value <input v-model="value" inputmode="decimal" /></label>
      <label
        >Coordinate system
        <select v-model="system">
          <option v-for="item in coordinateSystems" :key="item">{{ item }}</option>
        </select></label
      >
    </div>
    <div v-else-if="ui.dialog.id === 'view.grid-custom'" class="touch-dialog">
      <label>Grid size <input v-model="value" inputmode="decimal" /> mm</label>
    </div>
    <div v-else-if="ui.dialog.id === 'tool.edit'" class="tk-inset tool-table-wrap">
      <table class="tool-table">
        <thead>
          <tr>
            <th
              v-for="label in ['Tool', 'Pocket', 'X', 'Y', 'Z', 'Diameter', 'Comment']"
              :key="label"
            >
              {{ label }}
            </th>
          </tr>
        </thead>
        <tbody>
          <tr>
            <td colspan="7">No tool table connected</td>
          </tr>
        </tbody>
      </table>
    </div>
    <div v-else-if="ui.dialog.id === 'show.pyvcp'" class="placeholder-detail">
      PyVCP panels are machine-specific. No custom panel is configured for this XYZ preview.
    </div>
    <div class="dialog-actions"><TkButton @click="ui.dialog = null">Close</TkButton></div>
  </TkDialog>
</template>
