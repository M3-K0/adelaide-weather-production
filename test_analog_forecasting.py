#!/usr/bin/env python3
"""
Test Analog Forecasting Functionality
=====================================

Test the complete analog forecasting pipeline to ensure all data artifacts
work together correctly for production forecasts.
"""

import sys
import time
import numpy as np
from pathlib import Path

# Add core to path
sys.path.append('core')

try:
    from analog_forecaster import RealTimeAnalogForecaster
    import faiss
    DEPS_AVAILABLE = True
except ImportError as e:
    print(f"❌ Missing dependencies: {e}")
    DEPS_AVAILABLE = False

def test_analog_forecasting():
    """Test the complete analog forecasting pipeline."""
    print("🧪 Testing Analog Forecasting Pipeline...")
    
    if not DEPS_AVAILABLE:
        print("❌ Cannot test forecasting - missing dependencies")
        return False
    
    try:
        # Initialize forecaster
        print("  📋 Initializing forecaster...")
        forecaster = RealTimeAnalogForecaster(outcomes_dir=Path("outcomes"))
        
        # Test each horizon
        horizons_to_test = [6, 12, 24, 48]
        results = {}
        
        for horizon in horizons_to_test:
            print(f"  🕐 Testing {horizon}h horizon...")
            
            # Load outcomes for this horizon
            start_time = time.time()
            success = forecaster.load_outcomes_for_horizon(horizon)
            load_time = time.time() - start_time
            
            if not success:
                print(f"    ❌ Failed to load outcomes for {horizon}h")
                continue
            
            # Load FAISS index
            index_path = Path(f"indices/faiss_{horizon}h_flatip.faiss")
            if not index_path.exists():
                print(f"    ❌ FAISS index not found: {index_path}")
                continue
                
            index = faiss.read_index(str(index_path))
            
            # Load embeddings 
            embeddings_path = Path(f"embeddings/embeddings_{horizon}h.npy")
            if not embeddings_path.exists():
                print(f"    ❌ Embeddings not found: {embeddings_path}")
                continue
                
            embeddings = np.load(embeddings_path, mmap_mode='r')
            
            # Create a test query vector (use first embedding as query)
            query_vector = embeddings[0:1].copy().astype(np.float32)
            
            # Perform similarity search
            start_search = time.time()
            distances, indices = index.search(query_vector, 30)  # Top 30 analogs
            search_time = time.time() - start_search
            
            # Get analog outcomes
            analog_indices = indices[0][1:]  # Skip self-match
            analog_distances = distances[0][1:]
            
            # Load outcomes for these analogs
            outcomes = forecaster.outcomes_cache[horizon]
            analog_outcomes = outcomes[analog_indices]
            
            # Compute weights (only for the analogs, not the query)
            weights = forecaster.compute_analog_weights(analog_distances, horizon)
            
            # Compute ensemble statistics
            stats = forecaster.compute_ensemble_statistics(analog_outcomes, weights)
            
            # Assess forecast confidence
            confidence = forecaster.assess_forecast_confidence(analog_distances, weights, horizon)
            
            results[horizon] = {
                "load_time_ms": load_time * 1000,
                "search_time_ms": search_time * 1000,
                "num_analogs": len(analog_indices),
                "outcomes_shape": outcomes.shape,
                "embeddings_shape": embeddings.shape,
                "valid_forecast": True,
                "variables_computed": len(stats),
                "ensemble_stats": {
                    "t2m_mean": float(stats.get('t2m', {}).get('mean', 0.0)),
                    "t2m_std": float(stats.get('t2m', {}).get('std', 0.0)),
                    "t2m_range": float(stats.get('t2m', {}).get('range', 0.0)),
                    "confidence": float(confidence)
                }
            }
            
            print(f"    ✅ {horizon}h: {len(analog_indices)} analogs, "
                  f"search: {search_time*1000:.1f}ms, "
                  f"confidence: {confidence:.2f}")
        
        # Summary
        successful_horizons = len(results)
        print(f"\n  📊 Successfully tested {successful_horizons}/4 horizons")
        
        if successful_horizons == 4:
            print("  🎉 All analog forecasting pipelines working correctly!")
            return True
        else:
            print("  ❌ Some forecasting pipelines failed")
            return False
            
    except Exception as e:
        print(f"  ❌ Error testing forecasting: {e}")
        import traceback
        traceback.print_exc()
        return False

def test_data_consistency():
    """Test consistency between different data files."""
    print("\n🔍 Testing Data Consistency...")
    
    horizons = [6, 12, 24, 48]
    consistency_issues = []
    
    for horizon in horizons:
        print(f"  📊 Checking {horizon}h data consistency...")
        
        try:
            # Load all data for this horizon
            embeddings = np.load(f"embeddings/embeddings_{horizon}h.npy", mmap_mode='r')
            outcomes = np.load(f"outcomes/outcomes_{horizon}h.npy", mmap_mode='r')
            
            # Load FAISS index
            index = faiss.read_index(f"indices/faiss_{horizon}h_flatip.faiss")
            
            # Check dimensions match
            if embeddings.shape[0] != index.ntotal:
                consistency_issues.append(f"{horizon}h: embeddings count ({embeddings.shape[0]}) != FAISS vectors ({index.ntotal})")
            
            if embeddings.shape[1] != index.d:
                consistency_issues.append(f"{horizon}h: embeddings dim ({embeddings.shape[1]}) != FAISS dim ({index.d})")
            
            # Check for reasonable outcome ranges
            if outcomes.shape[1] != 9:  # Should have 9 variables
                consistency_issues.append(f"{horizon}h: unexpected outcomes variables ({outcomes.shape[1]} != 9)")
            
            print(f"    ✅ {horizon}h: {embeddings.shape[0]} samples, {embeddings.shape[1]}D embeddings")
            
        except Exception as e:
            consistency_issues.append(f"{horizon}h: error loading data - {e}")
    
    if consistency_issues:
        print(f"  ❌ Found {len(consistency_issues)} consistency issues:")
        for issue in consistency_issues:
            print(f"    • {issue}")
        return False
    else:
        print("  ✅ All data files are consistent!")
        return True

def main():
    """Main test function."""
    print("🔬 Adelaide Weather Data Artifacts Integration Test")
    print("=" * 60)
    
    # Test data consistency first
    consistency_ok = test_data_consistency()
    
    # Test analog forecasting pipeline
    forecasting_ok = test_analog_forecasting()
    
    # Overall result
    print("\n" + "=" * 60)
    print("📋 Integration Test Results:")
    print(f"  Data Consistency: {'✅ PASS' if consistency_ok else '❌ FAIL'}")
    print(f"  Analog Forecasting: {'✅ PASS' if forecasting_ok else '❌ FAIL'}")
    
    if consistency_ok and forecasting_ok:
        print("\n🎉 ALL INTEGRATION TESTS PASSED - READY FOR PRODUCTION!")
        return True
    else:
        print("\n❌ INTEGRATION TESTS FAILED - NOT READY FOR PRODUCTION")
        return False

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)