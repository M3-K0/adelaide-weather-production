#!/usr/bin/env python3
"""
Canonical Variable Definitions
=============================

Shared variable order, units, and metadata for Adelaide Weather Forecasting System.
Used by both API endpoints and UI components to ensure consistency.

Author: Web Service Layer
Version: 1.0.0 - Production Web Service
"""

from enum import Enum
from typing import Dict, List, Optional, Union
from pydantic import BaseModel
from dataclasses import dataclass

class VariableType(str, Enum):
    """Variable type classification for UI grouping and validation."""
    TEMPERATURE = "temperature"
    WIND = "wind" 
    PRESSURE = "pressure"
    HUMIDITY = "humidity"
    PRECIPITATION = "precipitation"
    CONVECTION = "convection"

@dataclass(frozen=True)
class VariableSpec:
    """Canonical variable specification with metadata."""
    name: str
    display_name: str
    unit_storage: str  # How it's stored in databases
    unit_display: str  # How it's shown to users
    var_type: VariableType
    description: str
    min_value: Optional[float] = None
    max_value: Optional[float] = None
    precision: int = 1  # Decimal places for display

# Canonical variable order - MUST match outcomes database structure
VARIABLE_ORDER = [
    "t2m",        # 2m temperature (index 0)
    "u10",        # 10m u-wind (index 1) 
    "v10",        # 10m v-wind (index 2)
    "msl",        # Mean sea level pressure (index 3)
    "r850",       # 850 hPa relative humidity (index 4)
    "tp6h",       # 6-hour total precipitation (index 5)
    "cape",       # Convective available potential energy (index 6)
    "t850",       # 850 hPa temperature (index 7)
    "z500"        # 500 hPa geopotential height (index 8)
]

# Canonical variable specifications
VARIABLE_SPECS: Dict[str, VariableSpec] = {
    "t2m": VariableSpec(
        name="t2m",
        display_name="Temperature",
        unit_storage="K",  # Kelvin in database
        unit_display="°C", # Celsius for users
        var_type=VariableType.TEMPERATURE,
        description="2-meter air temperature",
        min_value=-50.0,
        max_value=60.0,
        precision=1
    ),
    "u10": VariableSpec(
        name="u10", 
        display_name="U-Wind",
        unit_storage="m/s",
        unit_display="m/s",
        var_type=VariableType.WIND,
        description="10-meter u-component of wind",
        min_value=-50.0,
        max_value=50.0,
        precision=1
    ),
    "v10": VariableSpec(
        name="v10",
        display_name="V-Wind", 
        unit_storage="m/s",
        unit_display="m/s",
        var_type=VariableType.WIND,
        description="10-meter v-component of wind",
        min_value=-50.0,
        max_value=50.0,
        precision=1
    ),
    "msl": VariableSpec(
        name="msl",
        display_name="Sea Level Pressure",
        unit_storage="Pa",
        unit_display="hPa", 
        var_type=VariableType.PRESSURE,
        description="Mean sea level pressure",
        min_value=950.0,
        max_value=1050.0,
        precision=1
    ),
    "r850": VariableSpec(
        name="r850",
        display_name="850hPa Humidity",
        unit_storage="%",
        unit_display="%",
        var_type=VariableType.HUMIDITY, 
        description="850 hPa relative humidity",
        min_value=0.0,
        max_value=100.0,
        precision=1
    ),
    "tp6h": VariableSpec(
        name="tp6h",
        display_name="6h Precipitation",
        unit_storage="m",
        unit_display="mm",
        var_type=VariableType.PRECIPITATION,
        description="6-hour total precipitation",
        min_value=0.0,
        max_value=100.0,
        precision=2
    ),
    "cape": VariableSpec(
        name="cape",
        display_name="CAPE",
        unit_storage="J/kg", 
        unit_display="J/kg",
        var_type=VariableType.CONVECTION,
        description="Convective available potential energy",
        min_value=0.0,
        max_value=5000.0,
        precision=0
    ),
    "t850": VariableSpec(
        name="t850",
        display_name="850hPa Temperature",
        unit_storage="K",
        unit_display="°C",
        var_type=VariableType.TEMPERATURE,
        description="850 hPa temperature", 
        min_value=-50.0,
        max_value=40.0,
        precision=1
    ),
    "z500": VariableSpec(
        name="z500",
        display_name="500hPa Height", 
        unit_storage="m^2/s^2",
        unit_display="m",
        var_type=VariableType.PRESSURE,
        description="500 hPa geopotential height",
        min_value=5000.0,
        max_value=6000.0,
        precision=0
    )
}

# Valid horizons for forecasting
VALID_HORIZONS = ["6h", "12h", "24h", "48h"]

# Default variables for API responses (most relevant for users)
DEFAULT_VARIABLES = ["t2m", "u10", "v10", "msl"]

# Variable groups for UI organization
VARIABLE_GROUPS = {
    "core": ["t2m", "u10", "v10", "msl"],
    "atmospheric": ["r850", "t850", "z500"], 
    "weather": ["tp6h", "cape"]
}

