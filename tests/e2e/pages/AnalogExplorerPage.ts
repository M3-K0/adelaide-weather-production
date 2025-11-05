import { Page, Locator, expect } from '@playwright/test';
import { BasePage } from './BasePage';

/**
 * Analog Explorer Page Object Model
 * 
 * Represents the analog pattern exploration interface for viewing
 * historical weather patterns similar to current conditions.
 */
export class AnalogExplorerPage extends BasePage {
  // Main components
  private readonly analogTable: Locator;
  private readonly analogMap: Locator;
  private readonly similarityChart: Locator;
  private readonly filterPanel: Locator;
  private readonly patternViewer: Locator;
  
  // Controls
  private readonly dateRangePicker: Locator;
  private readonly similarityThreshold: Locator;
  private readonly variableWeights: Locator;
  private readonly sortControls: Locator;
  private readonly exportAnalogs: Locator;
  
  // Analog details
  private readonly analogDetails: Locator;
  private readonly weatherConditions: Locator;
  private readonly outcomeDescription: Locator;
  private readonly confidenceScore: Locator;
  
  // Interactive elements
  private readonly analogRows: Locator;
  private readonly mapMarkers: Locator;
  private readonly timelineSlider: Locator;
  
  constructor(page: Page) {
    super(page);
    
    // Initialize locators
    this.analogTable = page.locator('[data-testid="analog-table"]');
    this.analogMap = page.locator('[data-testid="analog-map"]');
    this.similarityChart = page.locator('[data-testid="similarity-chart"]');
    this.filterPanel = page.locator('[data-testid="filter-panel"]');
    this.patternViewer = page.locator('[data-testid="pattern-viewer"]');
    
    // Controls
    this.dateRangePicker = page.locator('[data-testid="date-range-picker"]');
    this.similarityThreshold = page.locator('[data-testid="similarity-threshold"]');
    this.variableWeights = page.locator('[data-testid="variable-weights"]');
    this.sortControls = page.locator('[data-testid="sort-controls"]');
    this.exportAnalogs = page.locator('[data-testid="export-analogs"]');
    
    // Details
    this.analogDetails = page.locator('[data-testid="analog-details"]');
    this.weatherConditions = page.locator('[data-testid="weather-conditions"]');
    this.outcomeDescription = page.locator('[data-testid="outcome-description"]');
    this.confidenceScore = page.locator('[data-testid="confidence-score"]');
    
    // Interactive
    this.analogRows = page.locator('[data-testid^="analog-row-"]');
    this.mapMarkers = page.locator('[data-testid^="map-marker-"]');
    this.timelineSlider = page.locator('[data-testid="timeline-slider"]');
  }
  
  /**
   * Navigate to analog explorer page
   */
  async navigateToAnalogExplorer(): Promise<void> {
    await this.goto('/analog-demo');
    await this.validatePageLoaded();
  }
  
  /**
   * Validate that the analog explorer page has loaded correctly
   */
  async validatePageLoaded(): Promise<void> {
    await expect(this.analogTable).toBeVisible();
    await expect(this.analogMap).toBeVisible();
    await expect(this.filterPanel).toBeVisible();
    
    // Check that analog data is loaded
    await this.waitForElement('[data-testid="analog-table"]');
    
    // Verify no critical errors
    const errorText = await this.checkForErrors();
    if (errorText) {
      throw new Error(`Analog explorer loaded with error: ${errorText}`);
    }
  }
  
  /**
   * Get list of analog patterns
   */
  async getAnalogPatterns(): Promise<{
    id: string;
    date: string;
    similarity: number;
    outcome: string;
    confidence: number;
  }[]> {
    await this.waitForElement('[data-testid="analog-table"]');
    
    const patterns: any[] = [];
    const rowCount = await this.analogRows.count();
    
    for (let i = 0; i < rowCount; i++) {
      const row = this.analogRows.nth(i);
      
      const id = await row.getAttribute('data-analog-id') || `analog-${i}`;
      const dateCell = row.locator('[data-testid="analog-date"]');
      const similarityCell = row.locator('[data-testid="analog-similarity"]');
      const outcomeCell = row.locator('[data-testid="analog-outcome"]');
      const confidenceCell = row.locator('[data-testid="analog-confidence"]');
      
      const date = await dateCell.textContent() || '';
      const similarityText = await similarityCell.textContent() || '0';
      const outcome = await outcomeCell.textContent() || '';
      const confidenceText = await confidenceCell.textContent() || '0';
      
      // Parse similarity percentage
      const similarityMatch = similarityText.match(/(\d+\.?\d*)%/);
      const similarity = similarityMatch ? parseFloat(similarityMatch[1]) : 0;
      
      // Parse confidence score
      const confidenceMatch = confidenceText.match(/(\d+\.?\d*)/);
      const confidence = confidenceMatch ? parseFloat(confidenceMatch[1]) : 0;
      
      patterns.push({
        id,
        date: date.trim(),
        similarity,
        outcome: outcome.trim(),
        confidence,
      });
    }
    
    return patterns;
  }
  
