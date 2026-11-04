import { expect, test } from "@playwright/test";
import { readFile } from "node:fs/promises";
import path from "node:path";

const testPng = Buffer.from("iVBORw0KGgoAAAANSUhEUgAAABgAAAAQCAIAAACDRijCAAAAI0lEQVR4nGMM6NnHQA3ARBVTGEYNIgaMBjZhMBpGhMHgCyMAmPcBuih/SfoAAAAASUVORK5CYII=", "base64");
const password = "correct horse battery staple";

async function signUp(page: import("@playwright/test").Page, email: string) {
  await page.goto("/register");
  await page.getByRole("textbox", { name: "Full Name" }).fill("Browser Reviewer");
  await page.getByLabel("Username").fill(email.split("@")[0].replace(/[^A-Za-z0-9_]/g, "_").slice(0, 32));
  await page.getByLabel("Phone number").fill("3001234567");
  await page.getByLabel(/Email/).fill(email);
  await page.locator('input[name="password"]').fill(password);
  await page.locator('input[name="password_confirm"]').fill(password);
  await page.getByRole("button", { name: "Create account" }).click();
  await expect(page).toHaveURL(/\/login\?registered=1/);
  await page.locator('input[name="password"]').fill(password);
  await page.getByRole("button", { name: "Sign in" }).click();
  await expect(page.getByRole("heading", { name: "Forensic Intelligence Hub" })).toBeVisible();
}

