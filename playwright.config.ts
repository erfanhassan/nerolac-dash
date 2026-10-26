import { defineConfig, devices } from '@playwright/test';

export default defineConfig({
  testDir: './tests/visual',
  testMatch: ['**/*test*.ts', '**/*.spec.ts'],
  timeout: 30 * 1000,
  expect: {
    timeout: 5000,
  },
  fullyParallel: false,
  workers: 1,
  reporter: 'list',
  use: {
    baseURL: 'http://localhost:3000',
    trace: 'on-first-retry',
    viewport: { width: 1440, height: 900 },
  },
  projects: [
    {
      name: 'chromium',
      use: { ...devices['Desktop Chrome'] },
    },
  ],
  webServer: [
    {
      command: '.venv/bin/uvicorn src.backend.main:app --host 127.0.0.1 --port 8000',
      port: 8000,
      reuseExistingServer: true,
      timeout: 15 * 1000,
    },
    {
      command: 'npx next dev -p 3000',
      port: 3000,
      reuseExistingServer: true,
      timeout: 30 * 1000,
    },
  ],
});
