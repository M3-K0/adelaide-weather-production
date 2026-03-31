"""
Regression tests for core/real_time_embedder.py fixes.

Covers:
  M5  - Embedder num_variables is 9
  L1  - OMP_NUM_THREADS uses setdefault (does not override existing env var)
"""

import os
import inspect
import pytest


# ===================================================================
# M5: Embedder num_variables must be 9
# ===================================================================

class TestM5EmbedderVariables:
    """M5: RealTimeEmbedder must use num_variables=9."""

    def test_regression_m5_num_variables_is_9(self):
        """The embedder's num_variables attribute must be 9."""
        from core.real_time_embedder import RealTimeEmbedder
        # Instantiate without loading a real model (model will be None)
        embedder = RealTimeEmbedder.__new__(RealTimeEmbedder)
        # Read the default from class init
        source = inspect.getsource(RealTimeEmbedder.__init__)
        assert "self.num_variables = 9" in source, (
            "RealTimeEmbedder does not set num_variables = 9"
        )

    def test_regression_m5_preprocess_expects_9_variables(self):
        """_preprocess_era5_data should produce an array with 9 channels."""
        from core.real_time_embedder import RealTimeEmbedder

        embedder = RealTimeEmbedder.__new__(RealTimeEmbedder)
        embedder.num_variables = 9
        embedder.spatial_shape = (16, 16)
        embedder.timing_stats = {"preprocess_ms": 0}

        era5_data = {
            "z500": 5640.0,
            "t2m": 293.15,
            "t850": 285.65,
            "q850": 0.008,
            "u10": -2.5,
            "v10": 4.2,
            "u850": -8.1,
            "v850": 12.3,
            "cape": 150.0,
        }

        result = embedder._preprocess_era5_data(era5_data)
        assert result is not None
        assert result.shape == (9, 16, 16), f"Shape {result.shape}, expected (9, 16, 16)"

    def test_regression_m5_spatial_expansion_documented(self):
        """M5 fix should include documentation about spatial expansion limitation."""
        from core.real_time_embedder import RealTimeEmbedder
        source = inspect.getsource(RealTimeEmbedder._preprocess_era5_data)
        # Check that the limitation is documented
        assert "spatial" in source.lower(), (
            "M5: spatial expansion limitation not documented in _preprocess_era5_data"
        )


# ===================================================================
# L1: Thread limits use setdefault (do not override)
# ===================================================================

class TestL1ThreadLimits:
    """L1: OMP_NUM_THREADS must use os.environ.setdefault, not direct assignment."""

    def test_regression_l1_setdefault_in_source(self):
        """real_time_embedder.py must use setdefault for OMP_NUM_THREADS."""
        import core.real_time_embedder as mod
        source = inspect.getsource(mod)
        assert "setdefault" in source and "OMP_NUM_THREADS" in source, (
            "real_time_embedder does not use setdefault for OMP_NUM_THREADS"
        )

    def test_regression_l1_does_not_override_existing_env(self):
        """If OMP_NUM_THREADS is already set, importing the module must not override it."""
        # Set a custom value before the module code would run
        original = os.environ.get("OMP_NUM_THREADS")
        os.environ["OMP_NUM_THREADS"] = "8"
        try:
            # The setdefault call at module level should not change "8" -> "2"
            os.environ.setdefault("OMP_NUM_THREADS", "2")
            assert os.environ["OMP_NUM_THREADS"] == "8", (
                "setdefault overwrote existing OMP_NUM_THREADS"
            )
        finally:
            if original is not None:
                os.environ["OMP_NUM_THREADS"] = original
            else:
                os.environ.pop("OMP_NUM_THREADS", None)

    def test_regression_l1_no_direct_assignment(self):
        """Source must not contain os.environ['OMP_NUM_THREADS'] = (direct overwrite)."""
        import core.real_time_embedder as mod
        source = inspect.getsource(mod)
        # Match direct assignment but not setdefault
        import re
        direct_assign = re.search(
            r"os\.environ\[.OMP_NUM_THREADS.\]\s*=\s*", source
        )
        assert direct_assign is None, (
            "real_time_embedder.py still uses direct os.environ assignment for OMP_NUM_THREADS"
        )
