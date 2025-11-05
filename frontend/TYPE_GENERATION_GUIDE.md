# OpenAPI Type Generation Developer Guide

## Quick Start

### Prerequisites

- Node.js 18+ with npm
- Python 3.11+ (for API schema generation)
- TypeScript knowledge
- Basic understanding of OpenAPI/Swagger

### Basic Workflow

```bash
# 1. Install dependencies
npm install

# 2. Generate types from API
npm run generate:types

# 3. Validate generated types
npm run validate:types

# 4. Use types in your code
import type { ForecastResponse } from './types/api-utilities';
```

## Generated Files Overview

```
frontend/types/
├── generated-api.ts      # Auto-generated from OpenAPI schema
├── api-utilities.ts      # Enhanced utility types and helpers
├── README.md            # Auto-generated documentation
└── .generation_metadata.json  # Build metadata
```

## Type Usage Examples

### Basic API Response Handling

```typescript
import type { ForecastResponse, ApiResponse } from './types/api-utilities';
import { isForecastResponse, isApiError } from './types/api-utilities';

async function getForecast(horizon: string): Promise<ForecastResponse> {
  const response = await fetch(`/api/forecast?horizon=${horizon}`);
  const data: ApiResponse<ForecastResponse> = await response.json();
  
  if (isApiError(data)) {
    throw new Error(`API Error: ${data.error}`);
  }
  
  if (isForecastResponse(data)) {
    // TypeScript knows this is ForecastResponse
    return data;
  }
  
  throw new Error('Invalid response format');
}
```

### Type-Safe Parameter Validation

```typescript
import { 
  validateWeatherVariable, 
  validateForecastHorizon,
  WEATHER_VARIABLES,
  FORECAST_HORIZONS 
} from './types/api-utilities';

function buildForecastRequest(horizon: string, variables: string[]) {
  // Validate horizon
  if (!validateForecastHorizon(horizon)) {
    throw new Error(`Invalid horizon. Must be one of: ${FORECAST_HORIZONS.join(', ')}`);
  }
  
  // Validate variables
  for (const variable of variables) {
    if (!validateWeatherVariable(variable)) {
      throw new Error(`Invalid variable: ${variable}. Must be one of: ${WEATHER_VARIABLES.join(', ')}`);
    }
  }
  
  return `/forecast?horizon=${horizon}&vars=${variables.join(',')}`;
}
```

### React Component with Types

```typescript
import React, { useState, useEffect } from 'react';
import type { ForecastResponse, WeatherVariable } from './types/api-utilities';
import { isForecastResponse } from './types/api-utilities';

interface ForecastDisplayProps {
  horizon: string;
  variables: WeatherVariable[];
}

export function ForecastDisplay({ horizon, variables }: ForecastDisplayProps) {
  const [forecast, setForecast] = useState<ForecastResponse | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    async function fetchForecast() {
      setLoading(true);
      setError(null);
      
      try {
        const response = await fetch(
          `/api/forecast?horizon=${horizon}&vars=${variables.join(',')}`
        );
        const data = await response.json();
        
        if (isForecastResponse(data)) {
          setForecast(data);
        } else {
          setError('Invalid forecast response format');
        }
      } catch (err) {
        setError(`Failed to fetch forecast: ${err}`);
      } finally {
        setLoading(false);
      }
    }

    fetchForecast();
  }, [horizon, variables]);

  if (loading) return <div>Loading forecast...</div>;
  if (error) return <div>Error: {error}</div>;
  if (!forecast) return <div>No forecast data</div>;

  return (
    <div>
      <h2>Weather Forecast ({forecast.horizon})</h2>
      <p>{forecast.narrative}</p>
      
      <div>
        <h3>Risk Assessment</h3>
        <ul>
          <li>Thunderstorm: {forecast.risk_assessment.thunderstorm}</li>
          <li>Heat Stress: {forecast.risk_assessment.heat_stress}</li>
          <li>Wind Damage: {forecast.risk_assessment.wind_damage}</li>
          <li>Precipitation: {forecast.risk_assessment.precipitation}</li>
        </ul>
      </div>
      
      <div>
        <h3>Variables</h3>
        {Object.entries(forecast.variables).map(([key, variable]) => (
          variable.available && (
            <div key={key}>
              <strong>{key}:</strong> {variable.value} 
              (±{variable.confidence}% confidence)
            </div>
          )
        ))}
      </div>
    </div>
  );
}
```

## Development Workflow

### 1. When API Changes

