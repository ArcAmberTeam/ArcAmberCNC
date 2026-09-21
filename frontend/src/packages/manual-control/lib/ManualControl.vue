<script setup lang="ts">
import './manual.css';
import { ref } from 'vue';
import { useManualPresentation } from './presentation';
import { TabsRoot, TabsList, TabsTrigger, TabsContent } from 'reka-ui';
import { axes, fixture } from '../../axis-catalog';
import { useAxisPresentation } from '../../axis-presentation';
import { TkButton, TkRange } from '../../ui-system';
const dialogs = useAxisPresentation();
const ui = useManualPresentation();
const increment = ref('Continuous');
const mdi = ref('');
const feed = ref(100);
const rapid = ref(100);
const spindle = ref(100);
const jog = ref(600);
const maxVelocity = ref(3000);
</script>

<template>
  <section class="control-column" aria-label="Machine controls">
    <TabsRoot v-model="ui.controlTab" class="control-tabs">
      <TabsList class="tk-tabs" aria-label="Control mode">
        <TabsTrigger value="manual" class="tk-tab">Manual Control [F3]</TabsTrigger>
        <TabsTrigger value="mdi" class="tk-tab">MDI [F5]</TabsTrigger>
      </TabsList>
      <TabsContent value="manual" class="control-panel tk-panel" tabindex="-1">
        <div class="manual-grid">
          <span class="control-label">{{ ui.mode === 'joint' ? 'Joint:' : 'Axis:' }}</span>
          <div class="axis-radios" role="radiogroup" aria-label="Selected axis">
            <label v-for="(axis, index) in axes" :key="axis"
              ><input v-model="ui.selectedAxis" type="radio" :value="axis" name="axis" />{{
                ui.mode === 'joint' ? index : axis
              }}</label
            >
          </div>
          <div class="manual-actions">
            <div class="jog-row flex items-center">
              <TkButton
                aria-label="Jog negative"
                @click="dialogs.openDialog('machine.jog-minus', `Jog ${ui.selectedAxis} −`)"
                >−</TkButton
              >
              <TkButton
                aria-label="Jog positive"
                @click="dialogs.openDialog('machine.jog-plus', `Jog ${ui.selectedAxis} +`)"
                >+</TkButton
              >
              <select v-model="increment" aria-label="Jog increment">
                <option>Continuous</option>
                <option>0.1000</option>
                <option>0.0100</option>
                <option>0.0010</option>
                <option>0.0001</option>
              </select>
            </div>
            <div class="homing-buttons">
              <TkButton @click="dialogs.openDialog('machine.home-all')">Home All</TkButton
              ><TkButton
                @click="dialogs.openDialog('machine.touch-off', 'Touch Off', ui.selectedAxis)"
                >Touch Off</TkButton
              ><TkButton
                class="tool-touch"
                @click="dialogs.openDialog('tool.touch-off', 'Tool Touch Off', ui.selectedAxis)"
                >Tool Touch Off</TkButton
              >
            </div>
            <label class="check-label"
              ><input
                type="checkbox"
                :checked="false"
                @click.prevent="dialogs.openDialog('machine.override-limits', 'Override Limits')"
              />Override Limits</label
            >
          </div>
          <span class="control-label spindle-label">Spindle:</span>
          <div class="spindle-controls">
            <div class="flex items-center">
              <TkButton
                aria-label="Spindle counterclockwise"
                title="Spindle counterclockwise"
                @click="dialogs.openDialog('spindle.ccw', 'Spindle counterclockwise')"
                ><img src="/axis/spindle_ccw.gif" alt=""
              /></TkButton>
              <TkButton
                class="spindle-stop"
                :pressed="true"
                @click="dialogs.openDialog('spindle.stop', 'Stop spindle')"
                >Stop</TkButton
              >
              <TkButton
                aria-label="Spindle clockwise"
                title="Spindle clockwise"
                @click="dialogs.openDialog('spindle.cw', 'Spindle clockwise')"
                ><img src="/axis/spindle_cw.gif" alt=""
              /></TkButton>
            </div>
            <div class="flex">
              <TkButton
                aria-label="Decrease spindle speed"
                @click="dialogs.openDialog('spindle.decrease', 'Decrease spindle speed')"
                >−</TkButton
              ><TkButton
                aria-label="Increase spindle speed"
                @click="dialogs.openDialog('spindle.increase', 'Increase spindle speed')"
                >+</TkButton
              >
            </div>
            <label class="check-label"
              ><input
                type="checkbox"
                :checked="false"
                @click.prevent="dialogs.openDialog('spindle.brake', 'Brake')"
              />Brake</label
            >
          </div>
          <span class="control-label coolant-label">Coolant:</span>
          <div class="coolant-controls">
            <label v-for="label in ['Mist', 'Flood']" :key="label" class="check-label"
              ><input
                type="checkbox"
                :checked="false"
                @click.prevent="dialogs.openDialog(`coolant.${label.toLowerCase()}`, label)"
              />{{ label }}</label
            >
          </div>
        </div>
      </TabsContent>
      <TabsContent value="mdi" class="control-panel tk-panel mdi-panel" tabindex="-1">
        <label>History:</label>
        <div class="mdi-history tk-inset" aria-label="MDI history">
          <button
            v-for="(line, index) in fixture.history"
            :key="index"
            class="history-line"
            @click="mdi = line"
          >
            {{ line }}
          </button>
        </div>
        <form @submit.prevent="dialogs.openDialog('mdi.go', 'MDI Command')">
          <label for="mdi-command">MDI Command:</label>
          <div class="flex gap-1">
            <input id="mdi-command" v-model="mdi" autocomplete="off" spellcheck="false" /><TkButton
              @click="dialogs.openDialog('mdi.go', 'MDI Command')"
              >Go</TkButton
            >
          </div>
        </form>
      </TabsContent>
    </TabsRoot>
    <div class="override-controls">
      <TkRange v-model="feed" label="Feed Override" :max="120" />
      <TkRange v-model="rapid" label="Rapid Override" :max="100" />
      <TkRange v-model="spindle" label="Spindle Override" :max="120" />
      <TkRange v-model="jog" label="Jog Speed" :max="3000" unit=" mm/min" />
      <TkRange v-model="maxVelocity" label="Max Velocity" :max="6000" unit=" mm/min" />
    </div>
    <div v-if="ui.controlTab === 'mdi'" class="active-codes">
      <span>Active G-Codes:</span>
      <pre class="tk-inset">{{ fixture.activeCodes }}</pre>
    </div>
  </section>
</template>
