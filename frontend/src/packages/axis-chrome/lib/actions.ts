import { menus } from '../../axis-catalog';
import type { MenuItem } from '../../axis-catalog/model';
import { useAxisPresentation } from '../../axis-presentation';
import { useManualPresentation } from '../../manual-control/presentation';
import { useToolpathPresentation } from '../../toolpath-view/presentation';

function findItem(id: string, entries: MenuItem[]): MenuItem | undefined {
  for (const entry of entries) {
    if (entry.id === id) return entry;
    const child = entry.children && findItem(id, entry.children);
    if (child) return child;
  }
}

// AXIS chrome composes feature presentation APIs; it never sends controller commands.
export function useChromeActions() {
  const dialogs = useAxisPresentation();
  const preview = useToolpathPresentation();
  const manual = useManualPresentation();
  function selectedValue(group: string) {
    if (group === 'mode') return manual.mode;
    if (group === 'touch') return manual.touchTarget;
    return preview.choices[group];
  }
  function isSelected(item: MenuItem) {
    return item.kind === 'radio'
      ? selectedValue(item.group!) === item.value
      : !!preview.flags[item.id];
  }
  function activate(id: string, label?: string) {
    if (id === 'view.zoom-in') {
      preview.zoomBy(1.15);
      return;
    }
    if (id === 'view.zoom-out') {
      preview.zoomBy(1 / 1.15);
      return;
    }
    if (id === 'view.rotate') {
      preview.rotate = !preview.rotate;
      return;
    }
    if (id === 'view.clear') {
      preview.flags['show.live'] = false;
      return;
    }
    const item = findItem(id, menus);
    if (item?.kind === 'radio') {
      if (item.group === 'mode') manual.mode = item.value!;
      else if (item.group === 'touch') manual.touchTarget = item.value!;
      else preview.choices[item.group!] = item.value!;
      return;
    }
    if (item?.kind === 'check' && id in preview.flags) {
      preview.flags[id] = !preview.flags[id];
      return;
    }
    dialogs.openDialog(id, label);
  }
  return { selectedValue, isSelected, activate };
}
