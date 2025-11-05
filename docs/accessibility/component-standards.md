# Component Accessibility Standards
# Adelaide Weather Forecasting System

**Document Version:** 1.0  
**Date:** October 29, 2024  
**Scope:** Component-level accessibility implementation standards and guidelines  

## Overview

This document establishes comprehensive accessibility standards for all components in the Adelaide Weather Forecasting System. These standards ensure WCAG 2.1 AA compliance and provide excellent user experience for all users, including those using assistive technologies.

## Core Accessibility Principles

### 1. Universal Design
- Components must be usable by the widest range of users without requiring specialized versions
- Functionality must be accessible through multiple interaction methods (mouse, keyboard, touch, voice)
- Information must be perceivable through multiple senses

### 2. Progressive Enhancement
- Core functionality must work without JavaScript
- Enhanced interactions should be additive
- Graceful degradation for assistive technologies

### 3. Semantic First
- Use semantic HTML elements before adding ARIA
- Ensure logical document structure and reading order
- Provide clear relationships between related elements

## AccessibilityProvider Integration

All components should integrate with the AccessibilityProvider for centralized accessibility management:

```tsx
import { useAccessibility, useAnnounce, useFocusTrap } from '@/components/AccessibilityProvider';

const MyComponent = () => {
  const { announce, isKeyboardUser } = useAccessibility();
  const { announceSuccess, announceError } = useAnnounce();
  
  // Component implementation
};
```

## Component Standards by Type

### 1. Interactive Components (Buttons, Links, Controls)

#### Required Implementation
```tsx
// Standard button implementation
const AccessibleButton = ({ 
  children, 
  onClick, 
  disabled = false, 
  variant = 'primary',
  ariaLabel,
  ariaDescribedBy,
  ...props 
}) => {
  const { announce } = useAccessibility();
  
  const handleClick = (e) => {
    onClick?.(e);
    if (ariaLabel) {
      announce(`${ariaLabel} activated`, 'polite');
    }
  };
  
  return (
    <button
      onClick={handleClick}
      disabled={disabled}
      aria-label={ariaLabel}
      aria-describedby={ariaDescribedBy}
      className={`
        focus:outline-none focus:ring-2 focus:ring-cyan-500 focus:ring-offset-2
        disabled:opacity-50 disabled:cursor-not-allowed
        transition-colors duration-200
        ${getVariantClasses(variant)}
      `}
      {...props}
    >
      {children}
    </button>
  );
};
```

#### Standards Checklist
- [ ] Proper focus indicators (`focus:ring-2 focus:ring-cyan-500`)
- [ ] Disabled state handling with appropriate attributes
- [ ] ARIA labels for context when text content isn't descriptive
- [ ] Keyboard event handling (Enter, Space)
- [ ] Sufficient color contrast (4.5:1 minimum)
- [ ] Touch target size minimum 44px
- [ ] Screen reader feedback for state changes

### 2. Form Components

#### Required Implementation
```tsx
const AccessibleInput = ({ 
  label, 
  id, 
  error, 
  required = false, 
  helpText,
  ...props 
}) => {
  const helpTextId = helpText ? `${id}-help` : undefined;
  const errorId = error ? `${id}-error` : undefined;
  const describedBy = [helpTextId, errorId].filter(Boolean).join(' ') || undefined;
  
  return (
    <div className="form-group">
      <label 
        htmlFor={id} 
        className="block text-sm font-medium text-slate-300 mb-1"
      >
        {label}
        {required && (
          <span className="text-red-400 ml-1" aria-label="required">*</span>
        )}
      </label>
      
      <input
        id={id}
        required={required}
        aria-invalid={error ? 'true' : 'false'}
        aria-describedby={describedBy}
        className={`
          w-full px-3 py-2 border rounded-md
          focus:outline-none focus:ring-2 focus:ring-cyan-500 focus:border-cyan-500
          ${error ? 'border-red-500' : 'border-slate-600'}
          bg-slate-800 text-slate-100
        `}
        {...props}
      />
      
      {helpText && (
        <div id={helpTextId} className="text-xs text-slate-400 mt-1">
          {helpText}
        </div>
      )}
      
      {error && (
        <div id={errorId} className="text-xs text-red-400 mt-1" role="alert">
          {error}
        </div>
      )}
    </div>
  );
};
```

#### Standards Checklist
- [ ] Explicit label association using `htmlFor` and `id`
- [ ] Required field indication with both visual and screen reader cues
- [ ] Error state communication with `aria-invalid` and `role="alert"`
- [ ] Help text association using `aria-describedby`
- [ ] Focus management and visual indicators
- [ ] Validation feedback announcements

### 3. Data Display Components

