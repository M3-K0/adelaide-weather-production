/**
 * AccessibilityProvider Component
 * 
 * Provides comprehensive accessibility state management and utilities
 * for the Adelaide Weather Forecasting System
 * 
 * Features:
 * - Centralized focus management
 * - Live region announcements
 * - Keyboard navigation state
 * - Screen reader utilities
 * - ARIA live region coordination
 * - High contrast mode detection
 * - Reduced motion preference handling
 */

import React, {
  createContext,
  useContext,
  useState,
  useEffect,
  useRef,
  useCallback,
  ReactNode
} from 'react';

// Accessibility Context Types
interface AccessibilityState {
  // Focus management
  lastFocusedElement: HTMLElement | null;
  focusStack: HTMLElement[];
  isKeyboardUser: boolean;
  
  // Live announcements
  announcements: string[];
  lastAnnouncement: string | null;
  
  // User preferences
  prefersReducedMotion: boolean;
  prefersHighContrast: boolean;
  colorScheme: 'light' | 'dark' | 'auto';
  
  // Navigation state
  currentPage: string;
  breadcrumbs: string[];
  
  // Screen reader specific
  screenReaderActive: boolean;
  
  // Error announcements
  errorQueue: Array<{
    id: string;
    message: string;
    severity: 'error' | 'warning' | 'info';
    timestamp: number;
  }>;
}

interface AccessibilityActions {
  // Focus management
  saveFocus: (element?: HTMLElement) => void;
  restoreFocus: () => void;
  trapFocus: (container: HTMLElement) => () => void;
  setKeyboardUser: (isKeyboard: boolean) => void;
  
  // Live announcements
  announce: (message: string, priority?: 'polite' | 'assertive') => void;
  announceError: (message: string, severity?: 'error' | 'warning' | 'info') => void;
  clearAnnouncements: () => void;
  
  // Navigation
  setCurrentPage: (page: string) => void;
  addBreadcrumb: (crumb: string) => void;
  clearBreadcrumbs: () => void;
  
  // Skip links
  addSkipLink: (target: string, label: string) => void;
  removeSkipLink: (target: string) => void;
  
  // Utility functions
  isElementVisible: (element: HTMLElement) => boolean;
  getFocusableElements: (container: HTMLElement) => HTMLElement[];
  getAriaLabel: (element: HTMLElement) => string | null;
}

interface AccessibilityContextType extends AccessibilityState, AccessibilityActions {}

interface AccessibilityProviderProps {
  children: ReactNode;
  options?: {
    enableAnnouncements?: boolean;
    enableFocusManagement?: boolean;
    enableKeyboardDetection?: boolean;
    announcementDelay?: number;
  };
}

// Default options
const defaultOptions = {
  enableAnnouncements: true,
  enableFocusManagement: true,
  enableKeyboardDetection: true,
  announcementDelay: 1000
};

// Create context
const AccessibilityContext = createContext<AccessibilityContextType | null>(null);

// Custom hook to use accessibility context
export const useAccessibility = (): AccessibilityContextType => {
  const context = useContext(AccessibilityContext);
  if (!context) {
    throw new Error('useAccessibility must be used within an AccessibilityProvider');
  }
  return context;
};

// Skip link management
interface SkipLink {
  target: string;
  label: string;
}

