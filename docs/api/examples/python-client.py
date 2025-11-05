#!/usr/bin/env python3
"""
Adelaide Weather Forecasting API - Python Client
===============================================

Production-ready Python client for the Adelaide Weather Forecasting API.
Includes error handling, retry logic, and comprehensive examples.

Features:
- Automatic retry with exponential backoff
- Rate limit handling
- Request/response logging
- Type hints and docstrings
- Comprehensive error handling
- Session management with connection pooling

Requirements:
    pip install requests

Usage:
    export WEATHER_API_TOKEN="your_token_here"
    python python-client.py

Author: Adelaide Weather API Team
Version: 1.0.0
"""

import os
import sys
import time
import json
import logging
from datetime import datetime, timezone
from typing import Dict, List, Optional, Union, Any
from dataclasses import dataclass
import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry


# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger('adelaide_weather_client')


@dataclass
class ForecastRequest:
    """Forecast request parameters."""
    horizon: str = "24h"
    variables: List[str] = None
    
    def __post_init__(self):
        if self.variables is None:
            self.variables = ["t2m", "u10", "v10", "msl"]


@dataclass
class ClientConfig:
    """Client configuration."""
    base_url: str = "https://api.adelaideweather.example.com"
    timeout: int = 30
    max_retries: int = 3
    backoff_factor: float = 1.0
    rate_limit_retry_delay: int = 60


class WeatherAPIError(Exception):
    """Base exception for Weather API errors."""
    def __init__(self, message: str, status_code: int = None, correlation_id: str = None):
        super().__init__(message)
        self.status_code = status_code
        self.correlation_id = correlation_id


class AuthenticationError(WeatherAPIError):
    """Authentication failed."""
    pass


class RateLimitError(WeatherAPIError):
    """Rate limit exceeded."""
    def __init__(self, message: str, retry_after: int = 60):
        super().__init__(message)
        self.retry_after = retry_after


class ValidationError(WeatherAPIError):
    """Request validation failed."""
    pass


class ServiceUnavailableError(WeatherAPIError):
    """Service is unavailable."""
    pass


