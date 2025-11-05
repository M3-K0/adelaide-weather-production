#!/usr/bin/env python3
"""
Compact Real-Time Embedder
==========================

Optimized batched embedding generation for Adelaide weather forecasting.
Implements GPT-5 recommendations: single forward pass for all horizons.

Key Features:
- Batched horizon processing (6h, 12h, 24h, 48h) in single inference
- L2 normalization for cosine similarity compatibility  
- Data quality validation with ERA5 format consistency
- Performance optimized for <10 second inference

Usage:
    embedder = RealTimeEmbedder()
    embeddings = embedder.generate_batch(era5_data, horizons=[6, 12, 24, 48])
"""

import os
import time
import logging
import numpy as np
import pandas as pd
from typing import Dict, List, Optional, Tuple
from pathlib import Path

# Setup logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Set thread control for performance
os.environ['OMP_NUM_THREADS'] = '2'
os.environ['TORCH_NUM_THREADS'] = '2'

class RealTimeEmbedder:
    """Compact real-time embedding generator with batched horizon processing."""
    
    def __init__(self, model_path: Optional[str] = None, device: str = 'cpu'):
        """Initialize embedder with model loading and warmup."""
        self.device = device
        self.model = None
        self.is_warmed_up = False
        
        # Model configuration from specs
        self.embedding_dim = 256
        self.spatial_shape = (16, 16)
        self.num_variables = 9
        
        # Performance tracking
        self.timing_stats = {
            'load_ms': 0,
            'preprocess_ms': 0, 
            'inference_ms': 0,
            'normalize_ms': 0,
            'total_ms': 0
        }
        
        # Load model
        start_time = time.time()
        self._load_model(model_path)
        self.timing_stats['load_ms'] = (time.time() - start_time) * 1000
        
        logger.info(f"RealTimeEmbedder initialized in {self.timing_stats['load_ms']:.1f}ms")
    
    def _load_model(self, model_path: Optional[str] = None):
        """Load trained CNN encoder model."""
        try:
            import torch
            from .model_loader import load_model_safe
            
            # Use safe model loader
            self.model = load_model_safe(model_path, self.device)
            
            if self.model is not None:
                # Enable inference optimization
                if hasattr(torch, 'inference_mode'):
                    self.inference_context = torch.inference_mode
                else:
                    self.inference_context = torch.no_grad
                
                logger.info("Model loaded successfully")
            else:
                logger.error("Model loading failed")
            
        except ImportError:
            logger.error("PyTorch not available - cannot load model")
            self.model = None
        except Exception as e:
            logger.error(f"Failed to load model: {e}")
            self.model = None
    
    def _warmup(self):
        """Warmup model with dummy data for consistent timing."""
        if self.model is None or self.is_warmed_up:
            return
            
        try:
            import torch
            
            logger.info("Warming up model...")
            dummy_data = torch.randn(4, self.num_variables, *self.spatial_shape)
            dummy_lead_times = torch.tensor([6, 12, 24, 48])  # Lead times in hours
            dummy_months = torch.tensor([0, 0, 0, 0])  # January for dummy test
            dummy_hours = torch.tensor([0, 0, 0, 0])   # Midnight for dummy test
            
            with self.inference_context():
                _ = self.model(dummy_data, dummy_lead_times, dummy_months, dummy_hours)
            
            self.is_warmed_up = True
            logger.info("Model warmup complete")
            
        except Exception as e:
            logger.warning(f"Model warmup failed: {e}")
    
    def _preprocess_era5_data(self, era5_data: Dict) -> Optional[np.ndarray]:
        """Convert ERA5 format to model input tensor (16x16x9)."""
        start_time = time.time()
        
        try:
            # Extract variables in model order
            variables = [
                era5_data.get('z500'),      # geopotential 500mb
                era5_data.get('t2m'),       # 2m temperature  
                era5_data.get('t850'),      # temperature 850mb
                era5_data.get('q850'),      # specific humidity 850mb
                era5_data.get('u10'),       # u-wind 10m
                era5_data.get('v10'),       # v-wind 10m
                era5_data.get('u850'),      # u-wind 850mb
                era5_data.get('v850'),      # v-wind 850mb
                era5_data.get('cape', 0.0)  # CAPE
            ]
            
            # Check for missing critical variables
            missing_vars = [i for i, v in enumerate(variables) if v is None]
            if missing_vars:
                logger.warning(f"Missing variables at indices: {missing_vars}")
                return None
            
            # Create spatial grid (simplified - single point expanded)
            # Real implementation would use spatial interpolation
            weather_grid = np.zeros((self.num_variables, *self.spatial_shape))
            
            for i, value in enumerate(variables):
                if value is not None:
                    weather_grid[i, :, :] = float(value)
            
            self.timing_stats['preprocess_ms'] = (time.time() - start_time) * 1000
            return weather_grid
            
        except Exception as e:
            logger.error(f"Preprocessing failed: {e}")
            return None
    
    def _validate_data_quality(self, era5_data: Dict) -> bool:
        """Quick data quality validation."""
        # Temperature check (ERA5 in Kelvin)
        t2m = era5_data.get('t2m')
        if t2m and not (240 < t2m < 320):
            logger.warning(f"Temperature out of range: {t2m}K")
            return False
        
        # Pressure check  
        msl = era5_data.get('msl')
        if msl and not (90000 < msl < 110000):
            logger.warning(f"Pressure out of range: {msl}Pa")
            return False
        
        # Geopotential height check
        z500 = era5_data.get('z500')
        if z500 and not (4800 < z500 < 6000):
            logger.warning(f"500mb height out of range: {z500}m")
            return False
        
        return True
    
    def generate_batch(self, era5_data: Dict, horizons: List[int] = [6, 12, 24, 48]) -> Optional[np.ndarray]:
        """Generate embeddings for all horizons in single forward pass."""
        start_time = time.time()
        
        if self.model is None:
            logger.error("No model loaded")
            return None
        
        # Warmup if needed
        if not self.is_warmed_up:
            self._warmup()
        
        # Data quality validation
        if not self._validate_data_quality(era5_data):
            logger.error("Data quality validation failed")
            return None
        
        # Preprocess data
        weather_grid = self._preprocess_era5_data(era5_data)
        if weather_grid is None:
            return None
        
        try:
            import torch
            import faiss
            
            # Convert to tensors
            inference_start = time.time()
            
            # Create batch: repeat weather data for each horizon
            batch_size = len(horizons)
            weather_batch = np.tile(weather_grid[None, ...], (batch_size, 1, 1, 1))
            
            # Extract temporal information from ERA5 data
            # ERA5 time should be available in the data
            current_time = pd.Timestamp.now(tz='UTC')  # Default to current time
            if 'time' in era5_data and era5_data['time'] is not None:
                try:
                    current_time = pd.to_datetime(era5_data['time'])
                except:
                    logger.warning("Could not parse time from ERA5 data, using current time")
            
            # Extract month (0-11) and hour (0-23) for each horizon
            months = []
            hours = []
            for h in horizons:
                forecast_time = current_time + pd.Timedelta(hours=h)
                months.append(forecast_time.month - 1)  # Convert to 0-11
                hours.append(forecast_time.hour)        # Already 0-23
            
            # Convert to tensors
            weather_tensor = torch.from_numpy(weather_batch).float()
            lead_times_tensor = torch.tensor(horizons, dtype=torch.long)      # Lead times in hours
            months_tensor = torch.tensor(months, dtype=torch.long)             # Months (0-11) 
            hours_tensor = torch.tensor(hours, dtype=torch.long)               # Hours (0-23)
            
            # Single forward pass for all horizons
            with self.inference_context():
                embeddings = self.model(weather_tensor, lead_times_tensor, months_tensor, hours_tensor)  # (batch, 256)
            
            self.timing_stats['inference_ms'] = (time.time() - inference_start) * 1000
            
            # L2 normalization for cosine similarity
            normalize_start = time.time()
            embeddings_np = embeddings.cpu().numpy().astype(np.float32)
            faiss.normalize_L2(embeddings_np)  # In-place L2 normalization
            
            self.timing_stats['normalize_ms'] = (time.time() - normalize_start) * 1000
            self.timing_stats['total_ms'] = (time.time() - start_time) * 1000
            
            logger.info(f"Generated {len(horizons)} embeddings in {self.timing_stats['total_ms']:.1f}ms")
            logger.debug(f"Timing: preprocess={self.timing_stats['preprocess_ms']:.1f}ms, "
                        f"inference={self.timing_stats['inference_ms']:.1f}ms, "
                        f"normalize={self.timing_stats['normalize_ms']:.1f}ms")
            
            return embeddings_np
            
        except ImportError as e:
            logger.error(f"Missing dependencies: {e}")
            return None
        except Exception as e:
            logger.error(f"Embedding generation failed: {e}")
            return None
    
    def get_timing_stats(self) -> Dict[str, float]:
        """Get performance timing statistics."""
        return self.timing_stats.copy()

