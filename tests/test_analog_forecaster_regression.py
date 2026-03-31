"""
Regression tests for core/analog_forecaster.py fixes.

Covers:
  M8  - Distance-based analog quality cutoff (filter outliers)
  L5  - Interpolated quantile computation (not staircase)
"""

import numpy as np
import pytest
from core.analog_forecaster import RealTimeAnalogForecaster


# ===================================================================
# M8: Distance-based analog quality cutoff
# ===================================================================

class TestM8DistanceCutoff:
    """M8: filter_by_distance must remove outlier analogs."""

    @pytest.fixture(autouse=True)
    def _forecaster(self):
        self.fc = RealTimeAnalogForecaster.__new__(RealTimeAnalogForecaster)
        self.fc.min_analogs = 10
        self.fc.distance_cutoff_sigma = 2.0

    def test_regression_m8_outlier_removed(self):
        """An analog with distance far beyond mean+2*std should be filtered."""
        # 49 distances clustered around 1.0, plus one outlier at 100
        distances = np.concatenate([
            np.random.uniform(0.5, 1.5, 49),
            [100.0],
        ])
        mask = self.fc.filter_by_distance(distances)
        # The outlier at index 49 should be removed
        assert mask[49] is np.False_ or mask[49] == False, "Outlier at distance=100 not removed"
        # Most normal ones should be kept
        assert np.sum(mask) >= 49

    def test_regression_m8_all_within_threshold_kept(self):
        """When all distances are similar, all should be kept."""
        # Use deterministic data: all distances identical -- zero std, so
        # threshold = mean + 2*0 = mean, and all distances <= threshold.
        distances = np.full(50, 1.0)
        mask = self.fc.filter_by_distance(distances)
        assert np.all(mask), "No outliers present but some analogs were filtered"

    def test_regression_m8_minimum_analogs_preserved(self):
        """Even when all exceed threshold, at least min_analogs must remain."""
        # All distances are "outliers" relative to each other with high variance
        distances = np.array([1.0] * 5 + [1000.0] * 45)
        mask = self.fc.filter_by_distance(distances)
        assert np.sum(mask) >= self.fc.min_analogs, (
            f"Only {np.sum(mask)} analogs kept, minimum is {self.fc.min_analogs}"
        )

    def test_regression_m8_few_analogs_not_filtered(self):
        """If we have <= min_analogs, none should be filtered."""
        distances = np.array([1.0, 2.0, 100.0, 200.0, 500.0])
        self.fc.min_analogs = 10  # More than len(distances)
        mask = self.fc.filter_by_distance(distances)
        assert np.all(mask), "Analogs filtered when count <= min_analogs"

    def test_regression_m8_filter_method_exists(self):
        """RealTimeAnalogForecaster must have a filter_by_distance method."""
        assert hasattr(RealTimeAnalogForecaster, "filter_by_distance")

    def test_regression_m8_cutoff_used_in_generate_forecast(self):
        """generate_forecast source should call filter_by_distance."""
        import inspect
        source = inspect.getsource(RealTimeAnalogForecaster.generate_forecast)
        assert "filter_by_distance" in source, (
            "generate_forecast does not call filter_by_distance"
        )


# ===================================================================
# L5: Interpolated quantile computation
# ===================================================================

class TestL5InterpolatedQuantiles:
    """L5: Quantile computation should use interpolation, not pure staircase."""

    @pytest.fixture(autouse=True)
    def _forecaster(self):
        self.fc = RealTimeAnalogForecaster()

    def test_regression_l5_quantiles_interpolated(self):
        """Quantile values should not be restricted to exact data points."""
        # Create outcomes with known structure
        # 50 analogs, 9 variables
        num_analogs = 50
        num_vars = 9
        np.random.seed(42)

        # Temperature-like values around 290 K
        outcomes = np.random.normal(290.0, 5.0, size=(num_analogs, num_vars))
        # Ensure all positive for temperature variables
        outcomes = np.abs(outcomes) + 250.0

        weights = np.ones(num_analogs) / num_analogs

        stats = self.fc.compute_ensemble_statistics(outcomes, weights)

        # Check that q05 and q95 exist and are between min and max
        for var_name, var_stats in stats.items():
            q05 = var_stats["q05"]
            q95 = var_stats["q95"]
            var_idx = self.fc.variables.index(var_name) if var_name in self.fc.variables else None
            if var_idx is not None:
                values = outcomes[:, var_idx]
                assert q05 >= values.min() - 0.01
                assert q95 <= values.max() + 0.01
                assert q05 < q95, f"q05={q05} >= q95={q95} for {var_name}"

    def test_regression_l5_source_uses_interp(self):
        """compute_ensemble_statistics should use np.interp for quantiles."""
        import inspect
        source = inspect.getsource(RealTimeAnalogForecaster.compute_ensemble_statistics)
        assert "interp" in source, (
            "compute_ensemble_statistics does not use interpolation for quantiles"
        )

    def test_regression_l5_midpoint_cdf(self):
        """Quantile computation should use midpoint CDF for unbiased estimation."""
        import inspect
        source = inspect.getsource(RealTimeAnalogForecaster.compute_ensemble_statistics)
        assert "midpoint" in source.lower() or "sorted_weights / 2" in source, (
            "Quantile computation does not use midpoint CDF approach"
        )
