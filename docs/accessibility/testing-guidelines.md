# Accessibility Testing Guidelines
# Adelaide Weather Forecasting System

**Document Version:** 1.0  
**Date:** October 29, 2024  
**Scope:** Comprehensive accessibility testing procedures  

## Overview

This document establishes comprehensive accessibility testing procedures for the Adelaide Weather Forecasting System. All development team members must follow these testing guidelines to ensure WCAG 2.1 AA compliance and excellent accessibility.

## Testing Strategy

### Multi-Layered Approach
1. **Automated Testing**: Continuous integration with accessibility linting and testing
2. **Manual Testing**: Systematic keyboard and screen reader testing
3. **User Testing**: Real-world testing with assistive technology users
4. **Continuous Monitoring**: Ongoing accessibility validation

### Testing Frequency
- **Pre-commit**: Automated linting and basic checks
- **Pull Request**: Comprehensive automated testing
- **Sprint Review**: Manual testing of new features
- **Release**: Full accessibility audit and user testing
- **Quarterly**: Complete system accessibility review

## Automated Testing

### ESLint Configuration

**Setup jsx-a11y Plugin**
```json
// .eslintrc.json
{
  "extends": [
    "next/core-web-vitals",
    "plugin:jsx-a11y/recommended"
  ],
  "plugins": ["jsx-a11y"],
  "rules": {
    // Enforce strict accessibility rules
    "jsx-a11y/alt-text": "error",
    "jsx-a11y/anchor-has-content": "error",
    "jsx-a11y/anchor-is-valid": "error",
    "jsx-a11y/aria-props": "error",
    "jsx-a11y/aria-proptypes": "error",
    "jsx-a11y/aria-role": "error",
    "jsx-a11y/aria-unsupported-elements": "error",
    "jsx-a11y/click-events-have-key-events": "error",
    "jsx-a11y/heading-has-content": "error",
    "jsx-a11y/iframe-has-title": "error",
    "jsx-a11y/img-redundant-alt": "error",
    "jsx-a11y/interactive-supports-focus": "error",
    "jsx-a11y/label-has-associated-control": "error",
    "jsx-a11y/media-has-caption": "error",
    "jsx-a11y/mouse-events-have-key-events": "error",
    "jsx-a11y/no-access-key": "error",
    "jsx-a11y/no-autofocus": "error",
    "jsx-a11y/no-distracting-elements": "error",
    "jsx-a11y/no-interactive-element-to-noninteractive-role": "error",
    "jsx-a11y/no-noninteractive-element-interactions": "error",
    "jsx-a11y/no-noninteractive-element-to-interactive-role": "error",
    "jsx-a11y/no-noninteractive-tabindex": "error",
    "jsx-a11y/no-redundant-roles": "error",
    "jsx-a11y/no-static-element-interactions": "error",
    "jsx-a11y/role-has-required-aria-props": "error",
    "jsx-a11y/role-supports-aria-props": "error",
    "jsx-a11y/scope": "error",
    "jsx-a11y/tabindex-no-positive": "error"
  }
}
```

### Jest/Testing Library Setup

**Accessibility Matchers**
```typescript
// jest.setup.js
import '@testing-library/jest-dom';
import 'jest-axe/extend-expect';

// Custom accessibility matchers
expect.extend({
  toBeAccessible: async (element) => {
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
  }
});
```

**Component Testing Example**
```typescript
// __tests__/components/ForecastCard.accessibility.test.tsx
import { render, screen } from '@testing-library/react';
import { axe, toHaveNoViolations } from 'jest-axe';
import userEvent from '@testing-library/user-event';
import { ForecastCard } from '@/components/ForecastCard';
import { mockForecastData } from '@/types/mock-data';

expect.extend(toHaveNoViolations);

describe('ForecastCard Accessibility', () => {
  test('should not have accessibility violations', async () => {
    const { container } = render(
      <ForecastCard forecast={mockForecastData.forecast6h} />
    );
    
    const results = await axe(container);
    expect(results).toHaveNoViolations();
  });

  test('should be keyboard navigable', async () => {
    const user = userEvent.setup();
    render(<ForecastCard forecast={mockForecastData.forecast6h} />);
    
    const card = screen.getByRole('article');
    
    // Tab to card
    await user.tab();
    expect(card).toHaveFocus();
    
    // Enter should activate card
    await user.keyboard('{Enter}');
    // Verify expected behavior
  });

  test('should have proper ARIA attributes', () => {
    render(<ForecastCard forecast={mockForecastData.forecast6h} />);
    
    const card = screen.getByRole('article');
    expect(card).toHaveAttribute('aria-label');
    expect(card.getAttribute('aria-label')).toContain('Forecast for');
  });

  test('should announce updates to screen readers', async () => {
    const { rerender } = render(
      <ForecastCard forecast={mockForecastData.forecast6h} />
    );
    
    // Update forecast data
    const updatedForecast = {
      ...mockForecastData.forecast6h,
      variables: {
        ...mockForecastData.forecast6h.variables,
        t2m: { ...mockForecastData.forecast6h.variables.t2m, value: 25.5 }
      }
    };
    
    rerender(<ForecastCard forecast={updatedForecast} />);
    
    // Check for live region updates
    const liveRegion = screen.getByRole('status', { hidden: true });
    expect(liveRegion).toBeInTheDocument();
  });
});
```

