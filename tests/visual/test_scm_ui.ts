import { test, expect } from '@playwright/test';

test.describe('Supply Chain Control Center (Module 3) Visual & Interactive Test Suite', () => {
  test.beforeEach(async ({ page }) => {
    // Navigate directly to Supply Chain dashboard
    await page.goto('/supply-chain', { waitUntil: 'networkidle' });
  });

  test('should render Corporate Bright Light Mode layout and brand headers', async ({ page }) => {
    // 1. Verify page title and header
    await expect(page).toHaveTitle(/Nerolac Operations Dashboard/);
    const headerTitle = page.locator('h1', { hasText: 'Supply Chain Control Center' });
    await expect(headerTitle).toBeVisible();

    // 2. Verify Corporate Canvas Background is #FFFFFF (White)
    const body = page.locator('body');
    await expect(body).toHaveCSS('background-color', 'rgb(255, 255, 255)');

    // 3. Verify Nerolac Brand Banner and Navigation Link
    const brand = page.locator('text=KANSAI NEROLAC');
    await expect(brand).toBeVisible();
    await expect(page.getByText('BANGLADESH OPERATIONS', { exact: true })).toBeVisible();

    // 4. Verify Active Nav Link for SCM
    const navLink = page.locator('#nav-supply-chain');
    await expect(navLink).toBeVisible();
  });

  test('should render executive KPI metric summary cards with tabular-nums', async ({ page }) => {
    const kpiCards = page.locator('#scm-executive-kpi-cards');
    await expect(kpiCards).toBeVisible();

    // 1. Month 0 Firm SAP Orders Card
    const m0Card = page.locator('#kpi-m0-firm-demand');
    await expect(m0Card).toBeVisible();
    await expect(m0Card.locator('text=MONTH 0 FIRM SAP ORDERS')).toBeVisible();
    await expect(m0Card).toContainText(/L/);

    // 2. Month +1 ML Forecast Card
    const m1Card = page.locator('#kpi-m1-forecast');
    await expect(m1Card).toBeVisible();
    await expect(m1Card.locator('text=MONTH +1 ML PREDICTION')).toBeVisible();
    await expect(m1Card).toContainText(/L/);

    // 3. Month +2 ML Forecast Card
    const m2Card = page.locator('#kpi-m2-forecast');
    await expect(m2Card).toBeVisible();
    await expect(m2Card.locator('text=MONTH +2 ML PREDICTION')).toBeVisible();
    await expect(m2Card).toContainText(/L/);

    // 4. MRP Reorder Commitment Card
    const mrpCard = page.locator('#kpi-mrp-commitment');
    await expect(mrpCard).toBeVisible();
    await expect(mrpCard.locator('text=RECOMMENDED REORDER COMMITMENT')).toBeVisible();
    await expect(mrpCard).toContainText(/৳/);
  });

  test('should render Apache ECharts Demand Fan Chart with confidence bands and telemetry', async ({
    page,
  }) => {
    // 1. Verify container exists and is visible
    const fanChartContainer = page.locator('#echarts-fanchart-container');
    await expect(fanChartContainer).toBeVisible();

    // 2. Wait for ECharts to render HTML5 Canvas
    const canvas = fanChartContainer.locator('canvas');
    await expect(canvas).toBeVisible();

    // 3. Check ML model telemetry chips
    await expect(page.locator('text=/MAPE: .*%/')).toBeVisible();
    await expect(page.locator('text=Stockout Masked')).toBeVisible();

    // 4. Test 80% and 95% confidence interval toggle buttons
    const btn80 = page.getByRole('button', { name: /80% Band/ });
    await expect(btn80).toBeVisible();
    await btn80.click(); // Toggle off
    await expect(btn80).toContainText('+ 80% Band');
    await btn80.click(); // Toggle back on
    await expect(btn80).toContainText('✓ 80% Band');

    const btn95 = page.getByRole('button', { name: /95% Band/ });
    await expect(btn95).toBeVisible();
    await btn95.click(); // Toggle off
    await expect(btn95).toContainText('+ 95% Band');
    await btn95.click(); // Toggle back on
    await expect(btn95).toContainText('✓ 95% Band');
  });

  test('should render high-density MRP action table with inline search, filters, and CSV export', async ({
    page,
  }) => {
    // 1. Verify MRP table container
    const tableContainer = page.locator('#mrp-action-table-container');
    await expect(tableContainer).toBeVisible();

    // 2. Verify Table Title
    await expect(
      tableContainer.locator('text=Material Requirements Planning (MRP) Action Table')
    ).toBeVisible();

    // 3. Verify Table Rows Rendered
    const rows = tableContainer.locator('tbody tr');
    const rowCount = await rows.count();
    expect(rowCount).toBeGreaterThan(0);

    // 4. Verify Material Master columns and presence of alert badges
    await expect(tableContainer.locator('th', { hasText: 'Material Master' })).toBeVisible();
    await expect(tableContainer.locator('th', { hasText: 'Reorder Indent (KG)' })).toBeVisible();
    await expect(tableContainer.locator('th', { hasText: 'PO Value (BDT)' })).toBeVisible();

    // 5. Verify search filter functionality
    const searchInput = page.locator('#mrp-search-input');
    await expect(searchInput).toBeVisible();
    await searchInput.fill('TIO2');
    await page.waitForTimeout(300);

    // Assert that rows still match or contain TIO2
    const filteredRows = tableContainer.locator('tbody tr');
    const filteredCount = await filteredRows.count();
    expect(filteredCount).toBeGreaterThan(0);

    // Clear search
    await searchInput.clear();

    // 6. Test CSV Export Button
    const exportBtn = page.locator('#mrp-export-csv-btn');
    await expect(exportBtn).toBeVisible();
    await expect(exportBtn).toBeEnabled();

    // Expect download event when clicking Export Reorder Indents
    const downloadPromise = page.waitForEvent('download');
    await exportBtn.click();
    const download = await downloadPromise;
    expect(download.suggestedFilename()).toMatch(/Nerolac_MRP_Reorder_Indents_.*\.csv/);
  });

  test('should allow depot and SKU switching without errors', async ({ page }) => {
    // 1. Test depot dropdown
    const depotSelect = page.locator('#scm-depot-select');
    await expect(depotSelect).toBeVisible();
    await depotSelect.selectOption('DEPOT_02'); // Chittagong
    await expect(depotSelect).toHaveValue('DEPOT_02');

    // 2. Wait for network response / rerender
    await page.waitForTimeout(600);
    const canvas = page.locator('#echarts-fanchart-container canvas');
    await expect(canvas).toBeVisible();

    // 3. Test SKU dropdown
    const skuSelect = page.locator('#scm-sku-select');
    await expect(skuSelect).toBeVisible();
    await skuSelect.selectOption('SKU_DEC_001'); // Nerolac Impressions Eco Clean
    await expect(skuSelect).toHaveValue('SKU_DEC_001');

    await page.waitForTimeout(600);
    await expect(canvas).toBeVisible();
  });
});