class AdelaideWeatherClient:
    """
    Production-ready client for the Adelaide Weather Forecasting API.
    
    Features:
    - Automatic retry with exponential backoff
    - Rate limit handling
    - Session management with connection pooling
    - Comprehensive error handling
    - Request/response logging
    """
    
    # Valid forecast horizons
    VALID_HORIZONS = ["6h", "12h", "24h", "48h"]
    
    # Valid weather variables
    VALID_VARIABLES = [
        "t2m", "u10", "v10", "msl", "r850", 
        "tp6h", "cape", "t850", "z500"
    ]
    
    def __init__(self, api_token: str, config: ClientConfig = None):
        """
        Initialize the weather client.
        
        Args:
            api_token: API authentication token
            config: Client configuration (optional)
        """
        if not api_token:
            raise ValueError("API token is required")
        
        self.api_token = api_token
        self.config = config or ClientConfig()
        
        # Set up session with retry strategy
        self.session = self._create_session()
        
        logger.info(f"Adelaide Weather Client initialized for {self.config.base_url}")
    
    def _create_session(self) -> requests.Session:
        """Create requests session with retry strategy and connection pooling."""
        session = requests.Session()
        
        # Configure retry strategy
        retry_strategy = Retry(
            total=self.config.max_retries,
            status_forcelist=[429, 500, 502, 503, 504],
            method_whitelist=["HEAD", "GET", "OPTIONS"],
            backoff_factor=self.config.backoff_factor,
            raise_on_status=False
        )
        
        # Mount adapter with retry strategy
        adapter = HTTPAdapter(
            max_retries=retry_strategy,
            pool_connections=10,
            pool_maxsize=20
        )
        session.mount("http://", adapter)
        session.mount("https://", adapter)
        
        # Set default headers
        session.headers.update({
            'Authorization': f'Bearer {self.api_token}',
            'Accept': 'application/json',
            'User-Agent': 'Adelaide-Weather-Python-Client/1.0.0'
        })
        
        return session
    
    def _make_request(self, endpoint: str, params: Dict = None) -> Dict[str, Any]:
        """
        Make authenticated API request with error handling.
        
        Args:
            endpoint: API endpoint (e.g., '/forecast')
            params: Query parameters
            
        Returns:
            JSON response data
            
        Raises:
            WeatherAPIError: For various API errors
        """
        url = f"{self.config.base_url}{endpoint}"
        
        try:
            logger.debug(f"Making request to {url} with params: {params}")
            
            response = self.session.get(
                url,
                params=params,
                timeout=self.config.timeout
            )
            
            # Log response details
            logger.debug(f"Response status: {response.status_code}")
            logger.debug(f"Response headers: {dict(response.headers)}")
            
            return self._handle_response(response)
            
        except requests.exceptions.Timeout:
            raise WeatherAPIError(f"Request timeout after {self.config.timeout}s")
        except requests.exceptions.ConnectionError as e:
            raise WeatherAPIError(f"Connection error: {str(e)}")
        except requests.exceptions.RequestException as e:
            raise WeatherAPIError(f"Request failed: {str(e)}")
    
    def _handle_response(self, response: requests.Response) -> Dict[str, Any]:
        """
        Handle API response and convert errors to appropriate exceptions.
        
        Args:
            response: HTTP response object
            
        Returns:
            Parsed JSON response
            
        Raises:
            WeatherAPIError: For various error conditions
        """
        correlation_id = response.headers.get('X-Correlation-ID')
        
        if response.status_code == 200:
            try:
                return response.json()
            except json.JSONDecodeError:
                raise WeatherAPIError("Invalid JSON response", response.status_code, correlation_id)
        
        # Handle error responses
        try:
            error_data = response.json()
            error_message = error_data.get('error', {}).get('message', 'Unknown error')
        except json.JSONDecodeError:
            error_message = f"HTTP {response.status_code}: {response.reason}"
        
        if response.status_code == 401:
            raise AuthenticationError(error_message, response.status_code, correlation_id)
        elif response.status_code == 403:
            raise AuthenticationError(error_message, response.status_code, correlation_id)
        elif response.status_code == 400:
            raise ValidationError(error_message, response.status_code, correlation_id)
        elif response.status_code == 429:
            retry_after = int(response.headers.get('Retry-After', 60))
            raise RateLimitError(error_message, retry_after)
        elif response.status_code == 503:
            raise ServiceUnavailableError(error_message, response.status_code, correlation_id)
        else:
            raise WeatherAPIError(error_message, response.status_code, correlation_id)
    
    def get_health(self) -> Dict[str, Any]:
        """
        Get system health status.
        
        Returns:
            Health status information
        """
        return self._make_request('/health')
    
    def get_forecast(self, request: Union[ForecastRequest, Dict] = None) -> Dict[str, Any]:
        """
        Get weather forecast with uncertainty quantification.
        
        Args:
            request: Forecast request parameters
            
        Returns:
            Forecast data with uncertainty bounds
            
        Example:
            >>> client = AdelaideWeatherClient(token)
            >>> forecast = client.get_forecast(
            ...     ForecastRequest(horizon="24h", variables=["t2m", "u10", "v10"])
            ... )
            >>> print(f"Temperature: {forecast['variables']['t2m']['value']}°C")
        """
        if isinstance(request, dict):
            request = ForecastRequest(**request)
        elif request is None:
            request = ForecastRequest()
        
        # Validate parameters
        if request.horizon not in self.VALID_HORIZONS:
            raise ValidationError(f"Invalid horizon '{request.horizon}'. Must be one of: {self.VALID_HORIZONS}")
        
        invalid_vars = [var for var in request.variables if var not in self.VALID_VARIABLES]
        if invalid_vars:
            raise ValidationError(f"Invalid variables: {invalid_vars}. Valid: {self.VALID_VARIABLES}")
        
        params = {
            'horizon': request.horizon,
            'vars': ','.join(request.variables)
        }
        
        return self._make_request('/forecast', params)
    
    def get_metrics(self) -> str:
        """
        Get Prometheus metrics.
        
        Returns:
            Prometheus metrics in text format
        """
        response = self.session.get(
            f"{self.config.base_url}/metrics",
            timeout=self.config.timeout
        )
        
        if response.status_code == 200:
            return response.text
        else:
            self._handle_response(response)
    
    def get_analogs(self, horizon: str = "24h") -> Dict[str, Any]:
        """
        Get detailed analog patterns analysis.
        
        Args:
            horizon: Forecast horizon to analyze
            
        Returns:
            Historical analog patterns data
        """
        if horizon not in self.VALID_HORIZONS:
            raise ValidationError(f"Invalid horizon '{horizon}'. Must be one of: {self.VALID_HORIZONS}")
        
        params = {'horizon': horizon}
        return self._make_request('/analogs', params)
    
    def wait_for_ready(self, max_wait: int = 300, check_interval: int = 5) -> bool:
        """
        Wait for the API to become ready.
        
        Args:
            max_wait: Maximum time to wait in seconds
            check_interval: Check interval in seconds
            
        Returns:
            True if API is ready, False if timeout
        """
        start_time = time.time()
        
        while time.time() - start_time < max_wait:
            try:
                health = self.get_health()
                if health.get('ready', False):
                    logger.info("API is ready")
                    return True
                else:
                    logger.info("API not ready yet, waiting...")
            except Exception as e:
                logger.debug(f"Health check failed: {e}")
            
            time.sleep(check_interval)
        
        logger.warning(f"API did not become ready within {max_wait} seconds")
        return False
    
    def close(self):
        """Close the session and clean up resources."""
        if self.session:
            self.session.close()
            logger.info("Client session closed")


