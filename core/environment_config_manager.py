#!/usr/bin/env python3
"""
Environment Configuration Management System
===========================================

Production-ready environment configuration management for the Adelaide Weather 
Forecasting Application. Provides type-safe, validated configuration loading 
across development, staging, and production environments.

CORE FEATURES:
1. Multi-environment Support: Development, staging, production with environment detection
2. YAML Configuration Loading: Hierarchical config loading with environment overrides  
3. Configuration Validation: Schema validation with comprehensive error reporting
4. Environment Detection: Automatic environment detection via ENV variables
5. Configuration Merging: Base config + environment-specific overrides
6. Type Safety: Enum-based environment management with validation

CONFIGURATION STRUCTURE:
- Base configuration files in configs/ directory
- Environment-specific overrides in configs/environments/
- Supports nested configuration hierarchies
- Validates required fields and data types

Author: Backend/Architecture Engineer
Version: 1.0.0 - Production Configuration Management
"""

import os
import sys
import yaml
import logging
import hashlib
import json
from enum import Enum
from pathlib import Path
from typing import Dict, Any, Optional, List, Union
from dataclasses import dataclass
from copy import deepcopy
from datetime import datetime

# Setup logging
logger = logging.getLogger(__name__)

class Environment(Enum):
    """
    Supported environment types for the Adelaide Weather Forecasting System.
    
    Each environment has different configuration requirements:
    - DEVELOPMENT: Local development with relaxed validation and debug features
    - STAGING: Production-like environment for integration testing
    - PRODUCTION: Full production deployment with strict validation
    """
    DEVELOPMENT = "development"
    STAGING = "staging" 
    PRODUCTION = "production"
    
    @classmethod
    def from_string(cls, env_str: str) -> 'Environment':
        """Convert string to Environment enum with case-insensitive matching."""
        env_str = env_str.lower().strip()
        
        # Handle common variations
        env_mapping = {
            'dev': cls.DEVELOPMENT,
            'develop': cls.DEVELOPMENT,
            'development': cls.DEVELOPMENT,
            'stage': cls.STAGING,
            'staging': cls.STAGING,
            'prod': cls.PRODUCTION,
            'production': cls.PRODUCTION,
        }
        
        if env_str in env_mapping:
            return env_mapping[env_str]
        
        raise ValueError(f"Unknown environment: '{env_str}'. "
                        f"Valid options: {list(env_mapping.keys())}")

class ConfigValidationError(Exception):
    """
    Raised when configuration validation fails.
    
    Provides detailed error information including:
    - Missing required fields
    - Invalid data types  
    - Schema validation failures
    - Environment-specific validation errors
    """
    
    def __init__(self, message: str, config_path: Optional[str] = None, 
                 field_path: Optional[str] = None, errors: Optional[List[str]] = None):
        self.config_path = config_path
        self.field_path = field_path
        self.errors = errors or []
        
        detailed_message = message
        if config_path:
            detailed_message += f" (config: {config_path})"
        if field_path:
            detailed_message += f" (field: {field_path})"
        if self.errors:
            detailed_message += f"\nValidation errors:\n" + "\n".join(f"  - {error}" for error in self.errors)
            
        super().__init__(detailed_message)

@dataclass
class ConfigMetadata:
    """Metadata about loaded configuration."""
    environment: Environment
    config_files_loaded: List[str]
    load_timestamp: str
    validation_passed: bool
    config_hash: str

