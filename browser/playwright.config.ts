import { defineConfig, devices } from '@playwright/test';

const baseURL = process.env.ORGO_E2E_URL || 'http://127.0.0.1:3000';
if (!['localhost', '127.0.0.1', '[::1]'].includes(new URL(baseURL).hostname)) {
  throw new Error('Browser acceptance is restricted to a local test instance.');
}
for (const key of ['ORGO_E2E_ORGANIZATION', 'ORGO_E2E_EMAIL', 'ORGO_E2E_PASSWORD']) {
  if (!process.env[key]) throw new Error(`Missing ${key}`);
}
if (process.env.ORGO_E2E_ALLOW_WRITES !== 'test-instance') {
  throw new Error('Set ORGO_E2E_ALLOW_WRITES=test-instance for your disposable instance.');
}
export default defineConfig({
  testDir: './tests',
  fullyParallel: false,
  workers: 1,
  retries: 0,
  forbidOnly: true,
  timeout: 60000,
  expect: { timeout: 10000 },
  outputDir: process.env.ORGO_E2E_RESULTS || './test-results',
  reporter: [
    ['list'],
    ['html', { outputFolder: process.env.ORGO_E2E_HTML || './playwright-report', open: 'never' }],
    ['json', { outputFile: process.env.ORGO_E2E_JSON || './results.json' }],
  ],
  use: { baseURL, trace: 'retain-on-failure', screenshot: 'only-on-failure', video: 'off' },
  projects: [{ name: 'chromium', use: { ...devices['Desktop Chrome'] } }],
});
