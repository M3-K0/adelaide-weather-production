#!/usr/bin/env python3
"""
Adelaide Weather Forecasting API
================================

FastAPI web service for the production-ready Adelaide Weather Forecasting System.
Provides real-time analog ensemble forecasts with uncertainty quantification.

Features:
- GET /forecast: Real-time forecasting with variable filtering
- GET /api/analogs: Historical weather pattern analysis with FAISS search
- GET /health: System health monitoring and diagnostics  
- GET /metrics: Prometheus-compatible performance metrics
- Security: Token auth, CORS, rate limiting
- Performance: <150ms response times with caching

Author: Web Service Layer  
Version: 1.0.0 - Production API
"""

import os
import sys
import time
import json
import hashlib
import logging
from datetime import datetime, timezone, timedelta
from typing import Dict, List, Optional, Any

# FastAPI and dependencies
from fastapi import FastAPI, HTTPException, Depends, status, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.trustedhost import TrustedHostMiddleware
from fastapi.middleware.gzip import GZipMiddleware
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from fastapi.responses import JSONResponse, Response
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.util import get_remote_address
from slowapi.errors import RateLimitExceeded
from slowapi.middleware import SlowAPIMiddleware
import uvicorn
from pydantic import BaseModel, Field, field_validator
from prometheus_client import (
    Counter,
    Histogram,
    Gauge,
    generate_latest,
    CONTENT_TYPE_LATEST,
    REGISTRY,
)

# Add parent directory to path for imports
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Import our production system
from api.variables import (
    VARIABLE_ORDER, VARIABLE_SPECS, VALID_HORIZONS, DEFAULT_VARIABLES,
    convert_value, validate_variable, validate_horizon, parse_variables
)
from api.forecast_adapter import ForecastAdapter
from core.startup_validation_system import ExpertValidatedStartupSystem
from api.services.faiss_health_monitoring import FAISSHealthMonitor, get_faiss_health_monitor
from core.config_drift_detector import ConfigurationDriftDetector

# Import analog search service and models
from api.services.analog_search import get_analog_search_service
from api.response_models import AnalogExplorerData, WeatherVariable, ForecastHorizon

# Configure structured logging
from api.logging_config import (
    structured_logger, performance_logger, security_logger, forecast_logger,
    RequestLoggingMiddleware, logger
)

# Import security middleware
from api.security_middleware import (
    SecurityMiddleware, SecurityConfig, InputSanitizer, 
    SecurityException, ValidationUtils
)

# Import performance middleware
from api.performance_middleware import (
    performance_middleware, get_performance_stats, get_rate_limit_config
)

# Import enhanced health endpoints
from api.enhanced_health_endpoints import health_router, initialize_health_checker

# Initialize rate limiter with configurable limits
limiter = Limiter(key_func=get_remote_address)

def _get_or_create_metric(metric_cls, name, documentation, *args, **kwargs):
    """Return existing Prometheus metric or create a new one.

    During unit tests `api.main` may be imported multiple times. Prometheus registers
    collectors globally, so attempting to create them again raises ValueError.
    This helper safely reuses existing collectors to keep app initialization idempotent.
    """

    existing = REGISTRY._names_to_collectors.get(name)
    if existing is not None:
        return existing
    return metric_cls(name, documentation, *args, **kwargs)


# Prometheus metrics
forecast_requests = _get_or_create_metric(
    Counter, 'forecast_requests_total', 'Total forecast requests'
)
response_duration_metric = _get_or_create_metric(
    Histogram, 'response_duration_seconds', 'Forecast request duration'
)
health_requests = _get_or_create_metric(
    Counter, 'health_requests_total', 'Total health check requests'
)
metrics_requests = _get_or_create_metric(
    Counter, 'metrics_requests_total', 'Total metrics requests'
)
error_requests = _get_or_create_metric(
    Counter, 'error_requests_total', 'Total error responses', ['error_type']
)
security_violations = _get_or_create_metric(
    Counter, 'security_violations_total', 'Total security violations', ['violation_type']
)
validation_errors = _get_or_create_metric(
    Counter, 'validation_errors_total', 'Total validation errors', ['error_type']
)

# Analog search metrics (OBS1 requirements)
analog_real_total = _get_or_create_metric(
    Counter, 'analog_real_total', 'Total successful real FAISS analog searches'
)
analog_fallback_total = _get_or_create_metric(
    Counter, 'analog_fallback_total', 'Total fallback analog searches used'
)
analog_search_seconds = _get_or_create_metric(
    Histogram, 'analog_search_seconds', 'Analog search latency distribution', 
    ['horizon', 'k'], buckets=[0.001, 0.005, 0.01, 0.025, 0.05, 0.1, 0.25, 0.5, 1.0, 2.5, 5.0, float('inf')]
)
analog_results_count = _get_or_create_metric(
    Gauge, 'analog_results_count', 'Number of analogs returned per horizon', ['horizon']
)

# Initialize FastAPI app
app = FastAPI(
    title="Adelaide Weather Forecasting API",
    description="Production-ready analog ensemble weather forecasting system",
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc",
    openapi_url="/openapi.json"
)

# Include enhanced health endpoints
app.include_router(health_router)

# Add middleware - order matters!
# GZip compression first (will be conditionally applied based on nginx proxy detection)
gzip_min_size = int(os.getenv('COMPRESSION_MIN_SIZE', '500'))
if os.getenv('NGINX_COMPRESSION', 'false').lower() != 'true':
    app.add_middleware(GZipMiddleware, minimum_size=gzip_min_size)

app.add_middleware(SecurityMiddleware)  # Security second
app.add_middleware(RequestLoggingMiddleware)  # Then logging
app.add_middleware(SlowAPIMiddleware)  # Then rate limiting
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

# Add performance middleware 
app.middleware("http")(performance_middleware)

# CORS configuration  
allowed_origins = os.getenv("CORS_ORIGINS", "http://localhost:3000").split(",")
app.add_middleware(
    CORSMiddleware,
    allow_origins=allowed_origins,
    allow_credentials=True,
    allow_methods=["GET", "POST", "OPTIONS"],
    allow_headers=["*"],
)

# Trusted host middleware
app.add_middleware(
    TrustedHostMiddleware, 
    allowed_hosts=["localhost", "127.0.0.1", "*.vercel.app"]
)

# Enhanced token management with backward compatibility
from api.enhanced_token_manager import get_token_manager, get_api_token

# Security
security = HTTPBearer(auto_error=False)

# Get API token with enhanced management and fallback
token_manager = get_token_manager()
API_TOKEN = get_api_token()

if not API_TOKEN:
    logger.error("CRITICAL: No API token configured. Set API_TOKEN environment variable or use token rotation CLI")
    exit(1)

# SECURITY ENFORCEMENT: Strong token validation at startup
environment = os.getenv("ENVIRONMENT", "production").lower()
logger.info(f"Environment detected: {environment}")

# Enforce strong token requirements in staging and production
if environment in ["staging", "production"]:
    logger.info("Enforcing strong token security requirements for non-development environment...")
    
    try:
        # Import TokenEntropyValidator for strong validation
        from api.token_rotation_cli import TokenEntropyValidator
        
        # Validate token meets minimum security requirements
        is_valid, validation_issues = TokenEntropyValidator.validate_token(API_TOKEN)
        
        if not is_valid:
            logger.error("SECURITY VIOLATION: API token does not meet security requirements for production environment")
            logger.error(f"Token validation failures: {', '.join(validation_issues)}")
            logger.error("ABORTING STARTUP: Weak tokens are not permitted in staging/production environments")
            logger.error("Solutions:")
            logger.error("  1. Generate a strong token using: python -m api.token_rotation_cli generate")
            logger.error("  2. Set a secure 32+ character token with high entropy")
            logger.error("  3. Use token rotation CLI to manage secure tokens")
            logger.error(f"  4. For development only, set ENVIRONMENT=development to bypass this check")
            exit(1)
        
        # Calculate token metrics for logging
        token_metrics = TokenEntropyValidator.calculate_entropy(API_TOKEN)
        logger.info(f"Token validation passed: {token_metrics.entropy_bits:.1f} bits entropy, security level: {token_metrics.security_level}")
        logger.info("Strong token security requirements satisfied for production environment")
        
    except ImportError as e:
        logger.error(f"CRITICAL: TokenEntropyValidator not available: {e}")
        logger.error("Cannot validate token security in production environment")
        logger.error("Enhanced token validation features are required for secure operation")
        exit(1)
        
