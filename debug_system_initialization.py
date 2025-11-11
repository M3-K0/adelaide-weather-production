#!/usr/bin/env python3
"""
Debug System Initialization
============================

This script tests each component of the Adelaide Weather Forecasting System
to identify where the mock data fallback is being triggered.
"""

import os
import sys
import traceback
from pathlib import Path
import asyncio
import logging

# Add project root to path
sys.path.append(str(Path(__file__).parent))

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

async def test_analog_search_service():
    """Test AnalogSearchService initialization"""
    logger.info("=== Testing AnalogSearchService ===")
    
    try:
        from api.services.analog_search import AnalogSearchService, AnalogSearchConfig
        
        # Test configuration creation
        config = AnalogSearchConfig()
        logger.info(f"✅ Config created: model_path={config.model_path}")
        logger.info(f"   embeddings_dir={config.embeddings_dir}")
        logger.info(f"   indices_dir={config.indices_dir}")
        
        # Check if required files exist
        model_path = Path(config.model_path)
        embeddings_dir = Path(config.embeddings_dir)
        indices_dir = Path(config.indices_dir)
        
        logger.info(f"Model file exists: {model_path.exists()} ({model_path})")
        logger.info(f"Embeddings dir exists: {embeddings_dir.exists()} ({embeddings_dir})")
        logger.info(f"Indices dir exists: {indices_dir.exists()} ({indices_dir})")
        
        if indices_dir.exists():
            indices = list(indices_dir.glob("*.faiss"))
            logger.info(f"Found {len(indices)} FAISS indices: {[i.name for i in indices]}")
        
        # Test service creation
        service = AnalogSearchService(config)
        logger.info("✅ AnalogSearchService created")
        
        # Test service initialization
        logger.info("Attempting service initialization...")
        init_result = await service.initialize()
        logger.info(f"Service initialization result: {init_result}")
        logger.info(f"Degraded mode: {service.degraded_mode}")
        
        # Test health check
        health = await service.health_check()
        logger.info(f"Service health: {health['status']}")
        logger.info(f"Pool initialized: {health['pool']['initialized']}")
        logger.info(f"Pool size: {health['pool']['pool_size']}")
        
        return service, init_result
        
    except Exception as e:
        logger.error(f"❌ AnalogSearchService failed: {e}")
        logger.error(traceback.format_exc())
        return None, False

async def test_forecaster_direct():
    """Test the core AnalogEnsembleForecaster directly"""
    logger.info("=== Testing AnalogEnsembleForecaster ===")
    
    try:
        from scripts.analog_forecaster import AnalogEnsembleForecaster
        
        model_path = "outputs/training_production_demo/best_model.pt"
        config_path = "configs/model.yaml"
        embeddings_dir = "embeddings"
        indices_dir = "indices"
        
        logger.info(f"Attempting to create forecaster with:")
        logger.info(f"  model_path: {model_path}")
        logger.info(f"  config_path: {config_path}")
        logger.info(f"  embeddings_dir: {embeddings_dir}")
        logger.info(f"  indices_dir: {indices_dir}")
        
        forecaster = AnalogEnsembleForecaster(
            model_path=model_path,
            config_path=config_path,
            embeddings_dir=embeddings_dir,
            indices_dir=indices_dir,
            use_optimized_index=True
        )
        
        logger.info("✅ AnalogEnsembleForecaster created successfully")
        
        # Check what indices were loaded
        logger.info(f"Loaded indices for horizons: {list(forecaster.indices.keys())}")
        
        for horizon in forecaster.indices:
            index = forecaster.indices[horizon]
            logger.info(f"  {horizon}h: {index.ntotal} vectors, dimension {index.d}")
        
        return forecaster, True
        
    except Exception as e:
        logger.error(f"❌ AnalogEnsembleForecaster failed: {e}")
        logger.error(traceback.format_exc())
        return None, False

def test_model_loading():
    """Test model loading separately"""
    logger.info("=== Testing Model Loading ===")
    
    try:
        import torch
        from core.model_loader import WeatherCNNEncoder
        
        model_path = "outputs/training_production_demo/best_model.pt"
        logger.info(f"Testing model loading from: {model_path}")
        
        if not Path(model_path).exists():
            logger.error(f"❌ Model file does not exist: {model_path}")
            return None, False
        
        # Test model creation
        model = WeatherCNNEncoder()
        logger.info("✅ Model instance created")
        
        # Test checkpoint loading
        checkpoint = torch.load(model_path, map_location='cpu', weights_only=False)
        logger.info(f"✅ Checkpoint loaded, keys: {list(checkpoint.keys())}")
        
        # Test state dict loading
        model.load_state_dict(checkpoint['model_state_dict'])
        logger.info("✅ Model state dict loaded")
        
        model.eval()
        logger.info("✅ Model set to eval mode")
        
        return model, True
        
    except Exception as e:
        logger.error(f"❌ Model loading failed: {e}")
        logger.error(traceback.format_exc())
        return None, False

