import { Page, Locator, expect } from '@playwright/test';
import { BasePage } from './BasePage';

/**
 * Home Page Object Model
 * 
 * Represents the main landing page of the Adelaide Weather Forecasting application.
 * Contains forecast cards, navigation elements, and primary user interactions.
 */
export class HomePage extends BasePage {
  // Main page elements
  private readonly pageTitle: Locator;
  private readonly forecastCard: Locator;
  private readonly refreshButton: Locator;
  private readonly settingsButton: Locator;
  
  // Forecast components
  private readonly temperatureDisplay: Locator;
  private readonly windDisplay: Locator;
  private readonly pressureDisplay: Locator;
  private readonly capeDisplay: Locator;
  private readonly analogsSection: Locator;
  
  // Navigation and controls
  private readonly horizonSelector: Locator;
  private readonly variableSelector: Locator;
  private readonly exportButton: Locator;
  private readonly historyButton: Locator;
  
  // Status indicators
  private readonly statusBar: Locator;
  private readonly lastUpdated: Locator;
  private readonly confidenceIndicator: Locator;
  
  // Help and tour
  private readonly helpButton: Locator;
  private readonly tourButton: Locator;
  private readonly guidedTour: Locator;
  
  constructor(page: Page) {
    super(page);
    
    // Initialize locators
    this.pageTitle = page.locator('[data-testid="page-title"]');
    this.forecastCard = page.locator('[data-testid="forecast-card"]');
    this.refreshButton = page.locator('[data-testid="refresh-button"]');
    this.settingsButton = page.locator('[data-testid="settings-button"]');
    
    // Forecast components
    this.temperatureDisplay = page.locator('[data-testid="temperature-display"]');
    this.windDisplay = page.locator('[data-testid="wind-display"]');
    this.pressureDisplay = page.locator('[data-testid="pressure-display"]');
    this.capeDisplay = page.locator('[data-testid="cape-badge"]');
    this.analogsSection = page.locator('[data-testid="analogs-section"]');
    
    // Controls
    this.horizonSelector = page.locator('[data-testid="horizon-selector"]');
    this.variableSelector = page.locator('[data-testid="variable-selector"]');
    this.exportButton = page.locator('[data-testid="export-button"]');
    this.historyButton = page.locator('[data-testid="history-button"]');
    
    // Status
    this.statusBar = page.locator('[data-testid="status-bar"]');
    this.lastUpdated = page.locator('[data-testid="last-updated"]');
    this.confidenceIndicator = page.locator('[data-testid="confidence-indicator"]');
    
    // Help
    this.helpButton = page.locator('[data-testid="help-button"]');
    this.tourButton = page.locator('[data-testid="tour-button"]');
    this.guidedTour = page.locator('[data-testid="guided-tour"]');
  }
  
  /**
   * Navigate to home page
   */
  async navigateToHome(): Promise<void> {
    await this.goto('/');
    await this.validatePageLoaded();
  }
  
  /**
   * Validate that the home page has loaded correctly
   */
  async validatePageLoaded(): Promise<void> {
    await expect(this.pageTitle).toBeVisible();
    await expect(this.forecastCard).toBeVisible();
    await expect(this.refreshButton).toBeVisible();
    
    // Check that essential forecast data is present
    await this.waitForElement('[data-testid="forecast-card"]');
    
    // Verify no critical errors are shown
    const errorText = await this.checkForErrors();
    if (errorText) {
      throw new Error(`Page loaded with error: ${errorText}`);
    }
  }
  
  /**
   * Get current forecast data from the display
   */
  async getCurrentForecastData(): Promise<{
    temperature?: number;
    windSpeed?: number;
    windDirection?: number;
    pressure?: number;
    cape?: number;
    horizon: string;
    lastUpdated: string;
  }> {
    await this.waitForElement('[data-testid="forecast-card"]');
    
    const data: any = {};
    
    // Extract temperature
    if (await this.temperatureDisplay.isVisible()) {
      const tempText = await this.temperatureDisplay.textContent();
      const tempMatch = tempText?.match(/(-?\d+\.?\d*)°C/);
      if (tempMatch) {
        data.temperature = parseFloat(tempMatch[1]);
      }
    }
    
    // Extract wind data
    if (await this.windDisplay.isVisible()) {
      const windText = await this.windDisplay.textContent();
      const speedMatch = windText?.match(/(\d+\.?\d*)\s*m\/s/);
      const dirMatch = windText?.match(/(\d+)°/);
      if (speedMatch) data.windSpeed = parseFloat(speedMatch[1]);
      if (dirMatch) data.windDirection = parseInt(dirMatch[1]);
    }
    
    // Extract pressure
    if (await this.pressureDisplay.isVisible()) {
      const pressureText = await this.pressureDisplay.textContent();
      const pressureMatch = pressureText?.match(/(\d+)\s*hPa/);
      if (pressureMatch) {
        data.pressure = parseInt(pressureMatch[1]);
      }
    }
    
    // Extract CAPE
    if (await this.capeDisplay.isVisible()) {
      const capeText = await this.capeDisplay.textContent();
      const capeMatch = capeText?.match(/(\d+)/);
      if (capeMatch) {
        data.cape = parseInt(capeMatch[1]);
      }
    }
    
    // Get horizon
    data.horizon = await this.getSelectedHorizon();
    
    // Get last updated time
    data.lastUpdated = await this.getLastUpdatedTime();
    
    return data;
  }
  
