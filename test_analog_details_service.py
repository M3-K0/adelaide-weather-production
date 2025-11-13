#!/usr/bin/env python3
"""
Test script for the new get_analog_details() service method
"""

import asyncio
import json
import sys
from pathlib import Path

# Add project root to path
sys.path.append(str(Path(__file__).parent))

from api.services.analog_search import get_analog_search_service

async def test_analog_details():
    """Test the comprehensive get_analog_details() method"""
    print("🧪 Testing get_analog_details() service method...")
    
    try:
        # Initialize the service
        service = await get_analog_search_service()
        print("✅ Service initialized successfully")
        
        # Test basic functionality
        print("\n📊 Testing basic analog details...")
        result = await service.get_analog_details(
            horizon=24,
            variable="temperature",
            k=10
        )
        
        if result.get("success"):
            print("✅ Basic test successful")
            print(f"   - Found {len(result.get('analogs', []))} analogs")
            print(f"   - Processing time: {result['query_metadata']['processing_time_ms']:.1f}ms")
            print(f"   - Correlation ID: {result['query_metadata']['correlation_id']}")
        else:
            print(f"❌ Basic test failed: {result.get('error', 'Unknown error')}")
            return False
        
        # Test different horizons
        print("\n🔄 Testing different forecast horizons...")
        horizons = [6, 12, 24, 48]
        for horizon in horizons:
            result = await service.get_analog_details(
                horizon=horizon,
                variable="precipitation", 
                k=5
            )
            
            if result.get("success"):
                analogs_count = len(result.get('analogs', []))
                processing_time = result['query_metadata']['processing_time_ms']
                print(f"   - {horizon}h: {analogs_count} analogs in {processing_time:.1f}ms ✅")
            else:
                print(f"   - {horizon}h: Failed - {result.get('error')} ❌")
        
        # Test different variables
        print("\n🌡️ Testing different weather variables...")
        variables = ["temperature", "precipitation", "wind", "pressure"]
        for variable in variables:
            result = await service.get_analog_details(
                horizon=12,
                variable=variable,
                k=3
            )
            
            if result.get("success"):
                confidence = result.get('similarity_analysis', {}).get('confidence_metrics', {}).get('overall_confidence', 0)
                print(f"   - {variable}: confidence={confidence:.3f} ✅")
            else:
                print(f"   - {variable}: Failed - {result.get('error')} ❌")
        
        # Test response structure
        print("\n🔍 Validating response structure...")
        result = await service.get_analog_details(horizon=24, variable="temperature", k=5)
        
        expected_keys = [
            'query_metadata', 'analogs', 'search_metadata', 
            'timeline_data', 'similarity_analysis', 'meteorological_context'
        ]
        
        missing_keys = [key for key in expected_keys if key not in result]
        if missing_keys:
            print(f"❌ Missing response keys: {missing_keys}")
        else:
            print("✅ All expected response keys present")
            
            # Check analog details structure
            if result.get('analogs'):
                analog = result['analogs'][0]
                analog_keys = ['rank', 'analog_index', 'similarity_score', 'temporal_info', 'forecast_outcome']
                missing_analog_keys = [key for key in analog_keys if key not in analog]
                if missing_analog_keys:
                    print(f"❌ Missing analog keys: {missing_analog_keys}")
                else:
                    print("✅ Analog structure is complete")
            
            # Check timeline data
            timeline = result.get('timeline_data', {})
            if 'forecast_timeline' in timeline and timeline['forecast_timeline']:
                print(f"✅ Timeline data: {len(timeline['forecast_timeline'])} points")
            else:
                print("⚠️ Timeline data missing or empty")
            
            # Check similarity analysis
            similarity = result.get('similarity_analysis', {})
            if 'confidence_metrics' in similarity:
                confidence = similarity['confidence_metrics'].get('overall_confidence', 0)
                print(f"✅ Similarity analysis: overall confidence={confidence:.3f}")
            else:
                print("⚠️ Similarity analysis missing confidence metrics")
            
            # Check meteorological context
            meteo = result.get('meteorological_context', {})
            if 'temporal_context' in meteo:
                season = meteo['temporal_context'].get('season', 'unknown')
                print(f"✅ Meteorological context: season={season}")
            else:
                print("⚠️ Meteorological context missing temporal info")
        
        # Performance test
        print("\n⚡ Testing performance with larger k...")
        import time
        start = time.time()
        
        result = await service.get_analog_details(
            horizon=24,
            variable="temperature",
            k=100
        )
        
        elapsed = (time.time() - start) * 1000
        
        if result.get("success"):
            analogs_count = len(result.get('analogs', []))
            processing_time = result['query_metadata']['processing_time_ms']
            print(f"✅ Large k test: {analogs_count} analogs")
            print(f"   - Processing time: {processing_time:.1f}ms")
            print(f"   - Total elapsed: {elapsed:.1f}ms")
        else:
            print(f"❌ Large k test failed: {result.get('error')}")
        
        return True
        
    except Exception as e:
        print(f"❌ Test failed with exception: {e}")
        import traceback
        traceback.print_exc()
        return False

