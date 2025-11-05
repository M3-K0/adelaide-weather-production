/**
 * Adelaide Weather Forecasting API - JavaScript Client
 * ===================================================
 * 
 * Production-ready JavaScript/Node.js client for the Adelaide Weather Forecasting API.
 * Works in both Node.js and modern browsers with comprehensive error handling and examples.
 * 
 * Features:
 * - Automatic retry with exponential backoff
 * - Rate limit handling with intelligent delays
 * - TypeScript-style JSDoc annotations
 * - Browser and Node.js compatibility
 * - Request/response logging
 * - Session management
 * - Comprehensive error handling
 * 
 * Requirements:
 *   Node.js: npm install node-fetch
 *   Browser: Modern browser with fetch API
 * 
 * Usage:
 *   const client = new AdelaideWeatherClient('your_token_here');
 *   const forecast = await client.getForecast({ horizon: '24h' });
 * 
 * @author Adelaide Weather API Team
 * @version 1.0.0
 */

// Import fetch for Node.js (not needed in browsers)
const fetch = typeof window !== 'undefined' ? window.fetch : require('node-fetch');

/**
 * Custom error classes for different API error types
 */
class WeatherAPIError extends Error {
    /**
     * @param {string} message Error message
     * @param {number} [statusCode] HTTP status code
     * @param {string} [correlationId] Request correlation ID
     */
    constructor(message, statusCode = null, correlationId = null) {
        super(message);
        this.name = 'WeatherAPIError';
        this.statusCode = statusCode;
        this.correlationId = correlationId;
    }
}

class AuthenticationError extends WeatherAPIError {
    constructor(message, statusCode, correlationId) {
        super(message, statusCode, correlationId);
        this.name = 'AuthenticationError';
    }
}

class RateLimitError extends WeatherAPIError {
    /**
     * @param {string} message Error message
     * @param {number} retryAfter Seconds to wait before retry
     */
    constructor(message, retryAfter = 60) {
        super(message);
        this.name = 'RateLimitError';
        this.retryAfter = retryAfter;
    }
}

class ValidationError extends WeatherAPIError {
    constructor(message, statusCode, correlationId) {
        super(message, statusCode, correlationId);
        this.name = 'ValidationError';
    }
}

class ServiceUnavailableError extends WeatherAPIError {
    constructor(message, statusCode, correlationId) {
        super(message, statusCode, correlationId);
        this.name = 'ServiceUnavailableError';
    }
}

/**
 * Configuration object for the weather client
 * @typedef {Object} ClientConfig
 * @property {string} baseUrl - API base URL
 * @property {number} timeout - Request timeout in milliseconds
 * @property {number} maxRetries - Maximum number of retries
 * @property {number} backoffFactor - Exponential backoff factor
 * @property {number} rateLimitRetryDelay - Default rate limit retry delay
 * @property {boolean} enableLogging - Enable request/response logging
 */

/**
 * Forecast request parameters
 * @typedef {Object} ForecastRequest
 * @property {string} horizon - Forecast horizon (6h, 12h, 24h, 48h)
 * @property {string[]} variables - List of weather variables
 */

/**
 * Production-ready client for the Adelaide Weather Forecasting API
 */
class AdelaideWeatherClient {
    // Valid forecast horizons
    static VALID_HORIZONS = ['6h', '12h', '24h', '48h'];
    
    // Valid weather variables
    static VALID_VARIABLES = [
        't2m', 'u10', 'v10', 'msl', 'r850', 
        'tp6h', 'cape', 't850', 'z500'
    ];
    
    // Default configuration
    static DEFAULT_CONFIG = {
        baseUrl: 'https://api.adelaideweather.example.com',
        timeout: 30000,
        maxRetries: 3,
        backoffFactor: 1.0,
        rateLimitRetryDelay: 60000,
        enableLogging: false
    };
    
    /**
     * Initialize the weather client
     * @param {string} apiToken - API authentication token
     * @param {ClientConfig} [config] - Client configuration
     */
    constructor(apiToken, config = {}) {
        if (!apiToken) {
            throw new Error('API token is required');
        }
        
        this.apiToken = apiToken;
        this.config = { ...AdelaideWeatherClient.DEFAULT_CONFIG, ...config };
        
        // Generate correlation ID for this client session
        this.sessionId = this._generateCorrelationId();
        
        this._log('info', `Adelaide Weather Client initialized for ${this.config.baseUrl}`);
    }
    
