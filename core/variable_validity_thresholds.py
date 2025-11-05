#!/usr/bin/env python3
"""
Variable Validity Thresholds System for Production Runtime Reliability
======================================================================

Implements per-variable validity checking with configurable min_analogs thresholds
to prevent silent failures where variables have insufficient analog coverage.

Key Features:
- Per-variable minimum analog thresholds
- Proper N/A handling (not zeros) for insufficient analogs
- Horizon-specific confidence adjustments based on variable availability
- Variable-specific quality scoring
- Automatic degradation detection and reporting

Critical Functionality:
- Variables with <min_analogs show N/A instead of unreliable forecasts
- Horizon confidence reflects actual variable availability
- Quality metrics track variable-specific reliability
- Prevents silent failures from sparse analog coverage

This addresses the critical issue where variables might have very few analogs
but still produce forecasts, leading to unreliable results without user awareness.

Author: Production Runtime Reliability Team
Version: 1.0.0 - Variable Validity Thresholds
"""

import numpy as np
import pandas as pd
import logging
from pathlib import Path
from datetime import datetime, timezone
from typing import Dict, List, Optional, Tuple, Any, Union, Set
from dataclasses import dataclass, field
from enum import Enum
import warnings

logger = logging.getLogger(__name__)

class VariableAvailability(Enum):
    """Variable availability status."""
    AVAILABLE = "available"           # Sufficient analogs available
    SPARSE = "sparse"                # Few analogs, reduced confidence
    INSUFFICIENT = "insufficient"    # Too few analogs, N/A result
    UNAVAILABLE = "unavailable"      # No analogs available

class VariableQuality(Enum):
    """Variable quality classification."""
    HIGH = "high"           # >90% of required analogs
    GOOD = "good"           # 70-90% of required analogs
    FAIR = "fair"           # 50-70% of required analogs
    POOR = "poor"           # 30-50% of required analogs
    CRITICAL = "critical"   # <30% of required analogs

@dataclass
class VariableValidityConfig:
    """Configuration for variable validity thresholds."""
    # Minimum analog thresholds per variable
    min_analogs_absolute: Dict[str, int] = field(default_factory=lambda: {
        'z500': 15,    # Geopotential height - core variable
        't2m': 20,     # 2m temperature - critical for weather
        't850': 18,    # 850mb temperature - important for patterns
        'q850': 12,    # Specific humidity - can be sparse
        'u10': 10,     # 10m u-wind - surface winds variable
        'v10': 10,     # 10m v-wind - surface winds variable
        'u850': 8,     # 850mb u-wind - upper winds
        'v850': 8,     # 850mb v-wind - upper winds
        'cape': 6      # CAPE - often sparse/zero
    })
    
    # Minimum analog fractions (as fraction of total available)
    min_analogs_fraction: Dict[str, float] = field(default_factory=lambda: {
        'z500': 0.6,    # Need 60% of available analogs
        't2m': 0.7,     # Need 70% for temperature
        't850': 0.65,   # Need 65% for 850mb temp
        'q850': 0.5,    # 50% sufficient for humidity
        'u10': 0.5,     # 50% for surface winds
        'v10': 0.5,     # 50% for surface winds
        'u850': 0.4,    # 40% for upper winds
        'v850': 0.4,    # 40% for upper winds
        'cape': 0.3     # 30% for CAPE (often sparse)
    })
    
    # Horizon-specific adjustments (multipliers)
    horizon_adjustments: Dict[int, float] = field(default_factory=lambda: {
        6: 1.0,     # Full requirements for 6h
        12: 0.9,    # 90% requirements for 12h
        24: 0.8,    # 80% requirements for 24h
        48: 0.7     # 70% requirements for 48h
    })
    
    # Quality thresholds (as fraction of required)
    quality_thresholds: Dict[str, float] = field(default_factory=lambda: {
        'high': 0.9,
        'good': 0.7,
        'fair': 0.5,
        'poor': 0.3,
        'critical': 0.0
    })
    
    # Warning thresholds
    sparse_warning_threshold: float = 0.6  # Warn if <60% of required analogs
    critical_failure_threshold: float = 0.3  # Critical if <30% of required analogs

