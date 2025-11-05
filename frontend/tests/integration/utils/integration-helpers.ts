/**
 * Integration Test Utilities and Helpers
 * Comprehensive utilities for testing component interactions, state synchronization,
 * and complex integration scenarios across the weather forecasting application.
 */

import React from 'react';
import { render, RenderOptions, screen, waitFor, fireEvent } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { mockMetricsProvider, mockAccessibilityProvider } from '@integration/setup/test-environment';
import { MockStateManager } from '@mocks/api-mocks';
import type { ForecastHorizon, WeatherVariable } from '@/types/api';

// ============================================================================
// Test Providers and Wrappers
// ============================================================================

interface TestProvidersProps {
  children: React.ReactNode;
  queryClient?: QueryClient;
  metricsProvider?: any;
  accessibilityProvider?: any;
  initialState?: Record<string, any>;
}

export const TestProviders: React.FC<TestProvidersProps> = ({
  children,
  queryClient = new QueryClient({
    defaultOptions: {
      queries: { retry: false, cacheTime: 0 },
      mutations: { retry: false }
    }
  }),
  metricsProvider = mockMetricsProvider(),
  accessibilityProvider = mockAccessibilityProvider(),
  initialState = {}
}) => {
  // Set initial state in mock state manager
  React.useEffect(() => {
    Object.entries(initialState).forEach(([key, value]) => {
      MockStateManager.setState(key, value);
    });
  }, [initialState]);

  return (
    <QueryClientProvider client={queryClient}>
      <div 
        data-testid="test-providers"
        data-metrics-provider={JSON.stringify(Object.keys(metricsProvider))}
        data-a11y-provider={JSON.stringify(Object.keys(accessibilityProvider))}
      >
        {children}
      </div>
    </QueryClientProvider>
  );
};

// ============================================================================
// Enhanced Render Function
// ============================================================================

interface IntegrationRenderOptions extends RenderOptions {
  queryClient?: QueryClient;
  metricsProvider?: any;
  accessibilityProvider?: any;
  initialState?: Record<string, any>;
  withProviders?: boolean;
}

export const renderWithIntegration = (
  ui: React.ReactElement,
  options: IntegrationRenderOptions = {}
) => {
  const {
    queryClient,
    metricsProvider,
    accessibilityProvider,
    initialState,
    withProviders = true,
    ...renderOptions
  } = options;

  const Wrapper: React.FC<{ children: React.ReactNode }> = ({ children }) => {
    if (!withProviders) return <>{children}</>;
    
    return (
      <TestProviders
        queryClient={queryClient}
        metricsProvider={metricsProvider}
        accessibilityProvider={accessibilityProvider}
        initialState={initialState}
      >
        {children}
      </TestProviders>
    );
  };

  return {
    user: userEvent.setup(),
    ...render(ui, { wrapper: Wrapper, ...renderOptions })
  };
};

// ============================================================================
// Component Integration Helpers
// ============================================================================

/**
 * Verifies that two components are properly synchronized
 */
export const expectComponentsSynchronized = async (
  component1Selector: string,
  component2Selector: string,
  syncAttribute: string = 'data-sync-state'
) => {
  const component1 = await screen.findByTestId(component1Selector);
  const component2 = await screen.findByTestId(component2Selector);
  
  expect(component1).toBeInTheDocument();
  expect(component2).toBeInTheDocument();
  
  const state1 = component1.getAttribute(syncAttribute);
  const state2 = component2.getAttribute(syncAttribute);
  
  expect(state1).toBeTruthy();
  expect(state2).toBeTruthy();
  expect(state1).toBe(state2);
};

/**
 * Verifies that metrics are being tracked correctly across components
 */
export const expectMetricsTracked = (
  metricsProvider: any,
  expectedCalls: Array<{ method: string; args: any[] }>
) => {
  expectedCalls.forEach(({ method, args }) => {
    expect(metricsProvider[method]).toHaveBeenCalledWith(...args);
  });
};

/**
 * Verifies accessibility features are properly integrated
 */
export const expectAccessibilityIntegrated = async (
  component: HTMLElement,
  accessibilityProvider: any
) => {
  expect(component).toBeAccessible();
  expect(accessibilityProvider.getAccessibilityStatus).toHaveBeenCalled();
};

/**
 * Tests data flow between components
 */