    /**
     * Generate a correlation ID for request tracking
     * @returns {string} Correlation ID
     * @private
     */
    _generateCorrelationId() {
        return 'js_' + Math.random().toString(36).substr(2, 9);
    }
    
    /**
     * Log message if logging is enabled
     * @param {string} level - Log level
     * @param {string} message - Log message
     * @param {Object} [extra] - Extra data
     * @private
     */
    _log(level, message, extra = {}) {
        if (this.config.enableLogging) {
            const timestamp = new Date().toISOString();
            console.log(`[${timestamp}] [${level.toUpperCase()}] ${message}`, extra);
        }
    }
    
    /**
     * Sleep for specified milliseconds
     * @param {number} ms - Milliseconds to sleep
     * @returns {Promise<void>}
     * @private
     */
    _sleep(ms) {
        return new Promise(resolve => setTimeout(resolve, ms));
    }
    
    /**
     * Make authenticated API request with retry logic
     * @param {string} endpoint - API endpoint
     * @param {Object} [params] - Query parameters
     * @param {Object} [options] - Additional fetch options
     * @returns {Promise<Object>} JSON response
     * @private
     */
    async _makeRequest(endpoint, params = {}, options = {}) {
        const url = new URL(endpoint, this.config.baseUrl);
        
        // Add query parameters
        Object.entries(params).forEach(([key, value]) => {
            if (value !== undefined && value !== null) {
                url.searchParams.append(key, value);
            }
        });
        
        const correlationId = this._generateCorrelationId();
        
        // Prepare headers
        const headers = {
            'Authorization': `Bearer ${this.apiToken}`,
            'Accept': 'application/json',
            'User-Agent': 'Adelaide-Weather-JS-Client/1.0.0',
            'X-Correlation-ID': correlationId,
            ...options.headers
        };
        
        // Request configuration
        const requestConfig = {
            method: 'GET',
            headers,
            signal: AbortSignal.timeout ? AbortSignal.timeout(this.config.timeout) : undefined,
            ...options
        };
        
        this._log('debug', `Making request to ${url.toString()}`, { correlationId });
        
        // Retry logic
        let lastError;
        for (let attempt = 0; attempt <= this.config.maxRetries; attempt++) {
            try {
                const response = await fetch(url.toString(), requestConfig);
                
                this._log('debug', `Response status: ${response.status}`, {
                    correlationId,
                    attempt: attempt + 1
                });
                
                return await this._handleResponse(response, correlationId);
                
            } catch (error) {
                lastError = error;
                
                if (attempt < this.config.maxRetries) {
                    const delay = Math.pow(2, attempt) * this.config.backoffFactor * 1000;
                    this._log('warn', `Request failed, retrying in ${delay}ms`, {
                        correlationId,
                        attempt: attempt + 1,
                        error: error.message
                    });
                    await this._sleep(delay);
                } else {
                    this._log('error', 'Request failed after all retries', {
                        correlationId,
                        error: error.message
                    });
                }
            }
        }
        
        // Handle timeout and connection errors
        if (lastError.name === 'AbortError') {
            throw new WeatherAPIError(`Request timeout after ${this.config.timeout}ms`);
        } else if (lastError.message.includes('fetch')) {
            throw new WeatherAPIError(`Connection error: ${lastError.message}`);
        } else {
            throw new WeatherAPIError(`Request failed: ${lastError.message}`);
        }
    }
    
    /**
     * Handle API response and convert errors to appropriate exceptions
     * @param {Response} response - Fetch response object
     * @param {string} correlationId - Request correlation ID
     * @returns {Promise<Object>} Parsed JSON response
     * @private
     */
    async _handleResponse(response, correlationId) {
        const responseCorrelationId = response.headers.get('X-Correlation-ID') || correlationId;
        
        if (response.ok) {
            try {
                return await response.json();
            } catch (error) {
                throw new WeatherAPIError('Invalid JSON response', response.status, responseCorrelationId);
            }
        }
        
        // Handle error responses
        let errorMessage = `HTTP ${response.status}: ${response.statusText}`;
        try {
            const errorData = await response.json();
            errorMessage = errorData.error?.message || errorMessage;
        } catch (e) {
            // Use default error message if JSON parsing fails
        }
        
        switch (response.status) {
            case 401:
            case 403:
                throw new AuthenticationError(errorMessage, response.status, responseCorrelationId);
            case 400:
                throw new ValidationError(errorMessage, response.status, responseCorrelationId);
            case 429:
                const retryAfter = parseInt(response.headers.get('Retry-After')) || 60;
                throw new RateLimitError(errorMessage, retryAfter);
            case 503:
                throw new ServiceUnavailableError(errorMessage, response.status, responseCorrelationId);
            default:
                throw new WeatherAPIError(errorMessage, response.status, responseCorrelationId);
        }
    }
    
