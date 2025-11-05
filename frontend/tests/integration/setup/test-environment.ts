/**
 * Integration Test Environment Setup
 * Configures the testing environment for component integration tests including
 * mocking, global utilities, and React Testing Library extensions.
 */

import '@testing-library/jest-dom';
import { configure } from '@testing-library/react';
import { enableMapSet } from 'immer';
import { server } from '@mocks/api-mocks';

// Configure React Testing Library
configure({
  testIdAttribute: 'data-testid',
  computedStyleSupportsPseudoElements: false,
  asyncUtilTimeout: 5000,
  defaultHidden: false
});

// Enable Immer MapSet support for state management
enableMapSet();

// Global test utilities
declare global {
  namespace jest {
    interface Matchers<R> {
      toBeAccessible(): R;
      toHaveValidMetrics(): R;
      toSynchronizeWith(element: HTMLElement): R;
    }
  }
}

// Custom Jest matchers for integration testing
expect.extend({
  toBeAccessible(received: HTMLElement) {
    const hasAriaLabel = received.hasAttribute('aria-label') || 
                        received.hasAttribute('aria-labelledby') ||
                        received.hasAttribute('aria-describedby');
    const hasRole = received.hasAttribute('role');
    const hasValidTabIndex = !received.hasAttribute('tabindex') || 
                            parseInt(received.getAttribute('tabindex') || '0') >= -1;

    const pass = hasAriaLabel && hasRole && hasValidTabIndex;

    return {
      message: () => pass 
        ? `Expected element not to be accessible`
        : `Expected element to be accessible (missing aria-label/role/valid tabindex)`,
      pass
    };
  },

  toHaveValidMetrics(received: any) {
    const hasRequiredMetrics = received && 
                              typeof received.trackInteraction === 'function' &&
                              typeof received.trackCapeModal === 'function';

    return {
      message: () => hasRequiredMetrics
        ? `Expected metrics object not to be valid`
        : `Expected metrics object to have required tracking methods`,
      pass: hasRequiredMetrics
    };
  },

  toSynchronizeWith(received: HTMLElement, target: HTMLElement) {
    // Check if elements are properly synchronized by comparing data attributes
    const receivedState = received.getAttribute('data-sync-state');
    const targetState = target.getAttribute('data-sync-state');
    const pass = receivedState === targetState && receivedState !== null;

    return {
      message: () => pass
        ? `Expected elements not to be synchronized`
        : `Expected elements to be synchronized (states: ${receivedState} vs ${targetState})`,
      pass
    };
  }
});

// Mock window.matchMedia for responsive component testing
Object.defineProperty(window, 'matchMedia', {
  writable: true,
  value: jest.fn().mockImplementation(query => ({
    matches: false,
    media: query,
    onchange: null,
    addListener: jest.fn(), // Deprecated
    removeListener: jest.fn(), // Deprecated
    addEventListener: jest.fn(),
    removeEventListener: jest.fn(),
    dispatchEvent: jest.fn(),
  })),
});

// Mock IntersectionObserver for lazy loading components
global.IntersectionObserver = class IntersectionObserver {
  constructor(
    public callback: IntersectionObserverCallback,
    public options?: IntersectionObserverInit
  ) {}

  observe() {
    return null;
  }

  disconnect() {
    return null;
  }

  unobserve() {
    return null;
  }
};

// Mock ResizeObserver for responsive components
global.ResizeObserver = class ResizeObserver {
  constructor(public callback: ResizeObserverCallback) {}

  observe() {
    return null;
  }

  disconnect() {
    return null;
  }

  unobserve() {
    return null;
  }
};

// Mock localStorage for persistence testing
const localStorageMock = {
  getItem: jest.fn(),
  setItem: jest.fn(),
  removeItem: jest.fn(),
  clear: jest.fn(),
};
global.localStorage = localStorageMock as any;

// Mock sessionStorage for session persistence testing
const sessionStorageMock = {
  getItem: jest.fn(),
  setItem: jest.fn(),
  removeItem: jest.fn(),
  clear: jest.fn(),
};
global.sessionStorage = sessionStorageMock as any;

// Mock URL.createObjectURL for file download testing
global.URL.createObjectURL = jest.fn(() => 'mocked-url');
global.URL.revokeObjectURL = jest.fn();

// Mock HTMLElement methods used by components
HTMLElement.prototype.scrollIntoView = jest.fn();
HTMLElement.prototype.focus = jest.fn();

// Mock canvas context for chart components
HTMLCanvasElement.prototype.getContext = jest.fn(() => ({
  fillRect: jest.fn(),
  clearRect: jest.fn(),
  getImageData: jest.fn(() => ({ data: new Array(4) })),
  putImageData: jest.fn(),
  createImageData: jest.fn(() => []),
  setTransform: jest.fn(),
  drawImage: jest.fn(),
  save: jest.fn(),
  fillText: jest.fn(),
  restore: jest.fn(),
  beginPath: jest.fn(),
  moveTo: jest.fn(),
  lineTo: jest.fn(),
  closePath: jest.fn(),
  stroke: jest.fn(),
  translate: jest.fn(),
  scale: jest.fn(),
  rotate: jest.fn(),
  arc: jest.fn(),
  fill: jest.fn(),
  measureText: jest.fn(() => ({ width: 0 })),
  transform: jest.fn(),
  rect: jest.fn(),
  clip: jest.fn(),
})) as any;

// Console override for cleaner test output
const originalConsoleError = console.error;
console.error = (...args: any[]) => {
  // Filter out known React warnings during testing
  if (
    typeof args[0] === 'string' &&
    (args[0].includes('Warning: ReactDOM.render is no longer supported') ||
     args[0].includes('Warning: React.createFactory() is deprecated') ||
     args[0].includes('Warning: componentWillReceiveProps has been renamed'))
  ) {
    return;
  }
  originalConsoleError.call(console, ...args);
};

// Setup MSW server for API mocking
beforeAll(() => {
  server.listen({
    onUnhandledRequest: 'error'
  });
});

afterEach(() => {
  server.resetHandlers();
  // Clear all mocks between tests
  jest.clearAllMocks();
  localStorageMock.clear();
  sessionStorageMock.clear();
});

afterAll(() => {
  server.close();
  console.error = originalConsoleError;
});

// Global test utilities
export const waitForLoadingToComplete = async () => {
  const { waitFor } = await import('@testing-library/react');
  await waitFor(() => {
    expect(document.querySelector('[data-testid="loading"]')).not.toBeInTheDocument();
  }, { timeout: 10000 });
};

export const mockMetricsProvider = () => ({
  trackInteraction: jest.fn(),
  trackCapeModal: jest.fn(),
  trackAnalogToggle: jest.fn(),
  trackDetailsToggle: jest.fn(),
  trackExport: jest.fn(),
  trackRefresh: jest.fn(),
  updatePerformance: jest.fn(),
  getMetrics: jest.fn(() => ({
    interactions: 0,
    performance: { loadTime: 100, renderTime: 50 }
  }))
});

export const mockAccessibilityProvider = () => ({
  announceToScreenReader: jest.fn(),
  setFocusManagement: jest.fn(),
  getAccessibilityStatus: jest.fn(() => ({
    screenReaderActive: false,
    highContrast: false,
    reducedMotion: false
  }))
});

// Integration test helpers
export const createIntegrationTestId = (component: string, element?: string) => {
  return element ? `${component}-${element}-integration` : `${component}-integration`;
};

export const getByIntegrationTestId = (component: string, element?: string) => {
  return document.querySelector(`[data-testid="${createIntegrationTestId(component, element)}"]`);
};