### Playwright Integration

**Axe-core Integration**
```typescript
// playwright.config.ts
import { defineConfig } from '@playwright/test';

export default defineConfig({
  use: {
    // Enable accessibility testing
    baseURL: 'http://localhost:3000',
  },
});
```

**E2E Accessibility Tests**
```typescript
// tests/accessibility.spec.ts
import { test, expect } from '@playwright/test';
import AxeBuilder from '@axe-core/playwright';

test.describe('Accessibility Tests', () => {
  test('homepage should not have accessibility violations', async ({ page }) => {
    await page.goto('/');
    
    const accessibilityScanResults = await new AxeBuilder({ page })
      .withTags(['wcag2a', 'wcag2aa', 'wcag21aa'])
      .analyze();
    
    expect(accessibilityScanResults.violations).toEqual([]);
  });

  test('forecast cards should be keyboard accessible', async ({ page }) => {
    await page.goto('/');
    
    // Navigate using keyboard
    await page.keyboard.press('Tab');
    await page.keyboard.press('Tab');
    
    // Should reach first forecast card
    const focusedElement = await page.locator(':focus');
    await expect(focusedElement).toHaveAttribute('role', 'article');
  });

  test('modal dialogs should trap focus', async ({ page }) => {
    await page.goto('/');
    
    // Open CAPE badge modal
    await page.click('[data-testid="cape-badge"]');
    
    // Modal should be open and focused
    const modal = page.locator('[role="dialog"]');
    await expect(modal).toBeVisible();
    await expect(modal).toBeFocused();
    
    // Tab should cycle within modal
    await page.keyboard.press('Tab');
    const focusedElement = await page.locator(':focus');
    const modalBounds = await modal.boundingBox();
    const focusedBounds = await focusedElement.boundingBox();
    
    // Focused element should be within modal bounds
    expect(focusedBounds.x).toBeGreaterThanOrEqual(modalBounds.x);
    expect(focusedBounds.y).toBeGreaterThanOrEqual(modalBounds.y);
  });
});
```

## Manual Testing

### Keyboard Navigation Testing

**Keyboard Testing Checklist**
- [ ] All interactive elements reachable via Tab
- [ ] Tab order follows logical sequence
- [ ] Shift+Tab moves backward through elements
- [ ] Enter/Space activates buttons and links
- [ ] Arrow keys navigate within complex widgets
- [ ] Escape closes dialogs and dismisses menus
- [ ] Home/End keys work in appropriate contexts
- [ ] Focus indicators clearly visible
- [ ] No keyboard traps (except modals)
- [ ] Skip links function correctly

**Testing Procedure**
```bash
# 1. Disconnect mouse/trackpad
# 2. Use only keyboard for navigation
# 3. Test complete user workflows:

# Homepage navigation
Tab → Skip to main content
Tab → Navigation items
Tab → Forecast cards
Enter → Activate forecast card interactions

# Modal interactions
Tab → CAPE badge
Enter → Open modal
Tab → Navigate modal content
Escape → Close modal

# Form interactions
Tab → Variable selector
Space/Enter → Open dropdown
Arrow keys → Navigate options
Enter → Select option
Tab → Next form element
```

### Screen Reader Testing

**Screen Reader Tools**
- **NVDA** (Windows - free): Primary testing tool
- **JAWS** (Windows - commercial): Secondary testing
- **VoiceOver** (macOS - built-in): macOS testing
- **Orca** (Linux - free): Linux testing

**Screen Reader Testing Process**

