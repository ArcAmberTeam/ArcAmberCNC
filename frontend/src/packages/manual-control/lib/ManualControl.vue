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
  <section class="control-column" aria-label="机床操作">
    <TabsRoot v-model="ui.controlTab" class="control-tabs">
      <TabsList class="tk-tabs" aria-label="操作方式">
        <TabsTrigger value="manual" class="tk-tab">手动操作 [F3]</TabsTrigger>
        <TabsTrigger value="mdi" class="tk-tab">手动输入 [F5]</TabsTrigger>
      </TabsList>
      <TabsContent value="manual" class="control-panel tk-panel" tabindex="-1">
        <div class="manual-grid">
          <span class="control-label">{{ ui.mode === 'joint' ? '关节：' : '坐标轴：' }}</span>
          <div
            class="axis-radios"
            role="radiogroup"
            :aria-label="ui.mode === 'joint' ? '选择关节' : '选择坐标轴'"
          >
            <label v-for="(axis, index) in axes" :key="axis"
              ><input v-model="ui.selectedAxis" type="radio" :value="axis" name="axis" />{{
                ui.mode === 'joint' ? index : axis
              }}</label
            >
          </div>
          <div class="manual-actions">
            <div class="jog-row flex items-center">
              <TkButton
                aria-label="负向点动"
                @click="dialogs.openDialog('machine.jog-minus', `${ui.selectedAxis} 轴负向点动`)"
                >−</TkButton
              >
              <TkButton
                aria-label="正向点动"
                @click="dialogs.openDialog('machine.jog-plus', `${ui.selectedAxis} 轴正向点动`)"
                >+</TkButton
              >
              <select v-model="increment" aria-label="点动方式与步距">
                <option value="Continuous">连续点动</option>
                <option>0.1000</option>
                <option>0.0100</option>
                <option>0.0010</option>
                <option>0.0001</option>
              </select>
            </div>
            <div class="homing-buttons">
              <TkButton @click="dialogs.openDialog('machine.home-all')">全部回零</TkButton
              ><TkButton
                @click="dialogs.openDialog('machine.touch-off', '工件对刀', ui.selectedAxis)"
                >工件对刀</TkButton
              ><TkButton
                class="tool-touch"
                @click="dialogs.openDialog('tool.touch-off', '刀具对刀', ui.selectedAxis)"
                >刀具对刀</TkButton
              >
            </div>
            <label class="check-label"
              ><input
                type="checkbox"
                :checked="false"
                @click.prevent="dialogs.openDialog('machine.override-limits', '临时解除硬限位')"
              />临时解除硬限位</label
            >
          </div>
          <span class="control-label spindle-label">主轴：</span>
          <div class="spindle-controls">
            <div class="flex items-center">
              <TkButton
                aria-label="主轴反转"
                title="主轴反转"
                @click="dialogs.openDialog('spindle.ccw', '主轴反转')"
                ><img src="/axis/spindle_ccw.gif" alt=""
              /></TkButton>
              <TkButton
                class="spindle-stop"
                :pressed="true"
                @click="dialogs.openDialog('spindle.stop', '主轴停止')"
                >停止</TkButton
              >
              <TkButton
                aria-label="主轴正转"
                title="主轴正转"
                @click="dialogs.openDialog('spindle.cw', '主轴正转')"
                ><img src="/axis/spindle_cw.gif" alt=""
              /></TkButton>
            </div>
            <div class="flex">
              <TkButton
                aria-label="降低主轴转速"
                @click="dialogs.openDialog('spindle.decrease', '降低主轴转速')"
                >−</TkButton
              ><TkButton
                aria-label="提高主轴转速"
                @click="dialogs.openDialog('spindle.increase', '提高主轴转速')"
                >+</TkButton
              >
            </div>
            <label class="check-label"
              ><input
                type="checkbox"
                :checked="false"
                @click.prevent="dialogs.openDialog('spindle.brake', '主轴制动')"
              />主轴制动</label
            >
          </div>
          <span class="control-label coolant-label">冷却：</span>
          <div class="coolant-controls">
            <label
              v-for="item in [
                { id: 'mist', label: '喷雾冷却' },
                { id: 'flood', label: '切削液冷却' },
              ]"
              :key="item.id"
              class="check-label"
              ><input
                type="checkbox"
                :checked="false"
                @click.prevent="dialogs.openDialog(`coolant.${item.id}`, item.label)"
              />{{ item.label }}</label
            >
          </div>
        </div>
      </TabsContent>
      <TabsContent value="mdi" class="control-panel tk-panel mdi-panel" tabindex="-1">
        <label>历史指令：</label>
        <div class="mdi-history tk-inset" aria-label="手动输入历史">
          <button
            v-for="(line, index) in fixture.history"
            :key="index"
            class="history-line"
            @click="mdi = line"
          >
            {{ line }}
          </button>
        </div>
        <form @submit.prevent="dialogs.openDialog('mdi.go', '执行手动指令')">
          <label for="mdi-command">手动输入指令：</label>
          <div class="flex gap-1">
            <input id="mdi-command" v-model="mdi" autocomplete="off" spellcheck="false" /><TkButton
              @click="dialogs.openDialog('mdi.go', '执行手动指令')"
              >执行</TkButton
            >
          </div>
        </form>
      </TabsContent>
    </TabsRoot>
    <div class="override-controls">
      <TkRange v-model="feed" label="进给倍率" :max="120" />
      <TkRange v-model="rapid" label="快移倍率" :max="100" />
      <TkRange v-model="spindle" label="主轴倍率" :max="120" />
      <TkRange v-model="jog" label="点动速度" :max="3000" unit=" 毫米/分钟" />
      <TkRange v-model="maxVelocity" label="最大速度" :max="6000" unit=" 毫米/分钟" />
    </div>
    <div v-if="ui.controlTab === 'mdi'" class="active-codes">
      <span>当前模态指令：</span>
      <pre class="tk-inset">{{ fixture.activeCodes }}</pre>
    </div>
  </section>
</template>
