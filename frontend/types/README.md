# Adelaide Weather Forecasting API Types

This document describes the TypeScript types generated for the enhanced API schema (T-001).

## Core Types

### ForecastResponse
The main forecast response type with enhanced features including:
- Risk assessment for weather hazards
- Historical analog pattern analysis  
- Human-readable narrative
- Confidence explanations

### RiskAssessment
Risk levels for various weather hazards:
- Thunderstorm development
- Heat stress
- Wind damage potential  
- Heavy precipitation/flooding

### AnalogsSummary
Historical analog pattern matching results:
- Most similar date and similarity score
- Number of analogs used
- Outcome descriptions and confidence explanations

## Validation

Generated types include:
- Strict TypeScript mode compatibility
- Runtime type guards
- Input validation helpers
- Comprehensive error handling

## Usage

```typescript
import type { ForecastResponse, RiskAssessment, isApiError } from '@/types'

// Type-safe API response handling
const response = await fetch('/api/forecast')
const data = await response.json()

if (isApiError(data)) {
  console.error('API Error:', data.error)
} else {
  // data is now typed as ForecastResponse
  console.log('Risk level:', data.risk_assessment.thunderstorm)
  console.log('Narrative:', data.narrative)
}
```

---
Generated on: 2025-11-11T14:44:45.345Z
