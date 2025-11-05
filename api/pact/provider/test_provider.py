#!/usr/bin/env python3
"""
Pact Provider Tests for Adelaide Weather Forecast API

These tests verify that the backend API implementation satisfies the contracts
defined by the frontend consumer tests. They validate the enhanced API schema
including all new fields and error handling scenarios.

The tests use the actual FastAPI application with a test configuration to
ensure realistic behavior while maintaining test isolation.
"""

import os
import sys
import json
import pytest
import subprocess
from pathlib import Path
from unittest.mock import patch, MagicMock
from pact import Verifier

# Add parent directories to path for imports
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from main import app
from core.startup_validation_system import ExpertValidatedStartupSystem
from api.forecast_adapter import ForecastAdapter


class TestAdelaideWeatherProvider:
    """
    Provider tests that verify the API implementation meets the contract expectations
    defined by the frontend consumer tests.
    """
    
    @pytest.fixture(scope="session")
    def verifier(self):
        """Set up Pact verifier with provider configuration."""
        return Verifier(
            provider='adelaide-weather-api',
            provider_base_url='http://localhost:8001',  # Test server port
            pact_urls=[
                # Path to consumer-generated pact files
                str(Path(__file__).parent.parent.parent.parent / 'frontend' / 'pacts' / 
                    'adelaide-weather-frontend-adelaide-weather-api.json')
            ],
            provider_states_setup_url='http://localhost:8001/_pact/provider-states',
            publish_to_broker=False,  # Set to True when using Pact Broker
            publish_version='1.0.0',
            verbose=True
        )
    
    @pytest.fixture(scope="session")
    def test_server(self):
        """Start test server with mocked dependencies for contract testing."""
        import uvicorn
        import threading
        import time
        from unittest.mock import patch, MagicMock
        
        # Mock the startup validation and forecast adapter
        with patch('main.ExpertValidatedStartupSystem') as mock_validator_cls, \
             patch('main.ForecastAdapter') as mock_adapter_cls:
            
            # Configure mock validator
            mock_validator = MagicMock()
            mock_validator.run_expert_startup_validation.return_value = True
            mock_validator_cls.return_value = mock_validator
            
            # Configure mock adapter
            mock_adapter = MagicMock()
            mock_adapter.get_system_health.return_value = {
                "adapter_ready": True,
                "model_loaded": True,
                "indices_ready": True
            }
            mock_adapter_cls.return_value = mock_adapter
            
            # Start test server in background thread
            config = uvicorn.Config(
                app=app,
                host="127.0.0.1",
                port=8001,
                log_level="error"  # Reduce log noise
            )
            server = uvicorn.Server(config)
            
            def run_server():
                server.run()
            
            server_thread = threading.Thread(target=run_server, daemon=True)
            server_thread.start()
            
            # Wait for server to start
            time.sleep(2)
            
            yield server
            
            # Cleanup
            server.should_exit = True
    
    def test_provider_honours_contract(self, verifier, test_server):
        """
        Main test that verifies the provider implementation satisfies all consumer contracts.
        
        This test will:
        1. Start the test server with mocked dependencies
        2. Load consumer-generated pact files
        3. Replay all interactions against the running API
        4. Verify responses match consumer expectations
        """
        
        # Set up provider state handlers
        def provider_state_handler(state):
            """Handle provider states for different test scenarios."""
            if state == "forecast system is operational":
                return setup_operational_system()
            elif state == "forecast system is operational with CAPE data":
                return setup_operational_system_with_cape()
            elif state == "forecast system is down":
                return setup_down_system()
            elif state == "system is healthy and operational":
                return setup_healthy_system()
            elif state == "system is not ready":
                return setup_unhealthy_system()
            elif state == "health endpoint is rate limited":
                return setup_rate_limited_system()
            else:
                return {"status": "ok"}
        
        # Configure provider states
        verifier.set_info(
            provider_states_url='http://localhost:8001/_pact/provider-states',
            provider_states_setup_handler=provider_state_handler
        )
        
        # Run verification
        result = verifier.verify()
        assert result == 0, "Provider verification failed"


