#!/usr/bin/env python3
"""
Forecast Adapter
================

Bridges the secure API with the core forecasting system, handling schema mismatches,
variable mapping, and graceful degradation. Provides the missing `forecast_with_uncertainty`
method that the API expects.

Features:
- Variable schema mapping between API and forecaster
- Humidity conversion (q850 → r850) 
- Graceful fallback when variables unavailable
- Mock analog search until real component available
- Unit conversions and error handling
- Maintains API response format compatibility

Author: Integration Layer
Version: 1.0.0 - Production Bridge
"""

import os
import sys
import logging
import asyncio
import math
import numpy as np
from datetime import datetime, timezone
from typing import Dict, List, Optional, Any, Tuple
from pathlib import Path

# Add parent directory to path for imports
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Core forecasting system
from core.analog_forecaster import RealTimeAnalogForecaster

# Variable definitions and conversion utilities  
from api.variables import (
    VARIABLE_ORDER, VARIABLE_SPECS, VALID_HORIZONS, DEFAULT_VARIABLES,
    convert_value
)

# Production analog search service
from api.services import get_analog_search_service

logger = logging.getLogger(__name__)

class ForecastAdapter:
    """
    Adapter that bridges API expectations with core forecaster capabilities.
    
    Handles:
    1. Missing forecast_with_uncertainty() method implementation
    2. Variable schema mapping (API vs forecaster variables)
    3. Production analog search via AnalogSearchService
    4. Unit conversions and graceful degradation
    """
    
    def __init__(self):
        """Initialize the forecast adapter."""
        self.forecaster = RealTimeAnalogForecaster()
        self.analog_service = None  # Will be initialized async
        
        # Variable mapping: API variable → forecaster variable
        self.variable_mapping = {
            # Direct mappings (same variable)
            't2m': 't2m',
            'u10': 'u10', 
            'v10': 'v10',
            'cape': 'cape',
            't850': 't850',
            'z500': 'z500',
            
            # Complex mappings (need conversion)
            'r850': 'q850',  # Relative humidity ← specific humidity
            
            # Derived variables (computed from other forecaster variables)
            'msl': 'z500',   # Mean sea level pressure derived from z500 via hypsometric eq.

            # Missing variables (not available in forecaster)
            'tp6h': None,    # 6-hour precipitation
        }
        
        # Horizon string to integer mapping
        self.horizon_mapping = {
            '6h': 6,
            '12h': 12, 
            '24h': 24,
            '48h': 48
        }
        
        logger.info("ForecastAdapter initialized with variable mapping")
    
    async def _ensure_analog_service(self):
        """Ensure analog search service is initialized."""
        if self.analog_service is None:
            self.analog_service = await get_analog_search_service()
            logger.info("✅ AnalogSearchService connected to adapter")
    
    async def forecast_with_uncertainty(self, horizon: str, variables: List[str]) -> Dict[str, Any]:
        """
        Generate forecast with uncertainty bounds for specified variables.
        
        This is the missing method that the API expects but the forecaster doesn't have.
        Now uses production AnalogSearchService for real FAISS-based analog search.
        
        Args:
            horizon: Forecast horizon string ('6h', '12h', '24h', '48h')
            variables: List of variable names to forecast
            
        Returns:
            Dictionary with forecast results matching API expected format
        """
        try:
            logger.info(f"Generating forecast for horizon={horizon}, variables={variables}")
            
            # Validate and convert horizon
            if horizon not in self.horizon_mapping:
                raise ValueError(f"Invalid horizon {horizon}. Must be one of {list(self.horizon_mapping.keys())}")
            
            horizon_hours = self.horizon_mapping[horizon]
            
            # Ensure analog search service is connected
            await self._ensure_analog_service()
            
            # Generate analog search results using production service
            analog_results = await self._generate_analog_results(horizon_hours)
            
            # Get raw forecast from core system
            forecast_result = self.forecaster.generate_forecast(analog_results, horizon_hours)
            
            if not forecast_result:
                logger.warning(f"Core forecaster returned no results for {horizon}")
                # Check if fallback is allowed via environment variable
                allow_fallback = os.getenv("ALLOW_ANALOG_FALLBACK", "false") == "true"
                
                if not allow_fallback:
                    raise RuntimeError("Service Unavailable: Core forecaster failed and fallback disabled")
                
                return self._generate_fallback_response(variables)
            
            # Convert forecaster output to API format
            api_response = {}

            for api_var in variables:
                api_response[api_var] = self._convert_variable_result(
                    api_var, forecast_result, analog_results
                )

            # Surface fallback_mode flag so clients know when results are from mock data (M7)
            is_fallback = analog_results.get('search_metadata', {}).get('fallback_mode', False)
            api_response['_fallback_mode'] = is_fallback

            logger.info(f"Successfully generated forecast for {len(variables)} variables"
                        f"{' (FALLBACK MODE)' if is_fallback else ''}")
            return api_response
            
        except Exception as e:
            logger.error(f"Forecast generation failed: {e}")
            # Respect global fallback gate
            allow_fallback = os.getenv("ALLOW_ANALOG_FALLBACK", "false") == "true"
            if not allow_fallback:
                raise
            return self._generate_fallback_response(variables)
    
    async def _generate_analog_results(self, horizon_hours: int) -> Dict[str, Any]:
        """
        Generate analog search results using production AnalogSearchService.
        
        Args:
            horizon_hours: Forecast horizon in hours
            
        Returns:
            Analog results compatible with forecaster expectations
        """
        try:
            # Use production analog search service
            analog_results = await self.analog_service.generate_analog_results_for_adapter(
                horizon_hours=horizon_hours,
                correlation_id=f"forecast-{horizon_hours}h-{int(datetime.now().timestamp())}"
            )
            
            logger.info(f"✅ Generated analog results via AnalogSearchService: "
                       f"{len(analog_results['indices'])} analogs, "
                       f"search_time: {analog_results['search_metadata'].get('search_time_ms', 0):.1f}ms")
            
            return analog_results
            
        except Exception as e:
            logger.warning(f"AnalogSearchService failed, falling back to mock: {e}")
            # Check if fallback is allowed via environment variable
            allow_fallback = os.getenv("ALLOW_ANALOG_FALLBACK", "false") == "true"
            
            if not allow_fallback:
                raise RuntimeError("Service Unavailable: AnalogSearchService failed and fallback disabled")
            
            return self._generate_mock_analog_fallback(horizon_hours)
    
    def _generate_mock_analog_fallback(self, horizon_hours: int) -> Dict[str, Any]:
        """
        Generate mock analog search results as fallback when service unavailable.
        
        Args:
            horizon_hours: Forecast horizon in hours
            
        Returns:
            Mock analog results compatible with forecaster expectations
        """
        # Check if fallback is allowed via environment variable
        allow_fallback = os.getenv("ALLOW_ANALOG_FALLBACK", "false") == "true"
        
        if not allow_fallback:
            raise RuntimeError("Service Unavailable: Mock analog fallback disabled")
        
        # Generate realistic-looking analog indices and distances
        num_analogs = min(50, 100)  # Typical analog count
        
        # Mock analog indices (random historical cases)
        analog_indices = np.random.choice(10000, size=num_analogs, replace=False)
        
        # Mock distances (exponential distribution, closer analogs have lower distance)
        distances = np.random.exponential(scale=2.0, size=num_analogs)
        distances = np.sort(distances)  # Best analogs first
        
        # Mock initialization time (current time)
        init_time = datetime.now(timezone.utc)
        
        mock_results = {
            'indices': analog_indices,
            'distances': distances,
            'init_time': init_time,
            'search_metadata': {
                'total_candidates': 10000,
                'search_time_ms': np.random.uniform(10, 50),
                'k_neighbors': num_analogs,
                'distance_metric': 'L2_fallback',
                'search_method': 'fallback',
                'faiss_search_successful': False,
                'fallback_mode': True
            }
        }
        
        logger.debug(f"Generated fallback analog results: {num_analogs} analogs, "
                    f"best distance: {distances[0]:.3f}")
        
        return mock_results
    
    def _convert_variable_result(self, api_var: str, forecast_result: Any, 
                               analog_results: Dict[str, Any]) -> Dict[str, Any]:
        """
        Convert individual variable result from forecaster format to API format.
        
        Args:
            api_var: API variable name
            forecast_result: Raw forecast result from core system
            analog_results: Analog search results for metadata
            
        Returns:
            API-formatted variable result
        """
        try:
            # Check if we have a mapping for this variable
            forecaster_var = self.variable_mapping.get(api_var)
            
            if forecaster_var is None:
                # Variable not available in forecaster
                return self._create_unavailable_result(api_var)
            
            # Check if forecaster has this variable
            if not hasattr(forecast_result, 'variables') or forecaster_var not in forecast_result.variables:
                logger.warning(f"Forecaster variable {forecaster_var} not found in results")
                return self._create_unavailable_result(api_var)
            
            # Get raw values from forecaster
            point_forecast = forecast_result.variables[forecaster_var]
            confidence_interval = forecast_result.confidence_intervals.get(forecaster_var, (None, None))
            
            # Apply variable-specific conversions
            converted_result = self._apply_variable_conversion(
                api_var, forecaster_var, point_forecast, confidence_interval,
                forecast_result=forecast_result
            )
            
            # Build API response format
            result = {
                'value': converted_result['value'],
                'p05': converted_result['p05'],
                'p95': converted_result['p95'],
                'confidence': converted_result['confidence'],
                'available': True,
                'analog_count': forecast_result.ensemble_size
            }
            
            return result
            
        except Exception as e:
            logger.error(f"Failed to convert variable {api_var}: {e}")
            return self._create_unavailable_result(api_var)
    
    def _apply_variable_conversion(self, api_var: str, forecaster_var: str,
                                 point_value: float, confidence_interval: Tuple[float, float],
                                 forecast_result: Any = None) -> Dict[str, Any]:
        """
        Apply variable-specific conversions and unit transformations.

        Args:
            api_var: API variable name
            forecaster_var: Forecaster variable name
            point_value: Point forecast value
            confidence_interval: (p05, p95) bounds
            forecast_result: Full forecast result for cross-variable lookups

        Returns:
            Converted values with proper units
        """
        p05, p95 = confidence_interval

        if api_var == 'r850' and forecaster_var == 'q850':
            value, p05_converted, p95_converted = self._convert_q850_to_r850(
                point_value, p05, p95, forecast_result
            )

        elif api_var == 'msl' and forecaster_var == 'z500':
            value, p05_converted, p95_converted = self._convert_z500_to_msl(
                point_value, p05, p95, forecast_result
            )

        else:
            # Direct mapping - apply unit conversions using existing utilities
            value = convert_value(point_value, api_var)
            p05_converted = convert_value(p05, api_var) if p05 is not None else None
            p95_converted = convert_value(p95, api_var) if p95 is not None else None

        # Calculate confidence width
        confidence = None
        if p05_converted is not None and p95_converted is not None:
            confidence = abs(p95_converted - p05_converted)

        return {
            'value': value,
            'p05': p05_converted,
            'p95': p95_converted,
            'confidence': confidence
        }

    # ------------------------------------------------------------------
    # H5 fix: Specific humidity -> relative humidity (Bolton 1980)
    # ------------------------------------------------------------------
    @staticmethod
    def _saturation_vapour_pressure(t_kelvin: float) -> float:
        """
        Saturation vapour pressure over liquid water using the Bolton (1980)
        form of the Tetens equation.

        Reference:
            Bolton, D. (1980). "The computation of equivalent potential
            temperature." Monthly Weather Review, 108(7), 1046-1053.
            Eq. 10:  e_s = 611.2 * exp(17.67 * T_C / (T_C + 243.5))

        Args:
            t_kelvin: Temperature in Kelvin.

        Returns:
            Saturation vapour pressure in Pa.
        """
        t_celsius = t_kelvin - 273.15
        # Guard against extreme values that would blow up the exponential
        t_celsius = max(-80.0, min(60.0, t_celsius))
        return 611.2 * math.exp(17.67 * t_celsius / (t_celsius + 243.5))

    @staticmethod
    def _specific_humidity_to_rh(q: float, t_kelvin: float, p_pa: float) -> float:
        """
        Convert specific humidity to relative humidity.

        Physics:
            w   = q / (1 - q)            mixing ratio (kg/kg)
            e_s = Bolton(T)               saturation vapour pressure (Pa)
            w_s = 0.622 * e_s / (p - e_s) saturation mixing ratio (kg/kg)
            RH  = 100 * w / w_s           relative humidity (%)

        Reference: Bolton (1980); WMO Guide to Meteorological Instruments
        and Methods of Observation (WMO-No. 8), Chapter 4.

        Args:
            q: Specific humidity in kg/kg.
            t_kelvin: Temperature in Kelvin.
            p_pa: Pressure in Pa.

        Returns:
            Relative humidity in %, clamped to [0, 100].
        """
        if q <= 0 or not math.isfinite(q):
            return 0.0
        if not math.isfinite(t_kelvin) or t_kelvin < 150.0:
            return 0.0

        e_s = ForecastAdapter._saturation_vapour_pressure(t_kelvin)

        # Avoid division by zero when e_s approaches or exceeds p
        denom = p_pa - e_s
        if denom <= 0:
            return 100.0

        w = q / (1.0 - q)
        w_s = 0.622 * e_s / denom

        if w_s <= 0:
            return 100.0

        rh = 100.0 * (w / w_s)
        return max(0.0, min(100.0, rh))

    def _convert_q850_to_r850(
        self, q_point: float, q_p05: Optional[float], q_p95: Optional[float],
        forecast_result: Any
    ) -> Tuple[float, float, float]:
        """
        Convert specific humidity at 850 hPa (kg/kg) to relative humidity (%).

        Uses t850 from the forecast result as the temperature input.
        Pressure is fixed at 85000 Pa (850 hPa level).

        Reference: Bolton (1980), Tetens formula for saturation vapour pressure.

        Args:
            q_point: Point forecast of specific humidity (kg/kg).
            q_p05: 5th-percentile bound (kg/kg), or None.
            q_p95: 95th-percentile bound (kg/kg), or None.
            forecast_result: Full ForecastResult for cross-variable access.

        Returns:
            (rh_value, rh_p05, rh_p95) all in %.
        """
        P_850 = 85000.0  # 850 hPa in Pa

        # Retrieve t850 (Kelvin) from the forecast result
        t850 = None
        if forecast_result is not None and hasattr(forecast_result, 'variables'):
            t850 = forecast_result.variables.get('t850')

        if t850 is None or not math.isfinite(t850):
            # Fallback: use Adelaide climatological mean at 850 hPa (~285 K / ~12 C)
            t850 = 285.0
            logger.warning("t850 unavailable for humidity conversion; using "
                           "Adelaide climatological mean 285 K")

        value = self._specific_humidity_to_rh(q_point, t850, P_850)

        # For confidence bounds, apply the same conversion.
        # Higher specific humidity -> higher RH (monotonic at fixed T, P),
        # so q percentile ordering is preserved.
        q_lo = q_p05 if q_p05 is not None else q_point
        q_hi = q_p95 if q_p95 is not None else q_point

        # Use t850 confidence bounds if available to widen RH uncertainty
        t850_lo = t850
        t850_hi = t850
        if (forecast_result is not None
                and hasattr(forecast_result, 'confidence_intervals')):
            t850_ci = forecast_result.confidence_intervals.get('t850')
            if t850_ci is not None:
                t850_lo, t850_hi = t850_ci

        # Lower RH bound: low q with warm temperature (higher e_s -> lower RH)
        p05_converted = self._specific_humidity_to_rh(q_lo, t850_hi, P_850)
        # Upper RH bound: high q with cool temperature (lower e_s -> higher RH)
        p95_converted = self._specific_humidity_to_rh(q_hi, t850_lo, P_850)

        # Ensure ordering
        if p05_converted > p95_converted:
            p05_converted, p95_converted = p95_converted, p05_converted

        logger.debug(f"Bolton q850->r850: q={q_point:.6f} kg/kg, t850={t850:.1f} K "
                     f"-> RH={value:.1f}% [{p05_converted:.1f}, {p95_converted:.1f}]")

        return value, p05_converted, p95_converted

    # ------------------------------------------------------------------
    # H6 fix: MSL pressure from 500 hPa geopotential (hypsometric eq.)
    # ------------------------------------------------------------------

    # ICAO standard atmosphere reference values for the hypsometric equation.
    # These anchor the calculation so that standard conditions reproduce
    # P_msl = 1013.25 hPa exactly (for dry air).
    _HYPS_G = 9.80665            # m/s2, WMO standard gravity
    _HYPS_R_D = 287.05           # J/(kg*K), gas constant for dry air
    _HYPS_P_500 = 50000.0        # Pa
    _HYPS_Z_SFC = 50.0           # m, Adelaide CBD approximate elevation
    _HYPS_Z500_STD = 5574.0      # m, ICAO standard geopotential height at 500 hPa
    _HYPS_T850_STD = 278.4       # K, ICAO standard temperature at ~1500 m
    _HYPS_P_MSL_STD = 101325.0   # Pa, standard sea-level pressure

    # Exact layer-mean virtual temperature for the standard atmosphere,
    # computed from the hypsometric equation inverted at standard values:
    #   T_v_std = (Z500_std - Z_sfc) * g / (R_d * ln(P_msl_std / P_500))
    # This evaluates to ~267.19 K.
    _HYPS_TV_STD = ((_HYPS_Z500_STD - _HYPS_Z_SFC) * _HYPS_G
                    / (_HYPS_R_D * math.log(_HYPS_P_MSL_STD / _HYPS_P_500)))

    # Ratio of column-mean T_v to T850 in the standard atmosphere.
    # Used to scale T850 anomalies into column-mean T_v anomalies.
    _HYPS_K_RATIO = _HYPS_TV_STD / _HYPS_T850_STD  # ~0.9597

    @staticmethod
    def _hypsometric_msl(z500_geopotential: float, t850_kelvin: float,
                         q850: float) -> float:
        """
        Estimate mean sea level pressure from 500 hPa geopotential using
        the hypsometric equation, anchored to the ICAO standard atmosphere.

        Method:
            1. Convert geopotential (m2/s2) to geopotential height (m).
            2. Estimate the column-mean virtual temperature by scaling T850
               departures from the ICAO standard using a calibrated ratio
               (k = T_v_mean_std / T850_std ~ 0.96). This preserves the
               standard-atmosphere relationship and uses T850 anomalies to
               adjust for the actual thermal structure.
            3. Apply virtual temperature correction for moisture (q850).
            4. Apply the hypsometric equation:
                  P_msl = P_500 * exp((Z500 - Z_sfc) * g / (R_d * T_v_mean))

        Calibration:
            At ICAO standard conditions (Z500=5574m, T850=278.4K, dry air),
            this function returns exactly 1013.25 hPa. The moisture correction
            introduces a physically correct offset (~1 hPa per 0.003 kg/kg).

        Constants:
            g     = 9.80665 m/s2   (WMO standard gravity)
            R_d   = 287.05 J/(kg*K) (gas constant for dry air)
            P_500 = 50000 Pa
            Z_sfc = 50 m           (Adelaide CBD elevation)

        Approximations and limitations:
            - The column-mean temperature is estimated from T850 alone using
              a linear scaling calibrated against the ICAO standard atmosphere.
              Real atmospheric profiles vary, introducing ~5-10 hPa structural
              uncertainty in extreme conditions (e.g. strong inversions, deep
              convective environments). For typical Adelaide synoptic patterns,
              accuracy is ~3-5 hPa.
            - Adelaide surface elevation is approximated at 50 m ASL.
            - Virtual temperature uses q850 as representative of low-level
              moisture. This is a small correction (~0.3 K, ~1 hPa).

        Reference:
            Wallace & Hobbs (2006), "Atmospheric Science", 2nd ed., Eq. 3.29.
            WMO Guide to Meteorological Instruments (WMO-No. 8), Appendix 3.B.
            ICAO Standard Atmosphere (Doc 7488/3).

        Args:
            z500_geopotential: 500 hPa geopotential in m2/s2 (ERA5 storage).
            t850_kelvin: Temperature at 850 hPa in Kelvin.
            q850: Specific humidity at 850 hPa in kg/kg.

        Returns:
            Estimated MSL pressure in Pa.
        """
        cls = ForecastAdapter
        g = cls._HYPS_G
        R_d = cls._HYPS_R_D

        # Step 1: geopotential (m2/s2) -> geopotential height (m)
        Z500 = z500_geopotential / g

        # Step 2: layer-mean temperature anchored to standard atmosphere
        # T_mean = T_v_std + k * (T850 - T850_std)
        T_mean = cls._HYPS_TV_STD + cls._HYPS_K_RATIO * (t850_kelvin - cls._HYPS_T850_STD)

        # Step 3: virtual temperature correction for moisture
        q_safe = max(0.0, q850) if math.isfinite(q850) else 0.0
        T_v = T_mean * (1.0 + 0.61 * q_safe)

        # Guard against non-physical temperatures
        if T_v < 180.0 or not math.isfinite(T_v):
            T_v = cls._HYPS_TV_STD
            logger.warning("Non-physical T_v in hypsometric MSL; "
                           "using standard atmosphere fallback %.1f K", cls._HYPS_TV_STD)

        # Step 4: hypsometric equation, surface to 500 hPa
        thickness = Z500 - cls._HYPS_Z_SFC
        if thickness <= 0 or not math.isfinite(thickness):
            return cls._HYPS_P_MSL_STD

        P_msl = cls._HYPS_P_500 * math.exp(thickness * g / (R_d * T_v))
        return P_msl

    def _convert_z500_to_msl(
        self, z500_point: float, z500_p05: Optional[float],
        z500_p95: Optional[float], forecast_result: Any
    ) -> Tuple[float, float, float]:
        """
        Derive MSL pressure (hPa) from 500 hPa geopotential using the
        hypsometric equation.

        Uses t850 and q850 from the forecast result for the virtual
        temperature computation. Uncertainty bounds combine the analog
        ensemble spread in z500 and t850.

        Structural uncertainty: this single-level derivation has an inherent
        ~3-5 hPa systematic uncertainty for typical Adelaide conditions,
        potentially ~5-10 hPa in extreme situations (strong inversions,
        deep convection). This is a fundamental limitation of not having
        a full atmospheric profile. The uncertainty bounds reflect the
        analog ensemble spread but do not include this structural term.

        Args:
            z500_point: Point forecast of 500 hPa geopotential (m2/s2).
            z500_p05: 5th-percentile bound (m2/s2), or None.
            z500_p95: 95th-percentile bound (m2/s2), or None.
            forecast_result: Full ForecastResult for cross-variable access.

        Returns:
            (msl_value, msl_p05, msl_p95) all in hPa (display units).
        """
        # Retrieve t850 and q850 from forecast result
        t850 = None
        q850 = 0.0
        if forecast_result is not None and hasattr(forecast_result, 'variables'):
            t850 = forecast_result.variables.get('t850')
            q850 = forecast_result.variables.get('q850', 0.0)

        if t850 is None or not math.isfinite(t850):
            t850 = 285.0  # Adelaide climatological mean at 850 hPa
            logger.warning("t850 unavailable for MSL derivation; using "
                           "Adelaide climatological mean 285 K")
        if not math.isfinite(q850):
            q850 = 0.005  # ~5 g/kg, typical Adelaide low-level moisture

        # Point estimate
        msl_pa = self._hypsometric_msl(z500_point, t850, q850)
        value = msl_pa / 100.0  # Pa -> hPa

        # Confidence bounds: combine z500 and t850 ensemble spread.
        z_lo = z500_p05 if z500_p05 is not None else z500_point
        z_hi = z500_p95 if z500_p95 is not None else z500_point

        t850_lo = t850
        t850_hi = t850
        if (forecast_result is not None
                and hasattr(forecast_result, 'confidence_intervals')):
            t850_ci = forecast_result.confidence_intervals.get('t850')
            if t850_ci is not None:
                t850_lo, t850_hi = t850_ci

        # The relationship between inputs and MSL is non-trivial:
        # higher Z500 -> higher MSL (thicker column means more mass above)
        # warmer T_v  -> lower MSL for same thickness (density effect)
        # Compute both extreme combinations and take the envelope.
        msl_a = self._hypsometric_msl(z_lo, t850_hi, q850) / 100.0
        msl_b = self._hypsometric_msl(z_hi, t850_lo, q850) / 100.0

        p05_converted = min(msl_a, msl_b)
        p95_converted = max(msl_a, msl_b)

        # Sanity clamp to physically plausible Adelaide range
        # (Adelaide record low ~968 hPa, record high ~1044 hPa)
        value = max(950.0, min(1070.0, value))
        p05_converted = max(950.0, min(1070.0, p05_converted))
        p95_converted = max(950.0, min(1070.0, p95_converted))

        logger.debug(f"Hypsometric z500->msl: z500={z500_point:.0f} m2/s2, "
                     f"t850={t850:.1f} K -> MSL={value:.1f} hPa "
                     f"[{p05_converted:.1f}, {p95_converted:.1f}]")

        return value, p05_converted, p95_converted
    
    def _create_unavailable_result(self, api_var: str) -> Dict[str, Any]:
        """Create result for unavailable variable."""
        return {
            'value': None,
            'p05': None,
            'p95': None,
            'confidence': None,
            'available': False,
            'analog_count': None
        }
    
    def _generate_fallback_response(self, variables: List[str]) -> Dict[str, Any]:
        """
        Generate fallback response when core forecaster fails.
        
        Args:
            variables: Requested variables
            
        Returns:
            Fallback response with mock data
        """
        logger.warning("Generating fallback response due to forecaster failure")

        fallback_response = {}

        for var in variables:
            # Generate reasonable mock values based on variable type
            if var == 't2m':
                value = 20.0  # 20°C
                p05, p95 = 15.0, 25.0
            elif var in ['u10', 'v10']:
                value = 5.0  # 5 m/s
                p05, p95 = 0.0, 10.0
            elif var == 'msl':
                value = 1013.25  # Standard pressure
                p05, p95 = 1008.0, 1018.0
            elif var == 'r850':
                value = 70.0  # 70% humidity
                p05, p95 = 50.0, 90.0
            elif var == 'cape':
                value = 500.0  # Moderate instability
                p05, p95 = 100.0, 1000.0
            else:
                # Generic fallback
                value = 0.0
                p05, p95 = -1.0, 1.0

            fallback_response[var] = {
                'value': value,
                'p05': p05,
                'p95': p95,
                'confidence': abs(p95 - p05),
                'available': True,  # Mark as available even though it's mock data
                'analog_count': 25  # Mock analog count
            }

        # Surface fallback flag so clients can detect mock data (M7)
        fallback_response['_fallback_mode'] = True

        return fallback_response
    
    def prepare_forecast_response(self, horizon: str, variables: List[str], 
                                 forecast_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Prepare final forecast response in the expected API format.
        
        Args:
            horizon: Forecast horizon (e.g., "24h")
            variables: List of requested variables
            forecast_data: Raw forecast data from the adapter
            
        Returns:
            Formatted response ready for API return
        """
        try:
            response = {
                "horizon": horizon,
                "generated_at": datetime.now(timezone.utc).isoformat(),
                "variables": {},
                "latency_ms": forecast_data.get("latency_ms", 0),
                "narrative": forecast_data.get("narrative", "Weather forecast generated successfully"),
                "risk_assessment": forecast_data.get("risk_assessment", "normal"),
                "analogs_summary": forecast_data.get("analogs_summary", {
                    "count": 0,
                    "confidence": 0.0,
                    "timespan": "unknown"
                })
            }
            
            # Process variables from forecast data
            if "variables" in forecast_data:
                response["variables"] = forecast_data["variables"]
            else:
                # Create placeholder variables structure
                for var in variables:
                    response["variables"][var] = {
                        "value": 0.0,
                        "unit": VARIABLE_SPECS.get(var, {}).get("unit", "unknown"),
                        "confidence": 0.5,
                        "available": False
                    }
            
            return response
            
        except Exception as e:
            logger.error(f"Error preparing forecast response: {e}")
            # Return error response in expected format
            return {
                "horizon": horizon,
                "generated_at": datetime.now(timezone.utc).isoformat(),
                "variables": {},
                "latency_ms": 0,
                "narrative": f"Error generating forecast: {str(e)}",
                "risk_assessment": "error",
                "analogs_summary": {"count": 0, "confidence": 0.0, "timespan": "unknown"},
                "error": str(e)
            }
    
    async def get_system_health(self) -> Dict[str, Any]:
        """Get health status of the adapter and underlying systems."""
        try:
            # Check forecaster health
            forecaster_healthy = self.forecaster is not None
            
            # Check variable mappings
            mappings_configured = len(self.variable_mapping) > 0
            
            # Check horizon mappings
            horizons_configured = len(self.horizon_mapping) > 0
            
            # Check analog search service health
            analog_service_health = None
            analog_service_ready = False
            
            try:
                await self._ensure_analog_service()
                analog_service_health = await self.analog_service.health_check()
                analog_service_ready = analog_service_health.get('status', 'unhealthy') in ['healthy', 'degraded']
            except Exception as e:
                logger.warning(f"Could not check analog service health: {e}")
                analog_service_health = {'status': 'unavailable', 'error': str(e)}
            
            overall_health = (forecaster_healthy and mappings_configured and 
                            horizons_configured and analog_service_ready)
            
            return {
                'adapter_ready': overall_health,
                'forecaster_loaded': forecaster_healthy,
                'analog_service_ready': analog_service_ready,
                'analog_service_health': analog_service_health,
                'variable_mappings': len(self.variable_mapping),
                'supported_horizons': list(self.horizon_mapping.keys()),
                'available_api_variables': list(self.variable_mapping.keys()),
                'direct_mappings': sum(1 for v in self.variable_mapping.values() if v is not None),
                'missing_variables': [k for k, v in self.variable_mapping.items() if v is None]
            }
            
        except Exception as e:
            logger.error(f"Health check failed: {e}")
            return {
                'adapter_ready': False,
                'error': str(e)
            }