1. **Initial Setup**
```bash
# NVDA shortcuts
NVDA + Space → Pass through mode
NVDA + F7 → Elements list
NVDA + T → Read title
NVDA + H → Navigate headings
NVDA + K → Navigate links
NVDA + B → Navigate buttons
NVDA + F → Navigate form fields
```

2. **Content Structure Testing**
```bash
# Test heading navigation
NVDA + H → Should announce proper heading levels
1, 2, 3, 4 → Jump to heading levels

# Test landmark navigation
NVDA + D → Navigate landmarks
Should announce: banner, navigation, main, complementary

# Test form structure
NVDA + F → Navigate form fields
Should announce: labels, required fields, error messages
```

3. **Interactive Element Testing**
```bash
# Button interaction
Tab to button → Should announce button name and role
Enter → Should announce action result

# Link interaction
Tab to link → Should announce link text and destination
Enter → Should navigate or announce action

# Complex widgets
Tab to slider → Should announce current value and range
Arrow keys → Should announce value changes
```

**Screen Reader Testing Checklist**
- [ ] Page title announced correctly
- [ ] Heading structure navigable
- [ ] Landmarks properly identified
- [ ] Form labels associated with inputs
- [ ] Error messages announced
- [ ] Dynamic content updates announced
- [ ] Button purposes clear
- [ ] Link destinations described
- [ ] Table structure understandable
- [ ] Lists properly structured

### Visual Accessibility Testing

**Color Contrast Testing**

Tools:
- WebAIM Contrast Checker
- Colour Contrast Analyser (CCA)
- Browser DevTools accessibility panel

Testing Process:
```bash
# Test all text/background combinations
1. Identify all text elements
2. Use color picker to get exact colors
3. Check contrast ratio in WebAIM tool
4. Verify 4.5:1 ratio for normal text
5. Verify 3:1 ratio for large text (18pt+ or 14pt+ bold)
6. Document any failures for remediation
```

**Color Blindness Testing**

Simulation Tools:
- Stark (Figma/Sketch plugin)
- Colorblinding.com
- Chrome DevTools Vision Deficiencies

Testing Types:
- Protanopia (red-blind)
- Deuteranopia (green-blind)
- Tritanopia (blue-blind)
- Monochromacy (total color blindness)

**High Contrast Mode Testing**

Windows High Contrast:
```bash
# Enable Windows High Contrast
Left Alt + Left Shift + Print Screen

# Test all interface elements
1. Text remains readable
2. Interactive elements visible
3. Focus indicators clear
4. Icons and graphics visible
```

## User Testing

### Assistive Technology User Testing

**Recruitment Criteria**
- Screen reader users (NVDA, JAWS, VoiceOver)
- Keyboard-only users
- Voice control users
- Users with low vision
- Users with cognitive disabilities

**Testing Protocol**

1. **Pre-test Setup**
```bash
# Environment preparation
- Familiar testing device
- Preferred assistive technology
- Comfortable testing environment
- Recording equipment (with consent)
```

2. **Task-Based Testing**
```bash
# Core user journeys
Task 1: Navigate to current weather forecast
Task 2: Check 24-hour forecast details
Task 3: Compare different forecast horizons
Task 4: Access system status information
Task 5: Use CAPE analysis features
Task 6: Export forecast data
```

3. **Think-Aloud Protocol**
- Encourage participants to verbalize thoughts
- Note points of confusion or frustration
- Identify where users deviate from expected paths
- Record successful strategies and workarounds

**Data Collection**
- Task completion rates
- Time to completion
- Error rates
- User satisfaction scores
- Qualitative feedback
- Specific accessibility barriers

### Testing Metrics

**Quantitative Metrics**
- Task completion rate: >90%
- Average task completion time
- Error recovery rate: >95%
- User satisfaction score: >4.0/5.0

**Qualitative Metrics**
- Ease of navigation
- Information clarity
- Interface predictability
- Error message helpfulness
- Overall accessibility experience

## Continuous Monitoring

### Automated Monitoring

**CI/CD Pipeline Integration**
```yaml
# .github/workflows/accessibility.yml
name: Accessibility Testing

on: [push, pull_request]

jobs:
  accessibility:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v2
      - uses: actions/setup-node@v2
        with:
          node-version: '18'
      
      - name: Install dependencies
        run: npm ci
      
      - name: Run accessibility linting
        run: npm run lint:a11y
      
      - name: Run accessibility tests
        run: npm run test:a11y
      
      - name: Build and test with Lighthouse
        run: |
          npm run build
          npm run start &
          npx wait-on http://localhost:3000
          npx lighthouse-ci autorun
```

