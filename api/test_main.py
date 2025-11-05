#!/usr/bin/env python3
"""
Standalone test version of the FastAPI application 
This removes the core forecasting system dependencies for testing
"""

import time
import random
import math
import re
import html
from datetime import datetime, timezone
from typing import Optional, Dict, Any, List

from fastapi import FastAPI, HTTPException, Depends, Request, status, Query
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, Response
from pydantic import BaseModel, Field, field_validator
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.util import get_remote_address
from slowapi.errors import RateLimitExceeded
import structlog
from prometheus_client import Counter, Histogram, generate_latest, CONTENT_TYPE_LATEST
from performance_middleware import performance_middleware, get_performance_stats

# Structured logging configuration
structlog.configure(
    processors=[
        structlog.stdlib.filter_by_level,
        structlog.stdlib.add_logger_name,
        structlog.stdlib.add_log_level,
        structlog.stdlib.PositionalArgumentsFormatter(),
        structlog.processors.TimeStamper(fmt="iso"),
        structlog.processors.StackInfoRenderer(),
        structlog.processors.format_exc_info,
        structlog.processors.UnicodeDecoder(),
        structlog.processors.JSONRenderer()
    ],
    context_class=dict,
    logger_factory=structlog.stdlib.LoggerFactory(),
    wrapper_class=structlog.stdlib.BoundLogger,
    cache_logger_on_first_use=True,
)

logger = structlog.get_logger()

# Rate limiting
limiter = Limiter(key_func=get_remote_address)

# Metrics
REQUEST_COUNT = Counter('api_requests_total', 'Total API requests', ['method', 'endpoint', 'status'])
REQUEST_DURATION = Histogram('response_duration_seconds', 'Forecast request duration')
SECURITY_VIOLATIONS = Counter('security_violations_total', 'Total security violations', ['violation_type'])
VALIDATION_ERRORS = Counter('validation_errors_total', 'Total validation errors', ['error_type'])

# Mock variables data
VARIABLE_ORDER = [
    "t2m", "u10", "v10", "z500", "t850", "q850", "u850", "v850", "cape"
]

VARIABLE_SPECS = {
    "t2m": {"name": "2m Temperature", "unit": "°C", "precision": 1},
    "u10": {"name": "10m U-Wind", "unit": "m/s", "precision": 1},
    "v10": {"name": "10m V-Wind", "unit": "m/s", "precision": 1},
    "z500": {"name": "500hPa Height", "unit": "m", "precision": 0},
    "t850": {"name": "850hPa Temperature", "unit": "°C", "precision": 1},
    "q850": {"name": "850hPa Humidity", "unit": "kg/kg", "precision": 6},
    "u850": {"name": "850hPa U-Wind", "unit": "m/s", "precision": 1},
    "v850": {"name": "850hPa V-Wind", "unit": "m/s", "precision": 1},
    "cape": {"name": "CAPE", "unit": "J/kg", "precision": 0}
}

# Enhanced Pydantic models with validation
class VariableData(BaseModel):
    value: float = Field(..., description="Forecast value")
    p05: float = Field(..., description="5th percentile (lower bound)")
    p95: float = Field(..., description="95th percentile (upper bound)")
    confidence: float = Field(..., ge=0, le=100, description="Confidence percentage")
    available: bool = Field(True, description="Data availability")
    analog_count: Optional[int] = Field(None, description="Number of analogs used")
    
    @field_validator('value', 'p05', 'p95')
    @classmethod
    def validate_numeric_values(cls, v):
        """Validate numeric values are reasonable."""
        if not isinstance(v, (int, float)):
            raise ValueError("Value must be numeric")
        if abs(v) > 1e10:  # Prevent extreme values
            raise ValueError("Value out of reasonable range")
        return v
    
    @field_validator('analog_count')
    @classmethod
    def validate_analog_count(cls, v):
        """Validate analog count is reasonable."""
        if v is not None:
            if not isinstance(v, int) or v < 0 or v > 10000:
                raise ValueError("Analog count must be between 0 and 10000")
        return v

class WindData(BaseModel):
    speed: float = Field(..., ge=0, description="Wind speed in m/s")
    direction: int = Field(..., ge=0, le=360, description="Wind direction in degrees")
    
    @field_validator('speed')
    @classmethod
    def validate_wind_speed(cls, v):
        """Validate wind speed is reasonable."""
        if not isinstance(v, (int, float)):
            raise ValueError("Wind speed must be numeric")
        if v < 0 or v > 200:  # Max hurricane wind speeds
            raise ValueError("Wind speed must be between 0 and 200 m/s")
        return v
    
    @field_validator('direction')
    @classmethod
    def validate_wind_direction(cls, v):
        """Validate wind direction is in valid range."""
        if not isinstance(v, (int, float)):
            raise ValueError("Wind direction must be numeric")
        if v < 0 or v >= 360:
            raise ValueError("Wind direction must be between 0 and 360 degrees")
        return v

