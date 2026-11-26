const { test, expect } = require("@playwright/test");

const rows = (page) => page.locator("#packages .row.pkg:not(.head)");

test.describe("главная: платформы и flavor", () => {
  test.beforeEach(async ({ page }) => {
    await page.goto("/");
    await expect(page.locator("#platforms .row.plat:not(.head)")).toHaveCount(3);
  });

  test("шапка, flavor и три платформы", async ({ page }) => {
    await expect(page.locator("h1")).toHaveText("ipk farm");
    await expect(page.locator("#flavors button")).toHaveCount(2);
    await expect(page.locator("#platforms [data-plat]")).toHaveCount(3);
  });

  test("выбор платформы меняет конфиг opkg", async ({ page }) => {
    await page.locator('[data-plat="r2"]').click();
    await expect(page.locator(".row.plat.sel")).toHaveAttribute("data-plat", "r2");
    await expect(page.locator("#cfgmeta")).toContainText("mt02");
    await expect(page.locator("#cfg")).toContainText("ramips/mt7620");
    await expect(page.locator("#cfg")).toContainText("src/gz openwrt_core");
  });

  test("donyx переключает на iRM, а для IRZ iRM недоступен", async ({ page }) => {
    await page.locator('#flavors button[data-flavor="donyx"]').click();
    await expect(page.locator("#feedname")).toContainText("donyx");
    await expect(page.locator(".row.plat.sel")).toHaveAttribute("data-plat", "irm");

    await page.locator('#flavors button[data-flavor="irz"]').click();
    await expect(page.locator('[data-plat="irm"]')).toHaveClass(/na/);
    await expect(page.locator('[data-plat="irm"]')).toContainText("только dnxOS");
    await expect(page.locator(".row.plat.sel")).toHaveAttribute("data-plat", "r50");
  });

  test("шестерёнка ведёт на страницу платформы", async ({ page }) => {
    await page.locator('[data-gear="r50"]').click();
    await expect(page).toHaveURL(/\/platform\/r50$/);
    await expect(page.locator("#pname")).toContainText("r50");
    await expect(page.locator("#dotconfig")).toHaveValue(/# OpenWrt Configuration/);
    await expect(page.locator("#deleteplat")).toBeVisible();
  });
});

test.describe("главная: пакеты", () => {
  test.beforeEach(async ({ page }) => {
    await page.goto("/");
    await expect(rows(page).first()).toBeVisible();
  });

  test("поиск по имени и фильтр «не в сборке»", async ({ page }) => {
    await page.locator("#q").fill("hello");
    await expect(rows(page).first()).toContainText("hello");
    expect(await rows(page).count()).toBeGreaterThanOrEqual(2); // cmhello, hello, libhello

    await page.locator("#q").fill("");
    await page.locator('#pfilters [data-f="outside"]').click();
    await expect(rows(page).first()).toContainText("не в сборке");
    expect(await rows(page).count()).toBeGreaterThan(0);
    expect(await page.locator("#packages .row.pkg:not(.head)").allTextContents()).toEqual(
      expect.arrayContaining([expect.stringContaining("hello")])
    );
  });

  test("галочки: «Собрать все» заменяется на «Собрать · 2»", async ({ page }) => {
    const boxes = page.locator("#packages [data-chk]:not([disabled])");
    await boxes.nth(0).check();
    await expect(page.locator("#rebuild")).toBeHidden();
    await boxes.nth(1).check();
    await expect(page.locator("#rebuild")).toBeVisible();
    await expect(page.locator("#rebuild")).toContainText("Собрать · 2");
    await expect(page.locator("#build")).toBeHidden();
  });

  test("выбор строки даёт кнопку «Собрать» и не ломает копирование", async ({ page }) => {
    const row = page.locator('#packages .row.pkg[data-name="halo"]');
    await row.click();
    await expect(row).toHaveClass(/sel/);
    await expect(row.locator("[data-one]")).toHaveText("Собрать");

    const text = await row.locator(".name").textContent();
    await row.locator(".name").click({ clickCount: 3 });
    const selected = await page.evaluate(() => window.getSelection().toString());
    expect(selected.includes(text) || selected.length > 0).toBeTruthy();
  });

  test("кнопка «Собрать» отправляет пакет и платформу", async ({ page }) => {
    let body = null;
    await page.route("**/api/build", async (route) => {
      body = route.request().postDataJSON();
      await route.fulfill({ json: { started: true } });
    });
    const row = page.locator('#packages .row.pkg[data-name="halo"]');
    await row.click();
    await row.locator("[data-one]").click();
    await expect.poll(() => body).not.toBeNull();
    expect(body.packages).toEqual(["halo"]);
    expect(body.flavor).toBe("irz");
    expect(body.platform).toBeTruthy();
  });

  test("таб customfeeds содержит только наш фид", async ({ page }) => {
    await page.locator('#cfgtabs [data-kind="custom"]').click();
    await expect(page.locator("#cfg")).toContainText("src/gz halo");
    await expect(page.locator("#cfg")).not.toContainText("src/gz openwrt_core");
  });

  test("выбор пакета показывает репозиторий и коммит", async ({ page }) => {
    await page.locator('#packages .row.pkg[data-name="zenith-uc"]').click();
    await expect(page.locator("#uptitle")).toContainText("horizon-uc", { timeout: 60_000 });
    await expect(page.locator("#commits .commit.hit")).toContainText("30cc82f");
    await expect(page.locator("#upback")).toBeVisible();
    await page.locator("#upback").click();
    await expect(page.locator("#uptitle")).toContainText("wrtnavsegda");
  });
});

test.describe("новые страницы", () => {
  test("кнопка «＋ платформа» ведёт на форму", async ({ page }) => {
    await page.goto("/");
    await page.locator("#addplat").click();
    await expect(page).toHaveURL(/\/platform\/new$/);
    await expect(page.locator("#name")).toBeVisible();
  });

  test("форма новой платформы: target задаёт arch", async ({ page }) => {
    await page.goto("/platform/new");
    await expect(page.locator("#archline")).toContainText("mipsel_24kc");
    await page.locator("#target").selectOption("ipq40xx/generic|arm_cortex-a7_neon-vfpv4");
    await expect(page.locator("#archline")).toContainText("arm_cortex-a7_neon-vfpv4");
  });

  test("источник SDK переключается: git / готовый архив", async ({ page }) => {
    await page.goto("/platform/new");
    await expect(page.locator("#src-git")).toBeVisible();
    await expect(page.locator("#create")).toHaveText("Собрать SDK");
    await expect(page.locator("#srccost")).toContainText("4–8 часов");
    await page.locator('#srctabs [data-src="archive"]').click();
    await expect(page.locator("#src-archive")).toBeVisible();
    await expect(page.locator("#src-git")).toBeHidden();
    await expect(page.locator("#create")).toHaveText("Скачать и добавить");
    await expect(page.locator("#urlpreview")).toContainText("downloads.openwrt.org");
  });

  test("неверное имя не запускает подготовку SDK", async ({ page }) => {
    await page.goto("/platform/new");
    await page.locator("#name").fill("TEST-UI");
    await page.locator("#create").click();
    await expect(page.locator("#err")).toContainText("имя");
    await expect(page.locator("#addform")).toBeVisible();
  });

  test("страница сборки показывает манифест и лог", async ({ page }) => {
    await page.goto("/build/2");
    await expect(page.locator("#btitle")).toContainText("Сборка #2");
    await expect(page.locator("#bpackages .row.brow")).toHaveCount(3); // шапка + 2 пакета
    await expect(page.locator("#blog")).toContainText("build #2");
  });
});

test.describe("страница платформы", () => {
  test.beforeEach(async ({ page }) => {
    await page.goto("/platform/r50");
    await expect(page.locator("#pname")).toContainText("r50");
  });

  test("параметры и .config заполнены", async ({ page }) => {
    await expect(page.locator("#sdk")).toHaveValue(/sdk24-r50/);
    await expect(page.locator("#feeds")).toHaveValue(/feeds\/r50\.conf/);
    await expect(page.locator("#dotconfig")).toHaveValue(/CONFIG_/);
  });

  test("операции подписаны действиями", async ({ page }) => {
    const buttons = page.locator("#ops button");
    await expect(buttons).toHaveCount(5);
    await expect(buttons.nth(0)).toHaveText("обновить фиды");
    await expect(buttons.nth(1)).toHaveText("установить все пакеты фидов");
    await expect(buttons.nth(4)).toHaveText("собрать образ прошивки");
    await expect(buttons.nth(3)).toBeDisabled(); // SDK не git
  });

  test("фиды SDK и поиск пакетов", async ({ page }) => {
    await expect(page.locator("#feedchips")).toContainText("halo");
    await page.locator("#pkgq").fill("transmission");
    const hit = page.locator(".pkgrow", { hasText: "transmission-daemon" }).first();
    await expect(hit).toBeVisible({ timeout: 30_000 });
    await expect(hit.locator("button")).toBeVisible();
  });
});
