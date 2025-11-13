/**
 * Analog Explorer Page Object Model
 * 
 * Page Object Model for the frontend analog explorer component
 * Provides reusable methods for interacting with the analog exploration interface
 */

import { Page, Locator, expect } from '@playwright/test';
import { BasePage } from './BasePage';

export interface AnalogExplorerState {
  selectedHorizon: string;
  selectedVariables: string[];
  analogsCount: number;
  isLoading: boolean;
  hasError: boolean;
  searchTime: number;
  dataSource: string;
  fallbackUsed: boolean;
}

export interface AnalogCard {
  index: number;
  similarityScore: number;
  distance: number;
  metadata: any;
  dateTime: string;
}

export class AnalogExplorerPage extends BasePage {
  // Main container selectors
  readonly analogExplorer: Locator;
  readonly horizonSelector: Locator;
  readonly variableSelector: Locator;
  readonly analogResults: Locator;
  readonly transparencySection: Locator;
  readonly performanceSection: Locator;

  // Control selectors
  readonly loadingIndicator: Locator;
  readonly errorMessage: Locator;
  readonly searchTime: Locator;
  readonly analogsCount: Locator;
  readonly dataSourceIndicator: Locator;
  readonly fallbackWarning: Locator;

  // Transparency selectors
  readonly modelVersion: Locator;
  readonly searchMethod: Locator;
  readonly confidenceIntervals: Locator;
  readonly qualityScores: Locator;

  constructor(page: Page) {
    super(page);
    
    // Main containers
    this.analogExplorer = page.locator('[data-testid="analog-explorer"]');
    this.horizonSelector = page.locator('[data-testid="horizon-selector"]');
    this.variableSelector = page.locator('[data-testid="variable-selector"]');
    this.analogResults = page.locator('[data-testid="analog-results"]');
    this.transparencySection = page.locator('[data-testid="transparency-section"]');
    this.performanceSection = page.locator('[data-testid="performance-section"]');

    // Controls
    this.loadingIndicator = page.locator('[data-testid="loading-indicator"]');
    this.errorMessage = page.locator('[data-testid="error-message"]');
    this.searchTime = page.locator('[data-testid="search-time"]');
    this.analogsCount = page.locator('[data-testid="analogs-count"]');
    this.dataSourceIndicator = page.locator('[data-testid="data-source"]');
    this.fallbackWarning = page.locator('[data-testid="fallback-warning"]');

    // Transparency
    this.modelVersion = page.locator('[data-testid="model-version"]');
    this.searchMethod = page.locator('[data-testid="search-method"]');
    this.confidenceIntervals = page.locator('[data-testid="confidence-intervals"]');
    this.qualityScores = page.locator('[data-testid="quality-scores"]');
  }

  /**
   * Validate page loaded (required by BasePage)
   */
  async validatePageLoaded(): Promise<void> {
    await expect(this.analogExplorer).toBeVisible();
    await expect(this.horizonSelector).toBeVisible();
    await expect(this.variableSelector).toBeVisible();
  }

  /**
   * Navigate to the analog explorer page
   */
  async goto(): Promise<void> {
    await this.page.goto('/analog-demo');
    await this.waitForPageLoad();
  }

  /**
   * Wait for page to load and analog explorer to be ready
   */
  async waitForPageLoad(): Promise<void> {
    await this.analogExplorer.waitFor({ timeout: 10000 });
    await this.horizonSelector.waitFor({ timeout: 5000 });
    await this.variableSelector.waitFor({ timeout: 5000 });
  }

  /**
   * Select a forecast horizon
   */
  async selectHorizon(horizon: '6h' | '12h' | '24h' | '48h'): Promise<void> {
    await this.page.click(`[data-testid="horizon-${horizon}"]`);
    await this.waitForSearchCompletion();
  }

