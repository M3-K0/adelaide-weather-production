#!/usr/bin/env python3
"""
Weather API Client for Adelaide Forecast System
==============================================

Provides unified interface to Bureau of Meteorology (BoM) weather data
and fallback providers for real-time weather observations.

Usage:
    client = WeatherApiClient()
    current_weather = client.get_current_weather()
    era5_format = client.convert_to_era5_format(current_weather)
"""

import requests
import json
import logging
from datetime import datetime, timezone
from typing import Dict, List, Optional, Union
import time
from pathlib import Path

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class WeatherApiClient:
    """Client for Bureau of Meteorology and fallback weather data."""
    
    # Adelaide coordinates
    ADELAIDE_LAT = -34.9285
    ADELAIDE_LON = 138.6007
    
    # BoM station IDs for Adelaide area
    ADELAIDE_STATIONS = {
        'adelaide_airport': '94672',  # Adelaide Airport
        'adelaide_kent_town': '94648',  # Kent Town
        'adelaide_west_terrace': '94675',  # West Terrace
    }
    
    def __init__(self, api_keys: Optional[Dict[str, str]] = None):
        """Initialize weather API client with optional API keys."""
        self.api_keys = api_keys or {}
        # Add WeatherAPI key
        if 'weatherapi' not in self.api_keys:
            self.api_keys['weatherapi'] = '8fb71420c6364a98919121035252410'
            
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'Adelaide-Weather-Forecast-System/1.0'
        })
        
        # Load config if available
        self.config = self._load_config()
        
        # API priority order - put GFS first for complete atmospheric data
        self.api_priority = ['gfs', 'weatherapi', 'open_meteo', 'bom_api', 'bom', 'openweathermap']
        
    def _load_config(self) -> Dict:
        """Load configuration from file if available."""
        config_file = Path(__file__).parent.parent / 'configs' / 'weather_api.yaml'
        if config_file.exists():
            try:
                import yaml
                with open(config_file, 'r') as f:
                    return yaml.safe_load(f)
            except ImportError:
                logger.warning("PyYAML not available, using default config")
            except Exception as e:
                logger.warning(f"Failed to load config: {e}")
        return {}
    
    def get_current_weather(self, include_upper_air: bool = True) -> Optional[Dict]:
        """Get current weather observations with optional upper-air data."""
        
        # Try APIs in priority order
        for api_name in self.api_priority:
            try:
                if api_name == 'gfs':
                    data = self._get_gfs_weather(include_upper_air)
                elif api_name == 'open_meteo':
                    data = self._get_open_meteo_weather(include_upper_air)
                elif api_name == 'bom_api' and 'bom_api_key' in self.api_keys:
                    data = self._get_bom_api_weather()
                elif api_name == 'bom':
                    data = self._get_bom_weather('adelaide_airport')
                elif api_name == 'openweathermap' and 'openweathermap' in self.api_keys:
                    data = self._get_openweather_data()
                elif api_name == 'weatherapi' and 'weatherapi' in self.api_keys:
                    data = self._get_weatherapi_data()
                else:
                    continue
                    
                if data:
                    logger.info(f"Successfully retrieved weather data from {api_name}")
                    return data
                    
            except Exception as e:
                logger.warning(f"API {api_name} failed: {e}")
                continue
        
        logger.error("Failed to retrieve weather data from all sources")
        return None
    
    def _get_open_meteo_weather(self, include_upper_air: bool = True) -> Optional[Dict]:
        """Get comprehensive weather data from Open-Meteo API including upper-air data."""
        try:
            url = "https://api.open-meteo.com/v1/forecast"
            
            # Base parameters
            params = {
                'latitude': self.ADELAIDE_LAT,
                'longitude': self.ADELAIDE_LON,
                'current': [
                    'temperature_2m',
                    'relative_humidity_2m', 
                    'surface_pressure',
                    'wind_speed_10m',
                    'wind_direction_10m'
                ],
                'models': 'gfs_seamless',  # Use GFS model
                'timezone': 'Australia/Adelaide'
            }
            
            # Add upper-air data if requested
            if include_upper_air:
                params['hourly'] = [
                    'temperature_500hPa',
                    'temperature_850hPa',
                    'geopotential_height_500hPa',
                    'geopotential_height_850hPa',
                    'relative_humidity_850hPa',
                    'wind_speed_500hPa',
                    'wind_direction_500hPa',
                    'wind_speed_850hPa', 
                    'wind_direction_850hPa',
                    'wind_speed_10m',
                    'wind_direction_10m',
                    'cape'
                ]
                params['forecast_hours'] = 1  # Just get the first hour (current conditions)
            
            logger.info("Fetching from Open-Meteo API...")
            response = self.session.get(url, params=params, timeout=15)
            response.raise_for_status()
            
            data = response.json()
            
            # Extract current conditions
            current = data.get('current', {})
            
            result = {
                'source': 'open_meteo',
                'station_name': f"Adelaide (Open-Meteo GFS)",
                'observation_time': current.get('time'),
                'temperature': current.get('temperature_2m'),
                'humidity': current.get('relative_humidity_2m'),
                'pressure': current.get('surface_pressure'),  # Already in hPa
                'wind_speed': current.get('wind_speed_10m') * 3.6 if current.get('wind_speed_10m') else None,  # Convert m/s to km/h
                'wind_direction': current.get('wind_direction_10m'),
                'latitude': self.ADELAIDE_LAT,
                'longitude': self.ADELAIDE_LON,
                'raw_data': data
            }
            
            # Add upper-air data if available
            if include_upper_air and 'hourly' in data:
                hourly = data['hourly']
                # Get first hour data (current conditions)
                if hourly.get('time') and len(hourly['time']) > 0:
                    result['upper_air'] = {
                        't500': hourly.get('temperature_500hPa', [None])[0],
                        't850': hourly.get('temperature_850hPa', [None])[0],
                        'z500': hourly.get('geopotential_height_500hPa', [None])[0],
                        'z850': hourly.get('geopotential_height_850hPa', [None])[0],
                        'rh850': hourly.get('relative_humidity_850hPa', [None])[0],
                        'wind_speed_500': hourly.get('wind_speed_500hPa', [None])[0],
                        'wind_dir_500': hourly.get('wind_direction_500hPa', [None])[0],
                        'wind_speed_850': hourly.get('wind_speed_850hPa', [None])[0],
                        'wind_dir_850': hourly.get('wind_direction_850hPa', [None])[0],
                        'cape': hourly.get('cape', [None])[0]
                    }
                    result['data_completeness'] = 'full_profile'
                else:
                    result['data_completeness'] = 'surface_only'
            else:
                result['data_completeness'] = 'surface_only'
            
            return result
            
        except requests.RequestException as e:
            logger.warning(f"Open-Meteo request failed: {e}")
            return None
        except Exception as e:
            logger.warning(f"Open-Meteo error: {e}")
            return None
    
    def _get_gfs_weather(self, include_upper_air: bool = True) -> Optional[Dict]:
        """Get weather data directly from Open-Meteo GFS API with atmospheric profile."""
        try:
            url = "https://api.open-meteo.com/v1/gfs"
            
            # Current surface variables
            current_vars = [
                'temperature_2m',
                'relative_humidity_2m', 
                'surface_pressure',
                'wind_speed_10m',
                'wind_direction_10m'
            ]
            
            # Add atmospheric profile variables if requested
            if include_upper_air:
                current_vars.extend([
                    'geopotential_height_500hPa',
                    'temperature_500hPa',
                    'temperature_850hPa',
                    'relative_humidity_850hPa'
                ])
            
            params = {
                'latitude': self.ADELAIDE_LAT,
                'longitude': self.ADELAIDE_LON,
                'current': ','.join(current_vars),
                'timezone': 'Australia/Adelaide'
            }
            
            # Also get hourly data for wind components and CAPE
            if include_upper_air:
                params['hourly'] = ','.join([
                    'wind_speed_850hPa',
                    'wind_direction_850hPa',
                    'cape'
                ])
                params['forecast_hours'] = 1  # Just current hour
            
            logger.info("Fetching from GFS API...")
            response = self.session.get(url, params=params, timeout=15)
            response.raise_for_status()
            
            data = response.json()
            current = data.get('current', {})
            
            result = {
                'source': 'gfs',
                'station_name': f"Adelaide (NOAA GFS)",
                'observation_time': current.get('time'),
                'temperature': current.get('temperature_2m'),
                'humidity': current.get('relative_humidity_2m'),
                'pressure': current.get('surface_pressure'),
                'wind_speed': current.get('wind_speed_10m') * 3.6 if current.get('wind_speed_10m') else None,
                'wind_direction': current.get('wind_direction_10m'),
                'latitude': self.ADELAIDE_LAT,
                'longitude': self.ADELAIDE_LON,
                'raw_data': data
            }
            
            # Add upper-air data if available
            if include_upper_air:
                # Start with current data
                upper_air = {
                    'z500': current.get('geopotential_height_500hPa'),
                    't500': current.get('temperature_500hPa'),
                    't850': current.get('temperature_850hPa'),
                    'rh850': current.get('relative_humidity_850hPa'),
                    'u850': None,
                    'v850': None,
                    'u500': None,
                    'v500': None,
                    'cape': None
                }
                
                # Add hourly data if available
                if 'hourly' in data and data['hourly'].get('time'):
                    hourly = data['hourly']
                    # Get first hour (current conditions)
                    wind_speed_850 = hourly.get('wind_speed_850hPa', [None])[0]
                    wind_dir_850 = hourly.get('wind_direction_850hPa', [None])[0] 
                    cape_val = hourly.get('cape', [None])[0]
                    
                    # Convert wind speed/direction to u/v components
                    if wind_speed_850 is not None and wind_dir_850 is not None:
                        import math
                        # Convert meteorological wind direction to u/v components
                        wind_dir_rad = math.radians(wind_dir_850)
                        upper_air['u850'] = -wind_speed_850 * math.sin(wind_dir_rad)  # Negative because wind FROM direction
                        upper_air['v850'] = -wind_speed_850 * math.cos(wind_dir_rad)
                    
                    upper_air['cape'] = cape_val
                
                result['upper_air'] = upper_air
                
                # Check data completeness
                core_vars = ['z500', 't850', 'rh850']  # Essential atmospheric profile
                wind_vars = ['u850', 'v850']  # Wind components
                
                missing_core = [var for var in core_vars if upper_air[var] is None]
                missing_wind = [var for var in wind_vars if upper_air[var] is None]
                
                if len(missing_core) == 0 and len(missing_wind) == 0:
                    result['data_completeness'] = 'full_profile'
                elif len(missing_core) == 0:
                    result['data_completeness'] = 'partial_profile'  # Core data but missing winds
                else:
                    result['data_completeness'] = 'surface_only'
            else:
                result['data_completeness'] = 'surface_only'
            
            return result
            
        except requests.RequestException as e:
            logger.warning(f"GFS API request failed: {e}")
            return None
        except Exception as e:
            logger.warning(f"GFS API error: {e}")
            return None
    
    def _get_bom_weather(self, station: str) -> Optional[Dict]:
        """Get weather data from BoM JSON endpoints."""
        station_id = self.ADELAIDE_STATIONS.get(station, station)
        
        # BoM JSON endpoint pattern
        url = f"http://www.bom.gov.au/fwo/IDS60801/IDS60801.{station_id}.json"
        
        try:
            logger.info(f"Fetching BoM data from: {url}")
            response = self.session.get(url, timeout=10)
            response.raise_for_status()
            
            data = response.json()
            
            # Extract latest observation
            if 'observations' in data and 'data' in data['observations']:
                observations = data['observations']['data']
                if observations:
                    latest = observations[0]  # Most recent observation
                    
                    return {
                        'source': 'bom',
                        'station_name': latest.get('name', 'Unknown'),
                        'observation_time': latest.get('aifstime_utc'),
                        'temperature': latest.get('air_temp'),
                        'humidity': latest.get('rel_hum'),
                        'pressure': latest.get('press_msl'),
                        'wind_speed': latest.get('wind_spd_kmh'),
                        'wind_direction': latest.get('wind_dir'),
                        'rainfall': latest.get('rain_trace'),
                        'latitude': latest.get('lat'),
                        'longitude': latest.get('lon'),
                        'raw_data': latest
                    }
            
            logger.warning("No observation data found in BoM response")
            return None
            
        except requests.RequestException as e:
            logger.warning(f"BoM request failed: {e}")
            return None
        except (KeyError, IndexError, json.JSONDecodeError) as e:
            logger.warning(f"BoM data parsing failed: {e}")
            return None
    
    def _get_bom_api_weather(self) -> Optional[Dict]:
        """Get weather data from official BoM API if available."""
        try:
            # This would use official BoM API endpoints if you have access
            # Format depends on your specific API access
            api_key = self.api_keys.get('bom_api_key')
            
            # Example endpoint (adjust based on your actual API access)
            url = f"https://api.weather.bom.gov.au/v1/observations/current"
            params = {
                'location': 'adelaide',
                'api_key': api_key
            }
            
            logger.info("Fetching from BoM API...")
            response = self.session.get(url, params=params, timeout=10)
            response.raise_for_status()
            
            data = response.json()
            
            # Convert to our standard format
            return {
                'source': 'bom_api',
                'station_name': data.get('station_name', 'Adelaide'),
                'observation_time': data.get('observation_time'),
                'temperature': data.get('temperature'),
                'humidity': data.get('humidity'),
                'pressure': data.get('pressure'),
                'wind_speed': data.get('wind_speed'),
                'wind_direction': data.get('wind_direction'),
                'latitude': self.ADELAIDE_LAT,
                'longitude': self.ADELAIDE_LON,
                'raw_data': data
            }
            
        except requests.RequestException as e:
            logger.warning(f"BoM API request failed: {e}")
            return None
        except Exception as e:
            logger.warning(f"BoM API error: {e}")
            return None
    
    def _get_fallback_weather(self) -> Optional[Dict]:
        """Get weather data from fallback providers."""
        
        # Try OpenWeatherMap if API key available
        if 'openweathermap' in self.api_keys:
            return self._get_openweather_data()
            
        # Try WeatherAPI if available
        if 'weatherapi' in self.api_keys:
            return self._get_weatherapi_data()
            
        logger.warning("No fallback weather APIs configured")
        return None
    
    def _get_openweather_data(self) -> Optional[Dict]:
        """Get weather data from OpenWeatherMap."""
        try:
            api_key = self.api_keys['openweathermap']
            url = "http://api.openweathermap.org/data/2.5/weather"
            params = {
                'lat': self.ADELAIDE_LAT,
                'lon': self.ADELAIDE_LON,
                'appid': api_key,
                'units': 'metric'
            }
            
            logger.info("Fetching from OpenWeatherMap...")
            response = self.session.get(url, params=params, timeout=10)
            response.raise_for_status()
            
            data = response.json()
            
            return {
                'source': 'openweathermap',
                'station_name': f"Adelaide ({data.get('name', 'Unknown')})",
                'observation_time': datetime.fromtimestamp(data['dt'], tz=timezone.utc).isoformat(),
                'temperature': data['main']['temp'],
                'humidity': data['main']['humidity'],
                'pressure': data['main']['pressure'],
                'wind_speed': data.get('wind', {}).get('speed', 0) * 3.6,  # Convert m/s to km/h
                'wind_direction': data.get('wind', {}).get('deg'),
                'latitude': data['coord']['lat'],
                'longitude': data['coord']['lon'],
                'raw_data': data
            }
            
        except Exception as e:
            logger.warning(f"OpenWeatherMap error: {e}")
            return None
    
    def _get_weatherapi_data(self) -> Optional[Dict]:
        """Get weather data from WeatherAPI."""
        try:
            api_key = self.api_keys['weatherapi']
            url = "http://api.weatherapi.com/v1/current.json"
            params = {
                'key': api_key,
                'q': f"{self.ADELAIDE_LAT},{self.ADELAIDE_LON}",
                'aqi': 'no'
            }
            
            logger.info("Fetching from WeatherAPI...")
            response = self.session.get(url, params=params, timeout=10)
            response.raise_for_status()
            
            data = response.json()
            current = data['current']
            location = data['location']
            
            return {
                'source': 'weatherapi',
                'station_name': f"Adelaide ({location['name']})",
                'observation_time': current['last_updated'],
                'temperature': current['temp_c'],
                'humidity': current['humidity'],
                'pressure': current['pressure_mb'],
                'wind_speed': current['wind_kph'],
                'wind_direction': current['wind_degree'],
                'latitude': location['lat'],
                'longitude': location['lon'],
                'raw_data': data
            }
            
        except Exception as e:
            logger.warning(f"WeatherAPI error: {e}")
            return None
    
    def convert_to_era5_format(self, weather_data: Dict) -> Optional[Dict]:
        """Convert weather API data to ERA5-like format for our model."""
        if not weather_data:
            return None
            
        try:
            import math
            
            # Extract basic meteorological variables
            temp_c = weather_data.get('temperature')
            humidity = weather_data.get('humidity')
            pressure = weather_data.get('pressure')
            wind_speed = weather_data.get('wind_speed')
            wind_dir = weather_data.get('wind_direction')
            source = weather_data.get('source', 'unknown')
            
            # Base ERA5 format
            era5_data = {
                # Surface variables
                't2m': temp_c + 273.15 if temp_c is not None else None,
                'r2m': humidity,  # Relative humidity (%)
                'msl': pressure * 100 if pressure is not None else None,  # Convert hPa to Pa
                'u10': None,
                'v10': None,
                'tp': 0.0,  # Total precipitation
                
                # Metadata
                'latitude': weather_data.get('latitude', self.ADELAIDE_LAT),
                'longitude': weather_data.get('longitude', self.ADELAIDE_LON),
                'time': weather_data.get('observation_time'),
                'source': source,
                'station_name': weather_data.get('station_name'),
            }
            
            # Convert wind speed/direction to u/v components (surface)
            if wind_speed is not None and wind_dir is not None:
                wind_speed_ms = wind_speed / 3.6  # Convert km/h to m/s
                wind_dir_rad = math.radians(wind_dir)
                
                # Wind components (meteorological convention)
                era5_data['u10'] = -wind_speed_ms * math.sin(wind_dir_rad)
                era5_data['v10'] = -wind_speed_ms * math.cos(wind_dir_rad)
            
            # Handle upper-air data if available (from Open-Meteo)
            if 'upper_air' in weather_data and weather_data['upper_air']:
                upper = weather_data['upper_air']
                
                # Temperature levels (convert Celsius to Kelvin)
                era5_data['t500'] = upper.get('t500') + 273.15 if upper.get('t500') is not None else None
                era5_data['t850'] = upper.get('t850') + 273.15 if upper.get('t850') is not None else None
                
                # Geopotential heights (already in meters)
                era5_data['z500'] = upper.get('z500')
                era5_data['z850'] = upper.get('z850')
                
                # CAPE (already in J/kg)
                era5_data['cape'] = upper.get('cape')
                
                # Convert 850mb relative humidity to specific humidity
                if upper.get('rh850') and era5_data['t850']:
                    # Rough conversion - could be improved with proper calculation
                    era5_data['q850'] = self._convert_relative_to_specific_humidity_at_level(
                        era5_data['t850'] - 273.15, upper['rh850'], 850)
                else:
                    era5_data['q850'] = None
                
                # Convert 500mb and 850mb wind components
                for level, level_name in [(500, '500'), (850, '850')]:
                    u_key = f'u{level}'
                    v_key = f'v{level}'
                    ws_key = f'wind_speed_{level}'
                    wd_key = f'wind_dir_{level}'
                    
                    # First check if u/v components are directly available
                    if upper.get(u_key) is not None and upper.get(v_key) is not None:
                        era5_data[f'u{level}'] = upper[u_key]
                        era5_data[f'v{level}'] = upper[v_key]
                    # Otherwise convert from wind speed/direction
                    elif upper.get(ws_key) is not None and upper.get(wd_key) is not None:
                        wind_speed_ms = upper[ws_key]  # Already in m/s from Open-Meteo
                        wind_dir_rad = math.radians(upper[wd_key])
                        
                        era5_data[f'u{level}'] = -wind_speed_ms * math.sin(wind_dir_rad)
                        era5_data[f'v{level}'] = -wind_speed_ms * math.cos(wind_dir_rad)
                    else:
                        era5_data[f'u{level}'] = None
                        era5_data[f'v{level}'] = None
                
                era5_data['data_completeness'] = 'full_profile'
                era5_data['missing_variables'] = []
                
            else:
                # Surface-only data
                era5_data.update({
                    'z500': None, 't500': None, 'u500': None, 'v500': None,
                    't850': None, 'q850': None, 'u850': None, 'v850': None,
                    'cape': None
                })
                era5_data['data_completeness'] = 'surface_only'
                era5_data['missing_variables'] = ['z500', 't500', 'u500', 'v500', 
                                                't850', 'q850', 'u850', 'v850', 'cape']
                
                # Use surface humidity as poor proxy for 850mb
                if temp_c and humidity and pressure:
                    era5_data['q2m'] = self._convert_relative_to_specific_humidity(
                        temp_c, humidity, pressure)
            
            return era5_data
            
        except Exception as e:
            logger.error(f"ERA5 format conversion failed: {e}")
            return None
    
    def _convert_relative_to_specific_humidity(self, temp_c: float, rh: float, pressure_hpa: float) -> float:
        """Convert relative humidity to specific humidity (rough approximation)."""
        try:
            import math
            # Saturation vapor pressure (Magnus formula)
            es = 6.112 * math.exp(17.67 * temp_c / (temp_c + 243.5))  # hPa
            
            # Actual vapor pressure
            e = es * rh / 100.0  # hPa
            
            # Specific humidity (kg/kg)
            q = 0.622 * e / (pressure_hpa - 0.378 * e)
            
            return q
        except Exception as e:
            logger.error(f"Humidity conversion failed: {e}")
            return None
    
    def _convert_relative_to_specific_humidity_at_level(self, temp_c: float, rh: float, pressure_hpa: float) -> float:
        """Convert relative humidity to specific humidity at pressure level."""
        # Same calculation but more explicit about pressure level
        return self._convert_relative_to_specific_humidity(temp_c, rh, pressure_hpa)
    
    def validate_data_quality(self, era5_data: Dict) -> bool:
        """Validate that converted data is suitable for forecasting."""
        if not era5_data:
            return False
            
        # Check required variables
        required_vars = ['t2m', 'r2m', 'msl', 'u10', 'v10']
        missing_vars = [var for var in required_vars if era5_data.get(var) is None]
        
        if missing_vars:
            logger.warning(f"Missing required variables: {missing_vars}")
            return False
        
        # Check reasonable ranges
        t2m = era5_data['t2m']
        if not (200 < t2m < 350):  # -73°C to 77°C in Kelvin
            logger.warning(f"Temperature out of range: {t2m}K")
            return False
            
        r2m = era5_data['r2m']
        if not (0 <= r2m <= 100):
            logger.warning(f"Humidity out of range: {r2m}%")
            return False
            
        msl = era5_data['msl']
        if not (80000 < msl < 110000):  # 800-1100 hPa in Pa
            logger.warning(f"Pressure out of range: {msl}Pa")
            return False
        
        logger.info("Data quality validation passed")
        return True
    
    def get_forecast_ready_data(self) -> Optional[Dict]:
        """Get current weather data in format ready for forecasting."""
        # Get current weather
        current_weather = self.get_current_weather()
        if not current_weather:
            logger.error("Failed to get current weather data")
            return None
        
        # Convert to ERA5 format
        era5_data = self.convert_to_era5_format(current_weather)
        if not era5_data:
            logger.error("Failed to convert to ERA5 format")
            return None
        
        # Validate data quality
        if not self.validate_data_quality(era5_data):
            logger.error("Data quality validation failed")
            return None
        
        logger.info(f"Successfully prepared forecast data from {era5_data['source']}")
        return era5_data