#### Required Implementation
```tsx
const AccessibleDataCard = ({ 
  title, 
  data, 
  trend, 
  confidence, 
  lastUpdated,
  ariaLabel 
}) => {
  const { announce } = useAccessibility();
  
  useEffect(() => {
    if (data.updated) {
      announce(`${title} updated to ${data.value}`, 'polite');
    }
  }, [data.updated, data.value, title, announce]);
  
  return (
    <article
      className="bg-slate-800 border border-slate-700 rounded-lg p-6 focus:outline-none focus:ring-2 focus:ring-cyan-500"
      tabIndex={0}
      role="article"
      aria-label={ariaLabel || `${title}: ${data.value} ${data.unit}, ${confidence}% confidence`}
    >
      <header className="flex justify-between items-start mb-4">
        <h3 className="text-lg font-medium text-slate-100">{title}</h3>
        <div className="text-xs text-slate-400" aria-label={`Last updated ${lastUpdated}`}>
          {lastUpdated}
        </div>
      </header>
      
      <div className="space-y-3">
        <div className="flex items-baseline gap-2">
          <span 
            className="text-3xl font-light text-slate-50"
            aria-label={`Value: ${data.value} ${data.unit}`}
          >
            {data.value}
          </span>
          <span className="text-lg text-slate-400">{data.unit}</span>
        </div>
        
        {trend && (
          <div className="flex items-center gap-2">
            <TrendIcon trend={trend} aria-hidden="true" />
            <span className="text-sm text-slate-300">
              Trending {trend}
            </span>
          </div>
        )}
        
        <div className="text-sm text-slate-400">
          Confidence: {confidence}%
        </div>
      </div>
      
      {/* Live region for updates */}
      <div aria-live="polite" aria-atomic="true" className="sr-only">
        {data.updated && `${title} updated to ${data.value} ${data.unit}`}
      </div>
    </article>
  );
};
```

#### Standards Checklist
- [ ] Semantic article structure with proper headings
- [ ] Comprehensive ARIA labels for complex information
- [ ] Live regions for dynamic content updates
- [ ] Focus management for card interactions
- [ ] Clear information hierarchy
- [ ] Time and date formatting with accessible labels

### 4. Navigation Components

#### Required Implementation
```tsx
const AccessibleNavigation = ({ items, currentPage }) => {
  const { setCurrentPage, addBreadcrumb } = useAccessibility();
  
  const handleNavigation = (item) => {
    setCurrentPage(item.label);
    addBreadcrumb(item.label);
  };
  
  return (
    <nav aria-label="Main navigation" role="navigation">
      <ul className="space-y-1">
        {items.map((item) => (
          <li key={item.id}>
            <button
              onClick={() => handleNavigation(item)}
              className={`
                w-full flex items-center gap-3 px-3 py-2 rounded-lg text-left
                transition-colors duration-200
                focus:outline-none focus:ring-2 focus:ring-cyan-500
                ${currentPage === item.id 
                  ? 'bg-slate-700 text-slate-100' 
                  : 'text-slate-400 hover:text-slate-200 hover:bg-slate-800'
                }
              `}
              aria-current={currentPage === item.id ? 'page' : undefined}
            >
              <item.icon size={18} aria-hidden="true" />
              <span>{item.label}</span>
            </button>
          </li>
        ))}
      </ul>
    </nav>
  );
};
```

#### Standards Checklist
- [ ] Semantic navigation structure with `nav` and `role="navigation"`
- [ ] Current page indication with `aria-current="page"`
- [ ] Descriptive `aria-label` for navigation context
- [ ] Keyboard navigation support
- [ ] Focus indicators for all interactive elements
- [ ] Screen reader announcements for navigation changes

### 5. Modal and Dialog Components

#### Required Implementation
```tsx
const AccessibleModal = ({ 
  isOpen, 
  onClose, 
  title, 
  children, 
  className = '' 
}) => {
  const modalRef = useRef<HTMLDivElement>(null);
  const { announce } = useAccessibility();
  
  // Use focus trap hook
  useFocusTrap(isOpen, modalRef);
  
  useEffect(() => {
    if (isOpen) {
      announce(`Dialog opened: ${title}`, 'polite');
    }
  }, [isOpen, title, announce]);
  
  const handleKeyDown = (e: KeyboardEvent) => {
    if (e.key === 'Escape') {
      onClose();
      announce('Dialog closed', 'polite');
    }
  };
  
  if (!isOpen) return null;
  
  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center">
      {/* Backdrop */}
      <div 
        className="absolute inset-0 bg-black/80" 
        onClick={onClose}
        aria-hidden="true"
      />
      
      {/* Modal */}
      <div
        ref={modalRef}
        role="dialog"
        aria-modal="true"
        aria-labelledby="modal-title"
        tabIndex={-1}
        onKeyDown={handleKeyDown}
        className={`
          relative bg-slate-800 rounded-lg shadow-xl max-w-md w-full mx-4
          focus:outline-none
          ${className}
        `}
      >
        <header className="flex items-center justify-between p-6 border-b border-slate-700">
          <h2 id="modal-title" className="text-lg font-semibold text-slate-100">
            {title}
          </h2>
          <button
            onClick={onClose}
            className="p-2 rounded-lg hover:bg-slate-700 focus:outline-none focus:ring-2 focus:ring-cyan-500"
            aria-label="Close dialog"
          >
            <X size={20} aria-hidden="true" />
          </button>
        </header>
        
        <div className="p-6">
          {children}
        </div>
      </div>
    </div>
  );
};
```