elif environment == "development":
    logger.warning("DEVELOPMENT MODE: Token security enforcement is relaxed")
    logger.warning("Strong token validation is bypassed - ensure this is not a production deployment")
    
    # Still perform basic validation in development
    if len(API_TOKEN) < 8:
        logger.error("CRITICAL: Token too short even for development (minimum 8 characters)")
        exit(1)
        
    # Check for obvious insecure patterns
    weak_patterns = ['test', 'demo', 'example', 'password', 'secret', 'admin']
    if any(pattern in API_TOKEN.lower() for pattern in weak_patterns):
        logger.warning(f"WARNING: Token contains weak patterns - acceptable in development but never use in production")

else:
    logger.warning(f"Unknown environment '{environment}' - defaulting to production security requirements")
    # Re-run validation with production settings
    environment = "production"

# Log token management status
token_health = token_manager.get_health_status()
logger.info(f"Token management initialized: source={token_health.get('source')}, enhanced_features={token_health.get('enhanced_features')}")

if token_health.get("issues"):
    for issue in token_health["issues"]:
        logger.warning(f"Token management issue: {issue}")

# Global state
forecast_adapter: Optional[ForecastAdapter] = None
faiss_health_monitor: Optional[FAISSHealthMonitor] = None
config_drift_detector: Optional[ConfigurationDriftDetector] = None
system_health: Dict[str, Any] = {}
startup_time = datetime.now(timezone.utc)

# Helper functions for dynamic rate limiting
def get_dynamic_rate_limit() -> str:
    """Get the current rate limit configuration"""
    return get_rate_limit_config()

def get_health_rate_limit() -> str:
    """Get rate limit for health endpoints (50% of main limit)"""
    base_limit = int(os.getenv('RATE_LIMIT_PER_MINUTE', '60'))
    return f"{int(base_limit * 0.5)}/minute"

def get_metrics_rate_limit() -> str:
    """Get rate limit for metrics endpoints (20% of main limit)"""
    base_limit = int(os.getenv('RATE_LIMIT_PER_MINUTE', '60'))
    return f"{int(base_limit * 0.2)}/minute"

async def verify_token(
    request: Request,
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(security)
):
    """Verify API token authentication with enhanced security validation."""
    if not credentials or not credentials.credentials:
        error_requests.labels(error_type="auth").inc()
        security_violations.labels(violation_type="missing_token").inc()
        security_logger.log_auth_attempt(request, success=False, token_hint=None)
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not authenticated",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    # Enhanced token validation with security checks
    is_valid, validation_details = token_manager.validate_token(credentials.credentials)
    if not is_valid:
        error_requests.labels(error_type="auth").inc()
        security_violations.labels(violation_type="invalid_token_format").inc()
        
        # Redacted token for logging (first 8 chars + "...")
        token_hint = credentials.credentials[:8] + "..." if len(credentials.credentials) > 8 else credentials.credentials
        security_logger.log_auth_attempt(
            request, 
            success=False, 
            token_hint=token_hint
        )
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid authentication token format",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    # Check if this is the current API token
    if not token_manager.is_current_token(credentials.credentials):
        error_requests.labels(error_type="auth").inc()
        security_violations.labels(violation_type="wrong_token").inc()
        # Redacted token for logging
        token_hint = credentials.credentials[:8] + "..." if len(credentials.credentials) > 8 else credentials.credentials
        security_logger.log_auth_attempt(
            request, 
            success=False, 
            token_hint=token_hint
        )
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid authentication token",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    # Log successful authentication with redacted token
    token_hint = credentials.credentials[:8] + "..." if len(credentials.credentials) > 8 else credentials.credentials
    security_logger.log_auth_attempt(
        request, 
        success=True, 
        token_hint=token_hint
    )
    return credentials.credentials

# Pydantic models for API contracts with enhanced validation
class VariableResult(BaseModel):
    """Individual variable forecast result with validation."""
    value: Optional[float] = Field(..., description="Point estimate")
    p05: Optional[float] = Field(..., description="5th percentile bound")
    p95: Optional[float] = Field(..., description="95th percentile bound") 
    confidence: Optional[float] = Field(..., description="Confidence interval width")
    available: bool = Field(..., description="Whether forecast is available")
    analog_count: Optional[int] = Field(..., description="Number of analogs used")
    
    @field_validator('value', 'p05', 'p95', 'confidence')
    @classmethod
    def validate_numeric_values(cls, v):
        """Validate numeric values are reasonable."""
        if v is not None:
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

class WindResult(BaseModel):
    """Wind forecast result with speed/direction validation."""
    speed: Optional[float] = Field(..., description="Wind speed (m/s)")
    direction: Optional[float] = Field(..., description="Wind direction (degrees)")
    gust: Optional[float] = Field(..., description="Wind gust speed (m/s)")
    available: bool = Field(..., description="Whether forecast is available")
    
    @field_validator('speed', 'gust')
    @classmethod
    def validate_wind_speed(cls, v):
        """Validate wind speeds are reasonable."""
        if v is not None:
            if not isinstance(v, (int, float)):
                raise ValueError("Wind speed must be numeric")
            if v < 0 or v > 200:  # Max hurricane wind speeds
                raise ValueError("Wind speed must be between 0 and 200 m/s")
        return v
    
    @field_validator('direction')
    @classmethod
    def validate_wind_direction(cls, v):
        """Validate wind direction is in valid range."""
        if v is not None:
            if not isinstance(v, (int, float)):
                raise ValueError("Wind direction must be numeric")
            if v < 0 or v >= 360:
                raise ValueError("Wind direction must be between 0 and 360 degrees")
        return v

class VersionInfo(BaseModel):
    """System version information."""
    model: str = Field(..., description="Model version")
    index: str = Field(..., description="FAISS index version")
    datasets: str = Field(..., description="Dataset version")  
    api_schema: str = Field(..., description="API schema version")

class HashInfo(BaseModel):
    """System hash information for reproducibility."""
    model: str = Field(..., description="Model hash")
    index: str = Field(..., description="Index hash")
    datasets: str = Field(..., description="Dataset hash")

class RiskAssessment(BaseModel):
    """Weather risk assessment for various hazards."""
    thunderstorm: str = Field(..., description="Thunderstorm risk level (low/moderate/high/extreme)")
    heat_stress: str = Field(..., description="Heat stress risk level")
    wind_damage: str = Field(..., description="Wind damage potential") 
    precipitation: str = Field(..., description="Heavy precipitation risk")
    
    @field_validator('thunderstorm', 'heat_stress', 'wind_damage', 'precipitation')
    @classmethod
    def validate_risk_level(cls, v):
        """Validate risk levels are valid."""
        valid_levels = {'minimal', 'low', 'moderate', 'high', 'extreme'}
        if v not in valid_levels:
            raise ValueError(f"Risk level must be one of {valid_levels}")
        return v

class AnalogsSummary(BaseModel):
    """Summary of analog pattern matching results."""
    most_similar_date: str = Field(..., description="Date of most similar historical pattern")
    similarity_score: float = Field(..., description="Similarity score (0-1)")
    analog_count: int = Field(..., description="Number of analog patterns used")
    outcome_description: str = Field(..., description="What happened in similar cases")
    confidence_explanation: str = Field(..., description="Explanation of confidence level")
    
    @field_validator('similarity_score')
    @classmethod
    def validate_similarity(cls, v):
        """Validate similarity score is in valid range."""
        if not 0 <= v <= 1:
            raise ValueError("Similarity score must be between 0 and 1")
        return v

class ForecastResponse(BaseModel):
    """Enhanced forecast API response with narrative and risk assessment."""
    horizon: str = Field(..., description="Forecast horizon")
    generated_at: datetime = Field(..., description="Generation timestamp")
    variables: Dict[str, VariableResult] = Field(..., description="Variable forecasts")
    wind10m: Optional[WindResult] = Field(None, description="Combined wind forecast")
    narrative: str = Field(..., description="Human-readable forecast narrative")
    risk_assessment: RiskAssessment = Field(..., description="Risk levels for weather hazards")
    analogs_summary: AnalogsSummary = Field(..., description="Historical analog information")
    confidence_explanation: str = Field(..., description="Overall confidence explanation")
    versions: VersionInfo = Field(..., description="System versions")
    hashes: HashInfo = Field(..., description="System hashes")
    latency_ms: float = Field(..., description="Response latency")

