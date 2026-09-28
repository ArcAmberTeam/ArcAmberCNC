import { expect, test } from '@playwright/test';

test('release metadata matches the exact commit selected for deployment', async ({ request }) => {
  test.skip(!process.env.EXPECTED_COMMIT, 'Commit metadata is added by the release packager.');
  const response = await request.get('/build-info.json');
  expect(response.ok()).toBe(true);
  expect(await response.json()).toMatchObject({
    commit: process.env.EXPECTED_COMMIT,
    interface: 'web',
  });
});

test('Linear-style workspace renders Chinese controls and local artwork without errors', async ({
  page,
}, info) => {
  const errors: string[] = [];
  page.on('pageerror', (error) => errors.push(error.message));
  await page.goto('/');
  await expect(page.locator('html')).toHaveAttribute('lang', 'zh-CN');
  await expect(page).toHaveTitle(/中文操作界面/);
  await expect(page.getByRole('menubar')).toBeVisible();
  await expect(page.getByRole('toolbar').getByRole('button')).toHaveCount(19);
  await expect(page.getByRole('tab', { name: '手动操作 [F3]', exact: true })).toHaveAttribute(
    'data-state',
    'active',
  );
  await expect(page.getByRole('img', { name: /LinuxCNC 标识刀路示意图/ })).toBeVisible();
  await expect(page.getByRole('region', { name: '加工程序', exact: true })).toContainText(
    'AXIS 标识演示程序',
  );
  const broken = await page
    .locator('img')
    .evaluateAll(
      (images) =>
        images.filter(
          (image) =>
            !(image as HTMLImageElement).complete || (image as HTMLImageElement).naturalWidth === 0,
        ).length,
    );
  expect(broken).toBe(0);
  expect(errors).toEqual([]);
  const flood = await page.getByRole('checkbox', { name: '切削液冷却', exact: true }).boundingBox();
  const feedLabelTop = await page
    .getByRole('slider', { name: '进给倍率', exact: true })
    .evaluate((element) => element.closest('label')!.getBoundingClientRect().top);
  expect(flood!.y + flood!.height).toBeLessThan(feedLabelTop);
  await page.screenshot({ path: info.outputPath('axis-default.png'), fullPage: true });
});

test('menus, nested entries and preview controls remain keyboard accessible', async ({ page }) => {
  await page.goto('/');
  await page.getByRole('menuitem', { name: '文件', exact: true }).click();
  await page.getByRole('menuitem', { name: '最近打开', exact: true }).hover();
  await expect(page.getByRole('menuitem', { name: '清空最近打开记录' })).toBeVisible();
  await page.keyboard.press('Escape');
  await page.keyboard.press('Escape');
  await page.getByRole('menuitem', { name: '视图', exact: true }).click();
  await page.getByRole('menuitem', { name: '网格', exact: true }).hover();
  await expect(page.getByRole('menuitemradio', { name: '100 毫米', exact: true })).toBeVisible();
  await page.keyboard.press('Escape');
  await page.keyboard.press('Escape');
  await page.getByRole('menuitem', { name: '视图', exact: true }).click();
  await page.getByRole('menuitemcheckbox', { name: '显示当前速度', exact: true }).click();
  await expect(page.getByLabel('坐标读数')).not.toContainText('速度：');
  await page.getByRole('tab', { name: '坐标数显', exact: true }).click();
  await expect(page.getByRole('tabpanel', { name: '坐标数显', exact: true })).toContainText(
    'G54 工件坐标偏置',
  );
  await page.getByRole('menuitem', { name: '帮助', exact: true }).focus();
  await page.keyboard.press('ArrowDown');
  await page.getByRole('menuitem', { name: '快捷键说明' }).click();
  await expect(page.getByRole('dialog')).toContainText('快捷键说明：');
  await page.keyboard.press('Escape');
  await expect(page.getByRole('dialog')).toHaveCount(0);
});

test('machine buttons and MDI cannot dispatch control requests or mutate sample feedback', async ({
  page,
}) => {
  const requests: string[] = [];
  await page.goto('/');
  page.on('request', (request) => {
    if (['fetch', 'xhr'].includes(request.resourceType())) requests.push(request.url());
  });
  for (const label of [
    '切换急停状态 [F1]',
    '机床使能／关闭 [F2]',
    '运行当前程序 [R]',
    '正向点动',
    '全部回零',
    '主轴正转',
  ]) {
    await page.getByRole('button', { name: label, exact: true }).click();
    await expect(page.getByRole('dialog')).toContainText('尚未连接控制器');
    await page.getByRole('button', { name: '关闭', exact: true }).click();
  }
  await page.getByRole('tab', { name: '手动输入 [F5]', exact: true }).click();
  await page.getByLabel('手动输入指令：', { exact: true }).fill('G0 X100');
  await page.getByRole('button', { name: '执行', exact: true }).click();
  await expect(page.getByRole('dialog')).toContainText('此操作不会执行');
  await expect(page.getByLabel('坐标读数')).toContainText('0.000');
  expect(requests).toEqual([]);
});

