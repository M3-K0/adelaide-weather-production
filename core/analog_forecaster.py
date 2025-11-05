#!/usr/bin/env python3
"""
Real-Time Analog Forecaster
==========================

Implements GPT-5's validated ensemble methodology for converting historical
analog patterns into actual weather forecasts with uncertainty quantification.

Features:
- Kernel-based soft weighting with adaptive temperature parameters
- Non-parametric uncertainty quantification using weighted empirical distributions
- Weighted quantiles for confidence intervals (5th-95th percentile)
- Memory-mapped outcomes access for O(100μs) performance
- Professional forecast formatting with confidence bounds

Based on GPT-5 expert recommendations for production-ready ensemble forecasting.
"""

import numpy as np
import pandas as pd
from pathlib import Path
from typing import Dict, List, Optional, Tuple, Any
import logging
from dataclasses import dataclass

# Setup logging
logger = logging.getLogger(__name__)

@dataclass
class ForecastResult:
    """Container for forecast results with uncertainty."""
    horizon: int
    forecast_time: pd.Timestamp
    variables: Dict[str, float]  # Point forecasts
    confidence_intervals: Dict[str, Tuple[float, float]]  # 5th-95th percentiles
    confidence_level: float  # Overall confidence (0-1)
    ensemble_size: int  # Number of analogs used
    
    def __str__(self) -> str:
        """Professional forecast formatting."""
        lines = [f"🌤️ Adelaide Weather Forecast (+{self.horizon}h):"]
        lines.append(f"   Valid: {self.forecast_time.strftime('%Y-%m-%d %H:%M UTC')}")
        lines.append(f"   Confidence: {self.confidence_level*100:.0f}% | Ensemble: {self.ensemble_size} analogs")
        lines.append("")
        
        # Format key variables with confidence intervals
        var_names = {
            't2m': '🌡️  Temperature',
            'u10': '🌪️  Wind (U)',  
            'v10': '🌪️  Wind (V)',
            'q850': '💧 Humidity',
            'z500': '📈 Pressure'
        }
        
        for var, name in var_names.items():
            if var in self.variables:
                value = self.variables[var]
                if var in self.confidence_intervals:
                    low, high = self.confidence_intervals[var]
                    lines.append(f"   {name}: {value:.1f} ± {(high-low)/2:.1f} [{low:.1f}, {high:.1f}]")
                else:
                    lines.append(f"   {name}: {value:.1f}")
        
        return "\n".join(lines)

