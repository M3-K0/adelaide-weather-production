"""
Shared test fixtures for Adelaide Weather regression tests.

Provides mock ERA5 data, model instances, FastAPI TestClient,
mock FAISS indices, and environment variable fixtures.
"""

import os
import sys
import pytest
import numpy as np
from unittest.mock import MagicMock, AsyncMock, patch
from pathlib import Path

# Ensure project root is on sys.path so imports resolve
PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

# Pre-populate sys.modules with stubs for faiss (C library) so that the deep
# import chain  api.services -> scripts.analog_forecaster -> faiss  resolves
# without requiring the native FAISS package in the test environment.
for _mod_name in ("faiss", "faiss.swigfaiss", "faiss.swigfaiss_avx2"):
    if _mod_name not in sys.modules:
        sys.modules[_mod_name] = MagicMock()


# ---------------------------------------------------------------------------
# Environment variable fixtures
# ---------------------------------------------------------------------------

@pytest.fixture(autouse=True)
def _set_test_env(monkeypatch):
    """Set safe environment variables for all tests."""
    monkeypatch.setenv("ENVIRONMENT", "development")
    monkeypatch.setenv("API_TOKEN", "test-token-abc123-secure-enough")
    monkeypatch.setenv("CORS_ORIGINS", "http://localhost:3000")
    monkeypatch.setenv("RATE_LIMIT_PER_MINUTE", "1000")
    monkeypatch.setenv("COMPRESSION_ENABLED", "false")


# ---------------------------------------------------------------------------
# Mock ERA5 data fixture (9 variables, correct shapes)
# ---------------------------------------------------------------------------

@pytest.fixture
def era5_data():
    """Realistic mock ERA5 data dictionary with 9 variables."""
    return {
        "z500": 5640.0,       # 500 hPa geopotential height (m)
        "t2m": 293.15,        # 2m temperature (K) ~ 20 C
        "t850": 285.65,       # 850 hPa temperature (K) ~ 12.5 C
        "q850": 0.008,        # 850 hPa specific humidity (kg/kg)
        "u10": -2.5,          # 10m u-wind (m/s)
        "v10": 4.2,           # 10m v-wind (m/s)
        "u850": -8.1,         # 850 hPa u-wind (m/s)
        "v850": 12.3,         # 850 hPa v-wind (m/s)
        "cape": 150.0,        # CAPE (J/kg)
    }


# ---------------------------------------------------------------------------
# PyTorch model fixture
# ---------------------------------------------------------------------------

@pytest.fixture
def weather_cnn_encoder():
    """WeatherCNNEncoder instance with default parameters (embedding_dim=256, num_variables=9)."""
    import torch
    from core.model_loader import WeatherCNNEncoder

    model = WeatherCNNEncoder(embedding_dim=256, num_variables=9)
    model.eval()
    return model


# ---------------------------------------------------------------------------
# Mock FAISS index fixture
# ---------------------------------------------------------------------------

@pytest.fixture
def mock_faiss_index():
    """Mock FAISS index that returns synthetic search results."""
    index = MagicMock()
    index.ntotal = 13148
    index.d = 256

    # search returns (distances, indices)
    distances = np.random.exponential(2.0, size=(1, 50)).astype(np.float32)
    indices = np.random.choice(13148, size=(1, 50), replace=False).astype(np.int64)
    index.search.return_value = (distances, indices)
    return index


# ---------------------------------------------------------------------------
# FastAPI TestClient fixture
# ---------------------------------------------------------------------------

@pytest.fixture
def test_client():
    """FastAPI TestClient for the main app.

    Heavy startup side-effects (model loading, FAISS, drift detector) are
    mocked out so the client boots quickly without real data files.

    The module is imported first (faiss stubs in conftest make this safe),
    then its heavy symbols are patched before the TestClient triggers startup.
    """
    from unittest.mock import patch, AsyncMock, MagicMock

    # Import the module first so patch() can resolve the dotted path.
    import api.main  # noqa: F401

    # Patch the startup event to avoid loading real models / indices
    with patch("api.main.ForecastAdapter") as MockAdapter, \
         patch("api.main.get_faiss_health_monitor", new_callable=AsyncMock) as mock_faiss, \
         patch("api.main.ExpertValidatedStartupSystem") as MockStartup, \
         patch("api.main.ConfigurationDriftDetector") as MockDrift:

        # Configure startup mock
        MockStartup.return_value.run_expert_startup_validation.return_value = True

        # Configure adapter mock
        adapter_instance = AsyncMock()
        adapter_instance.get_system_health.return_value = {"adapter_ready": True}
        adapter_instance.forecast_with_uncertainty.return_value = {
            "_fallback_mode": False,
            "t2m": {"value": 20.0, "p05": 15.0, "p95": 25.0, "confidence": 10.0, "available": True, "analog_count": 50},
        }
        MockAdapter.return_value = adapter_instance

        # Configure FAISS health mock
        mock_monitor = AsyncMock()
        mock_monitor.get_health_summary.return_value = {"status": "healthy", "indices": {}}
        mock_monitor.track_query.return_value.__aenter__ = AsyncMock()
        mock_monitor.track_query.return_value.__aexit__ = AsyncMock()
        mock_faiss.return_value = mock_monitor

        # Configure drift detector mock
        MockDrift.return_value.start_monitoring.return_value = True

        from fastapi.testclient import TestClient
        from api.main import app

        client = TestClient(app, raise_server_exceptions=False)
        yield client


# ---------------------------------------------------------------------------
# Analog search results fixture
# ---------------------------------------------------------------------------

@pytest.fixture
def analog_results():
    """Synthetic analog search results compatible with RealTimeAnalogForecaster."""
    import pandas as pd

    num_analogs = 50
    distances = np.sort(np.random.exponential(2.0, size=num_analogs))
    indices = np.random.choice(10000, size=num_analogs, replace=False)

    return {
        "indices": indices,
        "distances": distances.astype(np.float32),
        "init_time": pd.Timestamp.now(tz="UTC"),
        "search_metadata": {
            "total_candidates": 10000,
            "search_time_ms": 25.0,
            "k_neighbors": num_analogs,
            "distance_metric": "L2",
            "fallback_mode": False,
        },
    }
