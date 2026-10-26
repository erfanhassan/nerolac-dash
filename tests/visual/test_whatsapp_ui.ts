import { test, expect } from '@playwright/test';

test.describe('WhatsApp Field Operations & 7:00 PM SAP Recon (Module 4) Visual & Interactive Test Suite', () => {
  test.beforeEach(async ({ page }) => {
    // Navigate directly to WhatsApp dashboard
    await page.goto('/whatsapp', { waitUntil: 'networkidle' });
  });

  test('should render Corporate Bright Light Mode layout, brand banner, and active nav link', async ({
    page,
  }) => {
    // 1. Verify page title and header
    await expect(page).toHaveTitle(/Nerolac Operations Dashboard/);
    const headerTitle = page.locator('h1', {
      hasText: 'WhatsApp Field Operations & 7:00 PM SAP Recon',
    });
    await expect(headerTitle).toBeVisible();

    // 2. Verify Corporate Canvas Background is #FFFFFF (White)
    const body = page.locator('body');
    await expect(body).toHaveCSS('background-color', 'rgb(255, 255, 255)');

    // 3. Verify Nerolac Brand Banner
    const brand = page.locator('text=KANSAI NEROLAC');
    await expect(brand).toBeVisible();
    await expect(page.getByText('BANGLADESH OPERATIONS', { exact: true })).toBeVisible();

    // 4. Verify Active Nav Link for WhatsApp Recon (Module 4)
    const navLink = page.locator('#nav-whatsapp');
    await expect(navLink).toBeVisible();
    await expect(navLink).toContainText('WhatsApp Recon (Module 4)');
  });

  test('should render 7:00 PM SAP Daily Reconciliation Engine header, cutoff badge, and run action', async ({
    page,
  }) => {
    // 1. Engine header
    const engineTitle = page.locator('text=7:00 PM SAP Daily Sales Reconciliation Engine');
    await expect(engineTitle).toBeVisible();

    // 2. Cutoff schedule
    await expect(page.locator('strong:has-text("19:00:00 BST")')).toBeVisible();

    // 3. Run Recon Button
    const runBtn = page.locator('#btn-run-recon-now');
    await expect(runBtn).toBeVisible();
    await expect(runBtn).toContainText('Run 7:00 PM SAP Recon Now');
  });

  test('should render executive KPI summary metric cards with tabular-nums', async ({ page }) => {
    const kpiCards = page.locator('#recon-kpi-summary-cards');
    await expect(kpiCards).toBeVisible();

    // 1. WhatsApp Self-Reported Sales Card
    const waCard = page.locator('#kpi-total-whatsapp-sales');
    await expect(waCard).toBeVisible();
    await expect(waCard.locator('text=/WHATSAPP SELF-REPORTED SALES/i')).toBeVisible();
    await expect(waCard).toContainText(/৳/);

    // 2. SAP Invoiced Sales Card
    const sapCard = page.locator('#kpi-total-sap-invoiced');
    await expect(sapCard).toBeVisible();
    await expect(sapCard.locator('text=/SAP INVOICED SALES/i')).toBeVisible();
    await expect(sapCard).toContainText(/৳/);

    // 3. Net Variance Card
    const varianceCard = page.locator('#kpi-net-variance');
    await expect(varianceCard).toBeVisible();
    await expect(varianceCard.locator('text=/NET VARIANCE/i')).toBeVisible();
    await expect(varianceCard).toContainText(/৳/);

    // 4. Match Rate Card
    const matchRateCard = page.locator('#kpi-recon-match-rate');
    await expect(matchRateCard).toBeVisible();
    await expect(matchRateCard.locator('text=/OVERALL MATCH RATE/i')).toBeVisible();
    await expect(matchRateCard).toContainText(/%/);

    // 5. Flagged Exceptions Card
    const excCountCard = page.locator('#kpi-exception-count');
    await expect(excCountCard).toBeVisible();
    await expect(excCountCard.locator('text=/DISCREPANCIES REQUIRING ACTION/i')).toBeVisible();
  });

  test('should render Top-10 Exception Table with interactive search, filters, and CSV export', async ({
    page,
  }) => {
    // 1. Container check
    const container = page.locator('#recon-top10-exceptions-container');
    await expect(container).toBeVisible();
    await expect(
      container.locator('text=Top-10 Daily Reconciliation Exceptions (7:00 PM SAP Ledger Audit)')
    ).toBeVisible();

    // 2. Verify Table Rows
    const table = page.locator('#recon-exceptions-table');
    await expect(table).toBeVisible();
    const rows = table.locator('tbody tr');
    const rowCount = await rows.count();
    expect(rowCount).toBeGreaterThan(0);

    // 3. Verify presence of known SAP Dealer Code (e.g., D-11099)
    const dealerCodeChip = table.locator('text=D-11099').first();
    await expect(dealerCodeChip).toBeVisible();

    // 4. Verify Row Expansion (Diagnosis & Action Guidance)
    await rows.first().click();
    await expect(page.locator('text=PRIMARY DISCREPANCY DIAGNOSIS')).toBeVisible();
    await expect(page.locator('text=RECOMMENDED ACTION GUIDANCE')).toBeVisible();

    // 5. Search Filter test
    const searchInput = page.locator('#recon-search-input');
    await expect(searchInput).toBeVisible();
    await searchInput.fill('Uttara');
    await page.waitForTimeout(300);

    const filteredRows = table.locator('tbody tr');
    expect(await filteredRows.count()).toBeGreaterThan(0);
    await searchInput.clear();

    // 6. Depot Dropdown Filter test
    const depotSelect = page.locator('#recon-depot-select');
    await expect(depotSelect).toBeVisible();
    await depotSelect.selectOption({ index: 1 });
    await page.waitForTimeout(300);
    await depotSelect.selectOption('ALL');

    // 7. CSV Export Button test
    const exportBtn = page.locator('#recon-export-csv-btn');
    await expect(exportBtn).toBeVisible();
    await expect(exportBtn).toBeEnabled();

    const downloadPromise = page.waitForEvent('download');
    await exportBtn.click();
    const download = await downloadPromise;
    expect(download.suggestedFilename()).toMatch(/Nerolac_7PM_Reconciliation_Exceptions_.*\.csv/);
  });

  test('should render 8 Regional Depots Reconciliation Performance Breakdown', async ({ page }) => {
    const depotSection = page.locator('#recon-depot-breakdown');
    await expect(depotSection).toBeVisible();
    await expect(
      page.locator('text=8 Regional Depots Reconciliation Performance Breakdown')
    ).toBeVisible();

    // Check Chittagong Depot card
    await expect(depotSection.locator('text=Chittagong Port Depot')).toBeVisible();
    // Check Dhaka Central Hub card
    await expect(depotSection.locator('text=Dhaka Central Hub')).toBeVisible();
  });

  test('should render Real-Time WhatsApp Message Stream with Banglish text, resolved dealer chips, and SKU tables', async ({
    page,
  }) => {
    // 1. Message Stream Section
    const streamSection = page.locator('#whatsapp-stream-section');
    await expect(streamSection).toBeVisible();
    await expect(page.locator('text=Real-Time WhatsApp Ingestion Stream')).toBeVisible();

    // 2. Message Cards Container
    const streamCards = page.locator('#whatsapp-message-cards-stream');
    await expect(streamCards).toBeVisible();

    // 3. Verify Banglish Rep Speech Bubble
    const rawTag = page.locator('text=RAW BANGLISH REP TEXT').first();
    await expect(rawTag).toBeVisible();

    // 4. Verify Vector/Fuzzy Resolved SAP Dealer Chip
    const resolvedDealerChip = page.locator('text=SAP D-40982').first();
    await expect(resolvedDealerChip).toBeVisible();
    await expect(page.locator('text=pgvector + RapidFuzz').first()).toBeVisible();
    await expect(page.locator('text=Bismillah Hardware & Paint Store').first()).toBeVisible();

    // 5. Verify Extracted SKUs Table
    await expect(page.locator('text=/Extracted SKUs/i').first()).toBeVisible();
    await expect(page.locator('text=Nerolac Impressions Eco Clean').first()).toBeVisible();

    // 6. Verify Extracted Collection Pill
    await expect(page.locator('text=bKash:').first()).toBeVisible();

    // 7. Test Message Search Filter
    const msgSearch = page.locator('#whatsapp-message-search');
    await expect(msgSearch).toBeVisible();
    await msgSearch.fill('Bismillah');
    await page.waitForTimeout(300);

    const matchCard = page.locator('#whatsapp-card-1001');
    await expect(matchCard).toBeVisible();
    await msgSearch.clear();

    // 8. Test Refresh Button
    const refreshBtn = page.locator('#whatsapp-refresh-feed-btn');
    await expect(refreshBtn).toBeVisible();
    await refreshBtn.click();
    await page.waitForTimeout(400);
  });

  test('should support tab navigation between Unified, 7:00 PM Recon, and Live Feed views', async ({
    page,
  }) => {
    // 1. Switch to 7:00 PM Recon Tab
    const tabRecon = page.locator('#tab-btn-recon');
    await expect(tabRecon).toBeVisible();
    await tabRecon.click();
    await page.waitForTimeout(300);

    // Recon section visible, Stream section hidden
    await expect(page.locator('#recon-dashboard-section')).toBeVisible();
    await expect(page.locator('#whatsapp-stream-section')).not.toBeVisible();

    // 2. Switch to Live Feed Tab
    const tabFeed = page.locator('#tab-btn-feed');
    await expect(tabFeed).toBeVisible();
    await tabFeed.click();
    await page.waitForTimeout(300);

    // Stream section visible, Recon section hidden
    await expect(page.locator('#whatsapp-stream-section')).toBeVisible();
    await expect(page.locator('#recon-dashboard-section')).not.toBeVisible();

    // 3. Switch back to Unified Tab
    const tabAll = page.locator('#tab-btn-all');
    await expect(tabAll).toBeVisible();
    await tabAll.click();
    await page.waitForTimeout(300);

    // Both sections visible
    await expect(page.locator('#recon-dashboard-section')).toBeVisible();
    await expect(page.locator('#whatsapp-stream-section')).toBeVisible();
  });
});
