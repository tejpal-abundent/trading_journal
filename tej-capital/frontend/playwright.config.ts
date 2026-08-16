import { defineConfig } from "@playwright/test";

export default defineConfig({
  webServer: {
    command: "npm run dev",
    url: "http://localhost:5174/tej-capital/",
    timeout: 60_000,
    reuseExistingServer: !process.env.CI,
  },
  use: { baseURL: "http://localhost:5174" },
  testDir: "tests",
});