class EnvironmentConfigManager:
    """
    Environment-aware configuration management system.
    
    Handles loading and validation of YAML configuration files with 
    environment-specific overrides. Provides type-safe access to
    configuration values with comprehensive validation.
    
    CONFIGURATION HIERARCHY:
    1. Base configurations (data.yaml, model.yaml, training.yaml)
    2. Environment-specific overrides (configs/environments/{env}/)
    3. Environment variable overrides
    
    VALIDATION FEATURES:
    - Required field validation
    - Type validation  
    - Range validation for numeric values
    - Custom validation rules per environment
    - Schema validation with detailed error reporting
    """
    
    def __init__(self, config_dir: Optional[Union[str, Path]] = None, 
                 environment: Optional[Union[str, Environment]] = None):
        """
        Initialize configuration manager.
        
        Args:
            config_dir: Path to configuration directory (defaults to configs/)
            environment: Target environment (auto-detected if not provided)
        """
        self.config_dir = Path(config_dir) if config_dir else Path("configs")
        self.config = {}
        self.metadata: Optional[ConfigMetadata] = None
        
        # Determine environment
        if environment is None:
            self.environment = self._detect_environment()
        elif isinstance(environment, str):
            self.environment = Environment.from_string(environment)
        else:
            self.environment = environment
            
        logger.info(f"✅ Environment configuration manager initialized for: {self.environment.value}")
    
    def _detect_environment(self) -> Environment:
        """
        Auto-detect environment from environment variables.
        
        Checks multiple environment variables in order of precedence:
        1. ENVIRONMENT
        2. ENV  
        3. STAGE
        4. NODE_ENV (for compatibility)
        
        Defaults to DEVELOPMENT if no environment is specified.
        """
        env_vars = ['ENVIRONMENT', 'ENV', 'STAGE', 'NODE_ENV']
        
        for var in env_vars:
            env_value = os.getenv(var)
            if env_value:
                try:
                    return Environment.from_string(env_value)
                except ValueError:
                    logger.warning(f"Invalid environment value in {var}: {env_value}")
                    continue
        
        logger.info("No environment specified, defaulting to DEVELOPMENT")
        return Environment.DEVELOPMENT
    
    def load_config(self) -> Dict[str, Any]:
        """
        Load and validate configuration for the current environment.
        
        Loading order:
        1. Base configuration files (data.yaml, model.yaml, training.yaml)
        2. Environment-specific overrides
        3. Environment variable overrides
        
        Returns:
            Merged and validated configuration dictionary
            
        Raises:
            ConfigValidationError: If configuration loading or validation fails
        """
        config_files_loaded = []
        merged_config = {}
        
        try:
            # Load base configuration files
            base_files = ['data.yaml', 'model.yaml', 'training.yaml']
            
            for config_file in base_files:
                config_path = self.config_dir / config_file
                if config_path.exists():
                    logger.info(f"Loading base config: {config_path}")
                    file_config = self._load_yaml_file(config_path)
                    merged_config = self._deep_merge(merged_config, file_config)
                    config_files_loaded.append(str(config_path))
                else:
                    logger.warning(f"Base config file not found: {config_path}")
            
            # Load environment-specific overrides
            env_config_dir = self.config_dir / "environments" / self.environment.value
            if env_config_dir.exists():
                for config_file in base_files:
                    env_config_path = env_config_dir / config_file
                    if env_config_path.exists():
                        logger.info(f"Loading environment override: {env_config_path}")
                        env_config = self._load_yaml_file(env_config_path)
                        merged_config = self._deep_merge(merged_config, env_config)
                        config_files_loaded.append(str(env_config_path))
            
            # Apply environment variable overrides
            merged_config = self._apply_env_overrides(merged_config)
            
            # Validate configuration
            validation_errors = self._validate_config(merged_config)
            if validation_errors:
                raise ConfigValidationError(
                    f"Configuration validation failed for environment: {self.environment.value}",
                    errors=validation_errors
                )
            
            # Store configuration and metadata
            self.config = merged_config
            self.metadata = ConfigMetadata(
                environment=self.environment,
                config_files_loaded=config_files_loaded,
                load_timestamp=str(datetime.now()),
                validation_passed=True,
                config_hash=self._compute_config_hash(merged_config)
            )
            
            logger.info(f"✅ Configuration loaded successfully for {self.environment.value}")
            logger.info(f"📁 Files loaded: {len(config_files_loaded)}")
            
            return merged_config
            
        except Exception as e:
            if isinstance(e, ConfigValidationError):
                raise
            raise ConfigValidationError(f"Failed to load configuration: {str(e)}")
    
    def _load_yaml_file(self, file_path: Path) -> Dict[str, Any]:
        """Load and parse YAML configuration file."""
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                config = yaml.safe_load(f) or {}
            return config
        except yaml.YAMLError as e:
            raise ConfigValidationError(f"YAML parsing error in {file_path}: {str(e)}")
        except Exception as e:
            raise ConfigValidationError(f"Error reading {file_path}: {str(e)}")
    
    def _deep_merge(self, base: Dict[str, Any], override: Dict[str, Any]) -> Dict[str, Any]:
        """
        Deep merge two dictionaries, with override taking precedence.
        
        Handles nested dictionaries recursively while preserving list values
        from the override dictionary.
        """
        result = deepcopy(base)
        
        for key, value in override.items():
            if key in result and isinstance(result[key], dict) and isinstance(value, dict):
                result[key] = self._deep_merge(result[key], value)
            else:
                result[key] = deepcopy(value)
        
        return result
    
    def _apply_env_overrides(self, config: Dict[str, Any]) -> Dict[str, Any]:
        """
        Apply environment variable overrides to configuration.
        
        Supports dot notation for nested values:
        ADELAIDE_LAT="-34.9" overrides config['adelaide']['lat']
        """
        result = deepcopy(config)
        
        for env_var, value in os.environ.items():
            if env_var.startswith('ADELAIDE_'):
                # Convert environment variable to config path
                config_path = env_var[9:].lower().split('_')  # Remove ADELAIDE_ prefix
                
                # Navigate to the correct location in config
                current = result
                for key in config_path[:-1]:
                    if key not in current:
                        current[key] = {}
                    current = current[key]
                
                # Set the value (attempt type conversion)
                try:
                    # Try to convert to appropriate type
                    if value.lower() in ['true', 'false']:
                        converted_value = value.lower() == 'true'
                    elif value.replace('.', '').replace('-', '').isdigit():
                        converted_value = float(value) if '.' in value else int(value)
                    else:
                        converted_value = value
                    
                    current[config_path[-1]] = converted_value
                    logger.info(f"Applied environment override: {env_var} = {converted_value}")
                except Exception as e:
                    logger.warning(f"Failed to apply environment override {env_var}: {e}")
        
        return result
    
    def _validate_config(self, config: Dict[str, Any]) -> List[str]:
        """
        Validate configuration based on environment requirements.
        
        Returns:
            List of validation error messages (empty if valid)
        """
        errors = []
        
        # Environment-specific validation rules
        if self.environment == Environment.PRODUCTION:
            errors.extend(self._validate_production_config(config))
        elif self.environment == Environment.STAGING:
            errors.extend(self._validate_staging_config(config))
        else:  # DEVELOPMENT
            errors.extend(self._validate_development_config(config))
        
        # Common validation rules
        errors.extend(self._validate_common_config(config))
        
        return errors
    
    def _validate_common_config(self, config: Dict[str, Any]) -> List[str]:
        """Validate configuration rules common to all environments."""
        errors = []
        
        # Validate Adelaide coordinates
        if 'adelaide' in config:
            adelaide = config['adelaide']
            if 'lat' in adelaide:
                lat = adelaide['lat']
                if not isinstance(lat, (int, float)) or not -90 <= lat <= 90:
                    errors.append(f"adelaide.lat must be a number between -90 and 90, got: {lat}")
            
            if 'lon' in adelaide:
                lon = adelaide['lon']
                if not isinstance(lon, (int, float)) or not -180 <= lon <= 180:
                    errors.append(f"adelaide.lon must be a number between -180 and 180, got: {lon}")
        
        # Validate model configuration
        if 'encoder' in config:
            encoder = config['encoder']
            if 'embedding_dim' in encoder:
                dim = encoder['embedding_dim']
                if not isinstance(dim, int) or dim <= 0:
                    errors.append(f"encoder.embedding_dim must be a positive integer, got: {dim}")
        
        return errors
    
    def _validate_production_config(self, config: Dict[str, Any]) -> List[str]:
        """Validate production-specific configuration requirements."""
        errors = []
        
        # Production requires stricter validation
        required_sections = ['adelaide', 'era5', 'gfs', 'encoder', 'faiss']
        for section in required_sections:
            if section not in config:
                errors.append(f"Required configuration section missing: {section}")
        
        # GPU configuration should be available in production
        if 'device' in config and 'use_gpu' in config['device']:
            if not config['device']['use_gpu']:
                errors.append("Production environment should use GPU acceleration")
        
        return errors
    
    def _validate_staging_config(self, config: Dict[str, Any]) -> List[str]:
        """Validate staging-specific configuration requirements."""
        errors = []
        
        # Staging should have production-like configuration but with relaxed constraints
        required_sections = ['adelaide', 'era5', 'encoder']
        for section in required_sections:
            if section not in config:
                errors.append(f"Required configuration section missing: {section}")
        
        return errors
    
    def _validate_development_config(self, config: Dict[str, Any]) -> List[str]:
        """Validate development-specific configuration requirements."""
        errors = []
        
        # Development has minimal requirements for rapid iteration
        if 'adelaide' not in config:
            errors.append("adelaide configuration section is required")
        
        return errors
    
    def _compute_config_hash(self, config: Dict[str, Any]) -> str:
        """Compute hash of configuration for change detection."""
        # Create deterministic string representation
        config_str = json.dumps(config, sort_keys=True, default=str)
        return hashlib.sha256(config_str.encode()).hexdigest()[:16]
    
    def get(self, key_path: str, default: Any = None) -> Any:
        """
        Get configuration value using dot notation.
        
        Args:
            key_path: Dot-separated path to configuration value (e.g., 'adelaide.lat')
            default: Default value if key not found
            
        Returns:
            Configuration value or default
            
        Example:
            manager.get('adelaide.lat')  # Returns -34.9
            manager.get('model.encoder.embedding_dim', 256)
        """
        if not self.config:
            raise ConfigValidationError("Configuration not loaded. Call load_config() first.")
        
        keys = key_path.split('.')
        current = self.config
        
        try:
            for key in keys:
                current = current[key]
            return current
        except (KeyError, TypeError):
            return default
    
    def get_environment(self) -> Environment:
        """Get current environment."""
        return self.environment
    
    def get_metadata(self) -> Optional[ConfigMetadata]:
        """Get configuration metadata."""
        return self.metadata
    
    def is_production(self) -> bool:
        """Check if running in production environment."""
        return self.environment == Environment.PRODUCTION
    
    def is_staging(self) -> bool:
        """Check if running in staging environment."""
        return self.environment == Environment.STAGING
    
    def is_development(self) -> bool:
        """Check if running in development environment."""
        return self.environment == Environment.DEVELOPMENT
    
    def reload_config(self) -> Dict[str, Any]:
        """Reload configuration from files."""
        logger.info("Reloading configuration...")
        return self.load_config()
    
    def validate_config_file(self, file_path: Union[str, Path]) -> List[str]:
        """
        Validate a specific configuration file without loading it.
        
        Args:
            file_path: Path to configuration file
            
        Returns:
            List of validation errors (empty if valid)
        """
        try:
            config = self._load_yaml_file(Path(file_path))
            return self._validate_config(config)
        except Exception as e:
            return [f"Failed to validate {file_path}: {str(e)}"]

# Export public interface
__all__ = [
    'EnvironmentConfigManager',
    'Environment', 
    'ConfigValidationError',
    'ConfigMetadata'
]