  /**
   * Select forecast horizon
   */
  async selectHorizon(horizon: '6h' | '12h' | '24h' | '48h'): Promise<void> {
    await this.horizonSelector.click();
    await this.page.locator(`[data-testid="horizon-option-${horizon}"]`).click();
    
    // Wait for forecast to update
    await this.waitForForecastUpdate();
  }
  
  /**
   * Get currently selected horizon
   */
  async getSelectedHorizon(): Promise<string> {
    const horizonText = await this.horizonSelector.textContent();
    return horizonText?.trim() || '24h';
  }
  
  /**
   * Select forecast variables
   */
  async selectVariables(variables: string[]): Promise<void> {
    await this.variableSelector.click();
    
    // Clear existing selections
    const clearButton = this.page.locator('[data-testid="clear-variables"]');
    if (await clearButton.isVisible()) {
      await clearButton.click();
    }
    
    // Select new variables
    for (const variable of variables) {
      await this.page.locator(`[data-testid="variable-${variable}"]`).check();
    }
    
    // Apply selection
    await this.page.locator('[data-testid="apply-variables"]').click();
    
    // Wait for forecast to update
    await this.waitForForecastUpdate();
  }
  
  /**
   * Refresh forecast data
   */
  async refreshForecast(): Promise<void> {
    const lastUpdatedBefore = await this.getLastUpdatedTime();
    
    await this.refreshButton.click();
    
    // Wait for loading to complete
    await this.waitForForecastUpdate();
    
    // Verify data was actually updated
    const lastUpdatedAfter = await this.getLastUpdatedTime();
    expect(lastUpdatedAfter).not.toBe(lastUpdatedBefore);
  }
  
  /**
   * Export forecast data
   */
  async exportForecastData(format: 'json' | 'csv' | 'pdf' = 'json'): Promise<void> {
    await this.exportButton.click();
    
    // Select format
    await this.page.locator(`[data-testid="export-${format}"]`).click();
    
    // Wait for download to start
    const downloadPromise = this.page.waitForEvent('download');
    await this.page.locator('[data-testid="confirm-export"]').click();
    
    const download = await downloadPromise;
    expect(download.suggestedFilename()).toContain(format);
  }
  
  /**
   * Open historical data browser
   */
  async openHistoricalData(): Promise<void> {
    await this.historyButton.click();
    
    // Verify historical browser opened
    await expect(this.page.locator('[data-testid="historical-browser"]')).toBeVisible();
  }
  
  /**
   * Get last updated timestamp
   */
  async getLastUpdatedTime(): Promise<string> {
    const timeText = await this.lastUpdated.textContent();
    return timeText?.trim() || '';
  }
  
  /**
   * Get confidence level
   */
  async getConfidenceLevel(): Promise<string> {
    const confidenceText = await this.confidenceIndicator.textContent();
    return confidenceText?.trim() || '';
  }
  
  /**
   * Check if analogs section is visible and get analog count
   */
  async getAnalogInfo(): Promise<{ visible: boolean; count?: number; mostSimilar?: string }> {
    const isVisible = await this.analogsSection.isVisible();
    
    if (!isVisible) {
      return { visible: false };
    }
    
    const analogText = await this.analogsSection.textContent();
    const countMatch = analogText?.match(/(\d+)\s*analog/i);
    const dateMatch = analogText?.match(/similar.*?(\d{4}-\d{2}-\d{2})/);
    
    return {
      visible: true,
      count: countMatch ? parseInt(countMatch[1]) : undefined,
      mostSimilar: dateMatch ? dateMatch[1] : undefined,
    };
  }
  