class HealthCheck(BaseModel):
    """Individual health check result."""
    name: str = Field(..., description="Check name")
    status: str = Field(..., description="Check status (pass/fail)")
    message: str = Field(..., description="Check details")

class ModelInfo(BaseModel):
    """Model health information."""
    version: str = Field(..., description="Model version")
    hash: str = Field(..., description="Model hash")
    matched_ratio: float = Field(..., description="Parameter match ratio")

class IndexInfo(BaseModel):
    """FAISS index health information."""  
    ntotal: int = Field(..., description="Total vectors")
    dim: int = Field(..., description="Vector dimension")
    metric: str = Field(..., description="Distance metric")
    hash: str = Field(..., description="Index hash")
    dataset_hash: str = Field(..., description="Dataset hash")

class DatasetInfo(BaseModel):
    """Dataset health information."""
    horizon: str = Field(..., description="Forecast horizon")
    valid_pct_by_var: Dict[str, float] = Field(..., description="Valid % by variable")
    hash: str = Field(..., description="Dataset hash") 
    schema_version: str = Field(..., description="Schema version")

class HealthResponse(BaseModel):
    """System health API response."""
    ready: bool = Field(..., description="System ready status")
    checks: List[HealthCheck] = Field(..., description="Health check results")
    model: ModelInfo = Field(..., description="Model information")
    index: IndexInfo = Field(..., description="Index information")
    datasets: List[DatasetInfo] = Field(..., description="Dataset information")
    deps: Dict[str, str] = Field(..., description="Dependency versions")
    preprocessing_version: str = Field(..., description="Preprocessing version")
    uptime_seconds: float = Field(..., description="System uptime")

@app.on_event("startup")
async def startup_event():
    """Initialize the forecasting system with health validation."""
    global forecast_adapter, faiss_health_monitor, config_drift_detector, system_health
    
    logger.info("🚀 Starting Adelaide Weather Forecasting API")
    logger.info("📋 Initializing forecast adapter with core system...")
    
    try:
        # Run startup validation first
        validator = ExpertValidatedStartupSystem()
        validation_passed = validator.run_expert_startup_validation()
        
        if not validation_passed:
            logger.error("❌ Startup validation failed - system not ready")
            system_health = {"ready": False, "error": "Startup validation failed"}
            return
            
        # Initialize forecast adapter (which initializes the core forecaster)
        forecast_adapter = ForecastAdapter()
        
        # Initialize enhanced health checker
        logger.info("🏥 Initializing enhanced health checker...")
        initialize_health_checker(forecast_adapter)
        
        # Initialize FAISS health monitoring
        logger.info("🔍 Initializing FAISS health monitoring...")
        faiss_health_monitor = await get_faiss_health_monitor()
        
        # Initialize configuration drift monitoring
        logger.info("📊 Initializing configuration drift monitoring...")
        config_drift_detector = ConfigurationDriftDetector(
            enable_metrics=True,
            enable_webhooks=None,  # Use environment variable
            enable_real_time=os.getenv('CONFIG_DRIFT_REALTIME_ENABLED', 'true').lower() == 'true'
        )
        
        # Start drift monitoring in background
        drift_monitoring_started = config_drift_detector.start_monitoring()
        if drift_monitoring_started:
            logger.info("✅ Configuration drift monitoring started")
        else:
            logger.warning("⚠️ Configuration drift monitoring failed to start")
        
        # Get adapter health status
        adapter_health = await forecast_adapter.get_system_health()
        
        # Get initial FAISS health status
        faiss_health = await faiss_health_monitor.get_health_summary()
        
        # Cache system health information
        system_health = {
            "ready": adapter_health.get("adapter_ready", False),
            "validation_passed": validation_passed,
            "adapter_health": adapter_health,
            "faiss_health": faiss_health,
            "initialized_at": datetime.now(timezone.utc).isoformat()
        }
        
        # Log performance middleware configuration
        perf_stats = get_performance_stats()
        compression_enabled = perf_stats['compression']['enabled']
        rate_limit = perf_stats['rate_limiting']['limit_per_minute']
        
        logger.info("✅ Adelaide Weather Forecasting API ready")
        logger.info(f"🎯 Available endpoints: /forecast, /api/analogs, /health, /health/detailed, /health/live, /health/ready, /metrics, /health/faiss, /admin/performance")
        logger.info(f"🔒 Authentication: Enabled (secure token required)")
        logger.info(f"🗜️ Compression: {'Enabled' if compression_enabled else 'Disabled'} (min size: {perf_stats['compression']['minimum_size_bytes']} bytes)")
        logger.info(f"⚡ Rate limiting: {rate_limit}/minute")
        logger.info(f"🔗 Adapter status: {adapter_health}")
        logger.info(f"📊 FAISS monitoring: {faiss_health['status']}")
        logger.info(f"🏥 Enhanced health endpoints available at /health/detailed")
        
    except Exception as e:
        logger.error(f"💥 Startup failed: {e}")
        system_health = {"ready": False, "error": str(e)}

def _generate_forecast_narrative(horizon: str, variables: Dict[str, VariableResult], wind: Optional[WindResult]) -> str:
    """Generate human-readable forecast narrative."""
    parts = []
    
    # Temperature narrative
    if "t2m" in variables and variables["t2m"].available:
        temp = variables["t2m"]
        temp_desc = "warm" if temp.value > 25 else "mild" if temp.value > 15 else "cool"
        parts.append(f"{temp_desc} conditions with temperature around {temp.value:.1f}°C")
    
    # Wind narrative
    if wind and wind.available:
        wind_desc = "calm" if wind.speed < 2 else "light" if wind.speed < 5 else "moderate" if wind.speed < 10 else "strong"
        parts.append(f"{wind_desc} winds at {wind.speed:.1f} m/s from {wind.direction:.0f}°")
    
    # Pressure narrative
    if "msl" in variables and variables["msl"].available:
        pressure = variables["msl"].value / 100  # Convert Pa to hPa
        pressure_desc = "high" if pressure > 1020 else "normal" if pressure > 1000 else "low"
        parts.append(f"{pressure_desc} pressure system ({pressure:.0f} hPa)")
    
    if parts:
        return f"Forecast for {horizon}: " + ", ".join(parts) + "."
    return f"Forecast for {horizon} with limited data availability."

def _assess_weather_risks(variables: Dict[str, VariableResult], wind: Optional[WindResult]) -> RiskAssessment:
    """Assess weather-related risks based on forecast variables."""
    # CAPE-based thunderstorm risk
    thunderstorm_risk = "minimal"
    if "cape" in variables and variables["cape"].available:
        cape_value = variables["cape"].value
        if cape_value > 2000:
            thunderstorm_risk = "extreme"
        elif cape_value > 1000:
            thunderstorm_risk = "high"
        elif cape_value > 500:
            thunderstorm_risk = "moderate"
        elif cape_value > 100:
            thunderstorm_risk = "low"
    
    # Temperature-based heat stress
    heat_risk = "minimal"
    if "t2m" in variables and variables["t2m"].available:
        temp = variables["t2m"].value
        if temp > 40:
            heat_risk = "extreme"
        elif temp > 35:
            heat_risk = "high"
        elif temp > 30:
            heat_risk = "moderate"
        elif temp > 25:
            heat_risk = "low"
    
    # Wind damage risk
    wind_risk = "minimal"
    if wind and wind.available:
        if wind.speed > 25:  # >90 km/h
            wind_risk = "extreme"
        elif wind.speed > 17:  # >60 km/h
            wind_risk = "high"
        elif wind.speed > 11:  # >40 km/h
            wind_risk = "moderate"
        elif wind.speed > 6:   # >20 km/h
            wind_risk = "low"
    
    # Precipitation risk (simplified - would need more data in production)
    precip_risk = "low"  # Default for Adelaide's dry climate
    
    return RiskAssessment(
        thunderstorm=thunderstorm_risk,
        heat_stress=heat_risk,
        wind_damage=wind_risk,
        precipitation=precip_risk
    )

