# Adelaide Weather Forecasting API Documentation Portal

A comprehensive, production-ready API documentation portal with interactive examples and testing capabilities.

## 🌟 Features

### Complete OpenAPI Documentation
- **OpenAPI 3.0 Specification** (`openapi.yaml`) - Comprehensive API specification with detailed schemas, examples, and error responses
- **Interactive Swagger UI** (`index.html`) - Beautiful, custom-styled interface with real-time health monitoring
- **Parameter Validation** - Client-side validation and examples for all parameters
- **Response Examples** - Realistic examples for all endpoints and error conditions

### Developer Resources
- **🔐 Authentication Guide** (`authentication.md`) - Complete guide with examples in Python, JavaScript, and curl
- **⚡ Quick Start Tutorial** (`quickstart.md`) - Step-by-step guide to get started in minutes
- **🏗️ Integration Guide** (`integration-guide.md`) - Production-ready integration patterns for real applications
- **🚦 Rate Limiting Policy** (`rate-limiting.md`) - Detailed rate limiting information and best practices
- **❌ Error Codes Reference** (`error-codes.md`) - Comprehensive error handling guide with solutions

### Interactive Testing
- **🧪 Built-in Testing** - Quick test functions directly in the documentation portal
- **🔬 Advanced Testing Interface** (`test-interface.html`) - Comprehensive testing tool with request builder
- **📊 Real-time Response Display** - Formatted JSON responses with syntax highlighting
- **📜 Request History** - Track and replay previous API requests
- **⚡ Quick Test Suite** - Automated tests for common scenarios

### Production-Ready Client Libraries
- **Python Client** (`examples/python-client.py`) - Full-featured async client with retry logic, error handling, and examples
- **JavaScript Client** (`examples/javascript-client.js`) - Browser and Node.js compatible client with comprehensive error handling

## 🚀 Getting Started

### View the Documentation
1. Open `index.html` in your browser
2. Click "Authorize" to add your API token
3. Explore endpoints using "Try it out"

### Interactive Testing
1. Use the built-in quick tests in the main portal
2. Or open `test-interface.html` for advanced testing capabilities
3. Configure your API token and base URL
4. Build requests with the visual interface

### Integration
1. Read the `quickstart.md` for immediate setup
2. Check `integration-guide.md` for production patterns
3. Download client libraries from the `examples/` directory
4. Follow authentication setup in `authentication.md`

## 📁 File Structure

```
docs/api/
├── README.md                    # This file
├── index.html                   # Main documentation portal (Swagger UI)
├── openapi.yaml                 # Complete OpenAPI 3.0 specification
├── test-interface.html          # Advanced testing interface
├── authentication.md            # Authentication guide and examples
├── quickstart.md               # Quick start tutorial
├── integration-guide.md        # Production integration patterns
├── rate-limiting.md            # Rate limiting policies and handling
├── error-codes.md              # Error codes and troubleshooting
└── examples/
    ├── python-client.py        # Production Python client
    └── javascript-client.js    # Browser/Node.js client
```

## 🎯 Key Endpoints

| Endpoint | Description | Auth Required |
|----------|-------------|---------------|
| `GET /forecast` | Get weather forecast with uncertainty bounds | Yes |
| `GET /health` | Basic system health and readiness status | No |
| `GET /health/faiss` | FAISS-specific health monitoring and performance | Yes |
| `GET /health/detailed` | Comprehensive health report with all components | No |
| `GET /health/live` | Kubernetes liveness probe endpoint | No |
| `GET /health/ready` | Kubernetes readiness probe endpoint | No |
| `GET /health/dependencies` | External dependency status check | No |
| `GET /health/performance` | Performance metrics and baselines | No |
| `GET /health/status` | Simple UP/DOWN status check | No |
| `GET /metrics` | Prometheus metrics including FAISS monitoring | Yes |
| `GET /analogs` | Historical analog pattern analysis | Yes |

## 🔧 Configuration

### Environment Variables
```bash
# Required for authenticated endpoints
export WEATHER_API_TOKEN="your_token_here"

# Optional: Override default base URL
export WEATHER_API_BASE_URL="https://api.adelaideweather.example.com"
```

### Rate Limits
- **Forecast endpoint**: 60 requests/minute
- **Health endpoints**: 
  - `/health`, `/health/status`: 60 requests/minute
  - `/health/detailed`: 20 requests/minute
  - `/health/faiss`, `/health/dependencies`, `/health/performance`: 30 requests/minute
- **Metrics endpoint**: 10 requests/minute
- **Analogs endpoint**: 10 requests/minute

## 🔍 Testing Examples

### Quick Health Check
```bash
# Basic health check
curl -X GET "https://api.adelaideweather.example.com/health"

# Comprehensive health report
curl -X GET "https://api.adelaideweather.example.com/health/detailed"

# FAISS health monitoring (requires authentication)
curl -X GET "https://api.adelaideweather.example.com/health/faiss" \
  -H "Authorization: Bearer YOUR_TOKEN"

# Kubernetes liveness probe
curl -X GET "https://api.adelaideweather.example.com/health/live"

# Kubernetes readiness probe
curl -X GET "https://api.adelaideweather.example.com/health/ready"
```

