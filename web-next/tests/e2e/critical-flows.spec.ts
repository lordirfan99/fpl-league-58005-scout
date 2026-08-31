import { expect, test } from "@playwright/test";

const routes = ["/my-team", "/assistant", "/planner", "/journal", "/settings"];

for (const route of routes) {
  test(`${route} renders its primary navigation and content`, async ({ page }, testInfo) => {
    const severeConsoleErrors: string[] = [];
    page.on("console", (message) => {
      if (message.type() === "error") severeConsoleErrors.push(message.text());
    });
    const response = await page.goto(route, { waitUntil: "domcontentloaded" });
    expect(response?.status()).toBe(200);
    await expect(page.getByRole("main")).toBeVisible();
    const home = testInfo.project.name.includes("mobile")
      ? page.locator(".mobile-header").getByRole("link", { name: "Fantasy Scout" })
      : page.getByRole("link", { name: "Fantasy Scout home" });
    await expect(home).toBeVisible();
    await expect(page.locator("body")).not.toHaveCSS("font-family", "Times New Roman");
    expect(severeConsoleErrors).toEqual([]);
  });
}

test("journal opens a frozen archived gameweek", async ({ page }) => {
  await page.goto("/journal", { waitUntil: "domcontentloaded" });
  const archived = page.locator('a.journal-week[href="/journal/2026-27/gw/1"]');
  await expect(archived).toContainText("GW1");
  await archived.click();
  await expect(page).toHaveURL(/\/journal\/2026-27\/gw\/1$/);
  await expect(page.getByRole("heading", { name: "GW1 Review" })).toBeVisible();
  await expect(page.getByText("Complete research record")).toHaveCount(0);
});

test("season week navigation routes archive, live, planning and future weeks by purpose", async ({ page }) => {
  await page.goto("/journal", { waitUntil: "domcontentloaded" });
  await expect(page.getByRole("status")).toContainText("Requested GW2; showing the finalized GW1 archive");
  await page.locator("details.week-rail summary").click();
  const rail = page.locator("details.week-rail");
  await expect(rail.getByRole("link", { name: /GW1$/ })).toHaveAttribute("href", "/journal/2026-27/gw/1");
  await expect(rail.getByRole("link", { name: /GW2$/ })).toHaveAttribute("href", "/my-team");
  await expect(rail.getByRole("link", { name: /GW3$/ })).toHaveAttribute("href", "/assistant");
  await expect(rail.getByRole("link", { name: /GW4$/ })).toHaveAttribute("href", "/planner?gw=4");
});

test("mobile navigation exposes primary and overflow destinations", async ({ page }, testInfo) => {
  test.skip(!testInfo.project.name.includes("mobile"), "mobile-only control check");
  await page.goto("/my-team", { waitUntil: "domcontentloaded" });
  const mobileNav = page.getByRole("navigation", { name: "Mobile navigation" });
  await expect(mobileNav.getByRole("link", { name: "My Team" })).toBeVisible();
  const more = mobileNav.getByRole("button", { name: "More" });
  await expect(more).toBeEnabled();
  await more.click();
  await expect(more).toHaveAttribute("aria-expanded", "true");
  await expect(page.getByRole("link", { name: "Settings" })).toBeVisible();
});

test("player artwork resolves to an image or deterministic fallback", async ({ page }) => {
  await page.goto("/my-team", { waitUntil: "domcontentloaded" });
  const art = page.locator(".player-art").first();
  await expect(art).toBeVisible();
  await expect.poll(async () => art.evaluate((node) => {
    const image = node.querySelector("img") as HTMLImageElement | null;
    return Boolean((image && image.complete && image.naturalWidth > 0) || node.querySelector("span"));
  })).toBe(true);
});