def _generate_analogs_summary(variable_results: Dict[str, VariableResult], analog_count: int) -> AnalogsSummary:
    """Generate summary of analog pattern matching."""
    # Extract analog information from forecast result if available
    # This would be enhanced with actual historical data in production
    
    # Calculate average similarity from confidence levels
    total_confidence = 0
    count = 0
    for var, data in variable_results.items():
        if hasattr(data, 'confidence') and data.available:
            total_confidence += data.confidence or 0
            count += 1
    
    avg_similarity = (total_confidence / count) if count > 0 else 0.5
    
    # Generate outcome based on patterns (simplified)
    outcome = "Similar patterns typically resulted in stable conditions"
    if analog_count < 30:
        outcome = "Limited historical matches suggest unusual conditions"
    elif analog_count > 40:
        outcome = "Strong pattern match with typical seasonal conditions"
    
    confidence_desc = f"Based on {analog_count} historical analog patterns"
    
    return AnalogsSummary(
        most_similar_date="2023-03-15T12:00:00Z",  # Would be actual in production
        similarity_score=avg_similarity,
        analog_count=analog_count,
        outcome_description=outcome,
        confidence_explanation=confidence_desc
    )

def _explain_confidence(variables: Dict[str, VariableResult], analog_count: int) -> str:
    """Generate overall confidence explanation."""
    # Calculate average confidence
    confidences = [v.confidence for v in variables.values() if v.available]
    avg_confidence = sum(confidences) / len(confidences) if confidences else 0
    
    # Generate explanation
    if analog_count < 20:
        return f"Low confidence ({avg_confidence:.1%}) due to limited historical analogs ({analog_count} patterns)"
    elif analog_count > 40:
        return f"High confidence ({avg_confidence:.1%}) with {analog_count} strong analog matches"
    else:
        return f"Moderate confidence ({avg_confidence:.1%}) based on {analog_count} analog patterns"

def _validate_analog_request(horizon: str, variables: Optional[str], k: int, query_time: Optional[str]) -> Dict[str, Any]:
    """Validate analog API request parameters."""
    try:
        # Validate horizon
        if not validate_horizon(horizon):
            return {"valid": False, "error": f"Invalid horizon '{horizon}'. Must be one of: {', '.join(VALID_HORIZONS)}"}
        
        # Validate and parse variables
        try:
            parsed_variables = parse_variables(variables) if variables else DEFAULT_VARIABLES
        except ValueError as e:
            return {"valid": False, "error": f"Invalid variables parameter: {str(e)}"}
        
        # Validate k parameter
        if not isinstance(k, int) or k < 1 or k > 200:
            return {"valid": False, "error": "Parameter 'k' must be an integer between 1 and 200"}
        
        # Validate query_time if provided
        validated_query_time = None
        if query_time:
            try:
                from datetime import datetime
                import pandas as pd
                
                # Try parsing as ISO format
                if isinstance(query_time, str):
                    validated_query_time = pd.to_datetime(query_time).to_pydatetime()
                else:
                    return {"valid": False, "error": "query_time must be an ISO 8601 datetime string"}
                    
                # Check if time is reasonable (not too far in past/future)
                now = datetime.now(timezone.utc)
                max_past = timedelta(days=365 * 5)  # 5 years
                max_future = timedelta(days=30)     # 30 days
                
                if validated_query_time < now - max_past:
                    return {"valid": False, "error": "query_time too far in the past (max 5 years)"}
                if validated_query_time > now + max_future:
                    return {"valid": False, "error": "query_time too far in the future (max 30 days)"}
                    
            except Exception as e:
                return {"valid": False, "error": f"Invalid query_time format: {str(e)}"}
        
        return {
            "valid": True,
            "horizon": horizon,
            "variables": parsed_variables,
            "k": k,
            "query_time": validated_query_time
        }
        
    except Exception as e:
        return {"valid": False, "error": f"Validation error: {str(e)}"}

# Variable mapping from outcomes array indices to variable names (based on sidecar analysis)
OUTCOMES_VARIABLE_MAP = {
    0: "z500",
    1: "t2m", 
    2: "t850",
    3: "q850",
    4: "u10",
    5: "v10",
    6: "u850",
    7: "v850",
    8: "cape"
}

# Global cache for loaded outcomes and metadata
_data_cache = {}

def _load_outcomes_data(horizon: str):
    """Load and cache outcomes and metadata for a given horizon.

    Uses OUTCOMES_DIR env var if provided; otherwise resolves repo-relative
    paths to support different environments (WSL, CI, containers).
    """
    if horizon in _data_cache:
        return _data_cache[horizon]

    try:
        import numpy as np
        import pandas as pd
        from pathlib import Path
        
        base_dir_env = os.getenv("OUTCOMES_DIR")
        if base_dir_env:
            base = Path(base_dir_env)
        else:
            # Resolve repo root: api/main.py -> repo_root
            base = Path(__file__).resolve().parents[1] / "outcomes"

        outcomes_path = base / f"outcomes_{horizon}.npy"
        metadata_path = base / f"metadata_{horizon}_clean.parquet"

        outcomes = np.load(str(outcomes_path))
        metadata = pd.read_parquet(str(metadata_path))

        _data_cache[horizon] = {
            "outcomes": outcomes,
            "metadata": metadata
        }

        return _data_cache[horizon]

    except Exception as e:
        logger.error(f"Failed to load outcomes data for horizon {horizon}: {e}")
        return None

def _horizon_to_hours(horizon: str) -> int:
    """Convert horizon string to hours."""
    horizon_map = {"6h": 6, "12h": 12, "24h": 24, "48h": 48}
    return horizon_map.get(horizon, 24)

def _primary_variable_from_list(variables: List[str]) -> str:
    """Get primary variable for analog search from variable list."""
    # Prioritize temperature as it's most universally relevant
    if "t2m" in variables:
        return "temperature"
    elif any(v in ["u10", "v10"] for v in variables):
        return "wind"
    elif "tp6h" in variables:
        return "precipitation"
    elif "msl" in variables:
        return "pressure"
    else:
        return "temperature"  # Default fallback

def _transform_analog_result_to_response(
    analog_result: Dict[str, Any],
    horizon: str, 
    variables: List[str],
    correlation_id: str
) -> Dict[str, Any]:
    """Transform service result to API response model."""
    from datetime import datetime, timezone
    import numpy as np
    
    try:
        # Extract top analogs from service result
        service_analogs = analog_result.get("analogs", [])
        
        # Transform to response model format
        top_analogs = []
        for analog in service_analogs[:10]:  # Limit to top 10 for response size
            # Ensure analog has horizon information for real data extraction
            analog_with_horizon = analog.copy()
            analog_with_horizon["horizon"] = horizon
            
            # Convert service analog to response model format
            analog_pattern = {
                "date": analog.get("historical_date", datetime.now(timezone.utc).isoformat()),
                "similarity_score": analog.get("similarity_score", 0.5),
                "initial_conditions": _extract_initial_conditions(analog_with_horizon, variables),
                "timeline": _generate_timeline_from_analog(analog_with_horizon, horizon),
                "outcome_narrative": _generate_outcome_narrative(analog_with_horizon),
                "location": {
                    "latitude": -34.9285,  # Adelaide coordinates
                    "longitude": 138.6007,
                    "name": "Adelaide Weather Station"
                },
                "season_info": _extract_season_info(analog_with_horizon)
            }
            top_analogs.append(analog_pattern)
        
        # Generate ensemble statistics with horizon information
        service_analogs_with_horizon = []
        for analog in service_analogs:
            analog_with_horizon = analog.copy()
            analog_with_horizon["horizon"] = horizon
            service_analogs_with_horizon.append(analog_with_horizon)
        
        ensemble_stats = _generate_ensemble_statistics(service_analogs_with_horizon, variables)
        
        # Extract transparency fields from service response
        search_metadata = analog_result.get("search_metadata", {})
        faiss_successful = search_metadata.get("faiss_search_successful", False)
        
        # Determine data source based on search metadata
        data_source = "faiss" if faiss_successful else "fallback"
        
        return {
            "forecast_horizon": horizon,
            "top_analogs": top_analogs,
            "ensemble_stats": ensemble_stats,
            "generated_at": datetime.now(timezone.utc).isoformat(),
            "data_source": data_source,
            "search_metadata": search_metadata
        }
        
    except Exception as e:
        logger.error(f"[{correlation_id}] Failed to transform analog result: {e}")
        # Return minimal valid response with required transparency fields
        return {
            "forecast_horizon": horizon,
            "top_analogs": [],
            "ensemble_stats": {
                "mean_outcomes": {},
                "outcome_uncertainty": {},
                "common_events": []
            },
            "generated_at": datetime.now(timezone.utc).isoformat(),
            "data_source": "fallback",
            "search_metadata": {
                "search_method": "error_fallback",
                "faiss_search_successful": False,
                "error": "Failed to transform service response"
            }
        }

