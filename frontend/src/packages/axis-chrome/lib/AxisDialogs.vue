<script setup lang="ts">
import { computed, ref, watch } from 'vue';
import { coordinateSystems, fixture, quickReference, sampleProgram } from '../../axis-catalog';
import { useAxisPresentation } from '../../axis-presentation';
import { TkButton, TkDialog } from '../../ui-system';
const ui = useAxisPresentation();
const value = ref('0.0');
const system = ref('G54');
const description = computed(() => {
  if (ui.dialog?.id === 'help.about') return '基于 AXIS 的 LinuxCNC 中文操作界面';
  if (ui.dialog?.id === 'help.reference')
    return '快捷键说明：当前仅支持 F3、F5 和视图操作快捷键，机床控制快捷键尚未接入。';
  if (ui.dialog?.id === 'file.properties') return '当前内置演示程序的信息。';
  return '尚未连接控制器。当前仅演示界面，此操作不会执行。';
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
        <p>示例配置：{{ fixture.machine }}</p>
        <p>中文界面原型 · 仅作展示</p>
        <p>功能与布局参考 AXIS 2.9.10。</p>
      </div>
    </div>
    <dl v-else-if="ui.dialog.id === 'help.reference'" class="shortcut-list">
      <template v-for="[key, action] in quickReference" :key="key"
        ><dt>{{ key }}</dt>
        <dd>{{ action }}</dd></template
      >
    </dl>
    <dl v-else-if="ui.dialog.id === 'file.properties'" class="property-list">
      <dt>文件名</dt>
      <dd>{{ fixture.fileName }}</dd>
      <dt>程序行数</dt>
      <dd>{{ sampleProgram.length }}</dd>
      <dt>程序来源</dt>
      <dd>内置 AXIS 标识演示程序</dd>
      <dt>刀路预览</dt>
      <dd>静态示意图，尚未接入程序解释器</dd>
    </dl>
    <div
      v-else-if="
        ui.dialog.id === 'file.open' ||
        ui.dialog.id === 'file.open-sample' ||
        ui.dialog.id === 'file.save'
      "
      class="file-dialog"
    >
      <label>文件夹： <input value="/linuxcnc/nc_files" readonly /></label>
      <div class="tk-inset file-list">
        <span>📁&nbsp; 上级目录</span><span class="selected-file">▤&nbsp; axis.ngc</span>
      </div>
      <label>文件名： <input :value="fixture.fileName" readonly /></label>
      <label
        >文件类型：
        <select aria-label="文件类型">
          <option>加工程序（*.ngc）</option>
          <option>所有文件（*）</option>
        </select></label
      >
    </div>
    <div
      v-else-if="ui.dialog.id === 'machine.touch-off' || ui.dialog.id === 'tool.touch-off'"
      class="touch-dialog"
    >
      <p>
        设置 {{ ui.dialog.axis }} 轴{{
          ui.dialog.id.startsWith('tool') ? '刀具偏置' : '工件坐标'
        }}：
      </p>
      <label>设定值 <input v-model="value" inputmode="decimal" /></label>
      <label
        >工件坐标系
        <select v-model="system" aria-label="工件坐标系">
          <option v-for="item in coordinateSystems" :key="item">{{ item }}</option>
        </select></label
      >
    </div>
    <div v-else-if="ui.dialog.id === 'view.grid-custom'" class="touch-dialog">
      <label>网格间距 <input v-model="value" inputmode="decimal" /> 毫米</label>
    </div>
    <div v-else-if="ui.dialog.id === 'tool.edit'" class="tk-inset tool-table-wrap">
      <table class="tool-table">
        <thead>
          <tr>
            <th v-for="label in ['刀具号', '刀位号', 'X', 'Y', 'Z', '直径', '备注']" :key="label">
              {{ label }}
            </th>
          </tr>
        </thead>
        <tbody>
          <tr>
            <td colspan="7">尚未加载刀具表</td>
          </tr>
        </tbody>
      </table>
    </div>
    <div v-else-if="ui.dialog.id === 'show.pyvcp'" class="placeholder-detail">
      自定义面板需根据具体机床配置。当前三轴演示界面未配置 PyVCP 面板。
    </div>
    <div class="dialog-actions"><TkButton @click="ui.dialog = null">关闭</TkButton></div>
  </TkDialog>
</template>
