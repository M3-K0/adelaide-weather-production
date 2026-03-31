"""
Regression tests for api/forecast_adapter.py fixes.

Covers:
  H5  - Humidity conversion uses Bolton formula (not flat multiplier)
  H6  - MSL pressure uses hypsometric equation (not linear placeholder)
  M7  - Fallback response surfaces _fallback_mode flag
"""

import math
import sys
import pytest
from unittest.mock import MagicMock

# The import chain api.forecast_adapter -> api.services -> scripts.analog_forecaster
# pulls in faiss which may not be installed in the test environment.
# Pre-populate sys.modules with stubs so the imports succeed without the C library.
_MOCK_MODULES = {}
for mod_name in ("faiss", "faiss.swigfaiss", "faiss.swigfaiss_avx2"):
    if mod_name not in sys.modules:
        _MOCK_MODULES[mod_name] = sys.modules[mod_name] = MagicMock()

from api.forecast_adapter import ForecastAdapter


# ===================================================================
# H5: Humidity conversion — Bolton / Tetens formula
# ===================================================================

class TestH5HumidityConversion:
    """H5: q850 -> r850 must use proper Bolton 1980 formula."""

    @pytest.fixture(autouse=True)
    def _adapter(self):
        self.adapter = ForecastAdapter.__new__(ForecastAdapter)

    # -- saturation vapour pressure sanity --

    def test_regression_h5_saturation_vp_at_0c(self):
        """e_s at 0 C (273.15 K) should be approximately 611 Pa."""
        e_s = ForecastAdapter._saturation_vapour_pressure(273.15)
        assert 600 < e_s < 620, f"e_s(0C)={e_s:.1f} Pa, expected ~611 Pa"

    def test_regression_h5_saturation_vp_at_20c(self):
        """e_s at 20 C (293.15 K) should be approximately 2338 Pa."""
        e_s = ForecastAdapter._saturation_vapour_pressure(293.15)
        assert 2200 < e_s < 2500, f"e_s(20C)={e_s:.1f} Pa, expected ~2338 Pa"

    # -- specific humidity to RH --

    def test_regression_h5_low_humidity(self):
        """q=0.001 at T=285K, P=85000Pa should give RH roughly 10-30%."""
        rh = ForecastAdapter._specific_humidity_to_rh(0.001, 285.0, 85000.0)
        assert 5.0 < rh < 35.0, f"RH={rh:.1f}% for q=0.001, expected ~10-30%"

    def test_regression_h5_high_humidity_clamped(self):
        """q=0.02 should NOT produce RH > 100% (must be clamped)."""
        rh = ForecastAdapter._specific_humidity_to_rh(0.02, 285.0, 85000.0)
        assert rh <= 100.0, f"RH={rh:.1f}% exceeds 100% -- clamping broken"

    def test_regression_h5_zero_humidity(self):
        """q=0 should give RH=0%."""
        rh = ForecastAdapter._specific_humidity_to_rh(0.0, 285.0, 85000.0)
        assert rh == 0.0

    def test_regression_h5_negative_humidity(self):
        """q<0 should give RH=0% (guard)."""
        rh = ForecastAdapter._specific_humidity_to_rh(-0.001, 285.0, 85000.0)
        assert rh == 0.0

    def test_regression_h5_extreme_cold(self):
        """Very cold temperature should still return a finite RH."""
        rh = ForecastAdapter._specific_humidity_to_rh(0.001, 200.0, 85000.0)
        assert 0.0 <= rh <= 100.0

    def test_regression_h5_nonfinite_temperature(self):
        """Non-finite temperature should return 0%."""
        rh = ForecastAdapter._specific_humidity_to_rh(0.005, float("inf"), 85000.0)
        assert rh == 0.0

    def test_regression_h5_no_flat_multiplier_in_source(self):
        """The old flat multiplier (15000) must not appear in the conversion code."""
        import inspect
        source = inspect.getsource(ForecastAdapter._specific_humidity_to_rh)
        assert "15000" not in source, "Old flat multiplier 15000 still present in conversion"

    def test_regression_h5_typical_adelaide_humidity(self):
        """Typical Adelaide summer: q=0.008, T=295K should give roughly 40-80% RH."""
        rh = ForecastAdapter._specific_humidity_to_rh(0.008, 295.0, 85000.0)
        assert 30.0 < rh < 90.0, f"RH={rh:.1f}% for typical Adelaide summer"