    /**
     * Validate forecast request parameters
     * @param {ForecastRequest} request - Request parameters
     * @private
     */
    _validateForecastRequest(request) {
        if (request.horizon && !AdelaideWeatherClient.VALID_HORIZONS.includes(request.horizon)) {
            throw new ValidationError(
                `Invalid horizon '${request.horizon}'. Must be one of: ${AdelaideWeatherClient.VALID_HORIZONS.join(', ')}`
            );
        }
        
        if (request.variables) {
            const invalidVars = request.variables.filter(
                var_ => !AdelaideWeatherClient.VALID_VARIABLES.includes(var_)
            );
            if (invalidVars.length > 0) {
                throw new ValidationError(
                    `Invalid variables: ${invalidVars.join(', ')}. Valid: ${AdelaideWeatherClient.VALID_VARIABLES.join(', ')}`
                );
            }
        }
    }
    
    /**
     * Get system health status
     * @returns {Promise<Object>} Health status information
     */
    async getHealth() {
        return this._makeRequest('/health');
    }
    
    /**
     * Get weather forecast with uncertainty quantification
     * @param {ForecastRequest} [request] - Forecast request parameters
     * @returns {Promise<Object>} Forecast data with uncertainty bounds
     * 
     * @example
     * const forecast = await client.getForecast({
     *     horizon: '24h',
     *     variables: ['t2m', 'u10', 'v10', 'msl']
     * });
     * console.log(`Temperature: ${forecast.variables.t2m.value}°C`);
     */
    async getForecast(request = {}) {
        // Set defaults
        const forecastRequest = {
            horizon: '24h',
            variables: ['t2m', 'u10', 'v10', 'msl'],
            ...request
        };
        
        // Validate parameters
        this._validateForecastRequest(forecastRequest);
        
        const params = {
            horizon: forecastRequest.horizon,
            vars: forecastRequest.variables.join(',')
        };
        
        return this._makeRequest('/forecast', params);
    }
    
    /**
     * Get Prometheus metrics (requires authentication)
     * @returns {Promise<string>} Prometheus metrics in text format
     */
    async getMetrics() {
        const response = await this._makeRequest('/metrics', {}, {
            headers: { 'Accept': 'text/plain' }
        });
        return response;
    }
    
    /**
     * Get detailed analog patterns analysis
     * @param {string} [horizon='24h'] - Forecast horizon to analyze
     * @returns {Promise<Object>} Historical analog patterns data
     */
    async getAnalogs(horizon = '24h') {
        if (!AdelaideWeatherClient.VALID_HORIZONS.includes(horizon)) {
            throw new ValidationError(
                `Invalid horizon '${horizon}'. Must be one of: ${AdelaideWeatherClient.VALID_HORIZONS.join(', ')}`
            );
        }
        
        return this._makeRequest('/analogs', { horizon });
    }
    
    /**
     * Wait for the API to become ready
     * @param {number} [maxWait=300000] - Maximum time to wait in milliseconds
     * @param {number} [checkInterval=5000] - Check interval in milliseconds
     * @returns {Promise<boolean>} True if API is ready, false if timeout
     */
    async waitForReady(maxWait = 300000, checkInterval = 5000) {
        const startTime = Date.now();
        
        while (Date.now() - startTime < maxWait) {
            try {
                const health = await this.getHealth();
                if (health.ready) {
                    this._log('info', 'API is ready');
                    return true;
                } else {
                    this._log('info', 'API not ready yet, waiting...');
                }
            } catch (error) {
                this._log('debug', `Health check failed: ${error.message}`);
            }
            
            await this._sleep(checkInterval);
        }
        
        this._log('warn', `API did not become ready within ${maxWait}ms`);
        return false;
    }
}

/**
 * Helper class for analyzing forecast results
 */
