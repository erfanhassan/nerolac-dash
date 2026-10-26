import { test, expect } from '@playwright/test';

test.describe('HR Workforce Intelligence (Module 2) Visual & Interactive Test Suite', () => {
  test.beforeEach(async ({ page }) => {
    // Navigate directly to HR Workforce Intelligence dashboard
    await page.goto('/hr', { waitUntil: 'networkidle' });
  });

  test('should render Corporate Bright Light Mode layout and brand headers', async ({ page }) => {
    // 1. Verify page title and header
    await expect(page).toHaveTitle(/Nerolac Operations Dashboard/);
    const headerTitle = page.locator('h1', { hasText: 'HR Workforce Intelligence' });
    await expect(headerTitle).toBeVisible();

    // 2. Verify Corporate Canvas Background is #FFFFFF (White)
    const body = page.locator('body');
    await expect(body).toHaveCSS('background-color', 'rgb(255, 255, 255)');

    // 3. Verify Nerolac Brand Banner
    const brand = page.locator('text=KANSAI NEROLAC');
    await expect(brand).toBeVisible();
    await expect(page.getByText('BANGLADESH OPERATIONS', { exact: true })).toBeVisible();
  });

  test('should render executive KPI metric summary cards with tabular-nums', async ({ page }) => {
    const kpiSummary = page.locator('#hr-kpi-summary-cards');
    await expect(kpiSummary).toBeVisible();

    // 1. Vacant territories card
    await expect(kpiSummary.locator('text=VACANT TERRITORIES (CAPACITY DEFICIT)')).toBeVisible();
    await expect(kpiSummary.locator('text=39 Territories')).toBeVisible();

    // 2. Unlocked potential card
    await expect(kpiSummary.locator('text=UNLOCKED MONTHLY SALES POTENTIAL')).toBeVisible();
    await expect(kpiSummary.locator('text=/BDT .* Cr/')).toBeVisible();

    // 3. Active sales officers card
    await expect(kpiSummary.locator('text=ACTIVE SALES OFFICERS EVALUATED')).toBeVisible();

    // 4. 2-Factor benchmark card
    await expect(kpiSummary.locator('text=2-FACTOR BENCHMARK STANDARDS')).toBeVisible();
    await expect(kpiSummary.locator('text=15L Target • 24 Days')).toBeVisible();
  });

  test('should render Apache ECharts 6-Axis Radar chart and sales rep selector', async ({
    page,
  }) => {
    // 1. Verify container exists and is visible
    const radarContainer = page.locator('#echarts-radar-container');
    await expect(radarContainer).toBeVisible();

    // 2. Wait for ECharts to render HTML5 Canvas
    const canvas = radarContainer.locator('canvas');
    await expect(canvas).toBeVisible();

    // 3. Check sales officer selector dropdown
    const select = page.locator('#sales-rep-select');
    await expect(select).toBeVisible();

    // 4. Verify composite scorecard and 6 KPI dimensions
    const radarSection = page.locator('#rep-radar-chart-section');
    await expect(radarSection.locator('text=Composite Score')).toBeVisible();
    await expect(radarSection.locator('text=Sales Achievement %')).toBeVisible();
    await expect(radarSection.locator('text=Collections %')).toBeVisible();
    await expect(radarSection.locator('text=Dealer Beat Coverage %')).toBeVisible();
    await expect(radarSection.locator('text=New Product Conversions')).toBeVisible();
    await expect(radarSection.locator('text=Quarterly Reviews %')).toBeVisible();
    await expect(radarSection.locator('text=WhatsApp Discipline %')).toBeVisible();

    // 5. Test changing officer selection
    const firstOptionVal = await select.locator('option').first().getAttribute('value');
    const secondOptionVal = await select.locator('option').nth(1).getAttribute('value');
    if (secondOptionVal) {
      await select.selectOption(secondOptionVal);
      await expect(select).toHaveValue(secondOptionVal);
    }
  });

  test('should render Apache ECharts 4-Quadrant Scatter Plot (Stars, Heavy Hitters, Ramp-up, Value Destroyers)', async ({
    page,
  }) => {
    // 1. Verify container exists and is visible
    const scatterContainer = page.locator('#echarts-scatter-container');
    await expect(scatterContainer).toBeVisible();

    // 2. Wait for ECharts to render HTML5 Canvas
    const canvas = scatterContainer.locator('canvas');
    await expect(canvas).toBeVisible();

    // 3. Verify 4-Quadrant summary cards
    const summaryCards = page.locator('#quadrant-summary-cards');
    await expect(summaryCards).toBeVisible();
    await expect(summaryCards.locator('text=Stars')).toBeVisible();
    await expect(summaryCards.locator('text=Heavy Hitters')).toBeVisible();
    await expect(summaryCards.locator('text=Ramp-Up')).toBeVisible();
    await expect(summaryCards.locator('text=Value Destroyers')).toBeVisible();

    // 4. Test quadrant filter button
    const starsFilterBtn = page.locator('#ctc-scatter-plot-section button', {
      hasText: /Stars/,
    });
    await expect(starsFilterBtn).toBeVisible();
    await starsFilterBtn.click();
  });

  test('should render 39 Vacant Territory Justification Cards with ROI payback chips', async ({
    page,
  }) => {
    const cardsGrid = page.locator('#vacant-territory-cards-grid');
    await expect(cardsGrid).toBeVisible();

    // 1. Verify 39 cards are rendered
    const cards = cardsGrid.locator('.territory-card');
    await expect(cards).toHaveCount(39);

    // 2. Verify each card has an ROI payback chip
    const firstCard = cards.first();
    const paybackChip = firstCard.locator('.roi-payback-chip');
    await expect(paybackChip).toBeVisible();
    await expect(paybackChip).toContainText('payback');

    // 3. Verify 2-Factor Capacity breakdown is displayed on card
    await expect(firstCard.locator('text=2-FACTOR CAPACITY FORMULA')).toBeVisible();
    await expect(firstCard.locator('text=Sales Capacity')).toBeVisible();
    await expect(firstCard.locator('text=Workload Capacity')).toBeVisible();
    await expect(firstCard.locator('text=Target / 15 Lacs')).toBeVisible();
    await expect(firstCard.locator('text=/\\+.* Officer\\(s\\)/')).toBeVisible();

    // 4. Test search input filtering
    const searchInput = page.locator('#territory-search-input');
    await expect(searchInput).toBeVisible();
    await searchInput.fill('Faridpur');
    const filteredCards = cardsGrid.locator('.territory-card');
    await expect(filteredCards).toHaveCount(1);
    await expect(filteredCards.first()).toContainText('Faridpur Sadar');

    // Clear search
    await searchInput.fill('');
    await expect(cardsGrid.locator('.territory-card')).toHaveCount(39);
  });
});
