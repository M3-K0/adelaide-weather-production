#!/usr/bin/env python3
"""
Per-Variable Quality Monitoring and N/A Display Framework
=========================================================

Implements comprehensive per-variable validity monitoring, min_analogs threshold
enforcement, and proper N/A display for insufficient valid data. Prevents silent
failures through horizon-level confidence degradation tracking.

DESIGN PRINCIPLES:
- Per-variable min_analogs threshold enforcement
- N/A display for insufficient valid data (never zeros)
- Horizon-level confidence degradation when variables unavailable
- Variable order/units canonicalization (Kelvin storage, Celsius display)
- Continuous validity monitoring with alerts

Author: Production QA Framework  
Version: 1.0.0 - Variable Quality Gates
"""

import logging
import warnings
from typing import Dict, List, Optional, Tuple, Any, Union
from dataclasses import dataclass, asdict
from datetime import datetime
from enum import Enum

import numpy as np
import pandas as pd

logger = logging.getLogger(__name__)

class VariableStatus(Enum):
    """Variable availability status."""
    AVAILABLE = "available"          # Sufficient valid data
    INSUFFICIENT = "insufficient"    # Below min_analogs threshold
    UNAVAILABLE = "unavailable"      # No valid data
    DEGRADED = "degraded"           # Quality issues detected

@dataclass
class VariableQualityMetrics:
    """Quality metrics for a single variable."""
    variable_name: str
    total_analogs: int
    valid_analogs: int
    validity_ratio: float
    min_analogs_threshold: int
    status: VariableStatus
    quality_score: float  # 0-1 quality score
    
    # Data quality indicators
    has_outliers: bool
    outlier_count: int
    range_violation_count: int
    temporal_consistency_score: float
    
    # Display formatting
    canonical_units: str
    display_units: str
    conversion_factor: float
    
    def is_available(self) -> bool:
        return self.status == VariableStatus.AVAILABLE
    
    def requires_na_display(self) -> bool:
        return self.status in [VariableStatus.INSUFFICIENT, VariableStatus.UNAVAILABLE]

@dataclass
class HorizonQualityAssessment:
    """Quality assessment for a specific forecast horizon."""
    horizon: int
    timestamp: str
    
    # Per-variable metrics
    variable_metrics: Dict[str, VariableQualityMetrics]
    
    # Horizon-level aggregates
    available_variables: List[str]
    degraded_variables: List[str]
    unavailable_variables: List[str]
    
    # Confidence degradation
    baseline_confidence: float  # Confidence with all variables
    actual_confidence: float    # Degraded confidence with missing variables
    confidence_degradation: float
    
    # Overall assessment
    horizon_status: str  # 'operational', 'degraded', 'compromised'
    forecast_reliability: str  # 'high', 'medium', 'low', 'unreliable'