class RealTimeAnalogForecaster:
    """Real-time analog ensemble forecaster with GPT-5 methodology."""
    
    def __init__(self, outcomes_dir: Path = Path("outcomes")):
        self.outcomes_dir = outcomes_dir
        self.outcomes_cache = {}  # Memory-mapped arrays
        self.metadata_cache = {}  # Metadata DataFrames
        
        # Variable definitions (same as training)
        self.variables = [
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
        
        # Adaptive temperature parameters (learned per horizon)
        # These control the softness of the weighting function
        self.temperature_params = {
            6: 0.1,    # Sharp weighting for short-term
            12: 0.15,  # Medium weighting 
            24: 0.2,   # Softer weighting for longer-term
            48: 0.3    # Very soft weighting for 48h
        }
        
        # Confidence parameters
        self.min_analogs = 10      # Minimum analogs for reliable forecast
        self.max_analogs = 50      # Maximum analogs to consider
        self.confidence_threshold = 0.8  # Minimum confidence for "high confidence"
        
    def load_outcomes_for_horizon(self, horizon: int) -> bool:
        """Load outcomes and metadata for specified horizon."""
        if horizon in self.outcomes_cache:
            return True  # Already loaded
            
        try:
            # Load memory-mapped outcomes array
            outcomes_path = self.outcomes_dir / f"outcomes_{horizon}h.npy"
            if not outcomes_path.exists():
                logger.error(f"❌ Outcomes not found: {outcomes_path}")
                return False
                
            # Memory-map for O(100μs) access
            outcomes = np.load(outcomes_path, mmap_mode='r')
            self.outcomes_cache[horizon] = outcomes
            
            # Load metadata
            metadata_path = self.outcomes_dir / f"metadata_{horizon}h_clean.parquet"
            if not metadata_path.exists():
                logger.error(f"❌ Metadata not found: {metadata_path}")
                return False
                
            metadata = pd.read_parquet(metadata_path)
            self.metadata_cache[horizon] = metadata
            
            logger.info(f"✅ Loaded {horizon}h outcomes: {outcomes.shape} | {outcomes.nbytes/1024/1024:.1f}MB")
            return True
            
        except Exception as e:
            logger.error(f"❌ Failed to load outcomes for {horizon}h: {e}")
            return False
    
    def compute_analog_weights(self, distances: np.ndarray, horizon: int) -> np.ndarray:
        """Compute kernel-based soft weights using adaptive temperature."""
        # Get temperature parameter for this horizon
        tau = self.temperature_params.get(horizon, 0.2)
        
        # Apply softmax weighting: w_i = softmax(-distance_i / τ)
        # Negative distances because smaller distance = higher weight
        logits = -distances / tau
        
        # Numerical stability: subtract max before exp
        logits_stable = logits - np.max(logits)
        weights = np.exp(logits_stable)
        weights = weights / np.sum(weights)
        
        return weights
    
    def compute_ensemble_statistics(self, outcomes: np.ndarray, weights: np.ndarray) -> Dict[str, Any]:
        """Compute weighted ensemble statistics with uncertainty quantification."""
        n_vars = outcomes.shape[1]
        statistics = {}
        
        for i, var_name in enumerate(self.variables):
            values = outcomes[:, i]
            
            # Data validation: filter out invalid values (especially zeros for temperature)
            valid_mask = values > 0 if var_name in ['t2m', 't850'] else np.ones_like(values, dtype=bool)
            
            # If too many invalid values, skip this variable
            if np.sum(valid_mask) < len(values) * 0.5:  # Less than 50% valid
                logger.warning(f"⚠️ Insufficient valid data for {var_name}: {np.sum(valid_mask)}/{len(values)} valid")
                continue
            
            # Filter to valid values and corresponding weights
            valid_values = values[valid_mask]
            valid_weights = weights[valid_mask]
            
            # Renormalize weights
            valid_weights = valid_weights / np.sum(valid_weights)
            
            # Weighted mean (point forecast)
            weighted_mean = np.average(valid_values, weights=valid_weights)
            
            # Weighted quantiles for uncertainty bounds
            sorted_indices = np.argsort(valid_values)
            sorted_values = valid_values[sorted_indices]
            sorted_weights = valid_weights[sorted_indices]
            
            # Cumulative weights
            cumsum_weights = np.cumsum(sorted_weights)
            
            # Find 5th and 95th percentiles
            q05_idx = np.searchsorted(cumsum_weights, 0.05)
            q95_idx = np.searchsorted(cumsum_weights, 0.95)
            
            # Ensure valid indices
            q05_idx = max(0, min(q05_idx, len(sorted_values) - 1))
            q95_idx = max(0, min(q95_idx, len(sorted_values) - 1))
            
            q05 = sorted_values[q05_idx]
            q95 = sorted_values[q95_idx]
            
            # Weighted standard deviation
            weighted_var = np.average((valid_values - weighted_mean)**2, weights=valid_weights)
            weighted_std = np.sqrt(weighted_var)
            
            statistics[var_name] = {
                'mean': weighted_mean,
                'std': weighted_std,
                'q05': q05,
                'q95': q95,
                'range': q95 - q05
            }
            
        return statistics
    
    def assess_forecast_confidence(self, distances: np.ndarray, weights: np.ndarray, 
                                 horizon: int) -> float:
        """Assess overall forecast confidence based on analog quality."""
        # Factors affecting confidence:
        # 1. Concentration of weights (fewer dominant analogs = higher confidence)
        # 2. Quality of best analogs (smaller distances = higher confidence) 
        # 3. Number of analogs available
        # 4. Horizon length (shorter = higher confidence)
        
        # Weight concentration (entropy-based)
        # High concentration (low entropy) = high confidence
        entropy = -np.sum(weights * np.log(weights + 1e-12))
        max_entropy = np.log(len(weights))
        concentration = 1.0 - (entropy / max_entropy)
        
        # Analog quality (inverse of mean distance)
        mean_distance = np.average(distances, weights=weights)
        quality = 1.0 / (1.0 + mean_distance)  # Normalize to [0,1]
        
        # Sample size factor
        n_analogs = len(distances)
        sample_factor = min(1.0, n_analogs / self.min_analogs)
        
        # Horizon penalty (longer forecasts less confident)
        horizon_factor = 1.0 / (1.0 + horizon / 24.0)  # Decay with horizon
        
        # Combine factors
        confidence = (concentration * 0.4 + 
                     quality * 0.3 + 
                     sample_factor * 0.2 + 
                     horizon_factor * 0.1)
        
        return min(1.0, max(0.0, confidence))
    
    def generate_forecast(self, analog_results: Dict[str, Any], horizon: int) -> Optional[ForecastResult]:
        """Generate ensemble forecast from analog search results."""
        try:
            # Extract analog information
            analog_indices = analog_results['indices']
            distances = analog_results['distances']
            init_time = analog_results['init_time']
            
            # Validate inputs
            if len(analog_indices) == 0:
                logger.warning(f"No analogs found for {horizon}h forecast")
                return None
                
            # Load outcomes for this horizon
            if not self.load_outcomes_for_horizon(horizon):
                return None
                
            outcomes = self.outcomes_cache[horizon]
            metadata = self.metadata_cache[horizon]
            
            # Get outcomes for selected analogs
            analog_outcomes = outcomes[analog_indices]
            
            # Limit number of analogs
            max_analogs = min(self.max_analogs, len(analog_indices))
            analog_outcomes = analog_outcomes[:max_analogs]
            distances = distances[:max_analogs]
            analog_indices = analog_indices[:max_analogs]
            
            # Compute adaptive weights
            weights = self.compute_analog_weights(distances, horizon)
            
            # Generate ensemble statistics
            stats = self.compute_ensemble_statistics(analog_outcomes, weights)
            
            # Assess forecast confidence
            confidence = self.assess_forecast_confidence(distances, weights, horizon)
            
            # Calculate forecast valid time
            forecast_time = init_time + pd.Timedelta(hours=horizon)
            
            # Extract point forecasts and confidence intervals
            variables = {}
            confidence_intervals = {}
            
            for var_name in self.variables:
                if var_name in stats:
                    variables[var_name] = stats[var_name]['mean']
                    confidence_intervals[var_name] = (
                        stats[var_name]['q05'],
                        stats[var_name]['q95']
                    )
            
            # Create forecast result
            forecast = ForecastResult(
                horizon=horizon,
                forecast_time=forecast_time,
                variables=variables,
                confidence_intervals=confidence_intervals,
                confidence_level=confidence,
                ensemble_size=max_analogs
            )
            
            logger.info(f"✅ Generated {horizon}h forecast: {confidence*100:.0f}% confidence, {max_analogs} analogs")
            return forecast
            
        except Exception as e:
            logger.error(f"❌ Failed to generate {horizon}h forecast: {e}")
            return None
    
    def generate_multi_horizon_forecast(self, analog_results_dict: Dict[int, Dict[str, Any]]) -> Dict[int, ForecastResult]:
        """Generate forecasts for multiple horizons."""
        forecasts = {}
        
        for horizon, analog_results in analog_results_dict.items():
            forecast = self.generate_forecast(analog_results, horizon)
            if forecast is not None:
                forecasts[horizon] = forecast
            else:
                logger.warning(f"⚠️ Failed to generate forecast for {horizon}h")
                
        return forecasts
    
    def format_forecast_summary(self, forecasts: Dict[int, ForecastResult]) -> str:
        """Format multi-horizon forecast summary."""
        if not forecasts:
            return "❌ No forecasts available"
            
        lines = ["🌤️ Adelaide Weather Forecast Summary"]
        lines.append("=" * 45)
        
        for horizon in sorted(forecasts.keys()):
            forecast = forecasts[horizon]
            lines.append(f"\n📍 +{horizon}h | {forecast.forecast_time.strftime('%m/%d %H:%M')}")
            
            # Key variables with units
            if 't2m' in forecast.variables:
                temp_c = forecast.variables['t2m'] - 273.15  # Convert K to C
                temp_low, temp_high = forecast.confidence_intervals.get('t2m', (temp_c, temp_c))
                temp_low_c = temp_low - 273.15
                temp_high_c = temp_high - 273.15
                lines.append(f"   🌡️  {temp_c:.1f}°C ± {(temp_high_c-temp_low_c)/2:.1f} [{temp_low_c:.1f}, {temp_high_c:.1f}]")
            
            if 'u10' in forecast.variables and 'v10' in forecast.variables:
                u10 = forecast.variables['u10']
                v10 = forecast.variables['v10']
                wind_speed = np.sqrt(u10**2 + v10**2)
                wind_dir = np.degrees(np.arctan2(v10, u10)) % 360
                lines.append(f"   💨 {wind_speed:.1f} m/s @ {wind_dir:.0f}°")
            
            lines.append(f"   📊 {forecast.confidence_level*100:.0f}% confidence ({forecast.ensemble_size} analogs)")
        
        return "\n".join(lines)