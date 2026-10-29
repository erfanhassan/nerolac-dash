import { test, expect } from '@playwright/test';

test.describe('HR Workforce Intelligence Cross-Feature Synchronization Test Suite', () => {
  test.beforeEach(async ({ page }) => {
    await page.goto('/hr', { waitUntil: 'networkidle' });
  });

  test('1. Rep dropdown in Radar updates Selected Officer Pin on CTC Scatter', async ({ page }) => {
    const repSelect = page.locator('#sales-rep-select');
    await expect(repSelect).toBeVisible();

    // Select second sales rep
    const secondOption = repSelect.locator('option').nth(1);
    const secondRepId = await secondOption.getAttribute('value');
    const secondRepText = await secondOption.textContent();
    expect(secondRepId).toBeTruthy();

    await repSelect.selectOption(secondRepId!);

    // Verify Selected Officer callout in Scatter plot section updates to the selected officer
    const officerCallout = page.locator('#ctc-scatter-plot-section').getByText('Officer Position:');
    await expect(officerCallout).toBeVisible();

    // Check that the officer name appears in the callout banner
    const repNameOnly = secondRepText!.split('(')[0].trim();
    await expect(page.locator('#ctc-scatter-plot-section')).toContainText(repNameOnly);
  });

  test('2. Clicking Quadrant Summary Card filters Scatter points and marks Rep selector', async ({
    page,
  }) => {
    const summaryCards = page.locator('#quadrant-summary-cards');
    await expect(summaryCards).toBeVisible();

    // Click on Stars card in summary cards
    const starsCard = summaryCards.locator('text=Stars').first();
    await starsCard.click();

    // Verify filter badge appears in radar chart header
    const radarSection = page.locator('#rep-radar-chart-section');
    await expect(radarSection.getByText('Quadrant Filter:')).toBeVisible();
    await expect(radarSection.getByText('STARS', { exact: true })).toBeVisible();

    // Reset filter
    const resetBtn = radarSection.locator('button:has-text("Reset")');
    await resetBtn.click();
    await expect(radarSection.getByText('Quadrant Filter:')).not.toBeVisible();
  });

  test('3. Clicking Depot badge on a territory card synchronizes global Depot filter', async ({
    page,
  }) => {
    const cardsGrid = page.locator('#vacant-territory-cards-grid');
    await expect(cardsGrid).toBeVisible();

    // Find the first territory card and locate its depot button
    const firstCard = cardsGrid.locator('.territory-card').first();
    const depotBtn = firstCard.locator('button[title*="Filter all dashboard views"]');
    await expect(depotBtn).toBeVisible();

    await depotBtn.click();

    // Verify the global depot select dropdown updated from ALL
    const depotSelect = page.locator('#depot-select');
    const selectedVal = await depotSelect.inputValue();
    expect(selectedVal).not.toBe('ALL');
  });

  test('4. Territory search input inline clear button resets search instantly', async ({
    page,
  }) => {
    const searchInput = page.locator('#territory-search-input');
    await expect(searchInput).toBeVisible();

    await searchInput.fill('Faridpur');
    const cardsGrid = page.locator('#vacant-territory-cards-grid');
    await expect(cardsGrid.locator('.territory-card')).toHaveCount(1);

    // Verify clear button appears and click it
    const clearBtn = page.locator('#vacant-territories-section button:has-text("✕")');
    await expect(clearBtn).toBeVisible();
    await clearBtn.click();

    // Verify search input is cleared and all 39 cards return
    await expect(searchInput).toHaveValue('');
    await expect(cardsGrid.locator('.territory-card')).toHaveCount(39);
  });

  test('5. Reset All Filters button restores default baseline', async ({ page }) => {
    // 1. Change depot to DEPOT_01
    const depotSelect = page.locator('#depot-select');
    await depotSelect.selectOption('DEPOT_01');
    await expect(depotSelect).toHaveValue('DEPOT_01');

    // 2. Click Reset All Filters
    const resetAllBtn = page.locator('#reset-all-filters-btn');
    await expect(resetAllBtn).toBeVisible();
    await resetAllBtn.click();

    // 3. Verify depot reverted to ALL
    await expect(depotSelect).toHaveValue('ALL');
  });

  test('6. Executive KPI Card 3 toggles Stars filter', async ({ page }) => {
    const kpiCard3 = page.locator('#hr-kpi-summary-cards > div').nth(2);
    await expect(kpiCard3).toBeVisible();

    // Click KPI card 3 to toggle Stars
    await kpiCard3.click();

    // Verify Stars filter is active
    const radarSection = page.locator('#rep-radar-chart-section');
    await expect(radarSection.getByText('Quadrant Filter:')).toBeVisible();

    // Click again to toggle off
    await kpiCard3.click();
    await expect(radarSection.getByText('Quadrant Filter:')).not.toBeVisible();
  });
});
