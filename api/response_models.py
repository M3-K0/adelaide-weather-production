#!/usr/bin/env python3
"""
Adelaide Weather Forecasting API - Response Models
=================================================

Comprehensive Pydantic response models for the Adelaide Weather Forecasting API.
These models provide strict typing, validation, and OpenAPI schema generation
that matches the frontend TypeScript interfaces exactly.

Author: Backend Architecture Team
Version: 1.0.0 - T001 Implementation
"""

from datetime import datetime
from typing import Dict, List, Optional, Union, Literal
from pydantic import BaseModel, Field, field_validator, ConfigDict


# ============================================================================
# Core Domain Types
# ============================================================================

WeatherVariable = Literal[
    't2m',    # 2m temperature
    'u10',    # 10m U wind component
    'v10',    # 10m V wind component  
    'msl',    # Mean sea level pressure
    'r850',   # 850hPa relative humidity
    'tp6h',   # 6-hourly total precipitation
    'cape',   # Convective available potential energy
    't850',   # 850hPa temperature
    'z500'    # 500hPa geopotential height
]

ForecastHorizon = Literal['6h', '12h', '24h', '48h']
RiskLevel = Literal['minimal', 'low', 'moderate', 'high', 'extreme']
Season = Literal['summer', 'autumn', 'winter', 'spring']
TrendIndicator = Literal['rising', 'falling', 'stable']


# ============================================================================
# Base Variable Results (existing models from main.py)
# ============================================================================

class VariableResult(BaseModel):
    """Individual variable forecast result with uncertainty quantification."""
    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "value": 22.5,
                "p05": 18.2,
                "p95": 26.8,
                "confidence": 0.85,
                "available": True,
                "analog_count": 47
            }
        }
    )
    
    value: Optional[float] = Field(
        None,
        description="Point estimate value for the weather variable",
        examples=[22.5, 1013.2, 15.7]
    )
    p05: Optional[float] = Field(
        None,
        description="5th percentile (lower uncertainty bound)",
        examples=[18.2, 1008.5, 12.1]
    )
    p95: Optional[float] = Field(
        None,
        description="95th percentile (upper uncertainty bound)",
        examples=[26.8, 1018.0, 19.3]
    )
    confidence: Optional[float] = Field(
        None,
        description="Confidence level (0-1) based on analog similarity",
        examples=[0.85, 0.72, 0.93],
        ge=0.0,
        le=1.0
    )
    available: bool = Field(
        ...,
        description="Whether forecast is available for this variable",
        examples=[True, False]
    )
    analog_count: Optional[int] = Field(
        None,
        description="Number of historical analog patterns used",
        examples=[47, 32, 55],
        ge=0,
        le=10000
    )
    
    @field_validator('value', 'p05', 'p95')
    @classmethod
    def validate_numeric_values(cls, v):
        """Validate numeric values are reasonable."""
        if v is not None:
            if not isinstance(v, (int, float)):
                raise ValueError("Value must be numeric")
            if abs(v) > 1e10:
                raise ValueError("Value out of reasonable range")
        return v


class WindResult(BaseModel):
    """Wind forecast result with speed/direction components."""
    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "speed": 8.5,
                "direction": 225.0,
                "gust": 12.3,
                "available": True
            }
        }
    )
    
    speed: Optional[float] = Field(
        None,
        description="Wind speed in m/s",
        examples=[8.5, 2.1, 15.7],
        ge=0.0,
        le=200.0
    )
    direction: Optional[float] = Field(
        None,
        description="Wind direction in degrees (0-360, meteorological convention)",
        examples=[225.0, 090.0, 180.0],
        ge=0.0,
        lt=360.0
    )
    gust: Optional[float] = Field(
        None,
        description="Wind gust speed in m/s",
        examples=[12.3, 4.5, 22.1],
        ge=0.0,
        le=200.0
    )
    available: bool = Field(
        ...,
        description="Whether wind forecast is available",
        examples=[True, False]
    )


# ============================================================================
# Risk Assessment Models
# ============================================================================