export const testDataFlow = async (
  sourceComponent: string,
  targetComponent: string,
  triggerAction: () => Promise<void> | void,
  expectedChanges: Record<string, any>
) => {
  const source = screen.getByTestId(sourceComponent);
  const target = screen.getByTestId(targetComponent);
  
  // Capture initial state
  const initialTargetState = Object.keys(expectedChanges).reduce((acc, key) => ({
    ...acc,
    [key]: target.getAttribute(`data-${key}`)
  }), {});
  
  // Trigger the action
  await triggerAction();
  
  // Wait for changes to propagate
  await waitFor(() => {
    Object.entries(expectedChanges).forEach(([key, expectedValue]) => {
      const currentValue = target.getAttribute(`data-${key}`);
      expect(currentValue).toBe(expectedValue);
      expect(currentValue).not.toBe(initialTargetState[key]);
    });
  });
};

// ============================================================================
// Real-time Synchronization Helpers
// ============================================================================

/**
 * Simulates real-time updates and verifies component synchronization
 */
export const simulateRealTimeUpdate = async (
  updateType: 'status' | 'metrics' | 'forecast',
  newData: any,
  expectedComponents: string[]
) => {
  // Update mock state
  MockStateManager.setState(`realtime_${updateType}`, newData);
  
  // Trigger update event
  window.dispatchEvent(new CustomEvent('realtime-update', {
    detail: { type: updateType, data: newData }
  }));
  
  // Verify all expected components update
  await waitFor(() => {
    expectedComponents.forEach(componentTestId => {
      const component = screen.getByTestId(componentTestId);
      expect(component.getAttribute('data-last-update')).toBeTruthy();
    });
  });
};

/**
 * Tests WebSocket-like real-time synchronization
 */
export const testRealTimeSynchronization = async (
  components: string[],
  updateData: any,
  syncAttribute: string = 'data-sync-timestamp'
) => {
  const initialTimestamps = components.map(componentId => {
    const component = screen.getByTestId(componentId);
    return component.getAttribute(syncAttribute);
  });
  
  // Simulate real-time update
  await simulateRealTimeUpdate('status', updateData, components);
  
  // Verify all components updated with same timestamp
  await waitFor(() => {
    const newTimestamps = components.map(componentId => {
      const component = screen.getByTestId(componentId);
      return component.getAttribute(syncAttribute);
    });
    
    // All timestamps should be the same (synchronized)
    const uniqueTimestamps = [...new Set(newTimestamps)];
    expect(uniqueTimestamps).toHaveLength(1);
    
    // All timestamps should be different from initial
    newTimestamps.forEach((timestamp, index) => {
      expect(timestamp).not.toBe(initialTimestamps[index]);
    });
  });
};

// ============================================================================
// Error Handling Integration Helpers
// ============================================================================

/**
 * Tests error propagation between components
 */
export const testErrorPropagation = async (
  sourceComponent: string,
  expectedErrorComponents: string[],
  triggerError: () => Promise<void> | void
) => {
  await triggerError();
  
  await waitFor(() => {
    expectedErrorComponents.forEach(componentId => {
      const component = screen.getByTestId(componentId);
      expect(component.getAttribute('data-error-state')).toBe('true');
    });
  });
};

/**
 * Tests error boundary integration
 */
export const testErrorBoundaryIntegration = async (
  errorBoundaryTestId: string,
  componentToError: string,
  triggerError: () => void
) => {
  const errorBoundary = screen.getByTestId(errorBoundaryTestId);
  const component = screen.getByTestId(componentToError);
  
  expect(errorBoundary.getAttribute('data-has-error')).toBe('false');
  expect(component).toBeInTheDocument();
  
  triggerError();
  
  await waitFor(() => {
    expect(errorBoundary.getAttribute('data-has-error')).toBe('true');
    expect(screen.queryByTestId(componentToError)).not.toBeInTheDocument();
  });
};

// ============================================================================
// Performance Integration Helpers
// ============================================================================

/**
 * Measures component interaction performance
 */
export const measureInteractionPerformance = async (
  interaction: () => Promise<void> | void,
  expectedMaxDuration: number = 1000
): Promise<number> => {
  const startTime = performance.now();
  await interaction();
  const endTime = performance.now();
  
  const duration = endTime - startTime;
  expect(duration).toBeLessThan(expectedMaxDuration);
  
  return duration;
};

/**
 * Tests memory leak prevention in component interactions
 */
