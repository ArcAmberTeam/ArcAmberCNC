import { defineStore } from 'pinia';
import { ref } from 'vue';
import { menus } from '../../axis-catalog';
import type { MenuItem } from '../../axis-catalog/model';

const findItem = (id: string, items: MenuItem[]): MenuItem | undefined => {
  for (const item of items) {
    if (item.id === id) return item;
    const nested = item.children && findItem(id, item.children);
    if (nested) return nested;
  }
};

export const useAxisPresentation = defineStore('axis-presentation', () => {
  const dialog = ref<{ id: string; title: string; axis?: string } | null>(null);

  function openDialog(id: string, label?: string, axis?: string) {
    const item = findItem(id, menus);
    dialog.value = { id, title: item?.label.replace('…', '') ?? label ?? id, axis };
  }

  return { dialog, openDialog };
});
