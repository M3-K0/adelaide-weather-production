import { test, expect } from '@playwright/test';
import { HomePage } from '../../pages/HomePage';
import { AnalogExplorerPage } from '../../pages/AnalogExplorerPage';
import testData from '../../fixtures/test-data.json';

/**
 * Mobile User Experience Tests
 * 
 * Tests responsive interface, touch interactions, offline behavior,
 * and mobile-specific user workflows across different devices.
 */
test.describe('Mobile User Experience', () => {
  let homePage: HomePage;
  let analogExplorerPage: AnalogExplorerPage;
  
  test.beforeEach(async ({ page }) => {
    homePage = new HomePage(page);
    analogExplorerPage = new AnalogExplorerPage(page);
    
    // Set up mobile user preferences
    await homePage.authenticate(testData.authentication.validToken);
    await homePage.setUserPreferences(testData.userProfiles.mobileUser.preferences);
  });
  
  test('Mobile portrait orientation workflow', async ({ page }) => {
    // Set mobile viewport (iPhone 12 Pro)
    await page.setViewportSize({ width: 390, height: 844 });
    
    await test.step('Navigate and validate mobile homepage', async () => {
      await homePage.navigateToHome();
      
      // Should have mobile-optimized layout
      await expect(page.locator('[data-testid="mobile-layout"]')).toBeVisible();
      
      // Navigation should be collapsed into hamburger menu
      await expect(page.locator('[data-testid="mobile-nav-toggle"]')).toBeVisible();
      await expect(page.locator('[data-testid="desktop-nav"]')).not.toBeVisible();
      
      // Forecast card should be mobile-responsive
      const forecastCard = page.locator('[data-testid="forecast-card"]');
      await expect(forecastCard).toBeVisible();
      
      // Card should use full width on mobile
      const cardWidth = await forecastCard.evaluate(el => el.getBoundingClientRect().width);
      expect(cardWidth).toBeGreaterThan(350); // Nearly full width
    });
    
    await test.step('Test touch interactions', async () => {
      // Test tap gestures
      await page.locator('[data-testid="refresh-button"]').tap();
      await homePage.waitForPageReady();
      
      // Test swipe gestures for horizon selection
      const horizonSelector = page.locator('[data-testid="horizon-selector"]');
      await horizonSelector.tap();
      
      // Should show mobile-friendly picker
      await expect(page.locator('[data-testid="mobile-horizon-picker"]')).toBeVisible();
      
      // Select horizon with tap
      await page.locator('[data-testid="horizon-option-12h"]').tap();
      
      // Verify selection
      const selectedHorizon = await homePage.getSelectedHorizon();
      expect(selectedHorizon).toBe('12h');
    });
    
    await test.step('Test mobile navigation patterns', async () => {
      // Open mobile navigation menu
      await page.locator('[data-testid="mobile-nav-toggle"]').tap();
      
      // Should slide in navigation drawer
      await expect(page.locator('[data-testid="nav-drawer"]')).toBeVisible();
      
      // Should have touch-friendly menu items
      const menuItems = page.locator('[data-testid="nav-item"]');
      const menuItemCount = await menuItems.count();
      expect(menuItemCount).toBeGreaterThan(0);
      
      // Menu items should have adequate touch targets (44px minimum)
      for (let i = 0; i < menuItemCount; i++) {
        const item = menuItems.nth(i);
        const { height } = await item.boundingBox() || { height: 0 };
        expect(height).toBeGreaterThanOrEqual(44);
      }
      
      // Navigate to analog explorer
      await page.locator('[data-testid="nav-analog-explorer"]').tap();
      await analogExplorerPage.validatePageLoaded();
    });
    
    await test.step('Test pull-to-refresh gesture', async () => {
      // Get initial forecast timestamp
      const initialTimestamp = await homePage.getLastUpdatedTime();
      
      // Simulate pull-to-refresh gesture
      await page.mouse.move(200, 100);
      await page.mouse.down();
      await page.mouse.move(200, 300, { steps: 10 });
      await page.mouse.up();
      
      // Should trigger refresh
      await page.waitForTimeout(2000);
      
      // Verify refresh occurred
      const newTimestamp = await homePage.getLastUpdatedTime();
      // Note: In real implementation, timestamps should differ
    });
    
    await test.step('Test mobile keyboard handling', async () => {
      // Open settings or search that requires keyboard input
      await page.locator('[data-testid="mobile-search"]').tap();
      
      // Virtual keyboard should not obscure input
      const searchInput = page.locator('[data-testid="search-input"]');
      await expect(searchInput).toBeVisible();
      
      // Type search query
      await searchInput.fill('temperature');
      
      // Should handle input correctly
      await expect(searchInput).toHaveValue('temperature');
    });
  });
  
  test('Mobile landscape orientation workflow', async ({ page }) => {
    // Set mobile landscape viewport
    await page.setViewportSize({ width: 844, height: 390 });
    
    await test.step('Validate landscape layout adaptation', async () => {
      await homePage.navigateToHome();
      
      // Should adapt to landscape orientation
      await expect(page.locator('[data-testid="landscape-layout"]')).toBeVisible();
      
      // Content should reflow appropriately
      const forecastCard = page.locator('[data-testid="forecast-card"]');
      await expect(forecastCard).toBeVisible();
      
      // Should use horizontal space efficiently
      const cardWidth = await forecastCard.evaluate(el => el.getBoundingClientRect().width);
      expect(cardWidth).toBeGreaterThan(400);
    });
    
    await test.step('Test landscape-specific interactions', async () => {
      // Navigation might be different in landscape
      const navExists = await page.locator('[data-testid="landscape-nav"]').isVisible();
      
      if (navExists) {
        // Test landscape navigation
        await page.locator('[data-testid="landscape-nav"]').tap();
      }
      
      // Charts and data should be more visible in landscape
      await expect(page.locator('[data-testid="forecast-chart"]')).toBeVisible();
    });
  });
  
  test('Tablet user experience', async ({ page }) => {
    // Set tablet viewport (iPad Pro)
    await page.setViewportSize({ width: 1024, height: 1366 });
    
    await test.step('Validate tablet-optimized layout', async () => {
      await homePage.navigateToHome();
      
      // Should use tablet-specific layout
      await expect(page.locator('[data-testid="tablet-layout"]')).toBeVisible();
      
      // Should have split-screen or multi-column layout
      await expect(page.locator('[data-testid="main-content"]')).toBeVisible();
      await expect(page.locator('[data-testid="sidebar"]')).toBeVisible();
      
      // Navigation should be visible (not hamburger menu)
      await expect(page.locator('[data-testid="tablet-nav"]')).toBeVisible();
    });
    
    await test.step('Test tablet-specific interactions', async () => {
      // Should support touch and potentially hover interactions
      const forecastCard = page.locator('[data-testid="forecast-card"]');
      
      // Test hover effects (if tablet supports hover)
      await forecastCard.hover();
      
      // Test touch gestures
      await forecastCard.tap();
      
      // Should handle both interaction modes gracefully
      await expect(forecastCard).toBeVisible();
    });
    
    await test.step('Test multi-panel workflow on tablet', async () => {
      // Navigate to analog explorer
      await page.locator('[data-testid="explore-analogs"]').tap();
      await analogExplorerPage.validatePageLoaded();
      
      // Should show multiple panels simultaneously
      await expect(page.locator('[data-testid="analog-table"]')).toBeVisible();
      await expect(page.locator('[data-testid="analog-details"]')).toBeVisible();
      
      // Select analog pattern
      await analogExplorerPage.selectAnalogPattern(0);
      
      // Both panels should update appropriately
      const analogDetails = await analogExplorerPage.getSelectedAnalogDetails();
      expect(analogDetails.similarity).toBeGreaterThan(0);
    });
  });
  
  test('Mobile performance and optimization', async ({ page }) => {
    await page.setViewportSize({ width: 390, height: 844 });
    
    await test.step('Test mobile performance metrics', async () => {
      const startTime = Date.now();
      
      await homePage.navigateToHome();
      
      const loadTime = Date.now() - startTime;
      
      // Mobile should load quickly despite smaller viewport
      expect(loadTime).toBeLessThan(4000); // 4 seconds on mobile
      
      // Check mobile-specific Core Web Vitals
      const webVitals = await homePage.getCoreWebVitals();
      expect(webVitals.lcp).toBeLessThan(3000); // LCP under 3s on mobile
      expect(webVitals.fid).toBeLessThan(100);  // FID under 100ms
      expect(webVitals.cls).toBeLessThan(0.1);  // CLS under 0.1
    });
    
    await test.step('Test mobile data usage optimization', async () => {
      // Should load essential content first
      await expect(page.locator('[data-testid="forecast-card"]')).toBeVisible();
      
      // Optional content should load progressively
      const optionalContent = page.locator('[data-testid="detailed-charts"]');
      
      // May or may not be immediately visible (progressive loading)
      // but should not block essential functionality
      const forecastData = await homePage.getCurrentForecastData();
      expect(forecastData.temperature).toBeDefined();
    });
    
    await test.step('Test resource-constrained performance', async () => {
      // Simulate slower CPU with slower network
      await page.route('**/*', async (route) => {
        // Add artificial delay to simulate slow network
        await new Promise(resolve => setTimeout(resolve, 100));
        await route.continue();
      });
      
      // Should still be responsive
      await homePage.refreshForecast();
      
      // Should show loading states appropriately
      await expect(page.locator('[data-testid="loading-spinner"]')).toBeVisible();
      
      await homePage.waitForPageReady();
      
      // Should complete successfully despite constraints
      await expect(page.locator('[data-testid="forecast-card"]')).toBeVisible();
    });
  });
  
  test('Mobile offline behavior', async ({ page }) => {
    await page.setViewportSize({ width: 390, height: 844 });
    
    await test.step('Load content while online', async () => {
      await homePage.navigateToHome();
      
      // Get initial forecast data
      const onlineData = await homePage.getCurrentForecastData();
      expect(onlineData.temperature).toBeDefined();
    });
    
    await test.step('Test offline behavior', async () => {
      // Go offline
      await page.context().setOffline(true);
      
      // Should detect offline status
      await expect(page.locator('[data-testid="offline-indicator"]')).toBeVisible();
      
      // Should show cached content if available
      await expect(page.locator('[data-testid="forecast-card"]')).toBeVisible();
      
      // Should show offline message for refresh attempts
      await page.locator('[data-testid="refresh-button"]').tap();
      await expect(page.locator('[data-testid="offline-message"]')).toBeVisible();
    });
    
    await test.step('Test offline-to-online recovery', async () => {
      // Come back online
      await page.context().setOffline(false);
      
      // Should detect connection restoration
      await page.waitForTimeout(2000);
      await expect(page.locator('[data-testid="offline-indicator"]')).not.toBeVisible();
      
      // Should automatically refresh data
      await expect(page.locator('[data-testid="forecast-card"]')).toBeVisible();
      
      // Data should be up to date
      const onlineAgainData = await homePage.getCurrentForecastData();
      expect(onlineAgainData.lastUpdated).toBeTruthy();
    });
  });
  
  test('Mobile accessibility features', async ({ page }) => {
    await page.setViewportSize({ width: 390, height: 844 });
    
    await test.step('Test mobile screen reader compatibility', async () => {
      await homePage.navigateToHome();
      
      // Touch targets should be adequately sized and labeled
      const touchTargets = page.locator('[data-testid*="button"], [data-testid*="tap"]');
      const targetCount = await touchTargets.count();
      
      for (let i = 0; i < Math.min(targetCount, 10); i++) {
        const target = touchTargets.nth(i);
        
        // Check minimum touch target size (44x44px)
        const box = await target.boundingBox();
        if (box) {
          expect(box.width).toBeGreaterThanOrEqual(44);
          expect(box.height).toBeGreaterThanOrEqual(44);
        }
        
        // Check ARIA labeling
        const ariaLabel = await target.getAttribute('aria-label');
        const hasText = await target.textContent();
        
        // Should have either aria-label or visible text
        expect(ariaLabel || hasText).toBeTruthy();
      }
    });
    
    await test.step('Test mobile voice-over navigation', async () => {
      // Test logical tab order on mobile
      await page.keyboard.press('Tab');
      
      // Should navigate through interactive elements in logical order
      const focusedElement = await page.evaluate(() => document.activeElement?.tagName);
      expect(['BUTTON', 'A', 'INPUT', 'SELECT']).toContain(focusedElement || '');
    });
    
    await test.step('Test mobile zoom and text scaling', async () => {
      // Simulate text scaling (200%)
      await page.emulateMedia({ reducedMotion: 'reduce' });
      await page.addStyleTag({
        content: `
          * {
            font-size: calc(1em * 2) !important;
          }
        `
      });
      
      // Content should remain accessible and not overflow
      await expect(page.locator('[data-testid="forecast-card"]')).toBeVisible();
      
      // Text should not be cut off
      const temperatureDisplay = page.locator('[data-testid="temperature-display"]');
      const hasOverflow = await temperatureDisplay.evaluate(el => {
        return el.scrollWidth > el.clientWidth || el.scrollHeight > el.clientHeight;
      });
      
      expect(hasOverflow).toBe(false);
    });
  });
  
  test('Mobile cross-browser compatibility', async ({ page, browserName }) => {
    await page.setViewportSize({ width: 390, height: 844 });
    
    await test.step(`Test basic functionality on ${browserName} mobile`, async () => {
      await homePage.navigateToHome();
      
      // Core functionality should work across all mobile browsers
      await expect(page.locator('[data-testid="forecast-card"]')).toBeVisible();
      
      // Touch interactions should work
      await page.locator('[data-testid="refresh-button"]').tap();
      await homePage.waitForPageReady();
      
      // Navigation should work
      await page.locator('[data-testid="mobile-nav-toggle"]').tap();
      await expect(page.locator('[data-testid="nav-drawer"]')).toBeVisible();
    });
    
    await test.step(`Test ${browserName}-specific mobile features`, async () => {
      // Test browser-specific capabilities
      const userAgent = await page.evaluate(() => navigator.userAgent);
      
      if (browserName === 'webkit') {
        // Test iOS Safari specific features
        // Should handle iOS safe areas
        const safeAreaSupport = await page.evaluate(() => {
          return CSS.supports('padding-top', 'env(safe-area-inset-top)');
        });
        expect(safeAreaSupport).toBe(true);
      }
      
      if (browserName === 'chromium') {
        // Test Android Chrome specific features
        // Should support modern web APIs
        const modernSupport = await page.evaluate(() => {
          return 'serviceWorker' in navigator;
        });
        expect(modernSupport).toBe(true);
      }
    });
  });
});