test("auth screens share responsive styling, accessible password reveal, and real sign-in", async ({ page }) => {
  const email = `auth-review-${Date.now()}@example.com`;
  await page.setViewportSize({ width: 390, height: 760 });
  await page.goto("/register");

  await expect(page.getByRole("heading", { name: "Create your account" })).toBeVisible();
  await expect(page.getByRole("link", { name: "Back to home" })).toHaveAttribute("href", "/");
  await expect(page.getByText("Your reports are private to your account.")).toBeVisible();
  await page.evaluate(() => document.fonts.ready);
  const loadedFonts = await page.evaluate(() => ({
    poppins: document.fonts.check('500 13px "Poppins"'),
    cabinet: document.fonts.check('700 32px "Cabinet Grotesk"'),
  }));
  expect(loadedFonts).toEqual({ poppins: true, cabinet: true });
  await page.screenshot({ path: "../../.run/auth-signup-mobile.png", fullPage: true });
  for (const viewport of [{ width: 390, height: 760 }, { width: 768, height: 900 }, { width: 1440, height: 900 }]) {
    await page.setViewportSize(viewport);
    const layout = await page.evaluate(() => {
      const card = document.querySelector<HTMLElement>(".auth-card")?.getBoundingClientRect();
      const footer = document.querySelector<HTMLElement>(".auth-footer")?.getBoundingClientRect();
      const overflow = Array.from(document.querySelectorAll<HTMLElement>("body *"))
        .map((element) => ({ element: element.tagName, className: element.className, right: element.getBoundingClientRect().right }))
        .filter((element) => element.right > window.innerWidth + 1)
        .slice(0, 8);
      return { pageWidth: document.documentElement.scrollWidth, cardRight: card?.right, cardBottom: card?.bottom, footerTop: footer?.top, overflow };
    });
    expect(layout.pageWidth, JSON.stringify(layout.overflow)).toBeLessThanOrEqual(viewport.width);
    expect(layout.cardRight).toBeLessThanOrEqual(viewport.width);
    expect(layout.cardBottom).toBeLessThanOrEqual(layout.footerTop ?? 0);
  }

  await page.setViewportSize({ width: 390, height: 760 });
  const signupPassword = page.locator('input[name="password"]');
  await signupPassword.fill("short");
  expect(await signupPassword.evaluate((input: HTMLInputElement) => input.checkValidity())).toBe(false);
  const inputPresentation = await page.evaluate(() => {
    const input = document.querySelector<HTMLInputElement>('input[name="password"]');
    const caret = input?.parentElement?.querySelector<HTMLElement>(".smooth-input-caret");
    if (!input || !caret) return null;
    const inputRect = input.getBoundingClientRect();
    const caretRect = caret.getBoundingClientRect();
    return {
      textAlign: getComputedStyle(input).textAlign,
      caretCentered: Math.abs(inputRect.top + inputRect.height / 2 - (caretRect.top + caretRect.height / 2)) < 1,
      caretAnimation: getComputedStyle(caret).animationName,
      strengthLevel: document.querySelector(".auth-password-strength")?.getAttribute("data-level"),
    };
  });
  expect(inputPresentation).toEqual({ textAlign: "left", caretCentered: true, caretAnimation: "caret-blink", strengthLevel: "weak" });
  await signupPassword.fill(password);
  await page.locator('button[aria-controls="signup-password"]').click();
  await expect(signupPassword).toHaveAttribute("type", "text");
  await expect(signupPassword).toHaveValue(password);
  await page.locator('button[aria-controls="signup-password"]').click();
  await expect(signupPassword).toHaveAttribute("type", "password");
  await expect(signupPassword).toHaveValue(password);
  expect(await page.evaluate(() => document.documentElement.scrollWidth)).toBeLessThanOrEqual(390);

  await page.getByRole("textbox", { name: "Full Name" }).fill("Browser Reviewer");
  await page.getByLabel("Username").fill(email.split("@")[0].replace(/[^A-Za-z0-9_]/g, "_").slice(0, 32));
  await page.getByLabel("Phone number").fill("3001234567");
  await page.getByLabel(/Email/).fill(email);
  await page.locator('input[name="password_confirm"]').fill(password);
  await page.getByRole("button", { name: "Create account" }).click();
  await expect(page).toHaveURL(/\/login\?registered=1/);
  await expect(page.getByText(/Registration successful/)).toBeVisible();

  await page.locator('input[name="password"]').fill(password);
  await page.getByRole("button", { name: "Sign in" }).click();
  await expect(page).toHaveURL(/\/app$/);
  await expect(page.getByRole("heading", { name: "Forensic Intelligence Hub" })).toBeVisible();
  await expect(page.getByLabel("Cookie preferences")).toBeVisible();
  await page.getByRole("button", { name: "Reject" }).click();
  await page.setViewportSize({ width: 1280, height: 900 });
  await page.getByRole("button", { name: "Sign out" }).click();
  await expect(page).toHaveURL(/\/login(?:\?.*)?$/);

  await expect(page.getByRole("heading", { name: "Welcome back" })).toBeVisible();
  await expect(page.getByRole("link", { name: "Back to home" })).toHaveAttribute("href", "/");
  await page.setViewportSize({ width: 390, height: 760 });
  await page.screenshot({ path: "../../.run/auth-signin-mobile.png", fullPage: true });
  await expect(page.locator("html")).toHaveAttribute("data-theme", "light");
  const loginEmail = page.getByLabel("Email");
  await loginEmail.fill("");
  await page.locator('input[name="password"]').fill("short");
  await page.getByRole("button", { name: "Sign in" }).click();
  expect(await loginEmail.evaluate((input: HTMLInputElement) => input.checkValidity())).toBe(false);

  await loginEmail.fill(email);
  await page.evaluate(() => localStorage.removeItem("cgs-optional-cookie-choice"));
  await page.getByRole("button", { name: "Sign in" }).click();
  await expect(page.locator("#signin-error")).toContainText("Email or password is incorrect.");
  await page.locator('input[name="password"]').fill(password);
  await page.getByRole("button", { name: "Sign in" }).click();
  await expect(page.getByRole("heading", { name: "Forensic Intelligence Hub" })).toBeVisible();
  await expect(page.getByLabel("Cookie preferences")).toBeVisible();

  await page.goto(`/login?next=${encodeURIComponent(`/${String.fromCharCode(92)}attacker.example/landing`)}`);
  await page.getByLabel("Email").fill(email);
  await page.locator('input[name="password"]').fill(password);
  await page.getByRole("button", { name: "Sign in" }).click();
  await expect(page).toHaveURL("http://127.0.0.1:3100/app");
  await expect(page.getByRole("heading", { name: "Forensic Intelligence Hub" })).toBeVisible();
});

test("Explore menu stays open while moving the pointer into it", async ({ page }) => {
  await page.goto("/");
  await page.getByRole("button", { name: "Explore site pages" }).hover();
  const aboutLink = page.getByRole("navigation", { name: "Explore pages" }).getByRole("link", { name: "About us" });
  await expect(aboutLink).toBeVisible();
  await aboutLink.hover();
  await expect(aboutLink).toBeVisible();
  await aboutLink.click();
  await expect(page).toHaveURL(/\/about$/);
});

test("contact page keeps all inquiry controls usable", async ({ page }) => {
  await page.goto("/contact");
  await expect(page.getByRole("heading", { name: /careful review/ })).toBeVisible();
  await page.setViewportSize({ width: 390, height: 844 });
  expect(await page.evaluate(() => document.documentElement.scrollWidth)).toBeLessThanOrEqual(390);
  await page.getByLabel("Name").fill("Casey Reviewer");
  await page.getByLabel("Work or Contact Email").fill("casey@example.com");
  await page.getByLabel("Inquiry Category").selectOption("privacy");
  await page.getByLabel("Message").fill("I have a question about report privacy.");
  await page.getByRole("button", { name: /Send inquiry/ }).click();
  await expect(page.locator(".contact-success-card")).toBeVisible();
  await expect(page.locator(".contact-success-card").getByRole("heading", { name: "Inquiry Successfully Dispatched" })).toBeVisible();
});

