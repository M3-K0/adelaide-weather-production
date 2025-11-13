/**
 * TEST2: Frontend Analog Explorer Component Integration Tests
 * 
 * E2E tests for the frontend analog explorer component with:
 * - Real FAISS data integration
 * - Interactive exploration features
 * - Performance validation
 * - Transparency data display
 * - User workflow validation
 */

import { test, expect, Page, Locator } from '@playwright/test';
import { PerformanceMonitor } from '../../utils/performance-monitor';
import { AnalogExplorerPage } from '../../pages/AnalogExplorerPage';

interface AnalogExplorerState {
  selectedHorizon: string;
  selectedVariables: string[];
  analogsCount: number;
  isLoading: boolean;
  hasError: boolean;
  searchTime: number;
}

class FrontendAnalogExplorerTester {
  private page: Page;
  private performanceMonitor: PerformanceMonitor;
  private analogExplorerPage: AnalogExplorerPage;

  constructor(page: Page) {
    this.page = page;
    this.performanceMonitor = new PerformanceMonitor(page);
    this.analogExplorerPage = new AnalogExplorerPage(page);
  }

  async setupPerformanceMonitoring(): Promise<void> {
    await this.performanceMonitor.startMonitoring();
  }

  async waitForAnalogExplorer(): Promise<void> {
    await this.page.waitForSelector('[data-testid="analog-explorer"]', { timeout: 10000 });
    await this.page.waitForSelector('[data-testid="horizon-selector"]', { timeout: 5000 });
    await this.page.waitForSelector('[data-testid="variable-selector"]', { timeout: 5000 });
  }

  async getAnalogExplorerState(): Promise<AnalogExplorerState> {
    // Get selected horizon
    const selectedHorizon = await this.page.locator('[data-testid="horizon-selector"] .selected').textContent() || '';
    
    // Get selected variables
    const selectedVariables = await this.page.locator('[data-testid="variable-selector"] .selected').allTextContents();
    
    // Get analogs count
    const analogsCountText = await this.page.locator('[data-testid="analogs-count"]').textContent() || '0';
    const analogsCount = parseInt(analogsCountText.match(/\d+/)?.[0] || '0', 10);
    
    // Check loading state
    const isLoading = await this.page.locator('[data-testid="loading-indicator"]').isVisible();
    
    // Check error state
    const hasError = await this.page.locator('[data-testid="error-message"]').isVisible();
    
    // Get search time if available
    const searchTimeText = await this.page.locator('[data-testid="search-time"]').textContent() || '';
    const searchTime = parseFloat(searchTimeText.match(/(\d+\.?\d*)/)?.[0] || '0');

    return {
      selectedHorizon,
      selectedVariables,
      analogsCount,
      isLoading,
      hasError,
      searchTime
    };
  }

  async selectHorizon(horizon: string): Promise<void> {
    await this.page.click(`[data-testid="horizon-${horizon}"]`);
    await this.page.waitForSelector('[data-testid="loading-indicator"]', { state: 'hidden', timeout: 10000 });
  }

  async selectVariables(variables: string[]): Promise<void> {
    // Clear existing selections
    const selectedVars = await this.page.locator('[data-testid="variable-selector"] .selected').all();
    for (const selected of selectedVars) {
      await selected.click();
    }

    // Select new variables
    for (const variable of variables) {
      await this.page.click(`[data-testid="variable-${variable}"]`);
    }

    await this.page.waitForSelector('[data-testid="loading-indicator"]', { state: 'hidden', timeout: 10000 });
  }

  async validateAnalogResults(): Promise<void> {
    // Wait for analog results to load
    await this.page.waitForSelector('[data-testid="analog-results"]', { timeout: 15000 });
    
    // Check that analogs are displayed
    const analogCards = await this.page.locator('[data-testid^="analog-card-"]').all();
    expect(analogCards.length).toBeGreaterThan(0);

    // Validate analog card structure
    for (const card of analogCards) {
      await expect(card.locator('[data-testid="similarity-score"]')).toBeVisible();
      await expect(card.locator('[data-testid="distance-value"]')).toBeVisible();
      await expect(card.locator('[data-testid="metadata-info"]')).toBeVisible();
      await expect(card.locator('[data-testid="date-time"]')).toBeVisible();
    }
  }