class RiskAssessment(BaseModel):
    """Weather risk assessment for various hazards."""
    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "thunderstorm": "moderate",
                "heat_stress": "low", 
                "wind_damage": "minimal",
                "precipitation": "low"
            }
        }
    )
    
    thunderstorm: RiskLevel = Field(
        ...,
        description="Thunderstorm development risk level based on CAPE and atmospheric instability",
        examples=["moderate", "high", "minimal"]
    )
    heat_stress: RiskLevel = Field(
        ...,
        description="Heat stress risk for humans and agriculture based on temperature forecasts",
        examples=["low", "extreme", "moderate"]
    )
    wind_damage: RiskLevel = Field(
        ...,
        description="Wind damage potential to structures and vegetation",
        examples=["minimal", "high", "moderate"]
    )
    precipitation: RiskLevel = Field(
        ...,
        description="Heavy precipitation and flooding risk",
        examples=["low", "moderate", "high"]
    )


# ============================================================================
# Analog Pattern Models
# ============================================================================

class AnalogLocation(BaseModel):
    """Geographic location of an analog pattern."""
    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "latitude": -34.9285,
                "longitude": 138.6007,
                "name": "Adelaide Weather Station"
            }
        }
    )
    
    latitude: float = Field(
        ...,
        description="Latitude in decimal degrees",
        examples=[-34.9285, -35.1234, -34.5678],
        ge=-90.0,
        le=90.0
    )
    longitude: float = Field(
        ...,
        description="Longitude in decimal degrees",
        examples=[138.6007, 139.1234, 137.8901],
        ge=-180.0,
        le=180.0
    )
    name: Optional[str] = Field(
        None,
        description="Human-readable location name",
        examples=["Adelaide Weather Station", "Mount Lofty", "Port Adelaide"],
        max_length=100
    )


class SeasonInfo(BaseModel):
    """Season and month information for an analog pattern."""
    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "month": 3,
                "season": "autumn"
            }
        }
    )
    
    month: int = Field(
        ...,
        description="Month of the year (1-12)",
        examples=[3, 7, 11],
        ge=1,
        le=12
    )
    season: Season = Field(
        ...,
        description="Southern hemisphere season",
        examples=["autumn", "winter", "spring", "summer"]
    )


class AnalogTimelinePoint(BaseModel):
    """Single point in an analog timeline showing weather evolution."""
    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "hours_offset": 12,
                "values": {
                    "t2m": 24.5,
                    "msl": 1015.2,
                    "u10": 3.2,
                    "v10": -1.8
                },
                "events": ["Cloud cover increased", "Wind direction shifted"],
                "temperature_trend": "rising",
                "pressure_trend": "stable"
            }
        }
    )
    
    hours_offset: int = Field(
        ...,
        description="Hours from pattern start time",
        examples=[0, 6, 12, 24, 48],
        ge=0,
        le=168  # Max 1 week
    )
    values: Dict[WeatherVariable, Optional[float]] = Field(
        ...,
        description="Weather variable values at this time point",
        examples=[
            {"t2m": 24.5, "msl": 1015.2},
            {"u10": 3.2, "v10": -1.8, "cape": 850.0}
        ]
    )
    events: Optional[List[str]] = Field(
        None,
        description="Significant weather events observed at this time",
        examples=[
            ["Cloud cover increased", "Wind direction shifted"],
            ["Pressure began falling", "Temperature spike occurred"]
        ],
        max_length=10
    )
    temperature_trend: Optional[TrendIndicator] = Field(
        None,
        description="Temperature trend indicator",
        examples=["rising", "stable", "falling"]
    )
    pressure_trend: Optional[TrendIndicator] = Field(
        None,
        description="Pressure trend indicator",
        examples=["rising", "stable", "falling"]
    )
    
    @field_validator('events')
    @classmethod
    def validate_events(cls, v):
        """Validate weather events list."""
        if v is not None:
            if not isinstance(v, list):
                raise ValueError("Events must be a list")
            for event in v:
                if not isinstance(event, str) or len(event) > 200:
                    raise ValueError("Each event must be a string under 200 characters")
        return v


