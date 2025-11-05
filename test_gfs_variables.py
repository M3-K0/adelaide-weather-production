#!/usr/bin/env python3
"""
Quick test of GFS API variable coverage for forecasting.
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from scripts.weather_api_client import WeatherApiClient

def test_gfs_variables():
    """Test GFS API for complete atmospheric variable coverage."""
    
    print("🌤️ Testing GFS API Variable Coverage")
    print("=" * 50)
    
    # Create client
    client = WeatherApiClient()
    
    # Get current weather with full atmospheric profile
    print("📡 Fetching current Adelaide weather from GFS...")
    weather_data = client.get_current_weather(include_upper_air=True)
    
    if not weather_data:
        print("❌ Failed to get weather data")
        return False
    
    print(f"✅ Data source: {weather_data['source']}")
    print(f"   Station: {weather_data['station_name']}")
    print(f"   Temperature: {weather_data['temperature']}°C")
    print(f"   Observation time: {weather_data['observation_time']}")
    
    # Convert to ERA5 format
    print("\n🔄 Converting to ERA5 format...")
    era5_data = client.convert_to_era5_format(weather_data)
    
    if not era5_data:
        print("❌ Failed ERA5 conversion")
        return False
    
    # Check required variables for our model
    required_vars = ['z500', 't2m', 't850', 'q850', 'u10', 'v10', 'u850', 'v850', 'cape']
    
    print(f"\n📊 Variable Coverage Check:")
    print("-" * 30)
    
    available_count = 0
    for var in required_vars:
        value = era5_data.get(var)
        status = "✅" if value is not None else "❌"
        print(f"  {status} {var:>6}: {value}")
        if value is not None:
            available_count += 1
    
    coverage_pct = (available_count / len(required_vars)) * 100
    print(f"\n📈 Coverage: {available_count}/{len(required_vars)} variables ({coverage_pct:.1f}%)")
    
    # Show data completeness assessment
    completeness = era5_data.get('data_completeness', 'unknown')
    print(f"🎯 Data completeness: {completeness}")
    
    # Check if missing variables
    missing_vars = era5_data.get('missing_variables', [])
    if missing_vars:
        print(f"⚠️ Missing variables: {missing_vars}")
    
    # Check upper-air data specifically
    if 'upper_air' in weather_data and weather_data['upper_air']:
        print(f"\n🌤️ Upper-air data details:")
        upper = weather_data['upper_air']
        for key, value in upper.items():
            status = "✅" if value is not None else "❌"
            print(f"  {status} {key:>12}: {value}")
    
    # Final assessment
    if coverage_pct >= 80:
        print(f"\n✅ GFS API provides excellent variable coverage for forecasting!")
        return True
    else:
        print(f"\n⚠️ GFS API coverage may be insufficient for optimal forecasting")
        return False

if __name__ == "__main__":
    success = test_gfs_variables()
    print(f"\n{'='*50}")
    if success:
        print("🎉 GFS API integration ready for analog forecasting!")
    else:
        print("🔧 GFS API integration needs improvement")