class ForecastAnalyzer {
    /**
     * Print a formatted forecast summary
     * @param {Object} forecast - Forecast data
     */
    static printForecastSummary(forecast) {
        console.log('\n' + '='.repeat(60));
        console.log(`Adelaide Weather Forecast (${forecast.horizon})`);
        console.log('='.repeat(60));
        console.log(`Generated at: ${forecast.generated_at}`);
        console.log(`Latency: ${forecast.latency_ms.toFixed(1)}ms`);
        
        console.log('\n--- Narrative ---');
        console.log(forecast.narrative);
        
        console.log('\n--- Variables ---');
        Object.entries(forecast.variables).forEach(([varName, varData]) => {
            if (varData.available) {
                console.log(
                    `${varName.padStart(6)}: ${varData.value.toFixed(1).padStart(8)} ` +
                    `[${varData.p05.toFixed(1).padStart(6)} to ${varData.p95.toFixed(1).padStart(6)}] ` +
                    `(confidence: ${(varData.confidence * 100).toFixed(1).padStart(5)}%)`
                );
            } else {
                console.log(`${varName.padStart(6)}: Not available`);
            }
        });
        
        if (forecast.wind10m?.available) {
            console.log('\n--- Wind ---');
            console.log(`Speed: ${forecast.wind10m.speed.toFixed(1)} m/s`);
            console.log(`Direction: ${forecast.wind10m.direction.toFixed(0)}°`);
        }
        
        console.log('\n--- Risk Assessment ---');
        Object.entries(forecast.risk_assessment).forEach(([riskType, level]) => {
            const readable = riskType.replace('_', ' ').replace(/\b\w/g, l => l.toUpperCase());
            console.log(`${readable.padStart(20)}: ${level}`);
        });
        
        console.log('\n--- Analog Summary ---');
        const analogs = forecast.analogs_summary;
        console.log(`Most similar date: ${analogs.most_similar_date}`);
        console.log(`Similarity score: ${(analogs.similarity_score * 100).toFixed(1)}%`);
        console.log(`Analog count: ${analogs.analog_count}`);
        console.log(`Outcome: ${analogs.outcome_description}`);
        
        console.log('\n--- Confidence ---');
        console.log(forecast.confidence_explanation);
        console.log('='.repeat(60) + '\n');
    }
    
    /**
     * Extract temperature information
     * @param {Object} forecast - Forecast data
     * @returns {Object|null} Temperature information or null if not available
     */
    static extractTemperatureInfo(forecast) {
        const tempData = forecast.variables?.t2m;
        if (!tempData?.available) {
            return null;
        }
        
        return {
            temperature: tempData.value,
            minTemp: tempData.p05,
            maxTemp: tempData.p95,
            confidence: tempData.confidence
        };
    }
    
    /**
     * Extract wind information
     * @param {Object} forecast - Forecast data
     * @returns {Object|null} Wind information or null if not available
     */
    static extractWindInfo(forecast) {
        const windData = forecast.wind10m;
        if (!windData?.available) {
            return null;
        }
        
        return {
            speed: windData.speed,
            direction: windData.direction,
            gust: windData.gust
        };
    }
    
    /**
     * Assess severe weather risks
     * @param {Object} forecast - Forecast data
     * @returns {Object} Risk assessment summary
     */
    static assessSevereWeatherRisk(forecast) {
        const risks = forecast.risk_assessment;
        const riskLevels = ['minimal', 'low', 'moderate', 'high', 'extreme'];
        
        // Find maximum risk level
        const maxRiskIndex = Math.max(
            ...Object.values(risks).map(level => riskLevels.indexOf(level))
        );
        const overallRisk = riskLevels[maxRiskIndex];
        
        // Find primary concerns
        const primaryConcerns = Object.entries(risks)
            .filter(([, level]) => ['high', 'extreme'].includes(level))
            .map(([riskType]) => riskType);
        
        return {
            overallRisk,
            primaryConcerns,
            details: risks
        };
    }
}

/**
 * Example usage and demonstrations
 */
