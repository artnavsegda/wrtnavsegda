const { defineConfig } = require("@playwright/test");

module.exports = defineConfig({
  testDir: "./tests",
  timeout: 90_000,
  expect: { timeout: 20_000 },
  fullyParallel: false,
  workers: 1,
  reporter: [["list"]],
  use: {
    baseURL: process.env.FARM_URL || "http://192.168.245.248:8099",
    channel: process.env.FARM_BROWSER || "chrome",
    headless: true,
    viewport: { width: 1440, height: 900 },
    ignoreHTTPSErrors: true,
  },
});
