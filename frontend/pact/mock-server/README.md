# Pact Mock Server for Frontend Development

This mock server provides a realistic API backend for frontend development based on Pact contracts. It allows frontend developers to work independently of the backend while ensuring compatibility with the actual API contract.

## Features

- ✅ **Contract-based responses** - All responses match the Pact contract definitions
- ✅ **Enhanced API schema** - Supports the full enhanced schema with narratives, risk assessments, and analog summaries
- ✅ **Multiple provider states** - Switch between operational, down, and error states
- ✅ **Realistic data** - Generated responses with proper data types and ranges
- ✅ **Error scenarios** - Test authentication failures, validation errors, and system unavailability
- ✅ **Request logging** - Debug frontend requests and responses

## Usage

### Start the Mock Server

```bash
# From the frontend directory
npm run test:pact:mock

# Or directly with node
node pact/mock-server/start-mock-server.js
```

The server will start on `http://localhost:8089` by default.

### Available Endpoints

#### GET /forecast

Weather forecast with enhanced schema including:

- Variable forecasts with uncertainty bounds
- Wind calculations from u/v components
- Weather narrative description
- Risk assessment for various hazards
- Historical analog pattern summary

**Example Request:**

```bash
curl -H "Authorization: Bearer test-api-token" \
     "http://localhost:8089/forecast?horizon=24h&vars=t2m,u10,v10,msl"
```

**Example Response:**

```json
{
  "horizon": "24h",
  "generated_at": "2025-10-29T15:30:00Z",
  "variables": {
    "t2m": {
      "value": 22.5,
      "p05": 20.25,
      "p95": 24.75,
      "confidence": 87.2,
      "available": true,
      "analog_count": 42
    }
  },
  "wind10m": {
    "speed": 3.4,
    "direction": 225.7,
    "available": true
  },
  "narrative": "Forecast for 24h: mild conditions with temperature around 22.5°C, light winds at 3.4 m/s from 226°, normal pressure system (1014 hPa).",
  "risk_assessment": {
    "thunderstorm": "low",
    "heat_stress": "minimal",
    "wind_damage": "minimal",
    "precipitation": "low"
  },
  "analogs_summary": {
    "most_similar_date": "2023-03-15T12:00:00Z",
    "similarity_score": 0.82,
    "analog_count": 42,
    "outcome_description": "Strong pattern match with typical seasonal conditions",
    "confidence_explanation": "Based on 42 historical analog patterns"
  }
}
```

#### GET /health

System health and operational status

**Example Request:**

```bash
curl "http://localhost:8089/health"
```

### Supported Provider States

The mock server supports different provider states for testing various scenarios:

- **`operational`** (default) - System is healthy and returning forecasts
- **`down`** - System is unavailable (503 errors)
- **`cape_available`** - System includes CAPE data for thunderstorm risk assessment
- **`rate_limited`** - Rate limiting is active (429 errors)

### Testing Different Scenarios

#### Test Error Handling

```bash
# Invalid horizon
curl -H "Authorization: Bearer test-api-token" \
     "http://localhost:8089/forecast?horizon=invalid&vars=t2m"

# Invalid authentication
curl -H "Authorization: Bearer invalid-token" \
     "http://localhost:8089/forecast?horizon=24h&vars=t2m"

# Missing authentication
curl "http://localhost:8089/forecast?horizon=24h&vars=t2m"
```

#### Test Different Variables

```bash
# Basic variables
curl -H "Authorization: Bearer test-api-token" \
     "http://localhost:8089/forecast?horizon=6h&vars=t2m,msl"

# With wind components
curl -H "Authorization: Bearer test-api-token" \
     "http://localhost:8089/forecast?horizon=12h&vars=t2m,u10,v10,msl"

# With CAPE for thunderstorm risk
curl -H "Authorization: Bearer test-api-token" \
     "http://localhost:8089/forecast?horizon=6h&vars=t2m,cape,msl"
```

## Configuration

### Environment Variables

- `PACT_MOCK_PORT` - Server port (default: 8089)
- `PACT_MOCK_HOST` - Server host (default: localhost)

### Frontend Configuration

Update your frontend API client to use the mock server during development:

```javascript
// In your API configuration
const API_BASE_URL =
  process.env.NODE_ENV === 'development'
    ? 'http://localhost:8089' // Mock server
    : 'http://localhost:8000'; // Real API
```

## Development Workflow

1. **Start mock server** - Run the mock server for independent frontend development
2. **Develop frontend** - Build UI components against realistic API responses
3. **Run consumer tests** - Generate/update Pact contracts with new requirements
4. **Verify contracts** - Backend team runs provider tests to ensure compliance
5. **Integration testing** - Test against real backend before deployment

## Debugging

### Request Logging

All requests and responses are logged to `logs/mock-server.log`. Monitor this file for debugging:

```bash
tail -f logs/mock-server.log
```

### Contract Validation

The mock server responses are based on the Pact contracts. If you see unexpected responses:

1. Check the generated contract files in `pacts/`
2. Verify consumer tests are generating expected interactions
3. Ensure provider states match your test scenarios

## Troubleshooting

### Port Already in Use

If port 8089 is already in use:

```bash
PACT_MOCK_PORT=8090 npm run test:pact:mock
```

### Contract Files Not Found

Ensure consumer tests have been run to generate contract files:

```bash
npm run test:pact:consumer
```

### Authentication Issues

The mock server accepts any Bearer token starting with `test-` for development:

- ✅ `Bearer test-api-token`
- ✅ `Bearer test-dev-token`
- ❌ `Bearer invalid-token`