```bash
# API developer updates the FastAPI application
cd api
# ... make changes to main.py, models, etc.

# Regenerate OpenAPI schema
python enhanced_openapi_generator.py --validate

# Frontend developer regenerates types
cd ../frontend
npm run generate:types

# Validate that types work with existing code
npm run validate:types
npm run type-check
```

### 2. When Adding New Endpoints

```bash
# 1. Add endpoint to FastAPI app with proper type annotations
# 2. Generate new schema
cd api && python enhanced_openapi_generator.py --validate

# 3. Generate updated types
cd ../frontend && npm run generate:types

# 4. Update Pact contracts if needed
npm run test:pact

# 5. Validate everything works
npm run validate:pact
npm run validate:types
```

### 3. When Types Don't Match Expectations

```bash
# Run comprehensive validation
npm run validate:types -- --level exhaustive --strict

# Check Pact contract compatibility
npm run validate:pact -- --strict

# If there are issues, check the validation report
cat validation-reports/validation-report.md
```

## Troubleshooting

### Common Issues and Solutions

#### "Generated types file not found"

```bash
# Solution: Run type generation first
npm run generate:openapi
npm run generate:types
```

#### "TypeScript compilation failed"

```bash
# Check the specific errors
npx tsc --noEmit --skipLibCheck

# Common fixes:
# 1. Update import paths
# 2. Check for circular dependencies
# 3. Ensure all required types are exported
```

#### "Pact validation failed"

```bash
# Run with detailed output
npm run validate:pact -- --strict --output pact/debug

# Check the compatibility report
cat pact/generated/validation-report.json

# Common fixes:
# 1. Update Pact contracts to match new API
# 2. Regenerate types if schema changed
# 3. Check for breaking changes in API
```

#### "API response doesn't match types"

```bash
# Check runtime validation
npm run validate:types -- --level comprehensive

# Verify API is serving the expected schema
curl -H "Accept: application/json" http://localhost:8000/openapi.json

# Common fixes:
# 1. Ensure API and frontend are in sync
# 2. Regenerate schema from latest API
# 3. Check for environment-specific differences
```

### Debugging Tips

#### Enable Detailed Logging

```bash
# For CI environments
CI=true npm run generate:types

# For local development with verbose output
DEBUG=true npm run validate:types
```

#### Check Generated Metadata

```typescript
// View generation metadata
import metadata from './types/.generation_metadata.json';
console.log('Schema hash:', metadata.schemaHash);
console.log('Generated at:', metadata.timestamp);
```

#### Validate Specific Types

```typescript
import { isForecastResponse } from './types/api-utilities';

// Test type guard with sample data
const sampleData = { /* your test data */ };
console.log('Is valid forecast:', isForecastResponse(sampleData));
```

## Advanced Usage

### Custom Type Guards

```typescript
// Create custom type guards for specific use cases
export function isValidTemperature(value: unknown): value is number {
  return typeof value === 'number' && value > -100 && value < 100;
}

export function hasCompleteWeatherData(
  forecast: ForecastResponse
): forecast is ForecastResponse & {
  variables: { t2m: { available: true; value: number } }
} {
  return (
    forecast.variables.t2m?.available === true &&
    typeof forecast.variables.t2m.value === 'number'
  );
}
```

### Type-Safe API Client

```typescript
import type { 
  ForecastResponse, 
  HealthResponse, 
  ForecastRequestParams 
} from './types/api-utilities';

class WeatherApiClient {
  constructor(private baseUrl: string, private apiKey: string) {}

  async forecast(params: ForecastRequestParams): Promise<ForecastResponse> {
    const url = new URL('/forecast', this.baseUrl);
    if (params.horizon) url.searchParams.set('horizon', params.horizon);
    if (params.vars) url.searchParams.set('vars', params.vars);

    const response = await fetch(url.toString(), {
      headers: {
        'Authorization': `Bearer ${this.apiKey}`,
        'Content-Type': 'application/json'
      }
    });

    const data = await response.json();
    
    if (!response.ok) {
      throw new Error(`API Error: ${data.error || 'Unknown error'}`);
    }

    if (!isForecastResponse(data)) {
      throw new Error('Invalid forecast response format');
    }

    return data;
  }

  async health(): Promise<HealthResponse> {
    const response = await fetch(`${this.baseUrl}/health`);
    const data = await response.json();

    if (!isHealthResponse(data)) {
      throw new Error('Invalid health response format');
    }

    return data;
  }
}
```

### Testing with Generated Types