  async validateTransparencyDisplay(): Promise<void> {
    // Check transparency section is visible
    await expect(this.page.locator('[data-testid="transparency-section"]')).toBeVisible();
    
    // Check model version display
    await expect(this.page.locator('[data-testid="model-version"]')).toBeVisible();
    
    // Check search method display
    await expect(this.page.locator('[data-testid="search-method"]')).toBeVisible();
    
    // Check confidence intervals if available
    const confidenceIntervals = this.page.locator('[data-testid="confidence-intervals"]');
    if (await confidenceIntervals.isVisible()) {
      await expect(confidenceIntervals.locator('[data-testid="ci-50"]')).toBeVisible();
      await expect(confidenceIntervals.locator('[data-testid="ci-95"]')).toBeVisible();
    }
    
    // Check quality scores if available
    const qualityScores = this.page.locator('[data-testid="quality-scores"]');
    if (await qualityScores.isVisible()) {
      await expect(qualityScores.locator('[data-testid="similarity-quality"]')).toBeVisible();
      await expect(qualityScores.locator('[data-testid="relevance-quality"]')).toBeVisible();
    }
  }

  async validatePerformanceIndicators(): Promise<void> {
    // Check search time display
    await expect(this.page.locator('[data-testid="search-time"]')).toBeVisible();
    
    const searchTimeText = await this.page.locator('[data-testid="search-time"]').textContent();
    const searchTime = parseFloat(searchTimeText?.match(/(\d+\.?\d*)/)?.[0] || '0');
    
    // Validate search time is within acceptable limits
    expect(searchTime).toBeLessThan(150); // API response time requirement
    
    // Check data source indicator
    await expect(this.page.locator('[data-testid="data-source"]')).toBeVisible();
    const dataSource = await this.page.locator('[data-testid="data-source"]').textContent();
    expect(dataSource).toContain('FAISS');
    
    // Check fallback indicator (should not be present)
    const fallbackIndicator = this.page.locator('[data-testid="fallback-warning"]');
    await expect(fallbackIndicator).not.toBeVisible();
  }

  async validateDistanceMonotonicity(): Promise<void> {
    const distanceElements = await this.page.locator('[data-testid^="distance-value-"]').all();
    const distances: number[] = [];

    for (const element of distanceElements) {
      const text = await element.textContent();
      const distance = parseFloat(text?.replace(/[^\d.]/g, '') || '0');
      distances.push(distance);
    }

    // Verify distances are non-decreasing (monotonic)
    for (let i = 1; i < distances.length; i++) {
      expect(distances[i]).toBeGreaterThanOrEqual(distances[i - 1]);
    }
  }

  async interactWithAnalogCard(index: number): Promise<void> {
    const card = this.page.locator(`[data-testid="analog-card-${index}"]`);
    
    // Click on analog card to expand details
    await card.click();
    
    // Wait for detail panel to appear
    await this.page.waitForSelector('[data-testid="analog-detail-panel"]', { timeout: 5000 });
    
    // Validate detail panel content
    await expect(this.page.locator('[data-testid="full-metadata"]')).toBeVisible();
    await expect(this.page.locator('[data-testid="weather-patterns"]')).toBeVisible();
    await expect(this.page.locator('[data-testid="similarity-breakdown"]')).toBeVisible();
  }

  async validateResponsiveDesign(): Promise<void> {
    // Test mobile viewport
    await this.page.setViewportSize({ width: 375, height: 667 });
    await this.waitForAnalogExplorer();
    
    // Check mobile layout adaptations
    await expect(this.page.locator('[data-testid="mobile-navigation"]')).toBeVisible();
    await expect(this.page.locator('[data-testid="analog-explorer"]')).toBeVisible();
    
    // Test tablet viewport
    await this.page.setViewportSize({ width: 768, height: 1024 });
    await this.waitForAnalogExplorer();
    
    // Check tablet layout adaptations
    await expect(this.page.locator('[data-testid="analog-explorer"]')).toBeVisible();
    
    // Reset to desktop
    await this.page.setViewportSize({ width: 1280, height: 720 });
  }

