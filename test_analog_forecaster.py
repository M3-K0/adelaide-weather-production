#!/usr/bin/env python3
"""
Test Analog Forecaster Demo
===========================

Demonstrates the complete analog ensemble forecasting pipeline:
Live Weather → AI Embeddings → Historical Search → Ensemble Forecast

Shows GPT-5's validated methodology in action with professional output.
"""

import sys
import time
import numpy as np
import pandas as pd
from pathlib import Path

# Add project to path
sys.path.append(str(Path(__file__).parent))

from core.analog_forecaster import RealTimeAnalogForecaster
from core.real_time_embedder import RealTimeEmbedder
from scripts.weather_api_client import WeatherApiClient
import faiss

def load_faiss_index(horizon: int):
    """Load FAISS index for specified horizon."""
    # Try FlatIP index first (more accurate)
    index_path = Path(f"indices/faiss_{horizon}h_flatip.faiss")
    if index_path.exists():
        return faiss.read_index(str(index_path))
    
    # Fall back to IVF-PQ index
    index_path = Path(f"indices/faiss_{horizon}h_ivfpq.faiss")
    if index_path.exists():
        return faiss.read_index(str(index_path))
    
    return None

def search_analogs(embedder, api_client, forecaster, k=50):
    """Complete analog search pipeline."""
    print("🔍 Running Complete Analog Forecasting Pipeline...")
    print("=" * 55)
    
    # Step 1: Get live Adelaide weather
    print("📡 Step 1: Fetching live Adelaide weather...")
    current_weather = api_client.get_forecast_ready_data()
    
    if not current_weather:
        print("❌ Failed to get current weather")
        return None
    
    # Debug: show available keys
    print(f"   ✅ Retrieved weather data with keys: {list(current_weather.keys())}")
    
    # Show temperature if available
    temp_key = None
    for key in current_weather.keys():
        if 'temp' in key.lower() or 't2m' in key:
            temp_key = key
            break
    
    if temp_key:
        temp = current_weather[temp_key]
        if temp_key == 't2m':
            temp_c = temp - 273.15  # Convert K to C
        else:
            temp_c = temp  # Assume already in C
        print(f"   🌡️ Current temperature: {temp_c:.1f}°C")
    
    # Step 2: Generate embeddings for multiple horizons
    print("\n🧠 Step 2: Generating AI embeddings...")
    horizons = [6, 12, 24, 48]
    
    start_time = time.time()
    embeddings_dict = embedder.generate_batch(current_weather, horizons)
    embedding_time = time.time() - start_time
    
    if embeddings_dict is None or len(embeddings_dict) == 0:
        print("❌ Failed to generate embeddings")
        return None
        
    # Handle embeddings (could be dict or array)
    if isinstance(embeddings_dict, dict):
        print(f"   ✅ Generated {len(embeddings_dict)} embeddings in {embedding_time*1000:.0f}ms")
        print(f"   📊 Available horizons: {list(embeddings_dict.keys())}")
        embeddings_map = embeddings_dict
    else:
        # Assume numpy array in same order as horizons
        print(f"   ✅ Generated {len(embeddings_dict)} embeddings in {embedding_time*1000:.0f}ms")
        print(f"   📊 Embedding shape: {embeddings_dict.shape}")
        embeddings_map = {horizons[i]: embeddings_dict[i] for i in range(len(horizons))}
    
    # Step 3: Search for analogs
    print("\n🔎 Step 3: Searching for historical analogs...")
    analog_results = {}
    
    for horizon in horizons:
        # Load FAISS index
        index = load_faiss_index(horizon)
        if index is None:
            print(f"   ⚠️ No index found for {horizon}h")
            continue
        
        # Search for similar patterns
        if horizon not in embeddings_map:
            print(f"   ⚠️ No embedding for {horizon}h")
            continue
            
        embedding = embeddings_map[horizon].reshape(1, -1).astype(np.float32)
        
        start_time = time.time()
        distances, indices = index.search(embedding, k)
        search_time = time.time() - start_time
        
        analog_results[horizon] = {
            'indices': indices[0],
            'distances': distances[0], 
            'init_time': pd.Timestamp.now(),
            'search_time_ms': search_time * 1000
        }
        
        print(f"   ✅ {horizon}h: Found {len(indices[0])} analogs in {search_time*1000:.1f}ms")
    
    # Step 4: Generate ensemble forecasts
    print("\n🌤️ Step 4: Generating ensemble forecasts...")
    
    start_time = time.time()
    forecasts = forecaster.generate_multi_horizon_forecast(analog_results)
    forecast_time = time.time() - start_time
    
    print(f"   ✅ Generated {len(forecasts)} forecasts in {forecast_time*1000:.0f}ms")
    
    # Step 5: Display results
    print("\n" + "="*55)
    print(forecaster.format_forecast_summary(forecasts))
    print("="*55)
    
    # Performance summary
    total_time = embedding_time + sum(r['search_time_ms']/1000 for r in analog_results.values()) + forecast_time
    print(f"\n⚡ Performance: {total_time*1000:.0f}ms total")
    print(f"   • Embeddings: {embedding_time*1000:.0f}ms")
    print(f"   • FAISS search: {sum(r['search_time_ms'] for r in analog_results.values()):.0f}ms")
    print(f"   • Ensemble forecast: {forecast_time*1000:.0f}ms")
    
    return forecasts

def main():
    """Main demo."""
    print("🚀 Adelaide Analog Ensemble Forecasting Demo")
    print("Implementing GPT-5's validated methodology")
    print()
    
    try:
        # Initialize components
        print("🔧 Initializing components...")
        embedder = RealTimeEmbedder()
        api_client = WeatherApiClient()
        forecaster = RealTimeAnalogForecaster()
        
        print("   ✅ Real-time embedder ready")
        print("   ✅ Weather API client ready") 
        print("   ✅ Analog forecaster ready")
        
        # Run complete pipeline
        forecasts = search_analogs(embedder, api_client, forecaster)
        
        if forecasts:
            print(f"\n🎉 SUCCESS: Generated forecasts for {len(forecasts)} horizons!")
            print("✅ Adelaide Analog Ensemble Forecasting System Operational!")
        else:
            print("\n❌ Pipeline failed")
            
    except Exception as e:
        print(f"\n❌ Error: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    main()