```typescript
import type { ForecastResponse } from './types/api-utilities';
import { WeatherApiMatchers } from './pact/generated/pact-helpers';

// Use generated Pact matchers for testing
describe('Forecast API', () => {
  it('should return valid forecast response', async () => {
    const mockResponse = WeatherApiMatchers.forecastResponse();
    
    // Your test code here
    expect(mockResponse).toMatchObject({
      horizon: expect.any(String),
      variables: expect.any(Object),
      narrative: expect.any(String)
    });
  });
});

// Type-safe test data creation
function createMockForecast(overrides: Partial<ForecastResponse> = {}): ForecastResponse {
  return {
    horizon: '24h',
    generated_at: new Date().toISOString(),
    variables: {
      t2m: { value: 20.5, p05: 18.0, p95: 23.0, confidence: 85.5, available: true, analog_count: 45 }
    },
    narrative: 'Test forecast',
    risk_assessment: {
      thunderstorm: 'low',
      heat_stress: 'minimal',
      wind_damage: 'minimal',
      precipitation: 'low'
    },
    // ... other required fields
    ...overrides
  };
}
```

## Best Practices

### 1. Always Use Type Guards

```typescript
// ❌ Don't assume response shape
const forecast = await api.getForecast();
console.log(forecast.variables.t2m.value); // Might crash

// ✅ Use type guards
const forecast = await api.getForecast();
if (isForecastResponse(forecast) && forecast.variables.t2m?.available) {
  console.log(forecast.variables.t2m.value); // Safe
}
```

### 2. Validate Input Parameters

```typescript
// ❌ Don't trust user input
function requestForecast(horizon: string, vars: string[]) {
  return fetch(`/api/forecast?horizon=${horizon}&vars=${vars.join(',')}`);
}

// ✅ Validate parameters
function requestForecast(horizon: string, vars: string[]) {
  if (!validateForecastHorizon(horizon)) {
    throw new Error(`Invalid horizon: ${horizon}`);
  }
  
  for (const variable of vars) {
    if (!validateWeatherVariable(variable)) {
      throw new Error(`Invalid variable: ${variable}`);
    }
  }
  
  return fetch(`/api/forecast?horizon=${horizon}&vars=${vars.join(',')}`);
}
```

### 3. Handle Errors Gracefully

```typescript
async function safeApiCall<T>(
  apiCall: () => Promise<T>,
  fallback: T
): Promise<T> {
  try {
    return await apiCall();
  } catch (error) {
    console.error('API call failed:', error);
    return fallback;
  }
}

// Usage
const forecast = await safeApiCall(
  () => api.getForecast({ horizon: '24h' }),
  createMockForecast() // Type-safe fallback
);
```

### 4. Keep Types Updated

```bash
# Add to your package.json scripts
{
  "scripts": {
    "predev": "npm run generate:types",
    "prebuild": "npm run generate:types && npm run validate:types",
    "postinstall": "npm run generate:types"
  }
}
```

### 5. Document Type Usage

```typescript
/**
 * Processes weather forecast data for display
 * @param forecast - Validated forecast response from API
 * @param options - Display configuration options
 * @returns Formatted forecast data ready for UI rendering
 */
function processForecast(
  forecast: ForecastResponse,
  options: { includeUncertainty: boolean; precision: number }
): ProcessedForecast {
  // Implementation here
}
```

## Migration Guide

### From Manual Types to Generated Types

1. **Backup existing types**
```bash
cp -r types types-backup
```

2. **Generate new types**
```bash
npm run generate:types
```

3. **Update imports**
```typescript
// Old
import { ForecastResponse } from './types/manual-types';

// New  
import type { ForecastResponse } from './types/api-utilities';
```

4. **Replace type guards**
```typescript
// Old custom implementation
function isForecast(data: any): data is ForecastResponse {
  return data && typeof data.horizon === 'string';
}

// New generated implementation
import { isForecastResponse } from './types/api-utilities';
```

5. **Update validation logic**
```typescript
// Old manual validation
if (typeof response.variables?.t2m?.value === 'number') {
  // ...
}

// New type-safe validation
if (isForecastResponse(response) && response.variables.t2m?.available) {
  // TypeScript knows the structure is correct
}
```

---

## Support and Resources

- **Internal Documentation:** Check `types/README.md` for generated documentation
- **Validation Reports:** Review `validation-reports/` for detailed analysis
- **CI/CD Logs:** Check GitHub Actions for pipeline failures
- **Type Definitions:** Explore generated files for available types and utilities

For issues or questions, check the validation reports first, then consult this guide or reach out to the development team.