@dataclass
class VariableValidityResult:
    """Result of variable validity check."""
    variable_name: str
    availability_status: VariableAvailability
    quality_level: VariableQuality
    
    # Analog counts
    analogs_available: int
    analogs_required: int
    analogs_fraction: float
    
    # Validation results
    is_valid: bool
    confidence_factor: float  # 0.0-1.0 confidence multiplier
    
    # Diagnostic information
    warnings: List[str] = field(default_factory=list)
    issues: List[str] = field(default_factory=list)
    
    # Metadata
    horizon: int = 0
    timestamp: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())

@dataclass
class HorizonValidityReport:
    """Complete validity report for a forecast horizon."""
    horizon: int
    timestamp: str
    
    # Overall metrics
    total_variables: int
    valid_variables: int
    invalid_variables: int
    overall_confidence: float
    
    # Variable-specific results
    variable_results: Dict[str, VariableValidityResult] = field(default_factory=dict)
    
    # Quality distribution
    quality_distribution: Dict[str, int] = field(default_factory=dict)
    
    # Issues and warnings
    critical_issues: List[str] = field(default_factory=list)
    warnings: List[str] = field(default_factory=list)
    
    # Recommendations
    recommendations: List[str] = field(default_factory=list)

class VariableValidityThresholds:
    """Production-grade variable validity checking system."""
    
    def __init__(self, config: Optional[VariableValidityConfig] = None):
        """Initialize variable validity system.
        
        Args:
            config: Validity configuration (uses defaults if None)
        """
        self.config = config or VariableValidityConfig()
        
        # Expected variables (in canonical order)
        self.canonical_variables = [
            'z500',    # geopotential 500mb (m)
            't2m',     # 2m temperature (K) 
            't850',    # temperature 850mb (K)
            'q850',    # specific humidity 850mb (kg/kg)
            'u10',     # u-wind 10m (m/s)
            'v10',     # v-wind 10m (m/s)
            'u850',    # u-wind 850mb (m/s)
            'v850',    # v-wind 850mb (m/s)
            'cape'     # CAPE (J/kg)
        ]
        
        # Validation history for tracking degradation
        self.validation_history: List[HorizonValidityReport] = []
        
        logger.info(f"🔍 Variable Validity Thresholds initialized")
        logger.info(f"   Canonical variables: {len(self.canonical_variables)}")
        logger.info(f"   Min analogs (absolute): {self.config.min_analogs_absolute}")
        logger.info(f"   Min analogs (fraction): {self.config.min_analogs_fraction}")
    
    def calculate_required_analogs(self, variable_name: str, horizon: int, 
                                 total_available: int) -> int:
        """Calculate required number of analogs for variable at horizon.
        
        Args:
            variable_name: Name of weather variable
            horizon: Forecast horizon in hours
            total_available: Total analogs available for this search
            
        Returns:
            Required number of analogs for reliable forecast
        """
        # Get base requirements
        min_absolute = self.config.min_analogs_absolute.get(variable_name, 10)
        min_fraction = self.config.min_analogs_fraction.get(variable_name, 0.5)
        
        # Apply horizon adjustment
        horizon_factor = self.config.horizon_adjustments.get(horizon, 0.8)
        
        # Calculate adjusted requirements
        adjusted_absolute = int(min_absolute * horizon_factor)
        adjusted_fraction = min_fraction * horizon_factor
        
        # Calculate fraction-based requirement
        fraction_based = int(total_available * adjusted_fraction)
        
        # Use maximum of absolute and fraction-based requirements
        required = max(adjusted_absolute, fraction_based)
        
        # But don't require more than available
        required = min(required, total_available)
        
        return required
    
    def assess_variable_quality(self, analogs_available: int, 
                              analogs_required: int) -> VariableQuality:
        """Assess quality level of variable based on analog coverage.
        
        Args:
            analogs_available: Number of analogs available
            analogs_required: Number of analogs required
            
        Returns:
            Quality level classification
        """
        if analogs_required == 0:
            return VariableQuality.HIGH
        
        fraction = analogs_available / analogs_required
        
        if fraction >= self.config.quality_thresholds['high']:
            return VariableQuality.HIGH
        elif fraction >= self.config.quality_thresholds['good']:
            return VariableQuality.GOOD
        elif fraction >= self.config.quality_thresholds['fair']:
            return VariableQuality.FAIR
        elif fraction >= self.config.quality_thresholds['poor']:
            return VariableQuality.POOR
        else:
            return VariableQuality.CRITICAL
    
    def determine_availability_status(self, analogs_available: int,
                                    analogs_required: int) -> VariableAvailability:
        """Determine availability status of variable.
        
        Args:
            analogs_available: Number of analogs available
            analogs_required: Number of analogs required
            
        Returns:
            Availability status
        """
        if analogs_available == 0:
            return VariableAvailability.UNAVAILABLE
        
        fraction = analogs_available / analogs_required if analogs_required > 0 else 1.0
        
        if fraction >= 1.0:
            return VariableAvailability.AVAILABLE
        elif fraction >= self.config.sparse_warning_threshold:
            return VariableAvailability.SPARSE
        else:
            return VariableAvailability.INSUFFICIENT
    
    def calculate_confidence_factor(self, analogs_available: int,
                                  analogs_required: int,
                                  quality_level: VariableQuality) -> float:
        """Calculate confidence factor for variable.
        
        Args:
            analogs_available: Number of analogs available
            analogs_required: Number of analogs required
            quality_level: Quality level of variable
            
        Returns:
            Confidence factor (0.0-1.0)
        """
        if analogs_required == 0:
            return 1.0
        
        # Base confidence from analog coverage
        base_fraction = min(1.0, analogs_available / analogs_required)
        
        # Quality adjustments
        quality_multipliers = {
            VariableQuality.HIGH: 1.0,
            VariableQuality.GOOD: 0.9,
            VariableQuality.FAIR: 0.7,
            VariableQuality.POOR: 0.5,
            VariableQuality.CRITICAL: 0.2
        }
        
        quality_factor = quality_multipliers.get(quality_level, 0.5)
        
        # Combined confidence (weighted average)
        confidence = (base_fraction * 0.7) + (quality_factor * 0.3)
        
        return max(0.0, min(1.0, confidence))
    
    def validate_variable(self, variable_name: str, analog_outcomes: np.ndarray,
                        analog_weights: np.ndarray, horizon: int,
                        total_available_analogs: int) -> VariableValidityResult:
        """Validate single variable for sufficient analog coverage.
        
        Args:
            variable_name: Name of weather variable
            analog_outcomes: Outcomes array for this variable [n_analogs]
            analog_weights: Weights for analogs [n_analogs]
            horizon: Forecast horizon in hours
            total_available_analogs: Total analogs available before filtering
            
        Returns:
            Validation result for this variable
        """
        # Filter out invalid values
        valid_mask = np.isfinite(analog_outcomes) & (analog_outcomes != 0.0)
        
        # For temperature variables, also filter unrealistic values
        if 'temp' in variable_name.lower() or 't2m' in variable_name or 't850' in variable_name:
            # Reasonable temperature range 150K to 350K
            temp_mask = (analog_outcomes >= 150.0) & (analog_outcomes <= 350.0)
            valid_mask = valid_mask & temp_mask
        
        analogs_available = np.sum(valid_mask)
        analogs_required = self.calculate_required_analogs(
            variable_name, horizon, total_available_analogs
        )
        
        # Calculate metrics
        analogs_fraction = (analogs_available / analogs_required) if analogs_required > 0 else 1.0
        quality_level = self.assess_variable_quality(analogs_available, analogs_required)
        availability_status = self.determine_availability_status(analogs_available, analogs_required)
        confidence_factor = self.calculate_confidence_factor(
            analogs_available, analogs_required, quality_level
        )
        
        # Determine validity
        is_valid = availability_status in [VariableAvailability.AVAILABLE, VariableAvailability.SPARSE]
        
        # Generate warnings and issues
        warnings = []
        issues = []
        
        if availability_status == VariableAvailability.SPARSE:
            warnings.append(f"Sparse analog coverage: {analogs_available}/{analogs_required} ({analogs_fraction:.1%})")
        
        if availability_status == VariableAvailability.INSUFFICIENT:
            issues.append(f"Insufficient analog coverage: {analogs_available}/{analogs_required} ({analogs_fraction:.1%})")
        
        if availability_status == VariableAvailability.UNAVAILABLE:
            issues.append(f"No valid analogs available for {variable_name}")
        
        if quality_level in [VariableQuality.POOR, VariableQuality.CRITICAL]:
            warnings.append(f"Variable quality is {quality_level.value}")
        
        # Check for data quality issues
        if np.sum(analog_outcomes == 0.0) > len(analog_outcomes) * 0.5:
            warnings.append(f"High fraction of zero values: {np.sum(analog_outcomes == 0.0)/len(analog_outcomes):.1%}")
        
        return VariableValidityResult(
            variable_name=variable_name,
            availability_status=availability_status,
            quality_level=quality_level,
            analogs_available=analogs_available,
            analogs_required=analogs_required,
            analogs_fraction=analogs_fraction,
            is_valid=is_valid,
            confidence_factor=confidence_factor,
            warnings=warnings,
            issues=issues,
            horizon=horizon
        )
    
    def validate_horizon_forecast(self, analog_outcomes: np.ndarray,
                                analog_weights: np.ndarray, horizon: int,
                                variable_names: Optional[List[str]] = None) -> HorizonValidityReport:
        """Validate all variables for a horizon forecast.
        
        Args:
            analog_outcomes: Outcomes array [n_analogs, n_variables]
            analog_weights: Weights for analogs [n_analogs]
            horizon: Forecast horizon in hours
            variable_names: Names of variables (uses canonical if None)
            
        Returns:
            Complete validation report for horizon
        """
        if variable_names is None:
            variable_names = self.canonical_variables[:analog_outcomes.shape[1]]
        
        total_available_analogs = len(analog_outcomes)
        
        # Validate each variable
        variable_results = {}
        quality_counts = {q.value: 0 for q in VariableQuality}
        critical_issues = []
        warnings = []
        
        for i, var_name in enumerate(variable_names):
            if i >= analog_outcomes.shape[1]:
                logger.warning(f"⚠️ Variable {var_name} index {i} exceeds outcomes shape {analog_outcomes.shape}")
                continue
            
            var_outcomes = analog_outcomes[:, i]
            result = self.validate_variable(
                var_name, var_outcomes, analog_weights, horizon, total_available_analogs
            )
            
            variable_results[var_name] = result
            quality_counts[result.quality_level.value] += 1
            
            # Collect issues and warnings
            if result.issues:
                critical_issues.extend([f"{var_name}: {issue}" for issue in result.issues])
            
            if result.warnings:
                warnings.extend([f"{var_name}: {warning}" for warning in result.warnings])
        
        # Calculate overall metrics
        valid_variables = sum(1 for r in variable_results.values() if r.is_valid)
        invalid_variables = len(variable_results) - valid_variables
        
        # Calculate overall confidence as weighted average
        if variable_results:
            # Weight by importance (temperature and pressure more important)
            importance_weights = {
                'z500': 1.5, 't2m': 2.0, 't850': 1.5, 'q850': 1.0,
                'u10': 1.2, 'v10': 1.2, 'u850': 1.0, 'v850': 1.0, 'cape': 0.8
            }
            
            total_weight = 0.0
            weighted_confidence = 0.0
            
            for var_name, result in variable_results.items():
                weight = importance_weights.get(var_name, 1.0)
                total_weight += weight
                weighted_confidence += result.confidence_factor * weight
            
            overall_confidence = weighted_confidence / total_weight if total_weight > 0 else 0.0
        else:
            overall_confidence = 0.0
        
        # Generate recommendations
        recommendations = []
        
        if invalid_variables > 0:
            recommendations.append(f"Consider increasing analog search size (currently {total_available_analogs})")
        
        if quality_counts['critical'] > 0:
            recommendations.append("Critical variable quality detected - review data sources")
        
        if overall_confidence < 0.5:
            recommendations.append("Low overall confidence - consider using alternative forecasting method")
        
        if len(critical_issues) > len(variable_results) * 0.3:
            recommendations.append("High fraction of variable issues - system may need recalibration")
        
        # Create report
        report = HorizonValidityReport(
            horizon=horizon,
            timestamp=datetime.now(timezone.utc).isoformat(),
            total_variables=len(variable_results),
            valid_variables=valid_variables,
            invalid_variables=invalid_variables,
            overall_confidence=overall_confidence,
            variable_results=variable_results,
            quality_distribution=quality_counts,
            critical_issues=critical_issues,
            warnings=warnings,
            recommendations=recommendations
        )
        
        # Store for history tracking
        self.validation_history.append(report)
        
        # Log summary
        logger.info(f"📊 Horizon {horizon}h validation: {valid_variables}/{len(variable_results)} valid variables, "
                   f"confidence: {overall_confidence:.2f}")
        
        if critical_issues:
            logger.warning(f"⚠️ Critical issues found: {len(critical_issues)}")
            for issue in critical_issues[:3]:  # Log first 3
                logger.warning(f"   - {issue}")
        
        return report
    
    def filter_forecast_variables(self, forecast_results: Dict[str, float],
                                confidence_intervals: Dict[str, Tuple[float, float]],
                                validity_report: HorizonValidityReport) -> Tuple[Dict[str, float], Dict[str, Tuple[float, float]]]:
        """Filter forecast results to remove invalid variables.
        
        Args:
            forecast_results: Original forecast values
            confidence_intervals: Original confidence intervals
            validity_report: Validation report for this horizon
            
        Returns:
            Tuple of (filtered_forecasts, filtered_intervals)
        """
        filtered_forecasts = {}
        filtered_intervals = {}
        
        for var_name, value in forecast_results.items():
            if var_name in validity_report.variable_results:
                result = validity_report.variable_results[var_name]
                
                if result.is_valid:
                    # Include valid variables
                    filtered_forecasts[var_name] = value
                    if var_name in confidence_intervals:
                        filtered_intervals[var_name] = confidence_intervals[var_name]
                else:
                    # Log excluded variables
                    logger.info(f"🚫 Excluding {var_name} from forecast: {result.availability_status.value}")
            else:
                # Include variables not checked (for compatibility)
                filtered_forecasts[var_name] = value
                if var_name in confidence_intervals:
                    filtered_intervals[var_name] = confidence_intervals[var_name]
        
        return filtered_forecasts, filtered_intervals
    
    def get_validity_summary(self, reports: Optional[List[HorizonValidityReport]] = None) -> str:
        """Get human-readable validity summary.
        
        Args:
            reports: Specific reports to summarize (uses recent history if None)
            
        Returns:
            Formatted summary string
        """
        if reports is None:
            reports = self.validation_history[-4:]  # Last 4 horizons
        
        if not reports:
            return "No validation reports available"
        
        lines = ["🔍 Variable Validity Summary"]
        lines.append("=" * 40)
        
        for report in reports:
            lines.append(f"\n📍 Horizon {report.horizon}h:")
            lines.append(f"   Valid variables: {report.valid_variables}/{report.total_variables}")
            lines.append(f"   Overall confidence: {report.overall_confidence:.1%}")
            
            # Quality distribution
            quality_items = [f"{k}: {v}" for k, v in report.quality_distribution.items() if v > 0]
            if quality_items:
                lines.append(f"   Quality: {', '.join(quality_items)}")
            
            # Critical issues
            if report.critical_issues:
                lines.append(f"   Critical issues: {len(report.critical_issues)}")
                for issue in report.critical_issues[:2]:  # Show first 2
                    lines.append(f"     - {issue}")
            
            # Warnings
            if report.warnings:
                lines.append(f"   Warnings: {len(report.warnings)}")
        
        return "\n".join(lines)