  /**
   * Select multiple variables
   */
  async selectVariables(variables: string[]): Promise<void> {
    // Clear existing selections first
    const selectedVars = await this.variableSelector.locator('.selected').all();
    for (const selected of selectedVars) {
      await selected.click();
    }

    // Select new variables
    for (const variable of variables) {
      await this.page.click(`[data-testid="variable-${variable}"]`);
    }

    await this.waitForSearchCompletion();
  }

  /**
   * Wait for search to complete (loading indicator to disappear)
   */
  async waitForSearchCompletion(): Promise<void> {
    // Wait for loading to start if not already loading
    await this.page.waitForTimeout(100);
    
    // Wait for loading to finish
    await this.loadingIndicator.waitFor({ state: 'hidden', timeout: 15000 });
  }

  /**
   * Get current analog explorer state
   */
  async getState(): Promise<AnalogExplorerState> {
    // Get selected horizon
    const selectedHorizonElement = this.horizonSelector.locator('.selected').first();
    const selectedHorizon = await selectedHorizonElement.isVisible() 
      ? await selectedHorizonElement.textContent() || ''
      : '';

    // Get selected variables
    const selectedVariableElements = await this.variableSelector.locator('.selected').all();
    const selectedVariables: string[] = [];
    for (const element of selectedVariableElements) {
      const text = await element.textContent();
      if (text) selectedVariables.push(text.trim());
    }

    // Get analogs count
    const analogsCountText = await this.analogsCount.textContent() || '0';
    const analogsCount = parseInt(analogsCountText.match(/\d+/)?.[0] || '0', 10);

    // Check loading state
    const isLoading = await this.loadingIndicator.isVisible();

    // Check error state
    const hasError = await this.errorMessage.isVisible();

    // Get search time
    const searchTimeText = await this.searchTime.textContent() || '';
    const searchTime = parseFloat(searchTimeText.match(/(\d+\.?\d*)/)?.[0] || '0');

    // Get data source
    const dataSource = await this.dataSourceIndicator.textContent() || '';

    // Check fallback usage
    const fallbackUsed = await this.fallbackWarning.isVisible();

    return {
      selectedHorizon,
      selectedVariables,
      analogsCount,
      isLoading,
      hasError,
      searchTime,
      dataSource,
      fallbackUsed
    };
  }

  /**
   * Get all analog cards data
   */
  async getAnalogCards(): Promise<AnalogCard[]> {
    await this.analogResults.waitFor({ timeout: 10000 });
    
    const cardElements = await this.page.locator('[data-testid^="analog-card-"]').all();
    const cards: AnalogCard[] = [];

    for (let i = 0; i < cardElements.length; i++) {
      const card = cardElements[i];
      
      const similarityText = await card.locator('[data-testid="similarity-score"]').textContent() || '0';
      const similarityScore = parseFloat(similarityText.replace(/[^\d.]/g, ''));
      
      const distanceText = await card.locator('[data-testid="distance-value"]').textContent() || '0';
      const distance = parseFloat(distanceText.replace(/[^\d.]/g, ''));
      
      const dateTime = await card.locator('[data-testid="date-time"]').textContent() || '';
      
      // Try to get metadata if available
      let metadata = {};
      const metadataElement = card.locator('[data-testid="metadata-info"]');
      if (await metadataElement.isVisible()) {
        const metadataText = await metadataElement.textContent();
        try {
          metadata = metadataText ? JSON.parse(metadataText) : {};
        } catch {
          metadata = { raw: metadataText };
        }
      }

      cards.push({
        index: i,
        similarityScore,
        distance,
        metadata,
        dateTime
      });
    }

    return cards;
  }

  /**
   * Click on a specific analog card to view details
   */
  async clickAnalogCard(index: number): Promise<void> {
    const card = this.page.locator(`[data-testid="analog-card-${index}"]`);
    await card.click();
    
    // Wait for detail panel to appear
    await this.page.waitForSelector('[data-testid="analog-detail-panel"]', { timeout: 5000 });
  }