  getPerformanceReport(): any {
    return this.performanceMonitor.getPerformanceReport();
  }
}

test.describe('TEST2: Frontend Analog Explorer Integration', () => {
  let frontendTester: FrontendAnalogExplorerTester;

  test.beforeEach(async ({ page }) => {
    frontendTester = new FrontendAnalogExplorerTester(page);
    await frontendTester.setupPerformanceMonitoring();
    
    // Navigate to analog explorer page
    await page.goto('/analog-demo');
    await frontendTester.waitForAnalogExplorer();
  });

  test('FRONTEND-001: Basic analog explorer functionality', async () => {
    // Test initial state
    const initialState = await frontendTester.getAnalogExplorerState();
    expect(initialState.isLoading).toBe(false);
    expect(initialState.hasError).toBe(false);

    // Test horizon selection
    await frontendTester.selectHorizon('24h');
    
    const afterHorizonState = await frontendTester.getAnalogExplorerState();
    expect(afterHorizonState.selectedHorizon).toContain('24h');

    // Test variable selection
    await frontendTester.selectVariables(['t2m', 'u10', 'v10']);
    
    const afterVariableState = await frontendTester.getAnalogExplorerState();
    expect(afterVariableState.selectedVariables).toContain('t2m');
    expect(afterVariableState.selectedVariables).toContain('u10');
    expect(afterVariableState.selectedVariables).toContain('v10');

    // Validate analog results appear
    await frontendTester.validateAnalogResults();
    
    const finalState = await frontendTester.getAnalogExplorerState();
    expect(finalState.analogsCount).toBeGreaterThan(0);
    
    console.log('✓ Basic analog explorer functionality validated');
  });

  test('FRONTEND-002: Real FAISS data integration', async () => {
    // Configure for FAISS testing
    await frontendTester.selectHorizon('24h');
    await frontendTester.selectVariables(['t2m', 'u10', 'v10', 'cape']);

    // Validate results are from FAISS
    await frontendTester.validatePerformanceIndicators();
    
    // Check analog count matches expected FAISS results
    const state = await frontendTester.getAnalogExplorerState();
    expect(state.analogsCount).toBe(100); // Default FAISS analog count
    
    // Validate search performance
    expect(state.searchTime).toBeLessThan(150); // API response time requirement
    
    // Validate distance monotonicity from FAISS
    await frontendTester.validateDistanceMonotonicity();
    
    console.log(`✓ FAISS data integration validated - ${state.analogsCount} analogs in ${state.searchTime}ms`);
  });

  test('FRONTEND-003: Transparency data display', async () => {
    await frontendTester.selectHorizon('12h');
    await frontendTester.selectVariables(['t2m', 'cape']);

    // Wait for results and validate transparency display
    await frontendTester.validateAnalogResults();
    await frontendTester.validateTransparencyDisplay();
    
    console.log('✓ Transparency data display validated');
  });

  test('FRONTEND-004: Interactive analog exploration', async () => {
    await frontendTester.selectHorizon('6h');
    await frontendTester.selectVariables(['t2m']);

    await frontendTester.validateAnalogResults();
    
    // Test interaction with individual analog cards
    await frontendTester.interactWithAnalogCard(0);
    await frontendTester.interactWithAnalogCard(1);
    await frontendTester.interactWithAnalogCard(2);
    
    console.log('✓ Interactive analog exploration validated');
  });

  test('FRONTEND-005: Performance validation across scenarios', async () => {
    const testScenarios = [
      { horizon: '6h', variables: ['t2m'] },
      { horizon: '12h', variables: ['t2m', 'u10', 'v10'] },
      { horizon: '24h', variables: ['t2m', 'u10', 'v10', 'cape'] },
      { horizon: '48h', variables: ['t2m', 'u10', 'v10', 'z500'] }
    ];

    for (const scenario of testScenarios) {
      await frontendTester.selectHorizon(scenario.horizon);
      await frontendTester.selectVariables(scenario.variables);
      
      const state = await frontendTester.getAnalogExplorerState();
      
      // Validate performance requirements
      expect(state.searchTime).toBeLessThan(150);
      expect(state.analogsCount).toBeGreaterThan(0);
      expect(state.hasError).toBe(false);
      
      console.log(`✓ Performance validated for ${scenario.horizon} with ${scenario.variables.join(',')} - ${state.searchTime}ms`);
    }
  });

  test('FRONTEND-006: Error handling and resilience', async () => {
    // Test with invalid configuration (should gracefully handle)
    try {
      await frontendTester.selectHorizon('invalid');
    } catch (error) {
      // Expected to fail gracefully
    }

    // Ensure explorer still functions after error
    await frontendTester.selectHorizon('24h');
    await frontendTester.selectVariables(['t2m']);
    
    const state = await frontendTester.getAnalogExplorerState();
    expect(state.isLoading).toBe(false);
    
    console.log('✓ Error handling and resilience validated');
  });

  test('FRONTEND-007: Responsive design validation', async () => {
    await frontendTester.selectHorizon('24h');
    await frontendTester.selectVariables(['t2m', 'u10']);
    
    await frontendTester.validateResponsiveDesign();
    
    console.log('✓ Responsive design validated');
  });

  test('FRONTEND-008: Memory usage monitoring during exploration', async ({ page }) => {
    // Get initial memory metrics
    const initialMetrics = await page.evaluate(() => {
      return {
        usedJSHeapSize: (performance as any).memory?.usedJSHeapSize || 0,
        totalJSHeapSize: (performance as any).memory?.totalJSHeapSize || 0
      };
    });

    // Perform memory-intensive operations
    const scenarios = [
      { horizon: '6h', variables: ['t2m'] },
      { horizon: '12h', variables: ['t2m', 'u10'] },
      { horizon: '24h', variables: ['t2m', 'u10', 'v10'] },
      { horizon: '48h', variables: ['t2m', 'u10', 'v10', 'z500'] },
      { horizon: '24h', variables: ['t2m', 'u10', 'v10', 'cape', 't850'] }
    ];

    for (const scenario of scenarios) {
      await frontendTester.selectHorizon(scenario.horizon);
      await frontendTester.selectVariables(scenario.variables);
      await frontendTester.validateAnalogResults();
      
      // Interact with multiple analog cards
      for (let i = 0; i < 5; i++) {
        await frontendTester.interactWithAnalogCard(i);
        // Close detail panel
        await page.keyboard.press('Escape');
      }
    }

    // Get final memory metrics
    const finalMetrics = await page.evaluate(() => {
      return {
        usedJSHeapSize: (performance as any).memory?.usedJSHeapSize || 0,
        totalJSHeapSize: (performance as any).memory?.totalJSHeapSize || 0
      };
    });

    // Calculate memory increase
    const memoryIncrease = finalMetrics.usedJSHeapSize - initialMetrics.usedJSHeapSize;
    const memoryIncreaseMB = memoryIncrease / (1024 * 1024);

    // Memory increase should be reasonable (< 50MB for this test)
    expect(memoryIncreaseMB).toBeLessThan(50);
    
    console.log(`✓ Memory usage validated - Increase: ${memoryIncreaseMB.toFixed(2)}MB`);
  });

  test.afterAll(async () => {
    // Generate frontend performance report
    const performanceReport = frontendTester.getPerformanceReport();
    
    console.log('\n=== TEST2 Frontend Performance Report ===');
    console.log(JSON.stringify(performanceReport, null, 2));
    
    // Validate frontend performance requirements
    for (const [endpoint, metrics] of Object.entries(performanceReport)) {
      if (metrics.p95 && metrics.p95 > 150) {
        throw new Error(`Frontend performance requirement failed: ${endpoint} P95 ${metrics.p95}ms > 150ms`);
      }
    }
    
    console.log('✓ All TEST2 frontend integration requirements met');
  });
});