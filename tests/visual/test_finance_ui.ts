import { test, expect } from '@playwright/test';

test.describe('Finance Control Center (Module 1) Visual & Interactive Test Suite', () => {
  test.beforeEach(async ({ page }) => {
    // Navigate directly to Finance Control Center
    await page.goto('/finance', { waitUntil: 'domcontentloaded' });
  });

  test('should render Corporate Bright Light Mode layout and brand headers', async ({ page }) => {
    // 1. Verify page title and header
    await expect(page).toHaveTitle(/Nerolac Operations Dashboard/);
    const headerTitle = page.locator('h1', { hasText: 'Finance Control Center' });
    await expect(headerTitle).toBeVisible();

    // 2. Verify Corporate Canvas Background is #FFFFFF (White)
    const body = page.locator('body');
    await expect(body).toHaveCSS('background-color', 'rgb(255, 255, 255)');

    // 3. Verify Nerolac Brand Banner
    const brand = page.locator('text=KANSAI NEROLAC');
    await expect(brand).toBeVisible();
    await expect(page.locator('text=BANGLADESH OPERATIONS')).toBeVisible();
  });

  test('should render executive KPI metric cards with tabular-nums', async ({ page }) => {
    const kpiNetRev = page.locator('#kpi-net-revenue');
    await expect(kpiNetRev).toBeVisible();
    await expect(kpiNetRev).toContainText('৳');
    await expect(kpiNetRev).toHaveClass(/tabular-nums/);

    const kpiGM = page.locator('#kpi-gross-margin');
    await expect(kpiGM).toBeVisible();
    await expect(kpiGM).toContainText('%');
    await expect(kpiGM).toHaveClass(/tabular-nums/);

    const kpiEbitda = page.locator('#kpi-ebitda');
    await expect(kpiEbitda).toBeVisible();
    await expect(kpiEbitda).toContainText('%');
    await expect(kpiEbitda).toHaveClass(/tabular-nums/);

    const kpiNWC = page.locator('#kpi-working-capital');
    await expect(kpiNWC).toBeVisible();
    await expect(kpiNWC).toContainText('৳');
    await expect(kpiNWC).toHaveClass(/tabular-nums/);
  });

  test('should render Apache ECharts Segment P&L Waterfall chart', async ({ page }) => {
    // 1. Verify container exists and is visible
    const waterfallContainer = page.locator('#echarts-waterfall-container');
    await expect(waterfallContainer).toBeVisible();

    // 2. Wait for ECharts to mount canvas
    const canvas = waterfallContainer.locator('canvas');
    await expect(canvas).toBeVisible();

    // 3. Check legend items
    await expect(page.locator('text=Revenue Inflow')).toBeVisible();
    await expect(page.locator('text=Cost Deduction')).toBeVisible();
    await expect(page.locator('text=Subtotal Milestone')).toBeVisible();
  });

  test('should render TanStack Tree Grid and support row expansion', async ({ page }) => {
    const treeGridTable = page.locator('#tanstack-tree-grid-table');
    await expect(treeGridTable).toBeVisible();

    // 1. Verify Division Rows
    const archRow = page.locator('#tree-row-div_architectural_coatings');
    await expect(archRow).toBeVisible();
    await expect(archRow).toContainText('Architectural Coatings');

    const indRow = page.locator('#tree-row-div_industrial_coatings');
    await expect(indRow).toBeVisible();
    await expect(indRow).toContainText('Industrial Coatings');

    // 2. Verify Segment Sub-rows are expanded by default
    const decorativeRow = page.locator('#tree-row-seg_DECORATIVE');
    await expect(decorativeRow).toBeVisible();
    await expect(decorativeRow).toContainText('Decorative Segment');

    // 3. Test Collapse & Expand Toggle
    await archRow.click();
    await expect(decorativeRow).not.toBeVisible();

    await archRow.click();
    await expect(decorativeRow).toBeVisible();
  });

  test('should render Supplier Price Variance Table with #D97706 warm amber badges', async ({
    page,
  }) => {
    const varianceTable = page.locator('#supplier-variance-table');
    await expect(varianceTable).toBeVisible();

    // 1. Verify flagged spreads badge
    const flaggedBadge = page.locator('#flagged-count-badge');
    await expect(flaggedBadge).toBeVisible();
    await expect(flaggedBadge).toContainText('Spreads > 5% Flagged');

    // 2. Check for warm amber badges (#D97706) on flagged rows
    const amberBadge = page.locator('.badge-variance-amber').first();
    await expect(amberBadge).toBeVisible();
    await expect(amberBadge).toContainText('SPREAD');
    await expect(amberBadge).toHaveCSS('color', 'rgb(217, 119, 6)'); // #D97706
  });

  test('should render Real-Time Cash Flow Simulator with interactive sliders', async ({ page }) => {
    // 1. Verify simulator elements
    const arSlider = page.locator('#slider-ar-collection');
    await expect(arSlider).toBeVisible();

    const dpoSlider = page.locator('#slider-dpo');
    await expect(dpoSlider).toBeVisible();

    const capexSlider = page.locator('#slider-capex');
    await expect(capexSlider).toBeVisible();

    // 2. Verify liquidity badge
    const statusBadge = page.locator('#liquidity-status-badge');
    await expect(statusBadge).toBeVisible();
    await expect(statusBadge).toContainText(/LIQUIDITY/);

    // 3. Verify ECharts Cash Flow multi-series chart
    const cashflowChart = page.locator('#echarts-cashflow-container canvas');
    await expect(cashflowChart).toBeVisible();

    // 4. Test slider interaction
    await arSlider.fill('95');
    await expect(page.locator('#slider-val-ar')).toContainText('95%');
  });

  test('should render AR/AP Aging schedule across 0-30, 31-60, 61-90, 90+ buckets', async ({
    page,
  }) => {
    await expect(page.locator('#aging-bucket-days_1_30')).toBeVisible();
    await expect(page.locator('#aging-bucket-days_31_60')).toBeVisible();
    await expect(page.locator('#aging-bucket-days_61_90')).toBeVisible();
    await expect(page.locator('#aging-bucket-days_90_plus')).toBeVisible();

    const entitiesTable = page.locator('#ar-ap-entities-table');
    await expect(entitiesTable).toBeVisible();
  });
});
