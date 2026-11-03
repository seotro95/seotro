import { defineConfig } from '@playwright/test';
export default defineConfig({
  testDir: './tests/browser',
  workers: 1,
  fullyParallel: false,
  use: { baseURL: 'http://127.0.0.1:8789', headless: true,
    launchOptions: process.env.CHROMIUM_PATH ? { executablePath: process.env.CHROMIUM_PATH } : {} },
  webServer: { command: 'npm start', url: 'http://127.0.0.1:8789', env: { PORT: '8789', MUSE_ADAPTER_URL: '' }, reuseExistingServer: false },
});
