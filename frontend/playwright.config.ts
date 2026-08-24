import { defineConfig } from '@playwright/test'

export default defineConfig({
  testDir: './tests/e2e',
  use: { baseURL: 'http://127.0.0.1:5173', trace: 'retain-on-failure' },
  webServer: [
    { command: 'cd ../backend && .venv/bin/python -m uvicorn app.main:app --port 8000', url: 'http://127.0.0.1:8000/healthz', reuseExistingServer: true },
    { command: 'npm run dev -- --host 127.0.0.1', url: 'http://127.0.0.1:5173', reuseExistingServer: true },
  ],
})