#### Standards Checklist
- [ ] Proper modal ARIA attributes (`role="dialog"`, `aria-modal="true"`)
- [ ] Focus management with trap and restoration
- [ ] Escape key handling for dismissal
- [ ] Descriptive title with `aria-labelledby`
- [ ] Backdrop click handling (optional)
- [ ] Screen reader announcements for open/close
- [ ] Accessible close button with proper labeling

### 6. Chart and Visualization Components

#### Required Implementation
```tsx
const AccessibleChart = ({ 
  data, 
  title, 
  description, 
  type = 'line' 
}) => {
  const chartId = useId();
  const summaryId = `${chartId}-summary`;
  const tableId = `${chartId}-table`;
  
  return (
    <div className="space-y-4">
      {/* Chart title and description */}
      <div>
        <h3 id={chartId} className="text-lg font-medium text-slate-100">
          {title}
        </h3>
        <p id={summaryId} className="text-sm text-slate-400">
          {description}
        </p>
      </div>
      
      {/* Visual chart */}
      <div className="relative">
        <ResponsiveContainer 
          width="100%" 
          height={300}
          role="img"
          aria-labelledby={chartId}
          aria-describedby={summaryId}
        >
          <LineChart data={data}>
            <CartesianGrid strokeDasharray="3 3" stroke="#374151" />
            <XAxis 
              stroke="#94a3b8" 
              fontSize={12}
              tick={{ fill: '#94a3b8' }}
            />
            <YAxis 
              stroke="#94a3b8" 
              fontSize={12}
              tick={{ fill: '#94a3b8' }}
            />
            <Tooltip
              contentStyle={{
                backgroundColor: '#1e293b',
                border: '1px solid #475569',
                borderRadius: '4px',
                color: '#e2e8f0'
              }}
            />
            <Line
              type="monotone"
              dataKey="value"
              stroke="#22d3ee"
              strokeWidth={2}
              dot={{ fill: '#22d3ee', strokeWidth: 2, r: 4 }}
            />
          </LineChart>
        </ResponsiveContainer>
      </div>
      
      {/* Data table for screen readers */}
      <details className="mt-4">
        <summary className="cursor-pointer text-sm text-cyan-400 hover:text-cyan-300">
          View data table
        </summary>
        <table 
          id={tableId}
          className="mt-2 w-full text-sm border border-slate-700"
          aria-label={`Data table for ${title}`}
        >
          <caption className="sr-only">
            {title} - {description}
          </caption>
          <thead>
            <tr className="bg-slate-800">
              <th className="border border-slate-700 px-3 py-2 text-left">Time</th>
              <th className="border border-slate-700 px-3 py-2 text-left">Value</th>
            </tr>
          </thead>
          <tbody>
            {data.map((point, index) => (
              <tr key={index} className="even:bg-slate-900">
                <td className="border border-slate-700 px-3 py-2">{point.time}</td>
                <td className="border border-slate-700 px-3 py-2">{point.value}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </details>
    </div>
  );
};
```

#### Standards Checklist
- [ ] Alternative text through `role="img"` and ARIA labels
- [ ] Data table alternative for screen readers
- [ ] Proper heading structure and descriptions
- [ ] High contrast colors for chart elements
- [ ] Accessible tooltip implementation
- [ ] Collapsible data table with clear labeling

## Testing Standards

### 1. Automated Testing
Each component must include accessibility tests:

```tsx
// Component.test.tsx
import { render, screen } from '@testing-library/react';
import { axe, toHaveNoViolations } from 'jest-axe';
import userEvent from '@testing-library/user-event';
import { AccessibilityProvider } from '@/components/AccessibilityProvider';

expect.extend(toHaveNoViolations);

const renderWithAccessibility = (component) => {
  return render(
    <AccessibilityProvider>
      {component}
    </AccessibilityProvider>
  );
};

describe('Component Accessibility', () => {
  test('should not have accessibility violations', async () => {
    const { container } = renderWithAccessibility(<MyComponent />);
    const results = await axe(container);
    expect(results).toHaveNoViolations();
  });

  test('should be keyboard navigable', async () => {
    const user = userEvent.setup();
    renderWithAccessibility(<MyComponent />);
    
    // Test keyboard navigation
    await user.tab();
    expect(screen.getByRole('button')).toHaveFocus();
    
    await user.keyboard('{Enter}');
    // Verify expected behavior
  });

  test('should have proper ARIA attributes', () => {
    renderWithAccessibility(<MyComponent />);
    
    const element = screen.getByRole('button');
    expect(element).toHaveAttribute('aria-label');
    expect(element).toHaveAttribute('aria-describedby');
  });

  test('should announce changes to screen readers', async () => {
    const { rerender } = renderWithAccessibility(<MyComponent data={initialData} />);
    
    rerender(
      <AccessibilityProvider>
        <MyComponent data={updatedData} />
      </AccessibilityProvider>
    );
    
    expect(screen.getByRole('status')).toBeInTheDocument();
  });
});
```

### 2. Manual Testing Checklist
For each component:

#### Keyboard Navigation
- [ ] All interactive elements reachable via Tab
- [ ] Tab order follows logical sequence
- [ ] Shift+Tab moves backward correctly
- [ ] Enter/Space activates appropriate elements
- [ ] Arrow keys work for complex widgets
- [ ] Escape closes modals/dropdowns
- [ ] Focus indicators clearly visible

#### Screen Reader Testing
- [ ] Content structure announced correctly
- [ ] Interactive elements have clear names
- [ ] State changes announced appropriately
- [ ] Complex content has alternative text
- [ ] Navigation landmarks identified
- [ ] Form relationships clear

#### Visual Accessibility
- [ ] Text contrast meets 4.5:1 ratio minimum
- [ ] Interactive elements meet 3:1 contrast
- [ ] Information not conveyed by color alone
- [ ] Content readable at 200% zoom
- [ ] Focus indicators visible in high contrast

## Implementation Guidelines

### 1. Progressive Enhancement Approach
```tsx
// Base semantic HTML
const BaseComponent = () => (
  <button onClick={handleClick}>
    {label}
  </button>
);

// Enhanced with accessibility features
const EnhancedComponent = () => (
  <button
    onClick={handleClick}
    aria-label={ariaLabel}
    aria-describedby={helpTextId}
    className="focus:ring-2 focus:ring-cyan-500"
  >
    {label}
  </button>
);
```

### 2. Error Handling
```tsx
const ErrorBoundaryComponent = ({ error, children }) => {
  const { announceError } = useAnnounce();
  
  useEffect(() => {
    if (error) {
      announceError(error.message, 'error');
    }
  }, [error, announceError]);
  
  if (error) {
    return (
      <div role="alert" className="error-boundary">
        <h2>Something went wrong</h2>
        <p>{error.message}</p>
        <button onClick={() => window.location.reload()}>
          Reload page
        </button>
      </div>
    );
  }
  
  return children;
};
```

### 3. Loading States
```tsx
const LoadingComponent = ({ isLoading, children }) => {
  const { announce } = useAccessibility();
  
  useEffect(() => {
    if (isLoading) {
      announce('Loading content', 'polite');
    }
  }, [isLoading, announce]);
  
  if (isLoading) {
    return (
      <div 
        role="status" 
        aria-label="Loading content"
        className="animate-pulse"
      >
        <span className="sr-only">Loading...</span>
        {/* Visual loading indicator */}
      </div>
    );
  }
  
  return children;
};
```

## Code Review Checklist

Before merging any component code, ensure:

### Accessibility Requirements
- [ ] Component follows semantic HTML patterns
- [ ] ARIA attributes used appropriately (not redundantly)
- [ ] Focus management implemented correctly
- [ ] Keyboard navigation works as expected
- [ ] Screen reader testing completed
- [ ] Color contrast verified
- [ ] Error states accessible
- [ ] Loading states announced

### Integration Requirements
- [ ] AccessibilityProvider hooks used where applicable
- [ ] Live announcements implemented for dynamic content
- [ ] Focus traps implemented for modals
- [ ] Skip links added where appropriate
- [ ] Testing includes accessibility tests
- [ ] Documentation updated

### Performance Considerations
- [ ] No unnecessary re-renders from accessibility hooks
- [ ] ARIA labels generated efficiently
- [ ] Event listeners cleaned up properly
- [ ] Focus management doesn't impact performance

## Conclusion

These component standards ensure that the Adelaide Weather Forecasting System provides an excellent user experience for all users, including those using assistive technologies. By following these standards consistently, we maintain WCAG 2.1 AA compliance while providing a robust, accessible interface that serves our diverse user base effectively.

Regular review and updating of these standards ensures we stay current with accessibility best practices and continue to provide inclusive design patterns for our weather forecasting system.