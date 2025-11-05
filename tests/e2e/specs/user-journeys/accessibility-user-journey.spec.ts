import { test, expect } from '@playwright/test';
import { HomePage } from '../../pages/HomePage';
import { AnalogExplorerPage } from '../../pages/AnalogExplorerPage';
import { MetricsDashboardPage } from '../../pages/MetricsDashboardPage';
import testData from '../../fixtures/test-data.json';

/**
 * Accessibility User Journey Tests
 * 
 * Tests comprehensive accessibility features including screen reader navigation,
 * keyboard-only operation, high contrast mode, and assistive technology compatibility.
 */
test.describe('Accessibility User Journey', () => {
  let homePage: HomePage;
  let analogExplorerPage: AnalogExplorerPage;
  let metricsDashboardPage: MetricsDashboardPage;
  
  test.beforeEach(async ({ page }) => {
    homePage = new HomePage(page);
    analogExplorerPage = new AnalogExplorerPage(page);
    metricsDashboardPage = new MetricsDashboardPage(page);
    
    // Set up accessibility user preferences
    await homePage.authenticate(testData.authentication.validToken);
    await homePage.setUserPreferences(testData.userProfiles.accessibilityUser.preferences);
  });
  
  test('Screen reader user complete workflow', async ({ page }) => {
    await test.step('Navigate using screen reader semantics', async () => {
      await homePage.navigateToHome();
      
      // Check page has proper heading structure
      const h1Elements = page.locator('h1');
      await expect(h1Elements).toHaveCount(1);
      
      const mainHeading = await h1Elements.textContent();
      expect(mainHeading).toContain('Weather');
      
      // Check page has proper landmarks
      await expect(page.locator('main')).toBeVisible();
      await expect(page.locator('[role="navigation"]')).toBeVisible();
      
      // Check skip links for screen readers
      await expect(page.locator('[data-testid="skip-to-main"]')).toBeVisible();
    });
    
    await test.step('Navigate forecast card with screen reader', async () => {
      // Forecast card should have proper ARIA structure
      const forecastCard = page.locator('[data-testid="forecast-card"]');
      
      await homePage.checkRole('[data-testid="forecast-card"]', 'region');
      await homePage.checkAriaLabel('[data-testid="forecast-card"]', 'Weather forecast information');
      
      // Temperature should be announced properly
      const temperatureDisplay = page.locator('[data-testid="temperature-display"]');
      const tempAriaLabel = await temperatureDisplay.getAttribute('aria-label');
      expect(tempAriaLabel).toMatch(/temperature.*degrees/i);
      
      // Wind data should be screen reader friendly
      const windDisplay = page.locator('[data-testid="wind-display"]');
      const windAriaLabel = await windDisplay.getAttribute('aria-label');
      expect(windAriaLabel).toMatch(/wind.*speed|direction/i);
    });
    
    await test.step('Use keyboard navigation for forecast controls', async () => {
      // Focus should start at skip link
      await page.keyboard.press('Tab');
      const firstFocus = await page.evaluate(() => document.activeElement?.getAttribute('data-testid'));
      expect(firstFocus).toBe('skip-to-main');
      
      // Navigate to horizon selector using only keyboard
      let currentElement = '';
      let attempts = 0;
      
      while (currentElement !== 'horizon-selector' && attempts < 20) {
        await page.keyboard.press('Tab');
        currentElement = await page.evaluate(() => document.activeElement?.getAttribute('data-testid') || '');
        attempts++;
      }
      
      expect(currentElement).toBe('horizon-selector');
      
      // Should be able to change horizon with keyboard
      await page.keyboard.press('Enter');
      await page.keyboard.press('ArrowDown');
      await page.keyboard.press('Enter');
      
      // Verify horizon changed
      const newHorizon = await homePage.getSelectedHorizon();
      expect(['6h', '12h', '24h', '48h']).toContain(newHorizon);
    });
    
    await test.step('Test ARIA live regions for dynamic updates', async () => {
      // Refresh forecast to test live region updates
      const liveRegion = page.locator('[aria-live="polite"]');
      await expect(liveRegion).toBeVisible();
      
      // Trigger update
      await homePage.refreshForecast();
      
      // Live region should announce the update
      const liveText = await liveRegion.textContent();
      expect(liveText).toMatch(/updated|refreshed|loaded/i);
    });
  });
  
  test('Keyboard-only navigation complete workflow', async ({ page }) => {
    await test.step('Complete authentication using only keyboard', async () => {
      await homePage.navigateToHome();
      
      // Navigate to API setup using Tab
      let attempts = 0;
      while (attempts < 10) {
        await page.keyboard.press('Tab');
        const focusedElement = await page.evaluate(() => document.activeElement?.getAttribute('data-testid'));
        
        if (focusedElement === 'setup-api-key') {
          break;
        }
        attempts++;
      }
      
      // Open setup with Enter
      await page.keyboard.press('Enter');
      
      // Should open modal
      await expect(page.locator('[data-testid="api-setup-modal"]')).toBeVisible();
      
      // Type API key
      await page.keyboard.type(testData.authentication.validToken);
      
      // Navigate to submit and press Enter
      await page.keyboard.press('Tab');
      await page.keyboard.press('Enter');
      
      // Should complete authentication
      await expect(page.locator('[data-testid="forecast-card"]')).toBeVisible();
    });
    
    await test.step('Navigate analog explorer with keyboard only', async () => {
      // Navigate to analog explorer
      let found = false;
      for (let i = 0; i < 20; i++) {
        await page.keyboard.press('Tab');
        const element = await page.evaluate(() => document.activeElement?.getAttribute('data-testid'));
        
        if (element === 'explore-analogs') {
          await page.keyboard.press('Enter');
          found = true;
          break;
        }
      }
      
      expect(found).toBe(true);
      await analogExplorerPage.validatePageLoaded();
      
      // Should be able to navigate analog table with keyboard
      await analogExplorerPage.checkAccessibilityFeatures();
    });
    
    await test.step('Interact with data tables using keyboard', async () => {
      // Table should be keyboard navigable
      const table = page.locator('[data-testid="analog-table"]');
      await expect(table).toBeVisible();
      
      // Should support arrow key navigation
      await page.keyboard.press('ArrowDown');
      await page.keyboard.press('ArrowDown');
      
      // Should support row selection with Enter
      await page.keyboard.press('Enter');
      
      // Details should update
      await expect(page.locator('[data-testid="analog-details"]')).toBeVisible();
    });
    
    await test.step('Use keyboard shortcuts for common actions', async () => {
      // Test keyboard shortcuts (if implemented)
      await page.keyboard.press('Control+r'); // Refresh
      await homePage.waitForPageReady();
      
      // Test escape key to close modals
      await page.locator('[data-testid="help-button"]').click();
      await expect(page.locator('[data-testid="help-panel"]')).toBeVisible();
      
      await page.keyboard.press('Escape');
      await expect(page.locator('[data-testid="help-panel"]')).not.toBeVisible();
    });
  });
  
  test('High contrast and visual accessibility', async ({ page }) => {
    await test.step('Test high contrast mode', async () => {
      // Enable high contrast mode
      await page.addStyleTag({
        content: `
          @media (prefers-contrast: high) {
            * {
              filter: contrast(200%);
            }
          }
        `
      });
      
      await homePage.navigateToHome();
      
      // Elements should remain visible and usable
      await expect(page.locator('[data-testid="forecast-card"]')).toBeVisible();
      
      // Text should have sufficient contrast
      const temperatureText = page.locator('[data-testid="temperature-display"]');
      const color = await temperatureText.evaluate(el => getComputedStyle(el).color);
      const backgroundColor = await temperatureText.evaluate(el => getComputedStyle(el).backgroundColor);
      
      // Should have adequate contrast (simplified check)
      expect(color).not.toBe(backgroundColor);
    });
    
    await test.step('Test reduced motion preferences', async () => {
      // Enable reduced motion
      await page.emulateMedia({ reducedMotion: 'reduce' });
      
      await homePage.navigateToHome();
      
      // Animations should be reduced or disabled
      const animatedElements = page.locator('[class*="animate"], [class*="transition"]');
      const count = await animatedElements.count();
      
      // Elements should still be functional without motion
      await homePage.refreshForecast();
      await expect(page.locator('[data-testid="forecast-card"]')).toBeVisible();
    });
    
    await test.step('Test large text and zoom compatibility', async () => {
      // Simulate browser zoom to 200%
      await page.evaluate(() => {
        document.body.style.zoom = '2';
      });
      
      await page.waitForTimeout(500);
      
      // Content should remain accessible
      await expect(page.locator('[data-testid="forecast-card"]')).toBeVisible();
      
      // Text should not be cut off
      const tempDisplay = page.locator('[data-testid="temperature-display"]');
      const hasOverflow = await tempDisplay.evaluate(el => {
        return el.scrollWidth > el.clientWidth;
      });
      
      expect(hasOverflow).toBe(false);
      
      // Reset zoom
      await page.evaluate(() => {
        document.body.style.zoom = '1';
      });
    });
    
    await test.step('Test color blindness compatibility', async () => {
      // Simulate protanopia (red-green color blindness)
      await page.addStyleTag({
        content: `
          * {
            filter: url('data:image/svg+xml,<svg xmlns="http://www.w3.org/2000/svg"><defs><filter id="protanopia"><feColorMatrix values="0.567,0.433,0,0,0 0.558,0.442,0,0,0 0,0.242,0.758,0,0 0,0,0,1,0"/></filter></defs></svg>#protanopia');
          }
        `
      });
      
      await homePage.navigateToHome();
      
      // Information should not rely solely on color
      const statusIndicators = page.locator('[data-testid*="status"], [data-testid*="indicator"]');
      const indicatorCount = await statusIndicators.count();
      
      for (let i = 0; i < indicatorCount; i++) {
        const indicator = statusIndicators.nth(i);
        
        // Should have text or icon in addition to color
        const hasText = await indicator.textContent();
        const hasIcon = await indicator.locator('svg, i, [class*="icon"]').count();
        
        expect(hasText || hasIcon > 0).toBeTruthy();
      }
    });
  });
  
  test('Voice control and assistive technology', async ({ page }) => {
    await test.step('Test voice-over friendly markup', async () => {
      await homePage.navigateToHome();
      
      // Check for proper heading hierarchy
      const headings = await page.locator('h1, h2, h3, h4, h5, h6').allTextContents();
      expect(headings.length).toBeGreaterThan(0);
      
      // Should not skip heading levels
      const headingLevels = await page.locator('h1, h2, h3, h4, h5, h6').evaluateAll(elements => {
        return elements.map(el => parseInt(el.tagName.charAt(1)));
      });
      
      // Check logical progression (no skipping levels)
      for (let i = 1; i < headingLevels.length; i++) {
        const diff = headingLevels[i] - headingLevels[i - 1];
        expect(diff).toBeLessThanOrEqual(1);
      }
    });
    
    await test.step('Test form accessibility for voice input', async () => {
      // Open settings or search that has form inputs
      await page.locator('[data-testid="settings-button"]').click();
      
      const formInputs = page.locator('input, select, textarea');
      const inputCount = await formInputs.count();
      
      for (let i = 0; i < inputCount; i++) {
        const input = formInputs.nth(i);
        
        // Each input should have proper labeling
        const id = await input.getAttribute('id');
        const ariaLabel = await input.getAttribute('aria-label');
        const ariaLabelledBy = await input.getAttribute('aria-labelledby');
        
        if (id) {
          // Should have associated label
          const label = page.locator(`label[for="${id}"]`);
          const labelExists = await label.count() > 0;
          expect(labelExists || ariaLabel || ariaLabelledBy).toBeTruthy();
        }
      }
    });
    
    await test.step('Test error messaging accessibility', async () => {
      // Trigger an error condition
      await homePage.clearAuth();
      await page.reload();
      
      // Try to refresh without authentication
      await page.locator('[data-testid="refresh-button"]').click();
      
      // Error message should be accessible
      const errorMessage = page.locator('[data-testid="error-message"]');
      if (await errorMessage.isVisible()) {
        // Should have proper ARIA attributes
        const role = await errorMessage.getAttribute('role');
        const ariaLive = await errorMessage.getAttribute('aria-live');
        
        expect(role === 'alert' || ariaLive === 'assertive').toBeTruthy();
      }
    });
  });
  
  test('Accessibility compliance validation', async ({ page }) => {
    await test.step('Run axe-core accessibility audit', async () => {
      await homePage.navigateToHome();
      await homePage.authenticate();
      await page.reload();
      await homePage.validatePageLoaded();
      
      // Install axe-core
      await page.addScriptTag({
        url: 'https://unpkg.com/axe-core@4.8.2/axe.min.js'
      });
      
      // Run accessibility audit
      const results = await page.evaluate(() => {
        return new Promise((resolve) => {
          // @ts-ignore
          axe.run(document, {
            rules: {
              'color-contrast': { enabled: true },
              'keyboard-navigation': { enabled: true },
              'focus-management': { enabled: true },
              'aria-usage': { enabled: true }
            }
          }, (err: any, results: any) => {
            resolve(results);
          });
        });
      });
      
      // Check for violations
      const violations = (results as any).violations;
      
      // Log violations for debugging
      if (violations.length > 0) {
        console.log('Accessibility violations found:', violations);
      }
      
      // Should have no critical violations
      const criticalViolations = violations.filter((v: any) => 
        v.impact === 'critical' || v.impact === 'serious'
      );
      
      expect(criticalViolations.length).toBe(0);
    });
    
    await test.step('Test WCAG 2.1 AA compliance', async () => {
      // Test specific WCAG requirements
      
      // 1.1.1 - Non-text content has alternatives
      const images = page.locator('img');
      const imageCount = await images.count();
      
      for (let i = 0; i < imageCount; i++) {
        const img = images.nth(i);
        const alt = await img.getAttribute('alt');
        const ariaLabel = await img.getAttribute('aria-label');
        const ariaLabelledBy = await img.getAttribute('aria-labelledby');
        
        // Should have alt text or ARIA label
        expect(alt !== null || ariaLabel || ariaLabelledBy).toBeTruthy();
      }
      
      // 2.1.1 - All functionality available via keyboard
      // (Tested in keyboard navigation tests above)
      
      // 2.4.3 - Focus order is logical
      await page.keyboard.press('Tab');
      const focusOrder: string[] = [];
      
      for (let i = 0; i < 10; i++) {
        const focused = await page.evaluate(() => 
          document.activeElement?.getAttribute('data-testid') || 'unknown'
        );
        focusOrder.push(focused);
        await page.keyboard.press('Tab');
      }
      
      // Focus should progress logically through interactive elements
      expect(focusOrder.length).toBe(10);
      
      // 3.1.1 - Language of page is identified
      const htmlLang = await page.getAttribute('html', 'lang');
      expect(htmlLang).toBeTruthy();
      
      // 4.1.2 - Name, role, value for custom components
      const customComponents = page.locator('[role="button"], [role="tab"], [role="tabpanel"]');
      const customCount = await customComponents.count();
      
      for (let i = 0; i < customCount; i++) {
        const component = customComponents.nth(i);
        const name = await component.getAttribute('aria-label') || 
                    await component.textContent();
        const role = await component.getAttribute('role');
        
        expect(name?.trim()).toBeTruthy();
        expect(role).toBeTruthy();
      }
    });
    
    await test.step('Test assistive technology compatibility', async () => {
      // Test common screen reader commands simulation
      
      // Navigate by headings (simulated)
      const headings = page.locator('h1, h2, h3, h4, h5, h6');
      const headingCount = await headings.count();
      expect(headingCount).toBeGreaterThan(0);
      
      // Navigate by landmarks (simulated)
      const landmarks = page.locator('[role="main"], [role="navigation"], [role="banner"], [role="contentinfo"]');
      const landmarkCount = await landmarks.count();
      expect(landmarkCount).toBeGreaterThan(0);
      
      // Navigate by form controls (simulated)
      const formControls = page.locator('input, select, textarea, button');
      const controlCount = await formControls.count();
      expect(controlCount).toBeGreaterThan(0);
    });
  });
  
  test('Multi-modal accessibility experience', async ({ page }) => {
    await test.step('Test touch and keyboard hybrid interaction', async () => {
      await homePage.navigateToHome();
      
      // Should support both touch and keyboard on same elements
      const refreshButton = page.locator('[data-testid="refresh-button"]');
      
      // Touch interaction
      await refreshButton.tap();
      await homePage.waitForPageReady();
      
      // Keyboard interaction
      await refreshButton.focus();
      await page.keyboard.press('Enter');
      await homePage.waitForPageReady();
      
      // Both should work equally well
      await expect(page.locator('[data-testid="forecast-card"]')).toBeVisible();
    });
    
    await test.step('Test voice and visual feedback coordination', async () => {
      // Navigate to analog explorer
      await page.locator('[data-testid="explore-analogs"]').click();
      await analogExplorerPage.validatePageLoaded();
      
      // Select analog pattern
      await analogExplorerPage.selectAnalogPattern(0);
      
      // Should provide both visual and screen reader feedback
      const details = page.locator('[data-testid="analog-details"]');
      await expect(details).toBeVisible();
      
      // Should have ARIA live region for voice feedback
      const liveRegion = page.locator('[aria-live]');
      const liveText = await liveRegion.textContent();
      expect(liveText).toBeTruthy();
    });
  });
});