def main():
    """Demonstration of variable validity thresholds."""
    # Initialize system
    validity_system = VariableValidityThresholds()
    
    # Create synthetic test data
    n_analogs = 25
    n_variables = 9
    
    # Create outcomes with some variables having insufficient coverage
    analog_outcomes = np.random.randn(n_analogs, n_variables) * 10 + 273.15  # Temperature-like
    
    # Simulate insufficient coverage for some variables
    analog_outcomes[:15, 5] = 0.0  # v10 has many zeros
    analog_outcomes[:5, 8] = np.nan  # CAPE has many NaN
    
    analog_weights = np.ones(n_analogs) / n_analogs
    
    # Test validation
    report = validity_system.validate_horizon_forecast(
        analog_outcomes, analog_weights, horizon=24
    )
    
    print(f"Validation completed for {report.total_variables} variables")
    print(f"Valid: {report.valid_variables}, Invalid: {report.invalid_variables}")
    print(f"Overall confidence: {report.overall_confidence:.1%}")
    
    if report.critical_issues:
        print(f"\nCritical issues ({len(report.critical_issues)}):")
        for issue in report.critical_issues:
            print(f"  - {issue}")
    
    print("\nVariable details:")
    for var_name, result in report.variable_results.items():
        print(f"  {var_name}: {result.availability_status.value} "
              f"({result.analogs_available}/{result.analogs_required}, "
              f"confidence: {result.confidence_factor:.2f})")

if __name__ == "__main__":
    main()