class ForecastResponse(BaseModel):
    horizon: str = Field(..., description="Forecast horizon")
    variables: Dict[str, VariableData] = Field(..., description="Variable forecasts")
    wind10m: Optional[WindData] = Field(None, description="10m wind summary")
    timestamp: str = Field(..., description="Forecast generation time")
    latency_ms: int = Field(..., description="Response latency in milliseconds")

class HealthResponse(BaseModel):
    status: str = Field(..., description="Service status")
    timestamp: str = Field(..., description="Health check time")
    uptime_seconds: float = Field(..., description="Service uptime")
    version: str = Field(..., description="Service version")
    dependencies: Dict[str, str] = Field(..., description="Dependency status")

# Security utilities for testing
def sanitize_string(value: str, max_length: int = 1000) -> str:
    """Sanitize string input to prevent XSS and injection attacks."""
    if not isinstance(value, str):
        raise ValueError("Input must be a string")
    
    if len(value) > max_length:
        raise ValueError(f"Input too long (max {max_length} characters)")
    
    # HTML escape
    sanitized = html.escape(value.strip())
    
    # Remove null bytes and control characters
    sanitized = ''.join(char for char in sanitized if ord(char) >= 32 or char in '\t\n\r')
    
    # Check for suspicious patterns
    suspicious_patterns = [
        re.compile(r'<script[^>]*>.*?</script>', re.IGNORECASE | re.DOTALL),
        re.compile(r'javascript:', re.IGNORECASE),
        re.compile(r'(\bunion\b|\bselect\b|\binsert\b|\bupdate\b|\bdelete\b)', re.IGNORECASE),
    ]
    
    for pattern in suspicious_patterns:
        if pattern.search(sanitized):
            raise ValueError("Potentially malicious input detected")
    
    return sanitized

def validate_horizon(horizon: str) -> bool:
    """Validate horizon parameter with security checks."""
    try:
        sanitized = sanitize_string(horizon, 10)
        return sanitized in ["6h", "12h", "24h", "48h"]
    except ValueError:
        return False

def validate_variables(vars_str: str) -> List[str]:
    """Validate variables parameter with security checks."""
    if not vars_str:
        return []
    
    try:
        sanitized = sanitize_string(vars_str, 500)
        variables = [v.strip() for v in sanitized.split(',') if v.strip()]
        
        if len(variables) > 20:
            raise ValueError("Too many variables requested (max 20)")
        
        # Validate each variable name
        for var in variables:
            if len(var) > 20 or not re.match(r'^[a-zA-Z0-9_]+$', var):
                raise ValueError(f"Invalid variable name: {var}")
            if var not in VARIABLE_SPECS:
                raise ValueError(f"Unknown variable: {var}")
        
        return variables
    except ValueError:
        raise

def validate_token_format(token: str) -> bool:
    """Validate token format for security."""
    if not isinstance(token, str):
        return False
    if len(token) < 8 or len(token) > 128:
        return False
    if not re.match(r'^[a-zA-Z0-9\-_.]+$', token):
        return False
    return True

# Security
security = HTTPBearer(auto_error=False)

def verify_token(credentials: Optional[HTTPAuthorizationCredentials] = Depends(security)) -> str:
    """Verify API token with enhanced validation"""
    if not credentials or not credentials.credentials:
        SECURITY_VIOLATIONS.labels(violation_type="missing_token").inc()
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not authenticated",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    token = credentials.credentials
    if not validate_token_format(token):
        SECURITY_VIOLATIONS.labels(violation_type="invalid_token_format").inc()
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid authentication token format",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    expected_token = "dev-token-change-in-production"
    if token != expected_token:
        SECURITY_VIOLATIONS.labels(violation_type="wrong_token").inc()
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid authentication token",
            headers={"WWW-Authenticate": "Bearer"},
        )
    return token

# FastAPI app
app = FastAPI(
    title="Adelaide Weather Forecasting API (Test)",
    description="Test version of the production-ready weather forecasting API",
    version="1.0.0-test",
    docs_url="/docs",
    redoc_url="/redoc"
)

# Add rate limiting error handler
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

# CORS configuration
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000"],
    allow_credentials=True,
    allow_methods=["GET", "POST"],
    allow_headers=["*"],
)

# Performance middleware for caching and optimization
app.middleware("http")(performance_middleware)

# Startup time
startup_time = time.time()

def generate_mock_forecast(horizon: str, variables: List[str]) -> Dict[str, Any]:
    """Generate mock forecast data for testing"""
    result = {}
    
    for var in variables:
        if var in VARIABLE_SPECS:
            # Generate realistic mock data
            if var == "t2m":
                base_temp = 20.0 + random.uniform(-5, 5)
                uncertainty = random.uniform(0.5, 2.0)
            elif var in ["u10", "v10"]:
                base_temp = random.uniform(-10, 10)
                uncertainty = random.uniform(0.5, 3.0)
            else:
                base_temp = random.uniform(0, 100)
                uncertainty = random.uniform(1, 5)
                
            result[var] = VariableData(
                value=round(base_temp, VARIABLE_SPECS[var]["precision"]),
                p05=round(base_temp - uncertainty, VARIABLE_SPECS[var]["precision"]),
                p95=round(base_temp + uncertainty, VARIABLE_SPECS[var]["precision"]),
                confidence=random.uniform(45, 85),
                available=True,
                analog_count=random.randint(30, 60)
            )
    
    return result