  /**
   * Start guided tour
   */
  async startGuidedTour(): Promise<void> {
    await this.tourButton.click();
    
    // Verify tour started
    await expect(this.guidedTour).toBeVisible();
    await expect(this.page.locator('[data-testid="tour-step-1"]')).toBeVisible();
  }
  
  /**
   * Complete guided tour
   */
  async completeGuidedTour(): Promise<void> {
    let stepNumber = 1;
    const maxSteps = 10; // Safety limit
    
    while (stepNumber <= maxSteps) {
      const nextButton = this.page.locator('[data-testid="tour-next"]');
      const finishButton = this.page.locator('[data-testid="tour-finish"]');
      
      if (await finishButton.isVisible()) {
        await finishButton.click();
        break;
      } else if (await nextButton.isVisible()) {
        await nextButton.click();
        stepNumber++;
      } else {
        break;
      }
      
      // Wait for animation
      await this.page.waitForTimeout(500);
    }
    
    // Verify tour completed
    await expect(this.guidedTour).not.toBeVisible();
  }
  
  /**
   * Open help system
   */
  async openHelp(): Promise<void> {
    await this.helpButton.click();
    
    // Verify help panel opened
    await expect(this.page.locator('[data-testid="help-panel"]')).toBeVisible();
  }
  
  /**
   * Check status bar information
   */
  async getStatusInfo(): Promise<{
    systemStatus: string;
    apiStatus: string;
    dataAge: string;
  }> {
    await this.waitForElement('[data-testid="status-bar"]');
    
    const statusText = await this.statusBar.textContent();
    
    // Parse status information
    const systemMatch = statusText?.match(/System:\s*(\w+)/i);
    const apiMatch = statusText?.match(/API:\s*(\w+)/i);
    const ageMatch = statusText?.match(/Data:\s*(.+?)(?:\s|$)/i);
    
    return {
      systemStatus: systemMatch ? systemMatch[1] : 'unknown',
      apiStatus: apiMatch ? apiMatch[1] : 'unknown',
      dataAge: ageMatch ? ageMatch[1] : 'unknown',
    };
  }
  
  /**
   * Wait for forecast data to update
   */
  private async waitForForecastUpdate(): Promise<void> {
    // Wait for loading spinner to appear and disappear
    await this.page.waitForSelector('[data-testid="loading-spinner"]', { 
      state: 'visible', 
      timeout: 5000 
    }).catch(() => {}); // Ignore if spinner doesn't appear
    
    await this.page.waitForSelector('[data-testid="loading-spinner"]', { 
      state: 'hidden', 
      timeout: 15000 
    }).catch(() => {}); // Ignore if spinner wasn't present
    
    // Wait for network to be idle
    await this.page.waitForLoadState('networkidle', { timeout: 10000 });
    
    // Ensure forecast card is updated
    await expect(this.forecastCard).toBeVisible();
  }
  
  /**
   * Validate forecast data structure and ranges
   */
  async validateForecastData(): Promise<void> {
    const data = await this.getCurrentForecastData();
    
    // Temperature validation (-50°C to 60°C)
    if (data.temperature !== undefined) {
      expect(data.temperature).toBeGreaterThan(-50);
      expect(data.temperature).toBeLessThan(60);
    }
    
    // Wind speed validation (0 to 200 m/s)
    if (data.windSpeed !== undefined) {
      expect(data.windSpeed).toBeGreaterThanOrEqual(0);
      expect(data.windSpeed).toBeLessThan(200);
    }
    
    // Wind direction validation (0 to 360 degrees)
    if (data.windDirection !== undefined) {
      expect(data.windDirection).toBeGreaterThanOrEqual(0);
      expect(data.windDirection).toBeLessThan(360);
    }
    
    // Pressure validation (800 to 1100 hPa)
    if (data.pressure !== undefined) {
      expect(data.pressure).toBeGreaterThan(800);
      expect(data.pressure).toBeLessThan(1100);
    }
    
    // CAPE validation (0 to 10000)
    if (data.cape !== undefined) {
      expect(data.cape).toBeGreaterThanOrEqual(0);
      expect(data.cape).toBeLessThan(10000);
    }
    
    // Verify horizon is valid
    expect(['6h', '12h', '24h', '48h']).toContain(data.horizon);
    
    // Verify last updated timestamp is recent (within last hour)
    const lastUpdated = new Date(data.lastUpdated);
    const now = new Date();
    const hourAgo = new Date(now.getTime() - 60 * 60 * 1000);
    expect(lastUpdated).toBeInstanceOf(Date);
    expect(lastUpdated.getTime()).toBeGreaterThan(hourAgo.getTime());
  }
}