def main():
    """Test the real-time embedder."""
    # Test data (mock ERA5 format)
    test_data = {
        'z500': 5640.0,      # 500mb geopotential height
        't2m': 293.15,       # 2m temperature (20°C)
        't850': 285.65,      # 850mb temperature (12.5°C)
        'q850': 0.008,       # 850mb specific humidity
        'u10': -2.5,         # 10m u-wind
        'v10': 4.2,          # 10m v-wind
        'u850': -8.1,        # 850mb u-wind
        'v850': 12.3,        # 850mb v-wind
        'cape': 150.0,       # CAPE
        'msl': 101520.0,     # mean sea level pressure
        'source': 'test_data'
    }
    
    # Test embedder
    embedder = RealTimeEmbedder()
    
    if embedder.model is None:
        print("❌ Model not available - testing data pipeline only")
        weather_grid = embedder._preprocess_era5_data(test_data)
        if weather_grid is not None:
            print(f"✅ Data preprocessing successful: {weather_grid.shape}")
        return
    
    # Test batch generation
    print("Testing batched embedding generation...")
    embeddings = embedder.generate_batch(test_data, horizons=[6, 12, 24, 48])
    
    if embeddings is not None:
        print(f"✅ Generated embeddings: {embeddings.shape}")
        print(f"   L2 norms: {np.linalg.norm(embeddings, axis=1)}")
        print(f"   Performance: {embedder.get_timing_stats()}")
        
        # Test similarity calculation
        similarity_matrix = np.dot(embeddings, embeddings.T)
        print(f"   Self-similarities: {np.diag(similarity_matrix)}")
    else:
        print("❌ Embedding generation failed")

if __name__ == "__main__":
    main()