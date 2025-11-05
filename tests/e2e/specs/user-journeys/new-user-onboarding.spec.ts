import { test, expect } from '@playwright/test';
import { HomePage } from '../../pages/HomePage';
import { AnalogExplorerPage } from '../../pages/AnalogExplorerPage';
import testData from '../../fixtures/test-data.json';

/**
 * New User Onboarding Journey Tests
 * 
 * Tests the complete experience of a first-time user from initial landing
 * through API key setup, guided tour, and first forecast request.
 */
test.describe('New User Onboarding Journey', () => {
  let homePage: HomePage;
  let analogExplorerPage: AnalogExplorerPage;
  
  test.beforeEach(async ({ page }) => {
    homePage = new HomePage(page);
    analogExplorerPage = new AnalogExplorerPage(page);
    
    // Clear any existing authentication
    await homePage.clearAuth();
  });
  
  test('Complete new user onboarding flow', async ({ page }) => {
    // Step 1: Land on homepage without authentication
    await test.step('Navigate to homepage as unauthenticated user', async () => {
      await homePage.navigateToHome();
      
      // Should see authentication prompt
      await expect(page.locator('[data-testid="auth-required-message"]')).toBeVisible();
      
      // Should not see forecast data yet
      await expect(page.locator('[data-testid="forecast-card"]')).not.toBeVisible();
    });
    
    // Step 2: API key setup process
    await test.step('Complete API key setup', async () => {
      // Click setup button
      await page.locator('[data-testid="setup-api-key"]').click();
      
      // Should see setup modal
      await expect(page.locator('[data-testid="api-setup-modal"]')).toBeVisible();
      
      // Enter API key
      await page.locator('[data-testid="api-key-input"]').fill(testData.authentication.validToken);
      
      // Submit key
      await page.locator('[data-testid="save-api-key"]').click();
      
      // Should see success message
      await expect(page.locator('[data-testid="api-key-success"]')).toBeVisible();
      
      // Modal should close
      await expect(page.locator('[data-testid="api-setup-modal"]')).not.toBeVisible();
    });
    
    // Step 3: First forecast data load
    await test.step('Verify first forecast data loads', async () => {
      // Should now see forecast card
      await expect(page.locator('[data-testid="forecast-card"]')).toBeVisible();
      
      // Should see temperature data
      await expect(page.locator('[data-testid="temperature-display"]')).toBeVisible();
      
      // Should see wind data
      await expect(page.locator('[data-testid="wind-display"]')).toBeVisible();
      
      // Validate forecast data structure
      await homePage.validateForecastData();
    });
    
    // Step 4: Guided tour initiation
    await test.step('Start guided tour', async () => {
      // Should see tour prompt for new users
      await expect(page.locator('[data-testid="tour-prompt"]')).toBeVisible();
      
      // Start tour
      await page.locator('[data-testid="start-tour"]').click();
      
      // Tour should begin
      await expect(page.locator('[data-testid="guided-tour"]')).toBeVisible();
      await expect(page.locator('[data-testid="tour-step-1"]')).toBeVisible();
    });
    
    // Step 5: Complete guided tour
    await test.step('Complete guided tour experience', async () => {
      await homePage.completeGuidedTour();
      
      // Tour completion should be recorded
      const preferences = await page.evaluate(() => {
        return JSON.parse(localStorage.getItem('user-preferences') || '{}');
      });
      
      expect(preferences.tourCompleted).toBe(true);
    });
    
    // Step 6: Explore basic functionality
    await test.step('Explore basic forecast functionality', async () => {
      // Try changing horizon
      await homePage.selectHorizon('12h');
      
      // Verify data updates
      const forecastData = await homePage.getCurrentForecastData();
      expect(forecastData.horizon).toBe('12h');
      
      // Try refreshing forecast
      await homePage.refreshForecast();
      
      // Verify refresh worked
      await expect(page.locator('[data-testid="last-updated"]')).toBeVisible();
    });
    
    // Step 7: Discover advanced features
    await test.step('Discover analog explorer', async () => {
      // Navigate to analog explorer
      await page.locator('[data-testid="explore-analogs"]').click();
      
      // Should reach analog explorer page
      await analogExplorerPage.validatePageLoaded();
      
      // Should see historical patterns
      const patterns = await analogExplorerPage.getAnalogPatterns();
      expect(patterns.length).toBeGreaterThan(0);
    });
    
    // Step 8: Return to main dashboard
    await test.step('Return to main dashboard', async () => {
      // Navigate back to home
      await page.locator('[data-testid="nav-home"]').click();
      
      // Should be back on homepage
      await homePage.validatePageLoaded();
      
      // Should still be authenticated
      await expect(page.locator('[data-testid="auth-required-message"]')).not.toBeVisible();
    });
  });
  
  test('Handle invalid API key during setup', async ({ page }) => {
    await test.step('Attempt setup with invalid API key', async () => {
      await homePage.navigateToHome();
      
      // Start API key setup
      await page.locator('[data-testid="setup-api-key"]').click();
      
      // Enter invalid API key
      await page.locator('[data-testid="api-key-input"]').fill(testData.authentication.invalidToken);
      
      // Submit key
      await page.locator('[data-testid="save-api-key"]').click();
      
      // Should see error message
      await expect(page.locator('[data-testid="api-key-error"]')).toBeVisible();
      await expect(page.locator('[data-testid="api-key-error"]')).toContainText('Invalid authentication token');
      
      // Modal should remain open
      await expect(page.locator('[data-testid="api-setup-modal"]')).toBeVisible();
      
      // Should not see forecast data
      await expect(page.locator('[data-testid="forecast-card"]')).not.toBeVisible();
    });
    
    await test.step('Correct API key after error', async () => {
      // Clear the invalid key
      await page.locator('[data-testid="api-key-input"]').clear();
      
      // Enter valid key
      await page.locator('[data-testid="api-key-input"]').fill(testData.authentication.validToken);
      
      // Submit key
      await page.locator('[data-testid="save-api-key"]').click();
      
      // Should now succeed
      await expect(page.locator('[data-testid="api-key-success"]')).toBeVisible();
      await expect(page.locator('[data-testid="forecast-card"]')).toBeVisible();
    });
  });
  
  test('Skip tour and access help system', async ({ page }) => {
    // Complete authentication
    await homePage.navigateToHome();
    await homePage.authenticate();
    await page.reload();
    await homePage.validatePageLoaded();
    
    await test.step('Skip guided tour', async () => {
      // Skip tour when prompted
      await page.locator('[data-testid="skip-tour"]').click();
      
      // Should not see tour
      await expect(page.locator('[data-testid="guided-tour"]')).not.toBeVisible();
      
      // Should still have access to functionality
      await expect(page.locator('[data-testid="forecast-card"]')).toBeVisible();
    });
    
    await test.step('Access help system later', async () => {
      // Open help system
      await homePage.openHelp();
      
      // Should see help panel
      await expect(page.locator('[data-testid="help-panel"]')).toBeVisible();
      
      // Should see option to start tour
      await expect(page.locator('[data-testid="start-tour-from-help"]')).toBeVisible();
      
      // Can start tour from help
      await page.locator('[data-testid="start-tour-from-help"]').click();
      await expect(page.locator('[data-testid="guided-tour"]')).toBeVisible();
    });
  });
  
  test('Mobile user onboarding experience', async ({ page }) => {
    // Set mobile viewport
    await page.setViewportSize({ width: 390, height: 844 });
    
    await test.step('Mobile authentication flow', async () => {
      await homePage.navigateToHome();
      
      // Should have mobile-optimized auth setup
      await page.locator('[data-testid="setup-api-key"]').click();
      
      // Modal should be mobile-responsive
      const modal = page.locator('[data-testid="api-setup-modal"]');
      await expect(modal).toBeVisible();
      
      // Check modal adapts to mobile screen
      const modalWidth = await modal.evaluate(el => el.getBoundingClientRect().width);
      expect(modalWidth).toBeLessThan(400);
    });
    
    await test.step('Mobile tour experience', async () => {
      // Complete auth
      await page.locator('[data-testid="api-key-input"]').fill(testData.authentication.validToken);
      await page.locator('[data-testid="save-api-key"]').click();
      
      // Start mobile tour
      await page.locator('[data-testid="start-tour"]').click();
      
      // Tour should be mobile-optimized
      const tourOverlay = page.locator('[data-testid="guided-tour"]');
      await expect(tourOverlay).toBeVisible();
      
      // Tour steps should be mobile-friendly
      const tourStep = page.locator('[data-testid="tour-step-1"]');
      const stepWidth = await tourStep.evaluate(el => el.getBoundingClientRect().width);
      expect(stepWidth).toBeLessThan(380);
    });
    
    await test.step('Mobile navigation patterns', async () => {
      // Complete tour
      await homePage.completeGuidedTour();
      
      // Should have mobile navigation
      await expect(page.locator('[data-testid="mobile-nav-menu"]')).toBeVisible();
      
      // Touch interactions should work
      await page.locator('[data-testid="mobile-nav-menu"]').tap();
      await expect(page.locator('[data-testid="nav-drawer"]')).toBeVisible();
    });
  });
  
  test('Accessibility-focused onboarding', async ({ page }) => {
    await test.step('Screen reader compatible authentication', async () => {
      await homePage.navigateToHome();
      
      // Check ARIA labels on auth components
      await homePage.checkAriaLabel('[data-testid="setup-api-key"]', 'Set up API key for weather forecasts');
      
      // Start setup
      await page.locator('[data-testid="setup-api-key"]').click();
      
      // Modal should have proper ARIA attributes
      const modal = page.locator('[data-testid="api-setup-modal"]');
      await homePage.checkRole('[data-testid="api-setup-modal"]', 'dialog');
      await homePage.checkAriaLabel('[data-testid="api-key-input"]', 'Enter your weather API key');
    });
    
    await test.step('Keyboard navigation through onboarding', async () => {
      // Should be able to navigate with keyboard only
      await page.keyboard.press('Tab');
      await page.keyboard.press('Enter');
      
      // Fill API key with keyboard
      await page.keyboard.type(testData.authentication.validToken);
      
      // Navigate to submit button
      await page.keyboard.press('Tab');
      await page.keyboard.press('Enter');
      
      // Should complete authentication
      await expect(page.locator('[data-testid="forecast-card"]')).toBeVisible();
    });
    
    await test.step('Screen reader friendly tour', async () => {
      // Tour should announce itself
      await page.locator('[data-testid="start-tour"]').click();
      
      // Tour steps should have proper ARIA live regions
      const tourStep = page.locator('[data-testid="tour-step-1"]');
      await homePage.checkAttribute('[data-testid="tour-step-1"]', 'aria-live', 'polite');
      
      // Should be able to complete tour with keyboard
      for (let i = 0; i < 5; i++) {
        await page.keyboard.press('Tab');
        await page.keyboard.press('Enter');
        await page.waitForTimeout(500);
      }
    });
  });
  
  test('Performance during onboarding', async ({ page }) => {
    await test.step('Measure onboarding performance', async () => {
      // Start timing
      const startTime = Date.now();
      
      await homePage.navigateToHome();
      
      // Measure page load
      const pageLoadMetrics = await homePage.measurePageLoad();
      expect(pageLoadMetrics.loadTime).toBeLessThan(3000);
      
      // Complete authentication
      await page.locator('[data-testid="setup-api-key"]').click();
      await page.locator('[data-testid="api-key-input"]').fill(testData.authentication.validToken);
      await page.locator('[data-testid="save-api-key"]').click();
      
      // Measure first forecast load
      await expect(page.locator('[data-testid="forecast-card"]')).toBeVisible();
      
      const totalOnboardingTime = Date.now() - startTime;
      expect(totalOnboardingTime).toBeLessThan(10000); // 10 seconds max
      
      // Check Core Web Vitals
      const webVitals = await homePage.getCoreWebVitals();
      expect(webVitals.lcp).toBeLessThan(2500); // LCP under 2.5s
      expect(webVitals.fid).toBeLessThan(100);  // FID under 100ms
      expect(webVitals.cls).toBeLessThan(0.1);  // CLS under 0.1
    });
  });
});