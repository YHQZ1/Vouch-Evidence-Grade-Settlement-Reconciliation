import { defineConfig } from '@playwright/test';

export default defineConfig({
  testDir: './tests/e2e',
  testMatch: /scripted-agent\.spec\.ts/,
  use: { baseURL: 'http://127.0.0.1:5174', trace: 'retain-on-failure' },
  webServer: [
    {
      command:
        'cd ../backend && .venv/bin/python -m uvicorn tests.support.scripted_app:app --port 8001',
      url: 'http://127.0.0.1:8001/healthz',
      reuseExistingServer: false,
    },
    {
      command:
        'VITE_API_PROXY_TARGET=http://127.0.0.1:8001 npm run dev -- --host 127.0.0.1 --port 5174',
      url: 'http://127.0.0.1:5174',
      reuseExistingServer: false,
    },
  ],
});