def main():
    """Test the weather API client."""
    # Example usage
    client = WeatherApiClient()
    
    # Test getting current weather
    print("Testing weather data retrieval...")
    weather_data = client.get_current_weather()
    
    if weather_data:
        print(f"✅ Current weather from {weather_data['source']}:")
        print(f"  Station: {weather_data['station_name']}")
        print(f"  Temperature: {weather_data['temperature']}°C")
        print(f"  Humidity: {weather_data['humidity']}%")
        print(f"  Pressure: {weather_data['pressure']} hPa")
        
        # Test conversion to ERA5 format
        era5_data = client.convert_to_era5_format(weather_data)
        if era5_data:
            print(f"\n✅ ERA5 format conversion successful:")
            print(f"  t2m: {era5_data['t2m']:.2f}K" if era5_data['t2m'] else "  t2m: None")
            print(f"  msl: {era5_data['msl']:.0f}Pa" if era5_data['msl'] else "  msl: None")
            print(f"  u10: {era5_data['u10']:.2f}m/s" if era5_data['u10'] else "  u10: None")
            print(f"  v10: {era5_data['v10']:.2f}m/s" if era5_data['v10'] else "  v10: None")
            print(f"  Data completeness: {era5_data.get('data_completeness', 'unknown')}")
            
            # Show upper-air data if available
            if era5_data.get('data_completeness') == 'full_profile':
                print(f"  🌤️ Upper-air data:")
                print(f"    z500: {era5_data['z500']:.0f}m" if era5_data['z500'] else "    z500: None")
                print(f"    t850: {era5_data['t850']:.2f}K" if era5_data['t850'] else "    t850: None")
                print(f"    cape: {era5_data['cape']:.0f}J/kg" if era5_data['cape'] else "    cape: None")
            
            # Test validation
            if client.validate_data_quality(era5_data):
                print("✅ Data quality validation passed")
            else:
                print("❌ Data quality validation failed")
        else:
            print("❌ ERA5 format conversion failed")
    else:
        print("❌ Failed to get weather data")

if __name__ == "__main__":
    main()