### Basic Forecast
```bash
curl -X GET "https://api.adelaideweather.example.com/forecast?horizon=24h&vars=t2m,u10,v10,msl" \
  -H "Authorization: Bearer YOUR_TOKEN"
```

### Using Python Client
```python
import asyncio
from examples.python_client import AdelaideWeatherClient

async def main():
    async with AdelaideWeatherClient('your_token') as client:
        forecast = await client.get_forecast({'horizon': '24h'})
        print(f"Temperature: {forecast['variables']['t2m']['value']}°C")

asyncio.run(main())
```

### Using JavaScript Client
```javascript
const client = new AdelaideWeatherClient('your_token');

client.getForecast({ horizon: '24h' })
    .then(forecast => {
        console.log(`Temperature: ${forecast.variables.t2m.value}°C`);
    })
    .catch(error => console.error('Error:', error));
```

## 🛠️ Development

### Local Development Server
```bash
# Simple HTTP server for local testing
python -m http.server 8080
# or
npx serve .

# Then visit: http://localhost:8080
```

### API Mock Server
For local development, you can use the health endpoint without authentication:
```javascript
// Test connectivity
fetch('https://api.adelaideweather.example.com/health')
    .then(response => response.json())
    .then(data => console.log('API Status:', data.ready ? 'Ready' : 'Not Ready'));
```

## 📊 Monitoring

### Health Monitoring
The documentation portal includes real-time health monitoring:
- **Green indicator**: API is healthy and ready
- **Yellow indicator**: API responding but not fully ready
- **Red indicator**: API not responding

#### Enhanced Health Endpoints
- **`/health`**: Basic health check with system status
- **`/health/detailed`**: Comprehensive report including all components
- **`/health/faiss`**: FAISS-specific performance monitoring with query metrics
- **`/health/live`**: Kubernetes liveness probe (application alive check)
- **`/health/ready`**: Kubernetes readiness probe (traffic ready check)
- **`/health/dependencies`**: External dependency status (Redis, file system)
- **`/health/performance`**: System performance metrics and baselines
- **`/health/status`**: Simple UP/DOWN status for load balancers

### Metrics Integration
For production monitoring, integrate with:
- **Prometheus**: Use `/metrics` endpoint
- **Grafana**: Import dashboard configuration from integration guide
- **Custom Monitoring**: Use response headers for rate limiting and performance metrics

## 🔐 Security

### API Token Management
- Store tokens in environment variables
- Use different tokens for different environments
- Rotate tokens regularly
- Never commit tokens to version control

### Best Practices
- Always use HTTPS in production
- Implement proper error handling
- Use retry logic with exponential backoff
- Monitor rate limits and implement caching

## 📈 Performance Optimization

### Caching Strategies
- Cache responses for 5 minutes (forecast data)
- Use Redis or similar for shared caching
- Implement client-side caching for better UX

### Request Optimization
- Request only needed variables
- Use appropriate forecast horizons
- Batch similar requests when possible
- Monitor and respect rate limits

## 🆘 Support

### Getting Help
- **Documentation Issues**: Check the error codes reference
- **Integration Help**: Review the integration guide patterns
- **API Issues**: Include correlation IDs from error responses
- **Performance**: Monitor using the metrics endpoint

### Contact Information
- **Email**: support@adelaideweather.example.com
- **Documentation**: This portal and linked guides
- **Status Page**: Monitor via `/health` endpoint

## 📝 Contributing

### Documentation Updates
1. Update the OpenAPI specification in `openapi.yaml`
2. Test changes using the interactive interface
3. Update relevant markdown documentation
4. Verify all examples still work

### Client Library Updates
1. Test against the live API
2. Update error handling for new error codes
3. Add examples for new features
4. Update inline documentation

## 🏆 Features Completed

✅ **OpenAPI 3.0 Specification** - Complete with examples and error handling  
✅ **Interactive Swagger UI** - Custom-styled with health monitoring  
✅ **Authentication Guide** - Multi-language examples and best practices  
✅ **Quick Start Tutorial** - Step-by-step implementation guide  
✅ **Integration Guide** - Production-ready patterns and architectures  
✅ **Rate Limiting Documentation** - Comprehensive policy and handling  
✅ **Error Codes Reference** - Complete troubleshooting guide  
✅ **Advanced Testing Interface** - Visual request builder and history  
✅ **Production Client Libraries** - Python and JavaScript with full features  
✅ **Interactive Testing** - Built-in test functions and validation  
✅ **Real-time Health Monitoring** - Live API status in documentation portal  

## 🎉 Ready for Production

This documentation portal is production-ready and includes:
- Comprehensive API documentation with interactive examples
- Multiple testing interfaces for different use cases
- Production-ready client libraries with proper error handling
- Integration guides for real-world applications
- Monitoring and performance optimization guidance
- Security best practices and authentication management

The portal accelerates developer adoption and reduces support burden by providing self-service capabilities and comprehensive guidance for integration.