  /**
   * Select analog pattern by index or ID
   */
  async selectAnalogPattern(identifier: number | string): Promise<void> {
    let row: Locator;
    
    if (typeof identifier === 'number') {
      row = this.analogRows.nth(identifier);
    } else {
      row = this.page.locator(`[data-analog-id="${identifier}"]`);
    }
    
    await row.click();
    
    // Wait for details panel to update
    await this.waitForElement('[data-testid="analog-details"]');
  }
  
  /**
   * Get selected analog pattern details
   */
  async getSelectedAnalogDetails(): Promise<{
    date: string;
    similarity: number;
    conditions: Record<string, any>;
    outcome: string;
    confidence: number;
  }> {
    await this.waitForElement('[data-testid="analog-details"]');
    
    // Extract date and similarity from header
    const headerText = await this.analogDetails.locator('[data-testid="analog-header"]').textContent();
    const dateMatch = headerText?.match(/(\d{4}-\d{2}-\d{2})/);
    const similarityMatch = headerText?.match(/(\d+\.?\d*)%/);
    
    // Get weather conditions
    const conditions: Record<string, any> = {};
    const conditionElements = this.weatherConditions.locator('[data-testid^="condition-"]');
    const conditionCount = await conditionElements.count();
    
    for (let i = 0; i < conditionCount; i++) {
      const element = conditionElements.nth(i);
      const variable = await element.getAttribute('data-variable');
      const value = await element.textContent();
      
      if (variable && value) {
        // Parse numeric values
        const numericMatch = value.match(/(-?\d+\.?\d*)/);
        conditions[variable] = numericMatch ? parseFloat(numericMatch[1]) : value.trim();
      }
    }
    
    // Get outcome description
    const outcome = await this.outcomeDescription.textContent() || '';
    
    // Get confidence score
    const confidenceText = await this.confidenceScore.textContent() || '0';
    const confidenceMatch = confidenceText.match(/(\d+\.?\d*)/);
    const confidence = confidenceMatch ? parseFloat(confidenceMatch[1]) : 0;
    
    return {
      date: dateMatch ? dateMatch[1] : '',
      similarity: similarityMatch ? parseFloat(similarityMatch[1]) : 0,
      conditions,
      outcome: outcome.trim(),
      confidence,
    };
  }
  
  /**
   * Filter analogs by date range
   */
  async filterByDateRange(startDate: string, endDate: string): Promise<void> {
    await this.dateRangePicker.click();
    
    // Set start date
    const startInput = this.page.locator('[data-testid="start-date-input"]');
    await startInput.fill(startDate);
    
    // Set end date
    const endInput = this.page.locator('[data-testid="end-date-input"]');
    await endInput.fill(endDate);
    
    // Apply filter
    await this.page.locator('[data-testid="apply-date-filter"]').click();
    
    // Wait for table to update
    await this.waitForAnalogUpdate();
  }
  
  /**
   * Set similarity threshold
   */
  async setSimilarityThreshold(threshold: number): Promise<void> {
    await this.similarityThreshold.fill(threshold.toString());
    
    // Apply threshold
    await this.page.locator('[data-testid="apply-threshold"]').click();
    
    // Wait for results to update
    await this.waitForAnalogUpdate();
  }
  
  /**
   * Configure variable weights for similarity calculation
   */
  async setVariableWeights(weights: Record<string, number>): Promise<void> {
    await this.variableWeights.click();
    
    for (const [variable, weight] of Object.entries(weights)) {
      const weightSlider = this.page.locator(`[data-testid="weight-${variable}"]`);
      await weightSlider.fill(weight.toString());
    }
    
    // Apply weights
    await this.page.locator('[data-testid="apply-weights"]').click();
    
    // Wait for recalculation
    await this.waitForAnalogUpdate();
  }
  
  /**
   * Sort analogs by criteria
   */
  async sortAnalogs(criteria: 'similarity' | 'date' | 'confidence', direction: 'asc' | 'desc' = 'desc'): Promise<void> {
    await this.sortControls.click();
    
    // Select sort criteria
    await this.page.locator(`[data-testid="sort-${criteria}"]`).click();
    
    // Select direction
    await this.page.locator(`[data-testid="sort-${direction}"]`).click();
    
    // Wait for table to re-sort
    await this.waitForAnalogUpdate();
  }
  
  /**
   * Export analog data
   */
  async exportAnalogData(format: 'csv' | 'json' | 'pdf' = 'csv'): Promise<void> {
    await this.exportAnalogs.click();
    
    // Select format
    await this.page.locator(`[data-testid="export-format-${format}"]`).click();
    
    // Start download
    const downloadPromise = this.page.waitForEvent('download');
    await this.page.locator('[data-testid="confirm-analog-export"]').click();
    
    const download = await downloadPromise;
    expect(download.suggestedFilename()).toContain(`analogs.${format}`);
  }
  