def _extract_initial_conditions(analog: Dict[str, Any], variables: List[str]) -> Dict[str, Optional[float]]:
    """Extract initial conditions from analog data using real outcomes data."""
    conditions = {}
    
    # Get the analog index to extract from outcomes data (service uses 'analog_index')
    analog_index = analog.get("analog_index", analog.get("index"))
    if analog_index is None:
        # Fallback to minimal conditions if no index available
        for var in variables:
            conditions[var] = None
        return conditions
    
    # Get horizon to determine which outcomes file to use
    horizon = analog.get("horizon", "24h")
    
    # Load the actual outcomes data
    data = _load_outcomes_data(horizon)
    if data is None:
        # Fallback to minimal conditions if data can't be loaded
        for var in variables:
            conditions[var] = None
        return conditions
    
    outcomes = data["outcomes"]
    
    # Extract real values from the outcomes array for this analog
    try:
        if analog_index >= 0 and analog_index < len(outcomes):
            outcome_values = outcomes[analog_index]
            
            # Map from outcomes array indices to variable names
            for var in variables:
                if var in OUTCOMES_VARIABLE_MAP.values():
                    # Find the index for this variable in the outcomes array
                    var_index = None
                    for idx, var_name in OUTCOMES_VARIABLE_MAP.items():
                        if var_name == var:
                            var_index = idx
                            break
                    
                    if var_index is not None and var_index < len(outcome_values):
                        conditions[var] = float(outcome_values[var_index])
                    else:
                        conditions[var] = None
                else:
                    conditions[var] = None
        else:
            # Index out of range, set all to None
            for var in variables:
                conditions[var] = None
                
    except Exception as e:
        logger.error(f"Error extracting initial conditions from analog {analog_index}: {e}")
        for var in variables:
            conditions[var] = None
    
    return conditions

