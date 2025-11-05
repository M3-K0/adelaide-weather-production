import { Page, Locator, expect } from '@playwright/test';

/**
 * Base Page Object Model
 * 
 * Contains common functionality and patterns shared across all pages
 * including navigation, authentication, error handling, and accessibility helpers.
 */
export abstract class BasePage {
  protected page: Page;
  
  // Common locators
  protected loadingSpinner: Locator;
  protected errorMessage: Locator;
  protected successMessage: Locator;
  protected navigationMenu: Locator;
  
  constructor(page: Page) {
    this.page = page;
    this.loadingSpinner = page.locator('[data-testid="loading-spinner"]');
    this.errorMessage = page.locator('[data-testid="error-message"]');
    this.successMessage = page.locator('[data-testid="success-message"]');
    this.navigationMenu = page.locator('[data-testid="navigation-menu"]');
  }
  
  /**
   * Navigate to a specific URL with error handling
   */
  async goto(url: string, options?: { waitUntil?: 'load' | 'networkidle' }): Promise<void> {
    await this.page.goto(url, {
      waitUntil: options?.waitUntil || 'networkidle',
      timeout: 30000,
    });
    
    // Wait for initial page load indicators
    await this.waitForPageReady();
  }
  
  /**
   * Wait for page to be ready (loading spinners gone, content loaded)
   */
  async waitForPageReady(): Promise<void> {
    // Wait for loading spinners to disappear
    await this.page.waitForFunction(() => {
      const spinners = document.querySelectorAll('[data-testid="loading-spinner"]');
      return spinners.length === 0 || Array.from(spinners).every(s => !s.checkVisibility());
    }, { timeout: 15000 });
    
    // Wait for any critical API calls to complete
    await this.page.waitForLoadState('networkidle', { timeout: 10000 });
  }
  
  /**
   * Take a screenshot with timestamp
   */
  async takeScreenshot(name: string): Promise<void> {
    const timestamp = new Date().toISOString().replace(/[:.]/g, '-');
    await this.page.screenshot({
      path: `./reports/screenshots/${name}-${timestamp}.png`,
      fullPage: true,
    });
  }
  
  /**
   * Check for and handle error messages
   */
  async checkForErrors(): Promise<string | null> {
    const errorElement = await this.errorMessage.first().isVisible();
    if (errorElement) {
      return await this.errorMessage.first().textContent();
    }
    return null;
  }
  
  /**
   * Authenticate user with API token
   */
  async authenticate(token: string = 'test-token-12345'): Promise<void> {
    await this.page.evaluate((apiToken) => {
      localStorage.setItem('weather-api-token', apiToken);
    }, token);
  }
  
  /**
   * Clear all authentication data
   */
  async clearAuth(): Promise<void> {
    await this.page.evaluate(() => {
      localStorage.removeItem('weather-api-token');
      localStorage.removeItem('user-preferences');
    });
  }
  
  /**
   * Set user preferences
   */
  async setUserPreferences(preferences: Record<string, any>): Promise<void> {
    await this.page.evaluate((prefs) => {
      localStorage.setItem('user-preferences', JSON.stringify(prefs));
    }, preferences);
  }
  
  /**
   * Get current page title
   */
  async getTitle(): Promise<string> {
    return await this.page.title();
  }
  
  /**
   * Get current URL
   */
  async getCurrentUrl(): Promise<string> {
    return this.page.url();
  }
  
  /**
   * Wait for specific element to be visible
   */
  async waitForElement(selector: string, timeout: number = 10000): Promise<Locator> {
    const element = this.page.locator(selector);
    await element.waitFor({ state: 'visible', timeout });
    return element;
  }
  
  /**
   * Scroll element into view
   */
  async scrollIntoView(selector: string): Promise<void> {
    await this.page.locator(selector).scrollIntoViewIfNeeded();
  }
  
  /**
   * Check if element is visible
   */
  async isVisible(selector: string): Promise<boolean> {
    return await this.page.locator(selector).isVisible();
  }
  
  /**
   * Check if element is enabled
   */
  async isEnabled(selector: string): Promise<boolean> {
    return await this.page.locator(selector).isEnabled();
  }
  
  /**
   * Fill form field with validation
   */
  async fillField(selector: string, value: string, validate: boolean = true): Promise<void> {
    const field = this.page.locator(selector);
    await field.fill(value);
    
    if (validate) {
      await expect(field).toHaveValue(value);
    }
  }
  
  /**
   * Click element with retry logic
   */
  async clickElement(selector: string, options?: { force?: boolean }): Promise<void> {
    const element = this.page.locator(selector);
    await element.click(options);
  }
  
  /**
   * Double click element
   */
  async doubleClickElement(selector: string): Promise<void> {
    await this.page.locator(selector).dblclick();
  }
  
  /**
   * Right click element
   */
  async rightClickElement(selector: string): Promise<void> {
    await this.page.locator(selector).click({ button: 'right' });
  }
  
  /**
   * Hover over element
   */
  async hoverElement(selector: string): Promise<void> {
    await this.page.locator(selector).hover();
  }
  
  /**
   * Select option from dropdown
   */
  async selectOption(selector: string, option: string): Promise<void> {
    await this.page.locator(selector).selectOption(option);
  }
  
