#!/usr/bin/env python3
"""
Adelaide Weather Forecasting API - Structured Logging Configuration
==================================================================

Production-ready logging configuration with:
- Structured JSON logging for production
- Human-readable logging for development  
- Request tracking and correlation IDs
- Error tracking with context preservation
- Performance metrics and timing
- Security event logging
"""

import os
import sys
import json
import time
import uuid
import logging
import traceback
from datetime import datetime, timezone
from typing import Dict, Any, Optional
from contextlib import contextmanager

import structlog
from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware


class StructuredLogger:
    """Structured logging manager for the Adelaide Weather API."""
    
    def __init__(self, service_name: str = "adelaide-weather-api"):
        self.service_name = service_name
        self.environment = os.getenv("ENVIRONMENT", "development")
        self.setup_logging()
    
    def setup_logging(self):
        """Configure structured logging based on environment."""
        
        # Configure structlog
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
                self._add_service_context,
                structlog.processors.JSONRenderer() if self.environment == "production" 
                else structlog.dev.ConsoleRenderer(colors=True)
            ],
            context_class=dict,
            logger_factory=structlog.stdlib.LoggerFactory(),
            wrapper_class=structlog.stdlib.BoundLogger,
            cache_logger_on_first_use=True,
        )
        
        # Configure standard library logging
        logging.basicConfig(
            format="%(message)s",
            stream=sys.stdout,
            level=logging.INFO if self.environment == "production" else logging.DEBUG,
        )
        
        # Set log levels for third-party libraries
        logging.getLogger("uvicorn").setLevel(logging.INFO)
        logging.getLogger("uvicorn.access").setLevel(logging.WARNING)
        logging.getLogger("fastapi").setLevel(logging.INFO)
    
    def _add_service_context(self, logger, method_name, event_dict):
        """Add service-level context to all log entries."""
        event_dict["service"] = self.service_name
        event_dict["environment"] = self.environment
        event_dict["timestamp"] = datetime.now(timezone.utc).isoformat()
        return event_dict
    
    def get_logger(self, name: str) -> structlog.stdlib.BoundLogger:
        """Get a structured logger instance."""
        return structlog.get_logger(name)


class RequestLoggingMiddleware(BaseHTTPMiddleware):
    """Middleware for request/response logging with correlation tracking."""
    
    def __init__(self, app):
        super().__init__(app)
        self.logger = structlog.get_logger("request_middleware")
    
    async def dispatch(self, request: Request, call_next):
        """Process request with logging and timing."""
        # Generate correlation ID
        correlation_id = str(uuid.uuid4())
        request.state.correlation_id = correlation_id
        
        # Start timing
        start_time = time.time()
        
        # Log request start
        self.logger.info(
            "request_started",
            method=request.method,
            url=str(request.url),
            path=request.url.path,
            query_params=dict(request.query_params),
            client_ip=request.client.host if request.client else None,
            user_agent=request.headers.get("user-agent"),
            correlation_id=correlation_id,
        )
        
        # Process request
        try:
            response = await call_next(request)
            
            # Calculate duration
            duration = time.time() - start_time
            
            # Log successful response
            self.logger.info(
                "request_completed",
                method=request.method,
                path=request.url.path,
                status_code=response.status_code,
                duration_ms=round(duration * 1000, 2),
                correlation_id=correlation_id,
            )
            
            # Add correlation ID to response headers
            response.headers["X-Correlation-ID"] = correlation_id
            
            return response
            
        except Exception as exc:
            # Calculate duration for failed requests
            duration = time.time() - start_time
            
            # Log error with full context
            self.logger.error(
                "request_failed",
                method=request.method,
                path=request.url.path,
                duration_ms=round(duration * 1000, 2),
                correlation_id=correlation_id,
                error_type=type(exc).__name__,
                error_message=str(exc),
                traceback=traceback.format_exc(),
            )
            
            # Re-raise the exception
            raise


class PerformanceLogger:
    """Performance and timing logger for forecast operations."""
    
    def __init__(self):
        self.logger = structlog.get_logger("performance")
    
    @contextmanager
    def time_operation(self, operation: str, **context):
        """Context manager for timing operations."""
        start_time = time.time()
        
        try:
            self.logger.debug(
                "operation_started",
                operation=operation,
                **context
            )
            
            yield
            
            duration = time.time() - start_time
            self.logger.info(
                "operation_completed",
                operation=operation,
                duration_ms=round(duration * 1000, 2),
                **context
            )
            
        except Exception as exc:
            duration = time.time() - start_time
            self.logger.error(
                "operation_failed",
                operation=operation,
                duration_ms=round(duration * 1000, 2),
                error_type=type(exc).__name__,
                error_message=str(exc),
                **context
            )
            raise


class SecurityLogger:
    """Security event logging for authentication and authorization."""
    
    def __init__(self):
        self.logger = structlog.get_logger("security")
    
    def log_auth_attempt(self, request: Request, success: bool, token_hint: str = None):
        """Log authentication attempts."""
        self.logger.info(
            "auth_attempt",
            success=success,
            client_ip=request.client.host if request.client else None,
            user_agent=request.headers.get("user-agent"),
            token_hint=token_hint[:8] + "..." if token_hint else None,
            correlation_id=getattr(request.state, 'correlation_id', None),
        )
    
    def log_rate_limit_exceeded(self, request: Request, limit: str):
        """Log rate limiting events."""
        self.logger.warning(
            "rate_limit_exceeded",
            client_ip=request.client.host if request.client else None,
            path=request.url.path,
            limit=limit,
            correlation_id=getattr(request.state, 'correlation_id', None),
        )
    
    def log_security_event(self, event_type: str, request: Request, **context):
        """Log general security events."""
        self.logger.warning(
            "security_event",
            event_type=event_type,
            client_ip=request.client.host if request.client else None,
            path=request.url.path,
            correlation_id=getattr(request.state, 'correlation_id', None),
            **context
        )


class ForecastLogger:
    """Domain-specific logging for weather forecasting operations."""
    
    def __init__(self):
        self.logger = structlog.get_logger("forecast")
    
    def log_forecast_request(self, horizon: str, variables: list, correlation_id: str = None):
        """Log forecast request details."""
        self.logger.info(
            "forecast_requested",
            horizon=horizon,
            variables=variables,
            variable_count=len(variables),
            correlation_id=correlation_id,
        )
    
    def log_forecast_result(self, horizon: str, variables: dict, 
                          latency_ms: float, analog_count: int, 
                          correlation_id: str = None):
        """Log forecast computation results."""
        available_vars = [var for var, data in variables.items() if data.available]
        
        self.logger.info(
            "forecast_computed",
            horizon=horizon,
            requested_variables=list(variables.keys()),
            available_variables=available_vars,
            latency_ms=round(latency_ms, 2),
            analog_count=analog_count,
            success_rate=len(available_vars) / len(variables) if variables else 0,
            correlation_id=correlation_id,
        )
    
    def log_forecast_error(self, horizon: str, variables: list, 
                         error: Exception, correlation_id: str = None):
        """Log forecast computation errors."""
        self.logger.error(
            "forecast_error",
            horizon=horizon,
            variables=variables,
            error_type=type(error).__name__,
            error_message=str(error),
            correlation_id=correlation_id,
        )


# Global logger instances
structured_logger = StructuredLogger()
performance_logger = PerformanceLogger()
security_logger = SecurityLogger()
forecast_logger = ForecastLogger()

# Main logger for application use
logger = structured_logger.get_logger("main")