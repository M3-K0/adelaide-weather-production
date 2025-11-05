#!/usr/bin/env python3
"""
End-to-end test for analog forecaster to validate FAISS similarity fix.
This test ensures the entire pipeline works correctly with realistic similarities.
"""
import numpy as np
import torch
import xarray as xr
from datetime import datetime, timedelta
import logging
import sys
import os

# Add parent directory to path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from scripts.analog_forecaster import AnalogForecaster

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def test_analog_forecaster_end_to_end():
    """Test the complete analog forecasting pipeline."""
    logger.info("🔬 Starting end-to-end analog forecaster test...")
    
    # Test parameters
    test_date = datetime(2019, 6, 15, 12, 0)  # Summer test date
    test_horizon = 24  # 24-hour forecast
    
    try:
        # Initialize forecaster
        logger.info(f"📡 Initializing AnalogForecaster for {test_horizon}h horizon...")
        forecaster = AnalogForecaster(
            model_path="models/encoder_model_final.pth",
            indices_dir="indices",
            embeddings_dir="embeddings",
            era5_path="data/era5_adelaide_2010_2020.zarr",
            lead_time_hours=test_horizon
        )
        
        # Generate forecast
        logger.info(f"🎯 Generating forecast for {test_date}...")
        forecast = forecaster.forecast(test_date)
        
        # Validate forecast structure
        logger.info("✅ Validating forecast structure...")
        assert isinstance(forecast, dict), "Forecast should be a dictionary"
        
        required_fields = ['analog_dates', 'similarities', 'forecast_mean', 'forecast_std', 'forecast_ensemble']
        for field in required_fields:
            assert field in forecast, f"Missing required field: {field}"
        
        # Validate analog dates
        analog_dates = forecast['analog_dates']
        assert len(analog_dates) == 50, f"Expected 50 analogs, got {len(analog_dates)}"
        logger.info(f"📅 Found {len(analog_dates)} analog dates")
        
        # Validate similarities (critical test for our FAISS fix)
        similarities = forecast['similarities']
        assert len(similarities) == 50, f"Expected 50 similarities, got {len(similarities)}"
        
        # Check similarity values are realistic (not 0.000)
        min_sim = np.min(similarities)
        max_sim = np.max(similarities)
        mean_sim = np.mean(similarities)
        
        logger.info(f"🔍 Similarity statistics:")
        logger.info(f"   Min: {min_sim:.6f}")
        logger.info(f"   Max: {max_sim:.6f}")
        logger.info(f"   Mean: {mean_sim:.6f}")
        
        # Critical validation: similarities should be realistic
        assert min_sim > 0.1, f"Minimum similarity too low: {min_sim} (FAISS bug not fixed?)"
        assert max_sim <= 1.0, f"Maximum similarity too high: {max_sim}"
        assert mean_sim > 0.3, f"Mean similarity too low: {mean_sim}"
        
        # Validate forecast fields
        forecast_mean = forecast['forecast_mean']
        forecast_std = forecast['forecast_std']
        forecast_ensemble = forecast['forecast_ensemble']
        
        logger.info("🌡️ Validating forecast values...")
        
        # Check temperature ranges are realistic for Adelaide
        temp_mean = forecast_mean.sel(variable='t2m').values
        temp_std = forecast_std.sel(variable='t2m').values
        
        # Convert from Kelvin to Celsius for validation
        temp_mean_c = temp_mean - 273.15
        temp_std_c = temp_std
        
        logger.info(f"🌡️ Temperature forecast (°C):")
        logger.info(f"   Mean: {temp_mean_c:.2f}°C")
        logger.info(f"   Std: {temp_std_c:.2f}°C")
        
        # Realistic temperature ranges for Adelaide
        assert -10 < temp_mean_c < 50, f"Unrealistic temperature: {temp_mean_c}°C"
        assert 0 < temp_std_c < 20, f"Unrealistic temperature std: {temp_std_c}°C"
        
        # Validate ensemble has correct shape
        expected_shape = (50, len(forecast_mean.time), len(forecast_mean.variable))
        assert forecast_ensemble.shape == expected_shape, f"Wrong ensemble shape: {forecast_ensemble.shape}"
        
        # Print some analog dates for inspection
        logger.info("📋 Top 5 analog dates with similarities:")
        for i, (date, sim) in enumerate(zip(analog_dates[:5], similarities[:5])):
            logger.info(f"   {i+1}. {date} (similarity: {sim:.6f})")
        
        logger.info("🎉 END-TO-END TEST PASSED!")
        logger.info("✅ FAISS similarity bug is fixed")
        logger.info("✅ Analog forecaster working correctly")
        logger.info("✅ Realistic forecast values generated")
        
        return True
        
    except Exception as e:
        logger.error(f"❌ End-to-end test failed: {str(e)}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    # Change to weather forecast directory
    os.chdir("/home/micha/weather-forecast-final")
    
    success = test_analog_forecaster_end_to_end()
    sys.exit(0 if success else 1)