async def test_detailed_response():
    """Test and display a detailed response for inspection"""
    print("\n📋 Testing detailed response structure...")
    
    try:
        service = await get_analog_search_service()
        
        result = await service.get_analog_details(
            horizon=24,
            variable="temperature", 
            k=3,
            correlation_id="TEST001"
        )
        
        if result.get("success"):
            print("✅ Detailed test successful")
            print("\n📊 Sample Response Structure:")
            print(f"  Query Metadata:")
            print(f"    - Correlation ID: {result['query_metadata']['correlation_id']}")
            print(f"    - Processing time: {result['query_metadata']['processing_time_ms']:.1f}ms")
            print(f"    - Horizon: {result['query_metadata']['horizon']}h")
            print(f"    - Variable: {result['query_metadata']['variable']}")
            
            if result.get('analogs'):
                print(f"\n  Analogs ({len(result['analogs'])} found):")
                for analog in result['analogs'][:2]:  # Show first 2
                    print(f"    Analog #{analog['rank']}:")
                    print(f"      - Similarity: {analog['similarity_score']:.3f}")
                    print(f"      - Distance: {analog['distance']:.3f}")
                    print(f"      - Season: {analog['temporal_info']['season']}")
                    print(f"      - Predicted {analog['forecast_outcome']['variable']}: {analog['forecast_outcome']['predicted_value']}")
                    print(f"      - Reliability: {analog['forecast_outcome']['reliability_class']}")
            
            timeline = result.get('timeline_data', {})
            if timeline.get('ensemble_statistics'):
                temp_stats = timeline['ensemble_statistics'].get('temperature', {})
                print(f"\n  Ensemble Statistics:")
                print(f"    - Temperature mean: {temp_stats.get('ensemble_mean', 'N/A')}°C")
                print(f"    - Temperature std: {temp_stats.get('ensemble_std', 'N/A')}°C")
            
            similarity = result.get('similarity_analysis', {})
            if similarity.get('confidence_metrics'):
                metrics = similarity['confidence_metrics']
                print(f"\n  Confidence Metrics:")
                print(f"    - Overall confidence: {metrics.get('overall_confidence', 'N/A')}")
                print(f"    - High confidence analogs: {metrics.get('high_confidence_analogs', 'N/A')}")
                print(f"    - Consensus strength: {metrics.get('consensus_strength', 'N/A')}")
            
            meteo = result.get('meteorological_context', {})
            if meteo.get('pattern_classification'):
                pattern = meteo['pattern_classification']
                print(f"\n  Weather Pattern:")
                print(f"    - Type: {pattern.get('pattern_type', 'N/A')}")
                print(f"    - Stability: {pattern.get('stability', 'N/A')}")
                print(f"    - Description: {pattern.get('pattern_description', 'N/A')}")
            
        else:
            print(f"❌ Detailed test failed: {result.get('error')}")
            return False
            
        return True
        
    except Exception as e:
        print(f"❌ Detailed test failed with exception: {e}")
        return False

async def main():
    """Main test function"""
    print("🚀 Starting analog details service tests...\n")
    
    # Run basic tests
    basic_success = await test_analog_details()
    
    if basic_success:
        # Run detailed response test
        detailed_success = await test_detailed_response()
        
        if detailed_success:
            print("\n🎉 All tests passed successfully!")
            print("✅ get_analog_details() method is working correctly")
            return True
    
    print("\n❌ Some tests failed!")
    return False

if __name__ == "__main__":
    import sys
    success = asyncio.run(main())
    sys.exit(0 if success else 1)