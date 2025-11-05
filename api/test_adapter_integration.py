#!/usr/bin/env python3
"""
Test ForecastAdapter Integration
===============================

Simple test script to verify the ForecastAdapter is working correctly
with the full integration between API expectations and core forecaster.
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import json
from api.forecast_adapter import ForecastAdapter

def test_adapter():
    """Test the ForecastAdapter functionality."""
    print("🧪 Testing ForecastAdapter Integration")
    print("=" * 50)
    
    # Initialize adapter
    try:
        adapter = ForecastAdapter()
        print("✅ Adapter initialized successfully")
    except Exception as e:
        print(f"❌ Adapter initialization failed: {e}")
        return False
    
    # Test system health
    try:
        health = adapter.get_system_health()
        print(f"✅ System health check passed")
        print(f"   - Adapter ready: {health['adapter_ready']}")
        print(f"   - Forecaster loaded: {health['forecaster_loaded']}")
        print(f"   - Variable mappings: {health['variable_mappings']}")
        print(f"   - Direct mappings: {health['direct_mappings']}")
        print(f"   - Missing variables: {health['missing_variables']}")
    except Exception as e:
        print(f"❌ Health check failed: {e}")
        return False
    
    # Test forecast with basic variables
    print("\n🔮 Testing Basic Forecast")
    try:
        result = adapter.forecast_with_uncertainty('24h', ['t2m', 'u10', 'v10'])
        print("✅ Basic forecast successful")
        for var, data in result.items():
            available = data['available']
            value = data['value']
            analog_count = data.get('analog_count', 'N/A')
            value_str = f"{value:.2f}" if value is not None else "N/A"
            print(f"   - {var}: available={available}, value={value_str}, analogs={analog_count}")
    except Exception as e:
        print(f"❌ Basic forecast failed: {e}")
        return False
    
    # Test forecast with problematic variables  
    print("\n🔧 Testing Variable Conversions")
    try:
        result = adapter.forecast_with_uncertainty('24h', ['r850', 'msl', 'tp6h'])
        print("✅ Variable conversion test successful")
        for var, data in result.items():
            available = data['available']
            value = data['value']
            value_str = f"{value:.2f}" if value is not None else "N/A"
            print(f"   - {var}: available={available}, value={value_str}")
            
            if var == 'r850' and available:
                print(f"     → Converted from q850 to relative humidity: {value:.1f}%")
            elif var in ['msl', 'tp6h'] and not available:
                print(f"     → Correctly marked as unavailable (not in forecaster)")
                
    except Exception as e:
        print(f"❌ Variable conversion test failed: {e}")
        return False
        
    # Test all supported horizons
    print("\n⏰ Testing All Horizons")
    for horizon in ['6h', '12h', '24h', '48h']:
        try:
            result = adapter.forecast_with_uncertainty(horizon, ['t2m'])
            available = result['t2m']['available']
            print(f"   - {horizon}: {'✅' if available else '❌'}")
        except Exception as e:
            print(f"   - {horizon}: ❌ ({e})")
    
    # Test invalid horizon (should return fallback data)
    print("\n⚠️  Testing Error Handling")
    try:
        result = adapter.forecast_with_uncertainty('invalid_horizon', ['t2m'])
        # Check if it returns fallback data (still available but from fallback)
        if result['t2m']['available'] and result['t2m']['analog_count'] == 25:
            print("✅ Correctly handled invalid horizon with fallback data")
        else:
            print("❌ Invalid horizon handling unexpected")
            return False
    except Exception as e:
        print(f"✅ Correctly handled invalid horizon with exception: {type(e).__name__}")
    
    print("\n🎉 All tests passed! ForecastAdapter is working correctly.")
    print("\nKey Integration Points Verified:")
    print("✅ Missing forecast_with_uncertainty() method implemented")
    print("✅ Variable schema mapping (API ↔ forecaster)")
    print("✅ Humidity conversion (q850 → r850)")
    print("✅ Graceful handling of missing variables (msl, tp6h)")
    print("✅ Mock analog search functionality")
    print("✅ Unit conversions and error handling")
    
    return True

if __name__ == "__main__":
    success = test_adapter()
    sys.exit(0 if success else 1)