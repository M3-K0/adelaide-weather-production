"""
Adelaide Weather Forecasting Core Module
========================================

Core infrastructure components for the Adelaide Weather Forecasting System.
Provides essential services for configuration management, model loading,
validation, and system health monitoring.

Key Components:
- Environment Configuration Management
- Model Loading and Validation  
- Startup Validation System
- Performance Optimization
- System Health Monitoring
"""

from .environment_config_manager import (
    EnvironmentConfigManager,
    Environment,
    ConfigValidationError,
    ConfigMetadata
)

# Export the commonly used components
__all__ = [
    'EnvironmentConfigManager',
    'Environment', 
    'ConfigValidationError',
    'ConfigMetadata'
]