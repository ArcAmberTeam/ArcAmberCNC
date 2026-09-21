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

test('AXIS shell renders its native layout and local artwork without errors', async ({
  page,
}, info) => {
  const errors: string[] = [];
  page.on('pageerror', (error) => errors.push(error.message));
  await page.goto('/');
  await expect(page.getByRole('menubar')).toBeVisible();
  await expect(page.getByRole('toolbar').getByRole('button')).toHaveCount(19);
  await expect(page.getByRole('tab', { name: 'Manual Control [F3]', exact: true })).toHaveAttribute(
    'data-state',
    'active',
  );
  await expect(page.getByRole('img', { name: /Static LinuxCNC splash/ })).toBeVisible();
  await expect(page.getByLabel('G-code program')).toContainText('AXIS "splash G-code"');
  await expect(page.getByLabel('Sample machine status')).toHaveText(
    /ESTOPNo toolPosition: Relative Actual/,
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
  const flood = await page.getByRole('checkbox', { name: 'Flood', exact: true }).boundingBox();
  const feedLabelTop = await page
    .getByRole('slider', { name: 'Feed Override', exact: true })
    .evaluate((element) => element.closest('label')!.getBoundingClientRect().top);
  expect(flood!.y + flood!.height).toBeLessThan(feedLabelTop);
  await page.screenshot({ path: info.outputPath('axis-default.png'), fullPage: true });
});

test('menus, nested entries and preview controls remain keyboard accessible', async ({ page }) => {
  await page.goto('/');
  await page.getByRole('menuitem', { name: 'File', exact: true }).click();
  await page.getByRole('menuitem', { name: 'Recent Files', exact: true }).hover();
  await expect(page.getByRole('menuitem', { name: 'Clear Recents List' })).toBeVisible();
  await page.keyboard.press('Escape');
  await page.keyboard.press('Escape');
  await page.getByRole('menuitem', { name: 'View', exact: true }).click();
  await page.getByRole('menuitem', { name: 'Grid', exact: true }).hover();
  await expect(page.getByRole('menuitemradio', { name: '100mm', exact: true })).toBeVisible();
  await page.keyboard.press('Escape');
  await page.keyboard.press('Escape');
  await page.getByRole('menuitem', { name: 'View', exact: true }).click();
  await page.getByRole('menuitemcheckbox', { name: 'Show velocity', exact: true }).click();
  await expect(page.getByLabel('Position readout')).not.toContainText('Vel:');
  await page.getByRole('tab', { name: 'DRO', exact: true }).click();
  await expect(page.getByRole('tabpanel', { name: 'DRO', exact: true })).toContainText(
    'G54 offsets',
  );
  await page.getByRole('menuitem', { name: 'Help', exact: true }).focus();
  await page.keyboard.press('ArrowDown');
  await page.getByRole('menuitem', { name: 'Quick Reference' }).click();
  await expect(page.getByRole('dialog')).toContainText('AXIS keyboard reference');
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
    'Toggle Emergency Stop [F1]',
    'Toggle Machine power [F2]',
    'Begin executing current file [R]',
    'Jog positive',
    'Home All',
    'Spindle clockwise',
  ]) {
    await page.getByRole('button', { name: label, exact: true }).click();
    await expect(page.getByRole('dialog')).toContainText('no controller connected');
    await page.getByRole('button', { name: 'Close', exact: true }).click();
    await expect(page.getByLabel('Sample machine status')).toContainText('ESTOP');
  }
  await page.getByRole('tab', { name: 'MDI [F5]', exact: true }).click();
  await page.getByLabel('MDI Command:', { exact: true }).fill('G0 X100');
  await page.getByRole('button', { name: 'Go', exact: true }).click();
  await expect(page.getByRole('dialog')).toContainText('This action is not implemented');
  await expect(page.getByLabel('Position readout')).toContainText('0.000');
  expect(requests).toEqual([]);
});

test('manual selection stays in its feature and editable fields do not trigger shortcuts', async ({
  page,
}) => {
  await page.goto('/');
  await page.getByRole('radio', { name: 'Y', exact: true }).check();
  await page.getByRole('button', { name: 'Touch Off', exact: true }).click();
  await expect(page.getByRole('dialog')).toContainText('Set Y coordinate to:');
  await page.keyboard.press('Escape');
  await page.getByRole('tab', { name: 'MDI [F5]', exact: true }).click();
  await page.getByLabel('MDI Command:', { exact: true }).fill('xyz');
  await page.keyboard.press('F3');
  await expect(page.getByRole('tab', { name: 'Manual Control [F3]', exact: true })).toHaveAttribute(
    'data-state',
    'active',
  );
  await expect(page.getByRole('radio', { name: 'Y', exact: true })).toBeChecked();
  await page.getByRole('slider', { name: 'Feed Override', exact: true }).fill('75');
  await expect(page.getByRole('slider', { name: 'Feed Override', exact: true })).toHaveValue('75');
  await expect(page.getByLabel('Sample machine status')).toContainText('ESTOP');
});

test('program selection and panel resizing work at the compact desktop size', async ({
  page,
}, info) => {
  await page.setViewportSize({ width: 800, height: 680 });
  await page.goto('/');
  const program = page.getByLabel('G-code program');
  const before = await program.boundingBox();
  const sash = page.getByRole('separator', { name: 'Resize program panel' });
  await sash.focus();
  await page.keyboard.press('ArrowUp');
  const after = await program.boundingBox();
  expect(after!.height).toBeGreaterThan(before!.height);
  await program.getByText('#<depth>=2.0', { exact: true }).click({ button: 'right' });
  await expect(page.getByRole('menuitem', { name: 'Run from here', exact: true })).toBeVisible();
  await page.keyboard.press('Escape');
  expect(await page.evaluate(() => document.documentElement.scrollWidth <= window.innerWidth)).toBe(
    true,
  );
  await page.screenshot({ path: info.outputPath('axis-compact.png'), fullPage: true });
});
