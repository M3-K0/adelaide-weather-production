import '@testing-library/jest-dom';
import 'jest-axe/extend-expect';

// Mock environment variables for testing
process.env.API_TOKEN = 'test-secure-token';
process.env.API_BASE_URL = 'http://localhost:8000';

// Enhanced accessibility matchers
import { axe, toHaveNoViolations } from 'jest-axe';

expect.extend(toHaveNoViolations);

// Custom accessibility matchers
expect.extend({
  async toBeAccessible(element) {
    const results = await axe(element);
    const pass = results.violations.length === 0;
    
    if (pass) {
      return {
        message: () => 'Expected element to have accessibility violations',
        pass: true
      };
    } else {
      return {
        message: () => `Accessibility violations found:\n${
          results.violations.map(v => `${v.id}: ${v.description}`).join('\n')
        }`,
        pass: false
      };
    }
  },
  
  toHaveProperFocus(element) {
    const pass = element === document.activeElement;
    
    if (pass) {
      return {
        message: () => `Expected element not to have focus`,
        pass: true
      };
    } else {
      return {
        message: () => `Expected element to have focus, but focus is on ${document.activeElement?.tagName || 'null'}`,
        pass: false
      };
    }
  },
  
  toHaveVisibleFocusIndicator(element) {
    const styles = window.getComputedStyle(element);
    const hasOutline = styles.outline !== 'none' && styles.outline !== '';
    const hasBoxShadow = styles.boxShadow !== 'none' && styles.boxShadow !== '';
    const hasBorder = styles.border !== 'none' && styles.border !== '';
    
    const pass = hasOutline || hasBoxShadow || hasBorder;
    
    if (pass) {
      return {
        message: () => 'Expected element not to have visible focus indicator',
        pass: true
      };
    } else {
      return {
        message: () => 'Expected element to have visible focus indicator (outline, box-shadow, or border)',
        pass: false
      };
    }
  }
});

// Mock IntersectionObserver
global.IntersectionObserver = class IntersectionObserver {
  constructor() {}
  disconnect() {}
  observe() {}
  unobserve() {}
};

// Mock ResizeObserver
global.ResizeObserver = class ResizeObserver {
  constructor() {}
  disconnect() {}
  observe() {}
  unobserve() {}
};

// Mock matchMedia
Object.defineProperty(window, 'matchMedia', {
  writable: true,
  value: jest.fn().mockImplementation(query => ({
    matches: false,
    media: query,
    onchange: null,
    addListener: jest.fn(),
    removeListener: jest.fn(),
    addEventListener: jest.fn(),
    removeEventListener: jest.fn(),
    dispatchEvent: jest.fn()
  }))
});