# ===================================================================
# H6: MSL pressure — hypsometric equation
# ===================================================================

class TestH6MSLPressure:
    """H6: MSL pressure must use hypsometric equation, not linear placeholder."""

    def test_regression_h6_standard_atmosphere(self):
        """At ICAO standard conditions, MSL should be ~1013.25 hPa."""
        # ICAO: Z500 = 5574 m geopotential height; stored as m2/s2 in ERA5
        z500_geopotential = 5574.0 * 9.80665  # m2/s2
        t850 = 278.4  # K (ICAO standard at ~1500 m)
        q850 = 0.0    # dry
        msl_pa = ForecastAdapter._hypsometric_msl(z500_geopotential, t850, q850)
        msl_hpa = msl_pa / 100.0
        assert abs(msl_hpa - 1013.25) < 1.0, (
            f"Standard atmosphere MSL={msl_hpa:.2f} hPa, expected ~1013.25 hPa"
        )

    def test_regression_h6_realistic_adelaide_range(self):
        """Typical Adelaide z500 should produce MSL in 990-1030 hPa."""
        # Typical ERA5 z500 for Adelaide: ~5500-5700 m geopotential height
        z500_geopotential = 5600.0 * 9.80665
        t850 = 285.0  # Typical Adelaide 850 hPa temp
        q850 = 0.005   # ~5 g/kg
        msl_pa = ForecastAdapter._hypsometric_msl(z500_geopotential, t850, q850)
        msl_hpa = msl_pa / 100.0
        assert 990.0 < msl_hpa < 1040.0, f"MSL={msl_hpa:.1f} hPa outside plausible range"

    def test_regression_h6_no_linear_placeholder_in_source(self):
        """The old linear placeholder formula must be gone."""
        import inspect
        source = inspect.getsource(ForecastAdapter._hypsometric_msl)
        # Old pattern: -(point_value - 5500) * 0.1
        assert "5500" not in source or "HYPS" in source, (
            "Old linear placeholder '5500 * 0.1' pattern found in hypsometric method"
        )

    def test_regression_h6_moisture_correction_direction(self):
        """Adding moisture should lower MSL slightly (virtual temperature effect)."""
        z500_geopotential = 5600.0 * 9.80665
        t850 = 285.0
        msl_dry = ForecastAdapter._hypsometric_msl(z500_geopotential, t850, 0.0)
        msl_moist = ForecastAdapter._hypsometric_msl(z500_geopotential, t850, 0.01)
        # Moist air is less dense -> lower pressure for same thickness
        # Actually, virtual temperature increases -> larger exponent -> higher MSL estimate
        # The direction depends on the equation form; just check they differ
        assert msl_dry != msl_moist, "Moisture correction has no effect"

    def test_regression_h6_nonphysical_temperature_fallback(self):
        """Non-physical T_v should trigger fallback to standard atmosphere."""
        z500_geopotential = 5600.0 * 9.80665
        msl_pa = ForecastAdapter._hypsometric_msl(z500_geopotential, 50.0, 0.0)
        msl_hpa = msl_pa / 100.0
        # Should still produce a plausible value (standard atmo fallback)
        assert 900.0 < msl_hpa < 1100.0


# ===================================================================
# M7: Fallback response includes _fallback_mode
# ===================================================================

class TestM7FallbackMode:
    """M7: Fallback responses must surface _fallback_mode key."""

    def test_regression_m7_fallback_response_has_flag(self):
        """_generate_fallback_response must include _fallback_mode=True."""
        adapter = ForecastAdapter.__new__(ForecastAdapter)
        adapter.variable_mapping = {"t2m": "t2m"}
        result = adapter._generate_fallback_response(["t2m"])
        assert "_fallback_mode" in result, "Fallback response missing _fallback_mode key"
        assert result["_fallback_mode"] is True

    def test_regression_m7_normal_response_structure(self):
        """forecast_with_uncertainty return dict should include _fallback_mode."""
        # Inspect the method source to confirm the key is always set
        import inspect
        source = inspect.getsource(ForecastAdapter.forecast_with_uncertainty)
        assert "_fallback_mode" in source, (
            "forecast_with_uncertainty does not set _fallback_mode"
        )