class AnalogPattern(BaseModel):
    """Individual historical analog pattern with detailed timeline and outcomes."""
    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "date": "2023-03-15T12:00:00Z",
                "similarity_score": 0.89,
                "initial_conditions": {
                    "t2m": 22.1,
                    "msl": 1013.4,
                    "u10": 2.5,
                    "v10": -1.2
                },
                "timeline": [
                    {
                        "hours_offset": 0,
                        "values": {"t2m": 22.1, "msl": 1013.4},
                        "temperature_trend": "stable",
                        "pressure_trend": "stable"
                    },
                    {
                        "hours_offset": 12,
                        "values": {"t2m": 24.5, "msl": 1015.2},
                        "events": ["Cloud cover increased"],
                        "temperature_trend": "rising", 
                        "pressure_trend": "rising"
                    }
                ],
                "outcome_narrative": "Pattern showed stable conditions evolving into typical autumn weather with gradual warming and pressure rise over 24 hours.",
                "location": {
                    "latitude": -34.9285,
                    "longitude": 138.6007,
                    "name": "Adelaide Weather Station"
                },
                "season_info": {
                    "month": 3,
                    "season": "autumn"
                }
            }
        }
    )
    
    date: str = Field(
        ...,
        description="ISO 8601 datetime of the historical pattern occurrence",
        examples=["2023-03-15T12:00:00Z", "2022-07-22T06:00:00Z"],
        pattern=r"^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}Z?$"
    )
    similarity_score: float = Field(
        ...,
        description="Similarity score to current conditions (0-1, higher is more similar)",
        examples=[0.89, 0.72, 0.95],
        ge=0.0,
        le=1.0
    )
    initial_conditions: Dict[WeatherVariable, Optional[float]] = Field(
        ...,
        description="Weather conditions at the start of this historical pattern",
        examples=[
            {"t2m": 22.1, "msl": 1013.4, "u10": 2.5, "v10": -1.2},
            {"t2m": 18.5, "cape": 1250.0, "r850": 65.2}
        ]
    )
    timeline: List[AnalogTimelinePoint] = Field(
        ...,
        description="Chronological sequence of weather evolution during this pattern",
        examples=[],
        min_length=2,
        max_length=50
    )
    outcome_narrative: str = Field(
        ...,
        description="Human-readable description of what actually happened in this historical case",
        examples=[
            "Pattern showed stable conditions evolving into typical autumn weather.",
            "Rapid development of thunderstorm activity with heavy precipitation.",
            "Gradual warming trend with increasing wind speeds from northwest."
        ],
        min_length=10,
        max_length=1000
    )
    location: Optional[AnalogLocation] = Field(
        None,
        description="Geographic location where this analog pattern was observed"
    )
    season_info: SeasonInfo = Field(
        ...,
        description="Season and month information for temporal context"
    )
    
    @field_validator('timeline')
    @classmethod
    def validate_timeline_sequence(cls, v):
        """Validate timeline is chronologically ordered."""
        if not v:
            raise ValueError("Timeline must contain at least one point")
        
        for i in range(1, len(v)):
            if v[i].hours_offset <= v[i-1].hours_offset:
                raise ValueError("Timeline must be chronologically ordered")
        
        return v


# ============================================================================
# Ensemble Statistics Models
# ============================================================================

class EnsembleStats(BaseModel):
    """Statistical summary across all analog patterns."""
    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "mean_outcomes": {
                    "t2m": 23.7,
                    "msl": 1014.2,
                    "u10": 4.1,
                    "v10": -2.3
                },
                "outcome_uncertainty": {
                    "t2m": 2.8,
                    "msl": 5.4,
                    "u10": 3.2,
                    "v10": 2.9
                },
                "common_events": [
                    "Cloud cover increased",
                    "Wind direction shifted",
                    "Pressure began falling"
                ]
            }
        }
    )
    
    mean_outcomes: Dict[WeatherVariable, Optional[float]] = Field(
        ...,
        description="Mean final values across all analog patterns for each variable",
        examples=[
            {"t2m": 23.7, "msl": 1014.2, "u10": 4.1},
            {"cape": 850.0, "t850": 15.2, "z500": 5640.0}
        ]
    )
    outcome_uncertainty: Dict[WeatherVariable, Optional[float]] = Field(
        ...,
        description="Standard deviation of outcomes across analogs (measure of uncertainty)",
        examples=[
            {"t2m": 2.8, "msl": 5.4, "u10": 3.2},
            {"cape": 450.0, "t850": 1.8, "z500": 120.0}
        ]
    )
    common_events: List[str] = Field(
        ...,
        description="Weather events that occurred in multiple analog patterns",
        examples=[
            ["Cloud cover increased", "Wind direction shifted"],
            ["Pressure began falling", "Temperature spike occurred", "Humidity rose"]
        ],
        max_length=20
    )
    
    @field_validator('mean_outcomes', 'outcome_uncertainty')
    @classmethod 
    def validate_numeric_dicts(cls, v):
        """Validate numeric dictionary values."""
        if v:
            for key, value in v.items():
                if value is not None and not isinstance(value, (int, float)):
                    raise ValueError(f"Value for {key} must be numeric or null")
        return v