class VariableQualityMonitor:
    """Production-grade per-variable quality monitoring system."""
    
    # Variable definitions with canonical properties
    VARIABLE_DEFINITIONS = {
        'z500': {
            'name': 'Geopotential Height 500mb',
            'canonical_units': 'gpm',  # Geopotential meters
            'display_units': 'gpm',
            'conversion_factor': 1.0,
            'valid_range': (4800, 6200),
            'min_analogs': 15,
            'quality_weight': 1.0,
            'outlier_threshold': 3.0  # Standard deviations
        },
        't2m': {
            'name': '2m Temperature',
            'canonical_units': 'K',     # Kelvin storage
            'display_units': '°C',      # Celsius display
            'conversion_factor': -273.15,  # K to C conversion (additive)
            'valid_range': (200, 350),  # Kelvin range
            'display_range': (-73, 77), # Celsius range
            'min_analogs': 20,
            'quality_weight': 1.5,
            'outlier_threshold': 2.5
        },
        't850': {
            'name': 'Temperature 850mb',
            'canonical_units': 'K',
            'display_units': '°C',
            'conversion_factor': -273.15,
            'valid_range': (200, 340),
            'display_range': (-73, 67),
            'min_analogs': 15,
            'quality_weight': 1.0,
            'outlier_threshold': 2.5
        },
        'q850': {
            'name': 'Specific Humidity 850mb',
            'canonical_units': 'kg/kg',
            'display_units': 'g/kg',
            'conversion_factor': 1000.0,  # kg/kg to g/kg
            'valid_range': (0, 0.030),
            'display_range': (0, 30),
            'min_analogs': 12,
            'quality_weight': 0.8,
            'outlier_threshold': 3.0
        },
        'u10': {
            'name': 'U-Wind 10m',
            'canonical_units': 'm/s',
            'display_units': 'm/s',
            'conversion_factor': 1.0,
            'valid_range': (-50, 50),
            'min_analogs': 15,
            'quality_weight': 1.0,
            'outlier_threshold': 3.0
        },
        'v10': {
            'name': 'V-Wind 10m',
            'canonical_units': 'm/s',
            'display_units': 'm/s',
            'conversion_factor': 1.0,
            'valid_range': (-50, 50),
            'min_analogs': 15,
            'quality_weight': 1.0,
            'outlier_threshold': 3.0
        },
        'u850': {
            'name': 'U-Wind 850mb',
            'canonical_units': 'm/s',
            'display_units': 'm/s',
            'conversion_factor': 1.0,
            'valid_range': (-80, 80),
            'min_analogs': 12,
            'quality_weight': 0.8,
            'outlier_threshold': 3.0
        },
        'v850': {
            'name': 'V-Wind 850mb',
            'canonical_units': 'm/s',
            'display_units': 'm/s',
            'conversion_factor': 1.0,
            'valid_range': (-80, 80),
            'min_analogs': 12,
            'quality_weight': 0.8,
            'outlier_threshold': 3.0
        },
        'cape': {
            'name': 'Convective Available Potential Energy',
            'canonical_units': 'J/kg',
            'display_units': 'J/kg',
            'conversion_factor': 1.0,
            'valid_range': (0, 8000),
            'min_analogs': 10,
            'quality_weight': 0.5,
            'outlier_threshold': 4.0
        }
    }
    
    def __init__(self, strict_mode: bool = True):
        """Initialize variable quality monitor.
        
        Args:
            strict_mode: Enable strict quality gates for production
        """
        self.strict_mode = strict_mode
        self.quality_history = []
        
        # Quality thresholds
        self.global_min_analogs = 10
        self.confidence_degradation_per_missing_var = 0.15
        self.quality_score_threshold = 0.7
        
        logger.info(f"🔍 Variable Quality Monitor initialized (strict_mode={strict_mode})")
        logger.info(f"   Monitoring {len(self.VARIABLE_DEFINITIONS)} variables")
    
    def assess_variable_quality(self, variable_name: str, analog_data: np.ndarray,
                              analog_indices: np.ndarray) -> VariableQualityMetrics:
        """Assess quality metrics for a single variable.
        
        Args:
            variable_name: Name of the variable to assess
            analog_data: Array of analog values for this variable
            analog_indices: Indices of the analogs used
            
        Returns:
            VariableQualityMetrics with comprehensive quality assessment
        """
        if variable_name not in self.VARIABLE_DEFINITIONS:
            logger.warning(f"Unknown variable {variable_name}, using default settings")
            var_def = {
                'min_analogs': self.global_min_analogs,
                'valid_range': (-1e6, 1e6),
                'quality_weight': 1.0,
                'outlier_threshold': 3.0,
                'canonical_units': 'unknown',
                'display_units': 'unknown',
                'conversion_factor': 1.0
            }
        else:
            var_def = self.VARIABLE_DEFINITIONS[variable_name]
        
        total_analogs = len(analog_data)
        min_threshold = var_def['min_analogs']
        
        # Validity checks
        valid_mask = np.isfinite(analog_data)
        
        # Range validation
        if 'valid_range' in var_def:
            valid_range = var_def['valid_range']
            valid_mask &= (analog_data >= valid_range[0]) & (analog_data <= valid_range[1])
        
        valid_analogs = np.sum(valid_mask)
        validity_ratio = valid_analogs / total_analogs if total_analogs > 0 else 0
        
        # Outlier detection
        if valid_analogs > 3:
            valid_data = analog_data[valid_mask]
            mean_val = np.mean(valid_data)
            std_val = np.std(valid_data)
            outlier_threshold = var_def['outlier_threshold']
            
            z_scores = np.abs((valid_data - mean_val) / (std_val + 1e-8))
            outliers = z_scores > outlier_threshold
            outlier_count = np.sum(outliers)
            has_outliers = outlier_count > 0
        else:
            outlier_count = 0
            has_outliers = False
        
        # Range violations
        range_violation_count = total_analogs - valid_analogs
        
        # Temporal consistency (simplified - based on variance)
        if valid_analogs > 5:
            valid_data = analog_data[valid_mask]
            coefficient_of_variation = np.std(valid_data) / (np.abs(np.mean(valid_data)) + 1e-8)
            temporal_consistency_score = max(0, 1.0 - coefficient_of_variation)
        else:
            temporal_consistency_score = 0.0
        
        # Overall quality score
        quality_components = [
            validity_ratio,
            max(0, 1.0 - outlier_count / max(1, valid_analogs)),
            temporal_consistency_score,
            min(1.0, valid_analogs / min_threshold)
        ]
        quality_score = np.mean(quality_components)
        
        # Determine status
        if valid_analogs >= min_threshold and quality_score >= self.quality_score_threshold:
            status = VariableStatus.AVAILABLE
        elif valid_analogs >= self.global_min_analogs:
            status = VariableStatus.DEGRADED
        elif valid_analogs > 0:
            status = VariableStatus.INSUFFICIENT
        else:
            status = VariableStatus.UNAVAILABLE
        
        return VariableQualityMetrics(
            variable_name=variable_name,
            total_analogs=total_analogs,
            valid_analogs=valid_analogs,
            validity_ratio=validity_ratio,
            min_analogs_threshold=min_threshold,
            status=status,
            quality_score=quality_score,
            has_outliers=has_outliers,
            outlier_count=outlier_count,
            range_violation_count=range_violation_count,
            temporal_consistency_score=temporal_consistency_score,
            canonical_units=var_def['canonical_units'],
            display_units=var_def['display_units'],
            conversion_factor=var_def['conversion_factor']
        )
    
    def assess_horizon_quality(self, horizon: int, analog_outcomes: np.ndarray,
                             analog_indices: np.ndarray, baseline_confidence: float = 1.0) -> HorizonQualityAssessment:
        """Assess quality for all variables at a specific horizon.
        
        Args:
            horizon: Forecast horizon in hours
            analog_outcomes: Array of shape (n_analogs, n_variables)
            analog_indices: Indices of analogs used
            baseline_confidence: Baseline confidence level
            
        Returns:
            HorizonQualityAssessment with comprehensive horizon analysis
        """
        variable_names = list(self.VARIABLE_DEFINITIONS.keys())[:analog_outcomes.shape[1]]
        variable_metrics = {}
        
        # Assess each variable
        for i, var_name in enumerate(variable_names):
            if i < analog_outcomes.shape[1]:
                var_data = analog_outcomes[:, i]
                metrics = self.assess_variable_quality(var_name, var_data, analog_indices)
                variable_metrics[var_name] = metrics
        
        # Categorize variables by status
        available_variables = [name for name, metrics in variable_metrics.items() 
                             if metrics.is_available()]
        degraded_variables = [name for name, metrics in variable_metrics.items() 
                            if metrics.status == VariableStatus.DEGRADED]
        unavailable_variables = [name for name, metrics in variable_metrics.items() 
                               if metrics.status in [VariableStatus.INSUFFICIENT, VariableStatus.UNAVAILABLE]]
        
        # Calculate confidence degradation
        missing_weight = sum(self.VARIABLE_DEFINITIONS[var]['quality_weight'] 
                           for var in unavailable_variables 
                           if var in self.VARIABLE_DEFINITIONS)
        total_weight = sum(self.VARIABLE_DEFINITIONS[var]['quality_weight'] 
                         for var in variable_names 
                         if var in self.VARIABLE_DEFINITIONS)
        
        confidence_degradation = (missing_weight / total_weight) if total_weight > 0 else 0
        actual_confidence = baseline_confidence * (1.0 - confidence_degradation)
        
        # Determine horizon status
        if len(unavailable_variables) == 0:
            horizon_status = 'operational'
            forecast_reliability = 'high'
        elif len(unavailable_variables) <= 2:
            horizon_status = 'degraded'
            forecast_reliability = 'medium' if actual_confidence > 0.6 else 'low'
        else:
            horizon_status = 'compromised'
            forecast_reliability = 'unreliable'
        
        return HorizonQualityAssessment(
            horizon=horizon,
            timestamp=datetime.now().isoformat(),
            variable_metrics=variable_metrics,
            available_variables=available_variables,
            degraded_variables=degraded_variables,
            unavailable_variables=unavailable_variables,
            baseline_confidence=baseline_confidence,
            actual_confidence=actual_confidence,
            confidence_degradation=confidence_degradation,
            horizon_status=horizon_status,
            forecast_reliability=forecast_reliability
        )
    
    def format_variable_for_display(self, variable_name: str, value: Optional[float],
                                  confidence_interval: Optional[Tuple[float, float]] = None) -> str:
        """Format variable value for display with proper units and N/A handling.
        
        Args:
            variable_name: Name of the variable
            value: Variable value in canonical units (or None for N/A)
            confidence_interval: Optional confidence interval
            
        Returns:
            Formatted display string
        """
        if variable_name not in self.VARIABLE_DEFINITIONS:
            if value is None:
                return "N/A"
            return f"{value:.2f}"
        
        var_def = self.VARIABLE_DEFINITIONS[variable_name]
        display_name = var_def['name']
        display_units = var_def['display_units']
        conversion = var_def['conversion_factor']
        
        if value is None:
            return f"{display_name}: N/A"
        
        # Apply unit conversion
        if conversion != 1.0:
            if variable_name in ['t2m', 't850']:  # Additive conversion (K to C)
                display_value = value + conversion
            else:  # Multiplicative conversion
                display_value = value * conversion
        else:
            display_value = value
        
        # Format with confidence interval if available
        if confidence_interval is not None:
            low, high = confidence_interval
            if conversion != 1.0:
                if variable_name in ['t2m', 't850']:
                    low += conversion
                    high += conversion
                else:
                    low *= conversion
                    high *= conversion
            
            uncertainty = (high - low) / 2
            return f"{display_name}: {display_value:.1f} ± {uncertainty:.1f} {display_units}"
        else:
            return f"{display_name}: {display_value:.1f} {display_units}"
    
    def generate_quality_report(self, assessment: HorizonQualityAssessment) -> str:
        """Generate human-readable quality assessment report.
        
        Args:
            assessment: Horizon quality assessment
            
        Returns:
            Formatted quality report string
        """
        lines = []
        lines.append(f"📊 Variable Quality Report - Horizon +{assessment.horizon}h")
        lines.append("=" * 60)
        
        # Summary
        total_vars = len(assessment.variable_metrics)
        available_count = len(assessment.available_variables)
        
        lines.append(f"Overall Status: {assessment.horizon_status.upper()}")
        lines.append(f"Forecast Reliability: {assessment.forecast_reliability.upper()}")
        lines.append(f"Available Variables: {available_count}/{total_vars}")
        lines.append(f"Confidence: {assessment.actual_confidence:.1%} "
                    f"(degraded by {assessment.confidence_degradation:.1%})")
        lines.append("")
        
        # Variable details
        lines.append("Variable Status:")
        for var_name, metrics in assessment.variable_metrics.items():
            status_emoji = {
                VariableStatus.AVAILABLE: "✅",
                VariableStatus.DEGRADED: "⚠️",
                VariableStatus.INSUFFICIENT: "❌",
                VariableStatus.UNAVAILABLE: "🚫"
            }
            
            emoji = status_emoji.get(metrics.status, "❓")
            var_def = self.VARIABLE_DEFINITIONS.get(var_name, {})
            display_name = var_def.get('name', var_name)
            
            lines.append(f"  {emoji} {display_name}: {metrics.valid_analogs}/{metrics.total_analogs} "
                        f"valid (≥{metrics.min_analogs_threshold} required)")
            
            if metrics.status != VariableStatus.AVAILABLE:
                if metrics.has_outliers:
                    lines.append(f"     • {metrics.outlier_count} outliers detected")
                if metrics.range_violation_count > 0:
                    lines.append(f"     • {metrics.range_violation_count} range violations")
                if metrics.quality_score < self.quality_score_threshold:
                    lines.append(f"     • Quality score: {metrics.quality_score:.2f}")
        
        # Recommendations
        lines.append("")
        if assessment.unavailable_variables:
            lines.append("⚠️  Recommendations:")
            lines.append("   • Display N/A for unavailable variables")
            lines.append("   • Apply confidence degradation to forecast")
            if assessment.forecast_reliability == 'unreliable':
                lines.append("   • Consider forecast suppression or warning")
        
        return "\n".join(lines)
    
    def validate_analog_quality(self, distances: np.ndarray, indices: np.ndarray) -> Dict[str, Any]:
        """Validate analog search results for quality issues.
        
        Args:
            distances: Distance/similarity scores from FAISS search
            indices: Analog indices from FAISS search
            
        Returns:
            Dictionary with quality validation results
        """
        validation_results = {
            'total_analogs': len(indices),
            'unique_analogs': len(np.unique(indices)),
            'duplicate_count': len(indices) - len(np.unique(indices)),
            'mean_similarity': float(np.mean(distances)),
            'similarity_variance': float(np.var(distances)),
            'similarity_range': float(np.max(distances) - np.min(distances)),
            'quality_issues': []
        }
        
        # Check for duplicate analogs
        if validation_results['duplicate_count'] > 0:
            validation_results['quality_issues'].append(
                f"Duplicate analogs detected: {validation_results['duplicate_count']}"
            )
        
        # Check for degenerate similarity scores
        if validation_results['similarity_variance'] < 1e-6:
            validation_results['quality_issues'].append(
                "Degenerate similarity scores (low variance)"
            )
        
        # Check for unrealistic similarity range
        if validation_results['similarity_range'] < 0.01:
            validation_results['quality_issues'].append(
                "Suspicious similarity range (too narrow)"
            )
        
        # Check for negative similarities (should not happen with cosine)
        if np.any(distances < 0):
            validation_results['quality_issues'].append(
                "Negative similarity scores detected"
            )
        
        return validation_results
    
    def log_quality_assessment(self, assessment: HorizonQualityAssessment):
        """Log quality assessment with appropriate severity levels.
        
        Args:
            assessment: Horizon quality assessment to log
        """
        # Store in history
        self.quality_history.append(assessment)
        
        # Log summary
        if assessment.horizon_status == 'operational':
            logger.info(f"✅ H+{assessment.horizon}h: Operational quality, "
                       f"{len(assessment.available_variables)}/{len(assessment.variable_metrics)} variables available")
        elif assessment.horizon_status == 'degraded':
            logger.warning(f"⚠️ H+{assessment.horizon}h: Degraded quality, "
                          f"missing {assessment.unavailable_variables}")
        else:
            logger.error(f"❌ H+{assessment.horizon}h: Compromised quality, "
                        f"reliability={assessment.forecast_reliability}")
        
        # Log specific variable issues
        for var_name, metrics in assessment.variable_metrics.items():
            if metrics.requires_na_display():
                logger.warning(f"   {var_name}: {metrics.valid_analogs}/{metrics.total_analogs} "
                             f"valid (requires N/A display)")

