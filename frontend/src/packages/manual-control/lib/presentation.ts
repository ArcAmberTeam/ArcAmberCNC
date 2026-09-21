import { defineStore } from 'pinia';
import { ref } from 'vue';

export const useManualPresentation = defineStore('manual-control-ui', () => {
  const controlTab = ref('manual');
  const selectedAxis = ref('X');
  const mode = ref('world');
  const touchTarget = ref('workpiece');
  return { controlTab, selectedAxis, mode, touchTarget };
});