async function main() {
    // Get API token from environment or use default
    const apiToken = process.env.WEATHER_API_TOKEN;
    if (!apiToken) {
        console.error('❌ Please set WEATHER_API_TOKEN environment variable');
        console.error('   export WEATHER_API_TOKEN="your_token_here"');
        process.exit(1);
    }
    
    // Create client with custom configuration
    const client = new AdelaideWeatherClient(apiToken, {
        baseUrl: process.env.WEATHER_API_BASE_URL || 'https://api.adelaideweather.example.com',
        timeout: 30000,
        maxRetries: 3,
        enableLogging: true
    });
    
    try {
        console.log('🔍 Checking API health...');
        const health = await client.getHealth();
        
        if (!health.ready) {
            console.log('⚠️  API is not ready. Waiting for system to start...');
            const isReady = await client.waitForReady(60000); // Wait up to 1 minute
            if (!isReady) {
                console.log('❌ API did not become ready in time');
                return;
            }
        }
        
        console.log('✅ API is healthy and ready');
        
        // Example 1: Basic forecast
        console.log('\n📊 Getting 24-hour forecast...');
        const forecast = await client.getForecast();
        ForecastAnalyzer.printForecastSummary(forecast);
        
        // Example 2: Extended forecast with weather variables
        console.log('🌦️  Getting extended forecast with weather variables...');
        const extendedForecast = await client.getForecast({
            horizon: '48h',
            variables: ['t2m', 'u10', 'v10', 'msl', 'cape', 'tp6h']
        });
        
        // Analyze severe weather risk
        const riskAssessment = ForecastAnalyzer.assessSevereWeatherRisk(extendedForecast);
        console.log(`Overall risk level: ${riskAssessment.overallRisk}`);
        if (riskAssessment.primaryConcerns.length > 0) {
            console.log(`Primary concerns: ${riskAssessment.primaryConcerns.join(', ')}`);
        }
        
        // Example 3: Temperature trend analysis
        console.log('\n🌡️  Analyzing temperature trends...');
        const horizons = ['6h', '12h', '24h', '48h'];
        const temps = [];
        
        for (const horizon of horizons) {
            try {
                const tempForecast = await client.getForecast({
                    horizon,
                    variables: ['t2m']
                });
                
                const tempInfo = ForecastAnalyzer.extractTemperatureInfo(tempForecast);
                if (tempInfo) {
                    temps.push([horizon, tempInfo.temperature]);
                    console.log(
                        `${horizon.padStart(4)}: ${tempInfo.temperature.toFixed(1).padStart(5)}°C ` +
                        `(confidence: ${(tempInfo.confidence * 100).toFixed(1).padStart(5)}%)`
                    );
                }
            } catch (error) {
                console.log(`${horizon.padStart(4)}: Error - ${error.message}`);
            }
        }
        
        // Example 4: Wind analysis
        console.log('\n💨 Wind analysis...');
        const windForecast = await client.getForecast({
            horizon: '12h',
            variables: ['u10', 'v10']
        });
        
        const windInfo = ForecastAnalyzer.extractWindInfo(windForecast);
        if (windInfo) {
            console.log(`Wind speed: ${windInfo.speed.toFixed(1)} m/s`);
            console.log(`Wind direction: ${windInfo.direction.toFixed(0)}°`);
        }
        
        // Example 5: Historical analogs (if available)
        try {
            console.log('\n📚 Exploring historical analogs...');
            const analogs = await client.getAnalogs('24h');
            console.log(`Found ${analogs.top_analogs.length} similar patterns`);
            
            analogs.top_analogs.slice(0, 3).forEach((analog, i) => {
                console.log(`  ${i + 1}. ${analog.date} (similarity: ${(analog.similarity_score * 100).toFixed(1)}%)`);
                console.log(`     ${analog.outcome_narrative}`);
            });
        } catch (error) {
            console.log(`Analog data not available: ${error.message}`);
        }
        
    } catch (error) {
        if (error instanceof RateLimitError) {
            console.log(`⚠️  Rate limit exceeded. Retry after ${error.retryAfter} seconds`);
        } else if (error instanceof AuthenticationError) {
            console.log(`❌ Authentication failed: ${error.message}`);
            console.log('   Please check your API token');
        } else if (error instanceof ValidationError) {
            console.log(`❌ Validation error: ${error.message}`);
        } else if (error instanceof ServiceUnavailableError) {
            console.log(`⚠️  Service unavailable: ${error.message}`);
            console.log('   The forecasting system may be starting up');
        } else if (error instanceof WeatherAPIError) {
            console.log(`❌ API error: ${error.message}`);
            if (error.correlationId) {
                console.log(`   Correlation ID: ${error.correlationId}`);
            }
        } else {
            console.log(`❌ Unexpected error: ${error.message}`);
            console.error(error);
        }
    }
}

// Export for Node.js
if (typeof module !== 'undefined' && module.exports) {
    module.exports = {
        AdelaideWeatherClient,
        ForecastAnalyzer,
        WeatherAPIError,
        AuthenticationError,
        RateLimitError,
        ValidationError,
        ServiceUnavailableError
    };
}

// Run main function if this is the main module
if (typeof require !== 'undefined' && require.main === module) {
    main().catch(console.error);
}

// Export for browsers
if (typeof window !== 'undefined') {
    window.AdelaideWeatherClient = AdelaideWeatherClient;
    window.ForecastAnalyzer = ForecastAnalyzer;
}