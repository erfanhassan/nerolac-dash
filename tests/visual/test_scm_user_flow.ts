import { test, expect } from '@playwright/test';

test.describe('Supply Chain Control Center (Module 3) Comprehensive User Flow Test Suite', () => {
  test.beforeEach(async ({ page }) => {
    await page.goto('/supply-chain', { waitUntil: 'networkidle' });
  });

  test('1. Executive KPI Card 4 jumps to MRP Action Table and filters to Reorder Indents', async ({
    page,
  }) => {
    const kpiCard4 = page.locator('#kpi-mrp-commitment');
    await expect(kpiCard4).toBeVisible();

    // Click KPI card 4
    await kpiCard4.click();
    await page.waitForTimeout(400);

    // Verify MRP Action Table is visible and status is filtered
    const tableContainer = page.locator('#mrp-action-table-container');
    await expect(tableContainer).toBeVisible();

    // Verify Reorder button is active (dark background #0F172A)
    const reorderBtn = tableContainer.locator('button', { hasText: /^Reorder$/ });
    await expect(reorderBtn).toBeVisible();
    await expect(reorderBtn).toHaveCSS('background-color', 'rgb(15, 23, 42)');

    // Verify table displays filtered items
    const rows = tableContainer.locator('tbody tr');
    const rowCount = await rows.count();
    expect(rowCount).toBeGreaterThan(0);
    await expect(rows.first()).toContainText('REORDER REQUIRED');
  });

  test('2. Bidirectional Depot synchronization between TopBar and SCM page selector', async ({
    page,
  }) => {
    // 1. Select depot on SCM page
    const pageDepotSelect = page.locator('#scm-depot-select');
    await expect(pageDepotSelect).toBeVisible();
    await pageDepotSelect.selectOption('DEPOT_02');
    await expect(pageDepotSelect).toHaveValue('DEPOT_02');

    // 2. Verify TopBar depot switcher synchronized to DEPOT_02
    const topBarDepot = page
      .locator('#depot-select, #global-depot-select, select:has(option[value="DEPOT_02"])')
      .first();
    await expect(topBarDepot).toHaveValue('DEPOT_02');

    // 3. Select depot from TopBar to DEPOT_01
    await topBarDepot.selectOption('DEPOT_01');
    await page.waitForTimeout(500);

    // 4. Verify SCM page selector synchronized to DEPOT_01
    await expect(pageDepotSelect).toHaveValue('DEPOT_01');
  });

  test('3. SKU switching updates forecast data without server errors', async ({ page }) => {
    const skuSelect = page.locator('#scm-sku-select');
    await expect(skuSelect).toBeVisible();

    // Select each SKU in sequence to verify backend stability
    const skuValues = ['SKU_DEC_001', 'SKU_DEC_002', 'SKU_IND_001', 'SKU_EXT_001', 'ALL'];
    for (const sku of skuValues) {
      await skuSelect.selectOption(sku);
      await page.waitForTimeout(400);
      const canvas = page.locator('#echarts-fanchart-container canvas');
      await expect(canvas).toBeVisible();
    }
  });

  test('4. MRP Table inline search clear button and reset filters', async ({ page }) => {
    const searchInput = page.locator('#mrp-search-input');
    await expect(searchInput).toBeVisible();

    // Type search query
    await searchInput.fill('Epoxy');
    await page.waitForTimeout(300);

    // Verify clear button appears and click it
    const clearBtn = page.locator('#mrp-action-table-container button:has-text("✕")');
    await expect(clearBtn).toBeVisible();
    await clearBtn.click();

    // Verify search is reset
    await expect(searchInput).toHaveValue('');

    // Filter by Category
    const resinBtn = page.locator('#mrp-action-table-container button:has-text("RESIN")');
    await resinBtn.click();
    await page.waitForTimeout(300);

    // Click Reset Filters
    const resetTableBtn = page.locator(
      '#mrp-action-table-container button:has-text("Reset Filters")'
    );
    await expect(resetTableBtn).toBeVisible();
    await resetTableBtn.click();

    // Verify all rows return
    const allRows = page.locator('#mrp-action-table-container tbody tr');
    expect(await allRows.count()).toBeGreaterThanOrEqual(8);
  });

  test('5. Reset All Filters button restores default baseline', async ({ page }) => {
    // 1. Change depot and SKU
    await page.locator('#scm-depot-select').selectOption('DEPOT_02');
    await page.locator('#scm-sku-select').selectOption('SKU_DEC_001');

    // 2. Click Reset All Filters
    const resetAllBtn = page.locator('#scm-reset-all-btn');
    await expect(resetAllBtn).toBeVisible();
    await resetAllBtn.click();

    // 3. Verify defaults restored
    await expect(page.locator('#scm-depot-select')).toHaveValue('ALL');
    await expect(page.locator('#scm-sku-select')).toHaveValue('ALL');
  });

  test('6. CSV Export downloads valid file', async ({ page }) => {
    const exportBtn = page.locator('#mrp-export-csv-btn');
    await expect(exportBtn).toBeVisible();

    const downloadPromise = page.waitForEvent('download');
    await exportBtn.click();
    const download = await downloadPromise;
    expect(download.suggestedFilename()).toMatch(/Nerolac_MRP_Reorder_Indents_.*\.csv/);
  });
});
