import { expect, test } from '@playwright/test';

for (const desktop of [false, true]) {
  test(`${desktop ? 'desktop' : 'browser'} workspace omits status decorations and keeps machine actions inert`, async ({
    page,
  }) => {
    await page.addInitScript((isDesktop) => {
      Object.defineProperty(window, 'isTauri', { value: isDesktop });
      Object.defineProperty(window, '__TAURI_INTERNALS__', {
        value: {
          invoke: async () => {
            throw new Error('This screen must not invoke the desktop bridge');
          },
        },
      });
    }, desktop);
    await page.goto('/');
    await expect(page.getByRole('button', { name: '检查本地服务连接' })).toHaveCount(0);
    await expect(page.getByLabel('机床状态示例')).toHaveCount(0);
    await expect(page.getByText('界面演示', { exact: true })).toHaveCount(0);
    await expect(page.getByText('未连接控制器', { exact: true })).toHaveCount(0);
    await expect(page.getByText('未装刀', { exact: true })).toHaveCount(0);
    await expect(page.getByTitle('已回零标记（示例）')).toHaveCount(0);
    await page.getByRole('button', { name: '全部回零', exact: true }).click();
    await expect(page.getByRole('dialog')).toContainText('尚未连接控制器');
    await expect(page.getByLabel('坐标读数')).toContainText('0.000');
  });
}
