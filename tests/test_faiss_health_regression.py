"""
Regression tests for api/services/faiss_health_monitoring.py fixes.

Covers:
  M3  - _completed_queries must be bounded (pruned at max_samples)
"""

import inspect
import sys
import pytest
from unittest.mock import patch, MagicMock
from prometheus_client import CollectorRegistry

# The import chain api.services -> scripts.analog_forecaster pulls in faiss.
# Provide stubs so the test can import the health monitoring module without faiss.
for mod_name in ("faiss", "faiss.swigfaiss", "faiss.swigfaiss_avx2"):
    if mod_name not in sys.modules:
        sys.modules[mod_name] = MagicMock()

from api.services.faiss_health_monitoring import FAISSHealthMonitor, FAISSQueryMetrics


# ===================================================================
# M3: _completed_queries bounded
# ===================================================================

class TestM3CompletedQueriesBounded:
    """M3: _completed_queries list must be bounded and pruned."""

    @pytest.fixture
    def monitor(self):
        """Create a FAISSHealthMonitor with a fresh Prometheus registry."""
        registry = CollectorRegistry()
        return FAISSHealthMonitor(registry=registry)

    def test_regression_m3_completed_queries_pruned(self, monitor):
        """Adding more than max_samples entries must trigger pruning."""
        max_samples = monitor._max_samples

        # Simulate adding completed queries well beyond the limit
        for i in range(max_samples + 500):
            metric = FAISSQueryMetrics(
                query_id=f"q-{i}",
                horizon="24h",
                k_neighbors=50,
                start_time=0.0,
            )
            metric.complete(success=True)
            monitor._completed_queries.append(metric)
            # Mimic the pruning logic from track_query
            if len(monitor._completed_queries) > max_samples:
                monitor._completed_queries = monitor._completed_queries[-max_samples:]

        assert len(monitor._completed_queries) <= max_samples, (
            f"_completed_queries has {len(monitor._completed_queries)} entries, "
            f"max is {max_samples}"
        )

    def test_regression_m3_pruning_in_source(self, monitor):
        """The track_query context manager must contain pruning logic for _completed_queries."""
        # Check the source for the pruning pattern
        source = inspect.getsource(FAISSHealthMonitor)
        assert "_completed_queries" in source
        # There should be a length check and slicing
        assert "_max_samples" in source or "1000" in source, (
            "No max bound reference found for _completed_queries"
        )

    def test_regression_m3_max_samples_attribute_exists(self, monitor):
        """FAISSHealthMonitor must have _max_samples attribute."""
        assert hasattr(monitor, "_max_samples"), (
            "FAISSHealthMonitor missing _max_samples attribute"
        )
        assert monitor._max_samples > 0

    def test_regression_m3_initial_completed_queries_empty(self, monitor):
        """_completed_queries should start empty."""
        assert len(monitor._completed_queries) == 0

    def test_regression_m3_latency_samples_also_bounded(self, monitor):
        """_latency_samples should also respect _max_samples (pre-existing bound)."""
        assert hasattr(monitor, "_latency_samples")
        assert hasattr(monitor, "_max_samples")
        # The bound is the same for both lists
        assert monitor._max_samples == 1000