# ============================================================================
# Analog Explorer Data Response Model
# ============================================================================

class AnalogExplorerData(BaseModel):
    """Complete analog explorer API response with top patterns and ensemble analysis."""
    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "forecast_horizon": "24h",
                "top_analogs": [],  # Would contain AnalogPattern examples
                "ensemble_stats": {
                    "mean_outcomes": {"t2m": 23.7, "msl": 1014.2},
                    "outcome_uncertainty": {"t2m": 2.8, "msl": 5.4},
                    "common_events": ["Cloud cover increased"]
                },
                "generated_at": "2024-01-15T14:30:00Z"
            }
        }
    )
    
    forecast_horizon: ForecastHorizon = Field(
        ...,
        description="Forecast horizon for which analogs were searched",
        examples=["6h", "12h", "24h", "48h"]
    )
    top_analogs: List[AnalogPattern] = Field(
        ...,
        description="Top 5 most similar historical weather patterns",
        examples=[],
        min_length=0,
        max_length=10
    )
    ensemble_stats: EnsembleStats = Field(
        ...,
        description="Statistical summary across all analog patterns"
    )
    generated_at: str = Field(
        ...,
        description="ISO 8601 timestamp when this analysis was generated",
        examples=["2024-01-15T14:30:00Z", "2024-01-15T14:30:00.123Z"],
        pattern=r"^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}(\.\d{3})?Z?$"
    )
    
    @field_validator('top_analogs')
    @classmethod
    def validate_analog_ordering(cls, v):
        """Validate analogs are ordered by similarity score (highest first)."""
        if len(v) > 1:
            for i in range(1, len(v)):
                if v[i].similarity_score > v[i-1].similarity_score:
                    raise ValueError("Analogs must be ordered by similarity score (highest first)")
        return v


# ============================================================================
# System Information Models (Enhanced from main.py)
# ============================================================================

class VersionInfo(BaseModel):
    """System version information for reproducibility."""
    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "model": "v1.0.0",
                "index": "v1.0.0", 
                "datasets": "v1.0.0",
                "api_schema": "v1.1.0"
            }
        }
    )
    
    model: str = Field(
        ...,
        description="Model version identifier",
        examples=["v1.0.0", "v1.1.2", "v2.0.0-beta"]
    )
    index: str = Field(
        ...,
        description="FAISS index version",
        examples=["v1.0.0", "v1.1.0", "v2.0.0"]
    )
    datasets: str = Field(
        ...,
        description="Training datasets version",
        examples=["v1.0.0", "ERA5-2024Q1", "v1.1.0"]
    )
    api_schema: str = Field(
        ...,
        description="API schema version",
        examples=["v1.1.0", "v1.0.0", "v2.0.0"]
    )


class HashInfo(BaseModel):
    """System hash information for integrity verification."""
    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "model": "a7c3f92e8b4d1c56",
                "index": "2e8b4d1f9a7c3e56",
                "datasets": "d4f8a91b2c5e7f89"
            }
        }
    )
    
    model: str = Field(
        ...,
        description="SHA-256 hash of model files",
        examples=["a7c3f92e8b4d1c56", "f1e2d3c4b5a69788"],
        pattern=r"^[a-fA-F0-9]{8,64}$"
    )
    index: str = Field(
        ...,
        description="SHA-256 hash of FAISS index files",
        examples=["2e8b4d1f9a7c3e56", "c3b2a19f8e7d6c45"],
        pattern=r"^[a-fA-F0-9]{8,64}$"
    )
    datasets: str = Field(
        ...,
        description="SHA-256 hash of dataset files",
        examples=["d4f8a91b2c5e7f89", "a1b2c3d4e5f67890"],
        pattern=r"^[a-fA-F0-9]{8,64}$"
    )


# ============================================================================
# Enhanced Forecast Response (Updated from main.py)
# ============================================================================