test("auth panels respond to viewport width and small-screen navigation moves into the drawer", async ({ page }) => {
  await page.goto("/sign-in");
  for (const width of [320, 360, 390, 768, 1024, 1440]) {
    await page.setViewportSize({ width, height: 900 });
    const layout = await page.evaluate(() => {
      const visualElement = document.querySelector<HTMLElement>(".auth-visual")!;
      const visual = visualElement.getBoundingClientRect();
      const card = document.querySelector<HTMLElement>(".auth-card")!.getBoundingClientRect();
      const overflow = Array.from(document.querySelectorAll<HTMLElement>("body *"))
        .map((element) => ({ className: typeof element.className === "string" ? element.className : "", right: element.getBoundingClientRect().right }))
        .filter((element) => element.right > window.innerWidth + 1)
        .slice(0, 8);
      return {
        documentWidth: document.documentElement.scrollWidth,
        visualRight: visual.right,
        cardLeft: card.left,
        visualHidden: getComputedStyle(visualElement).display === "none",
        overflow,
      };
    });
    expect(layout.documentWidth, JSON.stringify(layout.overflow)).toBeLessThanOrEqual(width);
    if (width <= 900) {
      expect(layout.visualHidden).toBe(true);
    } else {
      expect(layout.visualHidden).toBe(false);
      expect(layout.visualRight).toBeLessThanOrEqual(layout.cardLeft + 1);
    }
  }

  await page.setViewportSize({ width: 390, height: 844 });
  await page.goto("/");
  const siteHeader = page.getByRole("banner");
  await expect(siteHeader.locator(".site-nav")).toBeHidden();
  await expect(siteHeader.locator(".header-actions")).toBeHidden();
  const menuToggle = page.getByRole("button", { name: "Open navigation" });
  await expect(menuToggle).toBeVisible();
  await menuToggle.click();
  const drawer = page.getByRole("dialog", { name: "Site navigation" });
  await expect(drawer).toBeVisible();
  await expect(drawer.getByRole("link", { name: "Technology" })).toBeVisible();
  await expect(drawer.getByRole("link", { name: "Get started" })).toBeVisible();
  await expect(page.locator(".mobile-menu-toggle")).toHaveClass(/is-open/);
  await expect(page.locator("html")).toHaveAttribute("data-theme", "light");
  await drawer.getByRole("link", { name: "Technology" }).click();
  await expect(page).toHaveURL(/\/technology$/);
});

test("home page adds review sections and renders the modern footer", async ({ page }) => {
  await page.goto("/");
  await expect(page.getByRole("heading", { name: "Start with what can be checked." })).toBeVisible();
  await expect(page.getByRole("heading", { name: "A report describes signals. It doesn’t decide authenticity." })).toBeVisible();

  for (const width of [320, 390, 768, 1440]) {
    await page.setViewportSize({ width, height: 900 });
    const footer = await page.locator(".site-footer-modern").evaluate((element) => {
      const rect = element.getBoundingClientRect();
      const style = getComputedStyle(element);
      return { documentWidth: document.documentElement.scrollWidth, left: rect.left, right: rect.right, paddingTop: style.paddingTop };
    });
    expect(footer.documentWidth).toBeLessThanOrEqual(width);
  }
});

test("register, upload, scan in the durable queue, open report, and delete", async ({ page }) => {
  const email = `reviewer-${Date.now()}@example.com`;
  await signUp(page, email);

  await page.goto("/app/analyze");
  await page.getByLabel("Choose an image or video file").setInputFiles({ name: "fixture.png", mimeType: "image/png", buffer: testPng });
  await page.getByRole("button", { name: /Execute Neural Forensics Screening/ }).click();

  await expect(page.getByRole("heading", { name: "Image Forensic Inspection Report" })).toBeVisible();
  await expect(page.getByRole("heading", { name: "Inconclusive / No Strong Signal" })).toBeVisible({ timeout: 30_000 });
  await expect(page.getByText("Deterministic automated-test fixture; never a production detector result.")).toBeVisible();
  await expect(page.getByText(/C2PA Manifest Status:/)).toBeVisible();

  page.once("dialog", dialog => dialog.accept());
  await page.getByRole("button", { name: "Purge Evidence" }).click();
  await expect(page).toHaveURL(/\/app\/history$/);
  await expect(page.getByRole("heading", { name: "No matching inspection records" })).toBeVisible();
});