test('manual selection stays in its feature and editable fields do not trigger shortcuts', async ({
  page,
}) => {
  await page.goto('/');
  await page.getByRole('radio', { name: 'Y', exact: true }).check();
  await page.getByRole('button', { name: '工件对刀', exact: true }).click();
  await expect(page.getByRole('dialog')).toContainText('设置 Y 轴工件坐标：');
  await page.keyboard.press('Escape');
  await page.getByRole('tab', { name: '手动输入 [F5]', exact: true }).click();
  await page.getByLabel('手动输入指令：', { exact: true }).fill('xyz');
  await page.keyboard.press('F3');
  await expect(page.getByRole('tab', { name: '手动操作 [F3]', exact: true })).toHaveAttribute(
    'data-state',
    'active',
  );
  await expect(page.getByRole('radio', { name: 'Y', exact: true })).toBeChecked();
  await page.getByRole('slider', { name: '进给倍率', exact: true }).fill('75');
  await expect(page.getByRole('slider', { name: '进给倍率', exact: true })).toHaveValue('75');
});

test('program selection and panel resizing work at the compact desktop size', async ({
  page,
}, info) => {
  await page.setViewportSize({ width: 800, height: 680 });
  await page.goto('/');
  const program = page.getByRole('region', { name: '加工程序', exact: true });
  const before = await program.boundingBox();
  const sash = page.getByRole('separator', { name: '调整程序区高度' });
  await sash.focus();
  await page.keyboard.press('ArrowUp');
  const after = await program.boundingBox();
  expect(after!.height).toBeGreaterThan(before!.height);
  await program.getByText('#<depth>=2.0', { exact: true }).click({ button: 'right' });
  await expect(page.getByRole('menuitem', { name: '从此行运行', exact: true })).toBeVisible();
  await page.keyboard.press('Escape');
  expect(await page.evaluate(() => document.documentElement.scrollWidth <= window.innerWidth)).toBe(
    true,
  );
  await page.screenshot({ path: info.outputPath('axis-compact.png'), fullPage: true });
});

test('Chinese dialogs distinguish work coordinates, tool offsets and signal controls', async ({
  page,
}) => {
  await page.goto('/');
  for (const button of await page.getByRole('toolbar').getByRole('button').all()) {
    await expect(button).toHaveAttribute('title', /\p{Script=Han}/u);
    await expect(button).toHaveAccessibleName(/\p{Script=Han}/u);
  }
  await page.getByRole('radio', { name: 'Z', exact: true }).check();
  await page.getByRole('button', { name: '刀具对刀', exact: true }).click();
  await expect(page.getByRole('dialog')).toContainText('设置 Z 轴刀具偏置：');
  await page.getByRole('button', { name: '关闭对话框' }).click();
  await page.getByRole('button', { name: '工件对刀', exact: true }).click();
  await expect(page.getByRole('dialog')).toContainText('设置 Z 轴工件坐标：');
  await page.getByLabel('工件坐标系', { exact: true }).selectOption('G55');
  await expect(page.getByLabel('工件坐标系', { exact: true })).toHaveValue('G55');
  await page.keyboard.press('Escape');
  await page.getByRole('checkbox', { name: '切削液冷却', exact: true }).click();
  await expect(page.getByRole('dialog')).toHaveAccessibleName('切削液冷却');
  await expect(page.getByRole('dialog')).toContainText('此操作不会执行');
  await page.keyboard.press('Escape');
  await expect(page.getByRole('checkbox', { name: '切削液冷却', exact: true })).not.toBeChecked();
  await page.getByRole('menuitem', { name: '视图', exact: true }).click();
  await page.getByRole('menuitemradio', { name: '显示机床坐标', exact: true }).click();
  await page.getByRole('menuitem', { name: '视图', exact: true }).click();
  await expect(
    page.getByRole('menuitemradio', { name: '显示机床坐标', exact: true }),
  ).toHaveAttribute('aria-checked', 'true');
  await page.keyboard.press('Escape');
  await page.getByRole('menuitem', { name: '文件', exact: true }).click();
  await page.getByRole('menuitem', { name: '打开程序…', exact: true }).click();
  await expect(page.getByLabel('文件类型', { exact: true })).toContainText('加工程序（*.ngc）');
  await expect(page.getByLabel('文件名：', { exact: true })).toHaveValue('axis.ngc');
});

test('workspace panels stay usable at minimum size after enlarging the program', async ({
  page,
}, info) => {
  await page.goto('/');
  const sash = page.getByRole('separator', { name: '调整程序区高度' });
  await sash.focus();
  for (let i = 0; i < 20; i++) await page.keyboard.press('ArrowUp');
  await page.setViewportSize({ width: 760, height: 640 });
  const program = page.getByRole('region', { name: '加工程序', exact: true });
  await expect
    .poll(async () => {
      const bounds = await program.boundingBox();
      return bounds!.y + bounds!.height <= 640;
    })
    .toBe(true);
  await expect(page.getByRole('img', { name: /LinuxCNC 标识刀路示意图/ })).toBeInViewport();
  const canvas = await page.getByRole('img', { name: /LinuxCNC 标识刀路示意图/ }).boundingBox();
  expect(canvas!.height).toBeGreaterThan(60);
  const speed = page.getByRole('slider', { name: '最大速度', exact: true });
  await speed.scrollIntoViewIfNeeded();
  await expect(speed).toBeInViewport();
  await page.getByRole('toolbar').getByRole('button').last().focus();
  await expect(page.getByRole('toolbar').getByRole('button').last()).toBeInViewport();
  await page.getByRole('toolbar').getByRole('button').first().focus();
  await expect(page.getByRole('toolbar').getByRole('button').first()).toBeInViewport();
  expect(await page.evaluate(() => document.documentElement.scrollWidth <= window.innerWidth)).toBe(
    true,
  );
  await page.screenshot({ path: info.outputPath('linear-minimum.png'), fullPage: true });
});