// Main AccessibilityProvider component
export const AccessibilityProvider: React.FC<AccessibilityProviderProps> = ({
  children,
  options = {}
}) => {
  const config = { ...defaultOptions, ...options };
  
  // Live region refs
  const politeRef = useRef<HTMLDivElement>(null);
  const assertiveRef = useRef<HTMLDivElement>(null);
  
  // State management
  const [state, setState] = useState<AccessibilityState>({
    lastFocusedElement: null,
    focusStack: [],
    isKeyboardUser: false,
    announcements: [],
    lastAnnouncement: null,
    prefersReducedMotion: false,
    prefersHighContrast: false,
    colorScheme: 'auto',
    currentPage: '',
    breadcrumbs: [],
    screenReaderActive: false,
    errorQueue: []
  });
  
  // Skip links state
  const [skipLinks, setSkipLinks] = useState<SkipLink[]>([]);
  
  // Detect user preferences
  useEffect(() => {
    const motionQuery = window.matchMedia('(prefers-reduced-motion: reduce)');
    const contrastQuery = window.matchMedia('(prefers-contrast: high)');
    const colorQuery = window.matchMedia('(prefers-color-scheme: dark)');
    
    const updatePreferences = () => {
      setState(prev => ({
        ...prev,
        prefersReducedMotion: motionQuery.matches,
        prefersHighContrast: contrastQuery.matches,
        colorScheme: colorQuery.matches ? 'dark' : 'light'
      }));
    };
    
    updatePreferences();
    
    motionQuery.addEventListener('change', updatePreferences);
    contrastQuery.addEventListener('change', updatePreferences);
    colorQuery.addEventListener('change', updatePreferences);
    
    return () => {
      motionQuery.removeEventListener('change', updatePreferences);
      contrastQuery.removeEventListener('change', updatePreferences);
      colorQuery.removeEventListener('change', updatePreferences);
    };
  }, []);
  
  // Detect screen reader usage
  useEffect(() => {
    // Check for common screen reader indicators
    const checkScreenReader = () => {
      const hasAriaLive = document.querySelector('[aria-live]');
      const hasScreenReaderClass = document.documentElement.classList.contains('sr-only');
      const userAgent = navigator.userAgent.toLowerCase();
      const hasScreenReaderUA = userAgent.includes('nvda') || userAgent.includes('jaws') || userAgent.includes('voiceover');
      
      setState(prev => ({
        ...prev,
        screenReaderActive: !!(hasAriaLive || hasScreenReaderClass || hasScreenReaderUA)
      }));
    };
    
    checkScreenReader();
    
    // Listen for focus events that might indicate screen reader usage
    const focusHandler = (e: FocusEvent) => {
      if (e.target && (e.target as HTMLElement).hasAttribute('aria-describedby')) {
        setState(prev => ({ ...prev, screenReaderActive: true }));
      }
    };
    
    document.addEventListener('focusin', focusHandler);
    return () => document.removeEventListener('focusin', focusHandler);
  }, []);
  
  // Keyboard user detection
  useEffect(() => {
    if (!config.enableKeyboardDetection) return;
    
    const handleKeyDown = (e: KeyboardEvent) => {
      if (e.key === 'Tab') {
        setState(prev => ({ ...prev, isKeyboardUser: true }));
      }
    };
    
    const handleMouseDown = () => {
      setState(prev => ({ ...prev, isKeyboardUser: false }));
    };
    
    document.addEventListener('keydown', handleKeyDown);
    document.addEventListener('mousedown', handleMouseDown);
    
    return () => {
      document.removeEventListener('keydown', handleKeyDown);
      document.removeEventListener('mousedown', handleMouseDown);
    };
  }, [config.enableKeyboardDetection]);
  
  // Focus management actions
  const saveFocus = useCallback((element?: HTMLElement) => {
    const elementToSave = element || (document.activeElement as HTMLElement);
    if (elementToSave && elementToSave !== document.body) {
      setState(prev => ({
        ...prev,
        lastFocusedElement: elementToSave,
        focusStack: [...prev.focusStack, elementToSave]
      }));
    }
  }, []);
  
  const restoreFocus = useCallback(() => {
    const { lastFocusedElement, focusStack } = state;
    
    if (focusStack.length > 0) {
      const elementToFocus = focusStack[focusStack.length - 1];
      if (elementToFocus && document.contains(elementToFocus)) {
        elementToFocus.focus();
      }
      setState(prev => ({
        ...prev,
        focusStack: prev.focusStack.slice(0, -1)
      }));
    } else if (lastFocusedElement && document.contains(lastFocusedElement)) {
      lastFocusedElement.focus();
    }
  }, [state]);
  
  const trapFocus = useCallback((container: HTMLElement) => {
    const focusableElements = getFocusableElements(container);
    if (focusableElements.length === 0) return () => {};
    
    const firstElement = focusableElements[0];
    const lastElement = focusableElements[focusableElements.length - 1];
    
    const handleKeyDown = (e: KeyboardEvent) => {
      if (e.key !== 'Tab') return;
      
      if (e.shiftKey) {
        if (document.activeElement === firstElement) {
          e.preventDefault();
          lastElement.focus();
        }
      } else {
        if (document.activeElement === lastElement) {
          e.preventDefault();
          firstElement.focus();
        }
      }
    };
    
    container.addEventListener('keydown', handleKeyDown);
    
    // Focus first element
    firstElement.focus();
    
    return () => {
      container.removeEventListener('keydown', handleKeyDown);
    };
  }, []);
  
  // Announcement actions
  const announce = useCallback((message: string, priority: 'polite' | 'assertive' = 'polite') => {
    if (!config.enableAnnouncements || !message.trim()) return;
    
    const targetRef = priority === 'assertive' ? assertiveRef : politeRef;
    
    if (targetRef.current) {
      // Clear previous announcement
      targetRef.current.textContent = '';
      
      // Add slight delay to ensure screen readers notice the change
      setTimeout(() => {
        if (targetRef.current) {
          targetRef.current.textContent = message;
        }
      }, 100);
      
      setState(prev => ({
        ...prev,
        announcements: [...prev.announcements, message],
        lastAnnouncement: message
      }));
      
      // Clear announcement after delay
      setTimeout(() => {
        if (targetRef.current) {
          targetRef.current.textContent = '';
        }
      }, config.announcementDelay);
    }
  }, [config.enableAnnouncements, config.announcementDelay]);
  
  const announceError = useCallback((message: string, severity: 'error' | 'warning' | 'info' = 'error') => {
    const errorId = `error-${Date.now()}-${Math.random().toString(36).substr(2, 9)}`;
    const timestamp = Date.now();
    
    setState(prev => ({
      ...prev,
      errorQueue: [...prev.errorQueue, { id: errorId, message, severity, timestamp }]
    }));
    
    // Announce with appropriate priority
    const priority = severity === 'error' ? 'assertive' : 'polite';
    announce(`${severity.toUpperCase()}: ${message}`, priority);
    
    // Auto-remove error after 10 seconds
    setTimeout(() => {
      setState(prev => ({
        ...prev,
        errorQueue: prev.errorQueue.filter(error => error.id !== errorId)
      }));
    }, 10000);
  }, [announce]);
  
  const clearAnnouncements = useCallback(() => {
    setState(prev => ({
      ...prev,
      announcements: [],
      lastAnnouncement: null
    }));
    
    if (politeRef.current) politeRef.current.textContent = '';
    if (assertiveRef.current) assertiveRef.current.textContent = '';
  }, []);
  
  // Navigation actions
  const setCurrentPage = useCallback((page: string) => {
    setState(prev => ({ ...prev, currentPage: page }));
    announce(`Navigated to ${page}`, 'polite');
  }, [announce]);
  
  const addBreadcrumb = useCallback((crumb: string) => {
    setState(prev => ({
      ...prev,
      breadcrumbs: [...prev.breadcrumbs, crumb]
    }));
  }, []);
  
  const clearBreadcrumbs = useCallback(() => {
    setState(prev => ({ ...prev, breadcrumbs: [] }));
  }, []);
  
  // Skip link management
  const addSkipLink = useCallback((target: string, label: string) => {
    setSkipLinks(prev => {
      const exists = prev.find(link => link.target === target);
      if (exists) return prev;
      return [...prev, { target, label }];
    });
  }, []);
  
  const removeSkipLink = useCallback((target: string) => {
    setSkipLinks(prev => prev.filter(link => link.target !== target));
  }, []);
  
  // Utility functions
  const isElementVisible = useCallback((element: HTMLElement): boolean => {
    const rect = element.getBoundingClientRect();
    const style = window.getComputedStyle(element);
    
    return (
      rect.width > 0 &&
      rect.height > 0 &&
      style.visibility !== 'hidden' &&
      style.display !== 'none' &&
      style.opacity !== '0'
    );
  }, []);
  
  const getFocusableElements = useCallback((container: HTMLElement): HTMLElement[] => {
    const focusableSelectors = [
      'a[href]',
      'button:not([disabled])',
      'input:not([disabled])',
      'select:not([disabled])',
      'textarea:not([disabled])',
      '[tabindex]:not([tabindex="-1"])',
      '[contenteditable="true"]'
    ].join(', ');
    
    const elements = Array.from(container.querySelectorAll<HTMLElement>(focusableSelectors));
    return elements.filter(el => isElementVisible(el));
  }, [isElementVisible]);
  
  const getAriaLabel = useCallback((element: HTMLElement): string | null => {
    return (
      element.getAttribute('aria-label') ||
      element.getAttribute('aria-labelledby') ||
      element.getAttribute('title') ||
      (element as HTMLInputElement).placeholder ||
      element.textContent?.trim() ||
      null
    );
  }, []);
  
  const setKeyboardUser = useCallback((isKeyboard: boolean) => {
    setState(prev => ({ ...prev, isKeyboardUser: isKeyboard }));
  }, []);
  
  // Context value
  const contextValue: AccessibilityContextType = {
    ...state,
    saveFocus,
    restoreFocus,
    trapFocus,
    setKeyboardUser,
    announce,
    announceError,
    clearAnnouncements,
    setCurrentPage,
    addBreadcrumb,
    clearBreadcrumbs,
    addSkipLink,
    removeSkipLink,
    isElementVisible,
    getFocusableElements,
    getAriaLabel
  };
  
  return (
    <AccessibilityContext.Provider value={contextValue}>
      {/* Skip Links */}
      {skipLinks.length > 0 && (
        <div className="skip-links fixed top-0 left-0 z-50">
          {skipLinks.map(({ target, label }) => (
            <a
              key={target}
              href={`#${target}`}
              className="sr-only focus:not-sr-only focus:absolute focus:top-2 focus:left-2 bg-white text-black px-4 py-2 rounded shadow-lg font-medium z-50"
              onFocus={() => announce(`Skip link: ${label}`, 'polite')}
            >
              {label}
            </a>
          ))}
        </div>
      )}
      
      {/* Live Regions */}
      <div aria-live="polite" aria-atomic="true" className="sr-only" ref={politeRef} />
      <div aria-live="assertive" aria-atomic="true" className="sr-only" ref={assertiveRef} />
      
      {/* Error Queue Display for Screen Readers */}
      {state.errorQueue.length > 0 && (
        <div className="sr-only" role="log" aria-label="Error messages">
          {state.errorQueue.map(error => (
            <div key={error.id} role="alert">
              {error.severity.toUpperCase()}: {error.message}
            </div>
          ))}
        </div>
      )}
      
      {children}
    </AccessibilityContext.Provider>
  );
};