class AnalogsSummary(BaseModel):
    """Summary of historical analog pattern matching."""
    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "most_similar_date": "2023-03-15T12:00:00Z",
                "similarity_score": 0.87,
                "analog_count": 47,
                "outcome_description": "Similar patterns typically resulted in stable conditions with gradual warming",
                "confidence_explanation": "High confidence based on 47 strong analog matches with average similarity of 87%"
            }
        }
    )
    
    most_similar_date: str = Field(
        ...,
        description="ISO 8601 datetime of the most similar historical weather pattern",
        examples=["2023-03-15T12:00:00Z", "2022-11-08T18:00:00Z"],
        pattern=r"^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}Z?$"
    )
    similarity_score: float = Field(
        ...,
        description="Similarity score of the best analog match (0-1)",
        examples=[0.87, 0.72, 0.95],
        ge=0.0,
        le=1.0
    )
    analog_count: int = Field(
        ...,
        description="Number of analog patterns used in ensemble",
        examples=[47, 32, 55],
        ge=0,
        le=1000
    )
    outcome_description: str = Field(
        ...,
        description="Description of what happened in similar historical cases",
        examples=[
            "Similar patterns typically resulted in stable conditions",
            "Historical patterns showed rapid thunderstorm development",
            "Previous cases led to sustained high pressure and clear skies"
        ],
        min_length=10,
        max_length=500
    )
    confidence_explanation: str = Field(
        ...,
        description="Explanation of confidence level and reasoning",
        examples=[
            "High confidence based on 47 strong analog matches",
            "Moderate confidence due to seasonal variation in patterns",
            "Low confidence with only 12 weak historical matches"
        ],
        min_length=10,
        max_length=500
    )


class ForecastResponse(BaseModel):
    """Complete forecast API response with narrative and risk assessment."""
    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "horizon": "24h",
                "generated_at": "2024-01-15T14:30:00Z",
                "variables": {
                    "t2m": {
                        "value": 22.5,
                        "p05": 18.2,
                        "p95": 26.8,
                        "confidence": 0.85,
                        "available": True,
                        "analog_count": 47
                    }
                },
                "wind10m": {
                    "speed": 8.5,
                    "direction": 225.0,
                    "gust": 12.3,
                    "available": True
                },
                "narrative": "Forecast for 24h: mild conditions with temperature around 22.5°C",
                "risk_assessment": {
                    "thunderstorm": "low",
                    "heat_stress": "minimal",
                    "wind_damage": "minimal", 
                    "precipitation": "low"
                },
                "analogs_summary": {
                    "most_similar_date": "2023-03-15T12:00:00Z",
                    "similarity_score": 0.87,
                    "analog_count": 47,
                    "outcome_description": "Similar patterns typically resulted in stable conditions",
                    "confidence_explanation": "High confidence based on 47 strong analog matches"
                },
                "confidence_explanation": "High confidence forecast based on 47 historical analog patterns",
                "versions": {
                    "model": "v1.0.0",
                    "index": "v1.0.0",
                    "datasets": "v1.0.0", 
                    "api_schema": "v1.1.0"
                },
                "hashes": {
                    "model": "a7c3f92e8b4d1c56",
                    "index": "2e8b4d1f9a7c3e56",
                    "datasets": "d4f8a91b2c5e7f89"
                },
                "latency_ms": 145.2
            }
        }
    )
    
    horizon: ForecastHorizon = Field(
        ...,
        description="Forecast time horizon",
        examples=["6h", "12h", "24h", "48h"]
    )
    generated_at: datetime = Field(
        ...,
        description="ISO 8601 timestamp when forecast was generated",
        examples=["2024-01-15T14:30:00Z"]
    )
    variables: Dict[WeatherVariable, VariableResult] = Field(
        ...,
        description="Dictionary of variable forecasts keyed by variable name",
        examples=[
            {"t2m": {"value": 22.5, "available": True}},
            {"msl": {"value": 1013.2, "available": True}, "u10": {"value": 3.5, "available": True}}
        ]
    )
    wind10m: Optional[WindResult] = Field(
        None,
        description="Combined 10m wind forecast (derived from u10/v10 components)"
    )
    narrative: str = Field(
        ...,
        description="Human-readable forecast narrative",
        examples=[
            "Forecast for 24h: mild conditions with temperature around 22.5°C",
            "Forecast for 12h: warm and humid with moderate easterly winds",
            "Forecast for 48h: cool and dry with high pressure dominating"
        ],
        min_length=10,
        max_length=1000
    )
    risk_assessment: RiskAssessment = Field(
        ...,
        description="Risk assessment for weather hazards"
    )
    analogs_summary: AnalogsSummary = Field(
        ...,
        description="Historical analog pattern analysis"
    )
    confidence_explanation: str = Field(
        ...,
        description="Explanation of overall forecast confidence",
        examples=[
            "High confidence forecast based on 47 historical analog patterns",
            "Moderate confidence due to limited seasonal analog availability",
            "Low confidence forecast - unusual atmospheric conditions"
        ],
        min_length=10,
        max_length=500
    )
    versions: VersionInfo = Field(
        ...,
        description="System version information for reproducibility"
    )
    hashes: HashInfo = Field(
        ...,
        description="System hash information for integrity verification"
    )
    latency_ms: float = Field(
        ...,
        description="Response generation latency in milliseconds",
        examples=[145.2, 89.7, 203.1],
        ge=0.0,
        le=30000.0
    )


