// @ts-check
const { defineConfig } = require('@playwright/test');
const path = require('path');
const fs = require('fs');
const localPython = path.resolve('.venv', process.platform === 'win32' ? 'Scripts/python.exe' : 'bin/python');
const python = process.env.GALACTICO_PYTHON || (fs.existsSync(localPython) ? localPython : 'python');
// One port per concurrent run. Two suites sharing 8111 would each believe the
// other's server was theirs, which is the stale-process failure below again.
const port = Number(process.env.GALACTICO_E2E_PORT || 8111);
const base = `http://127.0.0.1:${port}`;
process.env.GALACTICO_URL = process.env.GALACTICO_URL || base;

// Playwright owns the server lifecycle. An earlier run tested against a stale
// uvicorn still holding the previous bundle in an lru_cache, so a fix that was
// present in the artifact appeared to have failed. A test must never depend on a
// process it did not start.
module.exports = defineConfig({
  testDir: './e2e',
  timeout: 30000,
  fullyParallel: false,
  workers: 1,
  reporter: [['list']],
  use: { baseURL: base, screenshot: 'only-on-failure', trace: 'off' },
  webServer: {
    command: `"${python}" -m uvicorn galactico.api.player_lab:app --port ${port} --log-level warning`,
    url: `${base}/api/health`,
    reuseExistingServer: false,
    timeout: 120000,
    env: { PYTHONPATH: '.', PYTHONUTF8: '1' },
  },
});