**Lighthouse CI Configuration**
```json
// lighthouserc.json
{
  "ci": {
    "collect": {
      "url": ["http://localhost:3000"],
      "numberOfRuns": 3
    },
    "assert": {
      "assertions": {
        "categories:accessibility": ["error", {"minScore": 0.9}],
        "categories:best-practices": ["error", {"minScore": 0.9}]
      }
    }
  }
}
```

### Performance Monitoring

**Real-Time Monitoring**
```typescript
// Monitor accessibility performance
const AccessibilityMonitor = () => {
  useEffect(() => {
    // Monitor focus management
    const focusHandler = (e) => {
      if (!e.target.matches(':focus-visible')) {
        console.warn('Focus not visible on', e.target);
      }
    };
    
    document.addEventListener('focusin', focusHandler);
    return () => document.removeEventListener('focusin', focusHandler);
  }, []);
  
  // Monitor ARIA live region updates
  useEffect(() => {
    const observer = new MutationObserver((mutations) => {
      mutations.forEach((mutation) => {
        if (mutation.target.hasAttribute('aria-live')) {
          console.log('Live region updated:', mutation.target);
        }
      });
    });
    
    observer.observe(document.body, {
      subtree: true,
      childList: true,
      characterData: true
    });
    
    return () => observer.disconnect();
  }, []);
};
```

## Testing Tools and Resources

### Development Tools
- **ESLint jsx-a11y**: Accessibility linting
- **axe-core**: Automated accessibility testing
- **@testing-library/react**: Accessible testing utilities
- **jest-axe**: Jest integration for axe-core

### Manual Testing Tools
- **NVDA**: Free screen reader (Windows)
- **VoiceOver**: Built-in screen reader (macOS)
- **Chrome DevTools**: Accessibility panel
- **WebAIM WAVE**: Web accessibility evaluation
- **Color Oracle**: Color blindness simulator

### Browser Extensions
- **axe DevTools**: Accessibility testing in browser
- **WAVE**: Web accessibility evaluation
- **Lighthouse**: Performance and accessibility auditing
- **Accessibility Insights**: Microsoft accessibility testing

## Reporting and Documentation

### Test Results Documentation

**Test Report Template**
```markdown
# Accessibility Test Report

## Test Information
- Date: [Date]
- Tester: [Name]
- Testing Method: [Automated/Manual/User Testing]
- Scope: [Components/Pages tested]

## Summary
- Total Issues Found: [Number]
- Critical Issues: [Number]
- Moderate Issues: [Number]
- Minor Issues: [Number]

## Detailed Findings
### Issue 1: [Title]
- **Severity**: Critical/Moderate/Minor
- **WCAG Guideline**: [Guideline number and description]
- **Location**: [Component/Page]
- **Description**: [Detailed description]
- **Impact**: [User impact description]
- **Recommendation**: [Fix recommendation]
- **Status**: Open/In Progress/Fixed
```

### Issue Tracking

**GitHub Issue Template**
```markdown
---
name: Accessibility Issue
about: Report an accessibility barrier or WCAG violation
labels: accessibility, bug
---

## Accessibility Issue Description
Brief description of the accessibility issue

## WCAG Guideline
Which WCAG 2.1 guideline(s) are violated:
- [ ] 1.1.1 Non-text Content
- [ ] 1.4.3 Contrast (Minimum)
- [ ] 2.1.1 Keyboard
- [ ] 2.4.1 Bypass Blocks
- [Add relevant guidelines]

## Steps to Reproduce
1. 
2. 
3. 

## Expected Behavior
What should happen

## Actual Behavior
What actually happens

## User Impact
Who is affected and how

## Assistive Technology
- [ ] Screen reader (specify which)
- [ ] Keyboard only
- [ ] Voice control
- [ ] Other: 

## Priority
- [ ] Critical (blocks core functionality)
- [ ] High (significant usability impact)
- [ ] Medium (moderate usability impact)
- [ ] Low (minor enhancement)
```

## Conclusion

Following these comprehensive testing guidelines ensures the Adelaide Weather Forecasting System maintains WCAG 2.1 AA compliance and provides an excellent user experience for all users, including those using assistive technologies. Regular testing at all levels is essential for identifying and resolving accessibility barriers before they impact users.