  /**
   * Close analog detail panel
   */
  async closeAnalogDetail(): Promise<void> {
    // Try ESC key first
    await this.page.keyboard.press('Escape');
    
    // Or click close button if available
    const closeButton = this.page.locator('[data-testid="close-detail-panel"]');
    if (await closeButton.isVisible()) {
      await closeButton.click();
    }
  }

  /**
   * Validate transparency data is displayed correctly
   */
  async validateTransparencyDisplay(): Promise<void> {
    await expect(this.transparencySection).toBeVisible();
    await expect(this.modelVersion).toBeVisible();
    await expect(this.searchMethod).toBeVisible();
    
    // Check search method is FAISS
    const searchMethodText = await this.searchMethod.textContent();
    expect(searchMethodText?.toLowerCase()).toContain('faiss');
  }

  /**
   * Validate performance indicators show correct data
   */
  async validatePerformanceIndicators(): Promise<void> {
    await expect(this.performanceSection).toBeVisible();
    await expect(this.searchTime).toBeVisible();
    await expect(this.dataSourceIndicator).toBeVisible();
    
    // Validate data source is FAISS
    const dataSourceText = await this.dataSourceIndicator.textContent();
    expect(dataSourceText?.toLowerCase()).toContain('faiss');
    
    // Validate no fallback warning
    await expect(this.fallbackWarning).not.toBeVisible();
    
    // Validate search time is reasonable
    const searchTimeText = await this.searchTime.textContent() || '';
    const searchTime = parseFloat(searchTimeText.match(/(\d+\.?\d*)/)?.[0] || '0');
    expect(searchTime).toBeLessThan(150); // API response time requirement
  }

  /**
   * Validate distance monotonicity in analog results
   */
  async validateDistanceMonotonicity(): Promise<void> {
    const cards = await this.getAnalogCards();
    
    for (let i = 1; i < cards.length; i++) {
      expect(cards[i].distance).toBeGreaterThanOrEqual(cards[i - 1].distance);
    }
  }

  /**
   * Wait for analog results to load and validate basic structure
   */
  async waitForAndValidateResults(): Promise<void> {
    await this.analogResults.waitFor({ timeout: 15000 });
    
    // Check that analog cards are present
    const cards = await this.page.locator('[data-testid^="analog-card-"]').all();
    expect(cards.length).toBeGreaterThan(0);
    
    // Validate each card has required elements
    for (const card of cards) {
      await expect(card.locator('[data-testid="similarity-score"]')).toBeVisible();
      await expect(card.locator('[data-testid="distance-value"]')).toBeVisible();
      await expect(card.locator('[data-testid="date-time"]')).toBeVisible();
    }
  }

  /**
   * Set viewport for responsive testing
   */
  async setMobileViewport(): Promise<void> {
    await this.page.setViewportSize({ width: 375, height: 667 });
  }

  async setTabletViewport(): Promise<void> {
    await this.page.setViewportSize({ width: 768, height: 1024 });
  }

  async setDesktopViewport(): Promise<void> {
    await this.page.setViewportSize({ width: 1280, height: 720 });
  }

  /**
   * Get current memory usage from browser performance API
   */
  async getMemoryUsage(): Promise<any> {
    return await this.page.evaluate(() => {
      if ('memory' in performance) {
        return {
          usedJSHeapSize: (performance as any).memory.usedJSHeapSize,
          totalJSHeapSize: (performance as any).memory.totalJSHeapSize,
          jsHeapSizeLimit: (performance as any).memory.jsHeapSizeLimit
        };
      }
      return null;
    });
  }

  /**
   * Perform a complete analog exploration workflow
   */
  async performAnalogExploration(
    horizon: '6h' | '12h' | '24h' | '48h',
    variables: string[]
  ): Promise<AnalogExplorerState> {
    await this.selectHorizon(horizon);
    await this.selectVariables(variables);
    await this.waitForAndValidateResults();
    await this.validateTransparencyDisplay();
    await this.validatePerformanceIndicators();
    await this.validateDistanceMonotonicity();
    
    return await this.getState();
  }
}