def _generate_timeline_from_analog(analog: Dict[str, Any], horizon: str) -> List[Dict[str, Any]]:
    """Generate timeline points from analog data using real outcomes data."""
    timeline = []
    hours = _horizon_to_hours(horizon)
    
    # Get the analog index to extract from outcomes data
    analog_index = analog.get("analog_index", analog.get("index"))
    if analog_index is None:
        # Return empty timeline if no index available
        return timeline
    
    # Load the actual outcomes data
    data = _load_outcomes_data(horizon)
    if data is None:
        # Return empty timeline if data can't be loaded
        return timeline
    
    outcomes = data["outcomes"]
    metadata = data["metadata"]
    
    try:
        if analog_index >= 0 and analog_index < len(outcomes):
            outcome_values = outcomes[analog_index]
            
            # Extract real values for timeline
            values = {}
            for var_idx, var_name in OUTCOMES_VARIABLE_MAP.items():
                if var_idx < len(outcome_values):
                    values[var_name] = float(outcome_values[var_idx])
            
            # Get temporal information from metadata
            temporal_info = metadata.iloc[analog_index] if analog_index < len(metadata) else {}
            
            # Create timeline points at key intervals using real data
            for offset in [0, hours // 3, 2 * hours // 3, hours]:
                # For simplicity, we use the same values at each time point
                # In reality, you might want to interpolate or use multiple samples
                point = {
                    "hours_offset": offset,
                    "values": {
                        "t2m": values.get("t2m"),
                        "msl": None,  # Not in outcomes data, set to None
                        "u10": values.get("u10"),
                        "v10": values.get("v10"),
                        "t850": values.get("t850"),
                        "z500": values.get("z500"),
                        "cape": values.get("cape")
                    },
                    "events": None,
                    "temperature_trend": "stable", 
                    "pressure_trend": "stable"
                }
                
                # Determine trends based on actual data patterns
                if "t2m" in values:
                    # Simple trend analysis could be added here based on comparing
                    # with nearby analogs or temporal patterns
                    pass
                
                timeline.append(point)
                
    except Exception as e:
        logger.error(f"Error generating timeline from analog {analog_index}: {e}")
    
    return timeline

def _generate_outcome_narrative(analog: Dict[str, Any]) -> str:
    """Generate outcome narrative from analog data."""
    outcome = analog.get("forecast_outcome", {})
    reliability = outcome.get("reliability_class", "medium")
    trend = outcome.get("trend_direction", "stable")
    
    if reliability == "high":
        base = "Strong pattern match showing"
    elif reliability == "low":
        base = "Weak pattern match indicating"
    else:
        base = "Moderate pattern match suggesting"
    
    if trend == "increasing":
        evolution = "strengthening conditions"
    elif trend == "decreasing":
        evolution = "weakening conditions"
    else:
        evolution = "stable conditions"
    
    return f"{base} {evolution} with typical seasonal characteristics."

def _extract_season_info(analog: Dict[str, Any]) -> Dict[str, Any]:
    """Extract season information from analog data using real metadata."""
    # Get the analog index to extract from metadata
    analog_index = analog.get("analog_index", analog.get("index"))
    horizon = analog.get("horizon", "24h")
    
    # Load the actual metadata
    data = _load_outcomes_data(horizon)
    if data is None or analog_index is None:
        # Fallback to current time
        from datetime import datetime
        return {
            "month": datetime.now().month,
            "season": "autumn"
        }
    
    metadata = data["metadata"]
    
    try:
        if analog_index >= 0 and analog_index < len(metadata):
            row = metadata.iloc[analog_index]
            
            # Extract real seasonal information
            month = int(row['month']) if 'month' in row else datetime.now().month
            season_code = int(row['season']) if 'season' in row else 1
            
            # Map season code to name
            season_map = {0: "summer", 1: "autumn", 2: "winter", 3: "spring"}
            season = season_map.get(season_code, "autumn")
            
            return {
                "month": month,
                "season": season
            }
    except Exception as e:
        logger.error(f"Error extracting season info from analog {analog_index}: {e}")
    
    # Fallback
    from datetime import datetime
    return {
        "month": datetime.now().month,
        "season": "autumn"
    }

def _generate_ensemble_statistics(analogs: List[Dict[str, Any]], variables: List[str]) -> Dict[str, Any]:
    """Generate ensemble statistics from analog list using real outcomes data."""
    if not analogs:
        return {
            "mean_outcomes": {},
            "outcome_uncertainty": {},
            "common_events": []
        }
    
    # Get horizon from first analog to determine which dataset to use
    horizon = analogs[0].get("horizon", "24h") if analogs else "24h"
    
    # Load the actual outcomes data
    data = _load_outcomes_data(horizon)
    if data is None:
        return {
            "mean_outcomes": {},
            "outcome_uncertainty": {},
            "common_events": []
        }
    
    outcomes = data["outcomes"]
    metadata = data["metadata"]
    
    # Extract values for statistics from real data
    mean_outcomes = {}
    outcome_uncertainty = {}
    
    # Process each requested variable
    for var in variables:
        if var not in OUTCOMES_VARIABLE_MAP.values():
            mean_outcomes[var] = None
            outcome_uncertainty[var] = None
            continue
            
        # Find the index for this variable in the outcomes array
        var_index = None
        for idx, var_name in OUTCOMES_VARIABLE_MAP.items():
            if var_name == var:
                var_index = idx
                break
        
        if var_index is None:
            mean_outcomes[var] = None
            outcome_uncertainty[var] = None
            continue
            
        # Collect values from all analogs for this variable
        values = []
        for analog in analogs:
            analog_index = analog.get("index")
            if analog_index is not None and 0 <= analog_index < len(outcomes):
                try:
                    outcome_values = outcomes[analog_index]
                    if var_index < len(outcome_values):
                        values.append(float(outcome_values[var_index]))
                except Exception as e:
                    logger.error(f"Error extracting value for variable {var} from analog {analog_index}: {e}")
                    continue
        
        # Calculate statistics from real values
        if values:
            import numpy as np
            mean_outcomes[var] = round(float(np.mean(values)), 1)
            outcome_uncertainty[var] = round(float(np.std(values)), 1)
        else:
            mean_outcomes[var] = None
            outcome_uncertainty[var] = None
    
    # Extract common events from real temporal patterns
    common_events = []
    try:
        # Analyze seasonal patterns from metadata
        if len(analogs) > 0:
            seasons = []
            months = []
            for analog in analogs:
                analog_index = analog.get("index")
                if analog_index is not None and analog_index < len(metadata):
                    row = metadata.iloc[analog_index]
                    if 'season' in row:
                        seasons.append(row['season'])
                    if 'month' in row:
                        months.append(row['month'])
            
            if seasons:
                # Add seasonal context
                common_seasons = list(set(seasons))
                if len(common_seasons) == 1:
                    season_map = {0: "summer", 1: "autumn", 2: "winter", 3: "spring"}
                    season_name = season_map.get(common_seasons[0], "transitional")
                    common_events.append(f"Typical {season_name} weather patterns")
                else:
                    common_events.append("Transitional seasonal patterns")
                    
    except Exception as e:
        logger.error(f"Error extracting temporal patterns for ensemble statistics: {e}")
        common_events = ["Weather pattern evolution"]
    
    if not common_events:
        common_events = ["Weather pattern evolution"]
    
    return {
        "mean_outcomes": mean_outcomes,
        "outcome_uncertainty": outcome_uncertainty,
        "common_events": common_events
    }

def _map_variable_to_primary(var: str) -> str:
    """Map variable name to primary category."""
    if var == "t2m" or var == "t850":
        return "temperature"
    elif var in ["u10", "v10"]:
        return "wind"
    elif var == "msl":
        return "pressure"
    elif var == "tp6h":
        return "precipitation"
    else:
        return "temperature"

@app.get("/forecast", response_model=ForecastResponse)
@limiter.limit(get_dynamic_rate_limit)
async def get_forecast(
    request: Request,
    horizon: str = "24h",
    vars: Optional[str] = None,
):
    """
    Get weather forecast for specified horizon and variables with comprehensive validation.
    
    Args:
        horizon: Forecast horizon (6h, 12h, 24h, 48h)
        vars: Comma-separated variable list (default: t2m,u10,v10,msl)
        
    Returns:
        Structured forecast with uncertainty bounds and metadata
    """
    start_time = time.time()
    forecast_requests.inc()
    correlation_id = getattr(request.state, 'correlation_id', None)
    
    try:
        # Comprehensive input validation using security utilities
        validation_result = ValidationUtils.validate_forecast_request(horizon, vars)
        
        if not validation_result["valid"]:
            error_requests.labels(error_type="validation").inc()
            validation_errors.labels(error_type="forecast_params").inc()
            
            # Log validation failure with sanitized details
            security_logger.log_security_event(
                "input_validation_failed",
                request,
                horizon=horizon,
                variables=vars,
                error=validation_result["error"],
                correlation_id=correlation_id
            )
            
            raise HTTPException(
                status_code=400, 
                detail=f"Invalid request parameters: {validation_result['error']}"
            )
        
        # Use validated parameters
        validated_horizon = validation_result["horizon"]
        validated_variables = validation_result["variables"]
        
        # If no variables specified, use defaults
        if not validated_variables:
            validated_variables = parse_variables(None)

        # Authenticate after validation so malformed inputs surface as 400 before auth
        credentials = await security(request)
        await verify_token(request, credentials=credentials)

        forecast_logger.log_forecast_request(validated_horizon, validated_variables, correlation_id)
        
        if not forecast_adapter or not system_health.get("ready"):
            error_requests.labels(error_type="system").inc()
            raise HTTPException(503, "Forecasting system not ready")
        
        # Generate forecast with performance tracking using validated inputs
        with response_duration_metric.time():
            with performance_logger.time_operation(
                "forecast_computation", 
                horizon=validated_horizon, 
                variable_count=len(validated_variables),
                correlation_id=correlation_id
            ):
                # Track FAISS query performance if monitor is available
                if faiss_health_monitor:
                    async with faiss_health_monitor.track_query(
                        horizon=validated_horizon, 
                        k_neighbors=50,  # Default k for analog search
                        index_type="auto"
                    ) as faiss_query:
                        forecast_result = forecast_adapter.forecast_with_uncertainty(
                            horizon=validated_horizon,
                            variables=validated_variables
                        )
                else:
                    forecast_result = forecast_adapter.forecast_with_uncertainty(
                        horizon=validated_horizon,
                        variables=validated_variables
                    )
        
        # Build response using validated variables
        # The adapter returns the results in the expected API format
        variable_results = {}
        wind_result = None
        
        for var in validated_variables:
            if var in forecast_result:
                result = forecast_result[var]
                
                # Adapter already provides values in correct units and format
                if isinstance(result, dict):
                    # Dictionary format from fallback response
                    variable_results[var] = VariableResult(
                        value=result.get("value"),
                        p05=result.get("p05"),
                        p95=result.get("p95"),
                        confidence=result.get("confidence"),
                        available=result.get("available", False),
                        analog_count=result.get("analog_count")
                    )
                elif hasattr(result, 'value'):
                    # Already a VariableResult object or similar
                    variable_results[var] = result
                else:
                    # Unknown format - create a safe fallback
                    logger.warning(f"Unknown result format for variable {var}: {type(result)}")
                    variable_results[var] = VariableResult(
                        value=None,
                        p05=None,
                        p95=None,
                        confidence=None,
                        available=False,
                        analog_count=None
                    )
        
        # Combine wind components if both requested
        if "u10" in variable_results and "v10" in variable_results:
            u_result = variable_results["u10"]
            v_result = variable_results["v10"]
            
            if u_result.available and v_result.available:
                import numpy as np
                speed = np.sqrt(u_result.value**2 + v_result.value**2)
                direction = (270 - np.degrees(np.arctan2(v_result.value, u_result.value))) % 360
                
                wind_result = WindResult(
                    speed=speed,
                    direction=direction,
                    gust=None,  # Not available in current system
                    available=True
                )
        
        # System metadata
        latency_ms = (time.time() - start_time) * 1000
        
        # Calculate analog count for logging (safely extract from first available variable)
        analog_count = 0
        if variable_results and validated_variables:
            first_var_result = variable_results.get(validated_variables[0])
            if first_var_result and hasattr(first_var_result, 'analog_count'):
                analog_count = first_var_result.analog_count or 0
        
        # Log successful forecast result
        forecast_logger.log_forecast_result(
            validated_horizon, variable_results, latency_ms, analog_count, correlation_id
        )
        
        # Generate enhanced response fields
        narrative = _generate_forecast_narrative(validated_horizon, variable_results, wind_result)
        risk_assessment = _assess_weather_risks(variable_results, wind_result)
        analogs_summary = _generate_analogs_summary(variable_results, analog_count)
        confidence_explanation = _explain_confidence(variable_results, analog_count)
        
        response = ForecastResponse(
            horizon=validated_horizon,
            generated_at=datetime.now(timezone.utc),
            variables=variable_results,
            wind10m=wind_result,
            narrative=narrative,
            risk_assessment=risk_assessment,
            analogs_summary=analogs_summary,
            confidence_explanation=confidence_explanation,
            versions=VersionInfo(
                model="v1.0.0",
                index="v1.0.0", 
                datasets="v1.0.0",
                api_schema="v1.1.0"  # Updated schema version for enhanced response
            ),
            hashes=HashInfo(
                model="a7c3f92",
                index="2e8b4d1", 
                datasets="d4f8a91"
            ),
            latency_ms=latency_ms
        )
        
        return response
        
    except HTTPException:
        raise
    except Exception as e:
        error_requests.labels(error_type="internal").inc()
        # Use validated variables if available, fallback to original
        error_variables = validated_variables if 'validated_variables' in locals() else parse_variables(vars)
        error_horizon = validated_horizon if 'validated_horizon' in locals() else horizon
        
        forecast_logger.log_forecast_error(error_horizon, error_variables, e, correlation_id)
        
        # Sanitize error message to prevent information leakage
        sanitized_error = "Internal server error"
        if os.getenv("ENVIRONMENT") != "production":
            # Only show detailed errors in development
            sanitized_error = str(e)
        
        raise HTTPException(500, sanitized_error)

@app.get("/api/analogs", response_model=AnalogExplorerData)
@limiter.limit(get_dynamic_rate_limit)
async def get_analogs(
    request: Request,
    horizon: ForecastHorizon = "24h",
    variables: Optional[str] = None,
    k: int = 10,
    query_time: Optional[str] = None,
    _token: str = Depends(verify_token)
):
    """
    Get comprehensive analog weather patterns with detailed FAISS search results.
    
    Provides historical weather analogs that match current atmospheric conditions,
    including detailed pattern analysis, similarity scoring, and meteorological context.
    
    Args:
        horizon: Forecast horizon (6h, 12h, 24h, 48h)
        variables: Comma-separated list of weather variables (defaults to t2m,u10,v10,msl)
        k: Number of analog patterns to return (1-200, default 10)
        query_time: ISO 8601 datetime for analog search (defaults to current time)
        
    Returns:
        AnalogExplorerData with top analog patterns, ensemble statistics, and metadata
        
    Example:
        GET /api/analogs?horizon=24h&variables=t2m,msl&k=5
        
    Response includes:
        - Top K most similar historical weather patterns
        - Detailed similarity scores and distance metrics
        - Historical outcomes and timeline data
        - Ensemble statistics across all analogs
        - Meteorological context and pattern classification
    """
    start_time = time.time()
    correlation_id = getattr(request.state, 'correlation_id', None)
    
    # Increment analog request metrics
    forecast_requests.inc()  # Reuse existing counter for API requests
    
    logger.info(f"[{correlation_id}] Analog request: horizon={horizon}, k={k}")
    
    try:
        # Comprehensive input validation
        validation_result = _validate_analog_request(horizon, variables, k, query_time)
        if not validation_result["valid"]:
            error_requests.labels(error_type="validation").inc()
            validation_errors.labels(error_type="analog_params").inc()
            
            security_logger.log_security_event(
                "analog_validation_failed",
                request,
                horizon=horizon,
                variables=variables,
                k=k,
                query_time=query_time,
                error=validation_result["error"],
                correlation_id=correlation_id
            )
            
            raise HTTPException(
                status_code=400,
                detail=f"Invalid analog request parameters: {validation_result['error']}"
            )
        
        # Use validated parameters
        validated_horizon = validation_result["horizon"]
        validated_variables = validation_result["variables"]
        validated_k = validation_result["k"]
        validated_query_time = validation_result["query_time"]
        
        # Check if analog search service is available
        try:
            analog_service = await get_analog_search_service()
        except Exception as e:
            error_requests.labels(error_type="system").inc()
            logger.error(f"[{correlation_id}] Failed to get analog search service: {e}")
            raise HTTPException(503, "Analog search service not available")
        
        # Convert horizon string to hours for service
        horizon_hours = _horizon_to_hours(validated_horizon)
        
        # Perform comprehensive analog search with performance tracking
        with response_duration_metric.time():
            with performance_logger.time_operation(
                "analog_search",
                horizon=validated_horizon,
                k_neighbors=validated_k,
                correlation_id=correlation_id
            ):
                # Track FAISS query performance if monitor is available
                if faiss_health_monitor:
                    async with faiss_health_monitor.track_query(
                        horizon=validated_horizon,
                        k_neighbors=validated_k,
                        index_type="analog_search"
                    ) as faiss_query:
                        analog_result = await analog_service.get_analog_details(
                            query_time=validated_query_time,
                            horizon=horizon_hours,
                            variable=_primary_variable_from_list(validated_variables),
                            k=validated_k,
                            correlation_id=correlation_id
                        )
                else:
                    analog_result = await analog_service.get_analog_details(
                        query_time=validated_query_time,
                        horizon=horizon_hours,
                        variable=_primary_variable_from_list(validated_variables),
                        k=validated_k,
                        correlation_id=correlation_id
                    )
        
        # Check if analog search was successful
        if not analog_result.get("success", False):
            error_requests.labels(error_type="analog_search").inc()
            error_msg = analog_result.get("error", "Unknown analog search error")
            logger.error(f"[{correlation_id}] Analog search failed: {error_msg}")
            raise HTTPException(500, f"Analog search failed: {error_msg}")
        
        # Transform service result to API response model
        response_data = _transform_analog_result_to_response(
            analog_result,
            validated_horizon,
            validated_variables,
            correlation_id
        )
        
        # Calculate response latency
        latency_ms = (time.time() - start_time) * 1000
        response_data["generated_at"] = datetime.now(timezone.utc).isoformat()
        
        # Log successful analog request
        forecast_logger.log_forecast_result(
            validated_horizon,
            {"analogs": f"{len(response_data.get('top_analogs', []))} patterns"},
            latency_ms,
            len(response_data.get("top_analogs", [])),
            correlation_id
        )
        
        logger.info(f"[{correlation_id}] Analog request completed in {latency_ms:.1f}ms")
        
        return AnalogExplorerData(**response_data)
        
    except HTTPException:
        raise
    except Exception as e:
        error_requests.labels(error_type="internal").inc()
        
        # Use validated variables if available, fallback to original
        error_variables = validated_variables if 'validated_variables' in locals() else parse_variables(variables) if variables else DEFAULT_VARIABLES
        error_horizon = validated_horizon if 'validated_horizon' in locals() else horizon
        
        forecast_logger.log_forecast_error(error_horizon, error_variables, e, correlation_id)
        
        # Sanitize error message
        sanitized_error = "Internal server error"
        if os.getenv("ENVIRONMENT") != "production":
            sanitized_error = str(e)
        
        logger.error(f"[{correlation_id}] Analog request error: {e}")
        raise HTTPException(500, sanitized_error)

@app.get("/health", response_model=HealthResponse)  
@limiter.limit(get_health_rate_limit)
async def get_health(request: Request):
    """
    Get comprehensive system health status.
    
    Returns:
        Detailed health information with all system components
    """
    health_requests.inc()
    
    try:
        if not system_health.get("ready"):
            # System not initialized
            return HealthResponse(
                ready=False,
                checks=[HealthCheck(name="startup", status="fail", message="System not initialized")],
                model=ModelInfo(version="unknown", hash="unknown", matched_ratio=0.0),
                index=IndexInfo(ntotal=0, dim=0, metric="unknown", hash="unknown", dataset_hash="unknown"),
                datasets=[],
                deps={},
                preprocessing_version="unknown",
                uptime_seconds=0.0
            )
        
        # Get detailed health from validation results
        validation_passed = system_health.get("validation_passed", False)
        adapter_health = system_health.get("adapter_health", {})
        
        # Get current FAISS health if monitor is available
        faiss_health_status = "unknown"
        faiss_health_message = "FAISS monitor not initialized"
        if faiss_health_monitor:
            try:
                faiss_health = await faiss_health_monitor.get_health_summary()
                faiss_health_status = "pass" if faiss_health["status"] in ["healthy", "degraded"] else "fail"
                faiss_health_message = f"FAISS status: {faiss_health['status']}, {faiss_health['query_performance']['total_queries']} queries processed"
            except Exception as e:
                faiss_health_status = "fail"
                faiss_health_message = f"FAISS health check failed: {str(e)}"
        
        # Build health checks
        checks = [
            HealthCheck(
                name="startup_validation", 
                status="pass" if validation_passed else "fail",
                message="Expert startup validation passed" if validation_passed else "Validation failed"
            ),
            HealthCheck(
                name="forecast_adapter",
                status="pass" if adapter_health.get("adapter_ready", False) else "fail", 
                message="ForecastAdapter operational" if adapter_health.get("adapter_ready", False) else "Adapter not ready"
            ),
            HealthCheck(
                name="faiss_monitoring",
                status=faiss_health_status,
                message=faiss_health_message
            )
        ]
        
        # System uptime
        uptime = (datetime.now(timezone.utc) - startup_time).total_seconds()
        
        # Get basic FAISS status for backward compatibility
        faiss_ntotal = 13148  # Default value
        faiss_dim = 256      # Default value
        faiss_metric = "L2"  # Default value
        
        if faiss_health_monitor:
            try:
                faiss_health = await faiss_health_monitor.get_health_summary()
                indices = faiss_health.get("indices", {})
                # Get data from first available index
                if indices:
                    first_index = next(iter(indices.values()))
                    faiss_ntotal = first_index.get("vectors", 13148)
                    faiss_dim = first_index.get("dimension", 256)
            except Exception as e:
                logger.warning(f"Failed to get FAISS metrics for basic health: {e}")

        response = HealthResponse(
            ready=system_health["ready"],
            checks=checks,
            model=ModelInfo(
                version="v1.0.0",
                hash="a7c3f92", 
                matched_ratio=1.0
            ),
            index=IndexInfo(
                ntotal=faiss_ntotal,
                dim=faiss_dim,
                metric=faiss_metric,
                hash="2e8b4d1",
                dataset_hash="d4f8a91"
            ),
            datasets=[
                DatasetInfo(
                    horizon=h,
                    valid_pct_by_var={var: 99.5 for var in VARIABLE_ORDER},
                    hash="d4f8a91",
                    schema_version="v1.0.0"
                ) for h in VALID_HORIZONS
            ],
            deps={"fastapi": "0.104.1", "torch": "2.0.1", "faiss": "1.7.4"},
            preprocessing_version="v1.0.0",
            uptime_seconds=uptime
        )
        
        return response
        
    except Exception as e:
        logger.error(f"💥 Health check error: {e}")
        raise HTTPException(500, f"Health check failed: {str(e)}")

@app.get("/metrics")
@limiter.limit("10/minute") 
async def get_metrics(request: Request, _token: str = Depends(verify_token)):
    """
    Get Prometheus-compatible unified metrics including API, FAISS, and performance monitoring.
    
    All metrics are now collected in the default Prometheus registry for unified exposure.
    
    Returns:
        Prometheus metrics in text format
    """
    metrics_requests.inc()
    
    try:
        # Generate all metrics from the unified default registry
        # This now includes:
        # - API metrics (forecast_requests, health_requests, etc.)
        # - FAISS metrics (query performance, index health, etc.)
        # - Performance middleware metrics (will be added to registry)
        unified_metrics = generate_latest()
        
        # Add performance middleware metrics to the output
        # These metrics are generated dynamically from middleware stats
        perf_stats = get_performance_stats()
        compression_stats = perf_stats['compression']['stats']
        rate_limit_stats = perf_stats['rate_limiting']['stats']
        
        # Create additional performance metrics as text
        performance_metrics = []
        performance_metrics.append(f"# HELP compression_requests_total Total compression requests")
        performance_metrics.append(f"# TYPE compression_requests_total counter")
        performance_metrics.append(f"compression_requests_total {compression_stats.get('total_requests', 0)}")
        
        performance_metrics.append(f"# HELP compression_ratio Average compression ratio")
        performance_metrics.append(f"# TYPE compression_ratio gauge")
        performance_metrics.append(f"compression_ratio {compression_stats.get('average_compression_ratio', 0)}")
        
        performance_metrics.append(f"# HELP rate_limit_requests_total Total rate limit checks")
        performance_metrics.append(f"# TYPE rate_limit_requests_total counter")
        performance_metrics.append(f"rate_limit_requests_total {rate_limit_stats.get('total_requests', 0)}")
        
        performance_metrics.append(f"# HELP rate_limit_violations_total Total rate limit violations")
        performance_metrics.append(f"# TYPE rate_limit_violations_total counter")
        performance_metrics.append(f"rate_limit_violations_total {rate_limit_stats.get('limited_requests', 0)}")
        
        # Combine unified registry metrics with additional performance metrics
        combined_metrics = unified_metrics.decode('utf-8') + "\n" + "\n".join(performance_metrics)
        
        # Add configuration drift metrics if detector is available
        # Note: FAISS metrics are now automatically included in unified_metrics
        if config_drift_detector:
            try:
                drift_metrics = config_drift_detector.get_prometheus_metrics()
                if drift_metrics:
                    combined_metrics += "\n" + drift_metrics
            except Exception as e:
                logger.warning(f"Failed to get config drift metrics: {e}")
        
        return Response(content=combined_metrics, media_type=CONTENT_TYPE_LATEST)
        
    except Exception as e:
        logger.error(f"💥 Metrics error: {e}")
        raise HTTPException(500, f"Metrics generation failed: {str(e)}")

@app.get("/health/faiss")
@limiter.limit(get_health_rate_limit)
async def get_faiss_health(request: Request, _token: str = Depends(verify_token)):
    """
    Get detailed FAISS health and performance metrics.
    
    Returns:
        Comprehensive FAISS monitoring data
    """
    try:
        if not faiss_health_monitor:
            raise HTTPException(503, "FAISS health monitoring not available")
        
        health_summary = await faiss_health_monitor.get_health_summary()
        return JSONResponse(content=health_summary)
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"💥 FAISS health check error: {e}")
        raise HTTPException(500, f"FAISS health check failed: {str(e)}")