  /**
   * Interact with map visualization
   */
  async selectMapMarker(markerIndex: number): Promise<void> {
    const marker = this.mapMarkers.nth(markerIndex);
    await marker.click();
    
    // Wait for marker details to appear
    await this.waitForElement('[data-testid="marker-popup"]');
  }
  
  /**
   * Use timeline slider to explore temporal patterns
   */
  async setTimelinePosition(position: number): Promise<void> {
    // Position should be between 0 and 100 (percentage)
    await this.timelineSlider.fill(position.toString());
    
    // Wait for visualization to update
    await this.page.waitForTimeout(500);
  }
  
  /**
   * Get similarity chart data
   */
  async getSimilarityChartData(): Promise<{
    dates: string[];
    similarities: number[];
    selectedDate?: string;
  }> {
    await this.waitForElement('[data-testid="similarity-chart"]');
    
    // Extract chart data via JavaScript
    return await this.page.evaluate(() => {
      const chartElement = document.querySelector('[data-testid="similarity-chart"]');
      if (!chartElement) return { dates: [], similarities: [] };
      
      // This would depend on the specific chart library used
      // For now, return mock data structure
      return {
        dates: ['2023-01-15', '2023-02-20', '2023-03-10'],
        similarities: [85.2, 78.9, 92.1],
        selectedDate: '2023-03-10'
      };
    });
  }
  
  /**
   * Validate analog pattern data quality
   */
  async validateAnalogData(): Promise<void> {
    const patterns = await this.getAnalogPatterns();
    
    // Ensure we have some analog patterns
    expect(patterns.length).toBeGreaterThan(0);
    
    for (const pattern of patterns) {
      // Validate similarity is a percentage (0-100)
      expect(pattern.similarity).toBeGreaterThanOrEqual(0);
      expect(pattern.similarity).toBeLessThanOrEqual(100);
      
      // Validate confidence score
      expect(pattern.confidence).toBeGreaterThanOrEqual(0);
      expect(pattern.confidence).toBeLessThanOrEqual(1);
      
      // Validate date format
      expect(pattern.date).toMatch(/\d{4}-\d{2}-\d{2}/);
      
      // Validate outcome is not empty
      expect(pattern.outcome.length).toBeGreaterThan(0);
    }
  }
  
  /**
   * Check analog explorer accessibility features
   */
  async checkAccessibilityFeatures(): Promise<void> {
    // Check table has proper headers
    const tableHeaders = this.analogTable.locator('th');
    const headerCount = await tableHeaders.count();
    expect(headerCount).toBeGreaterThan(0);
    
    // Check each header has proper scope
    for (let i = 0; i < headerCount; i++) {
      const header = tableHeaders.nth(i);
      const scope = await header.getAttribute('scope');
      expect(scope).toBe('col');
    }
    
    // Check rows are properly labeled
    const firstRow = this.analogRows.first();
    const role = await firstRow.getAttribute('role');
    expect(['row', 'button']).toContain(role);
    
    // Check keyboard navigation
    await firstRow.focus();
    await this.pressKey('ArrowDown');
    
    // Verify focus moved to next row
    const secondRow = this.analogRows.nth(1);
    const isSecondRowFocused = await this.checkFocus('[data-testid^="analog-row-"]:nth-child(2)');
    expect(isSecondRowFocused).toBe(true);
  }
  
  /**
   * Test analog explorer performance
   */
  async measureAnalogExplorerPerformance(): Promise<{
    loadTime: number;
    filterTime: number;
    sortTime: number;
  }> {
    const startTime = Date.now();
    
    // Measure initial load
    await this.validatePageLoaded();
    const loadTime = Date.now() - startTime;
    
    // Measure filter performance
    const filterStart = Date.now();
    await this.setSimilarityThreshold(75);
    const filterTime = Date.now() - filterStart;
    
    // Measure sort performance
    const sortStart = Date.now();
    await this.sortAnalogs('similarity', 'asc');
    const sortTime = Date.now() - sortStart;
    
    return {
      loadTime,
      filterTime,
      sortTime,
    };
  }
  
  /**
   * Wait for analog data to update after operations
   */
  private async waitForAnalogUpdate(): Promise<void> {
    // Wait for loading indicator
    await this.page.waitForSelector('[data-testid="analog-loading"]', { 
      state: 'visible', 
      timeout: 3000 
    }).catch(() => {}); // Ignore if not found
    
    // Wait for loading to complete
    await this.page.waitForSelector('[data-testid="analog-loading"]', { 
      state: 'hidden', 
      timeout: 10000 
    }).catch(() => {}); // Ignore if wasn't present
    
    // Ensure table is visible and updated
    await expect(this.analogTable).toBeVisible();
    
    // Wait for network to be idle
    await this.page.waitForLoadState('networkidle', { timeout: 5000 });
  }
}