def setup_operational_system():
    """Set up system state for operational forecast testing."""
    with patch('main.forecast_adapter') as mock_adapter:
        mock_adapter.forecast_with_uncertainty.return_value = {
            't2m': {
                'value': 20.5,
                'p05': 18.0,
                'p95': 23.0,
                'confidence': 85.5,
                'available': True,
                'analog_count': 45
            },
            'u10': {
                'value': 3.2,
                'p05': 1.5,
                'p95': 5.8,
                'confidence': 78.2,
                'available': True,
                'analog_count': 45
            },
            'v10': {
                'value': -2.1,
                'p05': -4.5,
                'p95': 0.8,
                'confidence': 78.2,
                'available': True,
                'analog_count': 45
            },
            'msl': {
                'value': 101325.0,
                'p05': 101000.0,
                'p95': 101800.0,
                'confidence': 92.1,
                'available': True,
                'analog_count': 48
            }
        }
        
        # Update system health to ready
        import main
        main.system_health = {
            "ready": True,
            "validation_passed": True,
            "adapter_health": {"adapter_ready": True}
        }
        
        return {"status": "ok", "message": "System configured for operational testing"}


def setup_operational_system_with_cape():
    """Set up system state for CAPE-enabled forecast testing."""
    with patch('main.forecast_adapter') as mock_adapter:
        mock_adapter.forecast_with_uncertainty.return_value = {
            't2m': {
                'value': 32.5,
                'p05': 30.0,
                'p95': 35.0,
                'confidence': 88.5,
                'available': True,
                'analog_count': 38
            },
            'cape': {
                'value': 1500.0,
                'p05': 800.0,
                'p95': 2200.0,
                'confidence': 75.2,
                'available': True,
                'analog_count': 32
            },
            'msl': {
                'value': 100980.0,
                'p05': 100500.0,
                'p95': 101300.0,
                'confidence': 91.0,
                'available': True,
                'analog_count': 40
            }
        }
        
        import main
        main.system_health = {
            "ready": True,
            "validation_passed": True,
            "adapter_health": {"adapter_ready": True}
        }
        
        return {"status": "ok", "message": "System configured with CAPE data"}


def setup_down_system():
    """Set up system state for testing system unavailability."""
    import main
    main.system_health = {
        "ready": False,
        "validation_passed": False,
        "error": "System not initialized"
    }
    
    # Ensure forecast_adapter is None or not ready
    main.forecast_adapter = None
    
    return {"status": "ok", "message": "System configured as down"}


def setup_healthy_system():
    """Set up system state for healthy system status testing."""
    import main
    main.system_health = {
        "ready": True,
        "validation_passed": True,
        "adapter_health": {
            "adapter_ready": True,
            "model_loaded": True,
            "indices_ready": True
        }
    }
    
    return {"status": "ok", "message": "System configured as healthy"}


def setup_unhealthy_system():
    """Set up system state for unhealthy system status testing."""
    import main
    main.system_health = {
        "ready": False,
        "validation_passed": False,
        "adapter_health": {"adapter_ready": False}
    }
    
    return {"status": "ok", "message": "System configured as unhealthy"}


def setup_rate_limited_system():
    """Set up system state for rate limiting testing."""
    # This would typically involve configuring the rate limiter
    # For testing purposes, we'll mock the rate limiting behavior
    return {"status": "ok", "message": "System configured for rate limiting"}


# Provider state endpoint for Pact verification
@app.post("/_pact/provider-states")
async def handle_provider_state(request):
    """
    Handle provider state setup for Pact verification.
    
    This endpoint is called by the Pact verifier to set up the system
    in the correct state for each interaction test.
    """
    import json
    
    body = await request.body()
    state_data = json.loads(body) if body else {}
    
    state = state_data.get('state', '')
    
    if state == "forecast system is operational":
        setup_operational_system()
    elif state == "forecast system is operational with CAPE data":
        setup_operational_system_with_cape()
    elif state == "forecast system is down":
        setup_down_system()
    elif state == "system is healthy and operational":
        setup_healthy_system()
    elif state == "system is not ready":
        setup_unhealthy_system()
    elif state == "health endpoint is rate limited":
        setup_rate_limited_system()
    
    return {"result": f"Provider state '{state}' has been set"}


if __name__ == "__main__":
    # Run provider tests
    pytest.main([__file__, "-v", "--tb=short"])