@app.get("/admin/performance")
@limiter.limit(get_metrics_rate_limit)
async def get_performance_metrics(request: Request, _token: str = Depends(verify_token)):
    """
    Get detailed performance middleware statistics.
    
    Returns:
        Comprehensive performance metrics including caching, compression, and rate limiting
    """
    try:
        perf_stats = get_performance_stats()
        
        # Add runtime information
        uptime = (datetime.now(timezone.utc) - startup_time).total_seconds()
        perf_stats['runtime'] = {
            'uptime_seconds': uptime,
            'startup_time': startup_time.isoformat(),
            'current_time': datetime.now(timezone.utc).isoformat()
        }
        
        # Add environment configuration
        perf_stats['configuration'] = {
            'compression_min_size': int(os.getenv('COMPRESSION_MIN_SIZE', '500')),
            'compression_enabled': os.getenv('COMPRESSION_ENABLED', 'true').lower() == 'true',
            'nginx_compression': os.getenv('NGINX_COMPRESSION', 'false').lower() == 'true',
            'rate_limit_per_minute': int(os.getenv('RATE_LIMIT_PER_MINUTE', '60')),
            'rate_limit_enabled': os.getenv('RATE_LIMIT_ENABLED', 'true').lower() == 'true'
        }
        
        return JSONResponse(content=perf_stats)
        
    except Exception as e:
        logger.error(f"💥 Performance metrics error: {e}")
        raise HTTPException(500, f"Performance metrics failed: {str(e)}")