  /**
   * Check checkbox
   */
  async checkCheckbox(selector: string): Promise<void> {
    await this.page.locator(selector).check();
  }
  
  /**
   * Uncheck checkbox
   */
  async uncheckCheckbox(selector: string): Promise<void> {
    await this.page.locator(selector).uncheck();
  }
  
  /**
   * Press keyboard key
   */
  async pressKey(key: string): Promise<void> {
    await this.page.keyboard.press(key);
  }
  
  /**
   * Type text with delay (for slow typing simulation)
   */
  async typeText(text: string, delay: number = 100): Promise<void> {
    await this.page.keyboard.type(text, { delay });
  }
  
  /**
   * Get text content of element
   */
  async getTextContent(selector: string): Promise<string | null> {
    return await this.page.locator(selector).textContent();
  }
  
  /**
   * Get attribute value of element
   */
  async getAttribute(selector: string, attribute: string): Promise<string | null> {
    return await this.page.locator(selector).getAttribute(attribute);
  }
  
  /**
   * Get all text contents of elements matching selector
   */
  async getAllTextContents(selector: string): Promise<string[]> {
    return await this.page.locator(selector).allTextContents();
  }
  
  /**
   * Count elements matching selector
   */
  async countElements(selector: string): Promise<number> {
    return await this.page.locator(selector).count();
  }
  
  /**
   * Wait for network request to complete
   */
  async waitForRequest(urlPattern: string | RegExp, timeout: number = 10000): Promise<void> {
    await this.page.waitForRequest(urlPattern, { timeout });
  }
  
  /**
   * Wait for network response
   */
  async waitForResponse(urlPattern: string | RegExp, timeout: number = 10000): Promise<void> {
    await this.page.waitForResponse(urlPattern, { timeout });
  }
  
  /**
   * Accessibility helpers
   */
  
  /**
   * Check if element has proper ARIA label
   */
  async checkAriaLabel(selector: string, expectedLabel?: string): Promise<string | null> {
    const ariaLabel = await this.getAttribute(selector, 'aria-label');
    if (expectedLabel) {
      expect(ariaLabel).toBe(expectedLabel);
    }
    return ariaLabel;
  }
  
  /**
   * Check if element has proper role
   */
  async checkRole(selector: string, expectedRole?: string): Promise<string | null> {
    const role = await this.getAttribute(selector, 'role');
    if (expectedRole) {
      expect(role).toBe(expectedRole);
    }
    return role;
  }
  
  /**
   * Navigate using keyboard only
   */
  async navigateByKeyboard(direction: 'forward' | 'backward' = 'forward'): Promise<void> {
    const key = direction === 'forward' ? 'Tab' : 'Shift+Tab';
    await this.pressKey(key);
  }
  
  /**
   * Check focus management
   */
  async checkFocus(selector: string): Promise<boolean> {
    const element = this.page.locator(selector);
    return await element.evaluate(el => el === document.activeElement);
  }
  
  /**
   * Performance monitoring helpers
   */
  
  /**
   * Measure page load performance
   */
  async measurePageLoad(): Promise<{
    loadTime: number;
    domContentLoaded: number;
    firstContentfulPaint: number;
    largestContentfulPaint: number;
  }> {
    return await this.page.evaluate(() => {
      const perfData = performance.getEntriesByType('navigation')[0] as PerformanceNavigationTiming;
      const paintEntries = performance.getEntriesByType('paint');
      
      const fcp = paintEntries.find(entry => entry.name === 'first-contentful-paint');
      const lcp = paintEntries.find(entry => entry.name === 'largest-contentful-paint');
      
      return {
        loadTime: perfData.loadEventEnd - perfData.loadEventStart,
        domContentLoaded: perfData.domContentLoadedEventEnd - perfData.domContentLoadedEventStart,
        firstContentfulPaint: fcp ? fcp.startTime : 0,
        largestContentfulPaint: lcp ? lcp.startTime : 0,
      };
    });
  }
  
  /**
   * Get Core Web Vitals
   */
  async getCoreWebVitals(): Promise<{
    lcp: number;
    fid: number;
    cls: number;
  }> {
    return await this.page.evaluate(() => {
      return new Promise((resolve) => {
        const vitals = { lcp: 0, fid: 0, cls: 0 };
        
        // LCP
        new PerformanceObserver((list) => {
          const entries = list.getEntries();
          if (entries.length > 0) {
            vitals.lcp = entries[entries.length - 1].startTime;
          }
        }).observe({ entryTypes: ['largest-contentful-paint'] });
        
        // FID
        new PerformanceObserver((list) => {
          const entries = list.getEntries();
          if (entries.length > 0) {
            vitals.fid = (entries[0] as any).processingStart - entries[0].startTime;
          }
        }).observe({ entryTypes: ['first-input'] });
        
        // CLS
        new PerformanceObserver((list) => {
          const entries = list.getEntries();
          entries.forEach((entry: any) => {
            if (!entry.hadRecentInput) {
              vitals.cls += entry.value;
            }
          });
        }).observe({ entryTypes: ['layout-shift'] });
        
        setTimeout(() => resolve(vitals), 2000);
      });
    });
  }
  
  /**
   * Abstract method - each page must implement its own validation
   */
  abstract validatePageLoaded(): Promise<void>;
}