export const testMemoryLeakPrevention = async (
  componentTestId: string,
  mountUnmountCycles: number = 10
) => {
  const initialMemory = (performance as any).memory?.usedJSHeapSize || 0;
  
  for (let i = 0; i < mountUnmountCycles; i++) {
    const { unmount } = renderWithIntegration(
      <div data-testid={componentTestId}>Test Component {i}</div>
    );
    unmount();
  }
  
  // Force garbage collection if available
  if ((global as any).gc) {
    (global as any).gc();
  }
  
  await new Promise(resolve => setTimeout(resolve, 100));
  
  const finalMemory = (performance as any).memory?.usedJSHeapSize || 0;
  const memoryGrowth = finalMemory - initialMemory;
  
  // Memory growth should be minimal (less than 1MB per cycle)
  expect(memoryGrowth).toBeLessThan(mountUnmountCycles * 1024 * 1024);
};

// ============================================================================
// State Management Integration Helpers
// ============================================================================

/**
 * Tests cross-component state synchronization
 */
export const testCrossComponentState = async (
  stateKey: string,
  newValue: any,
  expectedComponents: string[]
) => {
  // Update state
  MockStateManager.setState(stateKey, newValue);
  
  // Trigger state change event
  window.dispatchEvent(new CustomEvent('state-change', {
    detail: { key: stateKey, value: newValue }
  }));
  
  // Verify all components reflect the new state
  await waitFor(() => {
    expectedComponents.forEach(componentId => {
      const component = screen.getByTestId(componentId);
      const componentState = component.getAttribute(`data-${stateKey}`);
      expect(componentState).toBe(String(newValue));
    });
  });
};

/**
 * Tests state persistence across browser sessions
 */
export const testStatePersistence = async (
  stateKey: string,
  value: any,
  storageType: 'localStorage' | 'sessionStorage' = 'localStorage'
) => {
  const storage = storageType === 'localStorage' ? localStorage : sessionStorage;
  
  // Set state
  MockStateManager.setState(stateKey, value);
  
  // Verify storage is called
  expect(storage.setItem).toHaveBeenCalledWith(
    expect.stringContaining(stateKey),
    expect.any(String)
  );
  
  // Clear state and restore from storage
  MockStateManager.clearState();
  
  // Mock storage retrieval
  (storage.getItem as jest.Mock).mockReturnValue(JSON.stringify(value));
  
  // Trigger restore
  window.dispatchEvent(new CustomEvent('storage-restore'));
  
  await waitFor(() => {
    expect(MockStateManager.getState(stateKey)).toEqual(value);
  });
};

// ============================================================================
// API Integration Helpers
// ============================================================================

/**
 * Tests API call coordination between components
 */
export const testApiCallCoordination = async (
  triggerComponent: string,
  dependentComponents: string[],
  apiEndpoint: string,
  action: () => Promise<void> | void
) => {
  const triggerElement = screen.getByTestId(triggerComponent);
  
  // Mark dependent components as waiting
  dependentComponents.forEach(componentId => {
    const component = screen.getByTestId(componentId);
    component.setAttribute('data-api-state', 'waiting');
  });
  
  await action();
  
  // Verify all dependent components update after API call
  await waitFor(() => {
    dependentComponents.forEach(componentId => {
      const component = screen.getByTestId(componentId);
      expect(component.getAttribute('data-api-state')).toBe('loaded');
    });
  });
};

/**
 * Tests loading state coordination
 */
export const testLoadingStateCoordination = async (
  components: string[],
  triggerLoading: () => Promise<void>
) => {
  // Verify initial state
  components.forEach(componentId => {
    const component = screen.getByTestId(componentId);
    expect(component.getAttribute('data-loading')).toBe('false');
  });
  
  const loadingPromise = triggerLoading();
  
  // Verify loading state
  await waitFor(() => {
    components.forEach(componentId => {
      const component = screen.getByTestId(componentId);
      expect(component.getAttribute('data-loading')).toBe('true');
    });
  });
  
  await loadingPromise;
  
  // Verify loading complete
  await waitFor(() => {
    components.forEach(componentId => {
      const component = screen.getByTestId(componentId);
      expect(component.getAttribute('data-loading')).toBe('false');
    });
  });
};

// ============================================================================
// Export Utilities
// ============================================================================

export const integrationTestUtils = {
  // Rendering
  renderWithIntegration,
  TestProviders,
  
  // Component synchronization
  expectComponentsSynchronized,
  expectMetricsTracked,
  expectAccessibilityIntegrated,
  testDataFlow,
  
  // Real-time features
  simulateRealTimeUpdate,
  testRealTimeSynchronization,
  
  // Error handling
  testErrorPropagation,
  testErrorBoundaryIntegration,
  
  // Performance
  measureInteractionPerformance,
  testMemoryLeakPrevention,
  
  // State management
  testCrossComponentState,
  testStatePersistence,
  
  // API integration
  testApiCallCoordination,
  testLoadingStateCoordination
};