def main():
    """Demonstration of variable quality monitoring."""
    monitor = VariableQualityMonitor(strict_mode=True)
    
    # Mock analog data for testing
    n_analogs = 50
    n_variables = 9
    
    # Simulate some quality issues
    analog_outcomes = np.random.randn(n_analogs, n_variables)
    
    # Add realistic scales and some invalid data
    analog_outcomes[:, 0] = 5500 + analog_outcomes[:, 0] * 200  # z500
    analog_outcomes[:, 1] = 293 + analog_outcomes[:, 1] * 10    # t2m (K)
    analog_outcomes[:, 2] = 285 + analog_outcomes[:, 2] * 8     # t850 (K)
    analog_outcomes[:, 3] = 0.008 + analog_outcomes[:, 3] * 0.004  # q850
    analog_outcomes[:, 4:6] *= 5  # winds
    analog_outcomes[:, 6:8] *= 8  # upper level winds
    analog_outcomes[:, 8] = np.abs(analog_outcomes[:, 8]) * 200  # CAPE
    
    # Introduce some quality issues
    analog_outcomes[45:, 1] = np.nan  # Missing t2m data
    analog_outcomes[40:, 3] = -999    # Invalid q850 data
    
    analog_indices = np.arange(n_analogs)
    
    # Test assessment
    assessment = monitor.assess_horizon_quality(24, analog_outcomes, analog_indices, 0.85)
    
    # Display results
    print(monitor.generate_quality_report(assessment))
    
    # Test variable formatting
    print("\nVariable Display Examples:")
    print(monitor.format_variable_for_display('t2m', 293.15, (290.15, 296.15)))
    print(monitor.format_variable_for_display('u10', None))  # N/A case
    print(monitor.format_variable_for_display('z500', 5640, (5600, 5680)))

if __name__ == "__main__":
    main()