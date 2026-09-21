import { expect, test } from '@playwright/test';

test('ordinary browser preview does not expose a desktop service connection', async ({ page }) => {
  await page.goto('/');
  await expect(page.getByRole('button', { name: '检查本地服务连接' })).toHaveCount(0);
});

test('desktop diagnostics never imply the machine is connected', async ({ page }) => {
  await page.addInitScript(() => {
    Object.defineProperty(window, 'isTauri', { value: true });
    Object.defineProperty(window, '__TAURI_INTERNALS__', {
      value: {
        invoke: async (command: string) => {
          if (command !== 'service_health') throw new Error('unexpected desktop operation');
          return { service: 'betterlinuxcnc', mode: 'diagnostics-only', machine_connected: false };
        },
      },
    });
  });
  await page.goto('/');
  await expect(page.getByRole('button', { name: '检查本地服务连接' })).toHaveText('本地服务已连接');
  await expect(page.getByText('界面演示', { exact: true })).toBeVisible();
  await page.getByRole('button', { name: '全部回零', exact: true }).click();
  await expect(page.getByRole('dialog')).toContainText('尚未连接控制器');
});

test('unexpected machine feedback is rejected at the desktop boundary', async ({ page }) => {
  await page.addInitScript(() => {
    Object.defineProperty(window, 'isTauri', { value: true });
    Object.defineProperty(window, '__TAURI_INTERNALS__', {
      value: {
        invoke: async () => ({
          service: 'betterlinuxcnc',
          mode: 'diagnostics-only',
          machine_connected: true,
        }),
      },
    });
  });
  await page.goto('/');
  await expect(page.getByRole('button', { name: '检查本地服务连接' })).toHaveText('本地服务未连接');
});