class ForecastAnalyzer:
    """Helper class for analyzing forecast results."""
    
    @staticmethod
    def print_forecast_summary(forecast: Dict[str, Any]):
        """Print a formatted forecast summary."""
        print(f"\n{'='*60}")
        print(f"Adelaide Weather Forecast ({forecast['horizon']})")
        print(f"{'='*60}")
        print(f"Generated at: {forecast['generated_at']}")
        print(f"Latency: {forecast['latency_ms']:.1f}ms")
        
        print(f"\n--- Narrative ---")
        print(forecast['narrative'])
        
        print(f"\n--- Variables ---")
        for var_name, var_data in forecast['variables'].items():
            if var_data['available']:
                print(f"{var_name:>6}: {var_data['value']:8.1f} "
                      f"[{var_data['p05']:6.1f} to {var_data['p95']:6.1f}] "
                      f"(confidence: {var_data['confidence']:5.1%})")
            else:
                print(f"{var_name:>6}: Not available")
        
        if forecast.get('wind10m', {}).get('available'):
            wind = forecast['wind10m']
            print(f"\n--- Wind ---")
            print(f"Speed: {wind['speed']:.1f} m/s")
            print(f"Direction: {wind['direction']:.0f}°")
        
        print(f"\n--- Risk Assessment ---")
        risks = forecast['risk_assessment']
        for risk_type, level in risks.items():
            print(f"{risk_type.replace('_', ' ').title():>20}: {level}")
        
        print(f"\n--- Analog Summary ---")
        analogs = forecast['analogs_summary']
        print(f"Most similar date: {analogs['most_similar_date']}")
        print(f"Similarity score: {analogs['similarity_score']:.1%}")
        print(f"Analog count: {analogs['analog_count']}")
        print(f"Outcome: {analogs['outcome_description']}")
        
        print(f"\n--- Confidence ---")
        print(forecast['confidence_explanation'])
        print(f"{'='*60}\n")
    
    @staticmethod
    def extract_temperature_info(forecast: Dict[str, Any]) -> Dict[str, float]:
        """Extract temperature information."""
        temp_data = forecast['variables'].get('t2m', {})
        if not temp_data.get('available'):
            return {}
        
        return {
            'temperature': temp_data['value'],
            'min_temp': temp_data['p05'],
            'max_temp': temp_data['p95'],
            'confidence': temp_data['confidence']
        }
    
    @staticmethod
    def extract_wind_info(forecast: Dict[str, Any]) -> Dict[str, float]:
        """Extract wind information."""
        wind_data = forecast.get('wind10m', {})
        if not wind_data.get('available'):
            return {}
        
        return {
            'speed': wind_data['speed'],
            'direction': wind_data['direction'],
            'gust': wind_data.get('gust')
        }
    
    @staticmethod
    def assess_severe_weather_risk(forecast: Dict[str, Any]) -> Dict[str, str]:
        """Assess severe weather risks."""
        risks = forecast['risk_assessment']
        
        # Determine overall risk level
        risk_levels = ['minimal', 'low', 'moderate', 'high', 'extreme']
        max_risk_index = max(risk_levels.index(level) for level in risks.values())
        overall_risk = risk_levels[max_risk_index]
        
        return {
            'overall_risk': overall_risk,
            'primary_concerns': [
                risk_type for risk_type, level in risks.items()
                if level in ['high', 'extreme']
            ],
            'details': risks
        }