@app.get("/health", response_model=HealthResponse)
async def health_check():
    """Health check endpoint"""
    return HealthResponse(
        status="healthy",
        timestamp=datetime.now(timezone.utc).isoformat(),
        uptime_seconds=time.time() - startup_time,
        version="1.0.0-test",
        dependencies={
            "api": "healthy",
            "forecasting_system": "mock",
            "database": "mock"
        }
    )

@app.get("/forecast", response_model=ForecastResponse)
@limiter.limit("60/minute")
async def get_forecast(
    request: Request,
    horizon: str = Query("24h", description="Forecast horizon (6h, 12h, 24h, 48h)"),
    vars: Optional[str] = Query(None, description="Comma-separated variables (default: all)"),
):
    """Get weather forecast with mock data and comprehensive validation"""
    start_time = time.time()
    
    try:
        # Comprehensive input validation
        if not validate_horizon(horizon):
            VALIDATION_ERRORS.labels(error_type="invalid_horizon").inc()
            raise HTTPException(
                status_code=400,
                detail=f"Invalid horizon format or value: {horizon}"
            )
        
        # Validate and parse variables
        if vars:
            try:
                requested_vars = validate_variables(vars)
            except ValueError as e:
                VALIDATION_ERRORS.labels(error_type="invalid_variables").inc()
                raise HTTPException(
                    status_code=400,
                    detail=f"Invalid variables parameter: {str(e)}"
                )
        else:
            requested_vars = list(VARIABLE_SPECS.keys())
        
        # Additional business logic validation
        if len(requested_vars) == 0:
            VALIDATION_ERRORS.labels(error_type="no_variables").inc()
            raise HTTPException(
                status_code=400,
                detail="At least one variable must be requested"
            )
        
        # Authenticate after validation so malformed inputs surface as 400 first
        credentials = await security(request)
        verify_token(credentials)

        # Log the validated request
        logger.info(
            "validated_forecast_request",
            horizon=horizon,
            variables=requested_vars,
            variable_count=len(requested_vars),
            client_ip=request.client.host if request.client else None
        )
        
        # Generate real forecast using forecasting adapter  
        from forecast_adapter import ForecastAdapter
        adapter = ForecastAdapter()
        forecast_result = adapter.forecast_with_uncertainty(horizon, requested_vars)
        
        # Convert to expected format
        variables = {}
        for var in requested_vars:
            if var in forecast_result:
                result = forecast_result[var]
                variables[var] = VariableResult(
                    value=result["value"],
                    p05=result["p05"], 
                    p95=result["p95"],
                    confidence=result["confidence"],
                    available=result["available"],
                    analog_count=result.get("analog_count", 0)
                )
        
        # Calculate wind if both u10 and v10 are present
        wind10m = None
        if "u10" in variables and "v10" in variables:
            u = variables["u10"].value
            v = variables["v10"].value
            speed = (u**2 + v**2)**0.5
            direction = int((270 - (180/3.14159) * math.atan2(v, u)) % 360)
            wind10m = WindData(speed=round(speed, 1), direction=direction)
        
        latency_ms = int((time.time() - start_time) * 1000)
        
        return ForecastResponse(
            horizon=horizon,
            variables=variables,
            wind10m=wind10m,
            timestamp=datetime.now(timezone.utc).isoformat(),
            latency_ms=latency_ms
        )
    
    except HTTPException:
        raise
    except Exception as e:
        # Log unexpected errors
        logger.error(
            "forecast_error",
            error_type=type(e).__name__,
            error_message=str(e),
            horizon=horizon,
            variables=vars,
            client_ip=request.client.host if request.client else None
        )
        
        # Return sanitized error message
        raise HTTPException(
            status_code=500,
            detail="Internal server error occurred during forecast generation"
        )

@app.get("/metrics")
async def metrics():
    """Prometheus metrics endpoint"""
    return Response(generate_latest(), media_type=CONTENT_TYPE_LATEST)

@app.get("/performance")
async def performance_stats():
    """Performance optimization statistics"""
    stats = get_performance_stats()
    return {
        "performance": stats,
        "targets": {
            "response_time_ms": 100,
            "cache_hit_rate_target": 60,
            "compression_savings_target": 30
        },
        "timestamp": datetime.now(timezone.utc).isoformat()
    }

@app.get("/")
async def root():
    """API root endpoint"""
    return {
        "service": "Adelaide Weather Forecasting API (Test)",
        "version": "1.0.0-test",
        "status": "operational",
        "docs": "/docs",
        "health": "/health"
    }

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
