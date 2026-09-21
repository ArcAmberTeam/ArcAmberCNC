import { defineStore } from 'pinia';
import { reactive, ref } from 'vue';

export const useToolpathPresentation = defineStore('toolpath-view-ui', () => {
  const previewTab = ref('preview');
  const zoom = ref(1);
  const rotate = ref(false);
  const choices = reactive<Record<string, string>>({
    view: 'p',
    units: 'mm',
    grid: 'off',
    position: 'actual',
    coordinates: 'relative',
  });
  const flags = reactive<Record<string, boolean>>({
    'show.program': true,
    'show.rapids': true,
    'show.alpha': false,
    'show.live': true,
    'show.tool': true,
    'show.extents': true,
    'show.offsets': false,
    'show.limits': false,
    'show.velocity': true,
    'show.dtg': false,
    'show.large': false,
  });
  function zoomBy(factor: number) {
    zoom.value = Math.max(0.5, Math.min(2, zoom.value * factor));
  }
  return { previewTab, choices, flags, zoom, rotate, zoomBy };
});
