import { defineConfig } from '@playwright/test';

const testRelease = process.env.PLAYWRIGHT_TEST_DIST === '1';
const baseURL = `http://127.0.0.1:${testRelease ? 4173 : 5173}`;

export default defineConfig({
  testDir: './tests',
  fullyParallel: true,
  use: {
    baseURL,
    viewport: { width: 1100, height: 820 },
    screenshot: 'only-on-failure',
    trace: 'retain-on-failure',
  },
  webServer: {
    command: testRelease ? 'npm run preview -- --port 4173 --strictPort' : 'npm run dev',
    url: baseURL,
    reuseExistingServer: !process.env.CI,
    timeout: 30_000,
  },
});
