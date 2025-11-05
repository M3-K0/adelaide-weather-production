# Environment Configuration Management System

## Overview

The Adelaide Weather Forecasting application now includes a comprehensive environment configuration management system that provides type-safe, validated configuration loading across development, staging, and production environments.

## Key Features

### 🌍 Multi-Environment Support
- **Development**: Optimized for rapid development with reduced datasets and simplified configurations
- **Staging**: Production-like settings for integration testing
- **Production**: Full production deployment with strict validation and optimization

### 📋 Configuration Validation
- Schema validation with comprehensive error reporting
- Environment-specific validation rules
- Required field validation with detailed error messages
- Type validation for configuration values

### 🔧 Environment Detection
- Automatic environment detection via environment variables
- Supports multiple environment variable patterns: `ENVIRONMENT`, `ENV`, `STAGE`, `NODE_ENV`
- Manual environment specification for testing

### 📁 Hierarchical Configuration Loading
- Base configuration files in `configs/` directory
- Environment-specific overrides in `configs/environments/{environment}/`
- Environment variable overrides using `ADELAIDE_` prefix
- Deep merging of configuration hierarchies

### 🛡️ Production Ready Features
- Configuration change detection via hashing
- Comprehensive metadata tracking
- Validation of individual configuration files
- Thread-safe configuration access

## Usage

### Basic Usage

```python
from core import EnvironmentConfigManager, Environment, ConfigValidationError

# Auto-detect environment (from ENV variables)
manager = EnvironmentConfigManager()

# Or specify environment explicitly
manager = EnvironmentConfigManager(environment=Environment.PRODUCTION)

# Load configuration
try:
    config = manager.load_config()
    
    # Access configuration values
    adelaide_lat = manager.get('adelaide.lat')
    embedding_dim = manager.get('encoder.embedding_dim', 256)  # with default
    
    # Check environment
    if manager.is_production():
        print("Running in production mode")
        
except ConfigValidationError as e:
    print(f"Configuration validation failed: {e}")
```

### Environment Variable Overrides

Set environment variables to override configuration values:

```bash
export ADELAIDE_LAT="-35.0"
export ADELAIDE_LON="139.0"
export ENVIRONMENT="production"
```

### Configuration Structure

```
configs/
├── data.yaml              # Base data configuration
├── model.yaml             # Base model configuration  
├── training.yaml          # Base training configuration
└── environments/
    ├── development/
    │   ├── data.yaml       # Development overrides
    │   └── model.yaml      # Development overrides
    ├── staging/
    │   └── model.yaml      # Staging overrides
    └── production/
        ├── data.yaml       # Production overrides
        └── model.yaml      # Production overrides
```

## Configuration Examples

### Development Environment
- Smaller embedding dimensions (128) for faster iteration
- Reduced batch sizes (32) for memory efficiency
- CPU-only operation for accessibility
- Simplified datasets for faster development

### Staging Environment  
- Production-like settings for integration testing
- GPU acceleration enabled
- Full embedding dimensions (256)
- Comprehensive validation

### Production Environment
- Optimized for performance and reliability
- Full dataset configuration
- Maximum batch sizes for throughput
- Strict validation requirements
- Experiment tracking enabled

## API Reference

### EnvironmentConfigManager

#### Constructor
```python
EnvironmentConfigManager(config_dir=None, environment=None)
```

#### Methods
- `load_config()` - Load and validate configuration
- `get(key_path, default=None)` - Get configuration value using dot notation
- `get_environment()` - Get current environment
- `get_metadata()` - Get configuration metadata
- `is_production()` / `is_staging()` / `is_development()` - Environment checks
- `reload_config()` - Reload configuration from files
- `validate_config_file(file_path)` - Validate specific config file

### Environment Enum

```python
class Environment(Enum):
    DEVELOPMENT = "development"
    STAGING = "staging"
    PRODUCTION = "production"
```

### ConfigValidationError

Exception raised when configuration validation fails, providing:
- Detailed error messages
- Configuration file path context
- Field path information  
- List of validation errors

## Integration with Tests

The configuration manager integrates seamlessly with the existing test infrastructure:

```python
# Clean imports for test files
from core import EnvironmentConfigManager, Environment, ConfigValidationError

# Test with specific environment
manager = EnvironmentConfigManager(environment=Environment.DEVELOPMENT)
config = manager.load_config()

# Access test-specific configuration
test_batch_size = manager.get('training.batch_size', 16)
```

## Environment Variable Detection

The system automatically detects the environment from these variables (in order of precedence):

1. `ENVIRONMENT` 
2. `ENV`
3. `STAGE` 
4. `NODE_ENV`

If no environment is specified, defaults to `DEVELOPMENT`.

## Configuration Override Hierarchy

Configuration values are resolved in this order (later values override earlier ones):

1. Base configuration files (`data.yaml`, `model.yaml`, `training.yaml`)
2. Environment-specific overrides (`configs/environments/{env}/`)
3. Environment variable overrides (`ADELAIDE_*`)

## Production Deployment

For production deployment:

```bash
export ENVIRONMENT="production"
export ADELAIDE_LAT="-34.9285"
export ADELAIDE_LON="138.6007"

# Application will automatically load production configuration
python3 -m core.model_loader
```

## Validation Rules

### Common Validation
- Adelaide coordinates within valid ranges
- Positive embedding dimensions
- Valid data types for all configuration values

### Production-Specific Validation  
- All required configuration sections present
- GPU acceleration enabled
- Comprehensive monitoring configuration

### Development-Specific Validation
- Minimal requirements for rapid iteration
- Optional GPU support
- Relaxed validation constraints

## Error Handling

The system provides comprehensive error handling:

```python
try:
    config = manager.load_config()
except ConfigValidationError as e:
    print(f"Validation failed: {e}")
    print(f"Config file: {e.config_path}")
    print(f"Field: {e.field_path}")
    for error in e.errors:
        print(f"  - {error}")
```

## Metadata and Change Detection

Track configuration changes and metadata:

```python
metadata = manager.get_metadata()
print(f"Environment: {metadata.environment.value}")
print(f"Files loaded: {len(metadata.config_files_loaded)}")
print(f"Config hash: {metadata.config_hash}")
print(f"Load time: {metadata.load_timestamp}")
```

## Testing

Run the comprehensive test suite:

```bash
# Basic functionality tests
python3 test_environment_config_manager.py

# Integration tests
python3 test_environment_integration.py
```

## Implementation Details

The system is implemented as a production-ready backend infrastructure component with:

- **Type Safety**: Full type annotations and enum-based environment management
- **Error Handling**: Comprehensive validation with detailed error reporting
- **Performance**: Efficient YAML loading and configuration caching
- **Security**: Safe environment variable processing and validation
- **Maintainability**: Clean architecture with separation of concerns
- **Extensibility**: Easy addition of new environments and validation rules

This environment configuration management system provides the foundation for reliable, maintainable configuration management across all environments in the Adelaide Weather Forecasting application.