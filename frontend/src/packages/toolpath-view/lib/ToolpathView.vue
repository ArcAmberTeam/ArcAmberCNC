<script setup lang="ts">
import './preview.css';
import { computed } from 'vue';
import { TabsRoot, TabsList, TabsTrigger, TabsContent } from 'reka-ui';
import { axes } from '../../axis-catalog';
import { useToolpathPresentation } from './presentation';
const ui = useToolpathPresentation();
const projection = computed(
  () =>
    ({
      p: 'matrix(0.94,0.30,-0.52,0.78,144,216)',
      z: 'matrix(1,0,0,1,105,190)',
      z2: 'matrix(0.86,-0.32,0.32,0.86,105,270)',
      x: 'matrix(0.5,0,0,1,215,190)',
      y: 'matrix(1,0,0,0.3,105,245)',
    })[ui.choices.view] ?? '',
);
const zero = computed(() => (ui.choices.units === 'inch' ? '0.0000' : '0.000'));
</script>

<template>
  <TabsRoot v-model="ui.previewTab" class="preview-column">
    <TabsList class="tk-tabs" aria-label="刀路与坐标显示"
      ><TabsTrigger value="preview" class="tk-tab">刀路预览</TabsTrigger
      ><TabsTrigger value="dro" class="tk-tab">坐标数显</TabsTrigger></TabsList
    >
    <TabsContent value="preview" class="preview-panel tk-inset" tabindex="-1">
      <div class="preview-readout" :class="{ large: ui.flags['show.large'] }" aria-label="坐标读数">
        <div v-for="axis in axes" :key="axis">
          <span>{{ axis }}:</span><span class="home-symbol" title="已回零标记（示例）">⌖</span
          ><span>{{ zero }}</span
          ><template v-if="ui.flags['show.dtg']"
            ><span class="dtg">剩余 {{ zero }}</span></template
          >
        </div>
        <div v-if="ui.flags['show.velocity']" class="velocity-readout">
          <span>速度：</span><span>{{ zero }}</span>
        </div>
        <div v-if="ui.flags['show.offsets']" class="offset-readout">
          G54 X: 0.000 Y: 0.000 Z: 0.000
        </div>
      </div>
      <svg
        class="toolpath-svg"
        viewBox="0 0 740 520"
        role="img"
        aria-label="LinuxCNC 标识刀路示意图，仅作展示，未经程序解释器计算"
      >
        <defs>
          <pattern id="preview-grid" width="24" height="24" patternUnits="userSpaceOnUse">
            <path d="M 24 0 L 0 0 0 24" fill="none" stroke="#244242" stroke-width="0.6" />
          </pattern>
          <linearGradient id="tool-fill">
            <stop stop-color="#ddd" stop-opacity="0.65" />
            <stop offset="1" stop-color="#5c6b74" stop-opacity="0.45" />
          </linearGradient>
        </defs>
        <g :transform="`translate(370 260) scale(${ui.zoom}) translate(-370 -260)`">
          <g :transform="projection" fill="none" stroke-linejoin="round">
            <rect
              v-if="ui.choices.grid !== 'off'"
              x="-50"
              y="-50"
              width="630"
              height="200"
              fill="url(#preview-grid)"
            />
            <path
              v-if="ui.flags['show.limits']"
              d="M-70 -80H610V190H-70ZM-70 -80L-35 -115H645V155L610 190M610 -80L645 -115M645 155H-35L-70 190M-35 155V-115"
              stroke="#6b7278"
              stroke-dasharray="5 5"
            />
            <g v-if="ui.flags['show.extents']" stroke="#b33131" stroke-width="1">
              <path
                d="M-15 -18H547V113H-15ZM-15 125V146M547 125V146M-15 137H547M-26 -18H-44M-26 113H-44M-35 -18V113"
              />
              <path
                d="M-15 137l8 -3v6zM547 137l-8 -3v6zM-35 -18l-3 8h6zM-35 113l-3 -8h6z"
                fill="#b33131"
              />
              <text
                x="234"
                y="155"
                stroke="none"
                fill="#ed6464"
                font-size="13"
                font-family="monospace"
              >
                {{ ui.choices.units === 'mm' ? '132.000' : '5.1969' }}
              </text>
              <text
                x="-57"
                y="73"
                transform="rotate(-90 -57 73)"
                stroke="none"
                fill="#ed6464"
                font-size="13"
                font-family="monospace"
              >
                {{ ui.choices.units === 'mm' ? '31.000' : '1.2205' }}
              </text>
            </g>
            <g v-if="ui.flags['show.program']" :opacity="ui.flags['show.alpha'] ? 0.55 : 1">
              <text
                x="0"
                y="84"
                font-family="Arial, Helvetica, sans-serif"
                font-size="97"
                font-weight="700"
                font-style="italic"
                textLength="528"
                lengthAdjust="spacingAndGlyphs"
                stroke="#dedede"
                stroke-width="0.9"
                fill="none"
              >
                LinuxCNC
              </text>
              <path
                v-if="ui.flags['show.rapids']"
                d="M0 85L52 2L61 85L104 2L112 85L170 16L183 85L250 15L265 85L334 0L349 85L419 0L429 85L520 4"
                stroke="#24bcc0"
                stroke-width="0.8"
                stroke-dasharray="4 4"
              />
            </g>
            <path
              v-if="ui.flags['show.live']"
              d="M-2 92H38L46 65"
              stroke="#a74949"
              stroke-width="1.2"
            />
            <g v-if="ui.flags['show.offsets']" stroke="#7c76dd">
              <path d="M0 0H65M0 0V-60" />
              <text x="5" y="-66" fill="#aaa6ef" stroke="none" font-size="15">G54</text>
            </g>
          </g>
          <g v-if="ui.flags['show.tool']" transform="translate(150 185)">
            <path
              d="M-18 -36Q0 -45 18 -36L7 -7L0 8L-7 -7Z"
              fill="url(#tool-fill)"
              stroke="#9aadb5"
              stroke-width="0.7"
            />
            <ellipse cx="0" cy="-36" rx="18" ry="5" fill="#94a0a5" fill-opacity="0.4" />
            <path d="M0 -51V15" stroke="#a3aeb3" stroke-dasharray="2 3" stroke-width="0.7" />
          </g>
        </g>
        <g transform="translate(57 440)" stroke-width="1.2" font-family="monospace" font-size="13">
          <path d="M0 0L47 17" stroke="#de4a49" />
          <path d="M0 0L-20 27" stroke="#4aa45a" />
          <path d="M0 0V-51" stroke="#799dce" />
          <g stroke="none">
            <text x="52" y="23" fill="#de6b64">X</text>
            <text x="-30" y="37" fill="#68b576">Y</text>
            <text x="-4" y="-59" fill="#799dce">Z</text>
          </g>
        </g>
      </svg>
    </TabsContent>
    <TabsContent value="dro" class="dro-panel tk-panel" tabindex="-1">
      <div class="dro-position" :class="{ large: ui.flags['show.large'] }">
        <div v-for="axis in axes" :key="axis">
          <span>{{ axis }}:</span><span>⌖</span><span>{{ zero }}</span>
        </div>
      </div>
      <div class="dro-details">
        <p>速度：0.000</p>
        <p>剩余行程：0.000</p>
        <hr />
        <p>G54 工件坐标偏置</p>
        <p v-for="axis in axes" :key="`offset-${axis}`">{{ axis }}: 0.000</p>
        <hr />
        <p>G92 临时坐标偏置</p>
        <p>X: 0.000 &nbsp; Y: 0.000 &nbsp; Z: 0.000</p>
        <hr />
        <p>刀具长度补偿</p>
        <p>Z: 0.000</p>
        <p>坐标旋转角度：0.000</p>
      </div>
    </TabsContent>
  </TabsRoot>
</template>