def test_faiss_indices():
    """Test FAISS indices loading directly"""
    logger.info("=== Testing FAISS Indices ===")
    
    try:
        import faiss
        
        indices_dir = Path("indices")
        logger.info(f"Testing FAISS indices in: {indices_dir}")
        
        if not indices_dir.exists():
            logger.error(f"❌ Indices directory does not exist: {indices_dir}")
            return False
        
        faiss_files = list(indices_dir.glob("*.faiss"))
        logger.info(f"Found {len(faiss_files)} FAISS files: {[f.name for f in faiss_files]}")
        
        loaded_indices = {}
        
        for faiss_file in faiss_files:
            try:
                logger.info(f"Loading {faiss_file.name}...")
                index = faiss.read_index(str(faiss_file))
                logger.info(f"  ✅ {faiss_file.name}: {index.ntotal} vectors, dimension {index.d}")
                loaded_indices[faiss_file.name] = index
                
            except Exception as e:
                logger.error(f"  ❌ Failed to load {faiss_file.name}: {e}")
        
        logger.info(f"Successfully loaded {len(loaded_indices)} indices")
        return len(loaded_indices) > 0
        
    except Exception as e:
        logger.error(f"❌ FAISS indices test failed: {e}")
        logger.error(traceback.format_exc())
        return False

async def test_forecast_adapter():
    """Test ForecastAdapter initialization and forecasting"""
    logger.info("=== Testing ForecastAdapter ===")
    
    try:
        from api.forecast_adapter import ForecastAdapter
        
        adapter = ForecastAdapter()
        logger.info("✅ ForecastAdapter created")
        
        # Test system health check
        health = await adapter.get_system_health()
        logger.info(f"Adapter health: {health}")
        
        # Test a simple forecast
        logger.info("Attempting simple forecast...")
        result = await adapter.forecast_with_uncertainty(
            horizon="24h",
            variables=["t2m", "u10", "v10"]
        )
        
        logger.info(f"Forecast result keys: {list(result.keys())}")
        for var, data in result.items():
            logger.info(f"  {var}: available={data.get('available', 'unknown')}")
        
        return adapter, result
        
    except Exception as e:
        logger.error(f"❌ ForecastAdapter failed: {e}")
        logger.error(traceback.format_exc())
        return None, None

def check_environment():
    """Check environment configuration"""
    logger.info("=== Checking Environment ===")
    
    # Check current working directory
    logger.info(f"Current working directory: {os.getcwd()}")
    
    # Check important environment variables
    env_vars_to_check = [
        'API_TOKEN', 'WEATHER_API_KEY', 'ENVIRONMENT', 'LOG_LEVEL',
        'FAISS_INDEX_PATH', 'MODEL_PATH', 'EMBEDDINGS_PATH'
    ]
    
    for var in env_vars_to_check:
        value = os.getenv(var, 'NOT_SET')
        logger.info(f"{var}: {value}")
    
    # Check critical files exist
    critical_files = [
        "outputs/training_production_demo/best_model.pt",
        "configs/model.yaml",
        "indices/faiss_24h_flatip.faiss",
        "api/forecast_adapter.py",
        "core/analog_forecaster.py",
    ]
    
    for file_path in critical_files:
        path = Path(file_path)
        logger.info(f"{file_path}: {'EXISTS' if path.exists() else 'MISSING'}")

async def main():
    """Run all diagnostic tests"""
    logger.info("Adelaide Weather System Diagnostic Tool")
    logger.info("=" * 50)
    
    # 1. Environment check
    check_environment()
    
    # 2. Test model loading
    model, model_ok = test_model_loading()
    
    # 3. Test FAISS indices
    faiss_ok = test_faiss_indices()
    
    # 4. Test core forecaster
    forecaster, forecaster_ok = await test_forecaster_direct()
    
    # 5. Test analog search service
    service, service_ok = await test_analog_search_service()
    
    # 6. Test forecast adapter
    adapter, forecast_result = await test_forecast_adapter()
    
    # Summary
    logger.info("\n" + "=" * 50)
    logger.info("DIAGNOSTIC SUMMARY")
    logger.info("=" * 50)
    logger.info(f"Model Loading: {'✅ PASS' if model_ok else '❌ FAIL'}")
    logger.info(f"FAISS Indices: {'✅ PASS' if faiss_ok else '❌ FAIL'}")
    logger.info(f"Core Forecaster: {'✅ PASS' if forecaster_ok else '❌ FAIL'}")
    logger.info(f"Analog Search Service: {'✅ PASS' if service_ok else '❌ FAIL'}")
    logger.info(f"Forecast Adapter: {'✅ PASS' if adapter is not None else '❌ FAIL'}")
    
    if service and hasattr(service, 'degraded_mode'):
        logger.info(f"Service Degraded Mode: {service.degraded_mode}")
    
    if forecast_result:
        # Check if result contains mock data indicators
        mock_indicators = []
        for var, data in forecast_result.items():
            if isinstance(data, dict):
                metadata = data.get('metadata', {})
                if 'fallback' in str(metadata).lower() or 'mock' in str(metadata).lower():
                    mock_indicators.append(var)
        
        if mock_indicators:
            logger.warning(f"❌ MOCK DATA DETECTED in variables: {mock_indicators}")
        else:
            logger.info("✅ No obvious mock data indicators found")

if __name__ == "__main__":
    asyncio.run(main())