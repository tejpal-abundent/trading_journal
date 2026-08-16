import { test, expect } from "@playwright/test";

const ROUTES = [
  ["/", "Today"],
  ["/ledger", "Ledger"],
  ["/performance", "Performance"],
  ["/monthly", "Monthly"],
  ["/attribution", "Attribution"],
  ["/policy", "Risk Policy"],
  ["/accounts", "Accounts"],
  ["/audit", "Audit"],
  ["/settings", "Settings"],
] as const;

for (const [path, headline] of ROUTES) {
  test(`${path} renders headline ${headline}`, async ({ page }) => {
    await page.goto(`http://localhost:5174/tej-capital${path}`);
    await expect(page.getByRole("heading", { name: headline })).toBeVisible();
  });
}