# ============================================================================
# Health Check Models (Enhanced from main.py)
# ============================================================================

class HealthCheck(BaseModel):
    """Individual health check result."""
    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "name": "faiss_index",
                "status": "pass",
                "message": "FAISS index operational with 13148 vectors"
            }
        }
    )
    
    name: str = Field(
        ...,
        description="Name of the health check component",
        examples=["startup_validation", "forecast_adapter", "faiss_index"],
        max_length=100
    )
    status: Literal["pass", "fail"] = Field(
        ...,
        description="Health check status",
        examples=["pass", "fail"]
    )
    message: str = Field(
        ...,
        description="Detailed message about the health check result",
        examples=[
            "FAISS index operational with 13148 vectors",
            "Expert startup validation passed",
            "ForecastAdapter not ready - initialization failed"
        ],
        max_length=500
    )


class ModelInfo(BaseModel):
    """Model health and version information."""
    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "version": "v1.0.0",
                "hash": "a7c3f92e8b4d1c56",
                "matched_ratio": 1.0
            }
        }
    )
    
    version: str = Field(
        ...,
        description="Model version identifier",
        examples=["v1.0.0", "v1.1.2", "v2.0.0-beta"]
    )
    hash: str = Field(
        ...,
        description="Model file hash for integrity verification",
        examples=["a7c3f92e8b4d1c56", "f1e2d3c4b5a69788"],
        pattern=r"^[a-fA-F0-9]{8,64}$"
    )
    matched_ratio: float = Field(
        ...,
        description="Parameter matching ratio (0-1) for model validation",
        examples=[1.0, 0.98, 0.95],
        ge=0.0,
        le=1.0
    )


class IndexInfo(BaseModel):
    """FAISS index health information."""
    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "ntotal": 13148,
                "dim": 256,
                "metric": "L2",
                "hash": "2e8b4d1f9a7c3e56",
                "dataset_hash": "d4f8a91b2c5e7f89"
            }
        }
    )
    
    ntotal: int = Field(
        ...,
        description="Total number of vectors in FAISS index",
        examples=[13148, 25896, 52344],
        ge=0
    )
    dim: int = Field(
        ...,
        description="Vector dimension",
        examples=[256, 512, 128],
        ge=1
    )
    metric: str = Field(
        ...,
        description="Distance metric used by the index",
        examples=["L2", "IP", "COSINE"],
        max_length=20
    )
    hash: str = Field(
        ...,
        description="FAISS index file hash for integrity verification",
        examples=["2e8b4d1f9a7c3e56", "c3b2a19f8e7d6c45"],
        pattern=r"^[a-fA-F0-9]{8,64}$"
    )
    dataset_hash: str = Field(
        ...,
        description="Hash of dataset this index was built from",
        examples=["d4f8a91b2c5e7f89", "a1b2c3d4e5f67890"],
        pattern=r"^[a-fA-F0-9]{8,64}$"
    )


class DatasetInfo(BaseModel):
    """Dataset health and quality information."""
    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "horizon": "24h",
                "valid_pct_by_var": {
                    "t2m": 99.5,
                    "msl": 98.7,
                    "u10": 99.1,
                    "v10": 99.1
                },
                "hash": "d4f8a91b2c5e7f89",
                "schema_version": "v1.0.0"
            }
        }
    )
    
    horizon: ForecastHorizon = Field(
        ...,
        description="Forecast horizon this dataset covers",
        examples=["6h", "12h", "24h", "48h"]
    )
    valid_pct_by_var: Dict[WeatherVariable, float] = Field(
        ...,
        description="Percentage of valid (non-null) data by weather variable",
        examples=[
            {"t2m": 99.5, "msl": 98.7},
            {"cape": 85.2, "r850": 96.3, "tp6h": 78.9}
        ]
    )
    hash: str = Field(
        ...,
        description="Dataset file hash for integrity verification",
        examples=["d4f8a91b2c5e7f89", "a1b2c3d4e5f67890"],
        pattern=r"^[a-fA-F0-9]{8,64}$"
    )
    schema_version: str = Field(
        ...,
        description="Dataset schema version",
        examples=["v1.0.0", "v1.1.0", "v2.0.0"]
    )
    
    @field_validator('valid_pct_by_var')
    @classmethod
    def validate_percentages(cls, v):
        """Validate percentages are in valid range."""
        for var, pct in v.items():
            if not 0.0 <= pct <= 100.0:
                raise ValueError(f"Percentage for {var} must be between 0 and 100")
        return v