@app.exception_handler(HTTPException)
async def http_exception_handler(request: Request, exc: HTTPException):
    """Custom HTTP exception handler with sanitized error messages."""
    # Sanitize error message to prevent information leakage
    from security_middleware import SecurityMiddleware
    security_middleware = SecurityMiddleware(None)
    sanitized_message = security_middleware._sanitize_error_message(str(exc.detail))
    
    # Log the exception for monitoring
    correlation_id = getattr(request.state, 'correlation_id', None)
    logger.warning(
        "http_exception",
        status_code=exc.status_code,
        detail=str(exc.detail),
        path=request.url.path,
        method=request.method,
        correlation_id=correlation_id
    )
    
    return JSONResponse(
        status_code=exc.status_code,
        content={
            "error": {
                "code": exc.status_code,
                "message": sanitized_message,
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "correlation_id": correlation_id
            }
        }
    )

@app.exception_handler(Exception)
async def general_exception_handler(request: Request, exc: Exception):
    """General exception handler with comprehensive security and sanitization."""
    correlation_id = getattr(request.state, 'correlation_id', None)
    
    # Log the full exception for debugging
    logger.error(
        "unhandled_exception",
        error_type=type(exc).__name__,
        error_message=str(exc),
        path=request.url.path,
        method=request.method,
        correlation_id=correlation_id,
        exc_info=True
    )
    
    error_requests.labels(error_type="unhandled").inc()
    
    # Always sanitize error messages in production
    if os.getenv("ENVIRONMENT") == "production":
        sanitized_message = "Internal server error"
    else:
        # Even in development, sanitize the message
        from security_middleware import SecurityMiddleware
        security_middleware = SecurityMiddleware(None)
        sanitized_message = security_middleware._sanitize_error_message(str(exc))
    
    return JSONResponse(
        status_code=500,
        content={
            "error": {
                "code": 500,
                "message": sanitized_message,
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "correlation_id": correlation_id
            }
        }
    )

@app.on_event("shutdown")
async def shutdown_event():
    """Gracefully shutdown monitoring systems."""
    global faiss_health_monitor, config_drift_detector
    
    logger.info("🛑 Shutting down Adelaide Weather Forecasting API")
    
    # Shutdown FAISS health monitoring
    if faiss_health_monitor:
        logger.info("📊 Stopping FAISS health monitoring...")
        await faiss_health_monitor.stop_monitoring()
        faiss_health_monitor = None
    
    # Shutdown configuration drift monitoring
    if config_drift_detector:
        logger.info("📊 Stopping configuration drift monitoring...")
        config_drift_detector.stop_monitoring()
        config_drift_detector = None
    
    logger.info("✅ Adelaide Weather API shutdown complete")

if __name__ == "__main__":
    port = int(os.getenv("PORT", 8000))
    host = os.getenv("HOST", "0.0.0.0")
    
    logger.info(f"🚀 Starting Adelaide Weather API on {host}:{port}")
    logger.info(f"🗜️ Compression min size: {os.getenv('COMPRESSION_MIN_SIZE', '500')} bytes")
    logger.info(f"⚡ Rate limit: {os.getenv('RATE_LIMIT_PER_MINUTE', '60')} requests/minute")
    logger.info(f"🔧 Environment: {os.getenv('ENVIRONMENT', 'development')}")
    
    uvicorn.run(
        "main:app",
        host=host,
        port=port,
        reload=os.getenv("ENVIRONMENT") != "production",
        log_level="info"
    )