test("guest can run repeated analyses without a balance or usage gate", async ({ page }) => {
  await page.goto("/app/analyze");
  await expect(page.getByRole("button", { name: /Execute Neural Forensics Screening/ })).toBeDisabled();
  await expect(page.getByText(/credits|points|balance/i)).toHaveCount(0);

  for (const name of ["guest-first.png", "guest-second.png"]) {
    await page.getByLabel("Choose an image or video file").setInputFiles({ name, mimeType: "image/png", buffer: testPng });
    await page.getByRole("button", { name: /Execute Neural Forensics Screening/ }).click();
    await expect(page.getByRole("heading", { name: "Image Forensic Inspection Report" })).toBeVisible();
    await page.goto("/app/analyze");
  }
  expect(await page.request.get("/api/v1/analyses").then((response) => response.json()).then((body) => body.total)).toBe(2);
});

test("IP restriction is shown as a blocking notice with a reference and recovery form", async ({ page }) => {
  await page.route("**/api/v1/account/status", (route) => route.fulfill({
    status: 200,
    contentType: "application/json",
    body: JSON.stringify({
      is_authenticated: false,
      email_verified: false,
      can_analyze: false,
      requires_email_verification: false,
      access_restricted: true,
      reference_id: "CGS-BLK-7F3K92",
      contact_email: "owner@example.com",
    }),
  }));
  await page.goto("/app/analyze");
  await expect(page.getByRole("alert").getByRole("heading", { name: "Access restricted" })).toBeVisible();
  await expect(page.getByText("CGS-BLK-7F3K92")).toBeVisible();
  await expect(page.getByRole("link", { name: "Contact CGS Owner" })).toHaveAttribute("href", /mailto:owner@example\.com/);
  await expect(page.getByText("Request access review", { exact: true })).toBeVisible();
  await expect(page.getByRole("button", { name: "Analysis unavailable" })).toBeDisabled();
});

test("public and guest analysis pages fit compact, standard, and ultra-wide viewports", async ({ page }) => {
  const routes = ["/", "/about", "/solutions", "/contact", "/privacy", "/register", "/app/analyze"];
  const widths = [320, 360, 390, 430, 640, 768, 980, 1024, 1440, 1920, 3840];
  const pageErrors: string[] = [];
  page.on("pageerror", (error) => pageErrors.push(error.message));

  for (const route of routes) {
    await page.goto(route, { waitUntil: "domcontentloaded" });
    for (const width of widths) {
      await page.setViewportSize({ width, height: width < 500 ? 720 : 1000 });
      const layout = await page.evaluate(() => ({
        viewport: window.innerWidth,
        document: document.documentElement.scrollWidth,
        body: document.body.scrollWidth,
        overflow: Array.from(document.querySelectorAll<HTMLElement>("body *"))
          .map((element) => {
            const rect = element.getBoundingClientRect();
            return {
              tag: element.tagName,
              className: typeof element.className === "string" ? element.className : "",
              left: Math.round(rect.left),
              right: Math.round(rect.right),
              scrollWidth: element.scrollWidth,
              clientWidth: element.clientWidth,
            };
          })
          .filter((element) => element.left < -1 || element.right > window.innerWidth + 1)
          .slice(0, 8),
      }));
      expect(layout.document, `${route} overflows at ${width}px: ${JSON.stringify(layout.overflow)}`).toBeLessThanOrEqual(width);
      expect(layout.body, `${route} body overflows at ${width}px: ${JSON.stringify(layout.overflow)}`).toBeLessThanOrEqual(width);
    }
  }
  expect(pageErrors).toEqual([]);
});