// Utility hook for skip link management
export const useSkipLinks = () => {
  const { addSkipLink, removeSkipLink } = useAccessibility();
  
  useEffect(() => {
    // Add default skip links
    addSkipLink('main-content', 'Skip to main content');
    addSkipLink('navigation', 'Skip to navigation');
    
    return () => {
      removeSkipLink('main-content');
      removeSkipLink('navigation');
    };
  }, [addSkipLink, removeSkipLink]);
};

// Utility hook for focus management in modals
export const useFocusTrap = (isOpen: boolean, containerRef: React.RefObject<HTMLElement>) => {
  const { trapFocus, saveFocus, restoreFocus } = useAccessibility();
  
  useEffect(() => {
    if (!isOpen || !containerRef.current) return;
    
    saveFocus();
    const releaseTrap = trapFocus(containerRef.current);
    
    return () => {
      releaseTrap();
      restoreFocus();
    };
  }, [isOpen, containerRef, trapFocus, saveFocus, restoreFocus]);
};

// Utility hook for live announcements
export const useAnnounce = () => {
  const { announce, announceError } = useAccessibility();
  
  return {
    announce,
    announceError,
    announceSuccess: (message: string) => announce(`Success: ${message}`, 'polite'),
    announceNavigation: (page: string) => announce(`Navigated to ${page}`, 'polite'),
    announceDataUpdate: (data: string) => announce(`${data} updated`, 'polite')
  };
};

export default AccessibilityProvider;