import { test, expect } from '@playwright/test';

test.describe('Bright Light Corporate Design System, Global TopBar & Monospaced Typography Audit', () => {
  test.beforeEach(async ({ page }) => {
    // Navigate to dashboard root / finance page
    await page.goto('/finance', { waitUntil: 'networkidle' });
  });

  test('should assert 100% compliance with Bright Light Corporate Mode tokens and strict 1px borders', async ({
    page,
  }) => {
    // 1. Primary Canvas Background: Pure White #FFFFFF
    const body = page.locator('body');
    await expect(body).toHaveCSS('background-color', 'rgb(255, 255, 255)');

    // 2. Sidebar Container: Warm Slate #F8FAFC with strict 1px solid #E2E8F0 border-right
    const sidebar = page.locator('aside');
    await expect(sidebar).toBeVisible();
    await expect(sidebar).toHaveCSS('background-color', 'rgb(248, 250, 252)');
    await expect(sidebar).toHaveCSS('border-right-width', '1px');
    await expect(sidebar).toHaveCSS('border-right-style', 'solid');
    await expect(sidebar).toHaveCSS('border-right-color', 'rgb(226, 232, 240)');

    // 3. Brand Accent: Kansai Nerolac Corporate Red #D32F2F
    const brandBlock = sidebar.locator('div').filter({ hasText: 'KANSAI NEROLAC' }).first();
    await expect(brandBlock).toBeVisible();
    const brandLogo = page.locator('#nerolac-brand-logo-mark');
    await expect(brandLogo).toBeVisible();
    await expect(brandLogo).toHaveCSS('background-color', 'rgb(211, 47, 47)');

    // 4. Global Top Bar: Strict 1px solid #E2E8F0 border-bottom and #FFFFFF background
    const topbar = page.locator('#global-topbar');
    await expect(topbar).toBeVisible();
    await expect(topbar).toHaveCSS('background-color', 'rgb(255, 255, 255)');
    await expect(topbar).toHaveCSS('border-bottom-width', '1px');
    await expect(topbar).toHaveCSS('border-bottom-style', 'solid');
    await expect(topbar).toHaveCSS('border-bottom-color', 'rgb(226, 232, 240)');

    // 5. Verify Zero Dark Mode, Zero Glassmorphism, Zero Floating Gradients on root layout
    const glassCheck = await page.evaluate(() => {
      const el = document.getElementById('global-topbar');
      if (!el) return { backdropFilter: 'none', bgImage: 'none' };
      const comp = window.getComputedStyle(el);
      return {
        backdropFilter: comp.backdropFilter || 'none',
        bgImage: comp.backgroundImage || 'none',
      };
    });
    expect(glassCheck.backdropFilter).toBe('none');
    expect(glassCheck.bgImage).not.toContain('gradient');
  });

  test('should render 1-click Global Depot Switcher with all 8 operational depots', async ({
    page,
  }) => {
    // 1. Verify Depot Switcher Container exists in Global Top Bar
    const switcherContainer = page.locator('#global-depot-switcher-container');
    await expect(switcherContainer).toBeVisible();
    await expect(switcherContainer).toHaveCSS('border-width', '1px');
    await expect(switcherContainer).toHaveCSS('border-color', 'rgb(226, 232, 240)');

    // 2. Verify Depot Select Dropdown has all required 8 regional depots
    const depotSelect = page.locator('#global-depot-switcher');
    await expect(depotSelect).toBeVisible();

    const requiredDepots = [
      { id: 'DEPOT_01', name: 'Dhaka' },
      { id: 'DEPOT_02', name: 'Chittagong' },
      { id: 'DEPOT_04', name: 'Sylhet' },
      { id: 'DEPOT_03', name: 'Bogra' },
      { id: 'DEPOT_06', name: 'Rajshahi' },
      { id: 'DEPOT_05', name: 'Khulna' },
      { id: 'DEPOT_07', name: 'Mymensingh' },
      { id: 'DEPOT_08', name: 'Comilla' },
    ];

    for (const depot of requiredDepots) {
      const option = depotSelect.locator(`option[value="${depot.id}"]`);
      await expect(option).toHaveCount(1);
    }

    // 3. Test 1-click switching to Chittagong
    await depotSelect.selectOption('DEPOT_02');
    const activeBadge = page.locator('#active-depot-badge');
    await expect(activeBadge).toHaveText('Chittagong');
    await expect(activeBadge).toHaveCSS('color', 'rgb(211, 47, 47)'); // Nerolac Red

    // 4. Test 1-click switching to Dhaka
    await depotSelect.selectOption('DEPOT_01');
    await expect(activeBadge).toHaveText('Dhaka');

    // 5. Test 1-click switching to Bogra & Khulna
    await depotSelect.selectOption('DEPOT_03');
    await expect(activeBadge).toHaveText('Bogra');

    await depotSelect.selectOption('DEPOT_05');
    await expect(activeBadge).toHaveText('Khulna');
  });

  test('should render April–March Fiscal Period Picker with year and period selection', async ({
    page,
  }) => {
    // 1. Verify Fiscal Period Picker Container
    const fiscalPicker = page.locator('#fiscal-period-picker');
    await expect(fiscalPicker).toBeVisible();
    await expect(fiscalPicker.locator('text=Fiscal (Apr–Mar):')).toBeVisible();

    // 2. Verify Fiscal Year Dropdown (April–March convention)
    const fySelect = page.locator('#fiscal-year-select');
    await expect(fySelect).toBeVisible();
    await expect(fySelect.locator('option[value="FY2026_27"]')).toHaveText(/FY 2026–27/);
    await expect(fySelect.locator('option[value="FY2025_26"]')).toHaveText(/FY 2025–26/);

    // 3. Verify Fiscal Period Dropdown (P01 Apr to P12 Mar + Quarters)
    const periodSelect = page.locator('#fiscal-period-select');
    await expect(periodSelect).toBeVisible();
    await expect(periodSelect.locator('option[value="P01"]')).toHaveText(/P01 - April/);
    await expect(periodSelect.locator('option[value="P07"]')).toHaveText(/P07 - October/);
    await expect(periodSelect.locator('option[value="P12"]')).toHaveText(/P12 - March/);
    await expect(periodSelect.locator('option[value="Q1"]')).toHaveText(/Q1 \(Apr–Jun\)/);

    // 4. Test Selecting Q2 (Jul–Sep)
    await periodSelect.selectOption('Q2');
    await expect(periodSelect).toHaveValue('Q2');

    // 5. Switch back to current period P07
    await periodSelect.selectOption('P07');
    await expect(periodSelect).toHaveValue('P07');
  });

  test('should render User SSO Role Badge with role switching and sovereign node status', async ({
    page,
  }) => {
    // 1. Verify SSO Role Badge Container
    const ssoBadge = page.locator('#user-sso-role-badge');
    await expect(ssoBadge).toBeVisible();
    await expect(ssoBadge).toHaveCSS('border-width', '1px');
    await expect(ssoBadge).toHaveCSS('border-color', 'rgb(226, 232, 240)');

    // 2. Verify SSO Identity & Sovereign Provider Info
    await expect(ssoBadge.locator('text=Azure AD SSO (Sovereign)')).toBeVisible();

    // 3. Verify Role Selector has enterprise roles
    const roleSelect = page.locator('#sso-role-select');
    await expect(roleSelect).toBeVisible();
    await expect(roleSelect).toHaveValue('FINANCE_DIRECTOR');

    // 4. Test Role Switching to SUPPLY_CHAIN_HEAD
    await roleSelect.selectOption('SUPPLY_CHAIN_HEAD');
    await expect(roleSelect).toHaveValue('SUPPLY_CHAIN_HEAD');
    await expect(ssoBadge.locator('text=Tariqul Islam')).toBeVisible();

    // 5. Test Role Switching to MANAGING_DIRECTOR
    await roleSelect.selectOption('MANAGING_DIRECTOR');
    await expect(roleSelect).toHaveValue('MANAGING_DIRECTOR');
    await expect(ssoBadge.locator('text=Shabir Ahmed')).toBeVisible();

    // Switch back to FINANCE_DIRECTOR
    await roleSelect.selectOption('FINANCE_DIRECTOR');
    await expect(roleSelect).toHaveValue('FINANCE_DIRECTOR');
  });

  test('should enforce monospaced and tabular-nums typography on numeric data values', async ({
    page,
  }) => {
    // 1. Verify tabular-nums enforcement on financial metrics
    const kpiElements = page.locator('.tabular-nums, table td, .kpi-value');
    const count = await kpiElements.count();
    expect(count).toBeGreaterThan(0);

    // 2. Check computed CSS font-variant-numeric
    const sampleTabularEl = kpiElements.first();
    const fontVariantNumeric = await sampleTabularEl.evaluate(
      (el) => window.getComputedStyle(el).fontVariantNumeric
    );
    expect(fontVariantNumeric).toContain('tabular-nums');

    // 3. Verify TopBar currency badge enforces tabular numbers
    const currencyBadge = page.locator('text=BDT (৳)');
    await expect(currencyBadge).toBeVisible();
    const currencyVariant = await currencyBadge.evaluate(
      (el) => window.getComputedStyle(el).fontVariantNumeric
    );
    expect(currencyVariant).toContain('tabular-nums');
  });

  test('should maintain consistent Bright Light Corporate Mode and TopBar across all dashboard pages', async ({
    page,
  }) => {
    const pagesToTest = ['/whatsapp', '/supply-chain', '/hr', '/finance'];

    for (const path of pagesToTest) {
      await page.goto(path, { waitUntil: 'networkidle' });

      // Verify canvas background is Pure White
      const body = page.locator('body');
      await expect(body).toHaveCSS('background-color', 'rgb(255, 255, 255)');

      // Verify Global Top Bar is present with all 3 widgets
      const topbar = page.locator('#global-topbar');
      await expect(topbar).toBeVisible();
      await expect(page.locator('#global-depot-switcher-container')).toBeVisible();
      await expect(page.locator('#fiscal-period-picker')).toBeVisible();
      await expect(page.locator('#user-sso-role-badge')).toBeVisible();
    }
  });
});