class HealthResponse(BaseModel):
    """Complete system health API response."""
    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "ready": True,
                "checks": [
                    {
                        "name": "startup_validation",
                        "status": "pass",
                        "message": "Expert startup validation passed"
                    },
                    {
                        "name": "forecast_adapter",
                        "status": "pass", 
                        "message": "ForecastAdapter operational"
                    }
                ],
                "model": {
                    "version": "v1.0.0",
                    "hash": "a7c3f92e8b4d1c56",
                    "matched_ratio": 1.0
                },
                "index": {
                    "ntotal": 13148,
                    "dim": 256,
                    "metric": "L2",
                    "hash": "2e8b4d1f9a7c3e56",
                    "dataset_hash": "d4f8a91b2c5e7f89"
                },
                "datasets": [],
                "deps": {
                    "fastapi": "0.104.1",
                    "torch": "2.0.1",
                    "faiss": "1.7.4"
                },
                "preprocessing_version": "v1.0.0",
                "uptime_seconds": 3600.5
            }
        }
    )
    
    ready: bool = Field(
        ...,
        description="Overall system readiness status",
        examples=[True, False]
    )
    checks: List[HealthCheck] = Field(
        ...,
        description="List of individual health check results",
        examples=[]
    )
    model: ModelInfo = Field(
        ...,
        description="Model health and version information"
    )
    index: IndexInfo = Field(
        ...,
        description="FAISS index health information"
    )
    datasets: List[DatasetInfo] = Field(
        ...,
        description="Dataset health information for each horizon",
        examples=[]
    )
    deps: Dict[str, str] = Field(
        ...,
        description="Dependency versions",
        examples=[
            {"fastapi": "0.104.1", "torch": "2.0.1"},
            {"faiss": "1.7.4", "numpy": "1.24.3"}
        ]
    )
    preprocessing_version: str = Field(
        ...,
        description="Preprocessing pipeline version",
        examples=["v1.0.0", "v1.1.0", "v2.0.0"]
    )
    uptime_seconds: float = Field(
        ...,
        description="System uptime in seconds",
        examples=[3600.5, 86400.0, 259200.0],
        ge=0.0
    )


# ============================================================================
# API Error Models
# ============================================================================

class ApiError(BaseModel):
    """API error response model."""
    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "error": "Invalid forecast horizon. Must be one of: 6h, 12h, 24h, 48h"
            }
        }
    )
    
    error: str = Field(
        ...,
        description="Error message describing what went wrong",
        examples=[
            "Invalid forecast horizon",
            "Authentication token required",
            "Forecasting system not ready",
            "Rate limit exceeded"
        ],
        max_length=500
    )
    details: Optional[str] = Field(
        None,
        description="Optional additional error details",
        examples=[
            "The horizon parameter must be one of: 6h, 12h, 24h, 48h",
            "Please provide a valid Bearer token in the Authorization header"
        ],
        max_length=1000
    )


# ============================================================================
# Export All Models
# ============================================================================

__all__ = [
    # Core types
    'WeatherVariable',
    'ForecastHorizon', 
    'RiskLevel',
    'Season',
    'TrendIndicator',
    
    # Variable results
    'VariableResult',
    'WindResult',
    
    # Risk assessment
    'RiskAssessment',
    
    # Analog models
    'AnalogLocation',
    'SeasonInfo',
    'AnalogTimelinePoint',
    'AnalogPattern',
    'EnsembleStats',
    'AnalogExplorerData',
    
    # System info
    'VersionInfo',
    'HashInfo',
    'AnalogsSummary',
    'ForecastResponse',
    
    # Health models
    'HealthCheck',
    'ModelInfo', 
    'IndexInfo',
    'DatasetInfo',
    'HealthResponse',
    
    # Error models
    'ApiError'
]