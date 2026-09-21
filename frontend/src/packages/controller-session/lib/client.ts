import { invoke, isTauri } from '@tauri-apps/api/core';

export const isDesktop = () => isTauri();

export async function checkLocalService(): Promise<void> {
  const result: unknown = await invoke('service_health');
  if (
    !result ||
    typeof result !== 'object' ||
    !('service' in result) ||
    result.service !== 'betterlinuxcnc' ||
    !('mode' in result) ||
    result.mode !== 'diagnostics-only' ||
    !('machine_connected' in result) ||
    result.machine_connected !== false
  ) {
    throw new Error('本地服务协议不匹配');
  }
}
