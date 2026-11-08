/**
 * Browser smoke: Members & Access UI surfaces authorized client engagement controls.
 * Requires frontend on E2E_FRONTEND_BASE (default http://localhost:3000).
 */
import { chromium } from "playwright";

const FRONTEND = (process.env.E2E_FRONTEND_BASE || "http://localhost:3000").replace(/\/$/, "");
const EMAIL = process.env.E2E_BROWSER_EMAIL || "demo@studio.com";
const PASSWORD = process.env.E2E_BROWSER_PASSWORD || "password123";

async function main() {
  const browser = await chromium.launch({ headless: true });
  const page = await browser.newPage();
  const failures = [];

  try {
    await page.goto(FRONTEND, { waitUntil: "networkidle", timeout: 60000 });

    // Login form
    const email = page.locator("#login-email");
    const password = page.locator("#login-password");
    if (await email.count()) {
      await email.fill(EMAIL);
      await password.fill(PASSWORD);
      await page.locator('button[type="submit"]').first().click();
      await page.waitForTimeout(3000);
    }

    const membersTab = page.getByRole("button", { name: /Members & Access/i });
    await membersTab.waitFor({ timeout: 20000 });
    await membersTab.click();
    await page.waitForTimeout(1000);

    const heading = page.getByText(/Workspace members & access/i);
    if (!(await heading.count())) {
      failures.push("Members panel heading not visible");
    }

    const addSection = page.getByText(/Authorized client engagements/i);
    // Role select exists; switch to client viewer to reveal engagement checkboxes.
    const roleSelect = page.locator("select").filter({ hasText: /Client \/ Viewer|Consultant/ }).first();
    if (await roleSelect.count()) {
      await roleSelect.selectOption("client_viewer");
      await page.waitForTimeout(400);
      if (!(await addSection.count())) {
        failures.push("authorized_client_ids checkbox section not shown for client_viewer");
      } else {
        console.log("[PASS] authorized_client_ids UI visible for client_viewer role");
      }
    } else {
      // Fallback: any select in members panel
      const selects = page.locator("select");
      if (await selects.count()) {
        await selects.first().selectOption("client_viewer");
        await page.waitForTimeout(400);
      }
      if (!(await page.getByText(/Authorized client engagements/i).count())) {
        failures.push("Could not reveal authorized client engagements controls");
      } else {
        console.log("[PASS] authorized_client_ids UI visible for client_viewer role");
      }
    }

    if (!(await page.getByRole("button", { name: /Add member/i }).count())) {
      failures.push("Add member button missing");
    } else {
      console.log("[PASS] Add member control present");
    }
  } catch (err) {
    failures.push(String(err));
  } finally {
    await browser.close();
  }

  if (failures.length) {
    console.error("[FAIL] Browser members smoke failed:");
    for (const f of failures) console.error(" -", f);
    process.exit(1);
  }
  console.log("[PASS] Browser Members & Access smoke completed");
}

main();
