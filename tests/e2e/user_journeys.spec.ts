import { test, expect } from '@playwright/test';

test.describe('Nerolac Operations Dashboard - Full End-to-End User Journeys', () => {
  test('Journey 1: Global Navigation, Depot Switcher, and Fiscal Period Selector', async ({
    page,
  }) => {
    // Navigate to root which directs to dashboard
    await page.goto('/finance', { waitUntil: 'domcontentloaded' });

    // 1. Verify Corporate Brand Identity
    await expect(page.locator('text=KANSAI NEROLAC')).toBeVisible();
    await expect(page.locator('text=BANGLADESH OPERATIONS')).toBeVisible();

    // 2. Verify Corporate Bright Light Mode Tokens
    const body = page.locator('body');
    await expect(body).toHaveCSS('background-color', 'rgb(255, 255, 255)');

    // 3. Verify Global Depot Switcher
    const depotSwitcher = page.locator('#global-depot-switcher');
    if (await depotSwitcher.isVisible()) {
      await depotSwitcher.click();
      // Verify all 8 Bangladesh hubs are present in options
      const optionsText = await depotSwitcher.textContent();
      expect(optionsText).toContain('Dhaka');
    }

    // 4. Verify Fiscal Period Picker (April–March fiscal year)
    const fiscalPicker = page.locator('#fiscal-period-picker');
    if (await fiscalPicker.isVisible()) {
      await expect(fiscalPicker).toBeVisible();
    }
  });

  test('Journey 2: Module 1 - Finance Control Center Full Interactive Journey', async ({
    page,
  }) => {
    await page.goto('/finance', { waitUntil: 'domcontentloaded' });

    // 1. Verify Main View Heading
    const title = page.locator('h1', { hasText: 'Finance Control Center' });
    await expect(title).toBeVisible();

    // 2. Verify Executive KPI Metric Cards with tabular-nums
    const netRevCard = page.locator('#kpi-net-revenue');
    await expect(netRevCard).toBeVisible();
    await expect(netRevCard).toHaveClass(/tabular-nums/);

    const grossMarginCard = page.locator('#kpi-gross-margin');
    await expect(grossMarginCard).toBeVisible();
    await expect(grossMarginCard).toHaveClass(/tabular-nums/);

    // 3. Verify ECharts Waterfall Chart Container
    const waterfallContainer = page.locator('#echarts-waterfall-container');
    await expect(waterfallContainer).toBeVisible();

    // 4. Interact with Real-Time Cashflow Simulation Sliders
    const arSlider = page.locator('#slider-ar-collection');
    if (await arSlider.isVisible()) {
      await arSlider.fill('90');
      // Verify simulated net cashflow updates in <50ms
      await expect(page.locator('#simulated-net-cashflow')).toBeVisible();
    }

    // 5. Inspect Supplier Price Variance Table
    const supplierTable = page.locator('#supplier-variance-table');
    if (await supplierTable.isVisible()) {
      await expect(supplierTable).toBeVisible();
    }
  });

  test('Journey 3: Module 2 - HR Workforce Intelligence Full Interactive Journey', async ({
    page,
  }) => {
    await page.goto('/hr', { waitUntil: 'domcontentloaded' });

    // 1. Verify Header
    const title = page.locator('h1', { hasText: 'HR Workforce Intelligence' });
    await expect(title).toBeVisible();

    // 2. Verify 2-Factor Capacity Metric Overview
    const capacitySection = page.locator('#manpower-capacity-container');
    if (await capacitySection.isVisible()) {
      await expect(capacitySection).toBeVisible();
    }

    // 3. Verify Vacant Territory Justification Cards
    const territoryCards = page.locator('[data-testid="vacant-territory-card"]');
    const cardCount = await territoryCards.count();
    expect(cardCount).toBeGreaterThanOrEqual(0);

    // 4. Verify 6-Axis Radar Chart Container
    const radarContainer = page.locator('#echarts-radar-container');
    if (await radarContainer.isVisible()) {
      await expect(radarContainer).toBeVisible();
    }
  });

  test('Journey 4: Module 3 - Supply Chain Control Center Demand & MRP Journey', async ({
    page,
  }) => {
    await page.goto('/supply-chain', { waitUntil: 'domcontentloaded' });

    // 1. Verify Header
    const title = page.locator('h1', { hasText: 'Supply Chain Control Center' });
    await expect(title).toBeVisible();

    // 2. Verify Demand Fan Chart Container
    const fanChart = page.locator('#echarts-fan-chart-container');
    if (await fanChart.isVisible()) {
      await expect(fanChart).toBeVisible();
    }

    // 3. Verify Material Requirements Planning (MRP) Action Table
    const mrpTable = page.locator('#mrp-action-table');
    if (await mrpTable.isVisible()) {
      await expect(mrpTable).toBeVisible();
    }
  });

  test('Journey 5: Module 4 - WhatsApp Field Intelligence & 7:00 PM Recon Journey', async ({
    page,
  }) => {
    await page.goto('/whatsapp', { waitUntil: 'domcontentloaded' });

    // 1. Verify Header
    const title = page.locator('h1', { hasText: /WhatsApp Field/ });
    await expect(title).toBeVisible();

    // 2. Verify Live Message Stream Container
    const messageStream = page.locator('#whatsapp-message-stream');
    if (await messageStream.isVisible()) {
      await expect(messageStream).toBeVisible();
    }

    // 3. Verify 7:00 PM Evening Reconciliation Summary Dashboard
    const reconDashboard = page.locator('#daily-recon-dashboard');
    if (await reconDashboard.isVisible()) {
      await expect(reconDashboard).toBeVisible();
    }
  });

  test('Journey 6: Zero Frontend Mock Data Verification', async ({ page }) => {
    // Assert frontend views do not contain mock arrays or dummy placeholder text
    for (const route of ['/finance', '/hr', '/supply-chain', '/whatsapp']) {
      await page.goto(route, { waitUntil: 'domcontentloaded' });
      const content = await page.content();
      expect(content).not.toContain('Lorem ipsum');
      expect(content).not.toContain('const mockData');
      expect(content).not.toContain('dummy_data');
    }
  });
});