test("admin login is hidden from public navigation and server-gated", async ({ page }) => {
  await page.goto("/");
  await expect(page.locator('a[href="/admin"]')).toHaveCount(0);

  await page.goto("/admin");
  await expect(page).toHaveURL(/\/sign-in\?next=%2Fadmin$/);
  await expect(page.getByRole("heading", { name: "Operations overview" })).toHaveCount(0);

  const env = await readFile(path.resolve(process.cwd(), "../../.env"), "utf8");
  const adminSlug = env.match(/^ADMIN_LOGIN_SLUG=(.+)$/m)?.[1]?.trim();
  expect(adminSlug).toMatch(/^[A-Za-z0-9_-]{32,128}$/);
  await page.goto(`/admin/${adminSlug}`);
  await expect(page.getByRole("heading", { name: "Administrator sign in" })).toBeVisible();

  await page.getByLabel("Email").fill("admin@cgs-example.com");
  await page.locator('input[name="password"]').fill(password);
  await page.getByRole("button", { name: "Sign in to admin" }).click();
  await expect(page.getByRole("heading", { name: "Operations overview" })).toBeVisible();

  const overviewSections = await page.locator(".admin-section").evaluateAll((items) =>
    items.filter((item) => !(item as HTMLElement).hidden).map((item) => (item as HTMLElement).id),
  );
  expect(overviewSections).toEqual([]);
  await expect(page.locator(".admin-metric-grid[aria-label='Platform summary']")).toBeVisible();
  await expect(page.locator("#ledger")).toBeHidden();

  const sections = [
    { id: "ledger", label: "Inspection ledger", heading: "Inspection ledger" },
    { id: "users", label: "User management", heading: "User management" },
    { id: "control", label: "Control panel", heading: "Control panel" },
    { id: "contacts", label: "Contact inbox", heading: "Contact inbox" },
    { id: "admins", label: "Admin management", heading: "Admin management" },
    { id: "user-logs", label: "User logs", heading: "User logs" },
    { id: "admin-logs", label: "Admin logs", heading: "Admin logs" },
    { id: "security", label: "Security monitoring", heading: "Security monitoring" },
    { id: "traffic", label: "Traffic management", heading: "Traffic management" },
    { id: "settings", label: "Settings", heading: "Settings" },
  ];
  for (const section of sections) {
    await page.getByRole("link", { name: new RegExp(section.label, "i") }).click();
    await expect(page).toHaveURL(new RegExp(`#${section.id}$`));
    await expect(page.locator(`#${section.id}`)).toBeVisible();
    await expect(page.locator(`#${section.id}`).getByRole("heading", { name: section.heading })).toBeVisible();
    const visibleSections = await page.locator(".admin-section").evaluateAll((items) =>
      items.filter((item) => !(item as HTMLElement).hidden).map((item) => (item as HTMLElement).id),
    );
    expect(visibleSections).toEqual([section.id]);
  }

  const inviteEmail = `administrator-${Date.now()}@example.com`;
  await page.getByRole("link", { name: /Admin management/i }).click();
  await page.getByLabel("Administrator email").fill(inviteEmail);
  await page.getByRole("button", { name: "Create or invite admin" }).click();
  await expect(page.locator(".admin-admin-invite-link")).toBeVisible();
  await expect(page.getByRole("button", { name: "Cancel invite" })).toBeVisible();
  await page.getByRole("button", { name: "Cancel invite" }).click();
  await expect(page.getByText("No pending administrator invitations.")).toBeVisible();
  await expect(page.locator(".admin-admin-invite-link")).toHaveCount(0);

  await page.getByRole("link", { name: /User logs/i }).click();
  await page.getByLabel("Search user logs").fill("account.login");
  await page.getByRole("button", { name: "Search user logs" }).click();
  await expect(page.locator(".admin-audit-row").filter({ hasText: "account · login" }).first()).toBeVisible();
  const userLogConfirmation = page.locator("#user-logs .admin-log-clear-card input");
  await userLogConfirmation.fill("DELETE ALL USER LOGS");
  await page.getByRole("button", { name: "Delete all user logs" }).click();
  await expect(page.locator(".admin-alert--success")).toContainText("user log entr");
  await expect(page.locator("#user-logs .admin-empty-state")).toContainText("No user activity matches this search.");

  await page.getByRole("link", { name: /Admin logs/i }).click();
  await page.getByLabel("Search administrator logs").fill("admin.login");
  await page.getByRole("button", { name: "Search admin logs" }).click();
  await expect(page.locator(".admin-audit-row").filter({ hasText: "admin · login" }).first()).toBeVisible();
  const adminLogConfirmation = page.locator("#admin-logs .admin-log-clear-card input");
  await adminLogConfirmation.fill("DELETE ALL ADMIN LOGS");
  await page.getByRole("button", { name: "Delete all admin logs" }).click();
  await expect(page.locator(".admin-alert--success")).toContainText("admin log entr");
  await expect(page.locator("#admin-logs .admin-audit-row")).toHaveCount(1);
});

test("a normal account cannot view administrator tools", async ({ page }) => {
  await signUp(page, `user-${Date.now()}@example.com`);
  await page.goto("/admin");
  await expect(page).toHaveURL(/\/app$/);
  await expect(page.getByRole("heading", { name: "Operations overview" })).toHaveCount(0);
});