def convert_value(value: float, var_name: str, to_display: bool = True) -> float:
    """Convert between storage and display units."""
    spec = VARIABLE_SPECS[var_name]
    
    if spec.unit_storage == spec.unit_display:
        return value
        
    if var_name in ["t2m", "t850"]:
        # Temperature: Kelvin ↔ Celsius
        if to_display:
            return value - 273.15  # K → °C
        else:
            return value + 273.15  # °C → K
            
    elif var_name == "msl":
        # Pressure: Pa ↔ hPa  
        if to_display:
            return value / 100.0   # Pa → hPa
        else:
            return value * 100.0   # hPa → Pa
            
    elif var_name == "tp6h":
        # Precipitation: m ↔ mm
        if to_display:
            return value * 1000.0  # m → mm
        else:
            return value / 1000.0  # mm → m
            
    elif var_name == "z500":
        # Geopotential: m^2/s^2 ↔ m (approximate)
        if to_display:
            return value / 9.80665  # m^2/s^2 → m (geopotential)
        else:
            return value * 9.80665  # m → m^2/s^2
    
    return value

def validate_variable(var_name: str) -> bool:
    """Check if variable name is valid."""
    return var_name in VARIABLE_SPECS

def validate_horizon(horizon: str) -> bool:
    """Check if horizon is valid with enhanced security checks."""
    if not isinstance(horizon, str):
        return False
    
    # Basic length and character validation
    if len(horizon) > 10 or len(horizon) < 2:
        return False
    
    # Remove any suspicious characters and check pattern
    sanitized = ''.join(c for c in horizon if c.isalnum())
    if sanitized != horizon:
        return False
    
    return horizon in VALID_HORIZONS

def get_variable_index(var_name: str) -> int:
    """Get database index for variable name."""
    try:
        return VARIABLE_ORDER.index(var_name)
    except ValueError:
        raise ValueError(f"Unknown variable: {var_name}")

def parse_variables(vars_param: Optional[str]) -> List[str]:
    """Parse comma-separated variables parameter with enhanced validation."""
    if not vars_param:
        return DEFAULT_VARIABLES
    
    # Basic input sanitization
    if len(vars_param) > 500:
        raise ValueError("Variables parameter too long")
    
    # Remove any suspicious characters
    sanitized_vars = ''.join(c for c in vars_param if c.isalnum() or c in ',_')
    
    variables = [v.strip() for v in sanitized_vars.split(",") if v.strip()]
    
    # Limit number of variables to prevent abuse
    if len(variables) > 20:
        raise ValueError("Too many variables requested (maximum 20)")
    
    # Check for duplicates
    if len(variables) != len(set(variables)):
        raise ValueError("Duplicate variables not allowed")
    
    # Validate each variable
    invalid = [v for v in variables if not validate_variable(v)]
    if invalid:
        raise ValueError(f"Invalid variables: {invalid}")
    
    # Check variable name patterns for security
    for var in variables:
        if len(var) > 20:
            raise ValueError(f"Variable name too long: {var}")
        if not var.replace('_', '').replace('0', '').replace('1', '').replace('2', '').replace('3', '').replace('4', '').replace('5', '').replace('6', '').replace('7', '').replace('8', '').replace('9', '').isalpha():
            raise ValueError(f"Invalid variable name format: {var}")
        
    return variables

def validate_variable_value(var_name: str, value: float) -> bool:
    """Validate that a variable value is within reasonable bounds."""
    if var_name not in VARIABLE_SPECS:
        return False
    
    spec = VARIABLE_SPECS[var_name]
    
    # Check if value is within specified bounds
    if spec.min_value is not None and value < spec.min_value:
        return False
    if spec.max_value is not None and value > spec.max_value:
        return False
    
    # Additional sanity checks for extreme values
    if abs(value) > 1e10:  # Prevent astronomically large values
        return False
    
    # Check for NaN or infinity
    if not isinstance(value, (int, float)) or value != value:  # NaN check
        return False
    
    return True

def sanitize_variable_name(var_name: str) -> str:
    """Sanitize variable name to prevent injection attacks."""
    if not isinstance(var_name, str):
        raise ValueError("Variable name must be a string")
    
    # Remove any non-alphanumeric characters except underscore
    sanitized = ''.join(c for c in var_name if c.isalnum() or c == '_')
    
    # Ensure it's not empty after sanitization
    if not sanitized:
        raise ValueError("Invalid variable name")
    
    # Limit length
    if len(sanitized) > 20:
        raise ValueError("Variable name too long")
    
    return sanitized

def validate_request_size(horizon: str, variables: List[str]) -> bool:
    """Validate that the request is not too large or complex."""
    # Check number of variables
    if len(variables) > 20:
        return False
    
    # Extended horizons should have fewer variables
    if horizon in ["48h"] and len(variables) > 10:
        return False
    
    # Check for reasonable variable combinations
    if len(variables) == 0:
        return False
    
    return True

def get_variable_display_info(var_name: str) -> Dict[str, str]:
    """Get display information for a variable safely."""
    if var_name not in VARIABLE_SPECS:
        return {
            "display_name": "Unknown",
            "unit": "",
            "description": "Unknown variable"
        }
    
    spec = VARIABLE_SPECS[var_name]
    return {
        "display_name": spec.display_name,
        "unit": spec.unit_display,
        "description": spec.description
    }

# Export for API and UI use
__all__ = [
    "VARIABLE_ORDER", 
    "VARIABLE_SPECS",
    "VALID_HORIZONS", 
    "DEFAULT_VARIABLES",
    "VARIABLE_GROUPS",
    "VariableType",
    "VariableSpec", 
    "convert_value",
    "validate_variable",
    "validate_horizon", 
    "get_variable_index",
    "parse_variables",
    "validate_variable_value",
    "sanitize_variable_name",
    "validate_request_size",
    "get_variable_display_info"
]