def main():
    """Main example demonstrating the client usage."""
    # Get API token from environment
    api_token = os.getenv('WEATHER_API_TOKEN')
    if not api_token:
        print("❌ Please set WEATHER_API_TOKEN environment variable")
        print("   export WEATHER_API_TOKEN='your_token_here'")
        sys.exit(1)
    
    # Create client
    config = ClientConfig(
        base_url=os.getenv('WEATHER_API_BASE_URL', 'https://api.adelaideweather.example.com'),
        timeout=30,
        max_retries=3
    )
    
    client = AdelaideWeatherClient(api_token, config)
    
    try:
        print("🔍 Checking API health...")
        health = client.get_health()
        
        if not health['ready']:
            print("⚠️  API is not ready. Waiting for system to start...")
            if not client.wait_for_ready(max_wait=60):
                print("❌ API did not become ready in time")
                return
        
        print("✅ API is healthy and ready")
        
        # Example 1: Basic forecast
        print("\n📊 Getting 24-hour forecast...")
        forecast = client.get_forecast()
        ForecastAnalyzer.print_forecast_summary(forecast)
        
        # Example 2: Extended forecast with weather variables
        print("🌦️  Getting extended forecast with weather variables...")
        extended_request = ForecastRequest(
            horizon="48h",
            variables=["t2m", "u10", "v10", "msl", "cape", "tp6h"]
        )
        extended_forecast = client.get_forecast(extended_request)
        
        # Analyze severe weather risk
        risk_assessment = ForecastAnalyzer.assess_severe_weather_risk(extended_forecast)
        print(f"Overall risk level: {risk_assessment['overall_risk']}")
        if risk_assessment['primary_concerns']:
            print(f"Primary concerns: {', '.join(risk_assessment['primary_concerns'])}")
        
        # Example 3: Temperature trend analysis
        print("\n🌡️  Analyzing temperature trends...")
        horizons = ["6h", "12h", "24h", "48h"]
        temps = []
        
        for horizon in horizons:
            try:
                forecast = client.get_forecast(ForecastRequest(
                    horizon=horizon,
                    variables=["t2m"]
                ))
                temp_info = ForecastAnalyzer.extract_temperature_info(forecast)
                if temp_info:
                    temps.append((horizon, temp_info['temperature']))
                    print(f"{horizon:>4}: {temp_info['temperature']:5.1f}°C "
                          f"(confidence: {temp_info['confidence']:5.1%})")
            except Exception as e:
                print(f"{horizon:>4}: Error - {e}")
        
        # Example 4: Wind analysis
        print("\n💨 Wind analysis...")
        wind_forecast = client.get_forecast(ForecastRequest(
            horizon="12h",
            variables=["u10", "v10"]
        ))
        wind_info = ForecastAnalyzer.extract_wind_info(wind_forecast)
        if wind_info:
            print(f"Wind speed: {wind_info['speed']:.1f} m/s")
            print(f"Wind direction: {wind_info['direction']:.0f}°")
        
        # Example 5: Historical analogs (if available)
        try:
            print("\n📚 Exploring historical analogs...")
            analogs = client.get_analogs("24h")
            print(f"Found {len(analogs['top_analogs'])} similar patterns")
            
            for i, analog in enumerate(analogs['top_analogs'][:3], 1):
                print(f"  {i}. {analog['date']} (similarity: {analog['similarity_score']:.1%})")
                print(f"     {analog['outcome_narrative']}")
        except Exception as e:
            print(f"Analog data not available: {e}")
        
    except RateLimitError as e:
        print(f"⚠️  Rate limit exceeded. Retry after {e.retry_after} seconds")
    except AuthenticationError as e:
        print(f"❌ Authentication failed: {e}")
        print("   Please check your API token")
    except ValidationError as e:
        print(f"❌ Validation error: {e}")
    except ServiceUnavailableError as e:
        print(f"⚠️  Service unavailable: {e}")
        print("   The forecasting system may be starting up")
    except WeatherAPIError as e:
        print(f"❌ API error: {e}")
        if e.correlation_id:
            print(f"   Correlation ID: {e.correlation_id}")
    except Exception as e:
        print(f"❌ Unexpected error: {e}")
        logger.exception("Unexpected error occurred")
    finally:
        client.close()


if __name__ == "__main__":
    main()